import Foundation
import SwiftData
import CoreLocation

/// 合作夥伴組織管理模組
///
/// 核心轉變：LegalShield 從「自營審查」變為「平台」
///
/// 誰是合作夥伴：
/// - 児童相談所 / 社會局（公務）
/// - DV 支援中心 / 婦女庇護所（NPO/公設民營）
/// - 兒少保護 NGO（如 Save the Children Japan）
/// - 勞動法律扶助中心
/// - 消費者生活支援中心
/// - 地方自治體防災/安全課
///
/// 合作夥伴的角色：
/// 1. 使用 Partner Dashboard 監看轄區內的警示案件
/// 2. 對轄區內的緊急轉介進行「最終判斷與執行」
/// 3. 提供個案後續追蹤（這是他們本來就在做的事）
///
/// 我們的角色：
/// 1. 提供技術平台（App + Dashboard + API）
/// 2. 確保資料傳輸安全（端到端加密）
/// 3. 不介入個案判斷，不儲存原始個資（平台中立）
class PartnerOrganizationModule: ObservableObject {
    
    // MARK: - Published
    
    @Published var registeredPartners: [PartnerOrganization] = []
    @Published var activeAlerts: [PartnerAlertView] = []
    
    // MARK: - 依賴
    
    private let modelContext: ModelContext?
    
    // MARK: - 初始化
    
    init(context: ModelContext? = nil) {
        self.modelContext = context
        loadRegisteredPartners()
    }
    
    // MARK: - 合作夥伴註冊
    
    /// 註冊一個新的合作夥伴組織
    /// 流程：
    /// 1. 組織提交申請（含法人登記、業務範圍、負責人資格）
    /// 2. LegalShield 審核（確認為合法社福/行政/法律援助機構）
    /// 3. 簽署 DPA (Data Processing Agreement) 數據處理協議
    /// 4. 開通 Partner Dashboard 帳號
    func registerPartner(
        name: String,
        shortName: String,
        organizationType: PartnerType,
        registrationNumber: String, // 法人登記號
        jurisdiction: JurisdictionArea, // 管轄區域
        services: [SupportedService],
        primaryContact: PartnerContact,
        operatingHours: OperatingHours,
        legalBasis: String // 該組織的法律授權（如「児童虐待防止法第6条」）
    ) throws -> PartnerOrganization {
        
        // 驗證：該組織類型是否具備處理此類個資的法律授權
        guard validateLegalAuthorization(type: organizationType, basis: legalBasis) else {
            throw PartnerError.insufficientLegalAuthorization
        }
        
        let partner = PartnerOrganization(
            id: UUID(),
            name: name,
            shortName: shortName,
            type: organizationType,
            registrationNumber: registrationNumber,
            jurisdiction: jurisdiction,
            services: services,
            primaryContact: primaryContact,
            operatingHours: operatingHours,
            legalBasis: legalBasis,
            status: .pendingApproval,
            createdAt: Date()
        )
        
        savePartner(partner)
        return partner
    }
    
    /// 審核通過合作夥伴申請
    func approvePartner(partnerId: UUID, approvedBy: String) {
        guard let partner = registeredPartners.first(where: { $0.id == partnerId }) else { return }
        partner.status = .active
        partner.approvedAt = Date()
        partner.approvedBy = approvedBy
        
        // 生成 Partner Dashboard API 金鑰
        partner.apiKey = generateSecureAPIKey()
        
        savePartner(partner)
    }
    
    // MARK: - 案件路由（最核心）
    
