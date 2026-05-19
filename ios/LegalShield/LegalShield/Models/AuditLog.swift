import Foundation
import SwiftData

/// 監査ログ — Audit Trail
///
/// 設計原則：
/// - すべての「証拠データへのアクセス」「外部送信」「設定変更」を記録
/// - 改ざん防止：前後ハッシュチェーン（Evidence と同じ仕組み）
/// - 端末ローカル保存。研究用途で集計時のみ匿名化エクスポート
/// - 本人 + パートナー機関スタッフ + 監査人（外部）が閲覧可能
@Model
final class AuditLog {
    @Attribute(.unique) var id: UUID
    var timestamp: Date

    /// 操作主体（who）
    var actorType: String       // AuditActorType.rawValue
    var actorId: String?        // ユーザーID / NGOスタッフID / システム
    var actorDeviceId: String?  // 端末識別子（端末ID）

    /// 操作種類（what）
    var actionType: String      // AuditActionType.rawValue
    var actionDetail: String    // "Evidence:UUID 閲覧" など人間可読

    /// 対象リソース
    var resourceType: String?   // "Evidence" / "Case" / "Consent" / "ExportPackage"
    var resourceId: String?     // 対象オブジェクトID

    /// 文脈情報
    var ipAddress: String?
    var userAgent: String?
    var geolocation: String?    // "lat,lng" 概略のみ
    var contextNotes: String?

    /// 改ざん防止チェーン
    var previousHash: String?
    var sha256Hash: String      // この監査エントリ自体のハッシュ
    var chainIndex: Int

    /// 同期状態（パートナー機関の監査人が閲覧する場合に push される）
    var syncedAt: Date?
    var syncStatus: String      // AuditSyncStatus.rawValue

    init(
        id: UUID = UUID(),
        timestamp: Date = Date(),
        actorType: AuditActorType,
        actorId: String? = nil,
        actorDeviceId: String? = nil,
        actionType: AuditActionType,
        actionDetail: String,
        resourceType: String? = nil,
        resourceId: String? = nil,
        ipAddress: String? = nil,
        userAgent: String? = nil,
        geolocation: String? = nil,
        contextNotes: String? = nil,
        previousHash: String? = nil,
        chainIndex: Int = 0,
        syncStatus: AuditSyncStatus = .local
    ) {
        self.id = id
        self.timestamp = timestamp
        self.actorType = actorType.rawValue
        self.actorId = actorId
        self.actorDeviceId = actorDeviceId
        self.actionType = actionType.rawValue
        self.actionDetail = actionDetail
        self.resourceType = resourceType
        self.resourceId = resourceId
        self.ipAddress = ipAddress
        self.userAgent = userAgent
        self.geolocation = geolocation
        self.contextNotes = contextNotes
        self.previousHash = previousHash
        self.chainIndex = chainIndex
        self.syncStatus = syncStatus.rawValue

        // ハッシュは本エントリの内容＋前ハッシュから計算
        let payload = "\(timestamp.timeIntervalSince1970)|\(actorType.rawValue)|\(actorId ?? "")|\(actionType.rawValue)|\(actionDetail)|\(resourceId ?? "")|\(previousHash ?? "")"
        self.sha256Hash = Self.computeSHA256(payload)
    }

    static func computeSHA256(_ input: String) -> String {
        guard let data = input.data(using: .utf8) else { return "" }
        return data.sha256Hex
    }
}

// MARK: - 列舉

enum AuditActorType: String, Codable {
    case user           // 当事者（被害者本人 / 保護者）
    case ngoStaff       // パートナーNGOのスタッフ
    case lawyer         // 弁護士
    case auditor        // 外部監査人
    case system         // 自動処理（バックアップ、定期チェックなど）
    case ai             // AI 分析エージェント
}

enum AuditActionType: String, Codable {
    // 閲覧系
    case viewEvidence
    case viewCase
    case viewConsent
    case viewExport

    // 作成・編集系
    case createEvidence
    case createCase
    case updateCase
    case updateConsent

    // エクスポート / 共有系
    case exportEmergency        // 緊急時用パッケージ生成
    case exportAnalysis         // 平時の分析用パッケージ生成
    case shareToPartner         // パートナー機関への共有
    case shareToAuthority       // 警察 / 児相 / DV センター

    // AI 系
    case aiAnalysisRun
    case aiPromptDispatched     // 外部 LLM への送信
    case aiResponseReceived

    // システム系
    case loginAttempt
    case loginSuccess
    case logoutEvent
    case settingsChanged
    case keyRotation            // 暗号鍵ローテーション
    case backupCreated
    case backupRestored

    // 削除系
    case deleteEvidence
    case archiveCase
}

enum AuditSyncStatus: String, Codable {
    case local              // 端末のみ
    case synced             // パートナー機関と同期済
    case syncFailed
    case anonymized         // 研究用途で匿名化済
}

// MARK: - SHA256 Helper

import CryptoKit

private extension Data {
    var sha256Hex: String {
        SHA256.hash(data: self).map { String(format: "%02x", $0) }.joined()
    }
}
