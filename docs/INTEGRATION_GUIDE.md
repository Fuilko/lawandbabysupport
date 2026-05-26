# LegalShield 統合ガイド — Plugins / Recognition / Taxonomy / Portable DB

**作成日**：2026-05-26
**対象**：iOS App 開発者 ＋ 外部 agent（Python / Node / Swift）

---

## 1. 追加された SPM プラグイン

| Package | URL | 用途 |
|---|---|---|
| WhisperKit | https://github.com/argmaxinc/WhisperKit | 99 言語自動判定の音声→テキスト |
| MLXSwift | https://github.com/ml-explore/mlx-swift | Apple MLX 推論基盤 |
| MLXSwiftExamples (`MLXLLM`) | https://github.com/ml-explore/mlx-swift-examples | LLM 推論ヘルパー |
| ZIPFoundation | https://github.com/weichsel/ZIPFoundation | Portable DB エクスポート用 |

`project.yml` の `packages:` セクション参照。`xcodegen generate` 後 Xcode で初回 SPM resolve 時に自動 DL（合計 ~30 MB、モデル本体は別途）。

---

## 2. 音声認識（多言語）— `WhisperKitTranscriber`

**ファイル**：`ios/LegalShield/LegalShield/Services/WhisperKitTranscriber.swift`

### 使い方

```swift
let transcriber = WhisperKitTranscriber(modelName: "openai_whisper-base")
await transcriber.loadModel()

let result = try await transcriber.transcribe(
    audioURL: someM4AURL,
    languageHint: nil  // 自動判定（日・中・英・台・越...）
)

print(result.text)               // 書き起こしテキスト
print(result.detectedLanguage)   // "ja", "zh", "en"...
```

### モデル選択指針

| 機種 | 推奨モデル | サイズ |
|---|---|---|
| iPhone 12 以下 | `openai_whisper-base` | 74 MB |
| iPhone 13–14 | `openai_whisper-small` | 244 MB |
| iPhone 15 以降 | `openai_whisper-large-v3-turbo` | 1.5 GB |

### 既存 `InterviewCopilot`（zh-TW Apple Speech）との関係

- 短文・即時性 → InterviewCopilot
- 長文・多言語・録音ファイル全体 → WhisperKitTranscriber

---

## 3. On-Device 推論 — `MLXOnDeviceProvider`

**ファイル**：`ios/LegalShield/LegalShield/Services/MLXOnDeviceProvider.swift`

**訓練は行わない**（Mac / Windows 上の `mlx-lm` 別途）。本クラスは推論専用。

### 推奨モデルプリセット

```swift
MLXOnDeviceProvider.presets
// [(label, modelId, ramHintMB)]
//  Phi-3.5 mini (3.8B, 推奨)   2048 MB
//  Gemma 2 (2B, 軽量)          1280 MB
//  Qwen 2.5 (1.5B, 最軽量)      896 MB
//  Llama 3.2 (3B, バランス)    1792 MB
```

### 既存 `OnDeviceSLMProvider` との関係

- `OnDeviceSLMProvider`：mock + Apple FoundationModels（iOS 18.4+）
- `MLXOnDeviceProvider`：MLX 経由の任意モデル（柔軟、要モデル DL）

`LLMSettings.ProviderKind` への追加は未実施（Phase 2）。当面は手動インスタンス化。

---

## 4. 案件分類スキーマ — `data/case_taxonomy/taxonomy_v1.json`

**単一真実源**（Single Source of Truth）：iOS 内部 enum と外部 agent の双方が同じ JSON を参照。

### iOS 側読込

```swift
let svc = CaseTaxonomyService.shared
if let cat = svc.category(byId: "child_abuse") {
    print(cat.labelJp)        // "児童虐待"
    print(cat.keyStatutes)    // ["児童虐待防止法 6 条", ...]
    print(cat.defaultPartners) // ["児童相談所 189", "警察 110", ...]
}
```

### 外部 agent (Python) 読込

```python
import json
tx = json.load(open("data/case_taxonomy/taxonomy_v1.json"))
for c in tx["categories"]:
    if c["id"] == "child_abuse":
        print(c["default_partners"])
```

