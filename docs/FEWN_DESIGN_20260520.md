# FEWN — Federated Encrypted Witness Network 設計書

**Doc ID**: `FEWN_DESIGN_20260520`
**Status**: Draft v0.1
**Tagline**: 「空氣盒子 for 被害証言 — プライバシーを破らずに加害者の重複を検知する」
**Related**: `SAFETY_GIS_DESIGN_20260520.md`, `EXPANSION_AND_DISPATCH_DESIGN_20260520.md`

---

## 0. 何を解決するか

社会的事実:
- 1 人の加害者は **平均 7 人を被害化** (内閣府 性犯罪被害調査; ストーカーは累犯率 60%+)
- 被害者は単独で警察行っても **「証拠不十分」** で帰される
- 被害者同士が **「同じ人だ」** と知る手段が無い → 連名告訴できない
- 結果: 加害者の犯行は続く、被害者は孤立

技術的に可能なこと:
- 顔写真を **サーバに送らずに** 「同じ人物を記録した被害者が他にいるか」を検知できる
- 検知できたら NPO 経由で **連絡仲介** → 連名告訴の選択肢が生まれる

法的に可能な範囲:
- 端末ローカル顔記録 = 私的領域（合法）
- 暗号学的バケットのみ送信 = 個人識別符号の該当性が薄い（匿名加工情報相当）
- マッチ時の連絡仲介 = NPO/警察の **公的機能と一体運用** すれば 個情法 27-1-1 で正当化可能
- 連名告訴 = 刑訴法 230、複数被害者の告訴は警察動員力を激変させる

---

## 1. 全体プロトコル

```
                ┌──────────────────────┐
                │  被害者 A のスマホ   │
                │                      │
                │  ① 加害者を撮影      │
                │  ② 顔エンベディング  │
                │     (端末ML)         │
                │  ③ LSH バケット      │
                │     b_A = LSH(emb)   │
                │                      │
                │  ④ PSI コミット送信  │
                │     {b_A, c_A, ψ_A}  │ ← ψ = pseudonym
                └──────────┬───────────┘
                           │ HTTPS + E2E
                           ▼
              ┌────────────────────────────┐
              │  Coordinator (NPO 主管)    │
              │  ・ φ ⊂ b の重なりを判定  │
              │  ・ 被害者個人の identity  │
              │    は持たない              │
              │  ・ Threshold k=2 で発火   │
              └──────────┬─────────────────┘
                         │
              重なり検知時のみ
                         │
                         ▼
              ┌────────────────────────────┐
              │  通知 (両者へ pseudo)       │
              │  「あなたの記録と類似の     │
              │    パターンが他 N 件あり    │
              │    NPO 連絡しますか?」      │
              └──────────┬─────────────────┘
                         │
                  本人同意 (YES) のみ
                         │
                         ▼
              ┌────────────────────────────┐
              │  NPO カウンセラー仲介       │
              │  ・両被害者と個別対話       │
              │  ・写真の比較 (E2E)        │
              │  ・確認できた場合のみ       │
              │    連名告訴の検討に進む    │
              └──────────┬─────────────────┘
                         │
                ≥3 人で確認
                         │
                         ▼
              ┌────────────────────────────┐
              │  警察への合同提供           │
              │  (個情法 27-1-1 法令に     │
              │   基づく + 本人同意付き)    │
              └────────────────────────────┘
```

**重要**: Coordinator は **顔も写真もエンベディングも見ない**。LSH バケット ID と暗号コミットだけ。

---

## 2. 暗号プリミティブ

### 2.1 顔エンベディング（端末のみ）

- iOS: `Vision.framework` `VNGenerateFaceDescriptor` または FaceNet/ArcFace の Core ML 化
- Android: ML Kit Face Detection + MediaPipe Face Mesh + ArcFace の TFLite
- 出力: 128〜512 次元 float ベクトル
- 保存: SQLCipher + Secure Enclave / Keystore で鍵保護
- **絶対に端末から出さない**

