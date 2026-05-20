import Foundation

/// Cloud Ollama プロバイダ（既存の Tailscale Windows サーバー）
public final class CloudOllamaProvider: LLMProvider {
    public let providerId = "cloud-ollama"
    public var displayName: String { "Ollama (\(modelId))" }
    public let requiresNetwork = true
    public let estimatedLatencyMs = 3000

    public let endpoint: String
    public let modelId: String
    private let session: URLSession

    public init(
        endpoint: String = "http://100.76.218.124:8000",
        modelId: String = "phi4:14b",
        session: URLSession = .shared
    ) {
        self.endpoint = endpoint
        self.modelId = modelId
        self.session = session
    }

    public func complete(prompt: LLMPrompt) async throws -> LLMResponse {
        let start = Date()
        guard let url = URL(string: "\(endpoint)/api/generate") else {
            throw LLMProviderError.unknown("Invalid endpoint URL")
        }

        let combined = buildPromptText(prompt)
        let body: [String: Any] = [
            "model": modelId,
            "prompt": combined,
            "stream": false,
            "options": [
                "temperature": prompt.temperature,
                "num_predict": prompt.maxTokens
            ]
        ]

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.timeoutInterval = 60

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
        case 200:
            break
        case 401, 403:
            throw LLMProviderError.unauthorized
        case 429:
            throw LLMProviderError.rateLimited(retryAfter: nil)
        case 503:
            throw LLMProviderError.modelUnavailable(modelId)
        default:
            throw LLMProviderError.unknown("HTTP \(http.statusCode)")
        }

        guard
            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
            let text = json["response"] as? String
        else {
            throw LLMProviderError.responseInvalid("Missing 'response' field")
        }

        let latency = Int(Date().timeIntervalSince(start) * 1000)

        return LLMResponse(
            text: text,
            modelId: modelId,
            promptTokens: json["prompt_eval_count"] as? Int,
            completionTokens: json["eval_count"] as? Int,
            latencyMs: latency,
            providerMetadata: [
                "endpoint": endpoint,
                "total_duration_ns": "\(json["total_duration"] ?? 0)"
            ]
        )
    }

    private func buildPromptText(_ p: LLMPrompt) -> String {
        var parts: [String] = []
        if let sys = p.systemPrompt {
            parts.append("【システム】\n\(sys)")
        }
        if !p.context.isEmpty {
            parts.append("【参考情報】\n" + p.context.enumerated().map { "[\($0+1)] \($1)" }.joined(separator: "\n"))
        }
        parts.append("【質問】\n\(p.userPrompt)")
        return parts.joined(separator: "\n\n")
    }
}
