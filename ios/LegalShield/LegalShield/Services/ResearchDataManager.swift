import Foundation
import CryptoKit

/// 研究數據管理器 — 研究-產品-補助閉環的核心引擎
///
/// 設計原則：
/// 1. 原始敏感數據永不離開裝置
/// 2. 上傳的僅為差分隱私 (Differential Privacy) 處理後的統計數據
/// 3. 需經 IRB (研究倫理委員會) 審查通過後，才能開啟上傳功能
/// 4. 所有上傳數據使用獨立金鑰對稱加密，與證據金鑰分離
class ResearchDataManager: ObservableObject {
    
    // MARK: - Published
    
    @Published var isIRBApproved: Bool = false
    @Published var lastUploadDate: Date?
    @Published var pendingUploadCount: Int = 0
    
    // MARK: - 配置
    
    /// IRB 審查狀態 (由遠端伺服器簽發的 JWT)
    var irbToken: String?
    
    /// 差分隱私參數 ε (越小隱私越強，但數據效用越低)
    /// 學術慣例：ε = 1.0 (強隱私) 到 ε = 10.0 (弱隱私)
    var epsilon: Double = 1.0
    
    /// 研究 API 端點 (獨立於 LLM API，更高安全等級)
    var researchEndpoint: String = "https://research.legalshield.jp/api/v1"
    
    // MARK: - 本地儲存
    
    private let localStatsKey = "com.legalshield.research.localstats"
    private let uploadQueueKey = "com.legalshield.research.queue"
    
    /// 本地累積的原始統計數據 (尚未 DP 處理)
    private var localRawStats: [ResearchStatRecord] = []
    
    // MARK: - 初始化
    
    init() {
        loadLocalStats()
        checkIRBStatus()
    }
    
    // MARK: - 數據收集 (產品端呼叫)
    
    /// 記錄一次「案件建立」事件
    func recordCaseCreation(
        category: CaseCategory,
        urgency: UrgencyLevel,
        hasFirstDisclosure: Bool
    ) {
        let record = ResearchStatRecord(
            timestamp: Date(),
            eventType: .caseCreated,
            caseCategory: category,
            urgencyLevel: urgency,
            hasFirstDisclosure: hasFirstDisclosure,
            evidenceCount: 0,
            leadingQuestionCount: nil,
            sensorType: nil
        )
        localRawStats.append(record)
        saveLocalStats()
    }
    
    /// 記錄一次「訪談完成」事件
    func recordInterviewCompleted(
        category: CaseCategory,
        duration: TimeInterval,
        leadingQuestionCount: Int,
        criticalWarnings: Int,
        transcriptLength: Int
    ) {
        let record = ResearchStatRecord(
            timestamp: Date(),
            eventType: .interviewCompleted,
            caseCategory: category,
            duration: duration,
            leadingQuestionCount: leadingQuestionCount,
            criticalWarnings: criticalWarnings,
            transcriptLength: transcriptLength
        )
        localRawStats.append(record)
        saveLocalStats()
    }
    
    /// 記錄一次「感測器異常」事件
    func recordSensorAnomaly(
        sensorType: SensorType,
        severity: AnomalySeverity,
        deviceCategory: String
    ) {
        let record = ResearchStatRecord(
            timestamp: Date(),
            eventType: .sensorAnomaly,
            sensorType: sensorType,
            anomalySeverity: severity,
            deviceCategory: deviceCategory
        )
        localRawStats.append(record)
        saveLocalStats()
    }
    
    /// 記錄一次「證據採集」事件
    func recordEvidenceCaptured(
        evidenceType: EvidenceType,
        hasLocation: Bool,
        fileSize: Int
    ) {
        let record = ResearchStatRecord(
            timestamp: Date(),
            eventType: .evidenceCaptured,
            evidenceType: evidenceType,
            hasLocation: hasLocation,
            fileSizeBucket: bucketFileSize(fileSize)
        )
        localRawStats.append(record)
        saveLocalStats()
    }
    
