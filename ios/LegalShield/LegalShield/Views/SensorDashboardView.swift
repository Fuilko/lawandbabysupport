import SwiftUI
import Combine

/// 感測器儀表板 — 藍牙裝置數據視覺化
struct SensorDashboardView: View {
    @StateObject private var sensorManager: SensorDataSource
    @State private var selectedTypes: Set<SensorType> = [.heartRate, .accelerometer]
    @State private var readings: [SensorData] = []
    @State private var analyzer = SensorAnalyzer()
    @State private var showAnomalyAlert = false
    @State private var latestAnomaly: SensorData?
    
    init() {
        #if targetEnvironment(simulator)
        _sensorManager = StateObject(wrappedValue: MockSensorManager(scenario: .normal))
        #else
        _sensorManager = StateObject(wrappedValue: BLESensorManager())
        #endif
    }
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    // 裝置掃描區
                    DeviceScanSection(manager: sensorManager)
                    
                    // 感測器類型選擇
                    SensorTypeSelector(selectedTypes: $selectedTypes)
                    
                    // 即時數據卡片
                    ForEach(Array(selectedTypes), id: \.self) { type in
                        if let latest = readings.filter({ $0.type == type }).last {
                            SensorDataCard(data: latest)
                        }
                    }
                    
                    // 數據趨勢圖 (簡化版)
                    if !readings.isEmpty {
                        TrendChartView(readings: readings.filter { selectedTypes.contains($0.type) })
                    }
                    
                    // 異常警報
                    if showAnomalyAlert, let anomaly = latestAnomaly {
                        AnomalyAlertCard(data: anomaly)
                    }
                }
                .padding()
            }
            .navigationTitle("感測器儀表板")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { sensorManager.startScanning() }) {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
        }
        .onAppear {
            startDataCollection()
        }
        .onDisappear {
            if let mock = sensorManager as? MockSensorManager {
                mock.stopSimulation()
            }
        }
    }
    
    private func startDataCollection() {
        // 啟動模擬 (Simulator) 或掃描 (實機)
        if let mock = sensorManager as? MockSensorManager {
            mock.startSimulation()
        } else {
            sensorManager.startScanning()
        }
        
        // 訂閱數據流
        sensorManager.subscribe(to: Array(selectedTypes))
            .receive(on: DispatchQueue.main)
            .sink { data in
                readings.append(data)
                // 限制歷史數據量
                if readings.count > 200 {
                    readings.removeFirst(readings.count - 200)
                }
                
                // 分析異常
                let severity = analyzer.analyze(data)
                if severity != .none {
                    var anomaly = data
                    anomaly.isAnomaly = true
                    anomaly.anomalySeverity = severity
                    latestAnomaly = anomaly
                    showAnomalyAlert = true
                }
            }
            .store(in: &cancellables)
    }
    
    @State private var cancellables = Set<AnyCancellable>()
}

// MARK: - 裝置掃描區

struct DeviceScanSection: View {
    @ObservedObject var manager: SensorDataSource
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("已連接裝置")
                    .font(.headline)
                
                Spacer()
                
                if manager.isScanning {
                    HStack(spacing: 4) {
                        ProgressView()
                            .scaleEffect(0.8)
                        Text("掃描中...")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            
            if manager.connectedDevices.isEmpty {
                HStack {
                    Image(systemName: "bluetooth.slash")
                        .foregroundStyle(.secondary)
                    Text("未發現藍牙裝置")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding()
                .frame(maxWidth: .infinity)
                .background(Color(.systemGray6))
                .cornerRadius(8)
            } else {
                ForEach(manager.connectedDevices) { device in
                    DeviceRow(device: device)
                }
            }
        }
    }
}

struct DeviceRow: View {
    let device: BLEDeviceInfo
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "sensor.tag.fill")
                .foregroundColor(.blue)
                .frame(width: 32, height: 32)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(device.name)
                    .font(.subheadline)
                    .fontWeight(.medium)
                Text("RSSI: \(device.rssi) dBm")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            
            Spacer()
            
            ConnectionStatusIndicator(isConnected: device.isConnectable)
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(8)
    }
}

struct ConnectionStatusIndicator: View {
    let isConnected: Bool
    
