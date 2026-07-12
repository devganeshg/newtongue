"""Assemble synthesized clips onto a silent track at their original timestamps.

This keeps the dub in sync with the video: each translated clip starts where the
original speech segment started. Clips that run longer than their slot are sped
up (pitch-preserving) up to a cap.
"""

from pathlib import Path

from pydub import AudioSegment

from . import media
from .stt import Segment

MAX_TEMPO = 1.35  # beyond this, sped-up speech sounds unnatural

_FRAME_RATE = 24000


def assemble(segments: list[Segment], clip_paths: list[Path | None], total_duration: float,
             out_wav: Path, work_dir: Path) -> None:
    base = AudioSegment.silent(duration=int(total_duration * 1000), frame_rate=_FRAME_RATE)

    for i, (seg, clip_path) in enumerate(zip(segments, clip_paths)):
        if clip_path is None:  # synthesis failed for this segment; leave silence
            continue
        clip = AudioSegment.from_file(clip_path)
        slot_end = segments[i + 1].start if i + 1 < len(segments) else total_duration
        slot = max(slot_end - seg.start, 0.3)
        clip_len = clip.duration_seconds
        if clip_len > slot:
            tempo = min(clip_len / slot, MAX_TEMPO)
            adjusted = work_dir / f"tempo_{i:04d}.wav"
            media.change_tempo(clip_path, adjusted, tempo)
            clip = AudioSegment.from_file(adjusted)
        base = base.overlay(clip, position=int(seg.start * 1000))

    base.export(out_wav, format="wav")
