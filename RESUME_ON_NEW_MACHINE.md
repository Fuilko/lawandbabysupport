# 新電腦接續進度 — クイックガイド / Resume Progress on a New Computer

> 別の電腦に移っても、これだけで「最新の進捗・主架構・接地ルール」を AI Agent に読ませて続きから作業できます。
> Repo: `https://github.com/Fuilko/lawandbabysupport.git` · Branch: `main`

---

## ステップ 1. 程式碼を取得する

**初めてのその電腦（まだclone してない）:**
```bash
git clone https://github.com/Fuilko/lawandbabysupport.git
cd lawandbabysupport
```

**すでに clone 済み（更新するだけ）:**
```bash
cd <あなたのリポジトリの場所>/lawandbabysupport
git pull origin main
```

---

## ステップ 2. AI Agent（Windsurf / Cascade）に進捗を読ませる

Windsurf でリポジトリを開き、**チャットに次の一文を貼るだけ**：

```
まず AGENTS.md → PROGRESS.md → DEPLOYMENT_TOPOLOGY.md を読んで、
今の進捗と次の一手を教えて。接地ルール（RAG-First / 幻覚禁止）も守って。
```

> `.windsurf/rules/00-grounding.md` が常時自動ロードされるので、Agent は接地ルールを自動で守ります。

---

## ステップ 3. 自分で最新進捗を確認する

- **`PROGRESS.md`** を開く → **一番上が最新**。
- 全体像は **`AGENTS.md`**（入口）→ **`ARCHITECTURE.md`**（主架構）→ **`DEPLOYMENT_TOPOLOGY.md`**（環境/同期/開発順序）。
- 印刷用まとめ: **`docs/LegalShield_開発ハンドブック.pdf`**（再生成は §5）。

---

## ステップ 4. 作業を終えたら必ずバックアップ（GitHub へ）

```bash
cd <repo>/lawandbabysupport
git add -A
git commit -m "作業内容を簡潔に書く"
git push origin main
```

> これをやらないと別電腦に同期されません。寝る前/作業後の習慣に。

---

## ステップ 5. ハンドブック PDF を再生成したいとき（任意・Mac）

```bash
cd <repo>/lawandbabysupport
# AGENTS / ARCHITECTURE / DEPLOYMENT_TOPOLOGY / PROGRESS を 1冊にまとめて PDF 化
# （詳しい生成コマンドは Cascade に「ハンドブックPDFを再生成して」と頼めばOK）
```

---

## 注意（同期されないもの）

- `ios/**/project.pbxproj`・`Package.resolved` は **gitignore**。別電腦では Xcode で再解決が要る場合あり（手順は `PROGRESS.md` 2026-06-01 参照）。
- **モデル・ベクトルDB・secrets・証拠データは git に入っていません**（容量・機密のため）。
  - モデル: `ollama pull <name:tag>` で取得
  - DB再構築: `gis/ingest/run_all.py` 等（`DEPLOYMENT_GUIDE.md` 参照）
  - secrets: `gis/.env.example` をコピーして `.env` を作る

---

## 一言

**新電腦では「git pull → AGENTS.md と PROGRESS.md を Agent に読ませる → 続きから」。終わったら git push。これだけ。**
