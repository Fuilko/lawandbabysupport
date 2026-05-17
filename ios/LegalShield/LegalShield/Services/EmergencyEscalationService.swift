import Foundation
import CoreLocation
import SwiftData

// MARK: - 緊急轉介服務
//
// 法律前提：
// 1. 個資法（日本：個人情報保護法 / 台灣：個資法）允許「緊急避難」為例外，但條件極嚴格
// 2. 必須有「明確同意」才能將個資轉給第三方（警察、社工、NGO）
// 3. AI 自動通報可能觸法——必須有人類審查（Human-in-the-loop）
// 4. 所有介入行為必須留痕，供日後舉證「已盡合理注意義務」

class EmergencyEscalationService: ObservableObject {
    
    // MARK: - Published
    
    @Published var emergencyStatus: EmergencyStatus = .idle
    @Published var activeEscalations: [EscalationRecord] = []
    
    // MARK: - 依賴
    
    private let evidenceManager: EvidenceManager
    private let locationManager: CLLocationManager
    private let modelContext: ModelContext?
    
    // MARK: - 配置
    
    /// 後端通報 API（獨立於 LLM API，更高安全等級）
    var backendEscalationEndpoint: String = "https://escalation.legalshield.jp/api/v1"
    
    /// 自動通報門檻（需多條件同時滿足）
    var autoReportThreshold: AutoReportThreshold = .strict
    
    // MARK: - 初始化
    
    init(evidenceManager: EvidenceManager, context: ModelContext? = nil) {
        self.evidenceManager = evidenceManager
        self.locationManager = CLLocationManager()
        self.modelContext = context
        self.locationManager.desiredAccuracy = kCLLocationAccuracyBest
    }
    
    // MARK: - 公開 API
    
    /// 使用者主動觸發緊急求助
    /// 前提：用戶已簽署「緊急轉介同意書」
    func userTriggeredEmergency(
        caseId: UUID,
        reason: EmergencyReason,
        userMessage: String? = nil
    ) async throws -> EscalationResult {
        
        // 1. 驗證用戶是否已授權緊急轉介
        guard let consent = loadEmergencyConsent(for: caseId),
              consent.isActive else {
            throw EscalationError.consentNotGranted
        }
        
        // 2. 收集當前狀態（GPS、裝置資訊、最後活動）
        let snapshot = try await collectEmergencySnapshot(caseId: caseId)
        
        // 3. 建立轉介記錄
        let record = EscalationRecord(
            id: UUID(),
            caseId: caseId,
            triggeredAt: Date(),
            triggerType: .userInitiated,
            reason: reason,
            snapshot: snapshot,
            consentSnapshot: consent,
            status: .collecting
        )
        
        // 4. 立即鎖定證據（防止用戶誤刪或裝置被奪）
        try await evidenceManager.lockEvidenceForCase(caseId)
        
        // 5. 透過 PartnerOrganizationModule 路由到合作夥伴
        // 不是上傳到「我們的審查佇列」，而是直接路由到「具備法律授權的合作夥伴」
        let partnerModule = PartnerOrganizationModule(context: modelContext)
        let caseData = loadCase(id: caseId)
        let partner = try partnerModule.routeEscalationToPartner(
            record: record,
            caseData: caseData
        )
        
        record.backendTicketId = partner.id.uuidString
        record.status = .humanReviewPending
        record.routedToPartnerName = partner.shortName
        
        saveRecord(record)
        
        return EscalationResult(
            recordId: record.id,
            ticketId: partner.id.uuidString,
            message: "您的求助已傳送至 \(partner.shortName)。該機構的值班專員將在 10 分鐘內確認並啟動協助。",
            estimatedResponseTime: 600 // 10 minutes
        )
    }
    
