"""End-to-end pipeline: video → transcript → translation → dubbed voice → new video."""

import copy
import tempfile
from dataclasses import dataclass, field
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
    subtitle_formats: tuple[str, ...] = ()   # any of "srt", "vtt", "ass", "txt"
    burn_subtitles: bool = False             # hard-code subtitles into the video frame
    speech_rate: str = "+0%"                 # edge-tts rate delta, e.g. "+15%", "-10%"
    speech_pitch: str = "+0Hz"               # edge-tts pitch delta, e.g. "+20Hz", "-15Hz"
    speech_volume: str = "+0%"               # edge-tts volume delta, e.g. "+10%"
    output: Path | None = None


@dataclass
class Result:
    target_lang: str
    video: Path
    subtitles: dict[str, Path]       # format -> path, e.g. {"srt": ..., "vtt": ...}
    source_lang: str
    segments: list[Segment]
    warnings: list[str]

    @property
    def srt(self) -> Path | None:
        return self.subtitles.get("srt")


def _write_subtitles(segments: list[Segment], output: Path, opts: Options) -> dict[str, Path]:
    formats = list(dict.fromkeys(opts.subtitle_formats))  # de-dup, keep order
    if opts.burn_subtitles and "srt" not in formats and "ass" not in formats:
        formats.append("srt")  # need a file ffmpeg can burn even if the user didn't ask for one
    if not formats:
        return {}
    return subtitles.write_subtitles(segments, output.with_suffix(""), formats)


def _dub_one(input_path: Path, segments: list[Segment], duration: float, target,
            opts: Options, output: Path, work: Path,
            report: Callable[[float, str], None]) -> tuple[list[str], dict[str, Path]]:
    """Translate/synthesize/mux a single target language; segments are mutated in place."""
    voice = opts.voice or target.default_voice

    report(0.1, f"Translating to {target.name}")
    source_google = get_language(opts.source_lang).google_code if opts.source_lang else "auto"
    translate.translate_segments(segments, source_google, target.google_code)

    report(0.2, f"Synthesizing voice ({voice})")
    clips, warnings = tts.synthesize_segments(
        segments, voice, work / "clips",
        on_progress=lambda done, total: report(
            0.2 + 0.45 * done / total, f"Synthesizing voice ({done}/{total})"
        ),
        rate=opts.speech_rate, pitch=opts.speech_pitch, volume=opts.speech_volume,
    )

    report(0.68, "Assembling dubbed audio track")
    dub_wav = work / "dub.wav"
    warnings += timeline.assemble(segments, clips, duration, dub_wav, work)

    report(0.78, "Muxing final video")
    # Mux straight to the final path unless we still need to burn subtitles in afterwards.
    mux_target = (work / f"muxed{output.suffix or '.mp4'}") if opts.burn_subtitles else output
    media.mux(input_path, dub_wav, mux_target, opts.keep_background)

    report(0.86, "Writing subtitles")
    sub_files = _write_subtitles(segments, output, opts)

    if opts.burn_subtitles:
        report(0.92, "Burning in subtitles")
        burn_src = sub_files.get("ass") or sub_files.get("srt")
        media.burn_subtitles(mux_target, burn_src, output)

    return warnings, sub_files


def translate_video(input_path: Path, opts: Options,
                    progress: ProgressFn | None = None) -> Result:
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    target = get_language(opts.target_lang)
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
        report(0.3, f"Transcribed {len(segments)} segments (source language: {detected_lang})")

        def sub_report(fraction: float, message: str) -> None:
            report(0.3 + 0.7 * fraction, message)

        warnings, sub_files = _dub_one(
            input_path, segments, duration, target, opts, output, work, sub_report
        )

    report(1.0, "Done")
    return Result(target_lang=target.code, video=output, subtitles=sub_files,
                  source_lang=detected_lang, segments=segments, warnings=warnings)


def translate_video_batch(input_path: Path, target_langs: list[str], opts: Options,
                          progress: ProgressFn | None = None) -> list[Result]:
    """Dub `input_path` into several target languages, transcribing only once.

    `opts.target_lang`/`opts.output` are ignored; per-language output paths are
    derived the same way `translate_video` derives its default.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if not target_langs:
        raise ValueError("target_langs must be non-empty")
    targets = [get_language(code) for code in target_langs]

    def report(fraction: float, message: str) -> None:
        if progress:
            progress(fraction, message)

    results: list[Result] = []
    with tempfile.TemporaryDirectory(prefix="videotranslate_") as tmp:
        work = Path(tmp)

        report(0.02, "Extracting audio")
        wav = work / "source.wav"
        media.extract_audio(input_path, wav)
        duration = media.get_duration(input_path)

        report(0.05, f"Transcribing with Whisper ({opts.model_size})")
        source_hint = get_language(opts.source_lang).whisper_code if opts.source_lang else None
        base_segments, detected_lang = transcribe(wav, opts.model_size, source_hint)
        if not base_segments:
            raise RuntimeError("No speech detected in the video.")
        report(0.15, f"Transcribed {len(base_segments)} segments (source language: {detected_lang})")

        n = len(targets)
        for i, target in enumerate(targets):
            segments = copy.deepcopy(base_segments)
            lang_work = work / target.code
            lang_work.mkdir()
            output = input_path.with_name(
                f"{input_path.stem}_{target.code}{input_path.suffix or '.mp4'}"
            )

            def lang_report(fraction: float, message: str, i=i) -> None:
                report(0.15 + 0.85 * (i + fraction) / n, f"[{target.code}] {message}")

            warnings, sub_files = _dub_one(
                input_path, segments, duration, target, opts, output, lang_work, lang_report
            )
            results.append(Result(target_lang=target.code, video=output, subtitles=sub_files,
                                  source_lang=detected_lang, segments=segments,
                                  warnings=warnings))

    report(1.0, "Done")
    return results
