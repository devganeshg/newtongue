"""Text-to-speech via edge-tts (free Microsoft neural voices, needs internet).

The free Edge endpoint occasionally returns NoAudioReceived for specific
text+voice combinations (deterministically, not transiently). Each segment is
therefore retried and then re-attempted with the other voices of the same
locale before being given up on.
"""

import asyncio
from pathlib import Path

import edge_tts
from edge_tts.exceptions import NoAudioReceived

from .stt import Segment

_CONCURRENCY = 4
_RETRIES = 2


async def _try_voice(text: str, voice: str, out_path: Path) -> bool:
    for attempt in range(_RETRIES):
        try:
            await edge_tts.Communicate(text, voice).save(str(out_path))
            return True
        except NoAudioReceived:
            return False  # deterministic for this text+voice; retrying won't help
        except Exception:
            if attempt == _RETRIES - 1:
                raise
            await asyncio.sleep(1 + attempt)
    return False


async def _locale_voices(voice: str) -> list[str]:
    locale = "-".join(voice.split("-")[:2])
    voices = await edge_tts.list_voices()
    return [v["ShortName"] for v in voices
            if v["Locale"] == locale and v["ShortName"] != voice]


def synthesize_segments(segments: list[Segment], voice: str, out_dir: Path,
                        on_progress=None) -> tuple[list[Path | None], list[str]]:
    """Synthesize each translated segment to an MP3.

    Returns (paths, warnings); a path is None when synthesis failed for that
    segment even after voice fallbacks (the segment stays silent in the dub).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path | None] = [out_dir / f"seg_{i:04d}.mp3" for i in range(len(segments))]
    warnings: list[str] = []

    async def synth(sem: asyncio.Semaphore, i: int, fallbacks: list[str]) -> None:
        async with sem:
            text, path = segments[i].translated, paths[i]
            if await _try_voice(text, voice, path):
                return
            for alt in fallbacks:
                if await _try_voice(text, alt, path):
                    warnings.append(
                        f"segment {i + 1} ({segments[i].start:.1f}s): voice {voice} "
                        f"produced no audio; used {alt} instead"
                    )
                    return
            paths[i] = None
            warnings.append(
                f"segment {i + 1} ({segments[i].start:.1f}s): no voice could synthesize "
                f"this text; left silent: {text[:60]!r}"
            )

    async def run() -> None:
        try:
            fallbacks = await _locale_voices(voice)
        except Exception:
            fallbacks = []
        sem = asyncio.Semaphore(_CONCURRENCY)
        done = 0
        tasks = [asyncio.create_task(synth(sem, i, fallbacks)) for i in range(len(segments))]
        for task in asyncio.as_completed(tasks):
            await task
            done += 1
            if on_progress:
                on_progress(done, len(tasks))

    try:
        asyncio.run(run())
    except Exception as exc:
        raise RuntimeError(
            f"Speech synthesis failed (voice {voice!r}) — check your internet connection. {exc}"
        ) from exc
    return paths, warnings


def list_voices(language_prefix: str | None = None) -> list[dict]:
    """List available edge-tts voices, optionally filtered by locale prefix (e.g. 'hi')."""
    voices = asyncio.run(edge_tts.list_voices())
    if language_prefix:
        prefix = language_prefix.lower()
        voices = [v for v in voices if v["Locale"].lower().startswith(prefix)]
    return sorted(voices, key=lambda v: v["ShortName"])
