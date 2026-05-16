import Foundation
import SwiftData
import Combine

/// 案件 ViewModel — 統一管理案件狀態與 UI 互動
@MainActor
class CaseViewModel: ObservableObject {
    
    // MARK: - Published
    
    @Published var currentCase: LegalCase?
    @Published var cases: [LegalCase] = []
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    
    // MARK: - 依賴
    
    private let modelContext: ModelContext
    private let llmService = LLMService()
    private var cancellables = Set<AnyCancellable>()
    
    // MARK: - 初始化
    
    init(container: ModelContainer? = nil) {
        // 嘗試取得共享的 ModelContainer，若無則建立新的
        if let container = container {
            self.modelContext = ModelContext(container)
        } else {
            // 這裡會在 preview 或測試時使用
            let schema = Schema([LegalCase.self, Evidence.self])
            let config = ModelConfiguration(isStoredInMemoryOnly: true)
            let container = try! ModelContainer(for: schema, configurations: [config])
            self.modelContext = ModelContext(container)
        }
        
        loadCases()
    }
    
    // MARK: - 案件 CRUD
    
    func createCase(
        title: String,
        category: CaseCategory,
        victimAlias: String = "匿名",
        victimAge: Int? = nil,
        institution: String? = nil,
        description: String? = nil
    ) -> LegalCase {
        let newCase = LegalCase(
            title: title,
            category: category,
            victimAlias: victimAlias,
            victimAge: victimAge,
            institutionName: institution,
            incidentDescription: description
        )
        
        modelContext.insert(newCase)
        saveContext()
        
        currentCase = newCase
        loadCases()
        
        return newCase
    }
    
    func selectCase(_ caseItem: LegalCase) {
        currentCase = caseItem
    }
    
    func loadCases() {
        let descriptor = FetchDescriptor<LegalCase>(sortBy: [SortDescriptor(\.createdAt, order: .reverse)])
        do {
            cases = try modelContext.fetch(descriptor)
        } catch {
            errorMessage = "載入案件失敗: \(error.localizedDescription)"
        }
    }
    
    func archiveCase(_ caseItem: LegalCase) {
        caseItem.status = CaseStatus.archived.rawValue
        saveContext()
        loadCases()
    }
    
    func deleteCase(_ caseItem: LegalCase) {
        modelContext.delete(caseItem)
        saveContext()
        if currentCase?.id == caseItem.id {
            currentCase = nil
        }
        loadCases()
    }
    
    // MARK: - AI 分析
    
    func runAIAnalysis() async throws -> AnalysisReport {
        guard let caseItem = currentCase else {
            throw CaseError.noActiveCase
        }
        
        isLoading = true
        defer { isLoading = false }
        
        let evidenceItems = caseItem.evidenceItems ?? []
        let anomalies = caseItem.anomalyLogs ?? []
        
        let report = try await llmService.analyzeEvidence(
            caseSummary: caseItem.incidentDescription ?? caseItem.title,
            evidenceList: evidenceItems,
            sensorAnomalies: anomalies
        )
        
        // 更新案件 AI 分析結果
        caseItem.updateAIAnalysis(
            summary: report.rawResponse.prefix(500).description,
            probability: report.winProbability,
            actions: report.actionItems
        )
        saveContext()
        
        return report
    }
    
    func generateDocument(_ template: DocumentTemplate) async throws -> String {
        guard let caseItem = currentCase else {
            throw CaseError.noActiveCase
        }
        
        isLoading = true
        defer { isLoading = false }
        
        let evidenceItems = caseItem.evidenceItems ?? []
        
        return try await llmService.generateDocument(
            templateType: template,
            caseData: caseItem,
            evidenceItems: evidenceItems
        )
    }
    
    func askLegalQuestion(_ question: String) async throws -> String {
        guard let caseItem = currentCase else {
            throw CaseError.noActiveCase
        }
        
        isLoading = true
        defer { isLoading = false }
        
        return try await llmService.legalQA(
            question: question,
            context: caseItem.incidentDescription
        )
    }
    
    // MARK: - 證據管理
    
    func getEvidenceCount(for caseId: UUID) -> Int {
        guard let caseItem = cases.first(where: { $0.id == caseId }) else { return 0 }
        return caseItem.evidenceCount
    }
    
    func getEvidenceChainIntegrity(for caseId: UUID) -> (complete: Bool, count: Int) {
        guard let caseItem = cases.first(where: { $0.id == caseId }),
              let evidence = caseItem.evidenceItems else {
            return (false, 0)
        }
        
        let hashedCount = evidence.filter {
            $0.status == EvidenceStatus.hashed.rawValue || $0.status == EvidenceStatus.verified.rawValue
        }.count
        
        return (hashedCount == evidence.count && evidence.count > 0, evidence.count)
    }
    
    // MARK: - 私有方法
    
    private func saveContext() {
        do {
            try modelContext.save()
        } catch {
            errorMessage = "儲存失敗: \(error.localizedDescription)"
        }
    }
}

// MARK: - 錯誤

enum CaseError: Error, LocalizedError {
    case noActiveCase
    case invalidCaseData
    
    var errorDescription: String? {
        switch self {
        case .noActiveCase: return "沒有選擇的案件"
        case .invalidCaseData: return "案件資料不完整"
        }
    }
}

// MARK: - 預覽用的 ViewModel

extension CaseViewModel {
    static var preview: CaseViewModel {
        let vm = CaseViewModel()
        
        // 建立預覽案件
        let demoCase = vm.createCase(
            title: "XX幼兒園 兒少保護案件",
            category: .childAbuse,
            victimAlias: "小華",
            victimAge: 5,
            institution: "XX幼兒園",
            description: "家長發現孩子突然抗拒上學，夜間頻繁驚醒，並在洗澡時說出『老師玩蟲蟲』等異常語句。"
        )
        
        // 加入預覽證據
        let evidence1 = Evidence(
            caseId: demoCase.id,
            type: .audio,
            fileName: "first_disclosure_20240517.m4a",
            fileSize: 2456789,
            sha256Hash: "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
            chainIndex: 0,
            isFirstDisclosure: true,
            status: .hashed
        )
        evidence1.transcript = "媽媽：你今天在學校開心嗎？\n孩子：不喜歡...老師玩蟲蟲...\n媽媽：什麼是蟲蟲？\n孩子：這裡（指向臀部）"
        
        let evidence2 = Evidence(
            caseId: demoCase.id,
            type: .sensorData,
            fileName: "heart_rate_anomaly_20240517.json",
            fileSize: 1024,
            sha256Hash: "b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456a1",
            previousHash: evidence1.sha256Hash,
            chainIndex: 1,
            status: .hashed
        )
        
        demoCase.addEvidence(evidence1)
        demoCase.addEvidence(evidence2)
        
        // 更新 AI 分析
        demoCase.updateAIAnalysis(
            summary: "證據鏈初步完整，建議補充醫療診斷與監視器調閱",
            probability: 0.65,
            actions: ["補充醫療診斷", "申請監視器", "尋找目擊證人"]
        )
        
        return vm
    }
}
