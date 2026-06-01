import Foundation
import AVFoundation
#if canImport(WhisperKit)
import WhisperKit
#endif

/// 多国語対応の音声 → テキスト サービス
///
/// **WhisperKit** ベース（argmaxinc/WhisperKit）で 99 言語対応・自動言語判定。
/// `InterviewCopilot` の `SFSpeechRecognizer`（Apple 内蔵、地域別ロケール固定）の代替。
///
/// ## 使い分け方針
/// - **InterviewCopilot（Apple Speech）**：低レイテンシ・短文・特定 1 言語のみ
/// - **WhisperKitTranscriber**：長文・多言語・録音ファイル全体の高精度書き起こし
///
/// ## モデル選択指針（端末別）
/// | 機種 | モデル | サイズ | 特徴 |
/// |---|---|---|---|
/// | iPhone 12 以下 | tiny / base | 39〜74 MB | 即時、英語のみ高精度 |
/// | iPhone 13〜14 | small | 244 MB | 多言語・実用 |
/// | iPhone 15 / 15 Pro | medium / large-v3-turbo | 769 MB / 1.5 GB | 多言語・最高精度 |
///
/// ## ロード戦略
/// 初回起動時 background でモデル DL → Documents/whisper-models/ に置く。
/// 二回目以降はインスタント起動。
@MainActor
public final class WhisperKitTranscriber: ObservableObject {

    // MARK: - 公開状態

    public enum LoadState: Equatable {
        case unloaded
        case downloading(progress: Double)
        case loading
        case ready
        case failed(String)
    }

    @Published public private(set) var loadState: LoadState = .unloaded
    @Published public private(set) var isTranscribing: Bool = false
    @Published public private(set) var lastResult: TranscriptionResult?

    // MARK: - 設定

    /// 既定モデル：iPhone 15 Pro 以上は large-v3-turbo、それ以下は base（推奨）
    public static let defaultModelName = "openai_whisper-base"
    public static let highEndModelName = "openai_whisper-large-v3-turbo"

    public let modelName: String

    #if canImport(WhisperKit)
    private var pipe: WhisperKit?
    #endif

    public init(modelName: String = defaultModelName) {
        self.modelName = modelName
    }

    // MARK: - モデルロード

    public func loadModel() async {
        #if canImport(WhisperKit)
        guard !(loadState == .ready || loadState == .loading) else { return }
        loadState = .loading
        do {
            let config = WhisperKitConfig(model: modelName, verbose: false)
            self.pipe = try await WhisperKit(config)
            loadState = .ready
        } catch {
            loadState = .failed("\(error)")
        }
        #else
        loadState = .failed("WhisperKit not linked. Run xcodegen generate first.")
        #endif
    }

    // MARK: - 書き起こし

    /// 音声ファイル → テキスト。`languageHint` が nil の場合は自動判定。
    public func transcribe(
        audioURL: URL,
        languageHint: String? = nil,
        translateToEnglish: Bool = false
    ) async throws -> TranscriptionResult {
        #if canImport(WhisperKit)
        if loadState != .ready { await loadModel() }
        guard case .ready = loadState, let pipe = pipe else {
            throw TranscriberError.notReady
        }

        isTranscribing = true
        defer { isTranscribing = false }

        let opts = DecodingOptions(
            task: translateToEnglish ? .translate : .transcribe,
            language: languageHint,
            temperature: 0.0,
            wordTimestamps: true
        )

        let results = try await pipe.transcribe(
            audioPath: audioURL.path,
            decodeOptions: opts
        )

        let segments = results.flatMap { $0.segments }
        let fullText = results.map { $0.text }.joined(separator: " ")
        let detectedLang = results.first?.language ?? languageHint ?? "und"

        let result = TranscriptionResult(
            text: fullText,
            detectedLanguage: detectedLang,
            translatedToEnglish: translateToEnglish,
            segments: segments.map { seg in
                TranscriptionSegment(
                    start: Double(seg.start),
                    end: Double(seg.end),
                    text: seg.text
                )
            },
            modelName: modelName,
            durationSec: Double(segments.last?.end ?? 0)
        )
        lastResult = result
        return result
        #else
        throw TranscriberError.notReady
        #endif
    }

    /// PCM バッファ列 → テキスト（リアルタイム書き起こし用）
    public func transcribe(
        samples: [Float],
        languageHint: String? = nil
    ) async throws -> TranscriptionResult {
        #if canImport(WhisperKit)
        if loadState != .ready { await loadModel() }
        guard case .ready = loadState, let pipe = pipe else {
            throw TranscriberError.notReady
        }

        isTranscribing = true
        defer { isTranscribing = false }

        let opts = DecodingOptions(
            task: .transcribe,
            language: languageHint,
            temperature: 0.0
        )
        let results = try await pipe.transcribe(
            audioArray: samples,
            decodeOptions: opts
        )
        let fullText = results.map { $0.text }.joined(separator: " ")
        let detectedLang = results.first?.language ?? languageHint ?? "und"

        let result = TranscriptionResult(
            text: fullText,
            detectedLanguage: detectedLang,
            translatedToEnglish: false,
            segments: [],
            modelName: modelName,
            durationSec: Double(samples.count) / 16000.0
        )
        lastResult = result
        return result
        #else
        throw TranscriberError.notReady
        #endif
    }
}

// MARK: - 入出力モデル

public struct TranscriptionResult: Codable, Sendable {
    public let text: String
    public let detectedLanguage: String     // ISO 639-1 ("ja", "zh", "en"...)
    public let translatedToEnglish: Bool
    public let segments: [TranscriptionSegment]
    public let modelName: String
    public let durationSec: Double
}

public struct TranscriptionSegment: Codable, Sendable {
    public let start: Double
    public let end: Double
    public let text: String
}

public enum TranscriberError: Error, LocalizedError {
    case notReady
    case audioReadFailed(String)

    public var errorDescription: String? {
        switch self {
        case .notReady: return "Whisper モデルがロードされていません"
        case .audioReadFailed(let msg): return "音声ファイル読み込み失敗: \(msg)"
        }
    }
}
