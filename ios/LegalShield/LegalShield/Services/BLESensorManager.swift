import Foundation
import Combine
import CoreBluetooth

/// 實體裝置的 CoreBluetooth 管理器
/// 
/// 支援裝置：
/// - 心率手環 (Heart Rate GATT Service 0x180D)
/// - 藍牙按鈕 (自訂 Service)
/// - 環境感測器 (Environmental Sensing 0x181A)
/// - 運動感測器 (Accelerometer 等)
///
/// ⚠️ 需要實體 iPhone + 藍牙權限
class BLESensorManager: NSObject, SensorDataSource {
    
    // MARK: - Publishers
    
    private let dataSubject = PassthroughSubject<SensorData, Never>()
    var dataStream: AnyPublisher<SensorData, Never> {
        dataSubject.eraseToAnyPublisher()
    }
    
    @Published private(set) var connectedDevices: [BLEDeviceInfo] = []
    @Published private(set) var isScanning: Bool = false
    
    // MARK: - CoreBluetooth
    
    private var centralManager: CBCentralManager!
    private var discoveredPeripherals: [UUID: CBPeripheral] = [:]
    private var connectedPeripherals: [UUID: CBPeripheral] = [:]
    
    // 感測器特徵 UUID 映射
    private let serviceUUIDs: [CBUUID] = [
        CBUUID(string: "180D"),  // Heart Rate
        CBUUID(string: "181A"),  // Environmental Sensing
        CBUUID(string: "180A"),  // Device Information
        CBUUID(string: "FF01"),  // Custom Button Service (Flic, etc.)
    ]
    
    private let characteristicUUIDs: [CBUUID] = [
        CBUUID(string: "2A37"),  // Heart Rate Measurement
        CBUUID(string: "2A6E"),  // Temperature
        CBUUID(string: "2A6F"),  // Humidity
        CBUUID(string: "2A19"),  // Battery Level
    ]
    
    // MARK: - 初始化
    
    override init() {
        super.init()
        centralManager = CBCentralManager(delegate: self, queue: .global())
    }
    
    // MARK: - SensorDataSource Protocol
    
    func startScanning() {
        guard centralManager.state == .poweredOn else {
            print("[BLE] Bluetooth not powered on. State: \(centralManager.state.rawValue)")
            return
        }
        
        isScanning = true
        centralManager.scanForPeripherals(
            withServices: serviceUUIDs,
            options: [CBCentralManagerScanOptionAllowDuplicatesKey: false]
        )
        print("[BLE] Started scanning for peripherals...")
    }
    
    func stopScanning() {
        isScanning = false
        centralManager.stopScan()
        print("[BLE] Stopped scanning")
    }
    
    func connect(to deviceID: String) {
        guard let uuid = UUID(uuidString: deviceID),
              let peripheral = discoveredPeripherals[uuid] else {
            print("[BLE] Device not found: \(deviceID)")
            return
        }
        
        centralManager.connect(peripheral, options: nil)
        print("[BLE] Connecting to \(peripheral.name ?? "Unknown")...")
    }
    
    func disconnect(from deviceID: String) {
        guard let uuid = UUID(uuidString: deviceID),
              let peripheral = connectedPeripherals[uuid] else { return }
        
        centralManager.cancelPeripheralConnection(peripheral)
        connectedPeripherals.removeValue(forKey: uuid)
        updateConnectedDevices()
    }
    
    func subscribe(to types: [SensorType]) -> AnyPublisher<SensorData, Never> {
        dataStream.filter { types.contains($0.type) }.eraseToAnyPublisher()
    }
    
    // MARK: - 私有方法
    
    private func updateConnectedDevices() {
        connectedDevices = connectedPeripherals.values.map { peripheral in
            BLEDeviceInfo(
                id: peripheral.identifier.uuidString,
                name: peripheral.name ?? "Unknown Device",
                rssi: -50,  // 連接後無法取得 RSSI
                manufacturerData: nil,
                advertisedServices: [],
                isConnectable: true,
                lastSeen: Date()
            )
        }
    }
    
    private func parseHeartRateData(_ data: Data, from peripheral: CBPeripheral) -> SensorData? {
        guard data.count >= 2 else { return nil }
        
        let flags = data[0]
        let is16Bit = (flags & 0x01) != 0
        let hasEnergy = (flags & 0x08) != 0
        
        var offset = 1
        var heartRate: Double = 0
        
        if is16Bit {
            heartRate = Double(UInt16(data[offset]) | (UInt16(data[offset + 1]) << 8))
            offset += 2
        } else {
            heartRate = Double(data[offset])
            offset += 1
        }
        
        return SensorData(
            timestamp: Date(),
            type: .heartRate,
            value: heartRate,
            unit: "bpm",
            deviceID: peripheral.identifier.uuidString,
            deviceName: peripheral.name ?? "HR Device",
            metadata: nil
        )
    }
    
