# LegalShield iOS — 原生 SwiftUI 防禦系統

> **設計目標**: 將手機變成「數位黑盒子」，結合既有藍牙裝置形成去中心化感測網路（LASS），並透過 LLM 提供法務級分析與協助。

---

## 系統架構

```
┌─────────────────────────────────────────────┐
│  iPhone (SwiftUI + CoreBluetooth)            │
│                                              │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Views   │  │ ViewModels│  │ Services   │  │
│  │ SwiftUI │  │ Combine   │  │ Protocol   │  │
│  │         │  │           │  │ Oriented   │  │
│  └────┬────┘  └─────┬─────┘  └─────┬──────┘  │
│       │             │              │          │
│       └─────────────┼──────────────┘          │
│                     │                         │
│  ┌──────────────────┼──────────────────────┐ │
│  │     Sensor Abstraction Layer            │ │
│  │  ┌──────────────┐  ┌─────────────────┐  │ │
│  │  │ MockSensor   │  │ BLESensorManager │  │ │
│  │  │ (Simulator)  │  │ (Real Device)    │  │ │
│  │  └──────────────┘  └─────────────────┘  │ │
│  └─────────────────────────────────────────┘ │
│                     │                         │
│  ┌──────────────────┼──────────────────────┐ │
│  │   Evidence Chain  │   LLM Integration    │ │
│  │  ┌────────────┐  │  ┌────────────────┐  │ │
│  │  │ CryptoKit  │  │  │ On-Device      │  │ │
│  │  │ SHA-256    │  │  │ (Apple MLX)    │  │ │
│  │  │ SwiftData  │  │  │ + Cloud API    │  │ │
│  │  └────────────┘  │  └────────────────┘  │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
            │
            ▼ BLE
┌─────────────────────────────────────────────┐
│  External Sensors (Existing Market Products)  │
│  • Bluetooth Heart Rate Band                  │
│  • Bluetooth Tag (AirTag-like panic button)   │
│  • Bluetooth Environmental Sensor             │
│  • AirPods (audio stream)                     │
│  • Apple Watch (health data via HealthKit)    │
└─────────────────────────────────────────────┘
```

---

## 核心功能

### 1. 證據保全 (Evidence Vault)
- **相機**: 拍照/錄影即時 SHA-256 哈希 + GPS + 時間戳
- **錄音**: 背景錄音（緊急模式），防誘導問句偵測
- **感測器數據**: 心跳、震動、定位等自動上鏈
- **CryptoKit**: 硬體級加密，證據鏈不可竄改

### 2. 防誘導取證 Copilot
- 即時語音轉文字 (Speech framework)
- LLM 判斷是否為「誘導性問句」
- 紅燈警告 + 建議開放式問句替代

### 3. 異常行為偵測 (Anomaly Detection)
- 多維度生理數據分析（心跳、睡眠、活動）
- 群體比對（零知識證明保護隱私）
- LLM 生成行為分析報告

### 4. 反偵察 (Anti-Surveillance)
- Wi-Fi 掃描異常 IoT 設備
- 磁力計掃描電磁線圈（麥克風/攝影機）
- LiDAR 深度異常偵測（iPhone Pro）
- AR 透視熱點圖（配合外接 IR Dongle）

### 5. 法律文書生成
- 自動彙整證據鏈
- LLM 生成刑事告發狀 / 準備書面
- 內建 12+ 種日本/台灣法律範本

---

## 快速開始

### 前置需求
- macOS 14+ ( Sonoma )
- Xcode 15+
- iOS 17+ (SwiftData, CryptoKit P-256)
- 實體 iPhone (Simulator 不支援 CoreBluetooth)

### 建立專案

```bash
# 1. 安裝 XcodeGen (如果尚未安裝)
brew install xcodegen

# 2. 進入目錄
cd ios/LegalShield

# 3. 產生 .xcodeproj
xcodegen generate

# 4. 開啟 Xcode
open LegalShield.xcodeproj
```

