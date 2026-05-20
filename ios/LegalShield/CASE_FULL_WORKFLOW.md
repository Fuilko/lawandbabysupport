# LegalShield 案件全生命周期工作流
## 從證據採集到法庭提告的完整設計

---

## 一、豐田財団補助的定位修正

> **核心修正：豐田財団 CSR 補助 ≠ 學術研究，不需要大學合作。**

### 豐田財団要的是什麼？

豐田財団的「国内助成」屬於**社會貢獻型資助**，評估標準是：

| 項目 | 豐田財団要求 | 我們如何滿足 |
|------|-------------|-------------|
| 社會課題解決 | 児童虐待通報のデジタル化 | 平台讓児童相談所接收案件更快 |
| 現場業務改善 | 児童福祉士の負担軽減 | Dashboard 減少紙本填寫、自動路由 |
| 可量化成果 | 回應時間縮短 X%、案件處理量提升 Y% | Track B 平台數據自動生成報告 |
| 可持續性 | 補助結束後能否自給自足 | B2B2C 模式：向行政單位收取平台使用費 |

### 不需要的東西（之前誤解）

- ❌ 不需要大學合作
- ❌ 不需要 IRB 倫理審查
- ❌ 不需要學術論文
- ❌ 不需要嚴謹的研究方法論

### 需要的東西

- ✅ 3-5 分鐘成果影片（平台實際操作畫面）
- ✅ 專員滿意度調查（簡短問卷，5 個問題）
- ✅ 處理案件數與回應時間統計（Track B 自動產出）
- ✅ 與紙本通報的效率比較（如「以前平均 45 分鐘，現在 8 分鐘」）

---

## 二、通訊記錄導入證據機制

### 問題：LINE、郵件、Messenger 等通訊記錄是最重要的證據之一

在性騷擾、家暴、職場霸凌、契約糾紛中，**聊天記錄往往比照片更重要**。但這些證據分散在不同 App，用戶不知道如何合法保存。

### 支援的通訊平台

| 平台 | 導入方式 | 法律地位 |
|------|---------|---------|
| **LINE** | 截圖分享 → App 內匯入 | 日本民事訴訟法上可採信（需完整鏈） |
| **Email (Gmail/Outlook)** | 截圖或 .eml 匯入 | 電磁記錄，具證據能力 |
| **SMS/iMessage** | 截圖匯入 | 電磁記錄 |
| **WhatsApp/Telegram** | 截圖匯入 | 同上 |
| **Facebook Messenger** | 截圖匯入 | 同上 |
| **職場 Slack/Teams** | 截圖匯入 | 職場霸凌、勞動糾紛關鍵證據 |

### iOS 端實作：通訊證據匯入流程

```swift
// 用戶在 LINE 中看到關鍵對話 → 截圖 → 分享按鈕 → 選擇「LegalShield」
// App 接收到截圖後自動處理：

class CommunicationEvidenceImporter {
    
    /// 從 Share Sheet 接收通訊截圖
    func importScreenshot(image: UIImage, sourceApp: String, caseId: UUID) async throws -> Evidence {
        
        // 1. 圖片本身的 SHA-256
        guard let imageData = image.pngData() else { throw .importFailed }
        let imageHash = Evidence.computeSHA256(for: imageData)
        
        // 2. OCR 提取對話文字（Vision 框架本地執行）
        let recognizedText = try await performOCR(on: image)
        
        // 3. 自動解析對話結構
        let parsedMessages = parseConversation(text: recognizedText)
        // 結果：[
        //   { sender: "加害者", text: "妳不來我就公開那些照片", time: "23:45" },
        //   { sender: "受害者", text: "請不要這樣", time: "23:46" }
        // ]
        
        // 4. 生成結構化通訊記錄 JSON
        let communicationRecord = CommunicationRecord(
            sourceApp: sourceApp,          // "LINE", "Gmail"
            parsedMessages: parsedMessages,
            rawOCRText: recognizedText,
            screenshotHash: imageHash,
            importedAt: Date()
        )
        
        // 5. 儲存為 Evidence（類型：.screenshot + .transcript）
        let evidence = Evidence(
            caseId: caseId,
            type: .screenshot,
            fileName: "comm_\(sourceApp)_\(Date().iso8601).png",
            fileSize: imageData.count,
            sha256Hash: imageHash,
            // ... 其他欄位
        )
        
        // 6. 自動標註關鍵詞（本地 NLP）
        let dangerKeywords = detectThreatKeywords(in: recognizedText)
        // 如：「殺」「死」「公開照片」「不來就」「報復」「騷擾」
        
        // 7. 如果有威脅性關鍵詞，提升案件緊急等級
        if dangerKeywords.count > 0 {
            await escalateUrgency(caseId: caseId, reason: "通訊內容檢測到威脅性關鍵詞: \(dangerKeywords)")
        }
        
        return evidence
    }
}
```

