# DEPLOYMENT_TOPOLOGY.md — 環境・同期・配布・ロール（統合マスター）

> 「どの端末で何が動くか」「環境間で何をどう同期するか」「DBを誰がどう持つか」「協力者をどう銜接するか」を
> **1 枚に束ねた正準ドキュメント**。詳細は各リンク先の既存設計書を参照。
> 入口は `AGENTS.md`、主架構は `ARCHITECTURE.md`、最新進捗は `PROGRESS.md`。
>
> 最終更新: **2026-06-02**

---

## 1. なぜこの構成か（前提）

- **Mac M1 / iPhone は重い LLM を動かせない** → エッジは「初步分析（トリアージ）」のみ。
- **本格分析（証拠・資料夾を読み、判例72万件で根拠付き解析）はサーバ側 LLM** が担当。
- サーバは **Windows RTX 4080（自前/開発）** と **AWS（共有/本番）** の二択。
- 詳細設計: `docs/strategy/2026-05-31_edge_training_and_role_architecture.md`

---

## 2. 計算がどこで走るか（3 層トポロジ）

```
┌─ エッジ層（手機 / Mac M1）──────────┐
│ iPhone・Mac : 3B SLM(MLX) + WhisperKit│  初步分析のみ
│ ・自由文/音声 → 分類・緊急度・去識別化 │  オフライン可
│ ・生データは端末内 AES-GCM 暗号化      │  送信は去識別化JSONだけ
└───────────────┬───────────────────────┘
                │ HTTPS (mTLS) / 去識別化済み
                ▼
┌─ 重分析層（サーバ）──────────────────────────────────────┐
│ A) Windows RTX 4080  : Ollama gemma3:27b + LanceDB RAG     │ 自前・開発・重訓練
│    (100.76.218.124:8000, Tailscale)  → harness L1-L7       │
│ B) AWS               : Bedrock(Claude) Lambda / EC2+PostGIS│ 共有・本番・協力者向け
│    aws/bedrock_proxy/ , gis/ (Docker)                      │
└───────────────┬───────────────────────────────────────────┘
                ▼
┌─ データ層 ─────────────────────────────────────────────────┐
│ LanceDB+DuckDB: 国法62.3万 + 判例72.4万 (vector)            │
│ PostGIS      : DV/犯罪統計/法テラス/行政界 (gis/)           │
│ Vault(KMS)   : 実PII（管理者も直接見れない・2-of-N復元）    │
└────────────────────────────────────────────────────────────┘
```

**結論**: 「LLM を引き込んで証拠・資料夾を読ませる深い解析」は **手機ではなくサーバ（4080 or AWS）**。
手機は去識別化トリアージのみ。完全ローカルで使いたい層には §5 のデスクトップ/オフラインパック。

---

## 3. 開発・実行環境の役割分担

| 環境 | ハード | 担当 | 動くもの |
|---|---|---|---|
| **iOS 開発** | Mac（Xcode 必須） | アプリ開発・on-device SLM 検証 | SwiftUI, MLX(小型), WhisperKit |
| **サーバ開発/訓練** | **Windows RTX 4080 16GB** | LLM 運用・RAG・**小型モデル訓練(LoRA)** | Ollama, LanceDB, harness, peft/trl |
| **本番/共有** | AWS（Lambda+Bedrock / EC2+PostGIS） | 協力者・NPO・弁護士の接続先 | bedrock_proxy, gis API |
| **エンドユーザー** | iPhone / (将来)デスクトップ | 利用 | アプリ / オフラインパック |

> Mac M1 は **iOS 開発と軽い検証専用**。27B 級の訓練・推論は不可 → 4080 か AWS。
> 環境再構築の詳細手順: `DEPLOYMENT_GUIDE.md`（ハード要件・依存・DB再構築）。

---

## 4. 同期マトリクス（環境間で何をどう同期するか）★