    private func parseEnvironmentalData(_ data: Data, characteristicUUID: CBUUID, from peripheral: CBPeripheral) -> SensorData? {
        // 簡化解析
        guard data.count >= 2 else { return nil }
        
        let value = Double(UInt16(data[0]) | (UInt16(data[1]) << 8)) / 100.0
        
        let sensorType: SensorType
        let unit: String
        
        if characteristicUUID == CBUUID(string: "2A6E") {
            sensorType = .temperature
            unit = "°C"
        } else if characteristicUUID == CBUUID(string: "2A6F") {
            sensorType = .humidity
            unit = "%"
        } else {
            return nil
        }
        
        return SensorData(
            timestamp: Date(),
            type: sensorType,
            value: value,
            unit: unit,
            deviceID: peripheral.identifier.uuidString,
            deviceName: peripheral.name ?? "ENV Device",
            metadata: nil
        )
    }
}

// MARK: - CBCentralManagerDelegate

extension BLESensorManager: CBCentralManagerDelegate {
    
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        switch central.state {
        case .poweredOn:
            print("[BLE] Bluetooth is powered on")
        case .poweredOff:
            print("[BLE] Bluetooth is powered off")
        case .unauthorized:
            print("[BLE] Bluetooth unauthorized - check Info.plist permissions")
        case .unsupported:
            print("[BLE] Bluetooth unsupported on this device")
        default:
            print("[BLE] Bluetooth state: \(central.state.rawValue)")
        }
    }
    
    func centralManager(_ central: CBCentralManager,
                        didDiscover peripheral: CBPeripheral,
                        advertisementData: [String: Any],
                        rssi RSSI: NSNumber) {
        
        discoveredPeripherals[peripheral.identifier] = peripheral
        
        let deviceInfo = BLEDeviceInfo(
            id: peripheral.identifier.uuidString,
            name: peripheral.name ?? "Unknown",
            rssi: RSSI.intValue,
            manufacturerData: advertisementData[CBAdvertisementDataManufacturerDataKey] as? Data,
            advertisedServices: (advertisementData[CBAdvertisementDataServiceUUIDsKey] as? [CBUUID])?.map { $0.uuidString } ?? [],
            isConnectable: advertisementData[CBAdvertisementDataIsConnectable] as? Bool ?? false,
            lastSeen: Date()
        )
        
        // 更新 UI 的設備列表 (這裡簡化處理)
        print("[BLE] Discovered: \(deviceInfo.name) (RSSI: \(deviceInfo.rssi))")
    }
    
    func centralManager(_ central: CBCentralManager,
                        didConnect peripheral: CBPeripheral) {
        print("[BLE] Connected to \(peripheral.name ?? "Unknown")")
        connectedPeripherals[peripheral.identifier] = peripheral
        peripheral.delegate = self
        peripheral.discoverServices(serviceUUIDs)
        updateConnectedDevices()
    }
    
    func centralManager(_ central: CBCentralManager,
                        didDisconnectPeripheral peripheral: CBPeripheral,
                        error: Error?) {
        print("[BLE] Disconnected from \(peripheral.name ?? "Unknown")")
        connectedPeripherals.removeValue(forKey: peripheral.identifier)
        updateConnectedDevices()
    }
    
    func centralManager(_ central: CBCentralManager,
                        didFailToConnect peripheral: CBPeripheral,
                        error: Error?) {
        print("[BLE] Failed to connect: \(error?.localizedDescription ?? "Unknown error")")
    }
}

// MARK: - CBPeripheralDelegate

extension BLESensorManager: CBPeripheralDelegate {
    
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        guard let services = peripheral.services else { return }
        
        for service in services {
            print("[BLE] Discovered service: \(service.uuid)")
            peripheral.discoverCharacteristics(characteristicUUIDs, for: service)
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral,
                    didDiscoverCharacteristicsFor service: CBService,
                    error: Error?) {
        guard let characteristics = service.characteristics else { return }
        
        for characteristic in characteristics {
            print("[BLE] Discovered characteristic: \(characteristic.uuid)")
            
            if characteristic.properties.contains(.notify) {
                peripheral.setNotifyValue(true, for: characteristic)
                print("[BLE] Subscribed to notifications for \(characteristic.uuid)")
            }
            
            if characteristic.properties.contains(.read) {
                peripheral.readValue(for: characteristic)
            }
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral,
                    didUpdateValueFor characteristic: CBCharacteristic,
                    error: Error?) {
        guard let data = characteristic.value else { return }
        
        var sensorData: SensorData?
        
        switch characteristic.uuid {
        case CBUUID(string: "2A37"):  // Heart Rate
            sensorData = parseHeartRateData(data, from: peripheral)
        case CBUUID(string: "2A6E"), CBUUID(string: "2A6F"):
            sensorData = parseEnvironmentalData(data, characteristicUUID: characteristic.uuid, from: peripheral)
        default:
            print("[BLE] Unhandled characteristic: \(characteristic.uuid)")
        }
        
        if let data = sensorData {
            dataSubject.send(data)
        }
    }
    
    func peripheral(_ peripheral: CBPeripheral,
                    didUpdateNotificationStateFor characteristic: CBCharacteristic,
                    error: Error?) {
        if let error = error {
            print("[BLE] Notification error: \(error.localizedDescription)")
            return
        }
        print("[BLE] Notification state updated for \(characteristic.uuid): \(characteristic.isNotifying)")
    }
}
