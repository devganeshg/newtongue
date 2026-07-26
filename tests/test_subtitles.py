"""Subtitle timestamp formatting, parsing, and cue-content selection.

These are the pure functions where an off-by-one silently produces a file that
still *looks* valid, so they're worth pinning down exactly.
"""

import pytest

from newtongue.stt import Segment
from newtongue.subtitles import (
    _cue_text,
    _parse_timestamp,
    _timestamp_ass,
    _timestamp_srt,
    _timestamp_vtt,
    read_subtitles,
    write_subtitles,
)


@pytest.mark.parametrize("seconds,expected", [
    (0, "00:00:00,000"),
    (0.001, "00:00:00,001"),
    (1.5, "00:00:01,500"),
    (59.999, "00:00:59,999"),
    (60, "00:01:00,000"),
    (3600, "01:00:00,000"),
    (3661.25, "01:01:01,250"),
    (36000.5, "10:00:00,500"),
])
def test_timestamp_srt(seconds, expected):
    assert _timestamp_srt(seconds) == expected


def test_timestamp_srt_rounds_rather_than_truncates():
    # 0.9999s is 1000ms to the nearest ms, and must not overflow into "1,000"
    assert _timestamp_srt(0.9999) == "00:00:01,000"


def test_timestamp_vtt_uses_dot_separator():
    assert _timestamp_vtt(3661.25) == "01:01:01.250"


@pytest.mark.parametrize("seconds,expected", [
    (0, "0:00:00.00"),
    (1.5, "0:00:01.50"),
    (3661.25, "1:01:01.25"),
])
def test_timestamp_ass(seconds, expected):
    # ASS uses centiseconds and a single-digit hour, unlike SRT/VTT
    assert _timestamp_ass(seconds) == expected


@pytest.mark.parametrize("raw,expected", [
    ("00:00:01,500", 1.5),
    ("00:00:01.500", 1.5),
    ("01:01:01,250", 3661.25),
    ("00:01,5", 1.5),          # no hour component (VTT short form)
    ("00:00:01,5", 1.5),       # 1-digit fraction means tenths, not milliseconds
    ("00:00:01,05", 1.05),     # 2-digit fraction means hundredths
])
def test_parse_timestamp(raw, expected):
    assert _parse_timestamp(raw) == pytest.approx(expected)


def test_parse_timestamp_rejects_garbage():
    with pytest.raises(ValueError):
        _parse_timestamp("not a timestamp")


def test_roundtrip_srt_preserves_timings(tmp_path):
    segments = [Segment(start=0.0, end=1.5, text="hello"),
                Segment(start=2.25, end=4.0, text="world")]
    for seg in segments:
        seg.translated = seg.text
    out = write_subtitles(segments, tmp_path / "clip", ["srt"])
    parsed = read_subtitles(out["srt"])
    assert [(s.start, s.end, s.text) for s in parsed] == [
        (0.0, 1.5, "hello"), (2.25, 4.0, "world")]


def test_read_subtitles_handles_vtt_crlf_bom_and_tags(tmp_path):
    path = tmp_path / "in.vtt"
    path.write_bytes(
        b"\xef\xbb\xbfWEBVTT\r\n\r\n"
        b"00:00:00.000 --> 00:00:01.000\r\n<v Speaker>tagged</v>\r\n\r\n"
        b"00:00:02.000 --> 00:00:03.000\r\nsecond\r\n"
    )
    segments = read_subtitles(path)
    assert [s.text for s in segments] == ["tagged", "second"]


def test_read_subtitles_sorts_out_of_order_cues(tmp_path):
    path = tmp_path / "in.srt"
    path.write_text("1\n00:00:05,000 --> 00:00:06,000\nlate\n\n"
                    "2\n00:00:01,000 --> 00:00:02,000\nearly\n", encoding="utf-8")
    assert [s.text for s in read_subtitles(path)] == ["early", "late"]


def test_read_subtitles_rejects_a_file_with_no_cues(tmp_path):
    path = tmp_path / "empty.srt"
    path.write_text("this is just prose\n", encoding="utf-8")
    with pytest.raises(ValueError, match="No subtitle cues"):
        read_subtitles(path)


def test_cue_text_content_modes():
    seg = Segment(start=0, end=1, text="original")
    seg.translated = "translated"
    assert _cue_text(seg, "translated") == "translated"
    assert _cue_text(seg, "original") == "original"
    assert _cue_text(seg, "both") == "translated\noriginal"


def test_cue_text_both_collapses_when_translation_is_identical():
    # Dubbing en -> en leaves text == translated; showing it twice is noise.
    seg = Segment(start=0, end=1, text="same")
    seg.translated = "same"
    assert _cue_text(seg, "both") == "same"


def test_write_subtitles_rejects_unknown_format_and_content(tmp_path):
    segments = [Segment(start=0, end=1, text="x")]
    with pytest.raises(ValueError, match="Unsupported subtitle format"):
        write_subtitles(segments, tmp_path / "a", ["mp4"])
    with pytest.raises(ValueError, match="Unsupported subtitle content"):
        write_subtitles(segments, tmp_path / "a", ["srt"], content="bilingual")


def test_write_ass_escapes_newlines_and_uses_requested_font(tmp_path):
    seg = Segment(start=0, end=1, text="orig")
    seg.translated = "line1"
    out = write_subtitles([seg], tmp_path / "a", ["ass"],
                          content="both", ass_font="Noto Sans Devanagari")
    body = out["ass"].read_text(encoding="utf-8")
    assert "Noto Sans Devanagari" in body
    assert "line1\\Norig" in body      # ASS needs \N, never a raw newline
    assert "line1\norig" not in body
