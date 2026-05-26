# Voice Triage System — 録音から遠隔通知までの全 pipeline

**作成日**：2026-05-26
**目的**：被害者の声を端末で受け止め、自動で「案件分類 → 緊急度判定 → 行動提案 → 遠隔送信」までを一気通貫で行う。

---

## 1. 録音モード：4 種

| Mode | 録音時間 | バッファ | トリガー | 用途 |
|---|---|---|---|---|
| **`standby`** | rolling 30 秒バッファ | 上書き | アプリ起動中常時 | キーワード検出（"助けて" / 悲鳴 / 泣声 ）|
| **`incident`** | 開始〜停止（最大 60 分） | full keep | ユーザーが「事件発生」ボタン | 緊急時記録 |
| **`continuous`** | 開始〜停止（無制限、自動分割 5 分毎） | full keep + チャンク | 弁護士面談・聴取録音 | 長時間記録 |
| **`evidence`** | 単発録音（最大 10 分） | full keep + 即時ハッシュ封印 | エビデンス追加メニュー | 司法級証拠保全 |

### 各モードの推奨時間

| シナリオ | 推奨 mode | 推奨時間 | 理由 |
|---|---|---|---|
| 子供との対話 (誘導なし聴取) | `evidence` | 10〜20 分 | InterviewCopilot 連携、通常 30 分以内に終わる |
| DV 現場 | `incident` | 開始〜安全になるまで | 20 分以内が多い |
| 弁護士相談 | `continuous` | 30〜90 分 | 長時間 5 分チャンク化 |
| 警察聴取 | `continuous` | 60〜180 分 | 同上 + 公的記録の二重化 |
| 通学路で不安音検知 | `standby` → `incident` 自動昇格 | 即時〜10 分 | キーワード検出後自動 |
| 緊急通報後の記録 | `incident` | 通報直後〜10 分 | 警察到着までの記録 |

### バッテリー・ストレージ目安

- 16kHz mono WAV = **2 MB/分**
- 60 分 = 120 MB / バッテリー消費 ~5%
- 24 時間 standby = ~10% / 日（rolling buffer なので Disk 増えない）

---

## 2. Pipeline 全体フロー

```
┌──────────────────────────────────────────────────────────────┐
│ iPhone (LegalShield app)                                      │
│                                                                │
│  [Mic] ─→ AVAudioEngine ─→ 16kHz PCM buffer                   │
│                              │                                 │
│             ┌────────────────┴─────────────────┐               │
│             ▼                                  ▼               │
│        WhisperKit                       VAD + Acoustic Event   │
│        (ASR multi-lang)                 (泣声・悲鳴・呼吸)       │
│             │                                  │               │
│             └──────────► transcript + tags ◄───┘               │
│                                  │                              │
│                                  ▼                              │
│           ┌────────────────────────────────────────┐           │
│           │ TriageEngine (On-Device SLM Phi-3.5)   │           │
│           │  - intent classification                │           │
│           │  - case_category (taxonomy_v1.json)     │           │
│           │  - urgency 1〜4                          │           │
│           │  - action recommendations              │           │
│           └────────────────────────────────────────┘           │
│                                  │                              │
│           ┌──────────────────────┼──────────────────────┐      │
│           ▼                      ▼                      ▼      │
│    [urgency<=2]            [urgency=3]            [urgency=4]   │
│    ローカル保存のみ          確認 dialog            自動エスカレ    │
│    Bedrock 呼ばず          → 雲端 LLM              即時送信     │
│                            (Bedrock Claude)        110番等      │
│                                  │                              │
│                                  ▼                              │
│                          詳細分析・文書生成                       │
│                                  │                              │
│                                  ▼                              │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
         GIS Triage API    管理者ダッシュ    APNs Push
         (heatmap)         WebSocket       (NGO/弁護士)
```

---

## 3. 録音 → 案件分類への導流ロジック

### Step A: 即時オンデバイス分類（Phi-3.5、~1 秒）

```
INPUT:
  transcript: "あの人が…う、私の腕を…[泣]…ずっと触って…"
  acoustic_events: ["crying", "heavy_breathing"]
  speaker_age_estimate: child
  GPS: (35.6762, 139.6503)
  timestamp: 2026-05-26T20:30:00+09:00

PROMPT (system):
  あなたは緊急被害者支援トリアージ AI です。
  以下の発話と音響イベントから:
  1. 案件カテゴリを taxonomy_v1.json から選択（27 種類から）
  2. 緊急度 1-4
  3. 推奨される直接行動を 3 つまで
  JSON のみ出力。

OUTPUT (JSON):
{
  "category": "child_abuse",
  "urgency": 4,
  "confidence": 0.85,
  "key_phrases": ["私の腕を", "ずっと触って"],
  "recommended_actions": [
    "児童相談所 189 へ通報",
    "現場から物理的距離を取る",
    "現在地を保存し、信頼できる大人に連絡"
  ],
  "needs_cloud_review": true
}
```

### Step B: クラウド LLM 詳細分析（緊急度 ≥ 3 のみ）