    /// 將緊急轉介案件路由到適當的合作夥伴
    /// 路由邏輯：
    /// 1. 根據 GPS 位置 → 匹配管轄區域
    /// 2. 根據案件類型 → 匹配服務能力
    /// 3. 根據營業時間 → 匹配在線夥伴
    /// 4. 根據負載均衡 → 避免單一夥伴過載
    func routeEscalationToPartner(
        record: EscalationRecord,
        caseData: LegalCase
    ) throws -> PartnerOrganization {
        
        let snapshot = record.snapshot
        let location = snapshot?.gpsLocation
        let category = caseData.caseCategory
        
        // 1. 過濾：活躍狀態 + 具備對應服務能力
        let candidates = registeredPartners.filter { partner in
            partner.status == .active &&
            partner.services.contains(mapCategoryToService(category)) &&
            isPartnerOnDuty(partner)
        }
        
        guard !candidates.isEmpty else {
            throw PartnerError.noAvailablePartner
        }
        
        // 2. 優先：管轄區域匹配
        let jurisdictionMatches = candidates.filter { partner in
            partner.jurisdiction.contains(location: location)
        }
        
        let finalCandidates = jurisdictionMatches.isEmpty ? candidates : jurisdictionMatches
        
        // 3. 選擇：當前負載最低
        let selected = finalCandidates.min { a, b in
            a.currentActiveCases < b.currentActiveCases
        }!
        
        // 4. 建立路由記錄
        let routing = CaseRoutingRecord(
            id: UUID(),
            escalationId: record.id,
            partnerId: selected.id,
            routedAt: Date(),
            reason: "管轄區域匹配 + 負載均衡",
            status: .routed
        )
        saveRouting(routing)
        
        // 5. 通知合作夥伴
        Task {
            await notifyPartnerOfNewCase(partner: selected, record: record)
        }
        
        return selected
    }
    
    // MARK: - Partner Dashboard 資料
    
    /// 為特定合作夥伴生成 Dashboard 可視化資料
    /// 這是 Partner Dashboard 的資料來源
    func generateDashboardData(for partnerId: UUID) -> PartnerDashboardData? {
        guard let partner = registeredPartners.first(where: { $0.id == partnerId }) else { return nil }
        
        let activeCases = loadActiveCasesForPartner(partnerId: partnerId)
        let todayAlerts = loadAlertsForPartner(partnerId: partnerId, since: Calendar.current.startOfDay(for: Date()))
        
        return PartnerDashboardData(
            partnerName: partner.shortName,
            activeCases: activeCases.map { mapToCaseView($0) },
            pendingAlerts: todayAlerts.filter { $0.status == "pending" }.count,
            avgResponseTime: calculateAvgResponseTime(partnerId: partnerId),
            jurisdictionMap: generateJurisdictionHeatmap(partnerId: partnerId)
        )
    }
    
    /// Partner Dashboard 看到的「案件卡片」
    /// 注意：合作夥伴看到的是「去識別化」的資料，需要進一步授權才能看到完整個資
    func mapToCaseView(_ routing: CaseRoutingRecord) -> PartnerCaseCard {
        let record = loadEscalationRecord(id: routing.escalationId)
        let snapshot = record?.snapshot
        
        return PartnerCaseCard(
            caseId: routing.escalationId.uuidString,
            receivedAt: routing.routedAt,
            urgency: routing.urgencyLevel,
            // 去識別化：只顯示「區域」而非精確地址
            approximateLocation: snapshot?.gpsLocation?.toApproximateAddress() ?? "未知區域",
            // 去識別化：只顯示案件類型，不顯示當事人姓名
            caseType: routing.caseType,
            // 去識別化：只顯示證據數量，不顯示內容
            evidenceCount: snapshot?.evidenceHashes.count ?? 0,
            // 是否已授權解密（需專員點擊「確認介入」後才開放）
            isAuthorized: routing.partnerAuthorizedAt != nil,
            status: routing.status.rawValue,
            // 系統建議行動
            systemRecommendation: routing.systemRecommendation
        )
    }
    
    // MARK: - 授權機制
    