### 關鍵功能：自動威脅檢測

```swift
struct ThreatDetectionResult {
    let hasThreat: Bool
    let keywords: [String]
    let threatLevel: ThreatLevel      // .low, .medium, .high, .critical
    let recommendedAction: String     // "建議立即申請保護令"
}

// 日本法對應的威脅類型
enum ThreatCategory {
    case physicalViolence      // 「殺す」「殴る」→ 刑法 222 条 脅迫罪
    case sexualCoercion       // 「写真公開」→ 刑法 222 条 + 性的脅迫
    case reputationalDamage    // 「会社に言う」→ 名誉毀損
    case economicCoercion      // 「給料減らす」→ 労基法違反
    case stalkingBehavior      // 「待ち伏せ」→ ストーカー規制法
}
```

---

## 三、證據統整 + LLM 生成司法報告

### 核心價值

用戶不會寫「告訴狀」「訴狀」「告發書」。平台把所有證據、時間線、法條分析統整後，由 LLM 生成可直接提交給檢察官/法官/警察的文書。

### 統整內容

一個案件開啟後，系統自動收集：

```
案件：XXX幼兒園兒少保護事件
├── 證據鏈（按時間排序）
│   ├── [2024-05-01 09:15] 照片：傷口瘀青（SHA-256: a1b2c3...）
│   ├── [2024-05-01 09:20] 錄音：受害者陳述（12分鐘，誘導問句：0）
│   ├── [2024-05-01 14:30] LINE截圖：老師威脅「不要告訴媽媽」
│   ├── [2024-05-02 10:00] 醫療記錄：診斷書（手腕挫傷）
│   └── [2024-05-03 11:00] 感測器：心率異常（BLE手環記錄）
│
├── 時間線自動重建
│   ├── 2024-04-28：異常行為開始
│   ├── 2024-05-01 08:30：事件發生（GPS: 幼兒園）
│   ├── 2024-05-01 09:15：首次採證
│   └── 2024-05-03：緊急轉介至東京都児童相談所
│
├── 法律分析（LLM RAG）
│   ├── 適用法條：児童虐待防止法第3条（通報義務）、刑法第223条（児童買春・児童ポルノ処罰）
│   ├── 證據力評估：照片（高）+ 錄音（高）+ LINE截圖（中）+ 醫療記錄（高）
│   ├── 訴訟策略：告訴 → 検察審査会（不起訴時）→ 民事損害賠償
│   └── 期限提醒：告訴期限（發現後 3 個月內）、民事請求（20年消滅時効）
│
└── 報告生成
    ├── 類型 A：檢察官告發書（刑事）
    ├── 類型 B：民事訴狀（損害賠償請求）
    ├── 類型 C：児童相談所通報書
    ├── 類型 D：保護令聲請書
    └── 類型 E：證據保全證明書（PDF，含所有 hash）
```

### LLM 生成報告流程（後端 Ollama）

```
📱 iPhone 打包請求 → {
  "case_id": "uuid",
  "report_type": "criminal_indictment",  // 刑事告訴狀
  "evidence_hashes": ["a1b2c3...", "d4e5f6..."],  // 只傳 hash
  "evidence_metadata": [          // 證據描述（去識別化）
    { "type": "photo", "date": "2024-05-01", "description": "手腕瘀青照片" },
    { "type": "audio", "date": "2024-05-01", "description": "受害者陳述錄音" }
  ],
  "timeline_events": [
    { "date": "2024-04-28", "event": "異常行為目擊" },
    { "date": "2024-05-01", "event": "傷害發生" }
  ],
  "legal_domain": "child_abuse",  // 法律領域
  "jurisdiction": "JP",             // 日本
  "victim_age": 6,                // 受害者年齡（去識別）
  "desired_outcome": "criminal_prosecution"  // 期望結果
}
    ↓
🖥️ 後端 FastAPI 接收 → 查詢 RAG（児童虐待防止法、刑法、民法的相關條文）
    ↓
🤖 Ollama LLM (RTX 4080) 生成報告：

「告訴状

告訴人：〇〇（匿名）
被疑者：〇〇 幼稚園教諭

【事実】
令和6年5月1日午前8時30分頃、東京都〇〇区の〇〇幼稚園において、
被疑者は告訴人（当時6歳）に対し、...

【証拠】
1. 写真（Exhibit A）：告訴人の右腕の瘀青。撮影日時：令和6年5月1日9:15。
   SHA-256: a1b2c3d4...（改竄不能）
2. 録音（Exhibit B）：告訴人の陳述。誘導的質問なし。
   所要時間：12分34秒。
3. LINEメッセージ（Exhibit C）：被疑者からの威嚇「ママに言うな」。

【適用法条】
• 刑法第223条（児童買春・児童ポルノに係る行為等の処罰）
• 児童虐待防止法第3条（通報義務）

【求め】
被疑者を厳正に処罰されるよう告訴する。

附記：本状に添付の証拠は、LegalShield 司法級証拠管理システムにより
SHA-256 ハッシュ化・暗号化保存されており、改竄が不可能であることを証明する
証拠保全証明書（別冊）を添付する。」
    ↓
📄 回傳 PDF（日語/繁體中文雙語）
📱 iPhone 本地儲存 PDF → 用戶確認後可列印或電子提交
```

