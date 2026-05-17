import Foundation
import Combine

/// Simulator 專用：模擬感測器數據
/// 
/// 用途：
/// - Xcode Simulator 無法使用 CoreBluetooth
/// - 離線開發 UI 與資料流邏輯
/// - 單元測試
/// - Demo 展示
class MockSensorManager: SensorDataSource {
    
    // MARK: - Publishers
    
    private let dataSubject = PassthroughSubject<SensorData, Never>()
    var dataStream: AnyPublisher<SensorData, Never> {
        dataSubject.eraseToAnyPublisher()
    }
    
    @Published private(set) var connectedDevices: [BLEDeviceInfo] = []
    @Published private(set) var isScanning: Bool = false
    
    // MARK: - 配置
    
    enum MockScenario {
        case normal                    // 正常日常數據
        case heartRateSpike            // 心率異常飆升 (家暴/恐慌)
        case panicButtonPressed        // 求救按鈕觸發
        case hiddenCameraDetected      // 磁力計偵測到異常
        case childBehaviorAnomaly      // 幼童行為異常模式
        case multiDeviceSync           // 多裝置同步異常 (群體偵測)
    }
    
    var activeScenario: MockScenario = .normal
    private var cancellables = Set<AnyCancellable>()
    private var simulationTimer: Timer?
    
    // MARK: - 初始化
    
    init(scenario: MockScenario = .normal) {
        self.activeScenario = scenario
        setupMockDevices()
    }
    
    // MARK: - SensorDataSource Protocol
    
