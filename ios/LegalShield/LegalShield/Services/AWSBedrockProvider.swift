import Foundation

/// AWS Bedrock プロバイダ
///
/// Bedrock InvokeModel API は SigV4 署名が必要なため、
/// 本格実装では AWSSwiftRuntime / SmithyClient を使うのが推奨。
///
/// **本番運用時の構成（推奨）**：
/// 1. iOS → Cognito → 一時的な IAM 認証情報を取得
/// 2. 一時認証で Bedrock InvokeModel を直接呼ぶ（SigV4 署名）
/// 3. または Lambda / API Gateway 経由で Bedrock を中継し、iOS は Bearer トークンのみで叩く
///
/// **当面の実装**：
/// - 自前の薄いプロキシ（Lambda Function URL や Tailscale 経由）を経由
/// - プロキシ側で SigV4 署名 + レート制限 + ログ記録
/// - iOS は単純な POST で済む（このクラスはそれを想定）
///
/// proxyEndpoint 形式：
///   POST {proxyEndpoint}/invoke
///   Body: {"model_id": "...", "prompt": "...", "max_tokens": 2048}
public final class AWSBedrockProvider: LLMProvider {
    public let providerId = "aws-bedrock"
    public var displayName: String { "AWS Bedrock (\(modelId))" }
    public let requiresNetwork = true
    public let estimatedLatencyMs = 1500

    public let proxyEndpoint: String
    public let apiKey: String?
    public let modelId: String      // "anthropic.claude-3-5-sonnet-20241022-v2:0" 等
    private let session: URLSession

    public init(
        proxyEndpoint: String,
        apiKey: String? = nil,
        modelId: String = "anthropic.claude-3-5-sonnet-20241022-v2:0",
        session: URLSession = .shared
    ) {
        self.proxyEndpoint = proxyEndpoint
        self.apiKey = apiKey
        self.modelId = modelId
        self.session = session
    }

    public func complete(prompt: LLMPrompt) async throws -> LLMResponse {
        let start = Date()
        guard let url = URL(string: "\(proxyEndpoint)/invoke") else {
            throw LLMProviderError.unknown("Invalid proxy endpoint")
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let key = apiKey {
            request.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
        }
        request.timeoutInterval = 60

        let body: [String: Any] = [
            "model_id": modelId,
            "system": prompt.systemPrompt ?? "",
            "messages": [
                ["role": "user", "content": buildUserContent(prompt)]
            ],
            "max_tokens": prompt.maxTokens,
            "temperature": prompt.temperature
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw LLMProviderError.networkUnavailable
        }

        guard let http = response as? HTTPURLResponse else {
            throw LLMProviderError.unknown("Invalid HTTP response")
        }

        switch http.statusCode {
        case 200: break
        case 401, 403: throw LLMProviderError.unauthorized
        case 429:
            let retry = (http.value(forHTTPHeaderField: "Retry-After")).flatMap(Double.init)
            throw LLMProviderError.rateLimited(retryAfter: retry)
        case 503: throw LLMProviderError.modelUnavailable(modelId)
        default: throw LLMProviderError.unknown("HTTP \(http.statusCode)")
        }

        guard
            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
            let content = json["content"] as? [[String: Any]],
            let firstText = content.first?["text"] as? String
        else {
            // Anthropic Bedrock 標準形式で取れなかった場合のフォールバック
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let text = json["completion"] as? String ?? json["text"] as? String {
                let latency = Int(Date().timeIntervalSince(start) * 1000)
                return LLMResponse(
                    text: text,
                    modelId: modelId,
                    promptTokens: nil,
                    completionTokens: nil,
                    latencyMs: latency,
                    providerMetadata: ["proxy": proxyEndpoint]
                )
            }
            throw LLMProviderError.responseInvalid("Unexpected Bedrock response shape")
        }

        let latency = Int(Date().timeIntervalSince(start) * 1000)
        let usage = json["usage"] as? [String: Any]

        return LLMResponse(
            text: firstText,
            modelId: modelId,
            promptTokens: usage?["input_tokens"] as? Int,
            completionTokens: usage?["output_tokens"] as? Int,
            latencyMs: latency,
            providerMetadata: ["proxy": proxyEndpoint]
        )
    }

    private func buildUserContent(_ p: LLMPrompt) -> String {
        if p.context.isEmpty { return p.userPrompt }
        let ctx = p.context.enumerated().map { "[\($0+1)] \($1)" }.joined(separator: "\n")
        return "【参考情報】\n\(ctx)\n\n【質問】\n\(p.userPrompt)"
    }
}
