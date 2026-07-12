"""Command-line interface: voxdub input.mp4 --to hi"""

import argparse
import sys
import warnings
from pathlib import Path

# pydub 0.25 trips SyntaxWarning on import under Python 3.12
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")

from .voices import LANGUAGES


def main(argv: list[str] | None = None) -> int:
    lang_help = ", ".join(f"{code} ({lang.name})" for code, lang in sorted(LANGUAGES.items()))
    parser = argparse.ArgumentParser(
        prog="voxdub",
        description="VoxDub: dub a video's voice into another language.",
        epilog=f"Languages: {lang_help}",
    )
    parser.add_argument("input", nargs="?", help="input video file")
    parser.add_argument("--to", dest="target", help="target language code (e.g. hi, es, th)")
    parser.add_argument("--from", dest="source", default=None,
                        help="source language code (default: auto-detect)")
    parser.add_argument("--voice", default=None,
                        help="edge-tts voice name (default: per-language voice)")
    parser.add_argument("--model", default="small",
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper model size (default: small)")
    parser.add_argument("--keep-bg", action="store_true",
                        help="keep original audio quietly in the background (music/ambience)")
    parser.add_argument("--srt", action="store_true", help="also write translated subtitles")
    parser.add_argument("-o", "--output", default=None, help="output video path")
    parser.add_argument("--list-voices", metavar="LANG", default=None,
                        help="list available voices for a language prefix (e.g. hi, zh-TW) and exit")
    args = parser.parse_args(argv)

    if args.list_voices:
        from .tts import list_voices
        for v in list_voices(args.list_voices):
            print(f"{v['ShortName']:32s} {v['Gender']:8s} {v['Locale']}")
        return 0

    if not args.input or not args.target:
        parser.error("input video and --to LANG are required (or use --list-voices)")

    from .pipeline import Options, translate_video

    def progress(fraction: float, message: str) -> None:
        print(f"[{fraction * 100:3.0f}%] {message}", flush=True)

    try:
        result = translate_video(
            Path(args.input),
            Options(
                target_lang=args.target,
                source_lang=args.source,
                voice=args.voice,
                model_size=args.model,
                keep_background=args.keep_bg,
                write_srt=args.srt,
                output=Path(args.output) if args.output else None,
            ),
            progress=progress,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"\nDubbed video: {result.video}")
    if result.srt:
        print(f"Subtitles:    {result.srt}")
    print(f"Source language detected: {result.source_lang}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