    /// 合作夥伴專員點擊「確認介入」後，才解密完整個資
    func partnerAuthorizedAccess(
        routingId: UUID,
        partnerStaffId: String,
        authorizationReason: String
    ) throws -> DecryptedCasePackage {
        guard let routing = loadRouting(id: routingId) else {
            throw PartnerError.routingNotFound
        }
        
        guard routing.status == .routed || routing.status == .reviewing else {
            throw PartnerError.invalidStatusForAuthorization
        }
        
        // 記錄：誰、何時、為什麼查看了完整個資
        let auditLog = AuditLogRecord(
            id: UUID(),
            routingId: routingId,
            partnerStaffId: partnerStaffId,
            action: "authorized_full_access",
            reason: authorizationReason,
            timestamp: Date(),
            ipAddress: nil // 從 request 取得
        )
        saveAuditLog(auditLog)
        
        routing.partnerAuthorizedAt = Date()
        routing.partnerStaffId = partnerStaffId
        routing.status = .partnerReviewing
        saveRouting(routing)
        
        // 解密並返回完整資料包
        let record = loadEscalationRecord(id: routing.escalationId)
        return try decryptCasePackage(for: record)
    }
    
    // MARK: - 案件狀態同步
    
    /// 合作夥伴更新案件處理狀態
    func partnerUpdatedCaseStatus(
        routingId: UUID,
        newStatus: PartnerCaseStatus,
        partnerNotes: String?,
        outcome: String?
    ) {
        guard let routing = loadRouting(id: routingId) else { return }
        
        routing.status = newStatus
        routing.partnerNotes = partnerNotes
        routing.outcome = outcome
        routing.updatedAt = Date()
        
        // 如果已結案，通知用戶
        if newStatus == .resolved || newStatus == .referredToOther {
            Task {
                await notifyUserOfResolution(routing: routing)
            }
        }
        
        saveRouting(routing)
    }
    
    // MARK: - 私有輔助
    
    private func validateLegalAuthorization(type: PartnerType, basis: String) -> Bool {
        switch type {
        case .childConsultationCenter:
            return basis.contains("児童虐待防止法") || basis.contains("児童福祉法")
        case .dvSupportCenter:
            return basis.contains("配偶者暴力") || basis.contains("DV")
        case .policeDepartment:
            return basis.contains("警察法")
        case .socialWelfareCouncil:
            return basis.contains("社会福祉法")
        case .legalAidCenter:
            return basis.contains("法律扶助") || basis.contains("法テラス")
        case .consumerCenter:
            return basis.contains("消費者基本法")
        case .laborStandardsOffice:
            return basis.contains("労働基準法")
        case .municipalSafetyDivision:
            return basis.contains("地方自治法")
        case .ngo:
            // NGO 需有明確的合作協議或政府委託
            return basis.contains("NPO法") || basis.contains("委託契約")
        }
    }
    
    private func mapCategoryToService(_ category: CaseCategory) -> SupportedService {
        switch category {
        case .childAbuse, .schoolBullying:
            return .childProtection
        case .domesticViolence, .stalking:
            return .domesticViolenceSupport
        case .sexualHarassment, .hiddenCamera:
            return .sexualViolenceSupport
        case .laborExploitation, .workplaceHarassment:
            return .laborRights
        case .consumerFraud, .contractTrap, .productLiability:
            return .consumerProtection
        case .elderAbuse, .institutionalNeglect:
            return .elderCare
        case .administrativeComplaint:
            return .administrativeRelief
        case .droneViolation, .privacyByDrone:
            return .publicSafety
        case .environmentalCrime:
            return .environmentalProtection
        case .general, .other:
            return .generalConsultation
        }
    }
    
    private func isPartnerOnDuty(_ partner: PartnerOrganization) -> Bool {
        let now = Date()
        let calendar = Calendar.current
        let weekday = calendar.component(.weekday, from: now)
        let hour = calendar.component(.hour, from: now)
        
        guard let hours = partner.operatingHours else { return false }
        
        let isWeekend = weekday == 1 || weekday == 7
        if isWeekend && !hours.weekendAvailable {
            return false
        }
        
        return hour >= hours.startHour && hour < hours.endHour
    }
    
    private func generateSecureAPIKey() -> String {
        let uuid = UUID().uuidString
        let timestamp = String(Date().timeIntervalSince1970)
        let raw = "\(uuid)_\(timestamp)"
        return raw.sha256 // 假設有 SHA256 extension
    }
    
