import Foundation
import SwiftData

/// 案件類型
enum CaseCategory: String, Codable, CaseIterable {
    // Phase 1: 核心 (兒少 + 偷拍 + 家暴)
    case childAbuse = "child_abuse"
    case sexualHarassment = "sexual_harassment"
    case domesticViolence = "domestic_violence"
    case schoolBullying = "school_bullying"
    case workplaceHarassment = "workplace_harassment"
    case hiddenCamera = "hidden_camera"
    
    // Phase 2: 勞動 + 消費者 + 契約
    case laborExploitation = "labor_exploitation"
    case consumerFraud = "consumer_fraud"
    case contractTrap = "contract_trap"
    case productLiability = "product_liability"
    
    // Phase 3: 高齡 + 行政
    case elderAbuse = "elder_abuse"
    case institutionalNeglect = "institutional_neglect"
    case administrativeComplaint = "administrative_complaint"
    
    // Phase 4: 無人機 + 環境
    case droneViolation = "drone_violation"
    case privacyByDrone = "privacy_by_drone"
    case environmentalCrime = "environmental_crime"
    
    // Phase 5: 民事領域擴展
    case contractDispute = "contract_dispute"           // 契約糾紛
    case productDefect = "product_defect"               // 產品缺陷/售後不履行
    case policeInaction = "police_inaction"             // 警察不作為
    case defamation = "defamation"                      // 名譽毀損
    case unjustEnrichment = "unjust_enrichment"         // 不當得利
    case neighborDispute = "neighbor_dispute"            // 鄰居糾紛
    case trafficAccident = "traffic_accident"           // 交通事故
    case medicalMalpractice = "medical_malpractice"   // 醫療過失
    
    case stalking = "stalking"
    case general = "general"
    case other = "other"
    
    var displayName: String {
        switch self {
        case .childAbuse: return "兒少保護"
        case .sexualHarassment: return "性騷擾/性侵"
        case .domesticViolence: return "家庭暴力"
        case .schoolBullying: return "校園霸凌"
        case .workplaceHarassment: return "職場霸凌"
        case .hiddenCamera: return "偷拍/隱私侵害"
        case .laborExploitation: return "勞動剝削/過勞"
        case .consumerFraud: return "消費詐欺"
        case .contractTrap: return "契約陷阱"
        case .productLiability: return "製造物責任"
        case .contractDispute: return "契約糾紛"
        case .productDefect: return "產品缺陷/售後"
        case .policeInaction: return "警察不作為"
        case .defamation: return "名譽毀損"
        case .unjustEnrichment: return "不當得利"
        case .neighborDispute: return "鄰居糾紛"
        case .trafficAccident: return "交通事故"
        case .medicalMalpractice: return "醫療過失"
        case .elderAbuse: return "高齡者虐待"
        case .institutionalNeglect: return "機構疏忽"
        case .administrativeComplaint: return "行政救濟"
        case .droneViolation: return "無人機違法"
        case .privacyByDrone: return "無人機偷拍"
        case .environmentalCrime: return "環境犯罪"
        case .stalking: return "跟蹤騷擾"
        case .general: return "一般法律諮詢"
        case .other: return "其他"
        }
    }
    
    var urgencyColor: String {
        switch self {
        case .childAbuse, .sexualHarassment, .domesticViolence, .elderAbuse:
            return "red"
        case .schoolBullying, .hiddenCamera, .stalking, .droneViolation, .privacyByDrone:
            return "orange"
        case .laborExploitation, .contractTrap, .consumerFraud, .contractDispute, .productDefect:
            return "yellow"
        case .policeInaction, .defamation, .trafficAccident, .medicalMalpractice:
            return "orange"
        case .unjustEnrichment, .neighborDispute:
            return "blue"
        default:
            return "blue"
        }
    }
    
    /// 對應的日本法規領域 (JapaneseLegalRAG.LegalDomain)
    var japaneseLegalDomains: [JapaneseLegalRAG.LegalDomain] {
        switch self {
        case .childAbuse, .schoolBullying:
            return [.childAbuse, .criminal]
        case .sexualHarassment, .stalking:
            return [.stalking, .criminal]
        case .domesticViolence:
            return [.criminal, .childAbuse]
        case .workplaceHarassment, .laborExploitation:
            return [.labor, .laborContract]
        case .consumerFraud, .contractTrap:
            return [.consumer, .specificCommercial]
        case .elderAbuse, .institutionalNeglect:
            return [.elderAbuse, .longTermCare]
        case .administrativeComplaint:
            return [.administrative, .adminLitigation]
        case .droneViolation, .privacyByDrone:
            return [.aviation, .criminal]
        case .environmentalCrime:
            return [.environmental, .soilPollution]
        case .hiddenCamera:
            return [.stalking, .criminal]
        case .productLiability:
            return [.consumer, .criminal]
        case .contractDispute:
            return [.civil, .consumer]
        case .productDefect:
            return [.consumer, .productLiabilityLaw]
        case .policeInaction:
            return [.administrative, .adminLitigation, .criminal]
        case .defamation:
            return [.civil, .criminal]
        case .unjustEnrichment:
            return [.civil]
        case .neighborDispute:
            return [.civil]
        case .trafficAccident:
            return [.civil, .criminal]
        case .medicalMalpractice:
            return [.civil, .criminal]
        case .general, .other:
            return [.criminal, .consumer]
        }
    }
}

/// 案件狀態
enum CaseStatus: String, Codable {
    case active = "active"           // 進行中
    case pending = "pending"         // 等待回應
    case resolved = "resolved"       // 已解決
    case escalated = "escalated"    // 已升級 (檢察/訴訟)
    case archived = "archived"       // 封存
}

