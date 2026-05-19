import Foundation
import CryptoKit
import UIKit

/// エクスポート（持ち出し）サービス
///
/// **2 種類の Package を厳密に分離**：
///
/// ## 1. EmergencyPackage（緊急時用）
/// - **想定シーン**：警察・児相にこれから駆け込む、5 分以内に渡したい
/// - **内容**：最小限の証拠ハッシュ + 概要 PDF + 緊急連絡先
/// - **暗号化**：軽量（AES-GCM）。鍵はパスフレーズ or QR コード共有
/// - **サイズ**：< 10 MB（全証拠原本は含めない、ハッシュのみ）
/// - **想定受信者**：警察官、児相職員、救急医
///
/// ## 2. AnalysisPackage（分析・後日参照用）
/// - **想定シーン**：弁護士事務所で時間をかけて読む、後日の裁判準備
/// - **内容**：全証拠原本 + メタデータ + チェーン検証ファイル + 監査ログ
/// - **暗号化**：強固（AES-256-GCM + RSA-4096 鍵交換）
/// - **サイズ**：100 MB 〜 数 GB
/// - **想定受信者**：弁護士、外部監査人、共同研究者（匿名化版のみ）
///
/// ## 共通：監査ログ記録
/// 両方とも作成 / アクセス時に AuditLogService に記録される。
@MainActor
final class ExportService {

    static let shared = ExportService()
    private init() {}

    // MARK: - Emergency Package

    /// 緊急時用パッケージを 30 秒以内で生成
    ///
    /// パスフレーズは 6 桁の数字（被害者本人が口頭で警察官に伝えられる）。
    /// QR コードでも共有可能。
    func buildEmergencyPackage(
        case: LegalCase,
        passphrase: String,
        recipientHint: String? = nil
    ) async throws -> EmergencyPackage {

        let manifest = EmergencyManifest(
            caseId: `case`.id,
            caseTitle: `case`.title,
            generatedAt: Date(),
            evidenceCount: `case`.evidenceCount,
            evidenceHashes: (`case`.evidenceItems ?? []).map { ev in
                EmergencyEvidenceRef(
                    id: ev.id,
                    type: ev.type,
                    sha256: ev.sha256Hash,
                    timestamp: ev.createdAt,
                    hasLocation: ev.latitude != nil
                )
            },
            recipientHint: recipientHint,
            chainHeadHash: (`case`.evidenceItems ?? []).last?.sha256Hash,
            issuerDevice: UIDevice.current.identifierForVendor?.uuidString,
            issuerNote: "緊急時用最小パッケージ。原本データは含まれません。受領後 24 時間以内に AnalysisPackage の取り寄せを推奨。"
        )

        let manifestData = try JSONEncoder.iso8601().encode(manifest)
        let key = Self.deriveKey(from: passphrase, salt: "legalshield-emergency")
        let sealed = try AES.GCM.seal(manifestData, using: key)

        AuditLogService.shared.record(
            actor: .user,
            action: .exportEmergency,
            detail: "緊急パッケージ生成 case=\(`case`.id)",
            resourceType: "Case",
            resourceId: `case`.id.uuidString
        )

        return EmergencyPackage(
            id: UUID(),
            caseId: `case`.id,
            createdAt: Date(),
            ciphertext: sealed.combined ?? Data(),
            recipientHint: recipientHint,
            sizeBytes: sealed.combined?.count ?? 0
        )
    }

    // MARK: - Analysis Package