    private func notifyPartnerOfNewCase(partner: PartnerOrganization, record: EscalationRecord) async {
        // 推播通知 / 簡訊 / 電子郵件
        // "LegalShield: 新しい緊急案件が管轄区域に発生しました。Partner Dashboard を確認してください。"
    }
    
    private func notifyUserOfResolution(routing: CaseRoutingRecord) async {
        // 推播通知用戶案件已由合作夥伴接手
    }
    
    private func decryptCasePackage(for record: EscalationRecord?) throws -> DecryptedCasePackage {
        guard let record = record,
              let snapshot = record.snapshot,
              let consent = record.consentSnapshot else {
            throw PartnerError.decryptionFailed
        }
        
        // 使用緊急解密金鑰
        return DecryptedCasePackage(
            reporterIdentity: consent.userIdentity, // 解密後
            location: snapshot.gpsLocation,
            contactInfo: snapshot.userContact,
            evidenceHashes: snapshot.evidenceHashes,
            description: snapshot.userDescription
        )
    }
    
    // MARK: - 儲存
    
    private func savePartner(_ partner: PartnerOrganization) {
        guard let context = modelContext else { return }
        context.insert(partner)
        try? context.save()
    }
    
    private func saveRouting(_ routing: CaseRoutingRecord) {
        guard let context = modelContext else { return }
        context.insert(routing)
        try? context.save()
    }
    
    private func saveAuditLog(_ log: AuditLogRecord) {
        guard let context = modelContext else { return }
        context.insert(log)
        try? context.save()
    }
    
    private func loadRegisteredPartners() {
        guard let context = modelContext else { return }
        let descriptor = FetchDescriptor<PartnerOrganization>(
            sortBy: [SortDescriptor(\.createdAt, order: .reverse)]
        )
        registeredPartners = (try? context.fetch(descriptor)) ?? []
    }
    
    private func loadActiveCasesForPartner(partnerId: UUID) -> [CaseRoutingRecord] {
        guard let context = modelContext else { return [] }
        let descriptor = FetchDescriptor<CaseRoutingRecord>(
            predicate: #Predicate { $0.partnerId == partnerId && $0.status != "resolved" && $0.status != "rejected" }
        )
        return (try? context.fetch(descriptor)) ?? []
    }
    
    private func loadAlertsForPartner(partnerId: UUID, since: Date) -> [CaseRoutingRecord] {
        guard let context = modelContext else { return [] }
        let descriptor = FetchDescriptor<CaseRoutingRecord>(
            predicate: #Predicate { $0.partnerId == partnerId && $0.routedAt >= since }
        )
        return (try? context.fetch(descriptor)) ?? []
    }
    
    private func loadEscalationRecord(id: UUID) -> EscalationRecord? {
        guard let context = modelContext else { return nil }
        let descriptor = FetchDescriptor<EscalationRecord>(
            predicate: #Predicate { $0.id == id }
        )
        return try? context.fetch(descriptor).first
    }
    
    private func loadRouting(id: UUID) -> CaseRoutingRecord? {
        guard let context = modelContext else { return nil }
        let descriptor = FetchDescriptor<CaseRoutingRecord>(
            predicate: #Predicate { $0.id == id }
        )
        return try? context.fetch(descriptor).first
    }
    
    private func calculateAvgResponseTime(partnerId: UUID) -> TimeInterval {
        // 簡化實作
        return 480 // 8 分鐘
    }
    
    private func generateJurisdictionHeatmap(partnerId: UUID) -> [String: Int] {
        // 簡化實作
        return [:]
    }
}

// MARK: - 資料結構

enum PartnerType: String, Codable {
    case childConsultationCenter = "児童相談所"
    case dvSupportCenter = "DV支援中心"
    case policeDepartment = "警察署"
    case socialWelfareCouncil = "社会福祉協議会"
    case legalAidCenter = "法律扶助中心"
    case consumerCenter = "消費生活支援中心"
    case laborStandardsOffice = "労働基準監督署"
    case municipalSafetyDivision = "市役所安全課"
    case ngo = "NPO/NGO"
}

