"""Speech-to-text with faster-whisper (runs fully locally)."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Segment:
    start: float
    end: float
    text: str
    translated: str = field(default="")


def _load_model(model_size: str, device: str):
    from faster_whisper import WhisperModel  # deferred: heavy import

    if device == "auto":
        try:
            return WhisperModel(model_size, device="cuda", compute_type="float16")
        except Exception:  # no CUDA device / CPU-only ctranslate2 build
            return WhisperModel(model_size, device="cpu", compute_type="int8")
    compute_type = "float16" if device == "cuda" else "int8"
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def transcribe(wav: Path, model_size: str = "small",
               source_language: str | None = None,
               device: str = "auto") -> tuple[list[Segment], str]:
    """Return timed speech segments and the detected source language code.

    `device`: "auto" uses an NVIDIA GPU when available and falls back to CPU;
    "cpu"/"cuda" force one.
    """
    model = _load_model(model_size, device)
    raw_segments, info = model.transcribe(
        str(wav), language=source_language, vad_filter=True,
    )
    segments = [
        Segment(start=s.start, end=s.end, text=s.text.strip())
        for s in raw_segments
        if s.text.strip()
    ]
    return segments, info.language
