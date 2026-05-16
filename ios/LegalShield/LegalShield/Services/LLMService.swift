import Foundation
import Combine

/// LLM 服務 — 端側 + 雲端混合架構
/// 
/// 隱私原則：
/// - 敏感證據原始數據不上傳
/// - 僅上傳去識別化結構化 JSON
/// - 端側優先：意圖分類、簡易 QA
/// - 雲端：複雜分析、文書生成
class LLMService: ObservableObject {
    
    // MARK: - Published
    
    @Published var isProcessing: Bool = false
    @Published var lastResponse: String = ""
    @Published var lastError: String?
    
    // MARK: - 配置
    
    /// API 端點 (指向你的 Windows / EC2 伺服器)
    var apiEndpoint: String = "http://100.76.218.124:8000"  // Windows Ollama API
    var apiKey: String? = nil
    
    /// 模型選擇
    enum LLMModel: String {
        case phi4 = "phi4:14b"           // 快速推理
        case llama33 = "llama3.3:70b"   // 高精度
        case gemma3 = "gemma3:27b"      // 平衡
        case custom = "custom"           // 自訂端點
    }
    
    // MARK: - 公開方法
    
    /// 一般法務 QA (雲端 API)
    func legalQA(
        question: String,
        context: String? = nil,
        model: LLMModel = .phi4
    ) async throws -> String {
        isProcessing = true
        defer { isProcessing = false }
        
        let systemPrompt = """
        你是一名資深的日本與台灣法律研究助理。請根據以下原則回答：
        
        1. 僅基於事實與法條，不臆測
        2. 區分「確定法律」與「實務傾向」
        3. 提供具體法條號與判例參考
        4. 最後必須加上：「本回答僅供參考，具體法律行動請諮詢執業律師」
        """
        
        var userPrompt = question
        if let ctx = context {
            userPrompt = "【案情背景】\n\(ctx)\n\n【問題】\n\(question)"
        }
        
        return try await callOllamaAPI(
            model: model.rawValue,
            system: systemPrompt,
            user: userPrompt
        )
    }
    
    /// 證據分析報告生成 (結構化數據輸入)
    func analyzeEvidence(
        caseSummary: String,
        evidenceList: [Evidence],
        sensorAnomalies: [AnomalyLog]? = nil
    ) async throws -> AnalysisReport {
        isProcessing = true
        defer { isProcessing = false }
        
        // 構建去識別化結構化數據
        let evidenceData = evidenceList.map { e in
            [
                "type": e.type,
                "timestamp": e.createdAt.iso8601,
                "has_evidence_hash": !e.sha256Hash.isEmpty,
                "has_location": e.latitude != nil,
                "is_first_disclosure": e.isFirstDisclosure,
                "leading_question_detected": e.leadingQuestionCount
            ] as [String: Any]
        }
        
        let sensorData = sensorAnomalies?.map { a in
            [
                "type": a.sensorType,
                "severity": a.severity,
                "description": a.description
            ] as [String: Any]
        } ?? []
        
        let structuredInput: [String: Any] = [
            "case_summary": caseSummary,
            "evidence_count": evidenceList.count,
            "evidence": evidenceData,
            "sensor_anomalies": sensorData,
            "analysis_request": [
                "assess_strength": true,
                "identify_gaps": true,
                "recommend_actions": true,
                "estimate_win_probability": true
            ]
        ]
        
        let jsonData = try JSONSerialization.data(withJSONObject: structuredInput)
        let jsonString = String(data: jsonData, encoding: .utf8) ?? "{}"
        
        let systemPrompt = """
        你是一名冷酷的檢察官兼法醫行為學專家。請分析以下去識別化的案件數據結構。
        
        注意：你沒有看到任何原始證據內容（錄音、照片內容），僅有元數據與哈希值。
        你的分析僅基於：證據鏈完整性、時序邏輯、感測器異常模式。
        
        請輸出以下格式：
        1. 證據鏈完整性評估 (A-F 級)
        2. 時間軸邏輯分析
        3. 感測器異常關聯性
        4. 證據缺口識別
        5. 建議補強方向
        6. 綜合勝訴機率估計 (0-100%)
        7. 下一步行動清單
        """
        
        let response = try await callOllamaAPI(
            model: LLMModel.llama33.rawValue,
            system: systemPrompt,
            user: jsonString
        )
        
        return parseAnalysisReport(from: response)
    }
    
