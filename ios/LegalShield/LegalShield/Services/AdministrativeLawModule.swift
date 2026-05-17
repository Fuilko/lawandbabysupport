import Foundation
import SwiftData
import UserNotifications

/// 行政法/訴訟法流程管理模組
///
/// 日本行政救濟體系：
/// 1. 行政機關對話 (抗議、陳情)
/// 2. 審查請求 (審査請求) — 對原處分機關的上級機關
/// 3. 行政訴訟 (行政事件訴訟) — 對法院
/// 4. 國家賠償 (国家賠償) — 損害賠償
///
/// 核心功能：
/// - 期限提醒 (不變期間、消滅時效)
/// - 流程導航 (下一步該做什麼)
/// - 文書範本生成 (審査請求書、訴訟起訴狀)
/// - 裁判員制度對應 (訴訟事件)
class AdministrativeLawModule: ObservableObject {
    
    // MARK: - Published
    
    @Published var activeProcedures: [AdministrativeProcedure] = []
    @Published var upcomingDeadlines: [DeadlineAlert] = []
    
    // MARK: - 依賴
    
    private let modelContext: ModelContext?
    private let notificationCenter = UNUserNotificationCenter.current()
    
    // MARK: - 初始化
    
    init(context: ModelContext? = nil) {
        self.modelContext = context
        requestNotificationPermission()
        loadActiveProcedures()
    }
    
    // MARK: - 流程啟動
    
    /// 啟動一個新的行政救濟流程
    func startProcedure(
        caseId: UUID,
        type: AdministrativeProcedureType,
        originalDecision: String,  // 原處分內容
        decisionDate: Date,
        authorityName: String,       // 原處分機關名稱
        claimantName: String
    ) -> AdministrativeProcedure {
        
        let procedure = AdministrativeProcedure(
            id: UUID(),
            caseId: caseId,
            type: type,
            originalDecision: originalDecision,
            decisionDate: decisionDate,
            authorityName: authorityName,
            claimantName: claimantName,
            status: .preparing,
            createdAt: Date()
        )
        
        // 計算關鍵期限
        procedure.deadlines = calculateDeadlines(for: type, from: decisionDate)
        
        // 排程通知
        scheduleDeadlineNotifications(for: procedure)
        
        activeProcedures.append(procedure)
        saveProcedure(procedure)
        
        return procedure
    }
    
    // MARK: - 期限計算
    
    /// 根據程序類型計算所有關鍵期限
    private func calculateDeadlines(
        for type: AdministrativeProcedureType,
        from decisionDate: Date
    ) -> [ProcedureDeadline] {
        let calendar = Calendar.current
        var deadlines: [ProcedureDeadline] = []
        
        switch type {
        case .reviewRequest:
            // 審査請求：原則 60 日 (行政手続法第24条)
            if let mainDeadline = calendar.date(byAdding: .day, value: 60, to: decisionDate) {
                deadlines.append(ProcedureDeadline(
                    type: .submissionDeadline,
                    description: "審査請求提出期限",
                    dueDate: mainDeadline,
                    isExtendable: false,
                    legalBasis: "行政手続法第24条"
                ))
            }
            // 提醒：截止前 7 天
            if let reminderDate = calendar.date(byAdding: .day, value: 53, to: decisionDate) {
                deadlines.append(ProcedureDeadline(
                    type: .reminder,
                    description: "審査請求提出期限即將屆滿 (7日前提醒)",
                    dueDate: reminderDate,
                    isExtendable: false
                ))
            }
            
        case .administrativeLitigation:
            // 撤銷訴訟：原則 6 個月 (行政事件訴訟法第38条)
            if let mainDeadline = calendar.date(byAdding: .month, value: 6, to: decisionDate) {
                deadlines.append(ProcedureDeadline(
                    type: .submissionDeadline,
                    description: "撤銷訴訟提起期限",
                    dueDate: mainDeadline,
                    isExtendable: false,
                    legalBasis: "行政事件訴訟法第38条"
                ))
            }
            // 提醒：截止前 1 個月
            if let reminderDate = calendar.date(byAdding: .month, value: 5, to: decisionDate) {
                deadlines.append(ProcedureDeadline(
                    type: .reminder,
                    description: "訴訟提起期限即將屆滿 (1個月前提醒)",
                    dueDate: reminderDate,
                    isExtendable: false
                ))
            }
            
        case .nationalCompensation:
            // 國家賠償請求：3 年 (国家賠償法第14条)
            if let mainDeadline = calendar.date(byAdding: .year, value: 3, to: decisionDate) {
                deadlines.append(ProcedureDeadline(
                    type: .limitationPeriod,
                    description: "国家賠償請求権消滅時效",
                    dueDate: mainDeadline,
                    isExtendable: true,  // 時效可中斷
                    legalBasis: "国家賠償法第14条"
                ))
            }
            
        case .objection:
            // 異議申立：通常無嚴格期限，但建議 14 日內
            if let suggestedDate = calendar.date(byAdding: .day, value: 14, to: decisionDate) {
                deadlines.append(ProcedureDeadline(
                    type: .suggestedDeadline,
                    description: "異議申立建議期限 (儘早為宜)",
                    dueDate: suggestedDate,
                    isExtendable: true
                ))
            }
        }
        
        return deadlines
    }
    
