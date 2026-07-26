"""Read and write subtitle files: SRT, VTT, ASS, or plain TXT.

Reading (SRT/VTT only) turns an existing subtitle file into timed segments so a
video can be dubbed from a hand-edited transcript instead of a fresh Whisper run.
"""

import re
from pathlib import Path

from .stt import Segment

FORMATS = ("srt", "vtt", "ass", "txt")
CONTENT_CHOICES = ("translated", "original", "both")

_TIMESTAMP_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{1,2})[.,](\d{1,3})")


def _cue_text(seg: Segment, content: str) -> str:
    if content == "original":
        return seg.text
    if content == "both":
        if seg.translated and seg.text and seg.translated != seg.text:
            return f"{seg.translated}\n{seg.text}"
        return seg.translated or seg.text
    return seg.translated


def _parse_timestamp(raw: str) -> float:
    m = _TIMESTAMP_RE.search(raw)
    if not m:
        raise ValueError(f"Unrecognized subtitle timestamp: {raw.strip()!r}")
    h, mnt, sec, frac = m.groups()
    return int(h or 0) * 3600 + int(mnt) * 60 + int(sec) + int(frac.ljust(3, "0")) / 1000


def read_subtitles(path: Path) -> list[Segment]:
    """Parse an SRT or VTT file into segments (cue text goes into Segment.text)."""
    raw = Path(path).read_text(encoding="utf-8-sig")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    segments: list[Segment] = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        for i, line in enumerate(lines):
            if "-->" not in line:
                continue
            start_raw, end_raw = line.split("-->", 1)
            text = " ".join(lines[i + 1:])
            text = re.sub(r"<[^>]+>", "", text).strip()  # strip VTT/HTML markup tags
            if text:
                segments.append(Segment(start=_parse_timestamp(start_raw),
                                        end=_parse_timestamp(end_raw), text=text))
            break
    if not segments:
        raise ValueError(
            f"No subtitle cues found in {path} — is it a valid SRT or VTT file?"
        )
    segments.sort(key=lambda s: s.start)
    return segments


def _timestamp_srt(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _timestamp_vtt(seconds: float) -> str:
    return _timestamp_srt(seconds).replace(",", ".")


def _timestamp_ass(seconds: float) -> str:
    cs = int(round(seconds * 100))  # centiseconds
    h, rem = divmod(cs, 360_000)
    m, rem = divmod(rem, 6_000)
    s, cs = divmod(rem, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def write_srt(segments: list[Segment], out_path: Path, content: str = "translated") -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines += [str(i), f"{_timestamp_srt(seg.start)} --> {_timestamp_srt(seg.end)}",
                  _cue_text(seg, content), ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_vtt(segments: list[Segment], out_path: Path, content: str = "translated") -> None:
    lines = ["WEBVTT", ""]
    for seg in segments:
        lines += [f"{_timestamp_vtt(seg.start)} --> {_timestamp_vtt(seg.end)}",
                  _cue_text(seg, content), ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_ass(segments: list[Segment], out_path: Path, content: str = "translated",
              font: str = "Arial") -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},42,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header.rstrip("\n")]
    for seg in segments:
        text = _cue_text(seg, content).replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_timestamp_ass(seg.start)},{_timestamp_ass(seg.end)},"
            f"Default,,0,0,0,,{text}"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_txt(segments: list[Segment], out_path: Path, content: str = "translated") -> None:
    lines = [_cue_text(seg, content).replace("\n", " — ") for seg in segments]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


_WRITERS = {"srt": write_srt, "vtt": write_vtt, "ass": write_ass, "txt": write_txt}


def write_subtitles(segments: list[Segment], base_path: Path, formats: list[str],
                    content: str = "translated", ass_font: str | None = None) -> dict[str, Path]:
    """Write one file per requested format (e.g. ["srt", "vtt"]) next to base_path.

    `content` picks what each cue shows: the translation, the original text, or
    both (translation on top — a bilingual subtitle). `ass_font` names the font
    family ASS files use (one that can render the target script).
    Returns {format: path}.
    """
    if content not in CONTENT_CHOICES:
        raise ValueError(
            f"Unsupported subtitle content {content!r}. Supported: {', '.join(CONTENT_CHOICES)}")
    out: dict[str, Path] = {}
    for fmt in formats:
        writer = _WRITERS.get(fmt)
        if writer is None:
            raise ValueError(f"Unsupported subtitle format {fmt!r}. Supported: {', '.join(FORMATS)}")
        path = base_path.with_suffix(f".{fmt}")
        if fmt == "ass" and ass_font:
            write_ass(segments, path, content, ass_font)
        else:
            writer(segments, path, content)
        out[fmt] = path
    return out
