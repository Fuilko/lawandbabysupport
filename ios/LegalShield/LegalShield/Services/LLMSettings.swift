import Foundation
import Combine

/// ユーザーが設定可能な LLM プロバイダ選択
@MainActor
public final class LLMSettings: ObservableObject {

    public static let shared = LLMSettings()

    @Published public var preferredProvider: ProviderKind {
        didSet { save() }
    }
    @Published public var ollamaEndpoint: String {
        didSet { save() }
    }
    @Published public var ollamaModelId: String {
        didSet { save() }
    }
    @Published public var bedrockProxy: String {
        didSet { save() }
    }
    @Published public var bedrockModelId: String {
        didSet { save() }
    }
    @Published public var bedrockApiKey: String {
        didSet { save() }
    }
    @Published public var enableMultiAgent: Bool {
        didSet { save() }
    }

    public enum ProviderKind: String, Codable, CaseIterable {
        case onDevice
        case ollama
        case bedrock

        public var displayName: String {
            switch self {
            case .onDevice: return "端末上 SLM (3B)"
            case .ollama:   return "自前 Ollama サーバー"
            case .bedrock:  return "AWS Bedrock"
            }
        }
    }

    private let defaults = UserDefaults.standard
    private let key = "LLMSettings.v1"

    private init() {
        if let data = defaults.data(forKey: key),
           let stored = try? JSONDecoder().decode(StoredSettings.self, from: data) {
            self.preferredProvider = stored.preferredProvider
            self.ollamaEndpoint = stored.ollamaEndpoint
            self.ollamaModelId = stored.ollamaModelId
            self.bedrockProxy = stored.bedrockProxy
            self.bedrockModelId = stored.bedrockModelId
            self.bedrockApiKey = stored.bedrockApiKey
            self.enableMultiAgent = stored.enableMultiAgent
        } else {
            self.preferredProvider = .ollama
            self.ollamaEndpoint = "http://100.76.218.124:8000"
            self.ollamaModelId = "phi4:14b"
            self.bedrockProxy = ""
            self.bedrockModelId = "anthropic.claude-3-5-sonnet-20241022-v2:0"
            self.bedrockApiKey = ""
            self.enableMultiAgent = false
        }
    }

    private func save() {
        let stored = StoredSettings(
            preferredProvider: preferredProvider,
            ollamaEndpoint: ollamaEndpoint,
            ollamaModelId: ollamaModelId,
            bedrockProxy: bedrockProxy,
            bedrockModelId: bedrockModelId,
            bedrockApiKey: bedrockApiKey,
            enableMultiAgent: enableMultiAgent
        )
        if let data = try? JSONEncoder().encode(stored) {
            defaults.set(data, forKey: key)
        }
    }

    /// 現在設定からプロバイダを 1 つ生成
    public func makeProvider() -> LLMProvider {
        switch preferredProvider {
        case .onDevice:
            return OnDeviceSLMProvider()
        case .ollama:
            return CloudOllamaProvider(endpoint: ollamaEndpoint, modelId: ollamaModelId)
        case .bedrock:
            return AWSBedrockProvider(
                proxyEndpoint: bedrockProxy,
                apiKey: bedrockApiKey.isEmpty ? nil : bedrockApiKey,
                modelId: bedrockModelId
            )
        }
    }

    /// マルチエージェント用に 3 つの provider を生成
    /// （triage は端末 SLM、reasoner は preferred、critic は別系統）
    public func makeMultiAgentSet() -> (triage: LLMProvider, reasoner: LLMProvider, critic: LLMProvider) {
        let triage = OnDeviceSLMProvider()
        let reasoner = makeProvider()

        // Critic は reasoner と別系統を選ぶ（バイアス低減）
        let critic: LLMProvider
        switch preferredProvider {
        case .ollama:
            critic = AWSBedrockProvider(
                proxyEndpoint: bedrockProxy,
                apiKey: bedrockApiKey.isEmpty ? nil : bedrockApiKey,
                modelId: bedrockModelId
            )
        case .bedrock:
            critic = CloudOllamaProvider(endpoint: ollamaEndpoint, modelId: ollamaModelId)
        case .onDevice:
            critic = CloudOllamaProvider(endpoint: ollamaEndpoint, modelId: ollamaModelId)
        }
        return (triage, reasoner, critic)
    }

    private struct StoredSettings: Codable {
        let preferredProvider: ProviderKind
        let ollamaEndpoint: String
        let ollamaModelId: String
        let bedrockProxy: String
        let bedrockModelId: String
        let bedrockApiKey: String
        let enableMultiAgent: Bool
    }
}
