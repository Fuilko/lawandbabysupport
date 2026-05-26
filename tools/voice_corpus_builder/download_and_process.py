"""
LegalShield 緊急時被害者音声 ASR 訓練データ構築 パイプライン
=================================================================

YouTube から seed クエリで音声収集 → VAD で発話区間抽出 → 16kHz mono WAV →
manifest.jsonl に書き込み（HuggingFace datasets / Whisper trainer 互換）

## 使用方法

```bash
pip install -r requirements.txt

# 1. シードクエリから検索 → URL リスト生成
python download_and_process.py discover --config seed_queries.yaml --out urls.jsonl

# 2. URL リストから DL + 処理
python download_and_process.py process --urls urls.jsonl --out_dir ./corpus

# 3. 既存ファイルから再処理のみ (再 DL なし)
python download_and_process.py reprocess --in_dir ./raw --out_dir ./corpus
```

## 出力構造

```
corpus/
├── manifest.jsonl       ← 各 segment 1 行 (audio_path, duration, lang, labels...)
├── audio/
│   ├── jp_doc_<videoid>_<seg>.wav   16kHz mono
│   └── ...
└── stats.json
```

## 法的・倫理的留意
- 学術非商用 ASR 訓練目的限定
- 出力モデル重みは非公開、原音声の二次配布なし
- AudioSet / Common Voice / Mozilla CV など公開コーパスとの併用推奨
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterator

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("voice_builder")


# ────────────────────────────────────────────
# データクラス
# ────────────────────────────────────────────

@dataclass
class VideoEntry:
    url: str
    video_id: str
    title: str
    duration_sec: float
    lang_hint: str
    category_id: str
    view_count: int = 0


@dataclass
class Segment:
    audio_path: str
    duration: float
    start_sec: float
    end_sec: float
    source_video_id: str
    source_url: str
    category_id: str
    lang_hint: str
    title: str = ""
    transcript: str | None = None       # 後段で Whisper pseudo-label 付与
    is_voiced: bool = True
    extra_labels: list[str] = field(default_factory=list)


# ────────────────────────────────────────────
# Step 1: discover URLs by yt-dlp ytsearch
# ────────────────────────────────────────────

def cmd_discover(args: argparse.Namespace) -> None:
    cfg = yaml.safe_load(open(args.config))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    seen_ids: set[str] = set()
    n_written = 0

    with out_path.open("w") as f_out:
        for cat in cfg["categories"]:
            for query in cat["queries"]:
                n = cat.get("max_per_query", 20)
                search_url = f"ytsearch{n}:{query}"
                log.info(f"[discover] {cat['id']} :: {query} (n={n})")
                videos = _yt_dlp_search(search_url)
                for v in videos:
                    if v.video_id in seen_ids:
                        continue
                    if v.duration_sec < cfg["filters"]["min_duration_sec"]:
                        continue
                    if v.duration_sec > cfg["filters"]["max_duration_sec"]:
                        continue
                    if v.view_count < cfg["filters"].get("min_view_count", 0):
                        continue
                    seen_ids.add(v.video_id)
                    v.category_id = cat["id"]
                    v.lang_hint = cat["lang"]
                    f_out.write(json.dumps(asdict(v), ensure_ascii=False) + "\n")
                    n_written += 1
    log.info(f"[discover] wrote {n_written} URL entries → {out_path}")


def _yt_dlp_search(query_url: str) -> list[VideoEntry]:
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        "--skip-download",
        query_url,
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        log.warning(f"timeout: {query_url}")
        return []
    entries = []
    for line in out.stdout.splitlines():
        try:
            j = json.loads(line)
            entries.append(VideoEntry(
                url=f"https://www.youtube.com/watch?v={j['id']}",
                video_id=j["id"],
                title=j.get("title", ""),
                duration_sec=float(j.get("duration") or 0),
                view_count=int(j.get("view_count") or 0),
                lang_hint="",
                category_id="",
            ))
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return entries


# ────────────────────────────────────────────
# Step 2: process — DL + ffmpeg + VAD + segment
# ────────────────────────────────────────────

def cmd_process(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    audio_dir = out_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = out_dir / "_raw_temp"
    raw_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / "manifest.jsonl"
    stats_path = out_dir / "stats.json"

    # 既存 manifest を読む（resume 対応）
    done_ids: set[str] = set()
    if manifest_path.exists():
        for line in manifest_path.open():
            try:
                j = json.loads(line)
                done_ids.add(j["source_video_id"])
            except json.JSONDecodeError:
                continue
        log.info(f"resume: {len(done_ids)} videos already processed")

    total_dur = 0.0
    n_videos = 0
    n_segments = 0

    with manifest_path.open("a") as f_manifest:
        for entry in _iter_url_entries(args.urls):
            if entry.video_id in done_ids:
                continue
            try:
                wav_path = _download_audio(entry, raw_dir)
                if wav_path is None:
                    continue
                segments = _vad_and_segment(
                    wav_path, entry, audio_dir,
                    min_seg=args.min_segment, max_seg=args.max_segment
                )
                for seg in segments:
                    f_manifest.write(json.dumps(asdict(seg), ensure_ascii=False) + "\n")
                    f_manifest.flush()
                    total_dur += seg.duration
                    n_segments += 1
                n_videos += 1
                # 元の長尺 WAV を削除（容量節約）
                wav_path.unlink(missing_ok=True)
            except Exception as e:  # noqa: BLE001
                log.warning(f"failed {entry.video_id}: {e}")
                continue

            if n_videos % 10 == 0:
                log.info(
                    f"progress: {n_videos} videos, {n_segments} segments, "
                    f"{total_dur/3600:.1f}h"
                )

    # 統計書出
    json.dump(
        {
            "total_videos": n_videos,
            "total_segments": n_segments,
            "total_duration_hours": total_dur / 3600,
        },
        stats_path.open("w"),
        indent=2,
    )
    log.info(f"done: {n_videos} videos, {n_segments} seg, {total_dur/3600:.1f}h")
    shutil.rmtree(raw_dir, ignore_errors=True)


def _iter_url_entries(urls_path: str) -> Iterator[VideoEntry]:
    with open(urls_path) as f:
        for line in f:
            j = json.loads(line)
            yield VideoEntry(**j)


def _download_audio(entry: VideoEntry, out_dir: Path) -> Path | None:
    out_template = str(out_dir / f"{entry.video_id}.%(ext)s")
    cmd = [
        "yt-dlp",
        "-x",                                  # 音声のみ抽出
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--postprocessor-args", "-ar 16000 -ac 1",  # 16kHz mono
        "-o", out_template,
        "--no-playlist",
        "--no-warnings",
        "--quiet",
        "--retries", "2",
        entry.url,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=600)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        log.warning(f"DL failed {entry.video_id}: {e}")
        return None
    wav_path = out_dir / f"{entry.video_id}.wav"
    return wav_path if wav_path.exists() else None


def _vad_and_segment(
    wav_path: Path,
    entry: VideoEntry,
    out_dir: Path,
    min_seg: float = 3.0,
    max_seg: float = 30.0,
) -> list[Segment]:
    """Silero VAD で発話区間検出 + ffmpeg で切出"""
    try:
        import torch
        from silero_vad import load_silero_vad, get_speech_timestamps, read_audio
    except ImportError:
        log.error("silero-vad / torch が必要 → pip install silero-vad torch torchaudio")
        sys.exit(2)

    model = load_silero_vad()
    audio = read_audio(str(wav_path), sampling_rate=16000)
    timestamps = get_speech_timestamps(
        audio, model,
        sampling_rate=16000,
        min_speech_duration_ms=200,        # 短い嗚咽も拾う
        min_silence_duration_ms=500,       # 自然な間
        threshold=0.3,                     # 閾値低 = 弱音声・耳語も拾う
        return_seconds=True,
    )

    segments: list[Segment] = []
    # 連続 timestamps を min_seg〜max_seg にまとめる
    buf_start: float | None = None
    buf_end: float | None = None
    for ts in timestamps:
        s, e = ts["start"], ts["end"]
        if buf_start is None:
            buf_start, buf_end = s, e
            continue
        if e - buf_start <= max_seg and (s - buf_end) < 1.5:
            buf_end = e
        else:
            if (buf_end - buf_start) >= min_seg:
                segments.append(_save_segment(
                    wav_path, buf_start, buf_end, entry, out_dir, len(segments)
                ))
            buf_start, buf_end = s, e
    if buf_start is not None and buf_end is not None and (buf_end - buf_start) >= min_seg:
        segments.append(_save_segment(
            wav_path, buf_start, buf_end, entry, out_dir, len(segments)
        ))
    return segments


def _save_segment(
    src_wav: Path,
    start: float,
    end: float,
    entry: VideoEntry,
    out_dir: Path,
    idx: int,
) -> Segment:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", entry.video_id)
    out_name = f"{entry.category_id}_{safe_id}_{idx:04d}.wav"
    out_path = out_dir / out_name
    duration = end - start
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(src_wav),
        "-ss", f"{start:.3f}",
        "-t", f"{duration:.3f}",
        "-ar", "16000", "-ac", "1",
        "-af", "loudnorm=I=-23:TP=-2:LRA=11",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)
    return Segment(
        audio_path=str(out_path.relative_to(out_dir.parent)),
        duration=duration,
        start_sec=start,
        end_sec=end,
        source_video_id=entry.video_id,
        source_url=entry.url,
        category_id=entry.category_id,
        lang_hint=entry.lang_hint,
        title=entry.title,
    )


# ────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────

def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("discover")
    pd.add_argument("--config", default="seed_queries.yaml")
    pd.add_argument("--out", default="urls.jsonl")
    pd.set_defaults(func=cmd_discover)

    pp = sub.add_parser("process")
    pp.add_argument("--urls", required=True)
    pp.add_argument("--out_dir", default="./corpus")
    pp.add_argument("--min_segment", type=float, default=3.0)
    pp.add_argument("--max_segment", type=float, default=30.0)
    pp.set_defaults(func=cmd_process)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