### 2.2 LSH バケット（局所性鋭敏ハッシュ）

```python
# 概念コード
def to_bucket(embedding: np.ndarray) -> bytes:
    # SimHash / random projection
    H = SHARED_RANDOM_PROJECTIONS  # 全端末共通の乱数行列 (公開定数)
    bits = (embedding @ H) > 0     # 64 bit
    return int(bits.dot(1 << np.arange(64))).to_bytes(8, "big")
```

性質:
- 似た顔 → 同じバケット
- 異なる顔 → 異なるバケット（高確率）
- バケットから元の顔を復元 **不可能**
- 1 つの顔に対し複数の独立 LSH を生成（≥ 5 投影）→ false positive 削減

### 2.3 Private Set Intersection (PSI)

ライブラリ:
- [OpenMined PSI](https://github.com/OpenMined/PSI) (Google 由来、商用可)
- [Microsoft APSI](https://github.com/microsoft/APSI)
- Cuckoo Filter ベースの軽量 PSI

プロトコル選択: **DDH-PSI (semi-honest)**
- Coordinator は暗号化バケットの **重複個数** だけ知る
- 各端末はローカルで「自分のバケットが他端末と重なるか」を判定
- 重複しない端末は何も学ばない

### 2.4 Threshold 発火

- k=2 (≥2 名一致) で発火 → 通知
- k=3 で警察提出推奨
- Threshold encryption: NPO 連合の m-of-n 鍵共有（例: 7 NPO の 4-of-7）で復号
- 単独 NPO が暴走できない

---

## 3. データモデル（Coordinator 側）

```sql
CREATE SCHEMA fewn;

-- ----------------------------------------------------------------
-- ペンネーム被害者 (実名は持たない)
-- ----------------------------------------------------------------
CREATE TABLE fewn.pseudonyms (
    psi_id          UUID PRIMARY KEY,            -- 端末生成 pseudonym
    enrolled_at     TIMESTAMPTZ DEFAULT now(),
    npo_contact_pk  TEXT,                        -- NPO 連絡用公開鍵 (E2E用)
    last_seen       TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ
);

-- ----------------------------------------------------------------
-- LSH バケット投稿 (顔由来) - 何度更新しても良い
-- ----------------------------------------------------------------
CREATE TABLE fewn.bucket_submissions (
    sub_id          BIGSERIAL PRIMARY KEY,
    psi_id          UUID NOT NULL REFERENCES fewn.pseudonyms(psi_id),
    bucket_hash     BYTEA NOT NULL,              -- LSH bucket (64-bit)
    projection_id   SMALLINT NOT NULL,           -- 0..4 (5 LSH 並列)
    commit_hmac     BYTEA NOT NULL,              -- HMAC(secret, sub_id) for tamper detect
    submitted_at    TIMESTAMPTZ DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL,        -- 90 日 TTL
    incident_geom   GEOMETRY(Point, 4326),       -- 任意, 250m 以上にぼかし
    incident_time   TIMESTAMPTZ,                 -- 任意, 日単位にぼかし
    incident_blur_m INTEGER DEFAULT 250
);
CREATE INDEX ON fewn.bucket_submissions (bucket_hash, projection_id);
CREATE INDEX ON fewn.bucket_submissions (psi_id);
CREATE INDEX ON fewn.bucket_submissions (expires_at);

-- ----------------------------------------------------------------
-- マッチ検出 (≥2 で 1 行作る)
-- ----------------------------------------------------------------
CREATE TABLE fewn.matches (
    match_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    detected_at         TIMESTAMPTZ DEFAULT now(),
    n_pseudonyms        INTEGER NOT NULL,        -- 一致した psi_id の数
    n_projections_hit   INTEGER NOT NULL,        -- 5 投影中いくつ一致
    confidence          REAL NOT NULL,           -- false positive 評価値
    geom_centroid       GEOMETRY(Point, 4326),
    time_window_start   TIMESTAMPTZ,
    time_window_end     TIMESTAMPTZ,
    threshold_unsealed  BOOLEAN DEFAULT false,   -- m-of-n 鍵で復号済か
    police_referred     BOOLEAN DEFAULT false,
    npo_steward_id      UUID
);

CREATE TABLE fewn.match_members (
    match_id        UUID REFERENCES fewn.matches(match_id),
    psi_id          UUID NOT NULL,
    notified_at     TIMESTAMPTZ,
    consent_to_mediation BOOLEAN,
    consent_at      TIMESTAMPTZ,
    PRIMARY KEY (match_id, psi_id)
);

-- ----------------------------------------------------------------
-- 監査 (全アクセス記録)
-- ----------------------------------------------------------------
CREATE TABLE fewn.access_log (
    log_id          BIGSERIAL PRIMARY KEY,
    at              TIMESTAMPTZ DEFAULT now(),
    actor_role      TEXT,                        -- 'coordinator' | 'npo' | 'police' | 'subject'
    actor_id_hash   TEXT,
    action          TEXT,
    target_match    UUID,
    target_psi      UUID,
    purpose         TEXT,
    notes           TEXT
);

-- ----------------------------------------------------------------
-- データ主体権利 (本人開示・削除)
-- ----------------------------------------------------------------
CREATE TABLE fewn.subject_requests (
    req_id          BIGSERIAL PRIMARY KEY,
    received_at     TIMESTAMPTZ DEFAULT now(),
    psi_id_proof    TEXT,                        -- pseudonym 鍵による署名
    request_type    TEXT,                        -- 'disclosure' | 'deletion' | 'opt_out'
    handled_at      TIMESTAMPTZ,
    outcome         TEXT
);
```

**注意**:
- バケットからの再識別困難性は数学的に検証 (information leak ≤ ε bits)
- 90 日 TTL で古いデータ自動消去
- match テーブル発生時のみ通知、生バケットの分析は禁止

---

## 4. False Positive 対策

LSH は近似なので必ず誤マッチが起きる。誤マッチで誤通報が起きると逆に被害が出る。

| 対策 | 効果 |
|------|------|
| 5 投影並列、3/5 一致で発火 | FP rate ~ 10⁻⁴ |
| バケット発火後、被害者間で写真を E2E 比較 | 人間の最終判定 |
| NPO カウンセラー仲介必須 | 暴走防止 |
| 「他 N 人に類似」のみ通知、相手の identity は出さない | 誤通知でも害が小さい |
| 通知文に「類似 ≠ 同一人物」を明記 | 認知バイアス回避 |
| ≥3 一致まで警察提出を推奨しない | 偶然の重なり排除 |

---

## 5. 法的論証

### 5.1 個人情報保護法

| 段階 | 該当性 | 根拠 |
|------|-------|------|
| 端末内顔エンベディング | 個人識別符号 (2-2-1) | 私的利用 (5条「事業者」非該当) |
| LSH バケット送信 | **微妙**。再識別可能性 ε で評価 | 安全管理 + 同意で正当化 |
| マッチ検出時の pseudonym | 仮名加工情報相当 | 41 条準拠 |
| 警察提供 (≥3 確認後 + 本人同意) | 第三者提供 | 27-1-1 (法令)、27-1-2 (生命)、27 一般 (同意) |

**戦略**: 内閣府男女共同参画局 / 都道府県の **DV・性犯罪支援団体認定** を取り、警察と業務協力協定を結ぶ。
これで Coordinator は「法令の規定に基づく業務」として 27-1-1 を発動できる。

### 5.2 名誉毀損 (刑法 230) 回避

- マッチ通知に **「同一人物である」と断定しない**
- バケット類似 = 「あなたの記録した特徴と似ているパターンが他にあった」
- NPO 仲介の対話で本人同士が確認するまで identity は確定しない
- 警察提出後の捜査で初めて公的な特定が行われる

### 5.3 ストーカー規制法逆抵触回避

- 加害者の所在追跡は **行わない**
- バケットマッチは **被害者間** の関連付けであり加害者監視ではない
- 加害者を特定したらアプリの追跡機能は終了 (警察に引き継ぎ)

### 5.4 「予測警察」差別問題回避

- 地域への汚名付与なし
- 個人スコアリングなし
- 「複数被害者の証言の符号」は **個人** に紐付く事実、 **属性** に紐付く偏見ではない

---

## 6. 空氣盒子的「公共財」アウトプット

FEWN の集約データから、**個人を特定せずに** 公開できるもの:

| 出力 | 例 |
|------|---|
| パターン密度マップ | 「23 区内、月別に類似パターン件数」(k>=20) |
| モダス・オペランディの傾向 | 「夜間 22-26 時、駅から 500m 以内、徒歩接近型」 |
| 累犯指標 | 「平均的に 1 加害パターンあたり N 人の被害者」 |
| 警察対応ギャップ | 「マッチ確認後、捜査着手までの平均日数」|
| 都道府県格差 | 「マッチから保護命令までの所要日数 Top/Bottom」|

これが **空氣盒子の「PM2.5 マップ」相当** で、政策提言の武器になる。

---

## 7. 端末側実装スケルトン (iOS / Swift)

```swift
import Vision
import CryptoKit

struct VaultRecord {
    let perpId: UUID            // local pseudonym for this perpetrator
    let embedding: [Float]      // 512-dim, encrypted at rest
    let incidentDate: Date
    let blurredLocation: CLLocationCoordinate2D
    let notes: String           // user's own note, never sent
}

class LocalVault {
    // SQLCipher-backed, key in Secure Enclave
    private let db: EncryptedDB

    func record(face image: UIImage, ...) async throws -> VaultRecord {
        let embedding = try await FaceEmbedder.embed(image)  // on-device Core ML
        let rec = VaultRecord(...)
        try db.insert(rec)
        return rec
    }
}

class FEWNUploader {
    // 5 公開 random projections (アプリ更新時にローテーション)
    static let projections: [[Float]] = loadProjections()

    func makeBucketSubmissions(_ rec: VaultRecord) -> [BucketSubmission] {
        return projections.enumerated().map { (i, proj) in
            let bucket = lshBucket(rec.embedding, projection: proj)
            return BucketSubmission(
                bucketHash: bucket,
                projectionId: i,
                commitHmac: hmac(secret: deviceSecret, message: rec.perpId.uuidString),
                blurredGeom: rec.blurredLocation,
                blurredTime: rec.incidentDate.startOfDay
            )
        }
    }

    func upload(_ subs: [BucketSubmission]) async throws {
        // HTTPS to Coordinator, no PII
        try await api.post("/v1/submissions", body: subs)
    }
}

func lshBucket(_ emb: [Float], projection: [Float]) -> Data {
    // 64-bit signed projection → bit pattern
    let bits = stride(from: 0, to: projection.count, by: emb.count).map { offset -> UInt8 in
        let p = Array(projection[offset..<offset+emb.count])
        let s = zip(p, emb).map(*).reduce(0, +)
        return s > 0 ? 1 : 0
    }
    return packBits(bits)  // 8 bytes
}
```

---

## 8. Coordinator 側マッチ検出 (Python / 概念)

```python
async def detect_matches(window_days: int = 30, k: int = 2):
    """
    最近 N 日のバケット投稿から、同一バケット (5 投影中 ≥3 一致) で
    異なる psi_id が ≥k 名いる組を検出。
    """
    sql = """
    WITH recent AS (
        SELECT psi_id, bucket_hash, projection_id
        FROM fewn.bucket_submissions
        WHERE submitted_at > now() - interval '%s days'
          AND expires_at > now()
    ),
    bucket_psis AS (
        SELECT bucket_hash, projection_id, array_agg(DISTINCT psi_id) AS psis
        FROM recent
        GROUP BY bucket_hash, projection_id
        HAVING count(DISTINCT psi_id) >= %s
    ),
    -- psi グループごとに、5 投影中いくつ一致したか
    psi_pairs AS (
        SELECT psis, count(*) AS n_proj_hit
        FROM bucket_psis
        GROUP BY psis
        HAVING count(*) >= 3   -- 5 中 3 投影一致
    )
    SELECT * FROM psi_pairs;
    """
    rows = await db.fetch(sql, window_days, k)
    for row in rows:
        await create_match(
            psi_ids=row["psis"],
            n_proj=row["n_proj_hit"],
            confidence=estimate_fp(row["n_proj_hit"]),
        )

async def create_match(psi_ids, n_proj, confidence):
    match_id = uuid4()
    await db.execute("INSERT INTO fewn.matches ...", ...)
    for psi in psi_ids:
        await notify_pseudonym(psi, match_id)
        await db.execute("INSERT INTO fewn.match_members ...", ...)
```

---

## 9. ガバナンス（再掲＋強化）

| 主体 | 鍵保有 | 役割 |
|------|-------|------|
| 警察庁 | m-of-n 鍵 1 枚 | マッチ確認後の捜査 |
| 弁護士連合会 | m-of-n 鍵 1 枚 | 法的助言、被害者代理 |
| NPO 連合 (≥5 団体) | 各 1 枚 | カウンセリング、仲介 |
| 大学 IRB | 監査鍵 (読み取り専用) | 倫理審査、年次外部監査 |

m=4, n=8 (例) → 4 主体合意なしに マッチ復号不可。

---

## 10. Phase 計画

### Phase 0 (1 ヶ月)
- [ ] 顔エンベディング on-device プロトタイプ (iOS, Vision Framework)
- [ ] SQLCipher Vault 実装
- [ ] LSH 投影パラメータ実験 (FP/FN rate 測定)
- [ ] OpenMined PSI 評価

### Phase 1 (2-3 ヶ月)
- [ ] Coordinator サーバ (FastAPI + PostGIS) MVP
- [ ] バケット投稿 + マッチ検出のクローズドβ
- [ ] NPO 1 団体とパイロット (内部運用、本番投入なし)
- [ ] 弁連 / 内閣府との設計レビュー

### Phase 2 (4-6 ヶ月)
- [ ] DV/性犯罪支援団体 認定取得
- [ ] 警察庁との業務協力協定
- [ ] m-of-n 鍵管理セレモニー
- [ ] 限定公開リリース

### Phase 3 (12 ヶ月+)
- [ ] 全国 NPO 連合へ拡大
- [ ] Steward Board 正式発足
- [ ] 透明性レポート Q1 公開

---

## 11. 失敗モード対策

| 失敗モード | 対策 |
|-----------|------|
| LSH 衝突で誤マッチ → 誤通報 | 5 投影 ≥3 一致 + NPO 人間判断 + 「類似」と明示 |
| Coordinator が悪意で全バケット解析 | 鍵分散 + 監査ログ + IRB 外部監査 + バケットからの再識別困難性数学的証明 |
| なりすまし psi_id 大量投稿 | 端末アテステーション (DeviceCheck/SafetyNet) + レート制限 + NPO 紹介必須化 |
| 加害者が逆利用 (被害者を特定しようとする) | psi_id は端末ローカル、Coordinator は実名持たない、NPO 経由連絡のみ |
| 「変態認定された」と加害者が名誉毀損訴訟 | 通知に「同一断定なし」明記、NPO 介在で公的記録、訴訟リスクは NPO/警察が一次的に負う構造 |
| 警察が捜査せず塩漬け | 透明性レポートで都道府県別「マッチから捜査着手まで」可視化 → 政治圧力 |

---

## 12. 一文サマリー

> **FEWN は空氣盒子の「分散センサー → 公共マップ」モデルを、暗号学的プライバシー保護の上で被害証言に適用する。**
> **顔写真は端末から出ない。バケットだけ送る。重なった時だけ NPO 仲介で被害者同士が会える。連名告訴で初めて公的捜査が動く。これが旧来の「単独の被害者は無視される」社会安全網の穴を埋める唯一の合法な道である。**

---

**End of Document**
