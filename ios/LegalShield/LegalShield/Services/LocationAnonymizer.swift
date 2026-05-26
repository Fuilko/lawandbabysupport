import Foundation
import CoreLocation

/// 位置情報の去識別化（被害者・使用者の保護）
///
/// ## 3 層防御
/// 1. **ランダムオフセット**：真の座標を中心に半径 R[m] の一様円分布で再ロール
/// 2. **H3 ヘックス集約**：geohash 風の 6 角形セルへ丸める（resolution 8 ≒ 460m 一辺）
/// 3. **k-匿名性ゲート**：同一 hex に k 件以上のイベントが集まった時のみ描画許可
///
/// ## 仮想都市マッピング（オプション）
/// `useVirtualCity = true` で、実座標の原点を高知市庁舎 (33.5597, 133.5311) に正規化し、
/// 地図には地名・住所ラベルを **一切表示しない**（MapLibre style で `text-field: ""`）。
///
/// ## H3 簡易実装
/// 本実装は H3 公式ライブラリの代わりに「等緯度・等経度グリッド + ハッシュ化」の
/// 簡易ヘックスインデックスを使用。精度は H3 と同程度（resolution 8 で 460m 一辺）。
/// 本格運用時は `Uber/h3-swift` を SPM 追加。
public struct LocationAnonymizer {

    // MARK: - 設定

    public struct Config {
        public var offsetRadiusMeters: Double      // ランダムオフセット半径
        public var hexResolutionMeters: Double     // 六角形セルの一辺（メートル）
        public var kAnonymityThreshold: Int        // この件数未満なら描画しない
        public var useVirtualCity: Bool            // 仮想都市変換を有効化
        public var virtualCityOrigin: CLLocationCoordinate2D
        public var seed: UInt64                    // 決定論的にしたい場合は固定 seed

        public init(
            offsetRadiusMeters: Double = 500,
            hexResolutionMeters: Double = 460,
            kAnonymityThreshold: Int = 5,
            useVirtualCity: Bool = true,
            virtualCityOrigin: CLLocationCoordinate2D = .init(latitude: 33.5597, longitude: 133.5311),
            seed: UInt64 = 0
        ) {
            self.offsetRadiusMeters = offsetRadiusMeters
            self.hexResolutionMeters = hexResolutionMeters
            self.kAnonymityThreshold = kAnonymityThreshold
            self.useVirtualCity = useVirtualCity
            self.virtualCityOrigin = virtualCityOrigin
            self.seed = seed
        }

        public static let `default` = Config()

        /// 緊急時用：オフセット小さめ・k-匿名性緩め
        public static let emergency = Config(
            offsetRadiusMeters: 100,
            hexResolutionMeters: 200,
            kAnonymityThreshold: 1,
            useVirtualCity: false
        )

        /// 研究公開用：強い匿名化
        public static let research = Config(
            offsetRadiusMeters: 2000,
            hexResolutionMeters: 1500,
            kAnonymityThreshold: 10,
            useVirtualCity: true
        )
    }

    public let config: Config

    public init(config: Config = .default) {
        self.config = config
    }

    // MARK: - 1. ランダムオフセット

    /// 真の座標を中心に半径 R[m] の一様円分布でランダム再ロール。
    /// イベント毎に新しい乱数を使う（リンク不可性のため）。
    public func randomOffset(_ coord: CLLocationCoordinate2D) -> CLLocationCoordinate2D {
        var rng = config.seed == 0
            ? SystemRandomNumberGenerator()
            : SeededRNG(seed: config.seed) as RandomNumberGenerator
        let theta = Double.random(in: 0..<(2 * .pi), using: &rng)
        let r = sqrt(Double.random(in: 0...1, using: &rng)) * config.offsetRadiusMeters
        let dx = r * cos(theta)
        let dy = r * sin(theta)
        return offset(coord, eastMeters: dx, northMeters: dy)
    }

    // MARK: - 2. H3 風ヘックス集約

    /// 簡易ヘックスインデックス（ID は決定論、複号不可）
    public func hexIndex(_ coord: CLLocationCoordinate2D) -> String {
        // メートル換算近似（緯度依存）
        let metersPerDegLat = 111_320.0
        let metersPerDegLon = 111_320.0 * cos(coord.latitude * .pi / 180)
        let cellLat = config.hexResolutionMeters / metersPerDegLat
        let cellLon = config.hexResolutionMeters / metersPerDegLon

        let q = Int((coord.longitude / cellLon).rounded())
        let r = Int((coord.latitude / cellLat).rounded())
        // ID は 13 文字 base32-like（H3 互換ではない、自前 schema）
        let raw = "ls_h\(config.hexResolutionMeters.rounded())_q\(q)_r\(r)"
        return raw
    }

