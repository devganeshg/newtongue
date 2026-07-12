<p align="center">
  <img src="assets/logo.svg" width="96" alt="VoxDub logo">
</p>

<h1 align="center">VoxDub</h1>

<p align="center"><b>Dub any video into another language</b> — natural neural voices, no API keys.<br>
Windows · macOS · Linux</p>

Give VoxDub a video and a target language; it returns the same video with the speech
replaced by a natural-sounding translated voice — plus optional subtitles.

## ✨ Features

- **🎬 One-click dubbing** — upload a video, pick a language, press *Dub it*. VoxDub
  transcribes the speech, translates it, synthesizes a new voice, and rebuilds the video.
- **🗣️ 15 languages, hundreds of voices** — English, Hindi, Spanish, French, German,
  Italian, Portuguese, Japanese, Korean, Chinese (Simplified & Taiwan), Thai, Vietnamese,
  Gulf Arabic, and Russian, each with a curated default Microsoft neural voice. Any
  edge-tts voice can be substituted (`voxdub --list-voices hi`).
- **🔍 Automatic source-language detection** — no need to say what language the video is
  in; Whisper figures it out (or force it with `--from`).
- **🧠 Local, private transcription** — speech-to-text runs entirely on your machine with
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CPU, int8). Your video is
  never uploaded anywhere; only the transcribed *text* goes to the translation service.
- **🆓 No API keys, no accounts** — translation (Google Translate) and voices
  (Microsoft Edge neural TTS) use free public endpoints.
- **⏱️ Time-synced dubbing, no overlapping voices** — every translated clip starts
  exactly where the original sentence started, and clips are guaranteed never to talk
  over each other: long translations are sped up pitch-preserved (gently up to 1.35×,
  harder up to 1.8× when needed) and, in extreme cases, faded out at the segment
  boundary — with a warning telling you which segment was affected.
- **🎵 Smart background-audio mode** — optionally keep the original soundtrack under
  the dub. The original is automatically ducked while the dubbed voice speaks
  (sidechain compression) and comes back up between sentences, so music and ambience
  survive without two voices fighting.
- **📝 Translated subtitles** — get a matching `.srt` file alongside the dubbed video.
- **🎚️ Adjustable accuracy** — five Whisper model sizes, from `tiny` (fast drafts) to
  `large-v3` (best transcription).
- **🛡️ Voice fallback** — if the free TTS endpoint rejects a specific text+voice combo,
  VoxDub automatically retries with other voices of the same locale and tells you.
- **🔇 Lossless video** — the video stream is copied untouched (no re-encode, no quality
  loss); only the audio track is replaced.
- **🖥️ Web UI and CLI** — a friendly browser app for everyday use, a `voxdub` command
  for scripting and batch work.
- **📦 Zero-setup launchers** — double-click starters for Windows, macOS, and Linux that
  install Python, all dependencies, and even ffmpeg automatically on first run.

## How it works

```
video ─ ffmpeg → audio ─ Whisper (local) → timed transcript ─ Google Translate (free)
      → translated text ─ edge-tts (free MS neural voices) → per-segment speech
      → clips placed at original timestamps → new video (video stream untouched)
```

Inspired by [ruslanmv/Video-Translator](https://github.com/ruslanmv/Video-Translator), upgraded with
local Whisper transcription, natural neural voices, and time-synced dubbing.

Transcription runs fully offline. Translation and voice synthesis use free online services
(no API keys), so an internet connection is needed while converting.

## Quick start (no manual setup)

Download the latest zip from the [Releases page](../../releases), unpack it, then:

| OS | Do this |
|---|---|
| **Windows** | Double-click `Start VoxDub.bat` |
| **macOS** | Right-click `Start VoxDub.command` → **Open** (only needed the first time; after that, double-click) |
| **Linux** | `./start-voxdub.sh` |

The first launch installs everything automatically — Python (via [uv](https://docs.astral.sh/uv/)),
all dependencies, and a static ffmpeg build if your system doesn't have one — then opens the app
in your browser. Later launches start in seconds. The Whisper `small` model (~460 MB) downloads
automatically on the first translation.

## Setup (developers)

```bash
# uv: https://docs.astral.sh/uv/getting-started/installation/
uv sync                    # creates .venv with Python 3.12 and installs deps
```

ffmpeg is found on PATH if installed (e.g. `brew install ffmpeg`); otherwise a static
build is downloaded automatically on first use.

## Usage

### Command line

```bash
uv run voxdub input.mp4 --to hi --srt          # dub to Hindi + subtitles
uv run voxdub input.mp4 --to es --keep-bg      # keep music/ambience underneath
uv run voxdub input.mp4 --to ja --model medium # better transcription, slower
uv run voxdub --list-voices th                 # see voices for a language
uv run voxdub input.mp4 --to zh-TW --voice zh-TW-YunJheNeural
```

(`videotranslate` still works as an alias.)

Output defaults to `input_<lang>.mp4` next to the input. Source language is auto-detected
(`--from en` to force it).

### Web UI

```bash
uv run python app.py       # opens http://127.0.0.1:7860 in your browser
```

Drag in a video, pick the target language, press Translate.

## Releasing

Pushing a tag like `v0.2.0` runs the smoke tests on Windows/macOS/Linux and publishes a
downloadable zip (with the launchers) as a GitHub Release — see `.github/workflows/`.

## Languages

en, hi, es, fr, de, it, pt, ja, ko, zh (Simplified), zh-TW, th, vi, ar (Gulf), ru —
see `video_translator/voices.py` to add more (any edge-tts locale works; add a line with
its Google Translate code and default voice).

## Notes & limitations

- The free Edge TTS endpoint sometimes returns no audio for specific text+voice combos.
  The tool automatically retries with other voices of the same locale and warns you;
  a segment is left silent only if every voice fails.
- Whisper model sizes: `tiny`/`base` (fast, rough), `small` (default), `medium`/`large-v3`
  (best accuracy, slower). All run on CPU with int8 quantization.
- `--keep-bg` keeps the original audio under the dub, ducked while the dubbed voice
  speaks — good for videos with music. Between sentences the original (including its
  speech) comes back up.
- Translation quality is Google Translate quality; dubbing timing is synced to segment
  starts, not lip movements.