### 報告類型對應表

| 報告類型 | 適用情境 | 提交對象 | 法律依據 |
|---------|---------|---------|---------|
| **刑事告訴狀** | 犯罪行為（傷害、性侵、虐待） | 警察/檢察官 | 刑事訴訟法第230条 |
| **民事訴狀** | 損害賠償（醫療費、精神賠償） | 法院 | 民法第709条 |
| **行政審査請求書** | 對行政處分不服 | 行政機關 | 行政不服審査法 |
| **保護令聲請書** | 家暴、跟蹤騷擾 | 家庭法院 | 配偶者暴力防止法 |
| **児童相談所通報書** | 兒少保護 | 児童相談所 | 児童虐待防止法第3条 |
| **労働基準監督署申告書** | 勞動糾紛 | 労基署 | 労働基準法 |
| **消費者申訴書** | 消費詐欺、契約陷阱 | 消費者センター | 消費者契約法 |

---

## 四、轉介資訊提取與同步機制

### 問題：用戶按下緊急按鈕後，合作夥伴（児童相談所）需要什麼資訊？

**不能給的（隱私保護）：**
- ❌ 原始照片/錄音內容
- ❌ 精確 GPS 座標
- ❌ 受害者真實姓名
- ❌ 未經同意的通訊內容

**必須給的（有效介入）：**
- ✅ 案件類型（兒少虐待 / 家暴 / 跟蹤騷擾）
- ✅ 緊急等級（critical / high / medium）
- ✅ 大致區域（東京都新宿區，非精確地址）
- ✅ 證據數量與類型（5張照片、2段錄音、3張LINE截圖）
- ✅ 事件描述摘要（去識別化：「幼兒園教師對6歲兒童的體罰」）
- ✅ 受害者年齡/性別（用於判斷児童相談所還是DV中心）
- ✅ 用戶留下的聯繫方式（電話/郵件，用於專員回撥）

### 轉介資料包結構

```swift
struct ReferralPackage {
    // 去識別化案件摘要
    let caseSummary: CaseSummary        // 不含姓名、精確地址
    
    // 證據索引（不含內容，只有 hash 和描述）
    let evidenceIndex: [EvidenceIndexItem]
    // 例：[
    //   { type: .photo, hash: "a1b2...", description: "手腕瘀青", timestamp: "2024-05-01T09:15:00" },
    //   { type: .screenshot, hash: "c3d4...", description: "LINE威脅截圖", timestamp: "2024-05-01T14:30:00" }
    // ]
    
    // 用戶聯繫資訊（需用戶明確同意分享）
    let contactInfo: UserContactInfo?    // 電話、郵件、LINE ID
    
    // 用戶自述（去識別化：將「我」改為「受害者」，將人名改為「〇〇」）
    let anonymizedStatement: String
    
    // 系統自動分析
    let threatAssessment: ThreatAssessment  // 威脅等級、建議行動
    let legalDomain: LegalDomain           // 適用法律領域
    
    // 時間線
    let timeline: [TimelineEvent]         // 按時間排序的事件摘要
    
    // 用戶授權範圍
    let consentScope: ConsentScope        // 用戶勾選了哪些分享項目
}
```

### 同步流程

