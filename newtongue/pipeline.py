"""End-to-end pipeline: video → transcript → translation → dubbed voice → new video."""

import copy
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import fonts, media, subtitles, timeline, translate, tts
from .stt import Segment, transcribe
from .voices import get_language

ProgressFn = Callable[[float, str], None]


@dataclass
class Options:
    target_lang: str
    source_lang: str | None = None   # None = auto-detect
    voice: str | None = None         # None = default voice for target_lang
    model_size: str = "small"
    device: str = "auto"             # Whisper device: "auto", "cpu", or "cuda"
    keep_background: bool = False
    subtitle_formats: tuple[str, ...] = ()   # any of "srt", "vtt", "ass", "txt"
    subtitle_content: str = "translated"     # "translated", "original", or "both" (bilingual)
    burn_subtitles: bool = False             # hard-code subtitles into the video frame
    embed_subtitles: bool = False            # add subtitles as a soft (toggleable) track
    subtitles_only: bool = False             # skip dubbing; just produce subtitle files
    source_subtitles: Path | None = None     # existing SRT/VTT transcript; skips Whisper
    speech_rate: str = "+0%"                 # edge-tts rate delta, e.g. "+15%", "-10%"
    speech_pitch: str = "+0Hz"               # edge-tts pitch delta, e.g. "+20Hz", "-15Hz"
    speech_volume: str = "+0%"               # edge-tts volume delta, e.g. "+10%"
    output: Path | None = None


@dataclass
class Result:
    target_lang: str
    video: Path | None               # None in subtitles-only mode
    subtitles: dict[str, Path]       # format -> path, e.g. {"srt": ..., "vtt": ...}
    source_lang: str
    segments: list[Segment]
    warnings: list[str]

    @property
    def srt(self) -> Path | None:
        return self.subtitles.get("srt")


def _write_subtitles(segments: list[Segment], output: Path, opts: Options,
                     ass_font: str | None = None) -> dict[str, Path]:
    formats = list(dict.fromkeys(opts.subtitle_formats))  # de-dup, keep order
    if opts.subtitles_only and not formats:
        formats = ["srt"]  # subtitles are the whole output; make sure there is at least one file
    if opts.burn_subtitles and "srt" not in formats and "ass" not in formats:
        formats.append("srt")  # need a file ffmpeg can burn even if the user didn't ask for one
    if opts.embed_subtitles and "srt" not in formats:
        formats.append("srt")  # the soft track is muxed from an SRT
    if not formats:
        return {}
    return subtitles.write_subtitles(segments, output.with_suffix(""), formats,
                                     opts.subtitle_content, ass_font)


def _dub_one(input_path: Path | None, segments: list[Segment], duration: float, target,
            opts: Options, output: Path, work: Path,
            report: Callable[[float, str], None]) -> tuple[list[str], dict[str, Path], Path | None]:
    """Translate/synthesize/mux a single target language; segments are mutated in place.

    Returns (warnings, subtitle files, dubbed video path — None in subtitles-only mode).
    """
    report(0.1, f"Translating to {target.name}")
    source_google = get_language(opts.source_lang).google_code if opts.source_lang else "auto"
    translate.translate_segments(segments, source_google, target.google_code)

    # A font that can render the target script — Arial can't draw Devanagari,
    # Thai, CJK, ... and would burn in as boxes.
    font = fonts.find_font(target.code)
    ass_font = font[0] if font else None

    if opts.subtitles_only:
        report(0.85, "Writing subtitles")
        return [], _write_subtitles(segments, output, opts, ass_font), None

    voice = opts.voice or target.default_voice
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
    # Mux straight to the final path unless subtitles still get burned/embedded afterwards.
    postprocess = opts.burn_subtitles or opts.embed_subtitles
    mux_target = (work / f"muxed{output.suffix or '.mp4'}") if postprocess else output
    media.mux(input_path, dub_wav, mux_target, opts.keep_background)

    report(0.86, "Writing subtitles")
    sub_files = _write_subtitles(segments, output, opts, ass_font)

    current = mux_target
    if opts.burn_subtitles:
        report(0.92, "Burning in subtitles")
        if font is None and target.code in fonts.SCRIPTS:
            warnings.append(
                f"no installed font found that can render {fonts.SCRIPTS[target.code]} — "
                f"burned-in subtitles may show boxes instead of text; installing "
                f"'Noto Sans' for that script fixes it"
            )
        burn_src = sub_files.get("ass") or sub_files.get("srt")
        burn_target = (work / f"burned{output.suffix or '.mp4'}") if opts.embed_subtitles else output
        media.burn_subtitles(current, burn_src, burn_target, font)
        current = burn_target
    if opts.embed_subtitles:
        report(0.96, "Embedding soft subtitle track")
        media.embed_subtitles(current, sub_files["srt"], output, target.iso639_2)

    return warnings, sub_files, output