    /// 生成法律文書
    func generateDocument(
        templateType: DocumentTemplate,
        caseData: LegalCase,
        evidenceItems: [Evidence]
    ) async throws -> String {
        isProcessing = true
        defer { isProcessing = false }
        
        let systemPrompt = templateType.systemPrompt
        let userPrompt = buildDocumentPrompt(template: templateType, case: caseData, evidence: evidenceItems)
        
        return try await callOllamaAPI(
            model: LLMModel.llama33.rawValue,
            system: systemPrompt,
            user: userPrompt
        )
    }
    
    /// 端側簡易意圖分類 (本地模型或規則引擎)
    func classifyIntent(_ text: String) -> UserIntent {
        let lowercased = text.lowercased()
        
        if lowercased.contains("求救") || lowercased.contains("help") || lowercased.contains("110") {
            return .emergency
        }
        if lowercased.contains("證據") || lowercased.contains("拍照") || lowercased.contains("錄音") {
            return .evidence
        }
        if lowercased.contains("法律") || lowercased.contains("條文") || lowercased.contains("判例") {
            return .legal
        }
        if lowercased.contains("策略") || lowercased.contains("怎麼辦") || lowercased.contains("下一步") {
            return .strategy
        }
        if lowercased.contains("轉介") || lowercased.contains("社工") || lowercased.contains("律師") {
            return .referral
        }
        
        return .general
    }
    
    // MARK: - 私有 API 呼叫
    
    private func callOllamaAPI(
        model: String,
        system: String,
        user: String,
        temperature: Double = 0.3
    ) async throws -> String {
        let url = URL(string: "\(apiEndpoint)/api/generate")!
        
        let requestBody: [String: Any] = [
            "model": model,
            "system": system,
            "prompt": user,
            "stream": false,
            "options": [
                "temperature": temperature,
                "num_predict": 2048
            ]
        ]
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            let statusCode = (response as? HTTPURLResponse)?.statusCode ?? 0
            throw LLMError.apiError("HTTP \(statusCode)")
        }
        
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let result = json["response"] as? String else {
            throw LLMError.parseError
        }
        
        return result
    }
    
    // MARK: - 私有輔助方法
    
    private func parseAnalysisReport(from text: String) -> AnalysisReport {
        // 簡化解析：從回應中提取結構化數據
        var grade: String = "C"
        var winProbability: Double = 0.5
        
        if text.contains("A級") || text.contains("完整性評估：A") {
            grade = "A"
        } else if text.contains("B級") || text.contains("完整性評估：B") {
            grade = "B"
        }
        
        // 提取勝訴機率
        if let range = text.range(of: "機率.*?(\\d+)%", options: .regularExpression) {
            let match = text[range]
            if let num = Int(match.components(separatedBy: CharacterSet.decimalDigits.inverted).joined()) {
                winProbability = Double(num) / 100.0
            }
        }
        
        return AnalysisReport(
            rawResponse: text,
            evidenceGrade: grade,
            winProbability: winProbability,
            keyFindings: extractBulletPoints(from: text, section: "時間軸邏輯分析"),
            gaps: extractBulletPoints(from: text, section: "證據缺口識別"),
            recommendations: extractBulletPoints(from: text, section: "建議補強方向"),
            actionItems: extractBulletPoints(from: text, section: "下一步行動清單")
        )
    }
    
    private func extractBulletPoints(from text: String, section: String) -> [String] {
        // 簡化：找 section 後的項目
        guard let sectionRange = text.range(of: section) else { return [] }
        let afterSection = String(text[sectionRange.upperBound...])
        let lines = afterSection.components(separatedBy: .newlines)
        
        var bullets: [String] = []
        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            if trimmed.hasPrefix("-") || trimmed.hasPrefix("•") || trimmed.hasPrefix("1.") || trimmed.hasPrefix("2.") {
                bullets.append(trimmed.trimmingCharacters(in: CharacterSet(charactersIn: "-•1234567890. ")))
            }
            if bullets.count >= 5 { break }
        }
        return bullets
    }
    
    private func buildDocumentPrompt(
        template: DocumentTemplate,
        case: LegalCase,
        evidence: [Evidence]
    ) -> String {
        """
        案件標題：\(case.title)
        案件類型：\(case.caseCategory.displayName)
        當事人代號：\(case.victimAlias)
        案件年齡：\(case.victimAge.map(String.init) ?? "未知")
        機構名稱：\(case.institutionName ?? "未知")
        事件日期：\(case.incidentDate?.iso8601 ?? "未知")
        事件描述：\(case.incidentDescription ?? "未提供")
        
        證據摘要：
        \(evidence.map { "- [\($0.evidenceType.displayName)] \($0.createdAt.iso8601) (Hash: \($0.sha256Hash.prefix(16)))" }.joined(separator: "\n"))
        
        請根據以上資訊生成：\(template.displayName)
        """
    }
}