    func startScanning() {
        isScanning = true
        
        // 模擬 2 秒後找到裝置
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            self?.isScanning = false
        }
    }
    
    func stopScanning() {
        isScanning = false
    }
    
    func connect(to deviceID: String) {
        // 模擬連接成功
        print("[Mock] Connected to \(deviceID)")
    }
    
    func disconnect(from deviceID: String) {
        print("[Mock] Disconnected from \(deviceID)")
    }
    
    func subscribe(to types: [SensorType]) -> AnyPublisher<SensorData, Never> {
        dataStream.filter { types.contains($0.type) }.eraseToAnyPublisher()
    }
    
    // MARK: - 模擬控制
    
    func startSimulation() {
        stopSimulation()
        
        simulationTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            self?.emitMockData()
        }
        
        // 立即發送一筆
        emitMockData()
    }
    
    func stopSimulation() {
        simulationTimer?.invalidate()
        simulationTimer = nil
    }
    
    /// 手動觸發場景
    func triggerScenario(_ scenario: MockScenario) {
        activeScenario = scenario
        
        switch scenario {
        case .panicButtonPressed:
            emitButtonPress()
        case .heartRateSpike:
            emitHeartRateSpikeData(timestamp: Date())
        case .hiddenCameraDetected:
            emitMagnetometerSpike()
        default:
            emitMockData()
        }
    }
    
    // MARK: - 私有方法：數據生成
    
    private func setupMockDevices() {
        connectedDevices = [
            BLEDeviceInfo(
                id: "MOCK-HR-BAND-001",
                name: "Mi Band 8 (小華)",
                rssi: -67,
                manufacturerData: nil,
                advertisedServices: ["180D"],  // Heart Rate Service
                isConnectable: true,
                lastSeen: Date()
            ),
            BLEDeviceInfo(
                id: "MOCK-TAG-002",
                name: "Flic Button (媽媽)",
                rssi: -52,
                manufacturerData: Data([0x01, 0x02]),
                advertisedServices: ["FF01"],
                isConnectable: true,
                lastSeen: Date()
            ),
            BLEDeviceInfo(
                id: "MOCK-ENV-003",
                name: "SwitchBot Sensor",
                rssi: -74,
                manufacturerData: nil,
                advertisedServices: ["FE95"],
                isConnectable: true,
                lastSeen: Date()
            )
        ]
    }
    
    private func emitMockData() {
        let timestamp = Date()
        
        switch activeScenario {
        case .normal:
            emitNormalData(timestamp: timestamp)
        case .heartRateSpike:
            emitHeartRateSpikeData(timestamp: timestamp)
        case .panicButtonPressed:
            emitButtonPress()
        case .hiddenCameraDetected:
            emitMagnetometerSpike()
        case .childBehaviorAnomaly:
            emitChildAnomalyData(timestamp: timestamp)
        case .multiDeviceSync:
            emitMultiDeviceAnomaly(timestamp: timestamp)
        }
    }
    
    private func emitNormalData(timestamp: Date) {
        // 正常心率 60-90
        let hr = Double.random(in: 60...90)
        dataSubject.send(SensorData(
            timestamp: timestamp,
            type: .heartRate,
            value: hr,
            unit: "bpm",
            deviceID: "MOCK-HR-BAND-001",
            deviceName: "Mi Band 8",
            metadata: nil
        ))
        
        // 正常步數
        dataSubject.send(SensorData(
            timestamp: timestamp,
            type: .stepCount,
            value: Double.random(in: 0...5),
            unit: "steps",
            deviceID: "MOCK-HR-BAND-001",
            deviceName: "Mi Band 8",
            metadata: nil
        ))
    }
    
    private func emitHeartRateSpikeData(timestamp: Date) {
        // 模擬恐慌/運動時心率飆升
        let hr = Double.random(in: 120...160)
        dataSubject.send(SensorData(
            timestamp: timestamp,
            type: .heartRate,
            value: hr,
            unit: "bpm",
            deviceID: "MOCK-HR-BAND-001",
            deviceName: "Mi Band 8",
            metadata: ["alert": "HR_SPIKE", "note": "靜止狀態下異常高"]
        ))
        
        // 伴隨加速度異常
        dataSubject.send(SensorData(
            timestamp: timestamp,
            type: .accelerometer,
            value: Double.random(in: 5...9),
            unit: "m/s²",
            deviceID: "MOCK-HR-BAND-001",
            deviceName: "Mi Band 8",
            metadata: nil
        ))
    }
    
    private func emitButtonPress() {
        dataSubject.send(SensorData(
            timestamp: Date(),
            type: .buttonPress,
            value: 1,
            unit: "press",
            deviceID: "MOCK-TAG-002",
            deviceName: "Flic Button",
            metadata: ["pressType": "DOUBLE", "location": "媽媽口袋"]
        ))
    }
    
    private func emitMagnetometerSpike() {
        // 模擬偵測到電磁異常 (可能是隱藏攝影機)
        dataSubject.send(SensorData(
            timestamp: Date(),
            type: .magnetometer,
            value: Double.random(in: 150...300),
            unit: "μT",
            deviceID: "MOCK-PHONE",
            deviceName: "iPhone Internal",
            metadata: ["alert": "MAGNETIC_ANOMALY", "suspected_device": "hidden_camera"]
        ))
    }
    
    private func emitChildAnomalyData(timestamp: Date) {
        // 幼童異常行為：夜間心跳過快 + 翻身頻繁
        let hr = Double.random(in: 110...140)
        dataSubject.send(SensorData(
            timestamp: timestamp,
            type: .heartRate,
            value: hr,
            unit: "bpm",
            deviceID: "MOCK-HR-BAND-001",
            deviceName: "Mi Band 8",
            metadata: ["sleep_stage": "deep", "expected_hr": "65-80"]
        ))
        
        dataSubject.send(SensorData(
            timestamp: timestamp,
            type: .skinConductance,
            value: Double.random(in: 8...12),
            unit: "μS",
            deviceID: "MOCK-HR-BAND-001",
            deviceName: "Mi Band 8",
            metadata: ["stress_indicator": "high"]
        ))
    }
    
    private func emitMultiDeviceAnomaly(timestamp: Date) {
        // 模擬同一機構多個裝置同時異常
        for i in 0..<3 {
            let deviceIDs = ["CHILD-A", "CHILD-B", "CHILD-C"]
            dataSubject.send(SensorData(
                timestamp: timestamp,
                type: .heartRate,
                value: Double.random(in: 125...145),
                unit: "bpm",
                deviceID: deviceIDs[i],
                deviceName: "Device \(i+1)",
                metadata: ["institution": "XX幼兒園", "time_slot": "14:00-14:30"]
            ))
        }
    }
    
    deinit {
        stopSimulation()
    }
}