Bedrock Claude 3.5 Sonnet で：
- 法的論点の抽出（児童虐待防止法 6 条 / 刑法 176 条 など）
- 証拠保全プロトコルの提案
- 関連判例の検索
- 文書ドラフト生成

### Step C: 自動アクション（urgency 4 のみ、ユーザー同意済の場合）

- 信頼連絡先（事前登録）に自動 SMS / 通話
- GIS 平台に位置情報通報
- 録音継続（自動 incident mode 昇格）

---

## 4. 半自動処理フロー（管理者・遠隔者向け）

```
[受害者 iPhone]                           [管理者ダッシュボード]
     │                                          │
     │ 1. trigger detected                      │
     │    (urgency=3, category=child_abuse)     │
     ├──────────────────────────────────────►  │ ┌──────────────┐
     │    encrypted POST                        │ │ 新規通報通知   │
     │    to GIS API                            │ └──────────────┘
     │                                          │
     │                                          │ 担当者が確認
     │                                          │   ↓
     │ 2. WebSocket open                        │ ┌──────────────┐
     │◄─────────────────────────────────────────┤ │「対応中」表示  │
     │    "approved by NGO staff #42"           │ │ 録音 listen   │
     │                                          │ │ 文字起こし読 │
     │                                          │ │ 行動指示     │
     │                                          │ └──────────────┘
     │ 3. 行動指示受信                            │
     │    "現場から離れる、警察 110 番"            │
     │                                          │
     │ 4. 受信確認・実行ログ                      │
     ├──────────────────────────────────────►  │
     │                                          │
```

### 管理者側で見るもの

| 情報 | 説明 |
|---|---|
| **transcript（リアルタイム）** | WhisperKit 出力をストリーミング |
| **acoustic_events タイムライン** | [泣 0:30-0:45] [悲鳴 0:50] |
| **GPS + 移動経路** | 過去 10 分の動線マップ |
| **on-device triage 結果** | category / urgency / recommendations |
| **証拠ハッシュチェーン** | 改ざん不可検証 |
| **過去の同一案件履歴** | 累積通報があるか |

### 管理者の選択肢

1. **"自分で対応する"** → 担当割当
2. **"警察エスカレーション"** → 110 番 / 児相 189 番に転送
3. **"録音継続を依頼"** → アプリに incident mode 開始指示
4. **"安全確認"** → 受害者にメッセージ送信

---

## 5. 流暢な訓練 = フィードバックループ

```
本番運用
   │
   ▼
誤分類 / 低信頼ケース → flag: needs_review
   │
   ▼
管理者が修正 (correct_category, correct_urgency)
   │
   ▼
shared/voice_triage_corrections.jsonl に追記
   │
   ▼
週 1 回 → 訓練データに混入 → LoRA 再 fine-tune
   │
   ▼
A/B test (10% トラフィックで shadow deploy)
   │
   ▼
WER/CER 改善確認 → 全面 rollout
```

### Shadow deployment

新モデル v2 を本番に投入前：
- 全リクエストを並列で v1 と v2 両方に投げる
- v1 結果のみユーザーに返す
- v2 結果は log のみ
- 1 週間後 WER/CER 比較 → v2 が良ければ swap

---

## 6. 実装優先度（個人開発向け）

| Phase | 内容 | 期間 |
|---|---|---|
| **P1 (今週)** | VoiceTriageService.swift（録音 mode 4 種 + ASR + on-device triage） | 3 日 |
| **P1** | shared/voice_triage_event.schema.json（共通形式定義） | 1 日 |
| **P2 (来週)** | Bedrock 詳細分析連携（urgency≥3） | 2 日 |
| **P2** | GIS API push（既存 `intake.py` 拡張） | 1 日 |
| **P3 (再来週)** | 管理者ダッシュボード（Web）+ WebSocket | 5 日 |
| **P4** | フィードバック収集 → corrections.jsonl | 2 日 |
| **P5** | 月次 LoRA 再訓練ジョブ（Windows cron） | 3 日 |

---

## 7. 倫理・セキュリティ最低限

1. **録音はユーザー明示同意必須**：起動時に明示する
2. **standby mode はキーワード検出のみで full transcript はサーバーに送らない**
3. **GPS は incident 以上で送信、standby は端末内のみ**
4. **管理者は read-only 鍵、書込は受害者署名必須**
5. **逐字稿は AES-GCM 暗号化、鍵は keychain**
6. **送信前に AnonymizationLevel 必須選択**（none / partial / full）

---

## 8. 既存資産との接続

| 既存 | 新規との関係 |
|---|---|
| `InterviewCopilot.swift` | 子供聴取専用、誘導検出。VoiceTriageService から呼び出す |
| `WhisperKitTranscriber.swift` | 多言語 ASR エンジンとして使用 |
| `MLXOnDeviceProvider.swift` | TriageEngine の Phi-3.5 推論基盤 |
| `CaseTaxonomyService` | category 候補の取得 |
| `LegalCase / Evidence (SwiftData)` | 録音結果を Evidence として保存 |
| `ExportService` | 緊急/分析パッケージ生成 |
| `gis/services/legalshield-api/intake.py` | 遠隔送信先 |
| `aws/bedrock_proxy/` | クラウド LLM 詳細分析 |
