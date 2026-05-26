# LegalShield データフロー — 仮名化アーキテクチャ

**作成日**：2026-05-27
**目的**：証拠保全と去識別化を両立するために、私たち（CALL4 提携、または 我々独自）が持つべき 2 つの DB と、それらを跨ぐ復元（rollback）フローを定義する。

---

## 1. 設計原則

| 原則 | 内容 | 法的根拠 |
|---|---|---|
| **仮名化（Pseudonymization）≠ 匿名化** | 鍵を持つ我々のみ復元可能 | GDPR 4(5) / 改正個情法 41 条 仮名加工情報 |
| **2 層分離** | Identifier Vault と Operating DB は物理的・論理的に分離 | アクセス制御の原則（最小権限） |
| **2-of-N 鍵管理** | 復元には 2 名以上の合意 | 内部不正リスク低減 |
| **書面同意＋監査ログ** | 全アクセス記録、改ざん検出 | 民訴 228（文書真正）/ ePrivacy |
| **被害者削除権** | いつでも自分の Vault entry を削除可能 | GDPR 17 / 個情法 30 |

---

## 2. 全体図

```
┌────────────────────────────────────────────────────┐
│  端末（iPhone, 被害者の手元）                       │
│  生の音声・顔・GPS・時刻                            │
│         │                                          │
│         ▼ AES-GCM (端末鍵、Secure Enclave)         │
│  端末ローカル DB（SwiftData）                       │
│  ・暗号化保持 6h 〜 30 日                           │
│  ・ユーザー削除 → 即時消去                          │
└────────────────────────────────────────────────────┘
         │
         ▼ 送信時に分離: トークン化 + 暗号化生データ
┌──────────────────────────┐  ┌──────────────────────┐
│ ① IDENTIFIER VAULT       │  │ ② OPERATING DB       │
│   (HSM/KMS, 厳重保管)    │  │   (公開・連携・分析)  │
│                          │  │                      │
│ user_token → 実 UUID     │  │ event_id             │
│ face_code → 顔ベクター    │  │ user_token           │
│ phone_code → 電話番号    │  │ face_code            │
│ company_code → 会社名    │  │ company_code         │
│ url_code → URL           │  │ location_hex (500m)  │
│ salt 世代 (v1, v2…)      │  │ time_window (1h)     │
│ アクセスログ             │  │ event_category       │
│                          │  │ urgency / triage     │
│ アクセス権:              │  │ transcript_hash      │
│  弁護団 + 監査人          │  │ evidence_chain_hash  │
│  2-of-N 合意             │  │ tsa_token (TSA 印)   │
│                          │  │                      │
└──────────────────────────┘  └──────────────────────┘
         │                              │
         │ 復元 (rollback)               │ 公開・連携
         │                              │
         ▼                              ▼
   弁護団・捜査機関への          Q-Map 集計表示
   書面同意付き開示              FEWN マッチング
                                 研究公開（仮名）
```

---

## 3. ① IDENTIFIER VAULT（鍵金庫）

### スキーマ

```sql
CREATE TABLE identifier_vault (
    user_token       TEXT PRIMARY KEY,        -- usr_<uuid>
    real_user_uuid   TEXT NOT NULL,           -- 端末 SwiftData PK
    face_code        TEXT,                    -- face_<sha256>
    face_vector_enc  BYTEA,                   -- 512-d embedding (AES-GCM)
    phone_code       TEXT,
    phone_real_enc   BYTEA,                   -- 元の電話 (AES-GCM)
    company_code     TEXT,
    company_real_enc BYTEA,
    url_code         TEXT,
    url_real_enc     BYTEA,
    salt_generation  INT NOT NULL DEFAULT 1,  -- 鍵ローテ世代
    consent_record   TEXT,                    -- 同意書 PDF hash
    created_at       TIMESTAMPTZ NOT NULL,
    deleted_at       TIMESTAMPTZ              -- 論理削除（GDPR 17）
);

CREATE TABLE vault_access_log (
    log_id        BIGSERIAL PRIMARY KEY,
    user_token    TEXT NOT NULL,
    accessed_by   TEXT NOT NULL,              -- 弁護士 ID + 監査人 ID
    purpose       TEXT NOT NULL,              -- 連名告訴 / 削除 / 当人開示
    legal_basis   TEXT NOT NULL,              -- 民事訴訟 / 同意 / 法的義務
    decision_id   TEXT NOT NULL,              -- 2-of-N 決議 ID
    accessed_at   TIMESTAMPTZ NOT NULL,
    chain_hash    TEXT NOT NULL               -- 改ざん検出
);
```

### 保護
- **HSM / AWS KMS** で encryption key を保護
- **2-of-N (Shamir Secret Sharing)** で復号鍵を分割（弁護士 + 監査 + 技術責任者）
- **アクセスログは append-only**、SHA-256 chain で改ざん検出
- **物理サーバ分離**：Operating DB と別 VPC、別 RDS インスタンス

---

## 4. ② OPERATING DB（運用 DB）

### スキーマ