```
📱 iPhone 本地
├── 用戶按下緊急按鈕
├── 彈窗確認：「您確定要將此案件轉介給東京都児童相談所嗎？」
├── 顯示將分享的內容清單（勾選項）：
│   ☐ 區域位置（東京都新宿區）
│   ☐ 案件類型與描述
│   ☐ 證據索引（不含原始內容）
│   ☐ 您的聯繫電話
│   ☐ LINE 通訊記錄摘要
│   ☐ 允許專員查看原始證據
│
└── 用戶確認後，生成 ReferralPackage
    ↓
🔐 加密傳輸（TLS 1.3）
    ↓
🖥️ 後端接收
├── 驗證用戶身份與同意範圍
├── 比對管轄區域 → 確認接收方為「東京都児童相談所新宿分所」
├── 檢查接收方值班狀態
├── 去識別化處理（再次確認無個資洩露）
└── 推送至 Partner Dashboard（去識別化案件卡）
    ↓
👤 專員在 Dashboard 看到：
    【新案件】兒少保護 - 緊急
    區域：東京都新宿區
    摘要：幼兒園教師對6歲女童的體罰及威脅
    證據：5項（照片3、錄音1、LINE截圖1）
    聯繫：090-XXXX-XXXX（已授權）
    
    [確認介入] [暫不介入] [需要更多資訊]
    ↓
👤 專員點擊「確認介入」→ 輸入理由：「児童虐待防止法第6条に基づく介入」
    ↓
🖥️ 後端記錄審計日誌 → 解密顯示完整聯繫資訊
    ↓
👤 專員撥打用戶電話 → 啟動救援
```

---

## 五、預防二次受害機制（性暴力/兒少保護專用）

### 什麼是二次受害？

> 受害者在報案、接受調查、出庭過程中，因重複陳述、不當詢問、資訊洩露等再次受到心理傷害。

### 平台設計的五道防線

#### 防線 1：一次性完整記錄（避免重複陳述）

```
傳統流程（造成二次受害）：
受害者 → 報警（口述1次）→ 檢察官詢問（口述2次）→ 法庭（口述3次）
每次都要回憶細節，每次都要面對不同人的質疑。

LegalShield 流程：
受害者 → App 內錄音/錄影陳述（1次）→ 加密儲存
         → 檢察官/法官直接調閱錄音（不再詢問細節）
         → 法庭播放錄音（受害者可不出庭）
```

**技術實現：**
- App 提供「引導式陳述」功能：按時間順序引導受害者描述事件
- 自動檢測誘導問句：確保錄音品質符合法庭要求
- 錄音標記為「isFirstDisclosure = true」：法庭上具有更高證據力

#### 防線 2：陪同人機制

```swift
struct AccompanimentSettings {
    var enabled: Bool = false
    var accompanistName: String?      // 陪同人姓名（律師/社工/親友）
    var accompanistRole: String?      // "律師", "支援センター職員", "母"
    var shareEvidenceWithAccompanist: Bool = false  // 是否分享證據索引
    var accompanistContact: String?   // 陪同人聯繫方式
}
```

- 用戶可指定一位「陪同人」，專員介入時同步聯繫陪同人
- 陪同人可獲得案件進度通知（需用戶授權）
- 特別適用：未成年受害者、身心障礙受害者、外國籍受害者

#### 防線 3：匿名/化名處理

```swift
struct IdentityProtection {
    var usePseudonym: Bool = true
    var pseudonym: String = "Aさん"   // 法庭上的化名
    var realNameSharedWith: [String]  // 只有誰知道真實姓名
        // 預設只有：用戶本人、指定的律師、児童相談所專員（經授權）
    
    var blurFaceInEvidence: Bool = true  // 自動模糊照片中人臉
    var maskLocationPrecision: Bool = true // GPS 只顯示到區域級別
}
```

- 所有對外文件（告訴狀、通報書）自動使用化名
- 照片證據可選擇「自動模糊人臉」（本地 Vision 處理）
- 媒體報導時無法透過平台資料識別受害者

#### 防線 4：快速通道（避免等待造成的傷害）

```
一般流程：報案 → 3天後才聯繫 → 1週後安排詢問 → 2個月後開庭

性暴力快速通道：
報案（App 緊急按鈕）→ 30分鐘內專員回撥
         → 24hr 內安排醫療採證（性侵證據保全）
         → 72hr 內完成首次陳述錄音
         → 1週內轉介心理諮商
```

**技術實現：**
- 性暴力案件自動標記為「fast-track」
- 路由邏輯優先分配給性暴力專門機構（而非一般児童相談所）
- 自動推播醫療機構清單（可在24hr內採集性侵證據的醫院）

