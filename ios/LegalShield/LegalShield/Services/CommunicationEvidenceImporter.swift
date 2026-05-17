import Foundation
import UIKit
import Vision
import SwiftData

/// 通訊記錄證據匯入器
/// 支援 LINE、Email、SMS、WhatsApp、Messenger 等截圖匯入
/// 本地 OCR 提取對話文字 → 自動偵測威脅關鍵詞 → 儲存為 Evidence
class CommunicationEvidenceImporter {
    
    private let modelContext: ModelContext
    private let evidenceManager: EvidenceManager
    
    init(context: ModelContext, evidenceManager: EvidenceManager) {
        self.modelContext = context
        self.evidenceManager = evidenceManager
    }
    
    // MARK: - 主要入口
    
    /// 從 Share Sheet 接收截圖並處理
    func importScreenshot(
        image: UIImage,
        sourceApp: CommunicationSourceApp,
        caseId: UUID
    ) async throws -> CommunicationImportResult {
        
        // 1. 圖片本身 SHA-256
        guard let imageData = image.pngData() else {
            throw CommunicationImportError.imageEncodingFailed
        }
        let imageHash = Evidence.computeSHA256(for: imageData)
        
        // 2. 本地 OCR 提取文字
        let recognizedText = try await performLocalOCR(on: image)
        
        // 3. 解析對話結構
        let parsedMessages = parseConversation(text: recognizedText, sourceApp: sourceApp)
        
        // 4. 威脅關鍵詞偵測
        let threatResult = detectThreatKeywords(in: recognizedText)
        
        // 5. 儲存截圖證據
        let screenshotEvidence = try await saveScreenshotEvidence(
            imageData: imageData,
            hash: imageHash,
            caseId: caseId,
            sourceApp: sourceApp
        )
        
        // 6. 儲存結構化通訊記錄（作為 transcript 類型證據）
        let transcriptEvidence = try saveTranscriptEvidence(
            parsedMessages: parsedMessages,
            rawText: recognizedText,
            caseId: caseId,
            sourceApp: sourceApp,
            threatResult: threatResult
        )
        
        // 7. 如果有威脅，提升案件緊急等級
        if threatResult.hasThreat {
            await escalateCaseUrgency(caseId: caseId, threatResult: threatResult)
        }
        
        return CommunicationImportResult(
            screenshotEvidence: screenshotEvidence,
            transcriptEvidence: transcriptEvidence,
            threatResult: threatResult,
            parsedMessages: parsedMessages
        )
    }
    
    // MARK: - OCR 處理
    
    /// 使用 Vision 框架本地執行 OCR（不上傳）
    private func performLocalOCR(on image: UIImage) async throws -> String {
        guard let cgImage = image.cgImage else {
            throw CommunicationImportError.imageProcessingFailed
        }
        
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["zh-Hant", "ja", "en"] // 繁體中文、日文、英文
        request.usesLanguageCorrection = true
        
        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        try handler.perform([request])
        
        guard let observations = request.results as? [VNRecognizedTextObservation] else {
            return ""
        }
        
        let text = observations.compactMap { observation in
            observation.topCandidates(1).first?.string
        }.joined(separator: "\n")
        
        return text
    }
    
    // MARK: - 對話解析
    
    /// 根據不同 App 的格式解析對話
    private func parseConversation(
        text: String,
        sourceApp: CommunicationSourceApp
    ) -> [ParsedMessage] {
        let lines = text.components(separatedBy: .newlines)
        var messages: [ParsedMessage] = []
        
        for line in lines {
            guard let parsed = parseLine(line, for: sourceApp) else { continue }
            messages.append(parsed)
        }
        
        return messages
    }
    
    /// 逐行解析（依 App 格式不同）
    private func parseLine(_ line: String, for sourceApp: CommunicationSourceApp) -> ParsedMessage? {
        switch sourceApp {
        case .line:
            // LINE 格式範例：「12:34 田中さん こんにちは」或「12:34 已讀」
            return parseLINELine(line)
        case .email:
            return parseEmailLine(line)
        case .sms, .whatsapp, .messenger, .slack:
            // 通用格式：時間 + 發送者 + 內容
            return parseGenericLine(line)
        }
    }
    
    private func parseLINELine(_ line: String) -> ParsedMessage? {
        // 簡化解析：尋找時間模式 + 發送者 + 內容
        let timePattern = #"(\d{1,2}:\d{2})"#
        guard let timeMatch = line.range(of: timePattern, options: .regularExpression) else {
            return nil
        }
        let time = String(line[timeMatch])
        let remaining = String(line[timeMatch.upperBound...]).trimmingCharacters(in: .whitespaces)
        
        // 區分「發送者: 內容」和系統訊息
        if remaining.contains(": ") || remaining.contains("：") {
            let parts = remaining.components(separatedBy: CharacterSet(charactersIn: ":："))
            if parts.count >= 2 {
                return ParsedMessage(
                    timestamp: time,
                    sender: parts[0].trimmingCharacters(in: .whitespaces),
                    text: parts[1...].joined(separator: ": ").trimmingCharacters(in: .whitespaces),
                    isSystemMessage: false
                )
            }
        }
        
        return ParsedMessage(
            timestamp: time,
            sender: "未知",
            text: remaining,
            isSystemMessage: false
        )
    }
    