```sql
CREATE TABLE incident_event (
    event_id            TEXT PRIMARY KEY,        -- evt_<uuid>
    user_token          TEXT NOT NULL,           -- vault と join 可
    face_code           TEXT,                    -- 同一加害者・被害者追跡
    location_hex        TEXT NOT NULL,           -- ls_h460_q*_r*
    time_window         TIMESTAMPTZ NOT NULL,    -- 1h バケット
    event_category      TEXT NOT NULL,           -- taxonomy_v1
    urgency             INT NOT NULL,
    transcript_hash     TEXT NOT NULL,
    evidence_chain_hash TEXT NOT NULL,
    tsa_token           TEXT,                    -- NICT TSA 印
    triage_json         JSONB,                   -- 分類結果のみ（生文非含）
    created_at          TIMESTAMPTZ NOT NULL
);

CREATE INDEX ix_event_user ON incident_event(user_token);
CREATE INDEX ix_event_face ON incident_event(face_code);
CREATE INDEX ix_event_hex_time ON incident_event(location_hex, time_window);
CREATE INDEX ix_event_cat_urg ON incident_event(event_category, urgency);
```

### 公開・連携の規則
- **Q-Map 集計**：location_hex + time_window で集約、k≥5 のみ
- **FEWN マッチング**：face_code / phone_code / company_code を Bloom filter で照合
- **CALL4 公開訴訟**：user_token 集合を弁護団が選定 → Vault 経由で本人同意 → 公開
- **研究用途**：時系列 + カテゴリのみ、user_token を更にハッシュ化して提供

**OPERATING DB だけ見ても、誰の顔・電話・正確な住所はわからない。**

---

## 5. 復元（rollback）フロー — 必要時のみ

### ユースケース 1：連名告訴の打診

```
1. 弁護団が OPERATING DB を検索
   "Mapry 関連 face_code を共有する被害者ペア"
2. 該当 user_token のリストを抽出
3. 監査人 + 法務責任者 2-of-N 決議
4. Vault から user_token → real_user_uuid 復元
5. 端末（APNs）に通知:
   「他にも同様の被害者がいることを CALL4 弁護団が確認しました。
    連名告訴の参加に同意される場合は端末アプリで承認してください。」
6. 本人同意取得後のみ、氏名・連絡先を共有
7. 全工程を vault_access_log に append、chain_hash で封印
```

### ユースケース 2：当人による削除請求

```
1. 端末アプリから削除請求
2. Vault entry を soft delete (deleted_at)
3. 30 日後に Vault entry 完全削除
4. OPERATING DB の user_token と face_code は残す（仮名のまま）
   ※ 復元不能になるため事実上匿名化
5. 削除完了通知 + チェーンハッシュを本人に発行
```

### ユースケース 3：捜査機関からの照会（令状あり）

```
1. 令状受領 → 法務確認
2. 必要最小範囲のみ復元（特定 event_id のみ）
3. 2-of-N 決議 + 令状情報を log
4. 開示後、当該被害者本人にも事後通知（プロバイダ責任制限法）
```

---

## 6. 鍵ローテーション

| 鍵 | 周期 | 影響 |
|---|---|---|
| 端末側 AES-GCM 鍵 | 1 年 | 過去データは旧鍵で再暗号化 |
| HMAC salt（face_code 等の生成）| 5 年 | 新世代から face_code が変わる、Vault に旧↔新マッピング保持 |
| KMS マスター鍵 | 自動（AWS KMS） | サーバ側のみ |
| 2-of-N 分割鍵 | 人事変動時 | Shamir 再分配 |

salt ローテ時の課題：face_code が変わると過去のマッチング履歴が切れる。Vault に「旧 face_code → 新 face_code」のマッピングを保持して継続性を確保。

---

## 7. 法的検討まとめ

| 法令 | 該当性 | 設計での対応 |
|---|---|---|
| 改正個情法 41 条（仮名加工情報）| OPERATING DB | 第三者提供は「特定個人を識別できない方法」で可（face_code 単体では不可） |
| GDPR 4(5) | Pseudonymized | 89 条研究例外、技術組織措置あり |
| 民訴 228（文書真正）| evidence_chain_hash + TSA | 証拠能力推定 |
| 刑 230（名誉毀損）| 加害者氏名は Vault のみ | 公的訴訟移行時のみ書面手続で開示 |
| 個情法 30（利用停止請求）| 削除フロー | 30 日以内処理 |

---

## 8. 次の実装タスク

| # | 項目 | 担当 | 期限 |
|---|---|---|---|
| 1 | Vault SQLite/PostgreSQL スキーマ実装 | server | 1 週間 |
| 2 | iOS `IdentifierTokenizer.swift`（端末側でハッシュ化）| iOS | 3 日 |
| 3 | FEWN を Operating DB と統合 | server + iOS | 1 週間 |
| 4 | 2-of-N 決議 UI（管理者ダッシュ）| web | Phase 3 |
| 5 | NICT TSA 連携 PoC | server | 1 週間 |
| 6 | Vault access log の改ざん検出 audit | server | 1 週間 |
| 7 | 削除請求フロー実装 | iOS + server | 2 週間 |

---

## 9. CALL4 面談での説明用 1 文要約

> 「私たちは被害者の顔・電話・正確な住所を **直接受け取りません**。端末側でハッシュ化されたコードと暗号化された生データを別々の DB に保管し、**復元には弁護団 2 名以上の合意と本人同意が必要** な設計です。CALL4 様はこの公証人役を担っていただくことを想定しています。」