| 対象 | 同期手段 | Git 管理 | 備考 |
|---|---|---|---|
| **コード** | GitHub `main` | ✓ | Mac/Windows 両方が clone・pull |
| **正準ドキュメント** | GitHub（`AGENTS/ARCHITECTURE/PROGRESS/本書`） | ✓ | どの端末でも最新設計を読める |
| **LLM モデル** | Ollama pull（`name:tag` 固定）/ HF / S3 | ✗ | 大容量。名前+版を本書/設定で固定 |
| **ベクトル DB** | S3 等オブジェクトストレージ + 版管理、または crawler で再構築 | ✗ | 2.4GB級。`deploy-to-windows.md` 参照 |
| **PostGIS データ** | `gis/ingest/run_all.py` で再生成、or dump 共有 | ✗ | 公開データのみ |
| **secrets / 設定** | `.env`（`gis/.env.example` 等テンプレから） | ✗ | キー類は絶対 commit しない |
| **証拠 / ユーザーデータ** | 端末内暗号化。**同意時のみ** API 経由で Vault へ | ✗ **絶対** | git にも開発機にも置かない |

**鍵**: 同期して良いのは「コード・docs・公開データ・モデル参照」のみ。**PII/証拠は同期しない**。

---

## 5. データベースをユーザーに配布できるか（2 方式）

| 方式 | 仕組み | 向き | 更新 |
|---|---|---|---|
| **API 方式（既定・推奨）** | ホストした `/rag/answer` に問合せ。クライアントは DL 不要 | 一般ユーザー・協力者 | 常に最新 |
| **オフラインパック** | LanceDB の curated subset を圧縮・署名し配布。ローカル Ollama と組で完全オフライン解析 | プライバシー最優先・ネット断地域 | 版付き・差分更新 |

- 「資料庫を未来ユーザーに直接DLさせる」= **オフラインパック**として実現可能。ただし全量(150万件級)は重いので **用途別 curated subset + 署名 + 版管理**を推奨。
- LLM を引き込んでフォルダ/証拠を読む完全ローカル運用 = **デスクトップアプリ（Mac/Windows）+ オフラインパック + ローカル Ollama**。手機ではなく PC 上のソフトとして配る形。

---

## 6. 最新の判例・統計を API で銜接

```
legalshield/crawlers/ (e-Stat / 法令 / 判例 / NPA / 法テラス …)
   │  定期実行（cron / GitHub Actions）
   ▼
再埋め込み (unified_vectorize.py / elaws_embed*.py)
   ▼
LanceDB 更新（判例・法令） ＋ PostGIS 更新（統計・施設）
   ▼
/rag/* ・ gis /api/v1/* で配信  → クライアントは常に最新を取得
```

オフラインパック利用者には、版付きの差分更新を配布。

---

## 7. 協力者・NPO・弁護士の銜接（5 ロール）

詳細: `docs/strategy/2026-05-31_edge_training_and_role_architecture.md` §2、`docs/setup/AGENT_HANDOFF.md`。

| ロール | 誰 | 接続先 | 見える情報 |
|---|---|---|---|
| 使用者 | 被害当事者 | iOS アプリ | 自分の相談・証拠のみ |
| 導入者 | 自治体・NPO | 地域ダッシュボード | 集計のみ（k≥5）・リスクマップ |
| 協力者 | CALL4・弁護団・公証人 | 連携 API / ポータル | 本人同意済み案件サマリ（PII は 2-of-N 同意で開示）|
| 管理者 | 運用責任者 | 管理ダッシュボード | 仮名統計・監査・RBAC |
| 開発者 | 劉 | コード/CI/CD | 全コード（**本番 AWS 反映は劉の Review が必須ゲート**）|

**協力モデル**: 協力者は local repo + Pull Request まで。**main マージと AWS 反映は劉の Review 後のみ**（GitHub Actions → AWS）。
情報の到達範囲は同意ラダー T0〜T4 で段階制御。

---

## 7b. 製品形態（ユーザー種別ごとに配る物）

「AI エージェント（`AGENTS.md` が指す開発支援AI）」と「ユーザーに配る製品」は**別物**。
開発エージェントはユーザーに配らない。GitHub は**開発者だけ**。

