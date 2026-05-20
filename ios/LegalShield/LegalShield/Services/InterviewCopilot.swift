import Foundation
import Speech
import Combine

/// 防誘導取證 Copilot
/// 
/// 核心功能：
/// 1. 即時語音轉文字 (Speech framework)
/// 2. 誘導性問句偵測
/// 3. 即時紅燈警告 + 建議替代問句
/// 4. 錄音時自動標記「高風險提問」
///
/// 這是保護「童言童語」證據能力的關鍵防線
class InterviewCopilot: NSObject, ObservableObject {
    
    // MARK: - Published
    
    @Published var isListening: Bool = false
    @Published var transcript: String = ""
    @Published var currentWarning: Warning? = nil
    @Published var warningHistory: [Warning] = []
    @Published var sessionStats: SessionStats = SessionStats()
    
    // MARK: - 狀態
    
    private var speechRecognizer: SFSpeechRecognizer?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private let audioEngine = AVAudioEngine()
    
    private var cancellables = Set<AnyCancellable>()
    
    // MARK: - 誘導問句規則引擎
    
    private let leadingQuestionPatterns: [LeadingPattern] = [
        LeadingPattern(
            id: "direct_accusation",
            name: "直接指認",
            pattern: "(是不是|有沒有|難道)(.*)(老師|爸爸|媽媽|叔叔|阿姨)(.*)(你|摸|打|碰)",
            severity: .critical,
            explanation: "直接指認特定對象，屬於誘導性最強的問句類型",
            suggestion: "改問：『你可以告訴我，那時候發生了什麼事嗎？』"
        ),
        LeadingPattern(
            id: "yes_no_trap",
            name: "是非題陷阱",
            pattern: "^(是不是|有沒有|對不對|好不好|可以嗎)",
            severity: .high,
            explanation: "是非題限制了孩子的回答空間，容易產生順從性回答",
            suggestion: "改問：『你能描述一下那個畫面嗎？』"
        ),
        LeadingPattern(
            id: "emotion_suggestion",
            name: "情緒暗示",
            pattern: "(很痛|很可怕|很恐怖|很不舒服|被欺負)(.*)(對不對|是不是)",
            severity: .high,
            explanation: "將成人認定的情緒框架強加給孩子",
            suggestion: "改問：『那時候你的身體有什麼感覺？』"
        ),
        LeadingPattern(
            id: "location_suggestion",
            name: "地點暗示",
            pattern: "(是不是在|有沒有在)(.*)(教室|廁所|房間|小房間|角落)",
            severity: .medium,
            explanation: "暗示特定地點，可能誤導孩子的空間記憶",
            suggestion: "改問：『你記得那是在哪裡嗎？』"
        ),
        LeadingPattern(
            id: "action_suggestion",
            name: "動作暗示",
            pattern: "(是不是|有沒有)(.*)(摸|打|碰|脫|親)",
            severity: .critical,
            explanation: "暗示特定動作，這是法庭最忌諱的誘導類型",
            suggestion: "改問：『你可以用你自己的話告訴我嗎？』"
        ),
        LeadingPattern(
            id: "frequency_suggestion",
            name: "頻率暗示",
            pattern: "(很多次|經常|常常|每天|好幾次)(.*)(對不對|是不是)",
            severity: .medium,
            explanation: "暗示事件頻率，孩子可能為迎合而誇大",
            suggestion: "改問：『這種事情發生過幾次呢？』"
        ),
        LeadingPattern(
            id: "body_part_suggestion",
            name: "身體部位暗示",
            pattern: "(尿尿的地方|小雞雞|胸部|屁股|下面)(.*)(對不對|是不是|有沒有)",
            severity: .critical,
            explanation: "涉及性侵害案件時，直接提示身體部位會嚴重污染證詞",
            suggestion: "改問：『你可以指給我看是哪裡嗎？』（使用人形圖）"
        ),
    ]
    
    // MARK: - 初始化
    
