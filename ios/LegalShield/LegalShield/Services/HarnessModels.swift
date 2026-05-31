import Foundation

/// Anti-Hallucination Harness のレスポンスモデル
///
/// バックエンド `POST /rag/answer`（legalshield/backend/harness.py の L1-L7）の
/// JSON を 1:1 でデコードする。生 LLM ではなく「検索ゲートを通った grounded 回答」
/// を表現し、各根拠（source）・信頼度・弁護士介入フラグを UI に伝える。
public struct HarnessAnswer: Codable, Equatable {
    public let answer: String
    public let refused: Bool
    public let confidence: Double
    public let riskClass: String
    public let lawyerRequired: Bool
    public let irreversibleActionWarning: String?
    public let intent: HarnessIntent
    public let sources: [HarnessSource]
    public let verification: HarnessVerification
    public let warnings: [String]
    public let harnessVersion: String
    public let elapsedMs: Int
    public let modelUsed: String?

    enum CodingKeys: String, CodingKey {
        case answer, refused, confidence, intent, sources, verification, warnings
        case riskClass = "risk_class"
        case lawyerRequired = "lawyer_required"
        case irreversibleActionWarning = "irreversible_action_warning"
        case harnessVersion = "harness_version"
        case elapsedMs = "elapsed_ms"
        case modelUsed = "model_used"
    }

    /// 信頼度を 5 段階バッジに変換（L6 Transparency UI 用）
    public var confidenceBars: Int { Int((confidence * 5).rounded()) }

    /// 幻覚（未裏付け主張）が検出されたか
    public var hasUngrounded: Bool { !verification.ungroundedClaims.isEmpty }
}

public struct HarnessIntent: Codable, Equatable {
    public let claimType: String
    public let riskClass: String
    public let venue: String
    public let domain: String
    public let requiresExternalVerify: Bool
    public let requiresLawyer: Bool
    public let reasons: [String]

    enum CodingKeys: String, CodingKey {
        case venue, domain, reasons
        case claimType = "claim_type"
        case riskClass = "risk_class"
        case requiresExternalVerify = "requires_external_verify"
        case requiresLawyer = "requires_lawyer"
    }
}

public struct HarnessSource: Codable, Equatable, Identifiable {
    public let id: String          // "S1", "S2" ...
    public let kind: String        // precedent / statute / ...
    public let trust: String       // high / medium / low / quarantined
    public let provenance: String
    public let citation: String
    public let excerpt: String
    public let score: Double

    /// 出典の種別アイコン（UI 用）
    public var kindLabel: String {
        switch kind {
        case "statute": return "条文"
        case "precedent": return "判例"
        case "partner": return "窓口"
        case "user_upload": return "提出資料"
        default: return kind
        }
    }
}

public struct HarnessVerification: Codable, Equatable {
    public let ungroundedClaims: [HarnessUngrounded]
    public let citedSourceIds: [String]
    public let refused: Bool
    public let confidence: Double

    enum CodingKeys: String, CodingKey {
        case refused, confidence
        case ungroundedClaims = "ungrounded_claims"
        case citedSourceIds = "cited_source_ids"
    }
}

public struct HarnessUngrounded: Codable, Equatable {
    public let type: String
    public let value: String
    public let note: String?
}
