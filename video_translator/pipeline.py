"""End-to-end pipeline: video → transcript → translation → dubbed voice → new video."""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import media, subtitles, timeline, translate, tts
from .stt import Segment, transcribe
from .voices import get_language

ProgressFn = Callable[[float, str], None]


@dataclass
class Options:
    target_lang: str
    source_lang: str | None = None   # None = auto-detect
    voice: str | None = None         # None = default voice for target_lang
    model_size: str = "small"
    keep_background: bool = False
    write_srt: bool = False
    output: Path | None = None


@dataclass
class Result:
    video: Path
    srt: Path | None
    source_lang: str
    segments: list[Segment]
    warnings: list[str]


def translate_video(input_path: Path, opts: Options,
                    progress: ProgressFn | None = None) -> Result:
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    target = get_language(opts.target_lang)
    voice = opts.voice or target.default_voice
    output = Path(opts.output) if opts.output else input_path.with_name(
        f"{input_path.stem}_{target.code}{input_path.suffix or '.mp4'}"
    )

    def report(fraction: float, message: str) -> None:
        if progress:
            progress(fraction, message)

    with tempfile.TemporaryDirectory(prefix="videotranslate_") as tmp:
        work = Path(tmp)

        report(0.02, "Extracting audio")
        wav = work / "source.wav"
        media.extract_audio(input_path, wav)
        duration = media.get_duration(input_path)

        report(0.08, f"Transcribing with Whisper ({opts.model_size})")
        source_hint = get_language(opts.source_lang).whisper_code if opts.source_lang else None
        segments, detected_lang = transcribe(wav, opts.model_size, source_hint)
        if not segments:
            raise RuntimeError("No speech detected in the video.")
        report(0.5, f"Transcribed {len(segments)} segments (source language: {detected_lang})")

        report(0.52, f"Translating to {target.name}")
        source_google = (
            get_language(opts.source_lang).google_code if opts.source_lang else "auto"
        )
        translate.translate_segments(segments, source_google, target.google_code)

        report(0.6, f"Synthesizing voice ({voice})")
        clips, warnings = tts.synthesize_segments(
            segments, voice, work / "clips",
            on_progress=lambda done, total: report(
                0.6 + 0.25 * done / total, f"Synthesizing voice ({done}/{total})"
            ),
        )

        report(0.87, "Assembling dubbed audio track")
        dub_wav = work / "dub.wav"
        timeline.assemble(segments, clips, duration, dub_wav, work)

        report(0.93, "Muxing final video")
        media.mux(input_path, dub_wav, output, opts.keep_background)

        srt_path = None
        if opts.write_srt:
            srt_path = output.with_suffix(".srt")
            subtitles.write_srt(segments, srt_path)

    report(1.0, "Done")
    return Result(video=output, srt=srt_path, source_lang=detected_lang,
                  segments=segments, warnings=warnings)