    /// 分析・後日参照用フルパッケージ（時間がかかる）
    ///
    /// 被害者本人 → 弁護士 / 外部監査人 / 研究者（匿名化版） への送付想定。
    func buildAnalysisPackage(
        case: LegalCase,
        recipientPublicKeyPEM: String?,
        anonymizationLevel: AnonymizationLevel = .none,
        progress: ((Double) -> Void)? = nil
    ) async throws -> AnalysisPackage {

        let evidenceList = `case`.evidenceItems ?? []
        var entries: [AnalysisEvidenceEntry] = []

        for (i, ev) in evidenceList.enumerated() {
            // 原本ファイルパス（filePath）から実データを読み込む想定
            let entry = AnalysisEvidenceEntry(
                id: ev.id,
                type: ev.type,
                fileName: ev.fileName,
                filePath: ev.filePath,
                fileSize: ev.fileSize,
                sha256: ev.sha256Hash,
                previousHash: ev.previousHash,
                chainIndex: ev.chainIndex,
                createdAt: ev.createdAt,
                latitude: anonymizationLevel.maskGPS ? nil : ev.latitude,
                longitude: anonymizationLevel.maskGPS ? nil : ev.longitude,
                deviceID: anonymizationLevel.maskDeviceId ? nil : ev.deviceID
            )
            entries.append(entry)
            progress?(Double(i + 1) / Double(max(evidenceList.count, 1)))
        }

        // 監査ログを同梱（リソース ID 一致するもの）
        let relatedAudits = AuditLogService.shared
            .fetchByResource(type: "Case", id: `case`.id.uuidString)
            .map { AuditLogSnapshot(from: $0) }

        let manifest = AnalysisManifest(
            packageId: UUID(),
            caseId: `case`.id,
            caseTitle: `case`.title,
            generatedAt: Date(),
            anonymizationLevel: anonymizationLevel.rawValue,
            evidenceEntries: entries,
            auditTrail: relatedAudits,
            chainHeadHash: evidenceList.last?.sha256Hash
        )

        let manifestData = try JSONEncoder.iso8601().encode(manifest)

        // RSA-4096 公開鍵がある場合はそちらで AES 鍵を暗号化（ハイブリッド）
        let aesKey = SymmetricKey(size: .bits256)
        let sealed = try AES.GCM.seal(manifestData, using: aesKey)
        let aesKeyData = aesKey.withUnsafeBytes { Data($0) }

        // 公開鍵が無ければ、AES 鍵は端末上の Keychain 同等鍵で再暗号化（自分で読む用）
        let wrappedKey: Data
        if let pem = recipientPublicKeyPEM {
            wrappedKey = try Self.wrapKeyWithRSA(aesKey: aesKeyData, publicKeyPEM: pem)
        } else {
            wrappedKey = aesKeyData  // 注意：実運用では Keychain 由来の Master Key で再暗号化
        }

        AuditLogService.shared.record(
            actor: .user,
            action: .exportAnalysis,
            detail: "分析パッケージ生成 case=\(`case`.id) anonym=\(anonymizationLevel.rawValue)",
            resourceType: "Case",
            resourceId: `case`.id.uuidString
        )

        return AnalysisPackage(
            id: manifest.packageId,
            caseId: `case`.id,
            createdAt: Date(),
            ciphertext: sealed.combined ?? Data(),
            wrappedKey: wrappedKey,
            anonymizationLevel: anonymizationLevel,
            sizeBytes: sealed.combined?.count ?? 0
        )
    }

    // MARK: - Helpers

    private static func deriveKey(from passphrase: String, salt: String) -> SymmetricKey {
        var hasher = SHA256()
        hasher.update(data: Data(salt.utf8))
        hasher.update(data: Data(passphrase.utf8))
        let digest = hasher.finalize()
        return SymmetricKey(data: Data(digest))
    }

    /// RSA 公開鍵で AES 鍵をラップ（実装は SecKey API で要追加）
    private static func wrapKeyWithRSA(aesKey: Data, publicKeyPEM: String) throws -> Data {
        // TODO: SecKey + SecKeyCreateEncryptedData で本実装
        //       現状は仮で base64 する（本番厳禁）
        return aesKey.base64EncodedData()
    }
}

// MARK: - Models

enum AnonymizationLevel: String, Codable {
    case none           // 本人 → 弁護士
    case partial        // 弁護士 → 共同研究者（GPS マスクなど）
    case full           // 研究データ集計用（個人特定不可レベル）

    var maskGPS: Bool { self != .none }
    var maskDeviceId: Bool { self == .full }
}

struct EmergencyPackage {
    let id: UUID
    let caseId: UUID
    let createdAt: Date
    let ciphertext: Data
    let recipientHint: String?
    let sizeBytes: Int
}

struct AnalysisPackage {
    let id: UUID
    let caseId: UUID
    let createdAt: Date
    let ciphertext: Data
    let wrappedKey: Data
    let anonymizationLevel: AnonymizationLevel
    let sizeBytes: Int
}

// MARK: - Manifest 内部構造

struct EmergencyManifest: Codable {
    let caseId: UUID
    let caseTitle: String
    let generatedAt: Date
    let evidenceCount: Int
    let evidenceHashes: [EmergencyEvidenceRef]
    let recipientHint: String?
    let chainHeadHash: String?
    let issuerDevice: String?
    let issuerNote: String
}

struct EmergencyEvidenceRef: Codable {
    let id: UUID
    let type: String
    let sha256: String
    let timestamp: Date
    let hasLocation: Bool
}

struct AnalysisManifest: Codable {
    let packageId: UUID
    let caseId: UUID
    let caseTitle: String
    let generatedAt: Date
    let anonymizationLevel: String
    let evidenceEntries: [AnalysisEvidenceEntry]
    let auditTrail: [AuditLogSnapshot]
    let chainHeadHash: String?
}

struct AnalysisEvidenceEntry: Codable {
    let id: UUID
    let type: String
    let fileName: String
    let filePath: String?
    let fileSize: Int
    let sha256: String
    let previousHash: String?
    let chainIndex: Int
    let createdAt: Date
    let latitude: Double?
    let longitude: Double?
    let deviceID: String?
}

struct AuditLogSnapshot: Codable {
    let timestamp: Date
    let actorType: String
    let actionType: String
    let actionDetail: String
    let chainIndex: Int
    let sha256Hash: String

    init(from log: AuditLog) {
        self.timestamp = log.timestamp
        self.actorType = log.actorType
        self.actionType = log.actionType
        self.actionDetail = log.actionDetail
        self.chainIndex = log.chainIndex
        self.sha256Hash = log.sha256Hash
    }
}

// MARK: - JSON Encoder helper

extension JSONEncoder {
    static func iso8601() -> JSONEncoder {
        let enc = JSONEncoder()
        enc.dateEncodingStrategy = .iso8601
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        return enc
    }
}
