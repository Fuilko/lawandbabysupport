import Foundation
import SwiftUI

/// VoiceTriageService の設定（UserDefaults 永続化）
///
/// LLMSettings から独立。VoiceTriageService が起動時に参照する：
/// - `dispatchEndpoint`（GIS API or 管理者 Webhook URL）
/// - `dispatchBearerToken`（HTTP Bearer 認証用、AWS Bedrock proxy と同形式）
/// - `defaultRecordingMode`（標準録音モード）
/// - `whisperModelName`（端末スペックに応じたモデル選択）
/// - `mlxModelId`（On-device triage SLM のモデル）
/// - `cloudReviewThreshold`（urgency >= n で雲端 LLM 詳細分析を呼ぶ）
/// - `enableAutoEscalation`（urgency=4 で自動 110/189 通報を許可するか）
@MainActor
public final class VoiceTriageSettings: ObservableObject {

    public static let shared = VoiceTriageSettings()

    // MARK: - 遠隔送信先

    @Published public var dispatchEndpoint: String {
        didSet { UserDefaults.standard.set(dispatchEndpoint, forKey: "vt.dispatchEndpoint") }
    }

    @Published public var dispatchBearerToken: String {
        didSet { UserDefaults.standard.set(dispatchBearerToken, forKey: "vt.dispatchBearerToken") }
    }

    // MARK: - 録音

    @Published public var defaultRecordingMode: RecordingMode {
        didSet { UserDefaults.standard.set(defaultRecordingMode.rawValue, forKey: "vt.defaultRecordingMode") }
    }

    /// 待機モードを背景で常時オンにするか
    @Published public var enableStandbyAlwaysOn: Bool {
        didSet { UserDefaults.standard.set(enableStandbyAlwaysOn, forKey: "vt.enableStandbyAlwaysOn") }
    }

    // MARK: - モデル

    @Published public var whisperModelName: String {
        didSet { UserDefaults.standard.set(whisperModelName, forKey: "vt.whisperModelName") }
    }

    @Published public var mlxModelId: String {
        didSet { UserDefaults.standard.set(mlxModelId, forKey: "vt.mlxModelId") }
    }

    // MARK: - Triage

    /// この緊急度以上で雲端 Bedrock 詳細分析を呼ぶ（既定 3 = 高）
    @Published public var cloudReviewThreshold: Int {
        didSet { UserDefaults.standard.set(cloudReviewThreshold, forKey: "vt.cloudReviewThreshold") }
    }

    /// 緊急度 4 で自動的に 110/189 通報を許可するか（既定 false）
    /// true にする前に必ずユーザー同意を取る
    @Published public var enableAutoEscalation: Bool {
        didSet { UserDefaults.standard.set(enableAutoEscalation, forKey: "vt.enableAutoEscalation") }
    }

    /// 信頼連絡先（自動連絡用、3 件まで）
    @Published public var trustedContacts: [TrustedContact] {
        didSet {
            if let data = try? JSONEncoder().encode(trustedContacts) {
                UserDefaults.standard.set(data, forKey: "vt.trustedContacts")
            }
        }
    }

    // MARK: - 匿名化

    @Published public var defaultAnonymizationLevel: String {
        didSet { UserDefaults.standard.set(defaultAnonymizationLevel, forKey: "vt.anonymizationLevel") }
    }

    // MARK: - 位置情報の去識別化

    /// オフセット半径 [m]（被害者位置の保護）
    @Published public var locationOffsetRadiusM: Double {
        didSet { UserDefaults.standard.set(locationOffsetRadiusM, forKey: "vt.locOffsetRadius") }
    }

    /// H3 風ヘックス解像度 [m]
    @Published public var locationHexResolutionM: Double {
        didSet { UserDefaults.standard.set(locationHexResolutionM, forKey: "vt.locHexRes") }
    }

    /// k-匿名性閾値（同 hex に何人いれば描画するか）
    @Published public var kAnonymityThreshold: Int {
        didSet { UserDefaults.standard.set(kAnonymityThreshold, forKey: "vt.kAnonymity") }
    }

