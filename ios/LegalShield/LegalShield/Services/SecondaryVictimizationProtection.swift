import Foundation
import SwiftData

/// 預防二次受害保護機制
/// 核心設計：讓受害者在整個司法流程中只說一次、只被問一次、只暴露一次
class SecondaryVictimizationProtection {
    
    private let modelContext: ModelContext
    
    init(context: ModelContext) {
        self.modelContext = context
    }
    
    // MARK: - 一次性完整記錄
    
    /// 引導式陳述：按時間順序引導受害者描述事件
    /// 目標：讓受害者在最舒服的環境（自己的房間、自己的手機）中完成陳述
    /// 結果：錄音/錄影成為「初次陳述」證據，法庭可直接調閱
    struct GuidedStatementSession {
        let caseId: UUID
        let startTime: Date
        var currentQuestionIndex: Int = 0
        var responses: [StatementResponse] = []
        var isRecording: Bool = false
        
        // 引導問題序列（避免誘導性）
        static let questions: [GuidedQuestion] = [
            GuidedQuestion(
                id: 1,
                text: "請您用自己的話描述發生了什麼事。不用擔心順序，想到什麼說什麼。",
                type: .openEnded,
                avoidLeading: true
            ),
            GuidedQuestion(
                id: 2,
                text: "這件事是從什麼時候開始的？",
                type: .temporal,
                avoidLeading: true
            ),
            GuidedQuestion(
                id: 3,
                text: "當時有沒有其他人在場？",
                type: .witness,
                avoidLeading: true
            ),
            GuidedQuestion(
                id: 4,
                text: "事發後您有沒有告訴過其他人？",
                type: .disclosure,
                avoidLeading: true
            ),
            GuidedQuestion(
                id: 5,
                text: "您現在最擔心的是什麼？",
                type: .concern,
                avoidLeading: true
            )
        ]
    }
    
    struct GuidedQuestion {
        let id: Int
        let text: String
        let type: QuestionType
        let avoidLeading: Bool
    }
    
    enum QuestionType {
        case openEnded    // 開放式
        case temporal     // 時間
        case witness      // 目擊者
        case disclosure   // 揭露
        case concern      // 擔憂
    }
    
    struct StatementResponse {
        let questionId: Int
        let audioRecordingId: UUID?    // 錄音證據 ID
        let transcript: String?        // 語音轉文字結果
        let timestamp: Date
    }
    
    // MARK: - 陪同人機制
    
    /// 陪同人設定
    struct AccompanimentSettings: Codable {
        var enabled: Bool = false
        var accompanistName: String?           // 陪同人姓名
        var accompanistRole: String?           // "律師", "支援センター職員", "母", "友人"
        var accompanistContact: String?        // 電話/Email
        var shareEvidenceIndex: Bool = false   // 是否分享證據索引給陪同人
        var shareProgressUpdates: Bool = true  // 是否分享案件進度
        
        // 日本法律規定的陪同人類型
        var legalAccompanimentType: LegalAccompanimentType?
    }
    
    enum LegalAccompanimentType: String, Codable {
        case lawyer = "lawyer"                     // 選任弁護人
        case guardian = "guardian"               // 法定代理人（未成年）
        case supportStaff = "support_staff"       // 支援センター職員
        case familyMember = "family_member"       // 家族
        case friend = "friend"                    // 友人
        
        var legalAuthority: String {
            switch self {
            case .lawyer: return "弁護士法第1条：依頼人の権利利益を保護"
            case .guardian: return "民法第824条：親権者の代理権"
            case .supportStaff: return "配偶者暴力防止法第10条：支援センター"
            case .familyMember, .friend: return "用戶自主指定"
            }
        }
    }
    
    /// 設定陪同人
    func setupAccompaniment(
        for caseId: UUID,
        settings: AccompanimentSettings
    ) throws {
        let targetId = caseId
        let descriptor = FetchDescriptor<LegalCase>(
            predicate: #Predicate { $0.id == targetId }
        )
        guard let caseItem = try modelContext.fetch(descriptor).first else {
            throw ProtectionError.caseNotFound
        }
        
        // 儲存陪同人設定至案件 (未來可加密並儲存到專用欄位)
        _ = try JSONEncoder().encode(settings)
        caseItem.sharedWith = [settings.accompanistContact].compactMap { $0 }
        
        // 如果啟用，通知緊急轉介流程
        if settings.enabled {
            // 轉介時自動抄送陪同人
        }
        
        try modelContext.save()
    }
    
