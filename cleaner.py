"""Audio cleaning pipeline: any audio/video file in -> AI-denoised, polished MP3 out.

Noise removal uses DeepFilterNet3, a pretrained speech-enhancement model that runs locally.
"""

import io
import subprocess
import tempfile
import threading
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import torch
from df.enhance import enhance, init_df
from pedalboard import (
    Compressor,
    HighpassFilter,
    Limiter,
    LowShelfFilter,
    Pedalboard,
    PeakFilter,
)
from pedalboard.io import AudioFile

# Maximum noise reduction in dB per strength setting. None = no limit (remove everything).
# Limiting it keeps a little natural room tone and avoids an over-processed sound.
STRENGTH = {"light": 12, "medium": 24, "strong": None}

TARGET_PEAK = 0.89  # about -1 dBFS
SAMPLE_RATE = 48000  # DeepFilterNet works at 48 kHz

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".oga", ".opus", ".wma", ".aif", ".aiff", ".caf", ".amr"}
VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".3gp"}
SUPPORTED_EXTS = AUDIO_EXTS | VIDEO_EXTS

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
MODEL_DIR = Path(__file__).parent / "models" / "DeepFilterNet3"

# Load the model once and share it. The lock keeps simultaneous requests from
# running the model at the same time, which it isn't designed for.
_model, _df_state, _ = init_df(model_base_dir=str(MODEL_DIR), log_level="WARNING")
_model_lock = threading.Lock()


class DecodeError(Exception):
    pass


def decode(data: bytes, ext: str) -> np.ndarray:
    """Decode any audio or video file to mono float32 samples at SAMPLE_RATE.

    Uses a bundled FFmpeg. Video tracks are ignored; only the audio is kept.
    The upload is written to a temp file because formats like MP4 need seeking.
    """
    with tempfile.NamedTemporaryFile(suffix=ext) as tmp:
        tmp.write(data)
        tmp.flush()
        proc = subprocess.run(
            [FFMPEG, "-nostdin", "-v", "error", "-i", tmp.name,
             "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"],
            capture_output=True,
            timeout=600,
        )
    samples = np.frombuffer(proc.stdout, dtype=np.float32)
    if proc.returncode != 0 or samples.size == 0:
        raise DecodeError(proc.stderr.decode(errors="ignore").strip() or "No audio track found.")
    return samples[None, :].copy()


def denoise(audio: np.ndarray, atten_lim_db) -> np.ndarray:
    """Run DeepFilterNet on mono audio, shape (1, frames)."""
    with _model_lock, torch.no_grad():
        out = enhance(_model, _df_state, torch.from_numpy(audio), atten_lim_db=atten_lim_db)
    return out.numpy().astype(np.float32)


def clean_audio(data: bytes, strength: str = "medium", ext: str = ".mp3") -> bytes:
    atten_lim_db = STRENGTH.get(strength, STRENGTH["medium"])
    sr = SAMPLE_RATE

    # 1. Decode any format to mono float samples, shape (1, frames).
    #    Voiceovers are speech, so mono gives cleaner, more consistent results.
    audio = decode(data, ext.lower())

    # 2. Cut low rumble the model doesn't need to deal with.
    audio = Pedalboard([HighpassFilter(cutoff_frequency_hz=80)])(audio, sr)

    # 3. AI noise removal.
    audio = denoise(audio, atten_lim_db)

    # 4. Voice polish: tame mud, add a touch of presence, even out levels.
    polish = Pedalboard(
        [
            LowShelfFilter(cutoff_frequency_hz=200, gain_db=-2.0),
            PeakFilter(cutoff_frequency_hz=3500, gain_db=2.5, q=0.8),
            Compressor(threshold_db=-20, ratio=3, attack_ms=5, release_ms=120),
            Limiter(threshold_db=-1.0),
        ]
    )
    audio = polish(audio, sr)

    # 5. Normalize peak level.
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = (audio * (TARGET_PEAK / peak)).astype(np.float32)

    # 6. Encode back to MP3.
    out = io.BytesIO()
    with AudioFile(out, "w", sr, 1, format="mp3", quality="192k") as f:
        f.write(audio)
    return out.getvalue()