    override init() {
        super.init()
        speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "zh-TW"))
        requestAuthorization()
    }
    
    // MARK: - 權限
    
    func requestAuthorization() {
        SFSpeechRecognizer.requestAuthorization { status in
            DispatchQueue.main.async {
                print("[Speech] Authorization status: \(status.rawValue)")
            }
        }
    }
    
    // MARK: - 開始/停止監聽
    
    func startListening() throws {
        guard !isListening else { return }
        
        // 重置狀態
        transcript = ""
        warningHistory = []
        currentWarning = nil
        sessionStats = SessionStats()
        
        // 設定 Audio Session
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement, options: .duckOthers)
        try session.setActive(true, options: .notifyOthersOnDeactivation)
        
        // 建立辨識請求
        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let request = recognitionRequest else {
            throw CopilotError.recognitionRequestFailed
        }
        request.shouldReportPartialResults = true
        
        // 開始辨識
        recognitionTask = speechRecognizer?.recognitionTask(with: request) { [weak self] result, error in
            guard let self = self else { return }
            
            if let result = result {
                let text = result.bestTranscription.formattedString
                self.transcript = text
                self.analyzeTranscript(text)
                self.sessionStats.totalWords += 1
            }
            
            if error != nil {
                self.stopListening()
            }
        }
        
        // 設定 Audio Engine
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, _ in
            self?.recognitionRequest?.append(buffer)
        }
        
        audioEngine.prepare()
        try audioEngine.start()
        
        isListening = true
        sessionStats.startTime = Date()
    }
    
    func stopListening() {
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionRequest = nil
        recognitionTask?.cancel()
        recognitionTask = nil
        isListening = false
        sessionStats.endTime = Date()
    }
    
    // MARK: - 誘導問句分析
    
    private func analyzeTranscript(_ text: String) {
        let lastSentence = extractLastSentence(from: text)
        
        for pattern in leadingQuestionPatterns {
            if matchesPattern(lastSentence, pattern: pattern.pattern) {
                let warning = Warning(
                    id: UUID(),
                    pattern: pattern,
                    detectedText: lastSentence,
                    timestamp: Date(),
                    transcriptIndex: text.count
                )
                
                currentWarning = warning
                warningHistory.append(warning)
                sessionStats.leadingQuestionCount += 1
                
                // 根據嚴重度統計
                switch pattern.severity {
                case .critical: sessionStats.criticalWarnings += 1
                case .high: sessionStats.highWarnings += 1
                case .medium: sessionStats.mediumWarnings += 1
                default: break
                }
                
                // 5 秒後清除當前警告 (保留歷史)
                DispatchQueue.main.asyncAfter(deadline: .now() + 5) { [weak self] in
                    if self?.currentWarning?.id == warning.id {
                        self?.currentWarning = nil
                    }
                }
                
                break  // 只顯示最嚴重的一個
            }
        }
    }
    
    private func extractLastSentence(from text: String) -> String {
        let separators = CharacterSet(charactersIn: "。！？.!?")
        let components = text.components(separatedBy: separators)
        return components.last?.trimmingCharacters(in: .whitespaces) ?? text
    }
    
    private func matchesPattern(_ text: String, pattern: String) -> Bool {
        do {
            let regex = try NSRegularExpression(pattern: pattern, options: [.caseInsensitive])
            let range = NSRange(text.startIndex..., in: text)
            return regex.firstMatch(in: text, options: [], range: range) != nil
        } catch {
            print("[Copilot] Regex error: \(error)")
            return false
        }
    }
    
    // MARK: - 生成報告
    
    func generateSessionReport() -> String {
        let duration = sessionStats.duration
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        
        return """
        📋 訪談品質報告
        =================
        訪談時長：\(minutes)分\(seconds)秒
        總字數：\(sessionStats.totalWords)
        誘導問句偵測：\(sessionStats.leadingQuestionCount) 次
        
        ⚠️ 風險分佈：
        🔴 危急：\(sessionStats.criticalWarnings)
        🟠 高風險：\(sessionStats.highWarnings)
        🟡 中風險：\(sessionStats.mediumWarnings)
        
        📝 建議：
        \(sessionStats.assessment)
        
        逐字稿：
        \(transcript)
        """
    }
}

// MARK: - 資料結構

struct LeadingPattern {
    let id: String
    let name: String
    let pattern: String
    let severity: WarningSeverity
    let explanation: String
    let suggestion: String
}

enum WarningSeverity: String {
    case critical = "critical"
    case high = "high"
    case medium = "medium"
    case low = "low"
    
    var color: String {
        switch self {
        case .critical: return "red"
        case .high: return "orange"
        case .medium: return "yellow"
        case .low: return "blue"
        }
    }
    
    var icon: String {
        switch self {
        case .critical: return "exclamationmark.octagon.fill"
        case .high: return "exclamationmark.triangle.fill"
        case .medium: return "exclamationmark.circle.fill"
        case .low: return "info.circle.fill"
        }
    }
}

struct Warning: Identifiable {
    let id: UUID
    let pattern: LeadingPattern
    let detectedText: String
    let timestamp: Date
    let transcriptIndex: Int
}

struct SessionStats {
    var startTime: Date?
    var endTime: Date?
    var totalWords: Int = 0
    var leadingQuestionCount: Int = 0
    var criticalWarnings: Int = 0
    var highWarnings: Int = 0
    var mediumWarnings: Int = 0
    
    var duration: TimeInterval {
        guard let start = startTime else { return 0 }
        let end = endTime ?? Date()
        return end.timeIntervalSince(start)
    }
    
    var assessment: String {
        if criticalWarnings > 0 {
            return "❌ 本次訪談包含 \(criticalWarnings) 個危急誘導問句。這些問句可能導致證詞被法庭排除。建議重新進行訪談。"
        } else if highWarnings > 2 {
            return "⚠️ 有 \(highWarnings) 個高風險問句。雖非致命，但對方律師可能會以此攻擊證詞可信度。"
        } else if leadingQuestionCount == 0 {
            return "✅ 本次訪談品質優秀！未偵測到誘導問句。這份逐字稿具備良好的證據能力。"
        } else {
            return "✅ 整體品質可接受。建議下次訪談時更注意開放式問句的使用。"
        }
    }
}

enum CopilotError: Error {
    case recognitionRequestFailed
    case notAuthorized
    
    var localizedDescription: String {
        switch self {
        case .recognitionRequestFailed: return "無法建立語音辨識請求"
        case .notAuthorized: return "沒有語音辨識權限"
        }
    }
}