    /// 系統偵測到「可能需要介入」的訊號
    /// 例如：求救語音關鍵詞、異常感測器模式、多次緊急按鈕觸發
    func systemDetectedPotentialEmergency(
        caseId: UUID,
        detectionSource: DetectionSource,
        confidence: Double,
        rawEvidence: [Evidence]
    ) async {
        
        // ⚠️ 重要：系統偵測到「潛在危險」≠ 自動通報
        // 這裡只能做「預警標記」，絕對不能直接報警或聯繫第三方
        
        let alert = SystemAlertRecord(
            id: UUID(),
            caseId: caseId,
            detectedAt: Date(),
            source: detectionSource,
            confidence: confidence,
            evidenceIds: rawEvidence.map { $0.id },
            status: .flaggedForReview
        )
        
        // 僅在 App 內顯示警示——詢問用戶是否需要協助
        // 不傳送任何個資到後端
        await showInAppSafetyPrompt(alert: alert)
        
        saveSystemAlert(alert)
    }
    
    /// 使用者回應系統警示（選擇求助或取消）
    func userRespondedToAlert(
        alertId: UUID,
        userChoice: UserAlertChoice
    ) async throws {
        guard let alert = loadSystemAlert(id: alertId) else { return }
        
        switch userChoice {
        case .confirmNeedHelp:
            // 用戶確認需要幫助 → 等同主動觸發
            alert.status = .userConfirmed
            try await userTriggeredEmergency(
                caseId: alert.caseId,
                reason: mapDetectionToReason(alert.source)
            )
            
        case .falseAlarm:
            // 用戶取消 → 標記為誤報，記錄但不刪除（審計需求）
            alert.status = .userDismissed
            alert.dismissedAt = Date()
            saveSystemAlert(alert)
            
        case .snooze:
            // 用戶要求稍後再問（15分鐘後再次提示）
            alert.status = .snoozed
            alert.snoozeUntil = Date().addingTimeInterval(900)
            saveSystemAlert(alert)
        }
    }
    
    // MARK: - 後端人類審查（Backend Human Review）
    
    /// 後端專員審查後，決定是否執行轉介
    /// 這是「人類在環路」的關鍵節點——AI 不能自動完成這一步
    func backendReviewCompleted(
        ticketId: String,
        reviewerDecision: ReviewerDecision,
        reviewerNotes: String? = nil
    ) async throws {
        guard let record = activeEscalations.first(where: { $0.backendTicketId == ticketId }) else {
            throw EscalationError.recordNotFound
        }
        
        record.reviewerDecision = reviewerDecision
        record.reviewerNotes = reviewerNotes
        record.reviewedAt = Date()
        
        switch reviewerDecision {
        case .approveWithContact:
            // 審查通過 → 聯繫用戶確認最後細節
            record.status = .contactingUser
            try await contactUserForFinalConfirmation(record: record)
            
        case .approveImmediate:
            // 緊急情況（如即時生命危險）→ 直接啟動轉介
            record.status = .executingReferral
            try await executeReferral(record: record)
            
        case .requestMoreInfo:
            // 需要更多資訊
            record.status = .awaitingUserInput
            try await requestAdditionalInfoFromUser(record: record)
            
        case .reject:
            // 判定為誤報或無法介入
            record.status = .rejected
            record.completedAt = Date()
            saveRecord(record)
        }
    }
    
    // MARK: - 執行轉介（最敏感的操作）
    
    private func executeReferral(record: EscalationRecord) async throws {
        guard let consent = record.consentSnapshot else {
            throw EscalationError.consentMissing
        }
        
        // 根據用戶預先設定的「轉介偏好」選擇接收方
        for recipient in consent.preferredRecipients {
            switch recipient {
            case .police:
                try await reportToPolice(record: record)
            case .childConsultationCenter:
                try await reportToChildConsultation(record: record)
            case .domesticViolenceSupportCenter:
                try await reportToDVSupport(record: record)
            case .designatedNGO:
                if let ngo = consent.designatedNGO {
                    try await reportToNGO(record: record, ngo: ngo)
                }
            case .designatedLawyer:
                if let lawyer = consent.designatedLawyer {
                    try await reportToLawyer(record: record, lawyer: lawyer)
                }
            case .trustedContact:
                if let contact = consent.emergencyContact {
                    try await notifyTrustedContact(record: record, contact: contact)
                }
            }
        }
        
        record.status = .completed
        record.completedAt = Date()
        saveRecord(record)
    }
    
    // MARK: - 各類通報實作
    
