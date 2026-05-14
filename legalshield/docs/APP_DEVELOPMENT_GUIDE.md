# LegalShield APP 開發技術指南

> **目標**: 將現有資料庫與 AI 系統轉化為可上架的 iOS / Android APP
> **讀者**: 開發者、技術合伙人、投資人技術盡職調査

---

## 目錄

1. [現有技術資產盤點](#1-現有技術資產盤點)
2. [APP 化路徑選擇](#2-app-化路徑選擇)
3. [端末內 AI 推論實作](#3-端末內-ai-推論實作)
4. [向量資料庫端末化](#4-向量資料庫端末化)
5. [手機原生功能調用](#5-手機原生功能調用)
6. [隱私與安全架構](#6-隱私與安全架構)
7. [開發時程與里程碑](#7-開發時程與里程碑)
8. [開發者招募](#8-開發者招募)

---

## 1. 現有技術資產盤點

### 1.1 資料層（已完成）

| 資料集 | 規模 | 格式 | 位置 |
|--------|------|------|------|
| 國法全文 | 623,703 chunks | Parquet + LanceDB | `knowledge/vectors/` |
| 判例全文 | 724,443 chunks | Parquet + LanceDB | `knowledge/vectors/` |
| e-Stat 統計 | 885 表 | Parquet | `knowledge/vectors/` |
| 全國熱線 | 24 條 | CSV | `knowledge/seeds/` |
| 加害者側寫 | 17 類型 | Python dict + JSON | `backend/perpetrator_profiler.py` |
| 犯罪分類學 | 17 類型 | Markdown | `docs/CRIME_TAXONOMY_EXTENDED.md` |

### 1.2 AI 層（已完成原型）

| 模組 | 功能 | 狀態 |
|------|------|------|
| `victim_assistant.py` | 5重角色 AI（緊急・證據・法律・策略・轉介） | ✅ 可執行 |
| `perpetrator_profiler.py` | 加害者側寫・狡辯分析・反論生成 | ✅ 可執行 |
| `anti_grafting.py` | 防吃案報告書・警察交涉腳本 | ✅ 可執行 |
| `evidence_vault.py` | 證據保全・雜湊・加密・證明書 | ✅ 可執行 |
| `jstage_analyzer.py` | 學術論文分析 | ✅ 可執行 |

### 1.3 前端原型（已完成）

| 原型 | 技術 | 位置 |
|------|------|------|
| Streamlit Demo | Python Streamlit | `frontend/streamlit_demo.py` |
| 緊急模式 + トリアージ HTML | 純 HTML/CSS/JS | `frontend/triage_onboarding.html` |
| パートナー Pitch Deck | HTML | `docs/PARTNER_PITCH_DECK.html` |
| 統合介紹頁 | HTML | `docs/LEGALSHIELD_INTRO_COMPREHENSIVE.html` |

---

## 2. APP 化路徑選擇

### 2.1 三條路徑比較

| 路徑 | 技術 | 優點 | 缺點 | 推薦度 |
|------|------|------|------|--------|
| **A. PWA (Web APP)** | Next.js / React + Service Worker | 2週內上線、無需商店審核、跨平台 | 原生功能受限（SMS・離線 AI 較弱） | ⭐⭐⭐⭐ <br> MVP 首選 |
| **B. Flutter** | Dart + Flutter SDK | 一套程式碼 iOS+Android、效能好、原生功能完整 | 需學習 Dart、初期設定較複雜 | ⭐⭐⭐⭐⭐ <br> 正式版推薦 |
| **C. React Native** | JavaScript + React Native | JS 生態系龐大、開發者易找 | 效能略遜、版本碎片化嚴重 | ⭐⭐⭐⭐ |

### 2.2 建議採用「漸進式路徑」

```
Phase 0 (現在): Streamlit Demo → 驗證概念、收集回饋
Phase 1 (1-2月): PWA → 快速上線、測試使用者行為
Phase 2 (3-4月): Flutter MVP → 原生功能、端末 AI、商店上架
Phase 3 (6-12月): Flutter Full → 完整功能、自治体 SaaS 連携
```

---

## 3. 端末內 AI 推論實作

### 3.1 為什麼必須端末內推論？

被害人的手機可能在：
- 地下室（DV 避難）
- 飛行模式（控制中的監禁）
- 鄉下（網路不穩）
- 需要絕對隱私（不想讓伺服器知道內容）

**結論：AI 推論必須完全在端末內完成。**

### 3.2 模型選擇（端末可跑的小模型）

| 模型 | 大小 | 語言 | 用途 | 推論速度 |
|------|------|------|------|---------|
| **Phi-3 Mini** | 3.8B | 多語言含日語 | 對話・策略模擬 | 中 |
| **Gemma 2B** | 2B | 多語言含日語 | 對話・法律分析 | 快 |
| **Llama-3.2 1B** | 1B | 多語言含日語 | 意圖分類・トリアージ | 極快 |
| **Whisper Tiny** | 39M | 多語言 | 語音轉文字 | 快 |

### 3.3 端末推論程式碼範例（Flutter + ONNX）

```dart
// Flutter + ONNX Runtime Mobile
import 'package:onnxruntime/onnxruntime.dart';

class LegalShieldAI {
  late OrtSession _session;

  Future<void> loadModel() async {
    // 從 APP bundle 載入量化模型
    final modelPath = await _getModelPath('legalshield_gemma_2b.onnx');
    final sessionOptions = OrtSessionOptions();
    _session = OrtSession.fromFile(modelPath, sessionOptions);
  }

  Future<String> infer(String userInput) async {
    // 1. 意圖分類（トリアージ）
    final intent = await _classifyIntent(userInput);

    // 2. 根據意圖呼叫對應角色
    switch (intent) {
      case 'emergency':
        return await _emergencyResponder(userInput);
      case 'evidence':
        return await _evidenceCollector(userInput);
      case 'legal':
        return await _legalAnalyst(userInput);
      case 'strategy':
        return await _strategySimulator(userInput);
      case 'referral':
        return await _referralNavigator(userInput);
      default:
        return await _generalSupport(userInput);
    }
  }

  Future<String> _legalAnalyst(String query) async {
    // 端末內 RAG：查詢向量資料庫
    final relevantLaws = await _localVectorSearch(query, topK: 5);
    // 組合 Prompt
    final prompt = _buildLegalPrompt(query, relevantLaws);
    // 推論
    final output = await _runInference(prompt);
    return output;
  }
}
```

### 3.4 模型量化策略

```python
# Python 端模型量化腳本（開發者用）
from optimum.onnxruntime import ORTModelForCausalLM
from transformers import AutoTokenizer

model = ORTModelForCausalLM.from_pretrained(
    "google/gemma-2b",
    export=True,
    provider="CPUExecutionProvider",
)
tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b")

# 儲存量化模型（INT8）
model.save_pretrained("legalshield_gemma_2b_onnx")
tokenizer.save_pretrained("legalshield_gemma_2b_onnx")
```

---

## 4. 向量資料庫端末化

### 4.1 資料庫大小估算

| 資料集 | 原始大小 | 量化後（端末） | 壓縮率 |
|--------|---------|--------------|--------|
| 國法 623K | ~2GB | ~400MB | 80% |
| 判例 724K | ~3GB | ~500MB | 83% |
| e-Stat 885 | ~100MB | ~20MB | 80% |
| 合計 | ~5.1GB | ~920MB | ~82% |

**結論：920MB 的端末資料庫是可行的。**（現代手機儲存 64GB+）

### 4.2 LanceDB 嵌入式使用

```dart
// Flutter + LanceDB（嵌入式）
import 'package:lance_db/lance_db.dart';

class LegalShieldDB {
  late LanceTable _lawTable;
  late LanceTable _caseTable;

  Future<void> initialize() async {
    final dbPath = await _getLocalDBPath();
    final db = await LanceDB.connect(dbPath);

    // 開啟現有表（首次啟動時從伺服器同步）
    _lawTable = await db.openTable('elaws_vectors');
    _caseTable = await db.openTable('precedent_vectors');
  }

  Future<List<Map<String, dynamic>>> searchLaws(
    String query,
    {int topK = 5}
  ) async {
    // 1. 將查詢文本轉為向量（端末內 MiniLM 模型）
    final queryVector = await _embedText(query);

    // 2. 向量検索
    final results = await _lawTable.search(queryVector)
      .limit(topK)
      .execute();

    return results.map((r) => r.metadata).toList();
  }
}
```

### 4.3 首次同步策略

```
使用者安裝 APP
  ↓
首次啟動：下載 ~920MB 資料庫壓縮包
  ↓
背景解壓 + 建立索引（約 2-5 分鐘）
  ↓
之後：僅增量更新（每週 ~10-50MB）
  ↓
離線完全可用
```

---

## 5. 手機原生功能調用

### 5.1 功能總表

| 功能 | Flutter 套件 | React Native 套件 | PWA API |
|------|-------------|-------------------|---------|
| **GPS** | `geolocator` | `@react-native-community/geolocation` | Geolocation API ✅ |
| **相機** | `image_picker` + `camera` | `react-native-image-picker` | MediaDevices API ⚠️ |
| **麥克風** | `flutter_sound` + `speech_to_text` | `@react-native-voice/voice` | MediaRecorder API ⚠️ |
| **SMS** | `flutter_sms` | `react-native-sms` | ❌ 不可（需原生） |
| **通知** | `flutter_local_notifications` | `@notifee/react-native` | Notifications API ✅ |
| **生物辨識** | `local_auth` | `@react-native-biometrics` | WebAuthn ✅ |
| **離線儲存** | `hive` + `sqflite` | `AsyncStorage` + `SQLite` | IndexedDB ✅ |

### 5.2 GPS 實作（Flutter）

```dart
import 'package:geolocator/geolocator.dart';

Future<Position?> getCurrentLocation() async {
  // 檢查權限
  LocationPermission permission = await Geolocator.checkPermission();
  if (permission == LocationPermission.denied) {
    permission = await Geolocator.requestPermission();
    if (permission == LocationPermission.denied) return null;
  }

  // 取得高精度位置
  return await Geolocator.getCurrentPosition(
    desiredAccuracy: LocationAccuracy.high,
  );
}

// 模糊化位置（隱私保護）
Map<String, double> obfuscateLocation(Position pos) {
  // 僅保留到小數點後 2 位（約 1km 精度）
  return {
    'latitude': (pos.latitude * 100).round() / 100,
    'longitude': (pos.longitude * 100).round() / 100,
  };
}
```

### 5.3 相機 + 證據水印（Flutter）

```dart
import 'package:image_picker/image_picker.dart';
import 'package:image/image.dart' as img;
import 'package:crypto/crypto.dart';

Future<void> captureEvidence() async {
  final picker = ImagePicker();
  final photo = await picker.pickImage(source: ImageSource.camera);
  if (photo == null) return;

  // 1. 讀取圖片
  final bytes = await photo.readAsBytes();
  final image = img.decodeImage(bytes)!;

  // 2. 計算 SHA-256
  final hash = sha256.convert(bytes).toString();

  // 3. 取得位置與時間
  final position = await getCurrentLocation();
  final timestamp = DateTime.now().toIso8601String();

  // 4. 添加水印（不可移除的數位簽章）
  final watermarked = _addWatermark(image, hash: hash, time: timestamp, location: position);

  // 5. AES-256 加密儲存
  await _saveEncrypted(watermarked, filename: 'evidence_${timestamp}.jpg');
}
```

### 5.4 緊急 SMS（Flutter）

```dart
import 'package:flutter_sms/flutter_sms.dart';

Future<void> sendEmergencySMS() async {
  final contacts = await _getEmergencyContacts(); // 最多3人
  final location = await getCurrentLocation();
  final obfuscated = obfuscateLocation(location!);

  final message = '''
【LegalShield 自動緊急通知】
${await _getUserDisplayName()} が緊急事態に遭遇しました。
位置：${obfuscated['latitude']}, ${obfuscated['longitude']}（都道府県レベル）
時刻：${DateTime.now().toIso8601String()}

このメッセージは自動生成されたものです。
本人の確認が取れない場合、最寄りの支援機関に連絡してください。
'''; // ⚠️ 不送精確 GPS，僅模糊位置

  await sendSMS(message: message, recipients: contacts);
}
```

### 5.5 無音模式（Silent Mode）

```dart
import 'package:flutter_sms/flutter_sms.dart';
import 'package:flutter/services.dart';

Future<void> sendSilentSMS() async {
  // 1. 靜音設備
  await SystemSound.play(SystemSoundType.click); // 最小聲音

  // 2. 發送 SMS（不震動、不響鈴）
  await sendSMS(
    message: _buildSilentMessage(),
    recipients: _emergencyContacts,
    sendDirect: true, // 直接發送，不開啟系統 SMS App
  );

  // 3. 確認發送後，恢復原音量
}
```

---

## 6. 隱私與安全架構

### 6.1 核心原則：「最小資料・端末優先・使用者主權」

```
使用者輸入
  ↓
端末內 AI 處理（離線）
  ↓
敏感資料：
  • 錄音 → 端末轉文字後刪除音檔
  • 照片 → 端末加密，不上傳原圖
  • 位置 → 僅用於端末內搜尋，不上傳座標
  • 對話 → 僅上傳匿名化關鍵詞
  ↓
伺服器僅收到：
  • 匿名統計（犯罪類型分布・地域熱點）
  • 加密後的證據摘要（無法解密）
```

### 6.2 加密架構

| 層級 | 技術 | 金鑰管理 |
|------|------|---------|
| 通訊加密 | TLS 1.3 | 伺服器憑證 |
| 儲存加密 | AES-256-GCM | 使用者密碼 + 硬體綁定 |
| 證據加密 | AES-256-GCM | Secure Enclave (iOS) / Keystore (Android) |
| 備份加密 | AES-256-GCM | 使用者持有的復原短語 |

### 6.3 權限設計（透明化）

```
使用者首次啟動 APP：
  ├─ 「GPS 用於尋找最鄰近支援機構」→ 可拒絕（仍可手動輸入地址）
  ├─ 「相機用於拍攝證據照片」→ 可拒絕（仍可從相簿選擇）
  ├─ 「麥克風用於語音對話」→ 可拒絕（仍可文字輸入）
  └─ 「SMS 用於緊急通知信賴聯絡人」→ 可拒絕（仍可手動撥打 110）
```

**所有權限都可拒絕，APP 仍可使用核心功能。**

---

## 7. 開發時程與里程碑

### 7.1 建議時程（6個月）

| 月 | 里程碑 | 交付物 |
|---|--------|--------|
| M1 | PWA MVP 上線 | Web APP、緊急模式、トリアージ、法律検索 |
| M2 | 端末 AI 導入 | ONNX 模型整合、離線推論、 Whisper 語音轉文字 |
| M3 | Flutter MVP | iOS + Android 上架、GPS・相機・SMS 原生功能 |
| M4 | 證據保全完善 | 加密儲存・保全証明書・防吃案報告書生成 |
| M5 | パートナー連携 | 弁護士会 API・NPO 預約系統連動 |
| M6 | 自治体 SaaS | 自治体向けダッシュボード、データ洞察 |

### 7.2 人力需求

| 角色 | 人數 | 工作內容 |
|------|------|---------|
| Flutter 工程師 | 1-2 名 | APP 前端 + 原生功能 |
| AI/ML 工程師 | 1 名 | 模型量化・端末推論・RAG |
| 後端工程師 | 1 名 | FastAPI・DB・認証・統計 |
| 資安工程師 | 0.5 名 | 加密・滲透測試（兼職可） |
| UI/UX 設計師 | 1 名 | 高齢者対応・無障礙設計 |
| 法律/社福監修 | 1 名 | 內容監修・パートナー開拓 |

---

## 8. 開發者招募

### 8.1 我們需要的人才

| 類型 | 技能 | 貢獻方式 |
|------|------|---------|
| **Flutter 工程師** | Dart, 原生功能調用, 離線儲存 | 核心 APP 開發 |
| **AI 工程師** | ONNX, 模型量化, RAG, 向量 DB | 端末 AI 推論 |
| **資安工程師** | 加密, 滲透測試, 隱私設計 | 安全架構監修 |
| **UI/UX 設計師** | Figma, 無障礙設計, 高齢者 UX | 介面設計 |
| **法務監修** | 日本法, 被害人支援實務 | 內容監修 |

### 8.2 如何加入

- **GitHub**: github.com/Fuilko/lawandbabysupport
- **信箱**: info@legalshield.jp（標題請註明「開發者応募」）
- **報酬**: 現階段以志願・助成金後報酬為主，長期可轉為正式雇傭或共同創業

---

## 附錄：快速開始（開發者）

```bash
# 1. 克隆倉庫
git clone https://github.com/Fuilko/lawandbabysupport.git
cd legalshield

# 2. 安裝依賴
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 3. 啟動 Streamlit Demo
.venv\Scripts\streamlit run frontend/streamlit_demo.py

# 4. 執行防吃案模組
.venv\Scripts\python backend/anti_grafting.py --case-id TEST001 --scenario DV

# 5. 執行加害者側寫分析
.venv\Scripts\python backend/perpetrator_profiler.py --scenario chikan --excuses "混んでた"
```

---

*LegalShield — 被害者を支援し、誰も1人にはしない。*
