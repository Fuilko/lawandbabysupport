import Foundation

/// LLM プロバイダ抽象化
///
/// LegalShield が想定する 4 種類のバックエンド：
///
/// 1. **OnDeviceSLM** — Apple Foundation Models / MLX で動く 3B 級の SLM
///    用途：意図分類、簡易 QA、誘導質問チェック、緊急トリアージ
///    利点：完全オフライン、プライバシー最強、無料
///    欠点：複雑な法律推論には不向き
///
/// 2. **CloudOllama** — 自前 Tailscale 上の Ollama サーバー（既存）
///    用途：14B〜70B モデルでの本格分析、文書生成
///    利点：自己管理、コストゼロ
///    欠点：サーバーが落ちると停止、可用性に課題
///
/// 3. **AWSBedrock** — AWS Bedrock 経由 Claude / Llama
///    用途：商用品質の分析、SLA 保証が必要な本番転介
///    利点：可用性高、選択肢豊富
///    欠点：コスト、データが米国経由
///
/// 4. **MultiAgent** — 複数モデルを役割分担して協調動作
///    用途：複雑な案件で 70B 単体でも回答が浅い場合
///    例：[Triage SLM] → [Statute RAG] → [Reasoner LLM] → [Critic LLM]
///    利点：単一モデルの限界突破、説明可能性向上
///    欠点：レイテンシ、設計コスト
public protocol LLMProvider {
    var providerId: String { get }
    var displayName: String { get }
    var requiresNetwork: Bool { get }
    var estimatedLatencyMs: Int { get }

    func complete(prompt: LLMPrompt) async throws -> LLMResponse
}

// MARK: - 入出力

public struct LLMPrompt {
    public let systemPrompt: String?
    public let userPrompt: String
    public let context: [String]            // RAG チャンク
    public let temperature: Double
    public let maxTokens: Int
    public let stopSequences: [String]
    public let responseFormat: LLMResponseFormat

    public init(
        systemPrompt: String? = nil,
        userPrompt: String,
        context: [String] = [],
        temperature: Double = 0.3,
        maxTokens: Int = 2048,
        stopSequences: [String] = [],
        responseFormat: LLMResponseFormat = .text
    ) {
        self.systemPrompt = systemPrompt
        self.userPrompt = userPrompt
        self.context = context
        self.temperature = temperature
        self.maxTokens = maxTokens
        self.stopSequences = stopSequences
        self.responseFormat = responseFormat
    }
}

public enum LLMResponseFormat {
    case text
    case json
}

public struct LLMResponse {
    public let text: String
    public let modelId: String
    public let promptTokens: Int?
    public let completionTokens: Int?
    public let latencyMs: Int
    public let providerMetadata: [String: String]
}

// MARK: - エラー

public enum LLMProviderError: Error {
    case networkUnavailable
    case unauthorized
    case rateLimited(retryAfter: TimeInterval?)
    case modelUnavailable(String)
    case responseInvalid(String)
    case timeout
    case unknown(String)
}