    private func reportToPolice(record: EscalationRecord) async throws {
        // 日本：110番通報用データパック
        // 台灣：110 或婦幼保護專線
        let reportPackage = try buildPoliceReportPackage(record: record)
        
        var request = URLRequest(url: URL(string: "\(backendEscalationEndpoint)/police")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(reportPackage)
        
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw EscalationError.referralFailed
        }
    }
    
    private func reportToChildConsultation(record: EscalationRecord) async throws {
        // 日本：児童相談所 (189 番)
        // 台灣：各縣市社會局兒童保護專線
        let package = try buildChildConsultationPackage(record: record)
        // ...
    }
    
    private func reportToDVSupport(record: EscalationRecord) async throws {
        // 日本：DV相談支援センター (#8008)
        // ...
    }
    
    // MARK: - 資料包建構
    
    private func buildPoliceReportPackage(record: EscalationRecord) throws -> PoliceReportPackage {
        guard let snapshot = record.snapshot else {
            throw EscalationError.snapshotMissing
        }
        
        // ⚠️ 最小必要原則：只傳送通報「絕對必要」的資料
        return PoliceReportPackage(
            reportId: record.id.uuidString,
            timestamp: record.triggeredAt,
            // 只有當用戶明確同意分享定位時才包含
            location: snapshot.consentSnapshot?.includesLocation == true ? snapshot.gpsLocation : nil,
            // 只有當用戶明確同意分享聯繫方式時才包含
            reporterContact: snapshot.consentSnapshot?.includesContactInfo == true ? snapshot.userContact : nil,
            // 證據摘要（不含原始內容，只給 hash 和類型）
            evidenceSummary: snapshot.evidenceHashes.map { hash in
                EvidenceSummary(hash: hash, type: "photo/audio", timestamp: Date())
            },
            // 事件描述（用戶自行輸入）
            incidentDescription: snapshot.userDescription,
            // 法律依據聲明
            legalBasis: "本人明示同意による緊急通報（個人情報保護法第17条ただし書き）"
        )
    }
    
    // MARK: - 緊急快照收集
    
    private func collectEmergencySnapshot(caseId: UUID) async throws -> EmergencySnapshot {
        let location = locationManager.location?.coordinate
        
        // 只收集「用戶同意分享」的資料
        let consent = loadEmergencyConsent(for: caseId)
        
        return EmergencySnapshot(
            collectedAt: Date(),
            gpsLocation: consent?.includesLocation == true ? location : nil,
            deviceBattery: UIDevice.current.batteryLevel,
            networkStatus: getNetworkStatus(),
            lastEvidenceHash: evidenceManager.getLastEvidenceHash(for: caseId),
            evidenceHashes: evidenceManager.getAllEvidenceHashes(for: caseId),
            userContact: consent?.includesContactInfo == true ? consent?.emergencyContact : nil,
            userDescription: nil, // 待用戶補充
            consentSnapshot: consent
        )
    }
    
    // MARK: - 同意管理
    
    /// 建立緊急轉介同意書
    /// 這是法律核心——用戶必須逐條明確同意
    func createEmergencyConsent(
        caseId: UUID,
        userIdentity: UserIdentity, // 姓名、電話、住址（加密儲存）
        emergencyContact: EmergencyContactInfo?, // 緊急聯繫人
        includesLocation: Bool,
        includesContactInfo: Bool,
        includesEvidence: Bool,
        preferredRecipients: [ReferralRecipient],
        designatedNGO: NGOInfo? = nil,
        designatedLawyer: LawyerInfo? = nil
    ) -> EmergencyConsent {
        
        let consent = EmergencyConsent(
            id: UUID(),
            caseId: caseId,
            createdAt: Date(),
            userIdentity: encryptUserIdentity(userIdentity), // 立即加密
            emergencyContact: emergencyContact,
            includesLocation: includesLocation,
            includesContactInfo: includesContactInfo,
            includesEvidence: includesEvidence,
            preferredRecipients: preferredRecipients,
            designatedNGO: designatedNGO,
            designatedLawyer: designatedLawyer,
            isActive: true,
            version: "1.0"
        )
        
        saveConsent(consent)
        return consent
    }
    