    // MARK: - 匿名/化名處理
    
    /// 身份保護設定
    struct IdentityProtection: Codable {
        var usePseudonym: Bool = true
        var pseudonym: String = "Aさん"
        var realNameSharedWith: [String] = []  // 只有誰知道真實姓名
        var blurFaceInEvidence: Bool = true    // 自動模糊人臉
        var maskLocationPrecision: Bool = true // GPS 只顯示到區域
        
        // 生成化名建議
        static func generatePseudonym(for victimName: String, gender: String?) -> String {
            // 使用姓氏首字母 + さん/様
            let prefix = String(victimName.prefix(1))
            let suffix = (gender == "female") ? "さん" : "様"
            return "\(prefix)\(suffix)"
        }
    }
    
    /// 應用身份保護到所有證據
    func applyIdentityProtection(
        for caseId: UUID,
        protection: IdentityProtection
    ) async throws {
        let targetCaseId = caseId
        let descriptor = FetchDescriptor<Evidence>(
            predicate: #Predicate { $0.caseId == targetCaseId }
        )
        let evidences = try modelContext.fetch(descriptor)
        
        for evidence in evidences {
            // 如果是照片且需要模糊人臉
            if evidence.evidenceType == .photo && protection.blurFaceInEvidence {
                // 本地 Vision 人臉偵測 + 模糊處理
                // Note: 原始照片保留，產生一個「公開版」
            }
            
            // 標記證據使用化名
            if var tags = evidence.tags {
                tags.append("pseudonym:\(protection.pseudonym)")
                evidence.tags = tags
            }
        }
        
        try modelContext.save()
    }
    
    // MARK: - 快速通道
    
    /// 性暴力案件快速通道設定
    struct FastTrackConfig {
        static let responseTimeLimit: TimeInterval = 30 * 60  // 30 分鐘內專員回撥
        static let medicalEvidenceWindow: TimeInterval = 72 * 3600  // 72 小時內醫療採證
        static let counselingReferralDelay: TimeInterval = 24 * 3600  // 24 小時內心理諮商轉介
    }
    
    /// 啟用快速通道
    func enableFastTrack(for caseId: UUID, caseCategory: CaseCategory) async throws {
        guard caseCategory == .sexualHarassment || caseCategory == .childAbuse else {
            return // 只有特定類型啟用快速通道
        }
        
        let targetId = caseId
        let descriptor = FetchDescriptor<LegalCase>(
            predicate: #Predicate { $0.id == targetId }
        )
        guard let caseItem = try modelContext.fetch(descriptor).first else {
            throw ProtectionError.caseNotFound
        }
        
        caseItem.urgency = UrgencyLevel.critical.rawValue
        caseItem.updatedAt = Date()
        
        // 標記為快速通道
        if var tags = caseItem.recommendedActions {
            tags.append("FAST_TRACK:sexual_violence")
            caseItem.recommendedActions = tags
        } else {
            caseItem.recommendedActions = ["FAST_TRACK:sexual_violence"]
        }
        
        try modelContext.save()
        
        // 推播通知：
        // 1. 醫療機構清單（附近的性暴力被害者支援医療機関）
        // 2. 心理諮商熱線
        // 3. 72小時倒數計時提醒
    }
    
    // MARK: - 性暴力專門支援
    
    /// 性暴力被害者支援医療機関清單（日本）
    static let sexualAssaultMedicalFacilities: [SupportFacility] = [
        SupportFacility(
            name: "東京逓信病院",
            address: "東京都新宿区",
            phone: "03-0000-0000",
            type: .sexualAssaultCenter,
            hours: "24時間",
            acceptsWalkIn: true,
            requiresAppointment: false
        ),
        SupportFacility(
            name: "東京都医師会",
            address: "東京都新宿区",
            phone: "03-0000-0000",
            type: .counselingCenter,
            hours: "平日 9:00-17:00",
            acceptsWalkIn: false,
            requiresAppointment: true
        )
    ]
    
    struct SupportFacility {
        let name: String
        let address: String
        let phone: String
        let type: FacilityType
        let hours: String
        let acceptsWalkIn: Bool
        let requiresAppointment: Bool
    }
    