/// 緊急等級
enum UrgencyLevel: Int, Codable, CaseIterable {
    case low = 1
    case medium = 2
    case high = 3
    case critical = 4
    
    var displayName: String {
        switch self {
        case .low: return "一般"
        case .medium: return "注意"
        case .high: return "緊急"
        case .critical: return "危急"
        }
    }
}

/// 案件模型 — 中心管理單元
@Model
final class LegalCase {
    @Attribute(.unique) var id: UUID
    var title: String
    var category: String              // CaseCategory.rawValue
    var status: String                // CaseStatus.rawValue
    var urgency: Int                  // UrgencyLevel.rawValue
    var createdAt: Date
    var updatedAt: Date
    
    // 當事人資訊 (去識別化儲存)
    var victimAlias: String           // 代號，如 "小華"
    var victimAge: Int?
    var victimGender: String?
    var perpetratorAlias: String?     // 代號，如 "陳老師"
    var perpetratorRole: String?      // "幼兒園教師", "補習班老師"
    
    // 事件資訊
    var incidentDate: Date?
    var incidentLocation: String?
    var incidentDescription: String?
    var institutionName: String?      // 機構名稱 (幼兒園/學校)
    
    // 關聯證據 (透過 caseId 關聯)
    @Relationship(deleteRule: .cascade, inverse: \Evidence.caseId)
    var evidenceItems: [Evidence]?
    
    // 感測器異常記錄
    var anomalyLogs: [AnomalyLog]?
    
    // 法律進度
    var policeReportDate: Date?
    var policeCaseNumber: String?
    var prosecutorDate: Date?
    var courtDate: Date?
    
    // AI 分析結果
    var aiAnalysisSummary: String?
    var winProbability: Double?       // 0.0 ~ 1.0
    var recommendedActions: [String]?
    
    // 協作
    var sharedWith: [String]?         // 共享對象 email
    var cloudSyncEnabled: Bool
    
    // MARK: - Init
    
    init(
        id: UUID = UUID(),
        title: String,
        category: CaseCategory,
        urgency: UrgencyLevel = .medium,
        victimAlias: String = "匿名",
        victimAge: Int? = nil,
        victimGender: String? = nil,
        perpetratorAlias: String? = nil,
        perpetratorRole: String? = nil,
        incidentDate: Date? = nil,
        incidentLocation: String? = nil,
        incidentDescription: String? = nil,
        institutionName: String? = nil
    ) {
        self.id = id
        self.title = title
        self.category = category.rawValue
        self.status = CaseStatus.active.rawValue
        self.urgency = urgency.rawValue
        self.createdAt = Date()
        self.updatedAt = Date()
        self.victimAlias = victimAlias
        self.victimAge = victimAge
        self.victimGender = victimGender
        self.perpetratorAlias = perpetratorAlias
        self.perpetratorRole = perpetratorRole
        self.incidentDate = incidentDate
        self.incidentLocation = incidentLocation
        self.incidentDescription = incidentDescription
        self.institutionName = institutionName
        self.cloudSyncEnabled = false
    }
    
    // MARK: - 計算屬性
    
    var caseCategory: CaseCategory {
        CaseCategory(rawValue: category) ?? .other
    }
    
    var caseStatus: CaseStatus {
        CaseStatus(rawValue: status) ?? .active
    }
    
    var urgencyLevel: UrgencyLevel {
        UrgencyLevel(rawValue: urgency) ?? .medium
    }
    
    var evidenceCount: Int {
        evidenceItems?.count ?? 0
    }
    
    var chainOfCustodyComplete: Bool {
        guard let items = evidenceItems, !items.isEmpty else { return false }
        // 檢查所有證據都有 hash
        return items.allSatisfy { $0.status == EvidenceStatus.hashed.rawValue || $0.status == EvidenceStatus.verified.rawValue }
    }
    
    var daysSinceCreation: Int {
        Calendar.current.dateComponents([.day], from: createdAt, to: Date()).day ?? 0
    }
    
    // MARK: - 方法
    
    func addEvidence(_ evidence: Evidence) {
        if evidenceItems == nil {
            evidenceItems = []
        }
        evidenceItems?.append(evidence)
        updatedAt = Date()
    }
    
    func updateAIAnalysis(summary: String, probability: Double?, actions: [String]) {
        self.aiAnalysisSummary = summary
        self.winProbability = probability
        self.recommendedActions = actions
        self.updatedAt = Date()
    }
}

// MARK: - Anomaly Log

/// 感測器異常記錄
struct AnomalyLog: Codable {
    let timestamp: Date
    let sensorType: String
    let severity: String          // "low", "medium", "high", "critical"
    let description: String
    let threshold: Double
    let actualValue: Double
    let deviceName: String?
}

// MARK: - 案件範本

extension LegalCase {
    /// 建立幼兒園虐待案範本
    static func childAbuseTemplate(
        institution: String,
        victimAge: Int,
        victimAlias: String = "小華"
    ) -> LegalCase {
        let caseInstance = LegalCase(
            title: "\(institution) 兒少保護案件",
            category: .childAbuse,
            urgency: .critical,
            victimAlias: victimAlias,
            victimAge: victimAge,
            institutionName: institution
        )
        return caseInstance
    }
    
    /// 建立偷拍偵測案範本
    static func hiddenCameraTemplate(location: String) -> LegalCase {
        LegalCase(
            title: "\(location) 隱私侵害調查",
            category: .hiddenCamera,
            urgency: .high,
            incidentLocation: location
        )
    }
}