#### 防線 5：資訊最小化原則

```
誰知道什麼：

用戶本人：知道一切（原始證據、完整對話、精確位置）
    ↓
平台後端：只知道 hash + 區域 + 類型（無法看內容）
    ↓
合作夥伴專員：經授權後知道聯繫方式 + 案件摘要（無法直接看證據內容）
    ↓
檢察官/法官：經用戶授權後，由用戶主動匯出證據包提交（平台不直接傳給司法機關）
    ↓
對方當事人/被告：永遠不知道（除非法庭開示程序）
```

### 性暴力案件特殊功能

```swift
enum SexualViolenceProtectionFeature {
    // 1. 醫療機構快速導航
    case medicalFacilityLocator    // 顯示附近的「性暴力被害者支援医療機関」
    
    // 2. 證據保全計時器
    case evidencePreservationTimer  // 性侵證據最好在72hr內採集，倒數計時
    
    // 3. 心理諮商轉介
    case counselingReferral        // 一鍵轉介至心理諮商（不經過平台）
    
    // 4. 保護令輔助
    case protectionOrderAssistant  // 自動生成保護令聲請書
    
    // 5. 法庭陪同預約
    case courtAccompanimentBooking // 預約支援センター的法庭陪同服務
    
    // 6. 媒體應對指南
    case mediaResponseGuide        // 如果事件被媒體報導，如何保護隱私
}
```

---

## 六、民事領域擴展

### 新增案件類型

```swift
// 在 CaseCategory 中新增/強化
enum CaseCategory {
    // 原有類型...
    
    // 民事領域擴展
    case contractDispute = "contract_dispute"           // 契約糾紛（不限於陷阱）
    case productDefect = "product_defect"               // 產品缺陷/售後不履行
    case manufacturerLiability = "manufacturer_liability" // 製造商責任
    case policeInaction = "police_inaction"            // 警察不作為
    case defamation = "defamation"                     // 名譽毀損
    case unjustEnrichment = "unjust_enrichment"         // 不當得利
    case neighborDispute = "neighbor_dispute"           // 鄰居糾紛
    case trafficAccident = "traffic_accident"          // 交通事故
    case medicalMalpractice = "medical_malpractice"    // 醫療過失
}
```

### 各類型的證據收集策略

#### 1. 契約糾紛（Contract Dispute）

| 證據類型 | 收集方式 | 法律依據 |
|---------|---------|---------|
| 契約書原文 | 拍照/OCR/匯入PDF | 民法第521条（契約の成立） |
| 往來郵件 | 郵件截圖匯入 | 電磁記録 |
| 付款記錄 | 銀行轉帳截圖 | 民法第533条（債務の履行） |
| 口頭約定錄音 | 錄音證據 | 民法第522条（意思表示） |
| 契約履行狀況 | 照片/時間戳 | 民法第415条（債務不履行） |

**LLM 報告生成：** 自動分析契約條款，標註「有利條款」「不利條款」「缺失條款」，生成「損害賠償請求書」。

#### 2. 產品購買後問題（製造商不履行責任）

```swift
struct ProductLiabilityEvidence {
    let purchaseReceipt: Evidence       // 購買發票/收據
    let warrantyCard: Evidence?         // 保證書
    let defectPhotos: [Evidence]        // 缺陷照片（多角度）
    let communicationWithSeller: [Evidence]  // 與賣家/客服的通訊記錄
    let expertOpinion: Evidence?        // 第三方鑑定意見
    let similarComplaints: [Evidence]?  // 同類產品其他消費者的投訴
}
```

**適用法條：** 製造物責任法、消費者契約法、民法第415条（債務不履行）

**報告生成：** 「製造物責任請求書」，包含：
- 產品缺陷的具體描述
- 損害計算（維修費、替代購買費、精神損害）
- 製造商的免責條款是否有效（消費者契約法第10条）

#### 3. 精神病患攻擊但警察不受理

```swift
struct PoliceInactionCase {
    let incidentEvidence: [Evidence]     // 攻擊事件的證據（照片、錄音、醫療記錄）
    let policeReportRecord: Evidence?  // 報案紀錄（如果有）
    let policeRefusalEvidence: Evidence? // 警察不受理的證據（錄音、書面回覆）
    let perpetratorMedicalRecords: Evidence? // 加害者的精神診斷（如果已知）
    let witnessStatements: [Evidence] // 目擊者證詞
}
```