    // MARK: - 通知排程
    
    private func scheduleDeadlineNotifications(for procedure: AdministrativeProcedure) {
        for deadline in procedure.deadlines where deadline.type != .completed {
            let content = UNMutableNotificationContent()
            content.title = "LegalShield 行政救濟提醒"
            content.body = deadline.description
            content.sound = .default
            content.categoryIdentifier = "administrative_deadline"
            
            let components = Calendar.current.dateComponents([.year, .month, .day, .hour], from: deadline.dueDate)
            let trigger = UNCalendarNotificationTrigger(dateMatching: components, repeats: false)
            
            let request = UNNotificationRequest(
                identifier: "\(procedure.id.uuidString)_\(deadline.type.rawValue)",
                content: content,
                trigger: trigger
            )
            
            notificationCenter.add(request)
        }
    }
    
    // MARK: - 流程導航
    
    /// 取得「下一步行動」建議
    func getNextSteps(for procedureId: UUID) -> [NextStep] {
        guard let procedure = activeProcedures.first(where: { $0.id == procedureId }) else {
            return []
        }
        
        var steps: [NextStep] = []
        
        switch procedure.status {
        case .preparing:
            steps.append(NextStep(
                priority: 1,
                action: "準備審査請求書/訴訟起訴狀",
                description: "收集原處分相關文件、證據",
                suggestedDocument: procedure.type.documentTemplate,
                estimatedTime: "2-3 小時"
            ))
            steps.append(NextStep(
                priority: 2,
                action: "確認提出機關/管轄法院",
                description: procedure.type.filingDestination,
                estimatedTime: "30 分鐘"
            ))
            
        case .submitted:
            steps.append(NextStep(
                priority: 1,
                action: "等待審理/答辯",
                description: "通常 \(procedure.type.expectedResponseDays) 日內有回應",
                estimatedTime: "被動等待"
            ))
            steps.append(NextStep(
                priority: 2,
                action: "準備補充證據",
                description: "在期限內可隨時補提",
                estimatedTime: "持續"
            ))
            
        case .underReview:
            steps.append(NextStep(
                priority: 1,
                action: "準備口頭辯論/聴聞",
                description: "整理主張與證據要點",
                estimatedTime: "1-2 小時"
            ))
            
        case .decided:
            if procedure.result == .dismissed {
                steps.append(NextStep(
                    priority: 1,
                    action: "考慮進一步救濟",
                    description: "可提起 \(procedure.type.nextLevelProcedure?.rawValue ?? "訴訟")",
                    estimatedTime: "諮詢律師"
                ))
            }
            
        default:
            break
        }
        
        return steps.sorted { $0.priority < $1.priority }
    }
    