    private func parseEmailLine(_ line: String) -> ParsedMessage? {
        // Email 格式較複雜，簡化處理
        return ParsedMessage(
            timestamp: "",
            sender: "Email",
            text: line,
            isSystemMessage: false
        )
    }
    
    private func parseGenericLine(_ line: String) -> ParsedMessage? {
        // 通用解析：尋找時間 + 內容
        let timePattern = #"(\d{1,2}:\d{2})"#
        if let timeMatch = line.range(of: timePattern, options: .regularExpression) {
            let time = String(line[timeMatch])
            let text = String(line[timeMatch.upperBound...]).trimmingCharacters(in: .whitespaces)
            return ParsedMessage(timestamp: time, sender: "未知", text: text, isSystemMessage: false)
        }
        return ParsedMessage(timestamp: "", sender: "未知", text: line, isSystemMessage: false)
    }
    
    // MARK: - 威脅偵測
    
    /// 本地偵測威脅關鍵詞（不上傳）
    func detectThreatKeywords(in text: String) -> ThreatDetectionResult {
        let lowercasedText = text.lowercased()
        var detectedKeywords: [String] = []
        var threatCategories: [ThreatCategory] = []
        
        // 物理暴力
        let physicalKeywords = ["殺す", "殺して", "殴る", "殴って", "死ね", "kill", "beat"]
        for keyword in physicalKeywords {
            if lowercasedText.contains(keyword) {
                detectedKeywords.append(keyword)
                if !threatCategories.contains(.physicalViolence) {
                    threatCategories.append(.physicalViolence)
                }
            }
        }
        
        // 性脅迫
        let sexualKeywords = ["写真", "公開", "ばらす", "裸", "sex", "nude", "公開する"]
        for keyword in sexualKeywords {
            if lowercasedText.contains(keyword) {
                detectedKeywords.append(keyword)
                if !threatCategories.contains(.sexualCoercion) {
                    threatCategories.append(.sexualCoercion)
                }
            }
        }
        
        // 名譽毀損
        let reputationKeywords = ["会社", "学校", "知らせる", "言いふらす", "暴露", "spread"]
        for keyword in reputationKeywords {
            if lowercasedText.contains(keyword) {
                detectedKeywords.append(keyword)
                if !threatCategories.contains(.reputationalDamage) {
                    threatCategories.append(.reputationalDamage)
                }
            }
        }
        
        // 經濟脅迫
        let economicKeywords = ["給料", "賃金", "減らす", "払わない", "解雇", "fire", "salary"]
        for keyword in economicKeywords {
            if lowercasedText.contains(keyword) {
                detectedKeywords.append(keyword)
                if !threatCategories.contains(.economicCoercion) {
                    threatCategories.append(.economicCoercion)
                }
            }
        }
        
        // 跟蹤騷擾
        let stalkingKeywords = ["待ち伏せ", "待つ", "つけて", "監視", "stalk", "follow"]
        for keyword in stalkingKeywords {
            if lowercasedText.contains(keyword) {
                detectedKeywords.append(keyword)
                if !threatCategories.contains(.stalkingBehavior) {
                    threatCategories.append(.stalkingBehavior)
                }
            }
        }
        
        let hasThreat = !detectedKeywords.isEmpty
        let threatLevel = calculateThreatLevel(categories: threatCategories, keywordCount: detectedKeywords.count)
        
        return ThreatDetectionResult(
            hasThreat: hasThreat,
            keywords: detectedKeywords,
            threatCategories: threatCategories,
            threatLevel: threatLevel,
            recommendedAction: threatLevel.recommendedAction
        )
    }
    
    private func calculateThreatLevel(categories: [ThreatCategory], keywordCount: Int) -> ThreatLevel {
        if categories.contains(.physicalViolence) || categories.contains(.sexualCoercion) {
            return .critical
        }
        if categories.count >= 2 || keywordCount >= 3 {
            return .high
        }
        if categories.count == 1 {
            return .medium
        }
        return .low
    }
    
    // MARK: - 儲存
    
    private func saveScreenshotEvidence(
        imageData: Data,
        hash: String,
        caseId: UUID,
        sourceApp: CommunicationSourceApp
    ) async throws -> Evidence {
        let fileName = "comm_\(sourceApp.rawValue)_\(Date().iso8601).png"
        let filePath = try await evidenceManager.saveEncrypted(data: imageData, fileName: fileName)
        
        let evidence = Evidence(
            caseId: caseId,
            type: .screenshot,
            fileName: fileName,
            filePath: filePath,
            fileSize: imageData.count,
            sha256Hash: hash,
            previousHash: nil,
            chainIndex: 0 // 由 EvidenceManager 更新
        )
        
        evidence.notes = "來源: \(sourceApp.displayName)"
        evidence.tags = [sourceApp.rawValue, "communication"]
        
        modelContext.insert(evidence)
        try modelContext.save()
        
        return evidence
    }
    