    /// 記錄一次「AI 分析完成」事件
    func recordAIAnalysisCompleted(
        category: CaseCategory,
        evidenceGrade: String,
        winProbability: Double
    ) {
        let record = ResearchStatRecord(
            timestamp: Date(),
            eventType: .aiAnalysisCompleted,
            caseCategory: category,
            evidenceGrade: evidenceGrade,
            winProbability: winProbability
        )
        localRawStats.append(record)
        saveLocalStats()
    }
    
    // MARK: - 差分隱私處理
    
    /// 將原始統計數據轉為差分隱私統計包
    ///
    /// 機制：
    /// 1. 分組聚合 (按週、按案件類型)
    /// 2. 對每個計數加入 Laplace noise
    /// 3. 截斷極端值 (防止負數或過大值)
    func generateDifferentialPrivacyPackage() -> ResearchUploadPackage? {
        guard !localRawStats.isEmpty else { return nil }
        
        let calendar = Calendar.current
        let now = Date()
        
        // 只取最近 7 天的數據
        let cutoff = calendar.date(byAdding: .day, value: -7, to: now)!
        let recentStats = localRawStats.filter { $0.timestamp >= cutoff }
        
        // 按案件類型分組聚合
        var categoryCounts: [String: Int] = [:]
        var interviewStats: [String: (count: Int, avgLeading: Double, avgDuration: Double)] = [:]
        var anomalyCounts: [String: Int] = [:]
        var evidenceTypeCounts: [String: Int] = [:]
        var aiGradeDistribution: [String: Int] = [:]
        
        for stat in recentStats {
            // 案件類型分布
            if let category = stat.caseCategory {
                let key = category.rawValue
                categoryCounts[key, default: 0] += 1
            }
            
            // 訪談統計
            if stat.eventType == .interviewCompleted, let category = stat.caseCategory {
                let key = category.rawValue
                var existing = interviewStats[key] ?? (count: 0, avgLeading: 0, avgDuration: 0)
                existing.count += 1
                existing.avgLeading = (existing.avgLeading * Double(existing.count - 1) + Double(stat.leadingQuestionCount ?? 0)) / Double(existing.count)
                existing.avgDuration = (existing.avgDuration * Double(existing.count - 1) + (stat.duration ?? 0)) / Double(existing.count)
                interviewStats[key] = existing
            }
            
            // 感測器異常
            if stat.eventType == .sensorAnomaly, let type = stat.sensorType {
                let key = type.rawValue
                anomalyCounts[key, default: 0] += 1
            }
            
            // 證據類型
            if stat.eventType == .evidenceCaptured, let type = stat.evidenceType {
                let key = type.rawValue
                evidenceTypeCounts[key, default: 0] += 1
            }
            
            // AI 評分分佈
            if stat.eventType == .aiAnalysisCompleted, let grade = stat.evidenceGrade {
                aiGradeDistribution[grade, default: 0] += 1
            }
        }
        
        // 加入 Laplace noise
        let noisyCategoryCounts = categoryCounts.mapValues { addLaplaceNoise(count: $0, epsilon: epsilon) }
        let noisyAnomalyCounts = anomalyCounts.mapValues { addLaplaceNoise(count: $0, epsilon: epsilon) }
        let noisyEvidenceCounts = evidenceTypeCounts.mapValues { addLaplaceNoise(count: $0, epsilon: epsilon) }
        let noisyGradeDistribution = aiGradeDistribution.mapValues { addLaplaceNoise(count: $0, epsilon: epsilon) }
        
        // 截斷 (防止負數)
        let safeCategory = noisyCategoryCounts.mapValues { max(0, $0) }
        let safeAnomaly = noisyAnomalyCounts.mapValues { max(0, $0) }
        let safeEvidence = noisyEvidenceCounts.mapValues { max(0, $0) }
        let safeGrade = noisyGradeDistribution.mapValues { max(0, $0) }
        
        return ResearchUploadPackage(
            uploadId: UUID().uuidString,
            generatedAt: now,
            weekStarting: calendar.startOfWeek(for: now),
            epsilon: epsilon,
            totalRecords: recentStats.count,
            deviceCountry: Locale.current.region?.identifier ?? "JP",
            categoryDistribution: safeCategory,
            interviewStatistics: interviewStats.mapValues {
                InterviewDPStat(
                    sampleCount: max(0, addLaplaceNoise(count: $0.count, epsilon: epsilon)),
                    avgLeadingQuestions: $0.avgLeading,
                    avgDurationMinutes: $0.avgDuration / 60.0
                )
            },
            sensorAnomalyDistribution: safeAnomaly,
            evidenceTypeDistribution: safeEvidence,
            aiGradeDistribution: safeGrade
        )
    }
    
