"""ffmpeg helpers: audio extraction, probing, and muxing the dubbed track back in."""

import json
import shutil
import subprocess
from pathlib import Path


class FfmpegNotFound(RuntimeError):
    pass


def ensure_ffmpeg() -> None:
    """Make ffmpeg/ffprobe available on PATH.

    If the system has no ffmpeg, download a static build once (cached) via
    static-ffmpeg. Mutating PATH here also lets pydub find the binaries.
    """
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return
    try:
        import static_ffmpeg

        static_ffmpeg.add_paths(weak=True)
    except Exception:
        pass  # which() below still fails -> FfmpegNotFound with instructions


def _ffmpeg() -> str:
    ensure_ffmpeg()
    path = shutil.which("ffmpeg")
    if not path:
        raise FfmpegNotFound(
            "ffmpeg not found and the automatic download failed (are you offline?). "
            "Install it manually, e.g.: brew install ffmpeg"
        )
    return path


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2000:]}")


def extract_audio(video: Path, wav_out: Path) -> None:
    """Extract mono 16 kHz WAV (what Whisper expects)."""
    _run([_ffmpeg(), "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav_out)])


def get_duration(media: Path) -> float:
    ensure_ffmpeg()
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise FfmpegNotFound(
            "ffprobe not found and the automatic download failed (are you offline?). "
            "Install it manually, e.g.: brew install ffmpeg"
        )
    result = subprocess.run(
        [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", str(media)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {media}:\n{result.stderr[-2000:]}")
    return float(json.loads(result.stdout)["format"]["duration"])


def mux(video: Path, dub_audio: Path, output: Path, keep_background: bool = False,
        background_volume: float = 0.4) -> None:
    """Write `output` with the original video stream (copied) and the dubbed audio.

    With keep_background the original audio stays underneath, ducked while the
    dub speaks (sidechain compression) so the two voices don't fight; music and
    ambience come back up between sentences.
    """
    cmd = [_ffmpeg(), "-y", "-i", str(video), "-i", str(dub_audio)]
    if keep_background:
        cmd += [
            "-filter_complex",
            "[1:a]asplit=2[sc][dub];"
            f"[0:a]volume={background_volume}[bgv];"
            "[bgv][sc]sidechaincompress=threshold=0.03:ratio=12:attack=20:release=400[bg];"
            "[bg][dub]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a]",
            "-map", "0:v", "-map", "[a]",
        ]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(output)]
    _run(cmd)


# Subtitle codec each container can hold as a soft (selectable) track.
_SUBTITLE_CODECS = {".mp4": "mov_text", ".m4v": "mov_text", ".mov": "mov_text",
                    ".mkv": "srt", ".webm": "webvtt"}


def embed_subtitles(video: Path, subtitle_path: Path, output: Path,
                    language: str | None = None) -> None:
    """Add subtitles as a soft (selectable, toggleable) track; nothing is re-encoded.

    Unlike burn-in this is lossless and the viewer can turn the subtitles off.
    `language` is an ISO 639-2 code shown by players as the track's language.
    """
    codec = _SUBTITLE_CODECS.get(Path(output).suffix.lower(), "mov_text")
    cmd = [_ffmpeg(), "-y", "-i", str(video), "-i", str(subtitle_path),
           "-map", "0", "-map", "1:0", "-c", "copy", "-c:s", codec]
    if language:
        cmd += ["-metadata:s:s:0", f"language={language}"]
    _run(cmd + [str(output)])


def change_tempo(audio_in: Path, audio_out: Path, tempo: float) -> None:
    """Speed up (or slow down) audio without changing pitch."""
    _run([_ffmpeg(), "-y", "-i", str(audio_in), "-filter:a", f"atempo={tempo:.4f}", str(audio_out)])


def _filter_available(ffmpeg_path: str, name: str) -> bool:
    result = subprocess.run([ffmpeg_path, "-hide_banner", "-h", f"filter={name}"],
                            capture_output=True, text=True)
    return "Unknown filter" not in result.stdout + result.stderr


def _ffmpeg_with_subtitles_filter() -> str:
    """Resolve an ffmpeg binary that has the 'subtitles' filter (needs libass).

    Many distro/Homebrew ffmpeg builds omit libass. If the one already on PATH
    lacks it, fall back to the static-ffmpeg build Newtongue can auto-download,
    which is built with libass.
    """
    ffmpeg = _ffmpeg()
    if _filter_available(ffmpeg, "subtitles"):
        return ffmpeg
    try:
        import static_ffmpeg

        fallback, _ = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
    except Exception:
        fallback = None
    if fallback and _filter_available(fallback, "subtitles"):
        return fallback
    raise RuntimeError(
        "Burning in subtitles needs an ffmpeg build with libass (the 'subtitles' filter), "
        "and none was found. Install one, e.g. `brew install ffmpeg` on macOS or "
        "`apt install ffmpeg` on most Linux distros, or turn off \"Burn subtitles\" — the "
        "separate subtitle files still work fine in any video player."
    )


def _escape_filter_value(value: str) -> str:
    """Escape a value for use inside single quotes in an ffmpeg filtergraph."""
    return value.replace("\\", "\\\\").replace("'", r"\'").replace(":", r"\:")


def burn_subtitles(video: Path, subtitle_path: Path, output: Path,
                   font: tuple[str, Path] | None = None) -> None:
    """Hard-code subtitles into the video frame (re-encodes the video stream).

    `font` is a (family, file) pair naming a font that can render the target
    script. Pointing libass at the font file's directory (fontsdir) and forcing
    the family makes rendering work even on ffmpeg builds with no system font
    fallback (static builds), which otherwise draw missing glyphs as boxes.

    ffmpeg's subtitles filter needs a path with no characters that would break
    its internal escaping; the safest fix is to run with the subtitle file's
    own directory as cwd and pass just the filename.
    """
    ffmpeg = _ffmpeg_with_subtitles_filter()
    vf = f"subtitles=filename='{_escape_filter_value(subtitle_path.name)}'"
    if font:
        family, font_file = font
        vf += (f":fontsdir='{_escape_filter_value(str(Path(font_file).parent))}'"
               f":force_style='FontName={family}'")
    # cwd is overridden below so the subtitle filter can reference the file by bare name
    # (its path may contain ffmpeg-filtergraph-special characters); video/output must
    # therefore be absolute so they don't get resolved against that overridden cwd.
    cmd = [
        ffmpeg, "-y", "-i", str(Path(video).resolve()),
        "-vf", vf,
        "-c:a", "copy", str(Path(output).resolve()),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=subtitle_path.parent)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-2000:]}")
