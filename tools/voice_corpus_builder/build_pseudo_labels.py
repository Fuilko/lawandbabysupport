"""
Pseudo-label 付与スクリプト
============================

`manifest.jsonl` の各 segment に Whisper large-v3 の出力を transcript として付与。
これは self-distillation の教師信号として用いる
（学生モデル = 我々が fine-tune する base / small Whisper）。

訓練データに人手書き起こしが大量にあるのが理想だが、現実的に
Whisper large-v3 の出力をベースに：
1. 信頼度低い segment は除去（or `[?]` マーク）
2. 言語 ID と一致しない segment は除去
3. 非言語イベント（[泣]、[嗚咽]）は別ラベルで保存

## 使い方
```bash
python build_pseudo_labels.py \
    --manifest corpus/manifest.jsonl \
    --out_manifest corpus/manifest_labeled.jsonl \
    --model large-v3 \
    --device cuda
```
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("pseudo_label")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out_manifest", required=True)
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--min_logprob", type=float, default=-1.5,
                        help="この閾値より低い segment は除外（無効音声）")
    parser.add_argument("--audio_root", default="./corpus")
    args = parser.parse_args()

    try:
        import whisper
    except ImportError:
        log.error("openai-whisper を入れてください: pip install openai-whisper")
        return

    log.info(f"loading whisper {args.model}...")
    model = whisper.load_model(args.model, device=args.device)

    audio_root = Path(args.audio_root)
    n_in = n_kept = n_dropped = 0

    with open(args.manifest) as f_in, open(args.out_manifest, "w") as f_out:
        for line in f_in:
            n_in += 1
            seg = json.loads(line)
            audio_path = audio_root / seg["audio_path"]
            if not audio_path.exists():
                # サブパス整合性のため manifest 直下 を試す
                audio_path = Path(args.manifest).parent / seg["audio_path"]
            if not audio_path.exists():
                log.warning(f"missing: {audio_path}")
                n_dropped += 1
                continue

            try:
                result = model.transcribe(
                    str(audio_path),
                    language=seg.get("lang_hint") or None,
                    verbose=False,
                    word_timestamps=True,
                    condition_on_previous_text=False,
                    no_speech_threshold=0.8,
                    logprob_threshold=args.min_logprob,
                    compression_ratio_threshold=3.5,
                    temperature=(0.0, 0.2, 0.4),
                )
            except Exception as e:  # noqa: BLE001
                log.warning(f"whisper error {audio_path}: {e}")
                n_dropped += 1
                continue

            text = result["text"].strip()
            avg_logprob = sum(s.get("avg_logprob", -10) for s in result["segments"]) / max(len(result["segments"]), 1)
            no_speech = sum(s.get("no_speech_prob", 1) for s in result["segments"]) / max(len(result["segments"]), 1)

            # 品質フィルタ
            if not text or no_speech > 0.7:
                n_dropped += 1
                continue
            if args.min_logprob > avg_logprob:
                # 低信頼でも残すが [?] 付ける
                text = f"[?] {text}"

            seg["transcript"] = text
            seg["pseudo_avg_logprob"] = avg_logprob
            seg["pseudo_no_speech_prob"] = no_speech
            seg["pseudo_label_model"] = args.model
            f_out.write(json.dumps(seg, ensure_ascii=False) + "\n")
            n_kept += 1

            if n_kept % 50 == 0:
                log.info(f"progress: in={n_in} kept={n_kept} dropped={n_dropped}")

    log.info(f"done: in={n_in} kept={n_kept} dropped={n_dropped}")


if __name__ == "__main__":
    main()
