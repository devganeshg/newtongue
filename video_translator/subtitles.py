"""Write translated segments as subtitle files: SRT, VTT, ASS, or plain TXT."""

from pathlib import Path

from .stt import Segment

FORMATS = ("srt", "vtt", "ass", "txt")


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


def write_srt(segments: list[Segment], out_path: Path) -> None:
    lines = []
    for i, seg in enumerate(segments, start=1):
        lines += [str(i), f"{_timestamp_srt(seg.start)} --> {_timestamp_srt(seg.end)}",
                  seg.translated, ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_vtt(segments: list[Segment], out_path: Path) -> None:
    lines = ["WEBVTT", ""]
    for seg in segments:
        lines += [f"{_timestamp_vtt(seg.start)} --> {_timestamp_vtt(seg.end)}",
                  seg.translated, ""]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_ass(segments: list[Segment], out_path: Path) -> None:
    header = """[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,42,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,2,10,10,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header.rstrip("\n")]
    for seg in segments:
        text = seg.translated.replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_timestamp_ass(seg.start)},{_timestamp_ass(seg.end)},"
            f"Default,,0,0,0,,{text}"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_txt(segments: list[Segment], out_path: Path) -> None:
    lines = [seg.translated for seg in segments]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


_WRITERS = {"srt": write_srt, "vtt": write_vtt, "ass": write_ass, "txt": write_txt}


def write_subtitles(segments: list[Segment], base_path: Path,
                    formats: list[str]) -> dict[str, Path]:
    """Write one file per requested format (e.g. ["srt", "vtt"]) next to base_path.

    Returns {format: path}.
    """
    out: dict[str, Path] = {}
    for fmt in formats:
        writer = _WRITERS.get(fmt)
        if writer is None:
            raise ValueError(f"Unsupported subtitle format {fmt!r}. Supported: {', '.join(FORMATS)}")
        path = base_path.with_suffix(f".{fmt}")
        writer(segments, path)
        out[fmt] = path
    return out
