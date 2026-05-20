import Foundation

/// On-Device 3B SLM プロバイダ
///
/// 実装方針（段階的）：
///
/// **Phase 1 (現在)**: Apple Foundation Models（iOS 18.4+）
///   - Apple が提供する on-device LLM（〜3B 相当）
///   - import FoundationModels (iOS 18.4 SDK)
///   - 用途：意図分類、簡易 QA、テンプレート生成
///
/// **Phase 2**: MLX-Swift で Llama 3.2 3B / Phi-3 Mini 3.8B / Qwen 2.5 3B を実装
///   - 量子化済み（4-bit）モデルを App Bundle または Documents に配置
///   - 初回起動時にダウンロード（〜2GB）
///
/// **Phase 3**: Llama.cpp Swift binding でフルカスタム
///
/// 現状はインターフェイス定義 + 簡易ローカル応答（モック）。
/// FoundationModels API が iOS 26 で安定化したら本実装する。
public final class OnDeviceSLMProvider: LLMProvider {
    public let providerId = "on-device-slm"
    public let displayName = "端末上 SLM (3B)"
    public let requiresNetwork = false
    public let estimatedLatencyMs = 800

    /// 現在使用するモデル ID
    /// - "apple-foundation-3b": Apple Foundation Models
    /// - "llama-3.2-3b-q4": MLX で量子化した Llama 3.2 3B
    /// - "phi-3-mini-q4": MLX で量子化した Phi-3 Mini
    public let modelId: String

    public init(modelId: String = "apple-foundation-3b") {
        self.modelId = modelId
    }

    public func complete(prompt: LLMPrompt) async throws -> LLMResponse {
        let start = Date()

        // TODO Phase 1: Apple FoundationModels で実装
        //   import FoundationModels
        //   let session = LanguageModelSession(...)
        //   let response = try await session.respond(to: combined)
        //
        // TODO Phase 2: MLX
        //   import MLX
        //   import MLXLLM
        //   let result = try await model.generate(prompt: combined, ...)

        // 暫定モック：意図分類のみ簡易ルールで応答
        let combined = (prompt.systemPrompt ?? "") + "\n" + prompt.userPrompt
        let mockText = mockResponse(for: combined)

        let latency = Int(Date().timeIntervalSince(start) * 1000)

        return LLMResponse(
            text: mockText,
            modelId: modelId,
            promptTokens: combined.count / 4,
            completionTokens: mockText.count / 4,
            latencyMs: latency,
            providerMetadata: [
                "implementation": "mock",
                "note": "Apple FoundationModels の安定化を待って本実装"
            ]
        )
    }

    // MARK: - 暫定実装

    private func mockResponse(for prompt: String) -> String {
        // 意図分類用ルールベース fallback
        let lower = prompt.lowercased()
        if lower.contains("緊急") || lower.contains("emergency") || lower.contains("助けて") {
            return "[緊急対応モード] 最優先で 110番、もしくは指定 NGO への連絡を推奨。証拠保全を継続してください。"
        }
        if lower.contains("証拠") || lower.contains("evidence") {
            return "証拠の改ざん耐性を保つには、撮影と同時にハッシュ生成・GPS 記録を完了させてください。"
        }
        if lower.contains("誘導") || lower.contains("interview") {
            return "オープン質問テンプレートを使用してください：『〜について教えてくれる？』『そのとき何があったの？』"
        }
        return "（On-Device SLM 暫定応答）プロンプトを受信しましたが、本実装はまだです。CloudOllama または AWSBedrock を選択してください。"
    }
}
