import Foundation
import Combine

// MARK: - 感測器數據結構

struct SensorData: Identifiable {
    let id = UUID()
    let timestamp: Date
    let type: SensorType
    let value: Double
    let unit: String
    let deviceID: String
    let deviceName: String
    let metadata: [String: String]?
    
    var isAnomaly: Bool = false       // 由分析器標記
    var anomalySeverity: AnomalySeverity = .none
}

enum SensorType: String, CaseIterable {
    case heartRate = "heart_rate"
    case accelerometer = "accelerometer"
    case gyroscope = "gyroscope"
    case magnetometer = "magnetometer"
    case temperature = "temperature"
    case humidity = "humidity"
    case motion = "motion"
    case pressure = "pressure"
    case audioLevel = "audio_level"
    case buttonPress = "button_press"
    case location = "location"
    case stepCount = "step_count"
    case skinConductance = "skin_conductance"
    
    var displayName: String {
        switch self {
        case .heartRate: return "心率"
        case .accelerometer: return "加速度"
        case .gyroscope: return "陀螺儀"
        case .magnetometer: return "磁力計"
        case .temperature: return "溫度"
        case .humidity: return "濕度"
        case .motion: return "動作"
        case .pressure: return "壓力"
        case .audioLevel: return "音量"
        case .buttonPress: return "求救按鈕"
        case .location: return "定位"
        case .stepCount: return "步數"
        case .skinConductance: return "膚電反應"
        }
    }
    
    var icon: String {
        switch self {
        case .heartRate: return "heart.fill"
        case .accelerometer, .gyroscope, .motion: return "figure.walk.motion"
        case .magnetometer: return "bolt.magnet.fill"
        case .temperature: return "thermometer"
        case .humidity: return "humidity.fill"
        case .pressure: return "gauge.with.dots.needle.67percent"
        case .audioLevel: return "waveform"
        case .buttonPress: return "exclamationmark.circle.fill"
        case .location: return "location.fill"
        case .stepCount: return "shoe.2.fill"
        case .skinConductance: return "bolt.heart.fill"
        }
    }
}

enum AnomalySeverity: String {
    case none = "none"
    case low = "low"
    case medium = "medium"
    case high = "high"
    case critical = "critical"
    
    var color: String {
        switch self {
        case .none: return "gray"
        case .low: return "green"
        case .medium: return "yellow"
        case .high: return "orange"
        case .critical: return "red"
        }
    }
}

// MARK: - 感測器協定 (Protocol-Oriented)

/// 所有感測器的抽象接口
protocol SensorDataSource: AnyObject {
    /// 數據流 (Combine Publisher)
    var dataStream: AnyPublisher<SensorData, Never> { get }
    
    /// 當前連接的裝置列表
    var connectedDevices: [BLEDeviceInfo] { get }
    
    /// 掃描狀態
    var isScanning: Bool { get }
    
    /// 開始掃描周邊裝置
    func startScanning()
    
    /// 停止掃描
    func stopScanning()
    
    /// 連接特定裝置
    func connect(to deviceID: String)
    
    /// 斷開連接
    func disconnect(from deviceID: String)
    
    /// 訂閱特定類型的感測器數據
    func subscribe(to types: [SensorType]) -> AnyPublisher<SensorData, Never>
}

/// 藍牙裝置資訊
struct BLEDeviceInfo: Identifiable, Equatable {
    let id: String           // UUID string
    let name: String
    let rssi: Int            // 訊號強度
    let manufacturerData: Data?
    let advertisedServices: [String]
    let isConnectable: Bool
    let lastSeen: Date
    
    static func == (lhs: BLEDeviceInfo, rhs: BLEDeviceInfo) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - 感測器配置

struct SensorConfiguration {
    /// 異常閾值設定
    struct Threshold {
        let minValue: Double
        let maxValue: Double
        let sustainedDuration: TimeInterval  // 持續多久算異常
    }
    
    var heartRateThreshold: Threshold = Threshold(
        minValue: 40,      // 心搏過緩
        maxValue: 130,     // 靜止狀態下超過 130 算異常
        sustainedDuration: 60
    )
    