    // MARK: - 裁判員制度對應
    
    /// 檢查是否適用裁判員制度 (2009年5月以後)
    func isSaibaninApplicable(caseType: String) -> Bool {
        // 裁判員制度適用案件：重大刑事事件
        let applicableTypes = ["殺人", "強盗", "放火", "強制わいせつ", "薬物取締法違反"]
        return applicableTypes.contains { caseType.contains($0) }
    }
    
    /// 生成裁判員對應的證據呈現建議
    func generateSaibaninEvidenceGuide(evidenceItems: [Evidence]) -> String {
        var guide = "【裁判員制度対応 証拠呈現ガイド】\n\n"
        guide += "裁判員は法律専門家ではないため、以下の点に留意：\n\n"
        
        for (index, evidence) in evidenceItems.enumerated() {
            guide += "\(index + 1). \(evidence.evidenceType.displayName)\n"
            guide += "   提示方法：\(evidence.evidenceType.saibaninPresentationMethod)\n"
            guide += "   説明ポイント：\(evidence.evidenceType.saibaninExplanation)\n\n"
        }
        
        guide += "注意：証拠の連鎖 (chain of custody) を口頭で簡潔に説明すること。"
        return guide
    }
    
    // MARK: - 文書生成
    
    /// 生成行政救濟文書草稿
    func generateDocumentDraft(
        for procedure: AdministrativeProcedure,
        arguments: [String],
        evidenceReferences: [String]
    ) -> String {
        let template = procedure.type.documentTemplate
        
        // 注：原本透過 DocumentTemplate extension 的 header/footer 已被移除
        //     此處直接以 displayName 作為 header，footer 用通用簽名
        var draft = "\(template.displayName)\n"
        draft += "\n\n【原処分の内容】\n\(procedure.originalDecision)\n"
        draft += "【原処分機関】\(procedure.authorityName)\n"
        draft += "【処分日】\(procedure.decisionDate.jpFormatted)\n\n"
        draft += "【不服の理由】\n"
        for (index, arg) in arguments.enumerated() {
            draft += "\(index + 1). \(arg)\n"
        }
        draft += "\n【添付証拠】\n"
        for ref in evidenceReferences {
            draft += "・\(ref)\n"
        }
        draft += "\n以上\n\n\(Date().jpFormatted)\n署名: ____________"
        
        return draft
    }
    
    // MARK: - 補助款追蹤 (研究/法律援助)
    
    /// 記錄一筆補助款使用
    func recordGrantUsage(
        grantName: String,
        amount: Double,
        purpose: String,
        relatedCaseId: UUID?
    ) -> GrantRecord {
        let record = GrantRecord(
            id: UUID(),
            grantName: grantName,
            amount: amount,
            currency: "JPY",
            purpose: purpose,
            relatedCaseId: relatedCaseId,
            usedAt: Date(),
            status: .used
        )
        saveGrantRecord(record)
        return record
    }
    
    /// 生成補助款執行報告 (供補助機關查核)
    func generateGrantReport(grantName: String) -> String {
        let records = loadGrantRecords(for: grantName)
        let total = records.reduce(0) { $0 + $1.amount }
        
        var report = "【補助金執行報告書】\n"
        report += "補助金名稱：\(grantName)\n"
        report += "報告期間：\(records.first?.usedAt.jpFormatted ?? "") 〜 \(Date().jpFormatted)\n"
        report += "執行總額：¥\(Int(total))\n\n"
        report += "【用途明細】\n"
        for record in records {
            report += "・\(record.purpose)：¥\(Int(record.amount))\n"
        }
        return report
    }
    
    // MARK: - 私有輔助
    