def _check_input(input_path: Path | None, opts: Options) -> Path | None:
    if input_path is not None:
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(input_path)
    elif not (opts.subtitles_only and opts.source_subtitles):
        raise ValueError("An input video is required unless translating an existing "
                         "subtitle file in subtitles-only mode.")
    if opts.source_subtitles and not Path(opts.source_subtitles).exists():
        raise FileNotFoundError(opts.source_subtitles)
    return input_path


def _output_base(input_path: Path | None, opts: Options) -> tuple[Path, str]:
    """(path whose stem names the outputs, video suffix to use)."""
    if input_path is not None:
        return input_path, input_path.suffix or ".mp4"
    return Path(opts.source_subtitles), ".mp4"


def _load_transcript(input_path: Path | None, opts: Options, work: Path,
                     report: ProgressFn, transcribe_frac: float,
                     done_frac: float) -> tuple[list[Segment], str]:
    """Timed source segments — from an existing subtitle file, or Whisper on the video."""
    if opts.source_subtitles:
        report(transcribe_frac, f"Reading transcript from {Path(opts.source_subtitles).name}")
        segments = subtitles.read_subtitles(Path(opts.source_subtitles))
        detected_lang = opts.source_lang or "auto"
    else:
        report(0.02, "Extracting audio")
        wav = work / "source.wav"
        media.extract_audio(input_path, wav)
        report(transcribe_frac, f"Transcribing with Whisper ({opts.model_size})")
        source_hint = get_language(opts.source_lang).whisper_code if opts.source_lang else None
        segments, detected_lang = transcribe(wav, opts.model_size, source_hint, opts.device)
        if not segments:
            raise RuntimeError("No speech detected in the video.")
    report(done_frac, f"Loaded {len(segments)} segments (source language: {detected_lang})")
    return segments, detected_lang


def translate_video(input_path: Path | None, opts: Options,
                    progress: ProgressFn | None = None) -> Result:
    input_path = _check_input(input_path, opts)

    target = get_language(opts.target_lang)
    base, suffix = _output_base(input_path, opts)
    output = Path(opts.output) if opts.output else base.with_name(
        f"{base.stem}_{target.code}{suffix}"
    )

    def report(fraction: float, message: str) -> None:
        if progress:
            progress(fraction, message)

    with tempfile.TemporaryDirectory(prefix="newtongue_") as tmp:
        work = Path(tmp)

        segments, detected_lang = _load_transcript(input_path, opts, work, report, 0.08, 0.3)
        duration = media.get_duration(input_path) if not opts.subtitles_only else 0.0

        def sub_report(fraction: float, message: str) -> None:
            report(0.3 + 0.7 * fraction, message)

        warnings, sub_files, video = _dub_one(
            input_path, segments, duration, target, opts, output, work, sub_report
        )

    report(1.0, "Done")
    return Result(target_lang=target.code, video=video, subtitles=sub_files,
                  source_lang=detected_lang, segments=segments, warnings=warnings)


def translate_video_batch(input_path: Path | None, target_langs: list[str], opts: Options,
                          progress: ProgressFn | None = None) -> list[Result]:
    """Dub `input_path` into several target languages, transcribing only once.

    `opts.target_lang`/`opts.output` are ignored; per-language output paths are
    derived the same way `translate_video` derives its default.
    """
    input_path = _check_input(input_path, opts)
    if not target_langs:
        raise ValueError("target_langs must be non-empty")
    targets = [get_language(code) for code in target_langs]
    base, suffix = _output_base(input_path, opts)

    def report(fraction: float, message: str) -> None:
        if progress:
            progress(fraction, message)

    results: list[Result] = []
    with tempfile.TemporaryDirectory(prefix="newtongue_") as tmp:
        work = Path(tmp)

        base_segments, detected_lang = _load_transcript(input_path, opts, work, report, 0.05, 0.15)
        duration = media.get_duration(input_path) if not opts.subtitles_only else 0.0

        n = len(targets)
        for i, target in enumerate(targets):
            segments = copy.deepcopy(base_segments)
            lang_work = work / target.code
            lang_work.mkdir()
            output = base.with_name(f"{base.stem}_{target.code}{suffix}")

            def lang_report(fraction: float, message: str, i=i) -> None:
                report(0.15 + 0.85 * (i + fraction) / n, f"[{target.code}] {message}")

            warnings, sub_files, video = _dub_one(
                input_path, segments, duration, target, opts, output, lang_work, lang_report
            )
            results.append(Result(target_lang=target.code, video=video, subtitles=sub_files,
                                  source_lang=detected_lang, segments=segments,
                                  warnings=warnings))

    report(1.0, "Done")
    return results
