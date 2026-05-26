# FEWN — Forensic Evidence Witness Network

> 被害当事者が顔写真や位置情報を一切サーバに送らないまま、
> **同じ加害者・同じ事業者・同じ窓口** を記録した別の被害者と
> **暗号学的にのみ出会える** 分散型ネットワーク。

参照：Callisto Vault（米・性暴力被害者ネットワーク、2018-）の汎化版。LegalShield では **27 カテゴリ**（性暴力 / DV / ストーカー / 詐欺 / 児童虐待 / 高齢者虐待 / 外国人労働者搾取 / 消費者被害 など）に拡張。

---

## なぜ必要か（Mapry 事件の教訓）

LegalShield 発起人は、ドローン技術詐欺で被害を受けた当時、

- 10 以上の法律事務所のうち、技術論点が壁となり実質対応できたのは 3 社
- 内容証明 1 通に総額 20 万円、ソースコード解析は不能
- 検察庁からは「科警研級の専門解析は通常困難」と回答

**被害者は孤立した瞬間に「制度の隙間」に落ちる**。同じ加害者を持つ別の被害者と早期に繋がれていれば、連名告訴・公共訴訟・行政通報が可能だった。

しかし「同じ加害者を持つ被害者を探す」こと自体が**今のところ存在しない**。なぜなら：
- SNS で被害を語ると **名誉毀損** リスク
- 警察に相談しても **横断検索 DB** が無い
- 被害者個人情報を交換するのは **二次被害** の温床

→ **暗号学的マッチング** だけが解。

---

## 設計原理

### 3 つのプライバシー保証

1. **加害者識別子を端末側でハッシュ化**
   電話番号・銀行口座・URL・会社名・声紋ハッシュ → HMAC-SHA256(notary_salt, normalize(value)) → 16 byte
   サーバは生データを一度も受信しない

2. **公証人モデル**（Callisto と同じ）
   - CALL4（または独立財団）が「公証人」として `notary_salt` を保持
   - 公証人は集合演算結果（マッチありなし、件数）のみ知る
   - マッチした被害者同士も**互いの証拠内容は非開示**

3. **マッチ通知の最小化**
   - 「他にもいる」事実のみ被害者へ通知
   - 連名告訴の打診は **CALL4 弁護団が両被害者の同意を得て** 実施
   - 名誉毀損リスク回避：加害者特定情報は表に出さない

### 識別子の正規化

```
'phone:+81-90-1234-5678' → 'phone:819012345678'
'company:株式会社 Mapry'  → 'company:株式会社mapry'
'url:Https://Mapry.JP/'  → 'url:mapry.jp'
'account:三菱 1234-567'   → 'account:1234567'
```

これにより半角全角・大文字小文字・記号差・国コード差を吸収。

---

## クイック実行（demo）

```bash
# 1. 公証人鍵生成（CALL4 が一度だけ）
python fewn_demo.py init

# 2. 被害者 A 登録（Mapry 詐欺）
python fewn_demo.py register --name victim_A \
    --evidence "phone:+81-90-1234-5678" \
    --evidence "company:株式会社Mapry" \
    --evidence "url:https://mapry.jp/"

# 3. 被害者 B 登録（架空、Mapry 共通）
python fewn_demo.py register --name victim_B \
    --evidence "phone:+81-90-9999-9999" \
    --evidence "company:株式会社 Mapry"

# 4. 被害者 C 登録（無関係）
python fewn_demo.py register --name victim_C \
    --evidence "company:株式会社XYZ"

# 5. 公証人によるマッチング
python fewn_demo.py match
```

### 期待出力

```
[公証人マッチング開始] 被害者 3 名

  🚨 共通加害者ハッシュ 1 件を検出

  ── マッチペア ──
  ✓ victim_A  ⇔  victim_B
      共通加害者ハッシュ: 1 件
      個別証拠は両者とも非開示（ハッシュのみ照合）
      → CALL4 弁護団が両被害者に「他にもいる」事実のみ通知
      → 連名告訴の打診を被害者本人の同意のもと実施
```

---

## 実環境への拡張

| 段階 | 既存 demo | 本番 |
|---|---|---|
| 鍵管理 | ローカル file | HSM / AWS KMS、CALL4 が boards で管理 |
| 集合演算 | プレーン intersection | **PSI-Cardinality** (Google `private-join-and-compute`) |
| 端末↔サーバ通信 | – | mTLS + 端末公開鍵証明書 |
| 通知 | print | iOS APNs + 暗号化チャンネル |
| 連名告訴 BR | – | CALL4 公開訴訟 markdown 自動生成 → 編集 → 公開 |
| 加害者特定の検証 | – | 弁護団による登記簿・帝国 DB 照合 |
| ストレージ | jsonl | PostgreSQL + 監査 log + 削除権 |

---

## 法的・倫理的検討

### 適用法令

- **個人情報保護法**：ハッシュは「容易照合性」の有無で個人情報該当性が分かれる。salt が外部に出ない設計で非該当を狙う。
- **名誉毀損 (刑 230)**：マッチ通知は「他にもいる事実」のみ、加害者特定情報は CALL4 弁護団内のみで使用。
- **偽計業務妨害**：誤マッチ防止のため最低 2 件以上の証拠ハッシュ照合 + 弁護団による事前検証。
- **電気通信事業法**：公証人サーバは届出対象になる可能性、要確認。
- **プロバイダ責任制限法**：マッチ通知の送信は当該被害者本人の同意を要件とする。

### IRB / ELSI

- 被害者本人の事前同意（informed consent）必須
- 子供・障害者は法定代理人同意 + 児相連携
- データ保持期間：訴訟提起時または明示削除要求まで（最長 5 年）
- 第三者提供：CALL4 弁護団のみ、書面同意の下

---

## TODO

- [ ] PSI-Cardinality 実装（OpenMined PSI または `private-join-and-compute`）
- [ ] iOS Swift クライアント（`FEWNClient.swift`）
- [ ] サーバ side FastAPI endpoint
- [ ] CALL4 公開訴訟 markdown export
- [ ] 加害者特定の弁護団検証フロー（運用 SOP）
- [ ] 削除権 + 撤回フロー（GDPR 17 条相当）

---

## 参考文献

- Project Callisto: https://www.projectcallisto.org/
- Rajagopalan, Anjana et al. (2018) "Callisto: Information Escrows for Survivors of Sexual Violence"
- Google `private-join-and-compute`: https://github.com/google/private-join-and-compute
- OpenMined PSI: https://github.com/OpenMined/PSI