enum PartnerStatus: String, Codable {
    case pendingApproval = "審查中"
    case active = "營運中"
    case suspended = "暫停"
    case terminated = "終止合作"
}

enum SupportedService: String, Codable {
    case childProtection = "兒少保護"
    case domesticViolenceSupport = "家暴/跟踪支援"
    case sexualViolenceSupport = "性暴力支援"
    case laborRights = "勞動權益"
    case consumerProtection = "消費者保護"
    case elderCare = "高齡者照護"
    case administrativeRelief = "行政救濟"
    case publicSafety = "公共安全"
    case environmentalProtection = "環境保護"
    case generalConsultation = "一般諮詢"
}

enum PartnerCaseStatus: String, Codable {
    case routed = "已路由"
    case partnerReviewing = "夥伴審查中"
    case contactAttempted = "已嘗試聯繫"
    case interventionOngoing = "介入中"
    case resolved = "已解決"
    case referredToOther = "轉介其他單位"
    case rejected = "駁回"
}

enum PartnerError: Error, LocalizedError {
    case insufficientLegalAuthorization
    case noAvailablePartner
    case routingNotFound
    case invalidStatusForAuthorization
    case decryptionFailed
    
    var errorDescription: String? {
        switch self {
        case .insufficientLegalAuthorization: return "該組織缺乏處理此類個資的法律授權"
        case .noAvailablePartner: return "目前無可用合作夥伴，案件將進入人工備援佇列"
        case .routingNotFound: return "找不到對應的路由記錄"
        case .invalidStatusForAuthorization: return "當前狀態不允許授權查看"
        case .decryptionFailed: return "解密失敗，可能金鑰遺失或記錄損毀"
        }
    }
}

struct JurisdictionArea: Codable {
    let prefecture: String      // 都道府県
    let municipalities: [String] // 市町村
    let coordinates: [GeoBoundary]? // 地理邊界（精確到區域）
    
    func contains(location: CLLocationCoordinate2D?) -> Bool {
        guard let location = location, let boundaries = coordinates else { return false }
        // 簡化：檢查點是否在多邊形內
        return true // 簡化實作
    }
}

struct GeoBoundary: Codable {
    let lat: Double
    let lng: Double
}

struct PartnerContact: Codable {
    let name: String
    let title: String
    let email: String
    let phone: String
}

struct OperatingHours: Codable {
    let startHour: Int    // 9
    let endHour: Int      // 18
    let weekendAvailable: Bool
    let holidayAvailable: Bool
}

@Model
class PartnerOrganization {
    @Attribute(.unique) var id: UUID
    var name: String
    var shortName: String
    var type: String // PartnerType.rawValue
    var registrationNumber: String
    var jurisdictionData: Data? // JurisdictionArea
    var servicesData: Data? // [SupportedService]
    var primaryContactData: Data? // PartnerContact
    var operatingHoursData: Data? // OperatingHours
    var legalBasis: String
    var status: String // PartnerStatus.rawValue
    var apiKey: String?
    var approvedAt: Date?
    var approvedBy: String?
    var createdAt: Date
    
    // 即時狀態（非持久化，記憶體計算）
    var currentActiveCases: Int = 0
    
    var jurisdiction: JurisdictionArea? {
        guard let data = jurisdictionData else { return nil }
        return try? JSONDecoder().decode(JurisdictionArea.self, from: data)
    }
    
    var services: [SupportedService] {
        guard let data = servicesData else { return [] }
        return (try? JSONDecoder().decode([SupportedService].self, from: data)) ?? []
    }
    
    var primaryContact: PartnerContact? {
        guard let data = primaryContactData else { return nil }
        return try? JSONDecoder().decode(PartnerContact.self, from: data)
    }
    
    var operatingHours: OperatingHours? {
        guard let data = operatingHoursData else { return nil }
        return try? JSONDecoder().decode(OperatingHours.self, from: data)
    }
    
