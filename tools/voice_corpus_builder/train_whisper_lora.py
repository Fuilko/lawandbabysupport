"""
Whisper LoRA Fine-tune for Emergency Voice ASR
================================================

Windows RTX 4080 (16 GB) 想定。HuggingFace Transformers + PEFT (LoRA)。

## 必要環境
```bash
pip install -U "transformers>=4.45" datasets accelerate peft
pip install soundfile librosa evaluate jiwer
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

## 使い方
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

## Tips（緊急音声特化）
- `predict_with_generate=True` で WER 検証
- `forced_decoder_ids` を空にして 自動言語判定維持
- LoRA target = `q_proj, v_proj, k_proj, out_proj`（attention 全体）
- gradient_checkpointing で 16 GB に収める
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("whisper_lora")


# ────────────────────────────────────────────
# Manifest → Dataset
# ────────────────────────────────────────────

def build_dataset(manifest_path: str, audio_root: str, max_seconds: float = 30.0):
    from datasets import Dataset, Audio

    rows = []
    with open(manifest_path) as f:
        for line in f:
            j = json.loads(line)
            if not j.get("transcript"):
                continue
            if j["duration"] > max_seconds:
                continue
            rows.append({
                "audio": str(Path(audio_root) / j["audio_path"]),
                "text": j["transcript"],
                "lang": j.get("lang_hint", "ja"),
                "category_id": j.get("category_id", "unknown"),
                "duration": j["duration"],
            })
    log.info(f"loaded {len(rows)} segments")
    ds = Dataset.from_list(rows)
    ds = ds.cast_column("audio", Audio(sampling_rate=16000))
    return ds


def apply_lang_weight_sampling(
    ds, weight_lang_ja: float, weight_lang_other: float, seed: int = 42
):
    """在留外国人比率を反映した重み付きサンプリング"""
    random.seed(seed)
    np.random.seed(seed)

    indices = list(range(len(ds)))
    weights = [
        weight_lang_ja if ds[i]["lang"] == "ja" else weight_lang_other
        for i in indices
    ]
    # 正規化
    total = sum(weights)
    probs = [w / total for w in weights]
    n_sample = len(ds)  # 同サイズ
    sampled_idx = np.random.choice(indices, size=n_sample, replace=True, p=probs)
    return ds.select(sampled_idx.tolist())


# ────────────────────────────────────────────
# 訓練本体
# ────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--audio_root", default="./corpus")
    parser.add_argument("--base_model", default="openai/whisper-large-v3-turbo")
    parser.add_argument("--output_dir", default="./whisper_lora_out")
    parser.add_argument("--num_train_epochs", type=int, default=3)
    parser.add_argument("--per_device_train_batch_size", type=int, default=4)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=8)
    parser.add_argument("--learning_rate", type=float, default=1e-4)
    parser.add_argument("--lora_r", type=int, default=32)
    parser.add_argument("--lora_alpha", type=int, default=64)
    parser.add_argument("--lora_dropout", type=float, default=0.05)
    parser.add_argument("--weight_lang_ja", type=float, default=0.65)
    parser.add_argument("--weight_lang_other", type=float, default=0.35)
    parser.add_argument("--eval_split_ratio", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    import torch
    from transformers import (
        WhisperForConditionalGeneration,
        WhisperProcessor,
        Seq2SeqTrainingArguments,
        Seq2SeqTrainer,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    import evaluate

    # 1. Dataset
    ds = build_dataset(args.manifest, args.audio_root)
    ds = apply_lang_weight_sampling(
        ds, args.weight_lang_ja, args.weight_lang_other, seed=args.seed
    )
    split = ds.train_test_split(test_size=args.eval_split_ratio, seed=args.seed)
    train_ds = split["train"]
    eval_ds = split["test"]

    # 2. Processor / Model
    log.info(f"loading processor & model: {args.base_model}")
    processor = WhisperProcessor.from_pretrained(args.base_model)
    model = WhisperForConditionalGeneration.from_pretrained(
        args.base_model,
        torch_dtype=torch.float16,
    )
    model.config.forced_decoder_ids = None     # 自動言語判定維持
    model.config.suppress_tokens = []
    model.generation_config.forced_decoder_ids = None
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()

    # 3. LoRA
    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "v_proj", "k_proj", "out_proj"],
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="SEQ_2_SEQ_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 4. Preprocess
    def preprocess(batch):
        audio = batch["audio"]
        inputs = processor.feature_extractor(
            audio["array"],
            sampling_rate=audio["sampling_rate"],
            return_tensors="pt",
        )
        batch["input_features"] = inputs.input_features[0]
        # 多言語対応：lang token を tokenizer に通す
        with processor.as_target_processor():
            tokenized = processor(
                text=batch["text"],
                return_tensors="pt",
                truncation=True,
                max_length=448,
            )
        batch["labels"] = tokenized.input_ids[0]
        return batch

    log.info("preprocessing train set...")
    train_ds = train_ds.map(preprocess, remove_columns=train_ds.column_names, num_proc=4)
    eval_ds = eval_ds.map(preprocess, remove_columns=eval_ds.column_names, num_proc=4)

    # 5. Collator
    @dataclass
    class DataCollator:
        def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
            input_features = [
                {"input_features": f["input_features"]} for f in features
            ]
            batch = processor.feature_extractor.pad(input_features, return_tensors="pt")
            label_features = [{"input_ids": f["labels"]} for f in features]
            labels_batch = processor.tokenizer.pad(label_features, return_tensors="pt")
            labels = labels_batch["input_ids"].masked_fill(
                labels_batch.attention_mask.ne(1), -100
            )
            batch["labels"] = labels
            return batch

    collator = DataCollator()

    # 6. Metric (CER for ja/zh, WER for others)
    cer_metric = evaluate.load("cer")
    wer_metric = evaluate.load("wer")

    def compute_metrics(pred):
        pred_ids = pred.predictions
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        pred_str = processor.tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)
        cer = 100 * cer_metric.compute(predictions=pred_str, references=label_str)
        wer = 100 * wer_metric.compute(predictions=pred_str, references=label_str)
        return {"cer": cer, "wer": wer}

    # 7. Trainer
    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.per_device_train_batch_size,
        per_device_eval_batch_size=args.per_device_train_batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_steps=200,
        num_train_epochs=args.num_train_epochs,
        gradient_checkpointing=True,
        fp16=True,
        eval_strategy="steps",
        eval_steps=500,
        save_steps=500,
        save_total_limit=3,
        logging_steps=25,
        predict_with_generate=True,
        generation_max_length=225,
        report_to=["tensorboard"],
        load_best_model_at_end=True,
        metric_for_best_model="cer",
        greater_is_better=False,
        remove_unused_columns=False,
        label_names=["labels"],
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=collator,
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )

    log.info("start training")
    trainer.train()

    # 8. LoRA adapter のみ保存
    model.save_pretrained(f"{args.output_dir}/adapter_final")
    log.info(f"LoRA adapter saved → {args.output_dir}/adapter_final")
    log.info("merge & convert to CoreML / GGUF for iOS deployment if needed")


if __name__ == "__main__":
    main()