サンプル：`data/case_taxonomy/read_taxonomy_example.py`

---

## 5. ポータブル DB エクスポート — `PortableDBExporter`

**ファイル**：`ios/LegalShield/LegalShield/Services/PortableDBExporter.swift`

### 使い方

```swift
let pkgURL = try PortableDBExporter.shared.exportAllCases(
    modelContext: ctx,
    anonymization: .partial   // 弁護士共有用
) { progress in
    print("export \(Int(progress * 100))%")
}
// → /tmp/.../legalshield-export-2026-05-26T20-15-00.legalshield-pkg
```

### `.legalshield-pkg` の中身

```
manifest.json        ← schema_version, app_version, 各ファイルの SHA-256
schema.md            ← JSON / SQLite テーブル定義の人間読み doc
taxonomy_v1.json     ← 決定論性のため snapshot
cases.json           ← 案件全件（DTO 形式）
evidence.json        ← 証拠全件
audit_log.json       ← hash chain 検証可能な監査ログ
cases.sqlite         ← 同データを RDB で
README.md            ← 「他 agent はこう読みます」
```

### 他 agent からの読込

#### Python

```python
import json, sqlite3, zipfile

with zipfile.ZipFile("legalshield-export-X.legalshield-pkg") as zf:
    zf.extractall("/tmp/ls")

# 高優先度案件を抽出
db = sqlite3.connect("/tmp/ls/cases.sqlite")
high = db.execute(
    "SELECT id, title, urgency FROM cases WHERE urgency >= 3 ORDER BY created_at"
).fetchall()
```

#### Node.js

```javascript
const Database = require('better-sqlite3');
const db = new Database('cases.sqlite', { readonly: true });
const high = db.prepare(
    'SELECT id, title, urgency FROM cases WHERE urgency >= 3'
).all();
```

#### 改ざん検証（manifest.json による）

```python
import hashlib, json
manifest = json.load(open("/tmp/ls/manifest.json"))
for entry in manifest["files"]:
    actual = hashlib.sha256(open(f"/tmp/ls/{entry['name']}", "rb").read()).hexdigest()
    assert actual == entry["sha256"], f"破損: {entry['name']}"
```

### 匿名化レベル

| Level | GPS | DeviceId | 名前 | 場所 | 用途 |
|---|---|---|---|---|---|
| `none` | ✓ | ✓ | ✓ | ✓ | 本人 → 弁護士 |
| `partial` | ✗ | ✓ | ✓ | ✓ | 弁護士 → 共同研究者 |
| `full` | ✗ | ✗ | ✗ | ✗ | 研究データ集計 |

---

## 6. 実装状態サマリ

| 機能 | 状態 | 場所 |
|---|---|---|
| WhisperKit ラッパー | ✅ 実装済（`#if canImport` ガード）| `Services/WhisperKitTranscriber.swift` |
| MLX 推論プロバイダ | ✅ 実装済 | `Services/MLXOnDeviceProvider.swift` |
| 案件分類スキーマ | ✅ JSON + Swift サービス | `data/case_taxonomy/`, `Services/CaseTaxonomyService.swift` |
| ポータブル DB エクスポート | ✅ ZIP / JSON / SQLite | `Services/PortableDBExporter.swift` |
| LLMSettings に MLX を追加 | ⏳ Phase 2 | 手動インスタンス化のみ |
| WhisperKit を InterviewCopilot に統合 | ⏳ 設計済、コーディング未 | – |
| LoRA fine-tune（Mac/Windows）| ⏳ 別タスク | `mlx-lm` で別途 |

---

## 7. 次のステップ提案

1. **Xcode で SPM resolve**：iPhone 接続前に Xcode で開いて File → Packages → Resolve（初回 ~5 分）
2. **WhisperKit モデル DL**：iPhone 上、初回起動時自動 DL（base = 74 MB）
3. **MLX モデル DL**：Settings 画面の「モデルを準備」ボタンで実行（推奨 Phi-3.5 ~2 GB）
4. **エクスポートテスト**：1 件案件＋ダミー証拠で `.legalshield-pkg` 作成 → Python で読込検証