    private func requestNotificationPermission() {
        notificationCenter.requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            print("[AdminLaw] Notification permission: \(granted)")
        }
    }
    
    private func loadActiveProcedures() {
        // 從 SwiftData 載入
        guard let context = modelContext else { return }
        let descriptor = FetchDescriptor<AdministrativeProcedure>(
            sortBy: [SortDescriptor(\.createdAt, order: .reverse)]
        )
        do {
            activeProcedures = try context.fetch(descriptor)
            updateUpcomingDeadlines()
        } catch {
            print("[AdminLaw] Failed to load procedures: \(error)")
        }
    }
    
    private func updateUpcomingDeadlines() {
        let now = Date()
        upcomingDeadlines = activeProcedures.flatMap { procedure in
            procedure.deadlines
                .filter { $0.dueDate > now && $0.type != .completed }
                .map { DeadlineAlert(
                    procedureId: procedure.id,
                    procedureType: procedure.type,
                    deadline: $0,
                    daysRemaining: Calendar.current.dateComponents([.day], from: now, to: $0.dueDate).day ?? 0
                )}
        }.sorted { $0.daysRemaining < $1.daysRemaining }
    }
    
    private func saveProcedure(_ procedure: AdministrativeProcedure) {
        guard let context = modelContext else { return }
        context.insert(procedure)
        try? context.save()
    }
    
    private func saveGrantRecord(_ record: GrantRecord) {
        guard let context = modelContext else { return }
        context.insert(record)
        try? context.save()
    }
    
    private func loadGrantRecords(for grantName: String? = nil) -> [GrantRecord] {
        guard let context = modelContext else { return [] }
        var descriptor = FetchDescriptor<GrantRecord>(
            sortBy: [SortDescriptor(\.usedAt, order: .reverse)]
        )
        if let name = grantName {
            descriptor.predicate = #Predicate { $0.grantName == name }
        }
        return (try? context.fetch(descriptor)) ?? []
    }
}

// MARK: - 資料結構

enum AdministrativeProcedureType: String, Codable {
    case reviewRequest = "審査請求"
    case administrativeLitigation = "行政訴訟"
    case nationalCompensation = "国家賠償"
    case objection = "異議申立"
    
    var documentTemplate: DocumentTemplate {
        switch self {
        case .reviewRequest: return .reviewRequest
        case .administrativeLitigation: return .administrativeComplaint
        case .nationalCompensation: return .compensationClaim
        case .objection: return .objectionLetter
        }
    }
    
    var filingDestination: String {
        switch self {
        case .reviewRequest: return "原処分機関の上級機関 (通常は都道府県知事または国の大臣)"
        case .administrativeLitigation: return "被告所在地の地方裁判所"
        case .nationalCompensation: return "被告所在地の地方裁判所"
        case .objection: return "原処分機関自身"
        }
    }
    
    var expectedResponseDays: Int {
        switch self {
        case .reviewRequest: return 90
        case .administrativeLitigation: return 180
        case .nationalCompensation: return 60
        case .objection: return 30
        }
    }
    
    var nextLevelProcedure: AdministrativeProcedureType? {
        switch self {
        case .reviewRequest: return .administrativeLitigation
        case .objection: return .reviewRequest
        default: return nil
        }
    }
}

enum ProcedureStatus: String, Codable {
    case preparing = "準備中"
    case submitted = "提出済"
    case underReview = "審理中"
    case decided = "決定済"
    case appealed = "不服申立中"
}

enum ProcedureDeadlineType: String, Codable {
    case submissionDeadline = "提出期限"
    case reminder = "提醒"
    case limitationPeriod = "消滅時效"
    case suggestedDeadline = "建議期限"
    case completed = "已完成"
}

enum ProcedureResult: String, Codable {
    case granted = "認容"
    case dismissed = "棄却"
    case partiallyGranted = "一部認容"
    case pending = "未定"
}

@Model
class AdministrativeProcedure {
    @Attribute(.unique) var id: UUID
    var caseId: UUID
    var type: AdministrativeProcedureType
    var originalDecision: String
    var decisionDate: Date
    var authorityName: String
    var claimantName: String
    var status: ProcedureStatus
    var result: ProcedureResult?
    var deadlines: [ProcedureDeadline]
    var notes: String?
    var createdAt: Date
    var updatedAt: Date
    