    init(id: UUID, name: String, shortName: String, type: PartnerType,
         registrationNumber: String, jurisdiction: JurisdictionArea,
         services: [SupportedService], primaryContact: PartnerContact,
         operatingHours: OperatingHours, legalBasis: String,
         status: PartnerStatus, createdAt: Date) {
        self.id = id
        self.name = name
        self.shortName = shortName
        self.type = type.rawValue
        self.registrationNumber = registrationNumber
        self.jurisdictionData = try? JSONEncoder().encode(jurisdiction)
        self.servicesData = try? JSONEncoder().encode(services)
        self.primaryContactData = try? JSONEncoder().encode(primaryContact)
        self.operatingHoursData = try? JSONEncoder().encode(operatingHours)
        self.legalBasis = legalBasis
        self.status = status.rawValue
        self.createdAt = createdAt
    }
}

@Model
class CaseRoutingRecord {
    @Attribute(.unique) var id: UUID
    var escalationId: UUID
    var partnerId: UUID
    var routedAt: Date
    var reason: String
    var status: String // PartnerCaseStatus.rawValue
    var urgencyLevel: Int
    var caseType: String
    var systemRecommendation: String?
    
    // 授權記錄
    var partnerAuthorizedAt: Date?
    var partnerStaffId: String?
    
    // 處理結果
    var partnerNotes: String?
    var outcome: String?
    var updatedAt: Date?
    
    init(id: UUID, escalationId: UUID, partnerId: UUID, routedAt: Date,
         reason: String, status: PartnerCaseStatus, urgencyLevel: Int = 3,
         caseType: String = "", systemRecommendation: String? = nil) {
        self.id = id
        self.escalationId = escalationId
        self.partnerId = partnerId
        self.routedAt = routedAt
        self.reason = reason
        self.status = status.rawValue
        self.urgencyLevel = urgencyLevel
        self.caseType = caseType
        self.systemRecommendation = systemRecommendation
    }
}

@Model
class AuditLogRecord {
    @Attribute(.unique) var id: UUID
    var routingId: UUID
    var partnerStaffId: String
    var action: String
    var reason: String
    var timestamp: Date
    var ipAddress: String?
    
    init(id: UUID, routingId: UUID, partnerStaffId: String, action: String,
         reason: String, timestamp: Date, ipAddress: String?) {
        self.id = id
        self.routingId = routingId
        self.partnerStaffId = partnerStaffId
        self.action = action
        self.reason = reason
        self.timestamp = timestamp
        self.ipAddress = ipAddress
    }
}

// MARK: - Dashboard 資料結構

struct PartnerDashboardData {
    let partnerName: String
    let activeCases: [PartnerCaseCard]
    let pendingAlerts: Int
    let avgResponseTime: TimeInterval
    let jurisdictionMap: [String: Int] // 區域名: 案件數
}

struct PartnerCaseCard: Identifiable {
    let id: String
    let receivedAt: Date
    let urgency: Int
    let approximateLocation: String // 「東京都新宿区」而非精確地址
    let caseType: String
    let evidenceCount: Int
    let isAuthorized: Bool // 是否已解密
    let status: String
    let systemRecommendation: String?
    
    var urgencyColor: String {
        switch urgency {
        case 4: return "red"
        case 3: return "orange"
        case 2: return "yellow"
        default: return "blue"
        }
    }
}

struct PartnerAlertView: Identifiable {
    let id: UUID
    let caseId: UUID
    let timestamp: Date
    let alertType: String
    let status: String
    let partnerId: UUID
}

struct DecryptedCasePackage {
    let reporterIdentity: EncryptedUserIdentity?
    let location: CLLocationCoordinate2D?
    let contactInfo: EmergencyContactInfo?
    let evidenceHashes: [String]
    let description: String?
}

// MARK: - Extensions

extension CLLocationCoordinate2D {
    func toApproximateAddress() -> String {
        // 簡化：反向地理編碼到「區/市」層級
        return "東京都新宿区" // 簡化實作
    }
}
