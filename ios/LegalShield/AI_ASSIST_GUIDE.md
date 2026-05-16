# AI 輔助 Swift 開發最佳實踐

## 1. 工作流模式

### A. 規格先行 (Spec-First)
1. **先寫 README / 架構文件** — 讓 AI 理解整體設計
2. **再寫 Protocol / Interface** — 定義數據流與依賴
3. **最後實作 View / Service** — 避免來回修改

### B. 分層提示 (Layered Prompts)
```
層級 1: 架構 → "設計一個 BLE 感測器抽象層"
層級 2: 模型 → "定義 SensorData 結構與異常嚴重度枚舉"
層級 3: 實作 → "實作 MockSensorManager 遵循 SensorDataSource"
層級 4: UI   → "設計 SensorDashboardView 訂閱數據流"
```

## 2. 提示工程技巧

| 技巧 | 範例 |
|------|------|
| **角色設定** | "你是一名 iOS 安全工程師，請實作 AES-256-GCM 加密儲存" |
| **約束條件** | "使用 SwiftData，iOS 17+，不引入第三方依賴" |
| **範例驅動** | "參考以下 Evidence 結構，實作 Chain of Custody 驗證" |
| **反饋迴圈** | "這段程式碼在 Simulator 無法運作，請改用 Mock 方案" |

## 3. Xcode 專案生成

```bash
# 安裝 XcodeGen
brew install xcodegen

# 進入專案目錄
cd ~/工作用/lawandbabysupport/ios/LegalShield

# 生成 .xcodeproj
xcodegen generate

# 打開專案
open LegalShield.xcodeproj
```

## 4. 常見陷阱與解法

| 陷阱 | 解法 |
|------|------|
| AI 使用舊版 SwiftUI API | 明確指定 `@Observable` (iOS 17+) vs `ObservableObject` |
| 忽略 Info.plist 權限 | 每次新增功能（藍牙/相機/麥克風）先確認 plist |
| Simulator 無法測試 BLE | 使用 Protocol + MockManager，條件編譯切換 |
| 內存洩漏 | AI 常忘記 `[weak self]`，檢查所有閉包捕獲 |
| 錯誤處理不完整 | 要求 AI 補充 `LocalizedError` 與使用者友善訊息 |

## 5. 快速開發循環

```
1. 改需求 → 2. 貼給 AI → 3. 產生 Swift 檔案
4. `xcodegen generate` → 5. Cmd+R 測試 → 6. 回報錯誤給 AI
```

**建議批次操作**：一次產生 3-5 個相關檔案，減少上下文切換。

## 6. 測試策略

- **Unit Test**: 讓 AI 同步產生 `XCTestCase`，特別是：
  - SHA-256 哈希正確性
  - 證據鏈完整性驗證
  - 誘導問句正則匹配
  
- **UI Test**: 使用 Xcode Preview `#Preview` 快速視覺驗證

## 7. 與 Windows 後端協作

```swift
// LLMService.swift 中的 API 端點
var apiEndpoint: String = "http://100.76.218.124:8000"

// 開發時用 ngrok / Tailscale 暴露本地 Ollama
// 生產時改為 EC2 / Azure IP
```

## 8. 檔案組織慣例

```
LegalShield/
├── LegalShieldApp.swift      # @main + ModelContainer
├── Models/                   # SwiftData + 純數據結構
├── Services/                 # 商業邏輯 (BLE, Crypto, LLM)
├── ViewModels/               # @Observable / ObservableObject
├── Views/                    # SwiftUI View (細分畫面)
└── Tests/                    # XCTest
```

## 9. 下一步建議

1. **Xcode 中開啟專案**，解決編譯錯誤（AI 產的程式碼可能有小問題）
2. **在實機測試 BLE 掃描**，驗證 BLESensorManager
3. **部署 Windows Ollama API**，測試 LLMService 連線
4. **申請 Apple Developer**，準備 TestFlight 內測