    // MARK: - 上傳
    
    /// 上傳差分隱私統計包到研究伺服器
    func uploadResearchData() async throws {
        guard isIRBApproved else {
            throw ResearchError.irbNotApproved
        }
        
        guard let package = generateDifferentialPrivacyPackage() else {
            throw ResearchError.noDataToUpload
        }
        
        let jsonData = try JSONEncoder().encode(package)
        
        // 用研究金鑰加密 (與證據金鑰不同)
        let encryptedData = try encryptForResearch(jsonData)
        
        var request = URLRequest(url: URL(string: "\(researchEndpoint)/upload")!)
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(irbToken ?? "")", forHTTPHeaderField: "Authorization")
        request.httpBody = encryptedData
        
        let (_, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw ResearchError.uploadFailed
        }
        
        // 上傳成功，清除已處理的原始數據
        lastUploadDate = Date()
        clearProcessedStats(upTo: package.generatedAt)
    }
    
    // MARK: - 差分隱私工具
    
    /// Laplace 機制：加入 Laplace(0, 1/ε) 雜訊
    private func addLaplaceNoise(count: Int, epsilon: Double) -> Int {
        let scale = 1.0 / epsilon
        let u = Double.random(in: -0.5...0.5)
        let noise = -scale * sign(u) * log(1 - 2 * abs(u))
        return count + Int(round(noise))
    }
    
    private func sign(_ value: Double) -> Double {
        value >= 0 ? 1.0 : -1.0
    }
    
    /// 檔案大小分桶 (避免洩露精確大小)
    private func bucketFileSize(_ size: Int) -> String {
        switch size {
        case 0..<1_000_000: return "small"
        case 1_000_000..<10_000_000: return "medium"
        case 10_000_000..<100_000_000: return "large"
        default: return "very_large"
        }
    }
    
    // MARK: - 加密
    
    private func encryptForResearch(_ data: Data) throws -> Data {
        let key = try getOrCreateResearchKey()
        let sealedBox = try AES.GCM.seal(data, using: key)
        return sealedBox.combined!
    }
    
    private func getOrCreateResearchKey() throws -> SymmetricKey {
        let keyTag = "com.legalshield.research.key"
        if let existingData = KeychainHelper.load(key: keyTag) {
            return SymmetricKey(data: existingData)
        }
        let newKey = SymmetricKey(size: .bits256)
        let keyData = newKey.withUnsafeBytes { Data($0) }
        try KeychainHelper.save(key: keyTag, data: keyData)
        return newKey
    }
    
    // MARK: - 本地儲存管理
    
    private func loadLocalStats() {
        guard let data = UserDefaults.standard.data(forKey: localStatsKey),
              let stats = try? JSONDecoder().decode([ResearchStatRecord].self, from: data) else {
            localRawStats = []
            return
        }
        localRawStats = stats
    }
    
    private func saveLocalStats() {
        if let data = try? JSONEncoder().encode(localRawStats) {
            UserDefaults.standard.set(data, forKey: localStatsKey)
        }
    }
    