    /// 撤銷同意（用戶隨時可撤銷，但已執行的轉介無法撤回）
    func revokeEmergencyConsent(caseId: UUID) {
        if let consent = loadEmergencyConsent(for: caseId) {
            consent.isActive = false
            consent.revokedAt = Date()
            saveConsent(consent)
        }
    }
    
    // MARK: - 私有輔助
    
    private func encryptUserIdentity(_ identity: UserIdentity) -> EncryptedUserIdentity {
        // 使用獨立的緊急加密金鑰（與證據金鑰不同）
        // 僅在轉介執行時解密
        let jsonData = try! JSONEncoder().encode(identity)
        // ... AES-GCM 加密
        return EncryptedUserIdentity(cipherData: jsonData, keyId: "emergency_key_v1")
    }
    
    private func submitToHumanReviewQueue(record: EscalationRecord) async throws -> String {
        // 傳送到後端人類審查系統
        var request = URLRequest(url: URL(string: "\(backendEscalationEndpoint)/human-review")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let payload = HumanReviewPayload(
            recordId: record.id.uuidString,
            caseId: record.caseId.uuidString,
            triggerType: record.triggerType.rawValue,
            reason: record.reason.rawValue,
            timestamp: record.triggeredAt,
            // 傳送 hash 而非原始內容，審查員需要看原始證據時再授權解密
            evidenceHashList: record.snapshot?.evidenceHashes ?? []
        )
        
        request.httpBody = try JSONEncoder().encode(payload)
        let (data, _) = try await URLSession.shared.data(for: request)
        
        if let json = try JSONSerialization.jsonObject(with: data) as? [String: String],
           let ticketId = json["ticketId"] {
            return ticketId
        }
        throw EscalationError.submissionFailed
    }
    
    private func showInAppSafetyPrompt(alert: SystemAlertRecord) async {
        // 透過 NotificationCenter 發送本地通知
        // App 內顯示全屏安全提示，詢問用戶是否需要協助
    }
    
    private func contactUserForFinalConfirmation(record: EscalationRecord) async throws {
        // 簡訊/電話/推播通知用戶：「我們偵測到您可能需要協助，是否啟動轉介？」
    }
    
    private func requestAdditionalInfoFromUser(record: EscalationRecord) async throws {
        // 推播通知用戶補充資訊
    }
    
    private func notifyTrustedContact(record: EscalationRecord, contact: EmergencyContactInfo) async throws {
        // 發送簡訊給緊急聯繫人
        let message = "【LegalShield 緊急通知】\(record.snapshot?.userName ?? "您的親友") 已啟動安全求助，請盡快聯繫確認其安危。"
        // 使用 SMS API
    }
    
    // MARK: - 儲存
    
    private func saveRecord(_ record: EscalationRecord) {
        guard let context = modelContext else { return }
        context.insert(record)
        try? context.save()
    }
    
    private func saveConsent(_ consent: EmergencyConsent) {
        guard let context = modelContext else { return }
        context.insert(consent)
        try? context.save()
    }
    
    private func saveSystemAlert(_ alert: SystemAlertRecord) {
        guard let context = modelContext else { return }
        context.insert(alert)
        try? context.save()
    }
    
    private func loadEmergencyConsent(for caseId: UUID) -> EmergencyConsent? {
        guard let context = modelContext else { return nil }
        let descriptor = FetchDescriptor<EmergencyConsent>(
            predicate: #Predicate { $0.caseId == caseId && $0.isActive }
        )
        return try? context.fetch(descriptor).first
    }
    
    private func loadSystemAlert(id: UUID) -> SystemAlertRecord? {
        guard let context = modelContext else { return nil }
        let descriptor = FetchDescriptor<SystemAlertRecord>(
            predicate: #Predicate { $0.id == id }
        )
        return try? context.fetch(descriptor).first
    }
    
    private func loadCase(id: UUID) -> LegalCase {
        guard let context = modelContext else {
            return LegalCase(title: "未知案件", category: .other)
        }
        let descriptor = FetchDescriptor<LegalCase>(
            predicate: #Predicate { $0.id == id }
        )
        return (try? context.fetch(descriptor).first) ?? LegalCase(title: "未知案件", category: .other)
    }
    
    private func getNetworkStatus() -> String {
        // 簡化實作
        return "wifi"
    }
    
    private func mapDetectionToReason(_ source: DetectionSource) -> EmergencyReason {
        switch source {
        case .voiceKeyword: return .voiceDistressDetected
        case .sensorAnomaly: return .sensorDistressPattern
        case .repeatedEmergencyButton: return .repeatedEmergencySignals
        case .appInactivity: return .prolongedInactivity
        }
    }
}

// MARK: - 資料結構

enum EmergencyStatus: String {
    case idle = "待機"
    case collecting = "收集資料中"
    case humanReviewPending = "等待人員審查"
    case contactingUser = "聯繫用戶確認中"
    case awaitingUserInput = "等待用戶補充資訊"
    case executingReferral = "執行轉介中"
    case completed = "已完成"
    case rejected = "已駁回"
}

enum EmergencyReason: String {
    case userInitiated = "用戶主動求助"
    case voiceDistressDetected = "求救語音偵測"
    case sensorDistressPattern = "感測器異常模式"
    case repeatedEmergencySignals = "重複緊急訊號"
    case prolongedInactivity = "長時間無活動"
}

enum DetectionSource: String {
    case voiceKeyword = "語音關鍵詞"
    case sensorAnomaly = "感測器異常"
    case repeatedEmergencyButton = "重複緊急按鈕"
    case appInactivity = "App 無活動"
}

enum UserAlertChoice {
    case confirmNeedHelp
    case falseAlarm
    case snooze
}

enum ReviewerDecision: String {
    case approveWithContact = "通過，先聯繫用戶確認"
    case approveImmediate = "緊急通過，立即轉介"
    case requestMoreInfo = "需要更多資訊"
    case reject = "駁回"
}

enum ReferralRecipient: String, Codable {
    case police = "警察"
    case childConsultationCenter = "兒童相談所 / 社會局"
    case domesticViolenceSupportCenter = "家暴支援中心"
    case designatedNGO = "指定 NGO"
    case designatedLawyer = "指定律師"
    case trustedContact = "緊急聯繫人"
}

enum EscalationError: Error, LocalizedError {
    case consentNotGranted
    case consentMissing
    case snapshotMissing
    case recordNotFound
    case referralFailed
    case submissionFailed
    
