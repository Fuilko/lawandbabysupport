"""
Audio Augmentation Hook（Phase 2 用、デフォルト無効）
========================================================

訓練時に被害者音声へ環境変動を動的に重畳：
- **ノイズ重畳** (MUSAN noise/music/babble)
- **残響シミュレーション** (RIR convolution; OpenSLR RIRs)
- **帯域制限** (電話帯域 300-3400 Hz エミュレーション)
- **音量変動** (-12dB 〜 +6dB)
- **ピッチ・速度変動** (±10%)
- **コーデック劣化** (mp3 / opus 低ビットレート再エンコード)

## なぜ Phase 1 で OFF にするか
- Whisper large-v3 base モデルは既に 680K 時間で多環境訓練済
- LoRA fine-tune は「被害者発話スタイル」学習が主目的
- 過度な augmentation は drug 信号を希釈
- baseline 評価で **特定環境カテゴリの WER が特に悪い場合のみ** 該当 augmentation を ON

## 使い方（Phase 2 の時）

```python
from audio_augmentation import build_augmentation_pipeline

aug = build_augmentation_pipeline(
    enable_noise=True,
    enable_rir=True,
    enable_phone_band=False,   # eval set に電話帯域多ければ有効化
    musan_dir="/data/MUSAN",
    rir_dir="/data/RIRS_NOISES",
    p_apply=0.5,               # 半分の epoch で augment
)

audio_aug = aug(audio_array, sample_rate=16000)
```

## 必要 corpus（追加で DL）

| Corpus | サイズ | License | URL |
|---|---|---|---|
| MUSAN | 11 GB | CC-BY-4.0 | https://www.openslr.org/17/ |
| OpenSLR RIRS_NOISES | 14 GB | Apache 2.0 | https://www.openslr.org/28/ |
| DEMAND | 4.5 GB | CC0 | https://zenodo.org/record/1227121 |
| AudioSet (Crying/Wail) | 既に corpus 内 | Apache 2.0 | – |
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Callable

import numpy as np

log = logging.getLogger("audio_aug")


def build_augmentation_pipeline(
    enable_noise: bool = False,
    enable_rir: bool = False,
    enable_phone_band: bool = False,
    enable_volume: bool = True,
    enable_pitch: bool = False,
    enable_codec: bool = False,
    musan_dir: str | None = None,
    rir_dir: str | None = None,
    snr_db_range: tuple[float, float] = (5.0, 20.0),
    p_apply: float = 0.5,
    seed: int = 42,
) -> Callable[[np.ndarray, int], np.ndarray]:
    """
    各 augmentation を組み合わせた callable を返す。
    全部 OFF（デフォルト）なら identity 関数になる。
    """
    rng = random.Random(seed)
    musan_files: list[Path] = []
    rir_files: list[Path] = []

    if enable_noise:
        if not musan_dir:
            log.warning("enable_noise=True だが musan_dir 未設定 → 無効化")
            enable_noise = False
        else:
            musan_files = list(Path(musan_dir).rglob("*.wav"))
            log.info(f"MUSAN noise files: {len(musan_files)}")

    if enable_rir:
        if not rir_dir:
            log.warning("enable_rir=True だが rir_dir 未設定 → 無効化")
            enable_rir = False
        else:
            rir_files = list(Path(rir_dir).rglob("*.wav"))
            log.info(f"RIR files: {len(rir_files)}")

    def pipeline(audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        if rng.random() > p_apply:
            return audio  # 半分はそのまま（base distribution 保持）

        out = audio.astype(np.float32, copy=True)

        if enable_rir and rir_files:
            out = _apply_rir(out, rng.choice(rir_files), sample_rate)

        if enable_noise and musan_files:
            snr = rng.uniform(*snr_db_range)
            out = _add_noise(out, rng.choice(musan_files), sample_rate, snr_db=snr)

        if enable_phone_band:
            out = _phone_band_filter(out, sample_rate)

        if enable_volume:
            out = _random_gain(out, rng, db_range=(-12, 6))

        if enable_pitch:
            out = _pitch_shift(out, sample_rate, rng.uniform(-1, 1))

        if enable_codec:
            out = _codec_degrade(out, sample_rate, rng)

        return out

    return pipeline


# ────────────────────────────────────────────
# 個別 augmentation 実装
# ────────────────────────────────────────────

def _add_noise(audio: np.ndarray, noise_path: Path, sr: int, snr_db: float) -> np.ndarray:
    import soundfile as sf
    noise, nsr = sf.read(str(noise_path))
    if noise.ndim > 1:
        noise = noise.mean(axis=1)
    if nsr != sr:
        import librosa
        noise = librosa.resample(noise, orig_sr=nsr, target_sr=sr)
    # 長さ合わせ
    if len(noise) < len(audio):
        noise = np.tile(noise, len(audio) // len(noise) + 1)
    noise = noise[: len(audio)]

    # SNR に従ってスケール
    sig_power = np.mean(audio ** 2) + 1e-10
    noise_power = np.mean(noise ** 2) + 1e-10
    desired_noise_power = sig_power / (10 ** (snr_db / 10))
    noise = noise * np.sqrt(desired_noise_power / noise_power)
    return audio + noise


def _apply_rir(audio: np.ndarray, rir_path: Path, sr: int) -> np.ndarray:
    """Room Impulse Response 畳込で残響シミュレーション"""
    import soundfile as sf
    from scipy.signal import fftconvolve
    rir, rsr = sf.read(str(rir_path))
    if rir.ndim > 1:
        rir = rir.mean(axis=1)
    if rsr != sr:
        import librosa
        rir = librosa.resample(rir, orig_sr=rsr, target_sr=sr)
    rir = rir / (np.max(np.abs(rir)) + 1e-9)
    out = fftconvolve(audio, rir, mode="full")[: len(audio)]
    return out / (np.max(np.abs(out)) + 1e-9) * np.max(np.abs(audio))


def _phone_band_filter(audio: np.ndarray, sr: int) -> np.ndarray:
    """300-3400 Hz の電話帯域に制限（110 番通報想定）"""
    from scipy.signal import butter, sosfilt
    sos = butter(6, [300, 3400], btype="bandpass", fs=sr, output="sos")
    return sosfilt(sos, audio)


def _random_gain(audio: np.ndarray, rng: random.Random, db_range: tuple) -> np.ndarray:
    db = rng.uniform(*db_range)
    return audio * (10 ** (db / 20))


def _pitch_shift(audio: np.ndarray, sr: int, semitones: float) -> np.ndarray:
    import librosa
    return librosa.effects.pitch_shift(audio, sr=sr, n_steps=semitones)


def _codec_degrade(audio: np.ndarray, sr: int, rng: random.Random) -> np.ndarray:
    """mp3 / opus 低ビットレート → 再ロードで劣化"""
    import io
    import soundfile as sf
    bitrate = rng.choice([16, 24, 32])  # kbps
    buf = io.BytesIO()
    try:
        sf.write(buf, audio, sr, format="OGG", subtype="OPUS")
        buf.seek(0)
        out, _ = sf.read(buf)
        return out
    except Exception:  # noqa: BLE001
        return audio  # opus サポートなければスキップ
