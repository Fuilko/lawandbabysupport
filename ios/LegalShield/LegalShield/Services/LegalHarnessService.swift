import Foundation

/// Anti-Hallucination Harness クライアント
///
/// バックエンド `POST /rag/answer`（legalshield/backend/harness.py）を呼び、
/// **検索ゲートを通った grounded 回答**を取得する。
///
/// なぜ必要か：
///   従来の `CloudOllamaProvider` は `/api/generate`（無検索の生 Ollama）を叩くため、
///   法律質問に対して DB を参照せず「幻覚」で自信満々に回答していた。
///   本サービスは検索→根拠注入→自己検証をサーバ側で強制した結果を返す。
public final class LegalHarnessService {

    public struct Config {
        public var baseEndpoint: String   // 例: http://100.76.218.124:8000
        public var model: String?
        public var judgeModel: String?    // 指定時は独立 LLM で cross-check（L5）
        public var topK: Int
        public var useStatutes: Bool

        public init(
            baseEndpoint: String,
            model: String? = nil,
            judgeModel: String? = nil,
            topK: Int = 6,
            useStatutes: Bool = true
        ) {
            self.baseEndpoint = baseEndpoint
            self.model = model
            self.judgeModel = judgeModel
            self.topK = topK
            self.useStatutes = useStatutes
        }
    }

    public enum HarnessError: Error {
        case invalidEndpoint
        case http(Int, String)
        case decode(String)
        case network
    }

    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    /// grounded 回答を取得
    public func answer(question: String, config: Config) async throws -> HarnessAnswer {
        guard let url = URL(string: "\(config.baseEndpoint)/rag/answer") else {
            throw HarnessError.invalidEndpoint
        }

        var body: [String: Any] = [
            "question": question,
            "top_k": config.topK,
            "use_statutes": config.useStatutes,
            "audit": true,
        ]
        if let m = config.model { body["model"] = m }
        if let j = config.judgeModel { body["judge_model"] = j }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.timeoutInterval = 200  // judge を含むと時間がかかる

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw HarnessError.network
        }

        guard let http = response as? HTTPURLResponse else {
            throw HarnessError.http(-1, "no http response")
        }
        guard http.statusCode == 200 else {
            let msg = String(data: data, encoding: .utf8) ?? ""
            throw HarnessError.http(http.statusCode, String(msg.prefix(300)))
        }

        do {
            return try JSONDecoder().decode(HarnessAnswer.self, from: data)
        } catch {
            throw HarnessError.decode("\(error)")
        }
    }
}