    var errorDescription: String? {
        switch self {
        case .consentNotGranted: return "您尚未簽署緊急轉介同意書。請先設定緊急聯繫資訊與轉介偏好。"
        case .consentMissing: return "轉介記錄缺少同意書快照，無法執行。"
        case .snapshotMissing: return "緊急快照遺失，無法建構通報資料。"
        case .recordNotFound: return "找不到對應的轉介記錄。"
        case .referralFailed: return "通報傳送失敗，請檢查網路連線。"
        case .submissionFailed: return "提交人員審查失敗。"
        }
    }
}

// MARK: - 模型

@Model
class EscalationRecord {
    @Attribute(.unique) var id: UUID
    var caseId: UUID
    var triggeredAt: Date
    var triggerType: String // EscalationTriggerType.rawValue
    var reason: String // EmergencyReason.rawValue
    var status: String // EmergencyStatus.rawValue
    var backendTicketId: String?
    var routedToPartnerName: String? // 合作夥伴名稱（如「東京都児童相談所」）
    var reviewedAt: Date?
    var reviewerDecision: String? // ReviewerDecision.rawValue
    var reviewerNotes: String?
    var completedAt: Date?
    
    // 關聯快照（儲存為 JSON Data）
    var snapshotData: Data?
    var consentSnapshotData: Data?
    
    init(id: UUID, caseId: UUID, triggeredAt: Date, triggerType: String,
         reason: String, snapshot: EmergencySnapshot? = nil,
         consentSnapshot: EmergencyConsent? = nil, status: String) {
        self.id = id
        self.caseId = caseId
        self.triggeredAt = triggeredAt
        self.triggerType = triggerType
        self.reason = reason
        self.status = status
        self.snapshotData = try? JSONEncoder().encode(snapshot)
        self.consentSnapshotData = try? JSONEncoder().encode(consentSnapshot)
    }
}

@Model
class EmergencyConsent {
    @Attribute(.unique) var id: UUID
    var caseId: UUID
    var createdAt: Date
    var isActive: Bool
    var revokedAt: Date?
    var version: String
    
