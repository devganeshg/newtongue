"""Command-line interface: newtongue input.mp4 --to hi"""

import argparse
import sys
import warnings
from pathlib import Path

# pydub 0.25 trips SyntaxWarning on import under Python 3.12
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")

from . import __version__
from .subtitles import CONTENT_CHOICES as SUBTITLE_CONTENT_CHOICES
from .subtitles import FORMATS as SUBTITLE_FORMATS
from .voices import LANGUAGES


def main(argv: list[str] | None = None) -> int:
    lang_help = ", ".join(f"{code} ({lang.name})" for code, lang in sorted(LANGUAGES.items()))
    parser = argparse.ArgumentParser(
        prog="newtongue",
        description="Newtongue: dub a video's voice into another language.",
        epilog=f"Languages: {lang_help}",
    )
    parser.add_argument("--version", action="version", version=f"newtongue {__version__}")
    parser.add_argument("input", nargs="?", help="input video file")
    parser.add_argument("--to", dest="target",
                        help="target language code(s), comma-separated for a batch "
                             "(e.g. hi or hi,es,ja)")
    parser.add_argument("--from", dest="source", default=None,
                        help="source language code (default: auto-detect)")
    parser.add_argument("--voice", default=None,
                        help="edge-tts voice name (default: per-language voice)")
    parser.add_argument("--model", default="small",
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size (default: small)")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"],
                        help="where Whisper runs: auto = use an NVIDIA GPU when available "
                             "(default: auto)")
    parser.add_argument("--from-subs", metavar="FILE", default=None,
                        help="use an existing SRT/VTT file as the transcript instead of "
                             "running Whisper (edit your subtitles, then dub from them)")
    parser.add_argument("--no-dub", action="store_true",
                        help="skip dubbing; only produce translated subtitle files")
    parser.add_argument("--keep-bg", action="store_true",
                        help="keep original audio quietly in the background (music/ambience)")
    parser.add_argument("--subtitles", metavar="FORMATS", default=None,
                        help=f"comma-separated subtitle formats to write: "
                             f"{', '.join(SUBTITLE_FORMATS)} (e.g. srt,vtt)")
    parser.add_argument("--srt", action="store_true",
                        help="shorthand for --subtitles srt")
    parser.add_argument("--subtitle-content", default="translated",
                        choices=list(SUBTITLE_CONTENT_CHOICES),
                        help="what subtitle cues show: the translation, the original text, "
                             "or both (bilingual, translation on top; default: translated)")
    parser.add_argument("--burn-subtitles", action="store_true",
                        help="hard-code the subtitles into the video frame (re-encodes video)")
    parser.add_argument("--embed-subtitles", action="store_true",
                        help="add the subtitles as a soft (toggleable) track in the output "
                             "video — lossless, unlike --burn-subtitles")
    parser.add_argument("--rate", default="+0%", metavar="DELTA",
                        help="speech speed delta, e.g. +15%%, -10%% (default: +0%%)")
    parser.add_argument("--pitch", default="+0Hz", metavar="DELTA",
                        help="speech pitch delta, e.g. +20Hz, -15Hz (default: +0Hz)")
    parser.add_argument("--volume", default="+0%", metavar="DELTA",
                        help="speech volume delta, e.g. +10%%, -20%% (default: +0%%)")
    parser.add_argument("-o", "--output", default=None,
                        help="output video path (single target language only)")
    parser.add_argument("--list-voices", metavar="LANG", default=None,
                        help="list available voices for a language prefix (e.g. hi, zh-TW) and exit")
    args = parser.parse_args(argv)

    if args.list_voices:
        from .tts import list_voices
        for v in list_voices(args.list_voices):
            print(f"{v['ShortName']:32s} {v['Gender']:8s} {v['Locale']}")
        return 0

    if not args.target:
        parser.error("--to LANG is required (or use --list-voices)")
    if not args.input and not (args.no_dub and args.from_subs):
        parser.error("input video is required (translating just a subtitle file works "
                     "with --no-dub --from-subs FILE)")
    if args.no_dub and (args.burn_subtitles or args.embed_subtitles):
        parser.error("--burn-subtitles/--embed-subtitles produce a video and can't be "
                     "combined with --no-dub")

    targets = [t.strip() for t in args.target.split(",") if t.strip()]
    if len(targets) > 1 and args.output:
        parser.error("-o/--output can't be used with multiple --to languages")

    formats = [f.strip() for f in args.subtitles.split(",") if f.strip()] if args.subtitles else []
    if args.srt and "srt" not in formats:
        formats.append("srt")

    from .pipeline import Options, translate_video, translate_video_batch

    def progress(fraction: float, message: str) -> None:
        print(f"[{fraction * 100:3.0f}%] {message}", flush=True)

    opts = Options(
        target_lang=targets[0],
        source_lang=args.source,
        voice=args.voice,
        model_size=args.model,
        device=args.device,
        keep_background=args.keep_bg,
        subtitle_formats=tuple(formats),
        subtitle_content=args.subtitle_content,
        burn_subtitles=args.burn_subtitles,
        embed_subtitles=args.embed_subtitles,
        subtitles_only=args.no_dub,
        source_subtitles=Path(args.from_subs) if args.from_subs else None,
        speech_rate=args.rate,
        speech_pitch=args.pitch,
        speech_volume=args.volume,
        output=Path(args.output) if args.output else None,
    )

    input_path = Path(args.input) if args.input else None
    try:
        if len(targets) > 1:
            results = translate_video_batch(input_path, targets, opts, progress=progress)
        else:
            results = [translate_video(input_path, opts, progress=progress)]
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for result in results:
        for warning in result.warnings:
            print(f"warning [{result.target_lang}]: {warning}", file=sys.stderr)
        if result.video:
            print(f"\nDubbed video ({result.target_lang}): {result.video}")
        else:
            print(f"\nSubtitles-only run ({result.target_lang}):")
        for fmt, path in result.subtitles.items():
            print(f"Subtitles ({fmt}):        {path}")
        print(f"Source language detected: {result.source_lang}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
