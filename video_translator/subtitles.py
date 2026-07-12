"""Write translated segments as an .srt subtitle file."""

from pathlib import Path

from .stt import Segment


def _timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(segments: list[Segment], out_path: Path) -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines += [str(i), f"{_timestamp(seg.start)} --> {_timestamp(seg.end)}", seg.translated, ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")