    var accelerometerThreshold: Threshold = Threshold(
        minValue: -8,
        maxValue: 8,        // 異常劇烈晃動
        sustainedDuration: 5
    )
    
    var magnetometerThreshold: Threshold = Threshold(
        minValue: -100,
        maxValue: 100,      // 電磁異常 (針孔攝影機偵測)
        sustainedDuration: 3
    )
    
    var audioLevelThreshold: Threshold = Threshold(
        minValue: 0,
        maxValue: 80,      // 分貝
        sustainedDuration: 30
    )
}

// MARK: - 感測器分析器

/// 偵測異常的引擎
class SensorAnalyzer {
    private var history: [SensorType: [SensorData]] = [:]
    private let maxHistorySize = 100
    private var config = SensorConfiguration()
    
    /// 分析單筆數據
    func analyze(_ data: SensorData) -> AnomalySeverity {
        // 存入歷史
        if history[data.type] == nil {
            history[data.type] = []
        }
        history[data.type]?.append(data)
        if history[data.type]!.count > maxHistorySize {
            history[data.type]?.removeFirst()
        }
        
        // 根據類型檢查閾值
        switch data.type {
        case .heartRate:
            return checkHeartRate(data)
        case .accelerometer:
            return checkAccelerometer(data)
        case .magnetometer:
            return checkMagnetometer(data)
        case .audioLevel:
            return checkAudioLevel(data)
        case .buttonPress:
            return .critical  // 求救按鈕直接危急
        default:
            return .none
        }
    }
    
    private func checkHeartRate(_ data: SensorData) -> AnomalySeverity {
        let threshold = config.heartRateThreshold
        if data.value > threshold.maxValue {
            // 檢查是否持續異常
            let recent = history[.heartRate]?.suffix(5) ?? []
            let sustained = recent.allSatisfy { $0.value > threshold.maxValue }
            return sustained ? .critical : .high
        }
        if data.value < threshold.minValue {
            return .high
        }
        return .none
    }
    
    private func checkAccelerometer(_ data: SensorData) -> AnomalySeverity {
        let threshold = config.accelerometerThreshold
        if abs(data.value) > threshold.maxValue {
            return .high
        }
        return .none
    }
    
    private func checkMagnetometer(_ data: SensorData) -> AnomalySeverity {
        let threshold = config.magnetometerThreshold
        if abs(data.value) > threshold.maxValue {
            // 可能偵測到電磁裝置
            return .medium
        }
        return .none
    }
    
    private func checkAudioLevel(_ data: SensorData) -> AnomalySeverity {
        let threshold = config.audioLevelThreshold
        if data.value > threshold.maxValue {
            return .medium
        }
        return .none
    }
    
    /// 群體異常分析 (跨使用者)
    static func analyzeGroupPattern(
        readings: [[SensorData]],
        institution: String
    ) -> GroupAnomalyResult? {
        // 簡化版：檢查同一機構多個使用者在相似時間點出現異常
        let anomalyByTime = readings.flatMap { $0 }
            .filter { $0.isAnomaly }
            .reduce(into: [:]) { dict, data in
                let hour = Calendar.current.component(.hour, from: data.timestamp)
                dict[hour, default: 0] += 1
            }
        
        if let peakHour = anomalyByTime.max(by: { $0.value < $1.value }),
           peakHour.value >= 3 {
            return GroupAnomalyResult(
                institution: institution,
                peakHour: peakHour.key,
                affectedCount: readings.count,
                confidence: min(Double(peakHour.value) / 5.0, 1.0)
            )
        }
        return nil
    }
}

struct GroupAnomalyResult {
    let institution: String
    let peakHour: Int
    let affectedCount: Int
    let confidence: Double  // 0.0 ~ 1.0
    
    var summary: String {
        "\(institution) 在 \(peakHour):00 時段有 \(affectedCount) 個裝置出現異常，信心指數 \(Int(confidence * 100))%"
    }
}