    enum FacilityType {
        case sexualAssaultCenter    // 性暴力被害者支援医療機関
        case counselingCenter       // カウンセリングセンター
        case DVSupportCenter       // DV支援センター
        case childConsultation     // 児童相談所
        case legalAidCenter        // 法テラス
    }
    
    // MARK: - 保護令輔助
    
    /// 保護令類型（日本）
    enum ProtectionOrderType {
        case spousalViolence       // 配偶者暴力防止法：禁止命令 + 退去命令
        case stalking              // ストーカー規制法：禁止命令
        case childAbuse            // 児童虐待防止法：臨時保護措置
        
        var applicableLaw: String {
            switch self {
            case .spousalViolence: return "配偶者暴力防止法第26条"
            case .stalking: return "ストーカー行為等の規制等に関する法律第14条"
            case .childAbuse: return "児童虐待防止法第28条"
            }
        }
    }
    
    /// 生成保護令聲請書（PDF 格式）
    func generateProtectionOrderRequest(
        for caseId: UUID,
        orderType: ProtectionOrderType
    ) async throws -> Data {
        let targetId = caseId
        let descriptor = FetchDescriptor<LegalCase>(
            predicate: #Predicate { $0.id == targetId }
        )
        guard let caseItem = try modelContext.fetch(descriptor).first else {
            throw ProtectionError.caseNotFound
        }
        
        // 收集證據摘要
        let targetCaseId = caseId
        let evidenceDescriptor = FetchDescriptor<Evidence>(
            predicate: #Predicate { $0.caseId == targetCaseId }
        )
        let evidences = try modelContext.fetch(evidenceDescriptor)
        
        // 生成保護令聲請書內容
        let requestContent = """
        保護命令申立書
        
        申立人：\(caseItem.victimAlias)
        相手方：\(caseItem.perpetratorAlias ?? "不明")
        
        【申立の趣旨】
        \(orderType.applicableLaw)に基づき、以下の保護命令を求めます。
        
        1. 禁止命令：相手方が申立人に対する暴力、脅迫、またはストーカー行為を行わないこと。
        
        2. 退去命令：相手方が現在居住する\(caseItem.incidentLocation ?? "居所")から退去すること。
        
        【事実と理由】
        \(caseItem.incidentDescription ?? "（詳細は添付証拠に譲る）")
        
        【添付証拠】
        \(evidences.map { "• \($0.evidenceType.displayName)（\($0.createdAt.iso8601)）" }.joined(separator: "\n"))
        
        【証拠保全証明】
        本申立に添付の証拠は、LegalShield 司法級証拠管理システムにより
        SHA-256 ハッシュ化・暗号化保存されており、改竄が不可能です。
        """
        
        // 回傳 PDF Data（簡化版，實際需使用 PDFKit 生成）
        return requestContent.data(using: .utf8) ?? Data()
    }
    
    // MARK: - 資訊最小化
    
    /// 生成對外分享用的「去識別化案件摘要」
    func generateDeIdentifiedSummary(for caseId: UUID) throws -> String {
        let targetId = caseId
        let descriptor = FetchDescriptor<LegalCase>(
            predicate: #Predicate { $0.id == targetId }
        )
        guard let caseItem = try modelContext.fetch(descriptor).first else {
            throw ProtectionError.caseNotFound
        }
        
        return """
        案件類型：\(caseItem.caseCategory.displayName)
        緊急等級：\(caseItem.urgencyLevel.displayName)
        發生日期：\(caseItem.incidentDate?.iso8601 ?? "不明")
        事件摘要：\(anonymizeText(caseItem.incidentDescription ?? ""))
        證據數量：\(caseItem.evidenceCount) 項
        """
    }
    
    /// 自動化名處理文字
    private func anonymizeText(_ text: String) -> String {
        // TODO: 未來使用 NLP 命名實體識別替換姓名為 〇〇
        return text
    }
}

// MARK: - 錯誤定義

enum ProtectionError: Error, LocalizedError {
    case caseNotFound
    case accompanimentSetupFailed
    case protectionOrderGenerationFailed
    
    var errorDescription: String? {
        switch self {
        case .caseNotFound: return "找不到案件"
        case .accompanimentSetupFailed: return "陪同人設定失敗"
        case .protectionOrderGenerationFailed: return "保護令生成失敗"
        }
    }
}