| ユーザー | 配る物 | 入手 | インストール作業 |
|---|---|---|---|
| 被害者（主役） | **iOS App** | App Store / TestFlight | タップのみ・設定不要 |
| （任意）完全ローカル希望 | **デスクトップアプリ**(Mac/Win) | 署名済 .dmg/.exe（LLM+オフラインDB同梱） | ダブルクリック |
| NPO・自治体（導入者） | **Web ダッシュボード** | URL ログイン | 不要 |
| 弁護士・CALL4（協力者） | **Web ポータル / API** | URL ログイン / API キー | 不要 |
| 開発者 | **GitHub リポジトリ** | `git clone` | 開発環境構築 |

LLM は基本サーバ側（AWS/4080）。端末に入るのは**完全ローカルのデスクトップ版のみ**。

---

## 7c. 同一 DB・個別 UI 開発・同期（開発順序）★

**原則**: バックエンド＋DB は **1 つ（唯一の真実）**。UI は複数を**独立開発**し、
**API コントラクト**で繋ぐ。

```
        ┌──── 共有バックエンド＋DB ────┐
        │ legalshield/backend (/rag/answer, harness) │
        │ gis/ (PostGIS, /api/v1/...)                │
        │ ★ API コントラクト = 全UIの共通の約束       │
        └──┬──────────┬──────────┬──────────────────┘
           │ 同じAPI   │          │
        iOS App     Web         Desktop(任意)   ← UIは独立開発・並行可
        (被害者)   (NPO/弁護士)  (完全ローカル)
```

### 同期の 3 本柱
1. **モノレポ + git** — `ios/` `gis/frontend/` `web/`(将来) を 1 リポジトリに。`git pull` で全UI同期。
2. **API コントラクト** — `/api/v1/` でバージョン固定。backend 変更が黙って UI を壊さない。
3. **共有モデル** — 分類スキーマ `data/case_taxonomy/taxonomy_v1.json` を全UI共通参照。

### 開発順序（推奨）
```
Phase 1: API コントラクトを固定   ← 最小工数・最大レバレッジ（UI分岐の前に）
Phase 2: iOS App MVP を縦貫通     ← 採取→エッジ3Bトリアージ→/rag/answer→出典付き回答
Phase 3: Web ダッシュボード        ← 同じAPIを叩くだけ（被害者UIの後）
Phase 4: Desktop 完全ローカル版    ← 任意・最後
```

### いま集中すべき所（推奨）
**iOS App を 1 本、縦に貫通させる。** iOS が最も進んでいる（ビルド成功）・主役向け。
今 Web を始めると注意が割れる。Web は後から同じ API で作れる（手戻り小）。
最初の一歩 = **iOS（`LegalHarnessService`）を実際の `/rag/answer` バックエンドに接続**し、
証拠採取 → トリアージ → 根拠付き回答の縦貫通を成立させる。これがシステム全体の動作証明になる。

---

## 8. 関連ドキュメント（詳細はこちら）

| 目的 | ファイル |
|---|---|
| 環境再構築（ハード/依存/DB） | `DEPLOYMENT_GUIDE.md` |
| エッジ訓練・5ロール・障害分離（中核設計） | `docs/strategy/2026-05-31_edge_training_and_role_architecture.md` |
| 新マシン軽量起動 | `docs/setup/QUICKSTART_NEW_MACHINE.md` / `.windsurf/workflows/setup-new-machine.md` |
| Windows(4080) へ同期 | `.windsurf/workflows/deploy-to-windows.md` |
| 協力者ハンドオフ | `docs/setup/AGENT_HANDOFF.md` |
| AWS Bedrock プロキシ | `aws/bedrock_proxy/README.md` |
| GIS 配備 | `gis/DEPLOYMENT.md` / `gis/INTEGRATION.md` |
| iOS 実機配備 | `ios/LegalShield/IPHONE_DEPLOY_QUICKSTART.md` |

---

*環境やトポロジを変えたら本書と `ARCHITECTURE.md` を同一コミットで更新すること。*
