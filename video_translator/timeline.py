"""Assemble synthesized clips onto a silent track at their original timestamps.

This keeps the dub in sync with the video: each translated clip starts where the
original speech segment started. Clips never overlap the next segment: they are
sped up (pitch-preserving) up to a cap, and as a last resort faded out at the
slot boundary.
"""

from pathlib import Path

from pydub import AudioSegment
from pydub.silence import detect_leading_silence

from . import media
from .stt import Segment

MAX_TEMPO = 1.35       # preferred ceiling: speed-up is barely noticeable
HARD_MAX_TEMPO = 1.8   # last resort: rushed but intelligible, better than overlap
GAP_SECONDS = 0.1      # breathing room between consecutive clips
_SILENCE_THRESH_DBFS = -45.0

_FRAME_RATE = 24000


def _trim_silence(clip: AudioSegment) -> AudioSegment:
    """Drop the padding edge-tts bakes into clips; it inflates the measured
    length and causes speed-ups/overlaps that aren't needed."""
    lead = detect_leading_silence(clip, silence_threshold=_SILENCE_THRESH_DBFS)
    tail = detect_leading_silence(clip.reverse(), silence_threshold=_SILENCE_THRESH_DBFS)
    trimmed = clip[lead:len(clip) - tail]
    return trimmed if len(trimmed) > 0 else clip


def assemble(segments: list[Segment], clip_paths: list[Path | None], total_duration: float,
             out_wav: Path, work_dir: Path) -> list[str]:
    """Place clips at their timestamps; returns warnings about heavy adjustments."""
    warnings: list[str] = []
    base = AudioSegment.silent(duration=int(total_duration * 1000), frame_rate=_FRAME_RATE)

    for i, (seg, clip_path) in enumerate(zip(segments, clip_paths)):
        if clip_path is None:  # synthesis failed for this segment; leave silence
            continue
        clip = _trim_silence(AudioSegment.from_file(clip_path))
        slot_end = segments[i + 1].start if i + 1 < len(segments) else total_duration
        slot = max(slot_end - seg.start - GAP_SECONDS, 0.3)
        clip_len = clip.duration_seconds

        if clip_len > slot:
            # aim 3% short of the slot so ffmpeg rounding can't push us over
            tempo = min(clip_len / (slot * 0.97), HARD_MAX_TEMPO)
            trimmed = work_dir / f"trim_{i:04d}.wav"
            clip.export(trimmed, format="wav")
            adjusted = work_dir / f"tempo_{i:04d}.wav"
            media.change_tempo(trimmed, adjusted, tempo)
            clip = AudioSegment.from_file(adjusted)
            if tempo > MAX_TEMPO:
                warnings.append(
                    f"segment {i + 1} ({seg.start:.1f}s): translation is much longer than "
                    f"the original speech; sped up {tempo:.2f}x to keep segments from overlapping"
                )

        if clip.duration_seconds > slot + 0.05:  # even HARD_MAX_TEMPO wasn't enough
            clip = clip[:int(slot * 1000)].fade_out(120)
            warnings.append(
                f"segment {i + 1} ({seg.start:.1f}s): dub still too long at {HARD_MAX_TEMPO}x; "
                f"faded out early so it doesn't talk over the next segment"
            )

        base = base.overlay(clip, position=int(seg.start * 1000))

    base.export(out_wav, format="wav")
    return warnings
