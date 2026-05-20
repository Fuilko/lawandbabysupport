import SwiftUI

/// 反偷拍/反偵察掃描畫面
///
/// 功能：
/// 1. Wi-Fi 掃描異常 IoT 裝置
/// 2. 磁力計掃描電磁線圈 (針孔攝影機/麥克風)
/// 3. LiDAR 深度異常偵測 (iPhone Pro)
/// 4. AR 透視熱點圖 (配合外接 IR Dongle)
struct AntiSurveillanceView: View {
    @State private var scanMode: ScanMode = .wifi
    @State private var isScanning = false
    @State private var scanResults: [ScanResult] = []
    @State private var threatLevel: ThreatLevel = .safe
    @State private var showHardwareConnect = false
    
    enum ScanMode: String, CaseIterable {
        case wifi = "Wi-Fi 掃描"
        case magnetometer = "磁力計"
        case lidar = "LiDAR 深度"
        case infrared = "紅外線 (需外接)"
        
        var icon: String {
            switch self {
            case .wifi: return "wifi"
            case .magnetometer: return "bolt.magnet"
            case .lidar: return "camera.metering.center.weighted"
            case .infrared: return "eye.fill"
            }
        }
    }
    
    enum ThreatLevel: String {
        case safe = "安全"
        case low = "低風險"
        case medium = "中風險"
        case high = "高風險"
        case critical = "危急"
        
        var color: Color {
            switch self {
            case .safe: return .green
            case .low: return .blue
            case .medium: return .yellow
            case .high: return .orange
            case .critical: return .red
            }
        }
    }
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    // 威脅等級指示器
                    ThreatLevelIndicator(level: threatLevel, isScanning: isScanning)
                    
                    // 掃描模式選擇
                    ScanModeSelector(selectedMode: $scanMode)
                    
                    // 開始掃描按鈕
                    ScanButton(isScanning: $isScanning, mode: scanMode) {
                        startScan()
                    }
                    
                    // 掃描結果
                    if !scanResults.isEmpty {
                        ScanResultsList(results: scanResults)
                    }
                    
                    // 硬體擴充提示
                    HardwareExtensionCard(showConnect: $showHardwareConnect)
                    
                    // 使用指南
                    ScanGuideSection()
                }
                .padding()
            }
            .navigationTitle("反偵察掃描")
            .sheet(isPresented: $showHardwareConnect) {
                HardwareConnectSheet()
            }
        }
    }
    
    private func startScan() {
        isScanning = true
        scanResults = []
        
        // 模擬掃描過程
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            // 產生模擬結果
            switch scanMode {
            case .wifi:
                scanResults = simulateWifiScan()
            case .magnetometer:
                scanResults = simulateMagnetometerScan()
            case .lidar:
                scanResults = simulateLidarScan()
            case .infrared:
                scanResults = simulateInfraredScan()
            }
            
            // 計算威脅等級
            threatLevel = calculateThreatLevel(from: scanResults)
            isScanning = false
        }
    }
    
    private func simulateWifiScan() -> [ScanResult] {
        [
            ScanResult(
                type: .wifi,
                title: "可疑 IoT 裝置",
                description: "偵測到未知 IP Camera (MAC: A4:5E:60:XX:XX:XX)，正在進行大量上行傳輸",
                severity: .high,
                recommendation: "建議斷開該裝置網路連線，並記錄其 MAC 地址"
            ),
            ScanResult(
                type: .wifi,
                title: "路由器訊號異常",
                description: "2.4GHz 頻段出現不明 SSID 'ESP_Camera_01'",
                severity: .medium,
                recommendation: "可能是 ESP32-CAM 模組，常見於自製偷拍裝置"
            )
        ]
    }
    
    private func simulateMagnetometerScan() -> [ScanResult] {
        [
            ScanResult(
                type: .magnetometer,
                title: "電磁異常熱點",
                description: "於 (X:0.3, Y:-0.1) 偵測到 245 μT 異常磁場，疑似微型線圈",
                severity: .high,
                recommendation: "檢查該位置的煙霧偵測器、插座、裝飾品"
            )
        ]
    }
    
    private func simulateLidarScan() -> [ScanResult] {
        [
            ScanResult(
                type: .lidar,
                title: "深度異常點",
                description: "冷氣出風口偵測到 3mm 深度凹陷，形狀疑似鏡片",
                severity: .medium,
                recommendation: "建議使用放大鏡近距離檢查"
            )
        ]
    }
    
    private func simulateInfraredScan() -> [ScanResult] {
        [
            ScanResult(
                type: .infrared,
                title: "紅外線發射源",
                description: "偵測到 940nm 波長異常反射 (需外接 IR Dongle)",
                severity: .critical,
                recommendation: "極可能是夜視攝影機！立即遮蔽或移除"
            )
        ]
    }
    
    private func calculateThreatLevel(from results: [ScanResult]) -> ThreatLevel {
        let maxSeverity = results.map { $0.severityValue }.max() ?? 0
        switch maxSeverity {
        case 4: return .critical
        case 3: return .high
        case 2: return .medium
        case 1: return .low
        default: return .safe
        }
    }
}