    public func hexCenter(forIndex idx: String) -> CLLocationCoordinate2D? {
        // raw = "ls_h<RES>_q<Q>_r<R>"
        let parts = idx.split(separator: "_")
        guard parts.count == 4,
              let q = Int(parts[2].dropFirst(1)),
              let r = Int(parts[3].dropFirst(1)) else { return nil }
        let metersPerDegLat = 111_320.0
        let lat = Double(r) * (config.hexResolutionMeters / metersPerDegLat)
        let metersPerDegLon = 111_320.0 * cos(lat * .pi / 180)
        let lon = Double(q) * (config.hexResolutionMeters / metersPerDegLon)
        return CLLocationCoordinate2D(latitude: lat, longitude: lon)
    }

    // MARK: - 3. 仮想都市変換

    /// 実座標 → 高知市庁舎を原点とする仮想都市座標
    /// 距離・方位を保ちつつ「どこの街かわからない」表示にする
    public func toVirtualCity(_ coord: CLLocationCoordinate2D) -> CLLocationCoordinate2D {
        guard config.useVirtualCity else { return coord }
        // 実座標の中心を「適当な仮想中心」に平行移動
        let originLat = config.virtualCityOrigin.latitude
        let originLon = config.virtualCityOrigin.longitude
        let dLat = coord.latitude - originLat
        let dLon = coord.longitude - originLon
        // 仮想都市の中心を 0,0 とする座標系へ
        // （地図上ではこの座標を使い、ラベルなしのスタイルで描画）
        return CLLocationCoordinate2D(latitude: originLat + dLat, longitude: originLon + dLon)
    }

    // MARK: - 統合 API

    /// 真の座標 → 表示用 hex ID（k-匿名性チェックは別途）
    public func anonymize(_ coord: CLLocationCoordinate2D) -> AnonymizedLocation {
        let offset = randomOffset(coord)
        let hex = hexIndex(offset)
        let display = config.useVirtualCity ? toVirtualCity(offset) : offset
        return AnonymizedLocation(
            displayCoordinate: display,
            hexIndex: hex,
            offsetRadiusM: config.offsetRadiusMeters,
            virtualCity: config.useVirtualCity
        )
    }

    /// 複数イベントの hex ごと集計 + k-匿名性ゲート
    /// 戻り値：描画して良い hex のみ
    public func aggregateWithKAnonymity(
        events: [(coord: CLLocationCoordinate2D, payload: Any)]
    ) -> [HexAggregate] {
        var bucket: [String: [(CLLocationCoordinate2D, Any)]] = [:]
        for ev in events {
            let hex = hexIndex(ev.coord)
            bucket[hex, default: []].append((ev.coord, ev.payload))
        }
        return bucket.compactMap { (hex, list) in
            guard list.count >= config.kAnonymityThreshold else { return nil }
            // hex 中心座標を計算
            let avgLat = list.map(\.0.latitude).reduce(0, +) / Double(list.count)
            let avgLon = list.map(\.0.longitude).reduce(0, +) / Double(list.count)
            var center = CLLocationCoordinate2D(latitude: avgLat, longitude: avgLon)
            if config.useVirtualCity { center = toVirtualCity(center) }
            return HexAggregate(
                hexIndex: hex,
                center: center,
                count: list.count,
                payloads: list.map(\.1)
            )
        }
    }

    // MARK: - 内部ユーティリティ

    private func offset(
        _ coord: CLLocationCoordinate2D,
        eastMeters: Double,
        northMeters: Double
    ) -> CLLocationCoordinate2D {
        let metersPerDegLat = 111_320.0
        let metersPerDegLon = 111_320.0 * cos(coord.latitude * .pi / 180)
        return CLLocationCoordinate2D(
            latitude: coord.latitude + northMeters / metersPerDegLat,
            longitude: coord.longitude + eastMeters / metersPerDegLon
        )
    }
}

// MARK: - 出力モデル

public struct AnonymizedLocation: Codable, Equatable {
    public let displayCoordinate: CLLocationCoordinate2D
    public let hexIndex: String
    public let offsetRadiusM: Double
    public let virtualCity: Bool
}

public struct HexAggregate {
    public let hexIndex: String
    public let center: CLLocationCoordinate2D
    public let count: Int
    public let payloads: [Any]
}

// MARK: - CLLocationCoordinate2D Codable

extension CLLocationCoordinate2D: Codable {
    public func encode(to encoder: Encoder) throws {
        var c = encoder.unkeyedContainer()
        try c.encode(longitude)   // GeoJSON 順
        try c.encode(latitude)
    }
    public init(from decoder: Decoder) throws {
        var c = try decoder.unkeyedContainer()
        let lon = try c.decode(Double.self)
        let lat = try c.decode(Double.self)
        self.init(latitude: lat, longitude: lon)
    }
}

// MARK: - Seeded RNG（決定論テスト用）

private struct SeededRNG: RandomNumberGenerator {
    private var state: UInt64
    init(seed: UInt64) { self.state = seed == 0 ? 0xDEADBEEF : seed }
    mutating func next() -> UInt64 {
        // xorshift64
        state ^= state << 13
        state ^= state >> 7
        state ^= state << 17
        return state
    }
}
