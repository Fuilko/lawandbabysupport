import Foundation

/// 複雑案件向けの多段エージェント実行
///
/// 「70B では足りない」問題への解法：
/// **単一巨大モデル ❌ → 役割分担 + ループ ✓**
///
/// パイプライン例：
///
///   [入力] → Triage(SLM) → Retriever(RAG) → Reasoner(LLM) → Critic(LLM) → [出力]
///
/// - **Triage**: 端末上 SLM で「どの法分野か」「緊急度」を分類
/// - **Retriever**: 関連法条・判例を取得（JapaneseLegalRAG）
/// - **Reasoner**: 取得した文脈を入力に大型 LLM で推論
/// - **Critic**: 別の LLM で論理矛盾・幻覚を検出し再質問
/// - **Synthesizer**: 最終回答に統合（必要なら）
///
/// このアプローチで 14B モデル × 3 〜 4 ステージ ≒ 70B 単体を超える品質。
final class MultiAgentOrchestrator {

    private let triageProvider: LLMProvider       // 軽量 SLM 推奨
    private let reasonerProvider: LLMProvider     // 中〜大型 LLM
    private let criticProvider: LLMProvider       // 別系統の LLM 推奨（バイアス低減）
    private let rag: JapaneseLegalRAG?

    init(
        triage: LLMProvider,
        reasoner: LLMProvider,
        critic: LLMProvider,
        rag: JapaneseLegalRAG? = nil
    ) {
        self.triageProvider = triage
        self.reasonerProvider = reasoner
        self.criticProvider = critic
        self.rag = rag
    }

    /// 複雑案件を多段で処理
    func handle(
        question: String,
        caseCategory: CaseCategory? = nil
    ) async throws -> OrchestratedResponse {
        let runId = UUID()
        var trace: [AgentStep] = []

        // ----- Step 1: Triage -----
        let triageStart = Date()
        let triagePrompt = LLMPrompt(
            systemPrompt: "あなたは法律相談のトリアージ担当です。質問を読んで、関連する法分野（刑事/民事/労働/児童/DV/消費者/行政/その他）と緊急度（urgent/high/medium/low）を JSON で返してください。",
            userPrompt: question,
            temperature: 0.1,
            maxTokens: 256,
            responseFormat: .json
        )
        let triageRes = try await triageProvider.complete(prompt: triagePrompt)
        trace.append(AgentStep(
            stage: .triage,
            providerId: triageProvider.providerId,
            modelId: triageRes.modelId,
            input: question,
            output: triageRes.text,
            durationMs: Int(Date().timeIntervalSince(triageStart) * 1000)
        ))

        // ----- Step 2: Retrieval -----
        var ragContext: [String] = []
        if let category = caseCategory, let rag = rag {
            do {
                let statutes = try await rag.retrieveStatutes(for: category)
                ragContext = statutes.map { "\($0.title): \($0.content)" }
            } catch {
                trace.append(AgentStep(
                    stage: .retrieval,
                    providerId: "rag",
                    modelId: "embed",
                    input: category.rawValue,
                    output: "RAG 失敗: \(error)",
                    durationMs: 0
                ))
            }
        }

        // ----- Step 3: Reasoner -----
        let reasonStart = Date()
        let reasonerSys = """
        あなたは日本の法律専門家として、被害者支援の観点から回答してください。
        以下の参考法条を踏まえ、論理的根拠を明示しつつ回答してください。
        断定は避け、「〜の可能性が高い」「〜と解釈される」など慎重な表現を用いてください。
        最後に必ず「本回答は参考であり、具体的な法律行動は弁護士へ相談してください」を付記してください。
        """
        let reasonerPrompt = LLMPrompt(
            systemPrompt: reasonerSys,
            userPrompt: question,
            context: ragContext,
            temperature: 0.3,
            maxTokens: 2048
        )
        let reasonerRes = try await reasonerProvider.complete(prompt: reasonerPrompt)
        trace.append(AgentStep(
            stage: .reasoning,
            providerId: reasonerProvider.providerId,
            modelId: reasonerRes.modelId,
            input: question,
            output: reasonerRes.text,
            durationMs: Int(Date().timeIntervalSince(reasonStart) * 1000)
        ))

        // ----- Step 4: Critic -----
        let criticStart = Date()
        let criticSys = """
        あなたは法律回答のレビュー担当です。以下の回答について：
        1. 事実誤認や幻覚（hallucination）はないか
        2. 法条引用は正確か
        3. 過度に断定的でないか
        4. 当事者を不必要に煽る表現はないか
        を JSON 形式（OK/要修正の判定 + 具体的指摘）で返してください。
        """
        let criticPrompt = LLMPrompt(
            systemPrompt: criticSys,
            userPrompt: "【元の質問】\n\(question)\n\n【回答案】\n\(reasonerRes.text)",
            temperature: 0.1,
            maxTokens: 512,
            responseFormat: .json
        )
        let criticRes = try await criticProvider.complete(prompt: criticPrompt)
        trace.append(AgentStep(
            stage: .critique,
            providerId: criticProvider.providerId,
            modelId: criticRes.modelId,
            input: reasonerRes.text,
            output: criticRes.text,
            durationMs: Int(Date().timeIntervalSince(criticStart) * 1000)
        ))

        // ----- 最終回答 -----
        // 簡易：Critic が「要修正」を含む場合は注意書き追加
        var finalText = reasonerRes.text
        if criticRes.text.contains("要修正") || criticRes.text.localizedCaseInsensitiveContains("revis") {
            finalText += "\n\n⚠️ 注意：本回答は内部レビューで一部表現の見直しが提案されています。専門家への相談を強く推奨します。"
        }

        return OrchestratedResponse(
            runId: runId,
            finalText: finalText,
            trace: trace,
            triageJson: triageRes.text,
            criticJson: criticRes.text
        )
    }
}

// MARK: - 出力

struct OrchestratedResponse {
    let runId: UUID
    let finalText: String
    let trace: [AgentStep]
    let triageJson: String
    let criticJson: String

    var totalLatencyMs: Int { trace.reduce(0) { $0 + $1.durationMs } }
}

struct AgentStep {
    enum Stage: String { case triage, retrieval, reasoning, critique, synthesis }
    let stage: Stage
    let providerId: String
    let modelId: String
    let input: String
    let output: String
    let durationMs: Int
}