// MARK: - 威脅等級指示器

struct ThreatLevelIndicator: View {
    let level: AntiSurveillanceView.ThreatLevel
    let isScanning: Bool
    @State private var pulse = false
    
    var body: some View {
        VStack(spacing: 12) {
            ZStack {
                Circle()
                    .fill(level.color.opacity(0.2))
                    .frame(width: 120, height: 120)
                    .scaleEffect(pulse ? 1.1 : 1.0)
                    .animation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true), value: pulse)
                
                Circle()
                    .fill(level.color.opacity(0.4))
                    .frame(width: 80, height: 80)
                
                Image(systemName: isScanning ? "radar" : "shield.checkered")
                    .font(.system(size: 32))
                    .foregroundColor(level.color)
            }
            .onAppear { pulse = isScanning }
            .onChange(of: isScanning) { pulse = $0 }
            
            Text(isScanning ? "掃描中..." : level.rawValue)
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(level.color)
            
            if isScanning {
                Text("正在分析環境數據")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(level.color.opacity(0.05))
        .cornerRadius(16)
    }
}

// MARK: - 掃描模式選擇器

struct ScanModeSelector: View {
    @Binding var selectedMode: AntiSurveillanceView.ScanMode
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("掃描模式")
                .font(.headline)
            
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                ForEach(AntiSurveillanceView.ScanMode.allCases, id: \.self) { mode in
                    ScanModeButton(
                        mode: mode,
                        isSelected: selectedMode == mode
                    ) {
                        selectedMode = mode
                    }
                }
            }
        }
    }
}

struct ScanModeButton: View {
    let mode: AntiSurveillanceView.ScanMode
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: mode.icon)
                    .font(.title2)
                Text(mode.rawValue)
                    .font(.caption)
                    .fontWeight(isSelected ? .bold : .regular)
            }
            .frame(maxWidth: .infinity, minHeight: 80)
            .background(isSelected ? Color.blue.opacity(0.1) : Color(.systemGray6))
            .foregroundColor(isSelected ? .blue : .primary)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 2)
            )
            .cornerRadius(12)
        }
    }
}

// MARK: - 掃描按鈕

struct ScanButton: View {
    @Binding var isScanning: Bool
    let mode: AntiSurveillanceView.ScanMode
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            HStack {
                if isScanning {
                    ProgressView()
                        .scaleEffect(1.2)
                        .tint(.white)
                } else {
                    Image(systemName: "magnifyingglass")
                }
                Text(isScanning ? "掃描中..." : "開始 \(mode.rawValue)")
                    .fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(isScanning ? Color.gray : Color.blue)
            .foregroundColor(.white)
            .cornerRadius(12)
        }
        .disabled(isScanning)
    }
}

// MARK: - 掃描結果

struct ScanResult: Identifiable {
    let id = UUID()
    let type: AntiSurveillanceView.ScanMode
    let title: String
    let description: String
    let severity: AntiSurveillanceView.ThreatLevel
    let recommendation: String
    
    var severityValue: Int {
        switch severity {
        case .safe: return 0
        case .low: return 1
        case .medium: return 2
        case .high: return 3
        case .critical: return 4
        }
    }
}

struct ScanResultsList: View {
    let results: [ScanResult]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("掃描結果 (\(results.count) 項)")
                .font(.headline)
            
            ForEach(results) { result in
                ScanResultCard(result: result)
            }
        }
    }
}