// MARK: - 用戶意圖

enum UserIntent {
    case emergency
    case evidence
    case legal
    case strategy
    case referral
    case general
}

// MARK: - 分析報告

struct AnalysisReport {
    let rawResponse: String
    let evidenceGrade: String       // A, B, C, D, E, F
    let winProbability: Double      // 0.0 ~ 1.0
    let keyFindings: [String]
    let gaps: [String]
    let recommendations: [String]
    let actionItems: [String]
    
    var formattedSummary: String {
        """
        📊 證據鏈完整性：\(evidenceGrade) 級
        🎯 勝訴機率估計：\(Int(winProbability * 100))%
        
        🔍 關鍵發現：
        \(keyFindings.map { "• \($0)" }.joined(separator: "\n"))
        
        ⚠️ 證據缺口：
        \(gaps.map { "• \($0)" }.joined(separator: "\n"))
        
        💡 建議補強：
        \(recommendations.map { "• \($0)" }.joined(separator: "\n"))
        
        📝 下一步行動：
        \(actionItems.map { "\($0)" }.joined(separator: "\n"))
        """
    }
}

// MARK: - 文書範本

enum DocumentTemplate: String {
    case policeReport = "police_report"
    case prosecutorComplaint = "prosecutor_complaint"
    case civilComplaint = "civil_complaint"
    case evidenceList = "evidence_list"
    case witnessInterviewPlan = "witness_interview_plan"
    case preparationDocument = "preparation_document"
    
    var displayName: String {
        switch self {
        case .policeReport: return "警察報案筆錄輔助"
        case .prosecutorComplaint: return "檢察官告發狀"
        case .civilComplaint: return "民事訴狀"
        case .evidenceList: return "證據清單"
        case .witnessInterviewPlan: return "證人訪談計畫"
        case .preparationDocument: return "準備書面"
        }
    }
    
    var systemPrompt: String {
        switch self {
        case .policeReport:
            return "你是一名資深刑警，請根據案情協助生成一份「有助於警方立案」的報案陳述輔助文稿。重點：客觀事實、時間軸清晰、法律依據明確。"
        case .prosecutorComplaint:
            return "你是一名檢察官，請根據證據鏈生成一份「檢察官難以拒絕受理」的刑事告發狀草稿。重點：構成要件分析、證據對應、求刑建議。"
        case .civilComplaint:
            return "你是一名專精侵權訴訟的律師，請生成民事訴狀草稿。重點：損害賠償計算、過失比例、證據清單。"
        case .evidenceList:
            return "你是一名證據整理專家，請將所有證據按時間序排列，標註證據能力與證明力。"
        case .witnessInterviewPlan:
            return "你是一名檢察事務官，請針對證人設計訪談計畫。重點：開放式問題、誘導問題避免、交叉詰問預演。"
        case .preparationDocument:
            return "你是一名訴訟律師，請生成準備書面。重點：爭點整理、證據說明、法律見解。"
        }
    }
}

// MARK: - 錯誤

enum LLMError: Error {
    case apiError(String)
    case parseError
    case noEndpointConfigured
    
    var localizedDescription: String {
        switch self {
        case .apiError(let msg): return "API 錯誤: \(msg)"
        case .parseError: return "解析回應失敗"
        case .noEndpointConfigured: return "未設定 API 端點"
        }
    }
}