    private func clearProcessedStats(upTo date: Date) {
        localRawStats.removeAll { $0.timestamp <= date }
        saveLocalStats()
    }
    
    private func checkIRBStatus() {
        // 從 Keychain 讀取 IRB token，檢查是否過期
        if let tokenData = KeychainHelper.load(key: "com.legalshield.research.irb_token"),
           let token = String(data: tokenData, encoding: .utf8),
           !token.isEmpty {
            irbToken = token
            isIRBApproved = true
        }
    }
    
    // MARK: - 公開查詢
    
    /// 取得本地累積的統計摘要 (供研究儀表板預覽)
    func getLocalSummary() -> String {
        let totalCases = localRawStats.filter { $0.eventType == .caseCreated }.count
        let totalInterviews = localRawStats.filter { $0.eventType == .interviewCompleted }.count
        let totalAnomalies = localRawStats.filter { $0.eventType == .sensorAnomaly }.count
        let totalEvidence = localRawStats.filter { $0.eventType == .evidenceCaptured }.count
        
        return """
        本地累積統計：
        • 案件建立：\(totalCases)
        • 訪談完成：\(totalInterviews)
        • 感測器異常：\(totalAnomalies)
        • 證據採集：\(totalEvidence)
        
        IRB 狀態：\(isIRBApproved ? "✅ 已審查通過" : "⏳ 等待審查")
        """
    }
}

// MARK: - 資料結構

struct ResearchStatRecord: Codable {
    let timestamp: Date
    let eventType: ResearchEventType
    
    // 案件相關
    var caseCategory: CaseCategory?
    var urgencyLevel: UrgencyLevel?
    var hasFirstDisclosure: Bool?
    var evidenceCount: Int?
    
    // 訪談相關
    var duration: TimeInterval?
    var leadingQuestionCount: Int?
    var criticalWarnings: Int?
    var transcriptLength: Int?
    
    // 感測器相關
    var sensorType: SensorType?
    var anomalySeverity: AnomalySeverity?
    var deviceCategory: String?
    
    // 證據相關
    var evidenceType: EvidenceType?
    var hasLocation: Bool?
    var fileSizeBucket: String?
    
    // AI 分析相關
    var evidenceGrade: String?
    var winProbability: Double?
}

enum ResearchEventType: String, Codable {
    case caseCreated
    case interviewCompleted
    case sensorAnomaly
    case evidenceCaptured
    case aiAnalysisCompleted
}

struct ResearchUploadPackage: Codable {
    let uploadId: String
    let generatedAt: Date
    let weekStarting: Date
    let epsilon: Double
    let totalRecords: Int
    let deviceCountry: String
    
    let categoryDistribution: [String: Int]
    let interviewStatistics: [String: InterviewDPStat]
    let sensorAnomalyDistribution: [String: Int]
    let evidenceTypeDistribution: [String: Int]
    let aiGradeDistribution: [String: Int]
}

struct InterviewDPStat: Codable {
    let sampleCount: Int
    let avgLeadingQuestions: Double
    let avgDurationMinutes: Double
}

// MARK: - 錯誤

enum ResearchError: Error, LocalizedError {
    case irbNotApproved
    case noDataToUpload
    case uploadFailed
    case encryptionFailed
    
    var errorDescription: String? {
        switch self {
        case .irbNotApproved: return "研究倫理審查尚未通過，無法上傳數據"
        case .noDataToUpload: return "沒有可上傳的統計數據"
        case .uploadFailed: return "上傳失敗，請檢查網路連線"
        case .encryptionFailed: return "加密失敗"
        }
    }
}

// MARK: - Calendar Extension

extension Calendar {
    func startOfWeek(for date: Date) -> Date {
        var components = dateComponents([.yearForWeekOfYear, .weekOfYear], from: date)
        components.weekday = 1 // Sunday
        return self.date(from: components) ?? date
    }
}
