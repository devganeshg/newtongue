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
        background_volume: float = 0.15) -> None:
    """Write `output` with the original video stream (copied) and the dubbed audio.

    With keep_background the original audio stays underneath at reduced volume,
    preserving music/ambience.
    """
    cmd = [_ffmpeg(), "-y", "-i", str(video), "-i", str(dub_audio)]
    if keep_background:
        cmd += [
            "-filter_complex",
            f"[0:a]volume={background_volume}[bg];"
            "[bg][1:a]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[a]",
            "-map", "0:v", "-map", "[a]",
        ]
    else:
        cmd += ["-map", "0:v", "-map", "1:a"]
    cmd += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(output)]
    _run(cmd)


def change_tempo(audio_in: Path, audio_out: Path, tempo: float) -> None:
    """Speed up (or slow down) audio without changing pitch."""
    _run([_ffmpeg(), "-y", "-i", str(audio_in), "-filter:a", f"atempo={tempo:.4f}", str(audio_out)])