    init(id: UUID, caseId: UUID, type: AdministrativeProcedureType,
         originalDecision: String, decisionDate: Date, authorityName: String,
         claimantName: String, status: ProcedureStatus, deadlines: [ProcedureDeadline] = [],
         notes: String? = nil, createdAt: Date = Date(), updatedAt: Date = Date()) {
        self.id = id
        self.caseId = caseId
        self.type = type
        self.originalDecision = originalDecision
        self.decisionDate = decisionDate
        self.authorityName = authorityName
        self.claimantName = claimantName
        self.status = status
        self.deadlines = deadlines
        self.notes = notes
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

struct ProcedureDeadline: Codable {
    var type: ProcedureDeadlineType
    var description: String
    var dueDate: Date
    var isExtendable: Bool
    var legalBasis: String?
    var completedAt: Date?
}

struct NextStep: Identifiable {
    let id = UUID()
    let priority: Int
    let action: String
    let description: String
    var suggestedDocument: DocumentTemplate?
    let estimatedTime: String
}

struct DeadlineAlert: Identifiable {
    let id = UUID()
    let procedureId: UUID
    let procedureType: AdministrativeProcedureType
    let deadline: ProcedureDeadline
    let daysRemaining: Int
    
    var urgencyColor: String {
        switch daysRemaining {
        case ...3: return "red"
        case 4...7: return "orange"
        case 8...14: return "yellow"
        default: return "blue"
        }
    }
}

@Model
class GrantRecord {
    @Attribute(.unique) var id: UUID
    var grantName: String
    var amount: Double
    var currency: String
    var purpose: String
    var relatedCaseId: UUID?
    var usedAt: Date
    var status: GrantStatus
    var receiptData: Data?  // 收據照片
    
    enum GrantStatus: String, Codable {
        case planned = "計画中"
        case used = "執行済"
        case reported = "報告済"
    }
    
    init(id: UUID, grantName: String, amount: Double, currency: String,
         purpose: String, relatedCaseId: UUID? = nil, usedAt: Date,
         status: GrantStatus, receiptData: Data? = nil) {
        self.id = id
        self.grantName = grantName
        self.amount = amount
        self.currency = currency
        self.purpose = purpose
        self.relatedCaseId = relatedCaseId
        self.usedAt = usedAt
        self.status = status
        self.receiptData = receiptData
    }
}

// MARK: - Extensions

extension Date {
    var jpFormatted: String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy年MM月dd日"
        formatter.locale = Locale(identifier: "ja_JP")
        return formatter.string(from: self)
    }
}

// Note: DocumentTemplate 的 .reviewRequest / .administrativeComplaint / .compensationClaim / .objectionLetter
// 已直接定義為 LLMService.swift 內的 enum case。
// 原本此處的 extension 嘗試以 static let 重新定義同名屬性導致 redeclaration error，已移除。
// 文書範本的 header/footer 詳細內容請改在 LLMService.systemPrompt 或未來新增的 templateBody 中維護。

extension EvidenceType {
    var saibaninPresentationMethod: String {
        switch self {
        case .photo: return "大画面投影。撮影日時・場所を明示。"
        case .audio: return "音声再生。内容を書記官に文字起こしさせる。"
        case .video: return "動画再生。重要場面のタイムスタンプを事前に整理。"
        case .document: return "原本提示。複製は配付。"
        case .sensorData: return "グラフ化して視覚的に提示。専門家証人の説明を併用。"
        default: return "標準的な提示方法"
        }
    }
    
    var saibaninExplanation: String {
        switch self {
        case .photo: return "「これは何を写している写真ですか」から始める。"
        case .audio: return "「誰の声が入っていますか」→「何を話していますか」の順。"
        case .sensorData: return "「この数字が高い/低いことは何を意味しますか」。"
        default: return "簡潔に、専門用語を避けて説明。"
        }
    }
}
