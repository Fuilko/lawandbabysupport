"""
LegalShield 緊急音声 ASR 評価
================================

`eval_set/manifest.jsonl` を読込み、ベースモデルと fine-tune 済モデルの
WER / CER / 非言語イベント Recall を比較。

## 評価カテゴリ
1. **whispered**: 耳語・気息音
2. **disfluent**: 不流暢発話（あー、えー、断片）
3. **emotional_cry**: 泣きながらの発話
4. **panic**: パニック・早口
5. **multilingual**: 在留外国人想定の非ネイティブ日本語 / 母語混在
6. **child_speech**: 子供の発話

## 使い方
```bash
# 1. ベースモデルで評価
python eval_emergency_set.py \
    --eval_manifest eval_set/manifest.jsonl \
    --model openai/whisper-large-v3-turbo \
    --output baseline_results.json

# 2. LoRA 適用版で評価
python eval_emergency_set.py \
    --eval_manifest eval_set/manifest.jsonl \
    --model openai/whisper-large-v3-turbo \
    --lora_adapter ./whisper_lora_out/adapter_final \
    --output lora_results.json

# 3. 比較
python eval_emergency_set.py compare baseline_results.json lora_results.json
```
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("eval")


CATEGORIES = [
    "whispered", "disfluent", "emotional_cry",
    "panic", "multilingual", "child_speech",
]


def cmd_evaluate(args: argparse.Namespace) -> None:
    import torch
    from transformers import WhisperForConditionalGeneration, WhisperProcessor
    import evaluate

    log.info(f"loading {args.model}")
    processor = WhisperProcessor.from_pretrained(args.model)
    model = WhisperForConditionalGeneration.from_pretrained(
        args.model, torch_dtype=torch.float16
    ).to(args.device)

    if args.lora_adapter:
        from peft import PeftModel
        log.info(f"applying LoRA: {args.lora_adapter}")
        model = PeftModel.from_pretrained(model, args.lora_adapter)
        model = model.merge_and_unload()

    cer = evaluate.load("cer")
    wer = evaluate.load("wer")

    by_cat: dict[str, list[tuple[str, str]]] = defaultdict(list)
    nonverbal_total = 0
    nonverbal_recalled = 0

    import soundfile as sf

    with open(args.eval_manifest) as f:
        eval_rows = [json.loads(l) for l in f]
    log.info(f"eval set: {len(eval_rows)} rows")

    for i, row in enumerate(eval_rows):
        audio_path = Path(args.audio_root) / row["audio_path"]
        if not audio_path.exists():
            audio_path = Path(args.eval_manifest).parent / row["audio_path"]
        try:
            audio, sr = sf.read(str(audio_path))
        except Exception as e:  # noqa: BLE001
            log.warning(f"skip {audio_path}: {e}")
            continue

        inputs = processor.feature_extractor(
            audio, sampling_rate=sr, return_tensors="pt"
        ).input_features.to(args.device).half()

        with torch.no_grad():
            pred_ids = model.generate(
                inputs,
                max_new_tokens=225,
                num_beams=1,
                language=row.get("lang", "ja"),
                task="transcribe",
            )
        hyp = processor.tokenizer.decode(pred_ids[0], skip_special_tokens=True).strip()
        ref = row["text"]
        cat = row.get("category", "other")

        by_cat[cat].append((ref, hyp))

        # 非言語イベント Recall
        for tag in ["[泣]", "[嗚咽]", "[激しい呼吸]", "[沈黙"]:
            if tag in ref:
                nonverbal_total += 1
                if tag in hyp:
                    nonverbal_recalled += 1

        if (i + 1) % 20 == 0:
            log.info(f"progress {i + 1}/{len(eval_rows)}")

    # 集計
    results: dict = {"per_category": {}, "overall": {}}
    all_refs: list[str] = []
    all_hyps: list[str] = []
    for cat, pairs in by_cat.items():
        if not pairs:
            continue
        refs, hyps = zip(*pairs)
        all_refs.extend(refs)
        all_hyps.extend(hyps)
        c = 100 * cer.compute(predictions=list(hyps), references=list(refs))
        w = 100 * wer.compute(predictions=list(hyps), references=list(refs))
        results["per_category"][cat] = {"cer": c, "wer": w, "n": len(pairs)}

    if all_refs:
        results["overall"]["cer"] = 100 * cer.compute(predictions=all_hyps, references=all_refs)
        results["overall"]["wer"] = 100 * wer.compute(predictions=all_hyps, references=all_refs)
    if nonverbal_total > 0:
        results["overall"]["nonverbal_recall"] = nonverbal_recalled / nonverbal_total

    Path(args.output).write_text(json.dumps(results, indent=2, ensure_ascii=False))
    log.info(f"saved → {args.output}")
    print(json.dumps(results, indent=2, ensure_ascii=False))


def cmd_compare(args: argparse.Namespace) -> None:
    base = json.loads(Path(args.baseline).read_text())
    cand = json.loads(Path(args.candidate).read_text())

    print("=" * 70)
    print(f"{'Category':<20s} {'BaseCER':>8s} {'NewCER':>8s} {'ΔCER':>8s} {'BaseWER':>8s} {'NewWER':>8s} {'ΔWER':>8s}")
    print("-" * 70)
    for cat in CATEGORIES + ["other"]:
        if cat in base.get("per_category", {}) and cat in cand.get("per_category", {}):
            b = base["per_category"][cat]
            c = cand["per_category"][cat]
            print(f"{cat:<20s} {b['cer']:>8.2f} {c['cer']:>8.2f} {b['cer']-c['cer']:>+8.2f} "
                  f"{b['wer']:>8.2f} {c['wer']:>8.2f} {b['wer']-c['wer']:>+8.2f}")
    if "overall" in base and "overall" in cand:
        b, c = base["overall"], cand["overall"]
        print("-" * 70)
        print(f"{'OVERALL':<20s} {b.get('cer',0):>8.2f} {c.get('cer',0):>8.2f} {b.get('cer',0)-c.get('cer',0):>+8.2f} "
              f"{b.get('wer',0):>8.2f} {c.get('wer',0):>8.2f} {b.get('wer',0)-c.get('wer',0):>+8.2f}")
        if "nonverbal_recall" in c:
            print(f"\nNon-verbal event recall: {b.get('nonverbal_recall', 0):.2%} → {c['nonverbal_recall']:.2%}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    ev = sub.add_parser("evaluate")
    ev.add_argument("--eval_manifest", required=True)
    ev.add_argument("--audio_root", default="./eval_set")
    ev.add_argument("--model", default="openai/whisper-large-v3-turbo")
    ev.add_argument("--lora_adapter", default=None)
    ev.add_argument("--device", default="cuda")
    ev.add_argument("--output", required=True)
    ev.set_defaults(func=cmd_evaluate)

    cp = sub.add_parser("compare")
    cp.add_argument("baseline")
    cp.add_argument("candidate")
    cp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
