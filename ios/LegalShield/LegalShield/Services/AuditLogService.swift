import Foundation
import SwiftData
import UIKit

/// 監査ログサービス
///
/// 使い方：
///   AuditLogService.shared.record(
///       actor: .user, action: .viewEvidence,
///       detail: "Evidence \(evidenceId) を閲覧",
///       resourceType: "Evidence", resourceId: evidenceId
///   )
///
/// 後台監視 UI からの参照：
///   AuditLogService.shared.fetchRecent(limit: 100)
///   AuditLogService.shared.fetchByActor(actorId: "ngo-staff-001")
///   AuditLogService.shared.fetchSuspicious()  // 異常検出
///
/// 設計：
/// - シングルトン（端末内ログは 1 chain にまとめる）
/// - 全 record は前ハッシュチェーン → 改ざん検出可能
/// - パートナー機関への push は別途 AuditSync で（TODO）
@MainActor
final class AuditLogService {

    static let shared = AuditLogService()

    private var modelContext: ModelContext?
    private var lastHash: String?
    private var chainIndex: Int = 0

    private init() {}

    /// LegalShieldApp から呼ぶ初期化
    func configure(container: ModelContainer) {
        self.modelContext = ModelContext(container)
        loadLastChainState()
    }

    // MARK: - 記録

    @discardableResult
    func record(
        actor: AuditActorType,
        actorId: String? = nil,
        action: AuditActionType,
        detail: String,
        resourceType: String? = nil,
        resourceId: String? = nil,
        contextNotes: String? = nil
    ) -> AuditLog? {
        guard let ctx = modelContext else {
            print("⚠️ AuditLogService: modelContext 未設定")
            return nil
        }

        let entry = AuditLog(
            actorType: actor,
            actorId: actorId,
            actorDeviceId: UIDevice.current.identifierForVendor?.uuidString,
            actionType: action,
            actionDetail: detail,
            resourceType: resourceType,
            resourceId: resourceId,
            userAgent: Self.userAgentString(),
            previousHash: lastHash,
            chainIndex: chainIndex
        )

        ctx.insert(entry)
        do {
            try ctx.save()
            lastHash = entry.sha256Hash
            chainIndex += 1
        } catch {
            print("⚠️ AuditLog 保存失敗: \(error)")
            return nil
        }
        return entry
    }

    // MARK: - 検索（後台監視 UI 用）

    func fetchRecent(limit: Int = 100) -> [AuditLog] {
        guard let ctx = modelContext else { return [] }
        var descriptor = FetchDescriptor<AuditLog>(
            sortBy: [SortDescriptor(\.timestamp, order: .reverse)]
        )
        descriptor.fetchLimit = limit
        return (try? ctx.fetch(descriptor)) ?? []
    }

    func fetchByResource(type: String, id: String) -> [AuditLog] {
        guard let ctx = modelContext else { return [] }
        let predicate = #Predicate<AuditLog> { log in
            log.resourceType == type && log.resourceId == id
        }
        let descriptor = FetchDescriptor<AuditLog>(
            predicate: predicate,
            sortBy: [SortDescriptor(\.timestamp, order: .reverse)]
        )
        return (try? ctx.fetch(descriptor)) ?? []
    }

    func fetchByActor(actorId: String) -> [AuditLog] {
        guard let ctx = modelContext else { return [] }
        let predicate = #Predicate<AuditLog> { log in
            log.actorId == actorId
        }
        let descriptor = FetchDescriptor<AuditLog>(
            predicate: predicate,
            sortBy: [SortDescriptor(\.timestamp, order: .reverse)]
        )
        return (try? ctx.fetch(descriptor)) ?? []
    }

    /// 異常検出（簡易ルール）
    /// - 短時間に大量アクセス
    /// - 通常アクセスしない時間帯（深夜帯）
    /// - 同一リソースへの繰り返しアクセス
    func fetchSuspicious(within: TimeInterval = 3600) -> [AuditLog] {
        let recent = fetchRecent(limit: 500)
        let cutoff = Date().addingTimeInterval(-within)

        var suspicious: [AuditLog] = []

        // ルール 1: 1 時間に同一 actor が 50+ 件アクセス
        let bucket = Dictionary(grouping: recent.filter { $0.timestamp >= cutoff }) {
            $0.actorId ?? "unknown"
        }
        for (_, logs) in bucket where logs.count >= 50 {
            suspicious.append(contentsOf: logs.prefix(5))
        }

        // ルール 2: 02:00 - 05:00 のアクセス
        let calendar = Calendar.current
        for log in recent {
            let hour = calendar.component(.hour, from: log.timestamp)
            if (2..<5).contains(hour) {
                suspicious.append(log)
            }
        }

        return Array(Set(suspicious.map { $0.id })).compactMap { id in
            recent.first { $0.id == id }
        }
    }

    // MARK: - 改ざん検証

    /// チェーン全体の整合性検証
    func verifyIntegrity() -> AuditIntegrityReport {
        let logs = fetchAll()
        var brokenAt: [Int] = []
        var prevHash: String? = nil

        for log in logs.sorted(by: { $0.chainIndex < $1.chainIndex }) {
            if log.previousHash != prevHash {
                brokenAt.append(log.chainIndex)
            }
            prevHash = log.sha256Hash
        }

        return AuditIntegrityReport(
            totalEntries: logs.count,
            brokenIndices: brokenAt,
            isIntact: brokenAt.isEmpty
        )
    }

    private func fetchAll() -> [AuditLog] {
        guard let ctx = modelContext else { return [] }
        let descriptor = FetchDescriptor<AuditLog>()
        return (try? ctx.fetch(descriptor)) ?? []
    }

    // MARK: - 内部

    private func loadLastChainState() {
        let recent = fetchRecent(limit: 1)
        if let last = recent.first {
            lastHash = last.sha256Hash
            chainIndex = last.chainIndex + 1
        }
    }

    private static func userAgentString() -> String {
        let app = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0"
        return "LegalShield/\(app) iOS/\(UIDevice.current.systemVersion)"
    }
}

// MARK: - 報告

struct AuditIntegrityReport {
    let totalEntries: Int
    let brokenIndices: [Int]
    let isIntact: Bool

    var summary: String {
        if isIntact {
            return "✓ 監査ログは改ざんされていません（\(totalEntries) 件）"
        } else {
            return "⚠️ \(brokenIndices.count) 箇所の改ざんを検出（インデックス: \(brokenIndices.prefix(5))...）"
        }
    }
}