struct ScanResultCard: View {
    let result: ScanResult
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: result.type.icon)
                    .foregroundColor(result.severity.color)
                
                Text(result.title)
                    .font(.subheadline)
                    .fontWeight(.bold)
                
                Spacer()
                
                Text(result.severity.rawValue)
                    .font(.caption2)
                    .fontWeight(.bold)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 2)
                    .background(result.severity.color.opacity(0.2))
                    .foregroundColor(result.severity.color)
                    .clipShape(Capsule())
            }
            
            Text(result.description)
                .font(.body)
                .foregroundStyle(.secondary)
            
            HStack(spacing: 4) {
                Image(systemName: "lightbulb.fill")
                    .font(.caption)
                    .foregroundColor(.yellow)
                Text(result.recommendation)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .background(result.severity.color.opacity(0.05))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(result.severity.color.opacity(0.2), lineWidth: 1)
        )
        .cornerRadius(12)
    }
}

// MARK: - 硬體擴充

struct HardwareExtensionCard: View {
    @Binding var showConnect: Bool
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Image(systemName: "usb.fill")
                    .font(.title2)
                    .foregroundColor(.purple)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text("硬體擴充")
                        .font(.headline)
                    Text("連接外接感測器提升偵測能力")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                
                Spacer()
            }
            
            HStack(spacing: 8) {
                HardwareBadge(icon: "eye.fill", name: "IR Dongle")
                HardwareBadge(icon: "antenna.radiowaves.left.and.right", name: "RF 掃描器")
                HardwareBadge(icon: "camera.fill", name: "熱成像")
            }
            
            Button("連接裝置") {
                showConnect = true
            }
            .buttonStyle(.bordered)
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

struct HardwareBadge: View {
    let icon: String
    let name: String
    
    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: icon)
                .font(.caption)
            Text(name)
                .font(.caption2)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color.purple.opacity(0.1))
        .foregroundColor(.purple)
        .clipShape(Capsule())
    }
}

struct HardwareConnectSheet: View {
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Image(systemName: "usb.connector")
                    .font(.system(size: 64))
                    .foregroundColor(.purple)
                
                Text("連接外接感測器")
                    .font(.title2)
                    .fontWeight(.bold)
                
                Text("透過 Lightning / USB-C 連接 IR Dongle 或 RF 掃描器，提升反偷拍偵測能力")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                
                VStack(alignment: .leading, spacing: 12) {
                    HardwareStep(number: 1, text: "將 IR Dongle 插入 iPhone")
                    HardwareStep(number: 2, text: "App 自動偵測並啟用 AR 透視模式")
                    HardwareStep(number: 3, text: "緩慢掃描房間，尋找紅外線發射源")
                }
                .padding()
                
                Spacer()
                
                Button("了解") { dismiss() }
                    .buttonStyle(.borderedProminent)
                    .padding()
            }
            .padding()
            .navigationTitle("硬體擴充")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

struct HardwareStep: View {
    let number: Int
    let text: String
    
    var body: some View {
        HStack(spacing: 12) {
            Text("\(number)")
                .font(.caption)
                .fontWeight(.bold)
                .foregroundColor(.white)
                .frame(width: 24, height: 24)
                .background(Color.purple)
                .clipShape(Circle())
            
            Text(text)
                .font(.subheadline)
        }
    }
}

// MARK: - 使用指南

struct ScanGuideSection: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("掃描指南")
                .font(.headline)
            
            GuideItem(
                icon: "wifi",
                title: "Wi-Fi 掃描",
                description: "關閉房間所有已知裝置後，掃描剩餘的 IoT 裝置。注意 ESP32-CAM 等模組常用預設 SSID。"
            )
            
            GuideItem(
                icon: "bolt.magnet",
                title: "磁力計掃描",
                description: "將手機靠近可疑位置（冷氣口、插座、裝飾品），尋找超過 100 μT 的磁場異常。"
            )
            
            GuideItem(
                icon: "eye.slash.fill",
                title: "光學檢查",
                description: "關燈後使用手電筒尋找鏡片反光。配合外接 IR Dongle 可偵測肉眼不可見的紅外線夜視燈。"
            )
        }
    }
}

struct GuideItem: View {
    let icon: String
    let title: String
    let description: String
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(.blue)
                .frame(width: 24)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.subheadline)
                    .fontWeight(.medium)
                Text(description)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}