### 在 Simulator 中開發

使用 `MockSensorManager` 模擬所有感測器數據，無需實體裝置即可開發 UI 與資料流邏輯。

```swift
// 切換感測器來源
#if targetEnvironment(simulator)
let sensorManager: SensorDataSource = MockSensorManager()
#else
let sensorManager: SensorDataSource = BLESensorManager()
#endif
```

### 在實體裝置測試

1. 連接 iPhone
2. 設定 Signing & Capabilities (Apple ID)
3. 啟用 Background Modes: `Uses Bluetooth LE accessories`
4. Run

---

## 藍牙裝置整合指南

### 支援的既有產品類型

| 裝置類型 | 品牌範例 | 數據流 | 用途 |
|----------|----------|--------|------|
| 心率手環 | Xiaomi Mi Band, Garmin | HR BPM | 異常心跳觸發錄音 |
| 藍牙按鈕 | Flic, Tile | Click Event | 一鍵求救/證據保全 |
| 環境感測 | SwitchBot, Sensirion | Temp/Humidity/Motion | 環境異常偵測 |
| 藍牙麥克風 | Hollyland Lark | Audio Stream | 高品質取證錄音 |
| Apple Watch | Apple | HealthKit | 全面生理監測 |

### 配對方式

App 不需要「正式配對」。透過 BLE Scan 接收廣播封包 (Advertisement) 即可獲取數據。這意味著任何發送標準 BLE GATT 數據的裝置都能被整合。

---

## LLM 整合策略

### 端側 (On-Device) — 隱私優先
- **Apple MLX**: iOS 17+ 可跑 3B-7B 小模型
- **CoreML**: 意圖分類、簡易 QA
- 用途: 誘導問句偵測、基礎法條查詢

### 雲端 API — 複雜分析
- 僅上傳「去識別化結構化數據」
- JSON 格式: `{ timestamps, hr_values, anomaly_scores }`
- 無原始錄音、無照片、無個人識別資訊

### Prompt 設計

見 `Services/InterviewCopilot.swift` 與 `Services/LLMService.swift`

---

## 募資產品規劃

### 軟體訂閱 (App Store)
- **免費版**: 基礎錄音 + 1 個案件管理
- **Pro 月訂**: NT$480/月 — 無限案件 + LLM 分析 + 反偵察掃描
- **Pro 年訂**: NT$4,800/年 — 上述全部 + 文書生成

### 硬體套裝 (嘖嘖早鳥)
- **基礎套裝**: App Pro 1年 + 藍牙求救按鈕 x2
- **家庭套裝**: App Pro 1年 + 藍牙手環 x2 + 求救按鈕 x2
- **專業套裝**: App Pro 終身 + 外接 IR 熱成像 Dongle

---

## 專案結構

```
LegalShield/
├── LegalShieldApp.swift          # App Entry + DI Container
├── Models/
│   ├── Case.swift                # 案件模型 (SwiftData)
│   ├── Evidence.swift            # 證據模型 (含 SHA256)
│   └── SensorReading.swift       # 感測器讀數
├── Services/
│   ├── SensorProtocols.swift     # 感測器抽象協定
│   ├── MockSensorManager.swift   # Simulator 假數據
│   ├── BLESensorManager.swift    # CoreBluetooth 實作
│   ├── EvidenceManager.swift     # 證據保全 + CryptoKit
│   ├── LLMService.swift          # LLM 呼叫 (本地+雲端)
│   └── InterviewCopilot.swift   # 防誘導取證 Copilot
├── Views/
│   ├── ContentView.swift         # 主畫面
│   ├── EvidenceCaptureView.swift # 證據拍攝/錄音
│   ├── InterviewAssistView.swift # 訪談輔助畫面
│   └── SensorDashboardView.swift # 感測器儀表板
└── ViewModels/
    └── CaseViewModel.swift       # 案件邏輯
```

---

*LegalShield iOS — 被害者を支援し、誰も1人にはしない。*