    var body: some View {
        Circle()
            .fill(isConnected ? Color.green : Color.gray)
            .frame(width: 10, height: 10)
    }
}

// MARK: - 感測器類型選擇器

struct SensorTypeSelector: View {
    @Binding var selectedTypes: Set<SensorType>
    
    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(SensorType.allCases, id: \.self) { type in
                    SensorTypeChip(
                        type: type,
                        isSelected: selectedTypes.contains(type)
                    ) {
                        if selectedTypes.contains(type) {
                            selectedTypes.remove(type)
                        } else {
                            selectedTypes.insert(type)
                        }
                    }
                }
            }
        }
    }
}

struct SensorTypeChip: View {
    let type: SensorType
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 4) {
                Image(systemName: type.icon)
                    .font(.caption)
                Text(type.displayName)
                    .font(.caption)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(isSelected ? Color.blue : Color(.systemGray5))
            .foregroundColor(isSelected ? .white : .primary)
            .clipShape(Capsule())
        }
    }
}

// MARK: - 數據卡片

struct SensorDataCard: View {
    let data: SensorData
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: data.type.icon)
                .font(.title2)
                .foregroundColor(data.isAnomaly ? .red : .blue)
                .frame(width: 40, height: 40)
            
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(data.type.displayName)
                        .font(.subheadline)
                        .fontWeight(.medium)
                    
                    if data.isAnomaly {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.red)
                            .font(.caption)
                    }
                }
                
                HStack(alignment: .lastTextBaseline, spacing: 4) {
                    Text(String(format: "%.1f", data.value))
                        .font(.title3)
                        .fontWeight(.bold)
                    Text(data.unit)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                
                Text("來源: \(data.deviceName)")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 2) {
                Text(formatTime(data.timestamp))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(data.isAnomaly ? Color.red.opacity(0.05) : Color(.systemGray6))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(data.isAnomaly ? Color.red.opacity(0.2) : Color.clear, lineWidth: 1)
        )
        .cornerRadius(12)
    }
    
    private func formatTime(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: date)
    }
}

// MARK: - 趨勢圖 (簡化條狀圖)

struct TrendChartView: View {
    let readings: [SensorData]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("數據趨勢 (最近 30 筆)")
                .font(.headline)
            
            let recentReadings = Array(readings.suffix(30))
            let maxValue = recentReadings.map { $0.value }.max() ?? 1
            let minValue = recentReadings.map { $0.value }.min() ?? 0
            let range = maxValue - minValue
            
            HStack(alignment: .bottom, spacing: 2) {
                ForEach(recentReadings.indices, id: \.self) { index in
                    let reading = recentReadings[index]
                    let normalized = range > 0 ? (reading.value - minValue) / range : 0.5
                    
                    RoundedRectangle(cornerRadius: 2)
                        .fill(reading.isAnomaly ? Color.red : colorForType(reading.type))
                        .frame(width: 8, height: max(CGFloat(normalized) * 100, 4))
                }
            }
            .frame(height: 100)
            .frame(maxWidth: .infinity, alignment: .center)
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
    
    private func colorForType(_ type: SensorType) -> Color {
        switch type {
        case .heartRate: return .red
        case .accelerometer, .gyroscope, .motion: return .green
        case .magnetometer: return .purple
        case .temperature: return .orange
        case .humidity: return .blue
        case .audioLevel: return .yellow
        case .buttonPress: return .red
        default: return .gray
        }
    }
}

// MARK: - 異常警報卡

struct AnomalyAlertCard: View {
    let data: SensorData
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "exclamationmark.octagon.fill")
                    .font(.title2)
                    .foregroundColor(.red)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text("異常警報")
                        .font(.headline)
                        .foregroundColor(.red)
                    Text("\(data.type.displayName): \(String(format: "%.1f", data.value)) \(data.unit)")
                        .font(.subheadline)
                }
                
                Spacer()
            }
            
            Text("設備: \(data.deviceName)")
                .font(.caption)
                .foregroundStyle(.secondary)
            
            Button("標記為證據") {
                // 將此異常記錄到當前案件
            }
            .buttonStyle(.borderedProminent)
            .tint(.red)
        }
        .padding()
        .background(Color.red.opacity(0.05))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.red.opacity(0.3), lineWidth: 2)
        )
        .cornerRadius(12)
    }
}
