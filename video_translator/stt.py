"""Speech-to-text with faster-whisper (runs fully locally)."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Segment:
    start: float
    end: float
    text: str
    translated: str = field(default="")


def transcribe(wav: Path, model_size: str = "small",
               source_language: str | None = None) -> tuple[list[Segment], str]:
    """Return timed speech segments and the detected source language code."""
    from faster_whisper import WhisperModel  # deferred: heavy import

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    raw_segments, info = model.transcribe(
        str(wav), language=source_language, vad_filter=True,
    )
    segments = [
        Segment(start=s.start, end=s.end, text=s.text.strip())
        for s in raw_segments
        if s.text.strip()
    ]
    return segments, info.language
