"""Clip placement and the never-overlap guarantee.

`assemble` is the piece that keeps the dub in sync, and its failure mode is
subtle: a wrong slot calculation produces audio that plays fine but has two
voices talking over each other. These tests stub out `media.change_tempo`
(the only part needing ffmpeg) so the arithmetic can be checked directly.
"""

import pytest
from pydub import AudioSegment

from newtongue import timeline
from newtongue.stt import Segment

FRAME_RATE = 24000


def _tone(seconds: float) -> AudioSegment:
    """Audible (non-silent) audio, so _trim_silence doesn't eat it."""
    from pydub.generators import Sine
    return Sine(440, sample_rate=FRAME_RATE).to_audio_segment(duration=int(seconds * 1000))


@pytest.fixture
def stub_tempo(monkeypatch):
    """Replace ffmpeg tempo-shifting with exact resampling, and record the factors."""
    calls = []

    def fake_change_tempo(src, dst, tempo):
        calls.append(tempo)
        clip = AudioSegment.from_file(src)
        shortened = clip[:int(len(clip) / tempo)]
        shortened.export(dst, format="wav")

    monkeypatch.setattr(timeline.media, "change_tempo", fake_change_tempo)
    return calls


def write_clips(tmp_path, durations):
    paths = []
    for i, d in enumerate(durations):
        p = tmp_path / f"clip_{i}.wav"
        _tone(d).export(p, format="wav")
        paths.append(p)
    return paths


def test_clip_is_placed_at_its_original_timestamp(tmp_path, stub_tempo):
    segments = [Segment(start=2.0, end=3.0, text="x")]
    clips = write_clips(tmp_path, [1.0])
    out = tmp_path / "out.wav"

    warnings = timeline.assemble(segments, clips, 5.0, out, tmp_path)

    assert warnings == []
    result = AudioSegment.from_file(out)
    assert result.duration_seconds == pytest.approx(5.0, abs=0.05)
    # silence before 2.0s, audio after
    assert result[:1900].dBFS == float("-inf")
    assert result[2100:2900].dBFS > -40


def test_short_clip_is_not_sped_up(tmp_path, stub_tempo):
    segments = [Segment(start=0.0, end=3.0, text="x"), Segment(start=3.0, end=6.0, text="y")]
    clips = write_clips(tmp_path, [1.0, 1.0])

    timeline.assemble(segments, clips, 6.0, tmp_path / "out.wav", tmp_path)

    assert stub_tempo == []  # comfortably inside its slot; no adjustment


def test_long_clip_is_sped_up_to_fit_its_slot(tmp_path, stub_tempo):
    # 2.0s of speech into a slot that ends when the next segment starts at 1.5s
    segments = [Segment(start=0.0, end=1.5, text="x"), Segment(start=1.5, end=3.0, text="y")]
    clips = write_clips(tmp_path, [2.0, 0.5])

    timeline.assemble(segments, clips, 3.0, tmp_path / "out.wav", tmp_path)

    assert len(stub_tempo) == 1
    # slot = 1.5 - 0.0 - GAP(0.1) = 1.4; tempo = 2.0 / (1.4 * 0.97)
    assert stub_tempo[0] == pytest.approx(2.0 / (1.4 * 0.97))


def test_speedup_is_capped_and_warns(tmp_path, stub_tempo):
    segments = [Segment(start=0.0, end=1.0, text="x"), Segment(start=1.0, end=2.0, text="y")]
    clips = write_clips(tmp_path, [8.0, 0.2])  # absurdly long translation

    warnings = timeline.assemble(segments, clips, 2.0, tmp_path / "out.wav", tmp_path)

    assert stub_tempo[0] == timeline.HARD_MAX_TEMPO  # never exceeds the hard cap
    assert any("faded out early" in w for w in warnings)
    assert any("segment 1" in w for w in warnings)


def test_gentle_speedup_does_not_warn(tmp_path, stub_tempo):
    # needs a tempo above 1.0 but below MAX_TEMPO (1.35), so it stays silent
    segments = [Segment(start=0.0, end=5.0, text="x")]
    clips = write_clips(tmp_path, [5.2])

    warnings = timeline.assemble(segments, clips, 5.0, tmp_path / "out.wav", tmp_path)

    assert stub_tempo and stub_tempo[0] < timeline.MAX_TEMPO
    assert warnings == []


def test_last_segment_may_use_the_remaining_duration(tmp_path, stub_tempo):
    # the final clip's slot runs to total_duration, not to a following segment
    segments = [Segment(start=1.0, end=2.0, text="x")]
    clips = write_clips(tmp_path, [3.0])

    timeline.assemble(segments, clips, 10.0, tmp_path / "out.wav", tmp_path)

    assert stub_tempo == []  # 3.0s fits in the 8.9s remaining


def test_failed_synthesis_leaves_silence_without_crashing(tmp_path, stub_tempo):
    segments = [Segment(start=0.0, end=1.0, text="x"), Segment(start=1.0, end=2.0, text="y")]
    clips = write_clips(tmp_path, [0.5])
    out = tmp_path / "out.wav"

    warnings = timeline.assemble(segments, [clips[0], None], 2.0, out, tmp_path)

    assert warnings == []
    assert AudioSegment.from_file(out).duration_seconds == pytest.approx(2.0, abs=0.05)


def test_no_segments_produces_silence_of_the_full_duration(tmp_path, stub_tempo):
    out = tmp_path / "out.wav"
    warnings = timeline.assemble([], [], 4.0, out, tmp_path)
    assert warnings == []
    assert AudioSegment.from_file(out).duration_seconds == pytest.approx(4.0, abs=0.05)


def test_trim_silence_keeps_audio_and_drops_padding():
    padded = (AudioSegment.silent(duration=500, frame_rate=FRAME_RATE)
              + _tone(1.0)
              + AudioSegment.silent(duration=500, frame_rate=FRAME_RATE))
    trimmed = timeline._trim_silence(padded)
    assert trimmed.duration_seconds == pytest.approx(1.0, abs=0.1)


def test_trim_silence_returns_the_original_when_a_clip_is_all_silence():
    silent = AudioSegment.silent(duration=800, frame_rate=FRAME_RATE)
    # trimming to nothing would break placement, so the clip is returned intact
    assert len(timeline._trim_silence(silent)) == 800