    // 加密儲存的用戶身份
    var encryptedIdentityData: Data?
    var emergencyContactData: Data?
    
    // 資料分享偏好
    var includesLocation: Bool
    var includesContactInfo: Bool
    var includesEvidence: Bool
    
    // 轉介偏好
    var preferredRecipientsData: Data?
    var designatedNGOData: Data?
    var designatedLawyerData: Data?
    
    init(id: UUID, caseId: UUID, createdAt: Date, userIdentity: EncryptedUserIdentity,
         emergencyContact: EmergencyContactInfo?, includesLocation: Bool,
         includesContactInfo: Bool, includesEvidence: Bool,
         preferredRecipients: [ReferralRecipient], designatedNGO: NGOInfo? = nil,
         designatedLawyer: LawyerInfo? = nil, isActive: Bool, version: String) {
        self.id = id
        self.caseId = caseId
        self.createdAt = createdAt
        self.encryptedIdentityData = userIdentity.cipherData
        self.emergencyContactData = try? JSONEncoder().encode(emergencyContact)
        self.includesLocation = includesLocation
        self.includesContactInfo = includesContactInfo
        self.includesEvidence = includesEvidence
        self.preferredRecipientsData = try? JSONEncoder().encode(preferredRecipients)
        self.designatedNGOData = try? JSONEncoder().encode(designatedNGO)
        self.designatedLawyerData = try? JSONEncoder().encode(designatedLawyer)
        self.isActive = isActive
        self.version = version
    }
}

struct EmergencySnapshot: Codable {
    let collectedAt: Date
    let gpsLocation: CLLocationCoordinate2D?
    let deviceBattery: Float
    let networkStatus: String
    let lastEvidenceHash: String?
    let evidenceHashes: [String]
    let userContact: EmergencyContactInfo?
    let userDescription: String?
    let consentSnapshot: EmergencyConsent?
    
    var userName: String? {
        // 解密後取得
        return nil
    }
}

struct UserIdentity: Codable {
    let realName: String
    let phone: String
    let address: String?
    let dateOfBirth: Date?
}

struct EncryptedUserIdentity: Codable {
    let cipherData: Data
    let keyId: String
}

struct EmergencyContactInfo: Codable {
    let name: String
    let relationship: String
    let phone: String
}

struct NGOInfo: Codable {
    let name: String
    let contactPhone: String
    let contactEmail: String
}

struct LawyerInfo: Codable {
    let name: String
    let barAssociation: String
    let contactPhone: String
}

struct PoliceReportPackage: Codable {
    let reportId: String
    let timestamp: Date
    let location: CLLocationCoordinate2D?
    let reporterContact: EmergencyContactInfo?
    let evidenceSummary: [EvidenceSummary]
    let incidentDescription: String?
    let legalBasis: String
}

struct EvidenceSummary: Codable {
    let hash: String
    let type: String
    let timestamp: Date
}

struct HumanReviewPayload: Codable {
    let recordId: String
    let caseId: String
    let triggerType: String
    let reason: String
    let timestamp: Date
    let evidenceHashList: [String]
}

struct EscalationResult {
    let recordId: UUID
    let ticketId: String
    let message: String
    let estimatedResponseTime: TimeInterval
}

@Model
class SystemAlertRecord {
    @Attribute(.unique) var id: UUID
    var caseId: UUID
    var detectedAt: Date
    var source: String
    var confidence: Double
    var evidenceIdsData: Data?
    var status: String
    var dismissedAt: Date?
    var snoozeUntil: Date?
    
    init(id: UUID, caseId: UUID, detectedAt: Date, source: String,
         confidence: Double, evidenceIds: [UUID], status: String) {
        self.id = id
        self.caseId = caseId
        self.detectedAt = detectedAt
        self.source = source
        self.confidence = confidence
        self.evidenceIdsData = try? JSONEncoder().encode(evidenceIds)
        self.status = status
    }
}
