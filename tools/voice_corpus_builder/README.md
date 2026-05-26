# Voice Corpus Builder — LegalShield 緊急音声 ASR

被害者の **驚慌・泣き声・耳語・断片発話** に強い Whisper を作るためのデータパイプライン。

---

## ディレクトリ構成

```
tools/voice_corpus_builder/
├── seed_queries.yaml          ← YouTube 検索クエリ + 在留外国人比率配分
├── download_and_process.py    ← yt-dlp + ffmpeg + Silero VAD で segment 化
├── build_pseudo_labels.py     ← Whisper large-v3 で pseudo-label 付与
├── train_whisper_lora.py      ← Windows RTX 4080 で LoRA fine-tune
├── eval_emergency_set.py      ← WER/CER + 非言語イベント Recall 評価
├── eval_set/SPEC.md           ← 200 件 評価集の仕様書
├── requirements.txt
└── README.md  (this)
```

---

## 全体フロー

```
[1] discover  ─── seed_queries.yaml   ──→  urls.jsonl  (~10 万 URL)
       │
[2] process   ─── yt-dlp + VAD        ──→  corpus/audio/*.wav
                                              corpus/manifest.jsonl
       │ (~1000 時間)
[3] pseudo-label ── Whisper large-v3  ──→  corpus/manifest_labeled.jsonl
       │
[4] train (Windows RTX 4080)
       └── LoRA fine-tune              ──→  whisper_lora_out/adapter_final/
       │
[5] evaluate  ─── eval_set/manifest    ──→  baseline_results.json
                                              lora_results.json
                                              → compare で改善幅を測定
       │
[6] (任意) WhisperKit / CoreML 変換 → iOS App に組込
```

---

## ステップ別コマンド

### Step 1：URL 収集（Mac でも Windows でも）

```bash
cd tools/voice_corpus_builder
pip install -r requirements.txt
python download_and_process.py discover --config seed_queries.yaml --out urls.jsonl
```

→ `urls.jsonl` に検索結果が書かれる（重複除外・長さフィルタ済）。

### Step 2：DL + VAD + segment（Mac で十分、~24 時間）

```bash
python download_and_process.py process --urls urls.jsonl --out_dir ./corpus
```

→ `corpus/audio/*.wav`（16 kHz mono、3〜30 秒の発話セグメント）  
→ `corpus/manifest.jsonl`

途中で止めても resume 可能（`done_ids` で既処理動画をスキップ）。

### Step 3：Whisper large-v3 で pseudo-label（GPU 推奨、~6 時間 / 1000h）

```bash
python build_pseudo_labels.py \
    --manifest corpus/manifest.jsonl \
    --out_manifest corpus/manifest_labeled.jsonl \
    --model large-v3 --device cuda
```

低信頼セグメントは `[?]` プレフィックス、空セグメントは除外。

### Step 4：Windows RTX 4080 で LoRA fine-tune（~2 日 / 1000h × 3 epoch）

```bash
python train_whisper_lora.py \
    --manifest corpus/manifest_labeled.jsonl \
    --base_model openai/whisper-large-v3-turbo \
    --output_dir ./whisper_lora_out \
    --num_train_epochs 3 \
    --per_device_train_batch_size 4 \
    --gradient_accumulation_steps 8 \
    --learning_rate 1e-4 \
    --weight_lang_ja 0.65 \
    --weight_lang_other 0.35
```

VRAM 16 GB に収まる（gradient_checkpointing + fp16）。

### Step 5：評価セットで WER/CER 比較

```bash
# ベースライン
python eval_emergency_set.py evaluate \
    --eval_manifest eval_set/manifest.jsonl \
    --model openai/whisper-large-v3-turbo \
    --output baseline_results.json

# LoRA 適用版
python eval_emergency_set.py evaluate \
    --eval_manifest eval_set/manifest.jsonl \
    --model openai/whisper-large-v3-turbo \
    --lora_adapter ./whisper_lora_out/adapter_final \
    --output lora_results.json

# 改善幅を表示
python eval_emergency_set.py compare baseline_results.json lora_results.json
```

期待される改善（私の推定）：
- `emotional_cry` カテゴリ：CER -15〜-25 ポイント
- `whispered` カテゴリ：CER -10〜-20
- `disfluent` カテゴリ：CER -20〜-30（最大）

### Step 6（任意）：iOS 用に変換

```bash
# adapter merge → full weights
python merge_lora.py --base openai/whisper-large-v3-turbo \
    --adapter whisper_lora_out/adapter_final \
    --out merged_model

# CoreML / WhisperKit 形式へ
pip install whisperkittools
whisperkit-cli convert --model merged_model --output ./whisperkit_models/legalshield_v1
```

iOS 側 `WhisperKitTranscriber(modelName: "legalshield_v1")` で読込。

---

## 機械スペック目安

| Step | Mac M3 | Windows RTX 4080 | 備考 |
|---|---|---|---|
| 1 discover | ✓ 30 分 | ✓ 30 分 | ネットワーク律速 |
| 2 process | ✓ 24h / 1000h | ✓ 24h / 1000h | Disk I/O 律速 |
| 3 pseudo-label | △ 数日 | ✓ 6h | GPU 必須 |
| 4 train | △ ~MLX で可 | **✓ 2 日** | **本番はここ** |
| 5 evaluate | ✓ 30 分 | ✓ 10 分 | |

---

## ストレージ

- 1000 時間 × 16kHz mono = **約 110 GB**
- `manifest_labeled.jsonl` ≒ 100 MB
- LoRA adapter ≒ 50 MB
- 評価セット 200 件 ≒ 1 GB

外付け SSD 推奨。

---

## 在留外国人比率の更新

`seed_queries.yaml` の `weight` は **2024 年 12 月 出入国在留管理庁 統計** ベース。
毎年 6 月・12 月の更新時に再計算推奨：

```python
# 例：年次更新
import requests
# 出入国在留管理庁 PDF / e-Stat から CSV 取得 → weight 再計算
```