**這是最複雜的情境**，因為涉及：
- 刑法上的責任能力問題（刑法第39条：心神喪失者不罰）
- 行政救濟：對警察不作為的審査請求
- 民事救濟：對加害者監護人的損害賠償請求
- 社會福利：加害者的強制住院（精神保健福祉法）

**平台如何協助：**

```
步驟 1：用戶記錄攻擊事件（拍照/錄音/醫療記錄）
    ↓
步驟 2：用戶報警 → 如果警察以「心神喪失」為由不受理
    → App 自動記錄：報案時間、警局名稱、承辦警員編號（如有）
    → 提示：「請要求警察出具『不受理理由書』」
    ↓
步驟 3：App 自動生成三條並行路徑
    ├── 路徑 A：行政救濟
    │   └── 生成「審査請求書」→ 對警察署長提出審査請求
    │       （理由：不作為違法 → 要求依法處理）
    │
    ├── 路徑 B：民事救濟
    │   └── 生成「損害賠償請求書」→ 對加害者監護人提起訴訟
    │       （理由：民法第713条：監督義務違反）
    │
    └── 路徑 C：社會福利
        └── 生成「精神保健福祉法申請書」→ 申請加害者強制住院
            （理由：自身或他人有危害之虞）
    ↓
步驟 4：平台同步資訊給「精神保健福祉相談窓口」或「認知症の人・
        精神障害者人権センター」（依案件類型自動路由）
```

---

## 七、總結：資訊流與權限架構

```
┌─────────────────────────────────────────────────────────────────┐
│                        資訊層級架構                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: 用戶裝置（iPhone）                                    │
│  ───────────────────────────────────────────────────────────  │
│  • 原始證據（照片/錄音/通訊記錄/文件）                           │
│  • 精確 GPS 座標                                                │
│  • 真實姓名、身分證號                                           │
│  • 加密金鑰（Keychain）                                         │
│  • 權限：用戶 100% 控制                                         │
│                                                                 │
│  Layer 2: 平台後端（AWS EC2 / Windows）                          │
│  ───────────────────────────────────────────────────────────  │
│  • 證據 hash（非原始內容）                                       │
│  • 區域名稱（非精確地址）                                        │
│  • 案件類型、緊急等級                                            │
│  • 路由邏輯、夥伴管理                                            │
│  • 去識別化統計                                                 │
│  • 權限：平台看不到原始內容，只做索引與路由                      │
│                                                                 │
│  Layer 3: 合作夥伴（児童相談所 / DV中心）                         │
│  ───────────────────────────────────────────────────────────  │
│  • 經授權的聯繫方式（電話/郵件）                                  │
│  • 案件摘要（去識別化）                                          │
│  • 證據索引（不含內容）                                          │
│  • 點擊「確認介入」後才能解密完整個資                              │
│  • 權限：需專員授權 + 審計日誌                                   │
│                                                                 │
│  Layer 4: 司法機關（檢察官/法官/警察）                           │
│  ───────────────────────────────────────────────────────────  │
│  • 經用戶主動生成的「證據匯出包」                                │
│  • PDF 報告（告訴狀/訴狀/證據目錄）                               │
│  • 證據保全證明書（含 SHA-256 hash）                             │
│  • 權限：平台不直接傳給司法機關，由用戶主動提交                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 八、行動清單

### 立即（Phase 0）
- [ ] 修正豐田財団補助申請策略：強調社會影響力，而非學術研究
- [ ] 在緊急轉介同意書中加入「通訊記錄分享」獨立勾選項
- [ ] 設計「陪同人」功能 UI

### Phase 1（0-3 月）
- [ ] 實作 `CommunicationEvidenceImporter`（LINE/郵件截圖匯入 + OCR）
- [ ] 實作 `CaseReportGenerator`（統整證據 + 呼叫 Ollama 生成報告）
- [ ] 新增 CaseCategory：`.contractDispute`, `.productDefect`, `.policeInaction`
- [ ] 實作 `SecondaryVictimizationProtection`（快速通道 + 匿名化 + 陪同人）
- [ ] 後端：Partner Dashboard 顯示去識別化案件卡

### Phase 2（3-6 月）
- [ ] 實作「引導式陳述」功能（一次性完整記錄，避免重複詢問）
- [ ] 實作「醫療機構快速導航」（性暴力被害者支援医療機関）
- [ ] 實作「保護令輔助」功能（自動生成聲請書）
- [ ] 實作「警察不作為」三軌並行路徑（行政救濟 + 民事救濟 + 社會福利）
- [ ] 生成第一份 LLM 報告樣本（測試法庭可用性）