    /// 仮想都市変換（実地名・住所ラベルを地図に出さない）
    @Published public var useVirtualCity: Bool {
        didSet { UserDefaults.standard.set(useVirtualCity, forKey: "vt.useVirtualCity") }
    }

    /// 現在設定から LocationAnonymizer Config を構築
    public func anonymizerConfig() -> LocationAnonymizer.Config {
        LocationAnonymizer.Config(
            offsetRadiusMeters: locationOffsetRadiusM,
            hexResolutionMeters: locationHexResolutionM,
            kAnonymityThreshold: kAnonymityThreshold,
            useVirtualCity: useVirtualCity
        )
    }

    // MARK: - Init (UserDefaults からロード)

    private init() {
        let ud = UserDefaults.standard

        self.dispatchEndpoint = ud.string(forKey: "vt.dispatchEndpoint") ?? ""
        self.dispatchBearerToken = ud.string(forKey: "vt.dispatchBearerToken") ?? ""

        let modeRaw = ud.string(forKey: "vt.defaultRecordingMode") ?? RecordingMode.evidence.rawValue
        self.defaultRecordingMode = RecordingMode(rawValue: modeRaw) ?? .evidence

        self.enableStandbyAlwaysOn = ud.bool(forKey: "vt.enableStandbyAlwaysOn")

        self.whisperModelName = ud.string(forKey: "vt.whisperModelName")
            ?? WhisperKitTranscriber.defaultModelName

        self.mlxModelId = ud.string(forKey: "vt.mlxModelId")
            ?? "mlx-community/Phi-3.5-mini-instruct-4bit"

        self.cloudReviewThreshold = ud.object(forKey: "vt.cloudReviewThreshold") as? Int ?? 3
        self.enableAutoEscalation = ud.bool(forKey: "vt.enableAutoEscalation")

        if let data = ud.data(forKey: "vt.trustedContacts"),
           let contacts = try? JSONDecoder().decode([TrustedContact].self, from: data) {
            self.trustedContacts = contacts
        } else {
            self.trustedContacts = []
        }

        self.defaultAnonymizationLevel = ud.string(forKey: "vt.anonymizationLevel") ?? "partial"

        // 位置情報の去識別化（既定：500m オフセット、460m hex、k=5、仮想都市 ON）
        self.locationOffsetRadiusM = ud.object(forKey: "vt.locOffsetRadius") as? Double ?? 500.0
        self.locationHexResolutionM = ud.object(forKey: "vt.locHexRes") as? Double ?? 460.0
        self.kAnonymityThreshold = ud.object(forKey: "vt.kAnonymity") as? Int ?? 5
        self.useVirtualCity = ud.object(forKey: "vt.useVirtualCity") as? Bool ?? true
    }

    // MARK: - VoiceTriageService への適用

    /// 設定を VoiceTriageService に適用（起動時または設定変更時に呼ぶ）
    public func apply(to service: VoiceTriageService) {
        if let url = URL(string: dispatchEndpoint), !dispatchEndpoint.isEmpty {
            service.dispatchEndpoint = url
        }
        service.dispatchBearerToken = dispatchBearerToken.isEmpty ? nil : dispatchBearerToken
    }
}

// MARK: - 信頼連絡先

public struct TrustedContact: Codable, Identifiable, Equatable {
    public let id: UUID
    public var name: String
    public var phone: String?
    public var email: String?
    public var role: String   // "lawyer", "ngo", "family", "friend", "other"
    public var notifyOnUrgency: Int   // この urgency 以上で通知

    public init(
        id: UUID = UUID(),
        name: String,
        phone: String? = nil,
        email: String? = nil,
        role: String = "family",
        notifyOnUrgency: Int = 3
    ) {
        self.id = id
        self.name = name
        self.phone = phone
        self.email = email
        self.role = role
        self.notifyOnUrgency = notifyOnUrgency
    }
}