    private func saveTranscriptEvidence(
        parsedMessages: [ParsedMessage],
        rawText: String,
        caseId: UUID,
        sourceApp: CommunicationSourceApp,
        threatResult: ThreatDetectionResult
    ) throws -> Evidence {
        let transcriptData = try JSONEncoder().encode(parsedMessages)
        let hash = Evidence.computeSHA256(for: transcriptData)
        let fileName = "transcript_\(sourceApp.rawValue)_\(Date().iso8601).json"
        let filePath = try evidenceManager.saveEncrypted(data: transcriptData, fileName: fileName).get()
        
        let evidence = Evidence(
            caseId: caseId,
            type: .transcript,
            fileName: fileName,
            filePath: filePath,
            fileSize: transcriptData.count,
            sha256Hash: hash,
            previousHash: nil,
            chainIndex: 0
        )
        
        evidence.transcript = rawText
        evidence.notes = "\(sourceApp.displayName) 對話記錄。威脅偵測: \(threatResult.hasThreat ? "有" : "無")"
        evidence.tags = [sourceApp.rawValue, "transcript", threatResult.hasThreat ? "threat_detected" : "safe"]
        
        modelContext.insert(evidence)
        try modelContext.save()
        
        return evidence
    }
    
    // MARK: - 案件緊急度提升
    
    private func escalateCaseUrgency(caseId: UUID, threatResult: ThreatDetectionResult) async {
        let descriptor = FetchDescriptor<LegalCase>(
            predicate: #Predicate { $0.id == caseId }
        )
        guard let caseItem = try? modelContext.fetch(descriptor).first else { return }
        
        // 如果偵測到嚴重威脅，提升緊急等級
        if threatResult.threatLevel == .critical || threatResult.threatLevel == .high {
            caseItem.urgency = UrgencyLevel.critical.rawValue
            caseItem.updatedAt = Date()
            try? modelContext.save()
            
            // 發送本地通知提醒用戶
            // 可選：自動觸發緊急轉介（如果用戶已簽署同意書）
        }
    }
}

// MARK: - 資料結構

enum CommunicationSourceApp: String, Codable, CaseIterable {
    case line = "line"
    case email = "email"
    case sms = "sms"
    case whatsapp = "whatsapp"
    case messenger = "messenger"
    case slack = "slack"
    
    var displayName: String {
        switch self {
        case .line: return "LINE"
        case .email: return "Email"
        case .sms: return "SMS/iMessage"
        case .whatsapp: return "WhatsApp"
        case .messenger: return "Messenger"
        case .slack: return "Slack"
        }
    }
}

struct ParsedMessage: Codable {
    let timestamp: String
    let sender: String
    let text: String
    let isSystemMessage: Bool
}

enum ThreatCategory: String, Codable {
    case physicalViolence = "physical_violence"      // 刑法 222 条 脅迫罪
    case sexualCoercion = "sexual_coercion"          // 刑法 222 条 + 性的脅迫
    case reputationalDamage = "reputational_damage"    // 名譽毀損
    case economicCoercion = "economic_coercion"      // 労基法違反
    case stalkingBehavior = "stalking_behavior"      // ストーカー規制法
}

enum ThreatLevel: String, Codable {
    case low = "low"
    case medium = "medium"
    case high = "high"
    case critical = "critical"
    
    var recommendedAction: String {
        switch self {
        case .low:
            return "建議保存證據，持續觀察"
        case .medium:
            return "建議諮詢法律專業人士，考慮申請保護令"
        case .high:
            return "建議立即報警或聯繫支援機構，避免單獨接觸對方"
        case .critical:
            return "緊急：建議立即使用緊急轉介功能，或撥打 110/児童相談所"
        }
    }
}

struct ThreatDetectionResult {
    let hasThreat: Bool
    let keywords: [String]
    let threatCategories: [ThreatCategory]
    let threatLevel: ThreatLevel
    let recommendedAction: String
}

struct CommunicationImportResult {
    let screenshotEvidence: Evidence
    let transcriptEvidence: Evidence
    let threatResult: ThreatDetectionResult
    let parsedMessages: [ParsedMessage]
}

enum CommunicationImportError: Error, LocalizedError {
    case imageEncodingFailed
    case imageProcessingFailed
    case ocrFailed
    case saveFailed
    
    var errorDescription: String? {
        switch self {
        case .imageEncodingFailed: return "圖片編碼失敗"
        case .imageProcessingFailed: return "圖片處理失敗"
        case .ocrFailed: return "文字識別失敗"
        case .saveFailed: return "儲存失敗"
        }
    }
}
