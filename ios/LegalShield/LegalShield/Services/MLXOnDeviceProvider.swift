import Foundation
#if canImport(MLX) && canImport(MLXLLM)
import MLX
import MLXLLM
import MLXLMCommon
#endif

/// MLX-Swift 経由の On-Device SLM 推論プロバイダ
///
/// **訓練は行わない**（LoRA fine-tune は Mac / Windows 上の `mlx-lm` で別途実施）。
/// このクラスは **推論専用**。
///
/// ## 推奨モデル
/// - `mlx-community/Phi-3.5-mini-instruct-4bit` (3.8B / ~2.0 GB)
/// - `mlx-community/gemma-2-2b-it-4bit` (2B / ~1.2 GB)
/// - `mlx-community/Qwen2.5-1.5B-Instruct-4bit` (1.5B / ~0.9 GB)
///
/// ## ロード戦略
/// 1. 初回起動時 background download → `Documents/mlx-models/<model_id>/`
/// 2. 二回目以降は localStorage から即時ロード
/// 3. Settings 画面でモデル切替可
///
/// ## 既存 OnDeviceSLMProvider との関係
/// - `OnDeviceSLMProvider`：mock + Apple FoundationModels（iOS 18.4+）
/// - `MLXOnDeviceProvider`：MLX 経由のオープンウェイト LLM（任意モデル）
///
/// LLMSettings 上で **どちらを使うか選べる** ように `ProviderKind` を将来拡張する。
@MainActor
public final class MLXOnDeviceProvider: LLMProvider {
    public let providerId = "mlx-on-device"
    public var displayName: String { "MLX (\(modelId))" }
    public let requiresNetwork = false
    public let estimatedLatencyMs = 1200

    public let modelId: String

    #if canImport(MLX) && canImport(MLXLLM)
    private var modelContainer: ModelContainer?
    #endif

    public init(modelId: String = "mlx-community/Phi-3.5-mini-instruct-4bit") {
        self.modelId = modelId
    }

    // MARK: - モデルロード

    /// 初回ダウンロード or Documents/mlx-models/ から再ロード
    public func loadModel() async throws {
        #if canImport(MLX) && canImport(MLXLLM)
        guard modelContainer == nil else { return }

        let configuration = ModelConfiguration(
            id: modelId,
            tokenizerId: nil,
            overrideTokenizer: nil,
            defaultPrompt: ""
        )
        let factory = LLMModelFactory.shared
        let container = try await factory.loadContainer(configuration: configuration) { progress in
            // progress.fractionCompleted 0.0〜1.0
            #if DEBUG
            print("[MLX] downloading \(self.modelId): \(Int(progress.fractionCompleted * 100))%")
            #endif
        }
        self.modelContainer = container
        #else
        throw LLMProviderError.unknown("MLX not linked. Run xcodegen generate first.")
        #endif
    }

    // MARK: - LLMProvider

    public func complete(prompt: LLMPrompt) async throws -> LLMResponse {
        #if canImport(MLX) && canImport(MLXLLM)
        let start = Date()
        if modelContainer == nil { try await loadModel() }
        guard let container = modelContainer else {
            throw LLMProviderError.modelUnavailable(modelId)
        }

        // Chat-template に sytem + user を組み立て
        let userText = buildUserContent(prompt)
        let messages: [Chat.Message] = {
            var m: [Chat.Message] = []
            if let sys = prompt.systemPrompt, !sys.isEmpty {
                m.append(.system(sys))
            }
            m.append(.user(userText))
            return m
        }()
        let chat = Chat(messages: messages)

        let parameters = GenerateParameters(
            temperature: Float(prompt.temperature),
            topP: 0.9
        )

        let result = try await container.perform { ctx in
            let input = try await ctx.processor.prepare(input: .init(chat: chat))
            return try MLXLMCommon.generate(
                input: input,
                parameters: parameters,
                context: ctx
            ) { tokens in
                tokens.count >= prompt.maxTokens ? .stop : .more
            }
        }

        let latency = Int(Date().timeIntervalSince(start) * 1000)
        return LLMResponse(
            text: result.output,
            modelId: modelId,
            promptTokens: result.promptTokens,
            completionTokens: result.tokens.count,
            latencyMs: latency,
            providerMetadata: [
                "framework": "mlx-swift",
                "tps": String(format: "%.1f", result.tokensPerSecond)
            ]
        )
        #else
        throw LLMProviderError.unknown("MLX not linked")
        #endif
    }

    // MARK: - ヘルパー

    private func buildUserContent(_ p: LLMPrompt) -> String {
        if p.context.isEmpty { return p.userPrompt }
        let ctx = p.context.enumerated().map { "[\($0+1)] \($1)" }.joined(separator: "\n")
        return "【参考情報】\n\(ctx)\n\n【質問】\n\(p.userPrompt)"
    }
}

// MARK: - LLMSettings 拡張用ヘルパー

public extension MLXOnDeviceProvider {
    /// 推奨モデルプリセット（Settings 画面で選ばせる用）
    static let presets: [(label: String, modelId: String, ramHintMB: Int)] = [
        ("Phi-3.5 mini (3.8B, 推奨)", "mlx-community/Phi-3.5-mini-instruct-4bit", 2048),
        ("Gemma 2 (2B, 軽量)",         "mlx-community/gemma-2-2b-it-4bit",          1280),
        ("Qwen 2.5 (1.5B, 最軽量)",   "mlx-community/Qwen2.5-1.5B-Instruct-4bit",    896),
        ("Llama 3.2 (3B, バランス)",  "mlx-community/Llama-3.2-3B-Instruct-4bit",   1792),
    ]
}
