<p align="center">
  <img src="assets/logo.svg" width="96" alt="VoxDub logo">
</p>

<h1 align="center">VoxDub</h1>

<p align="center"><b>Dub any video into another language</b> — natural neural voices, no API keys.<br>
Windows · macOS · Linux</p>

<p align="center">
  <a href="https://github.com/devganeshg/voxdub/actions/workflows/ci.yml"><img src="https://github.com/devganeshg/voxdub/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="MIT license"></a>
  <a href="https://github.com/devganeshg/voxdub/releases"><img src="https://img.shields.io/github/v/release/devganeshg/voxdub?include_prereleases" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12-blue" alt="Python 3.11 | 3.12">
</p>

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
  (Microsoft Edge neural TTS) use free public endpoints. These are *unofficial*
  endpoints not intended for third-party use — see
  [Third-party services](#third-party-services-and-your-responsibilities).
- **⏱️ Time-synced dubbing, no overlapping voices** — every translated clip starts
  exactly where the original sentence started, and clips are guaranteed never to talk
  over each other: long translations are sped up pitch-preserved (gently up to 1.35×,
  harder up to 1.8× when needed) and, in extreme cases, faded out at the segment
  boundary — with a warning telling you which segment was affected.
- **🎵 Smart background-audio mode** — optionally keep the original soundtrack under
  the dub. The original is automatically ducked while the dubbed voice speaks
  (sidechain compression) and comes back up between sentences, so music and ambience
  survive without two voices fighting.
- **📝 Subtitles in SRT, VTT, ASS, or TXT** — generate any combination alongside the
  dubbed video, and optionally **burn them into the video frame** (hardcoded, for
  platforms that don't support separate subtitle tracks) or **embed them as a soft
  track** (toggleable in the player, lossless — the video isn't re-encoded).
- **🈺 Bilingual subtitles** — show the translation, the original text, or both
  (translation on top, original underneath) in every subtitle format.
- **✍️ Edit, then dub** — feed VoxDub your own (or hand-corrected) SRT/VTT with
  `--from-subs`: it dubs from your transcript instead of running Whisper. Generate
  subtitles first, fix any mis-transcriptions, then dub from the fixed file.
- **⚡ Subtitles-only mode** — `--no-dub` transcribes and translates without
  synthesizing a voice: fast translated subtitles for any video, or even for a bare
  subtitle file (`--no-dub --from-subs movie.srt --to es` needs no video at all).
- **🚀 GPU acceleration** — transcription automatically uses an NVIDIA GPU when one
  is available (`--device auto|cpu|cuda`); CPU with int8 quantization otherwise.
- **🌍 Dub into multiple languages in one run** — pick several target languages at
  once; VoxDub transcribes the source audio only once and reuses it for every
  language, so you get one video (and subtitle set) per language without re-running
  Whisper each time.
- **🎚️ Voice speed, pitch & volume control** — nudge the dubbed voice faster/slower,
  higher/lower, or louder/quieter, independent of the automatic sync speed-up.
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

### Troubleshooting first-run setup

The launchers print the actual error if something fails, but these are the most common causes:

<details>
<summary><b>Windows</b></summary>

- **"Windows protected your PC" (SmartScreen)** — expected for an unsigned `.bat` file
  downloaded from the internet. Click **More info** → **Run anyway**.
- **`uv sync` fails partway through** — often a path-length problem: Windows limits paths to
  260 characters, and this can be exceeded inside nested Python package folders. Move the
  unzipped VoxDub folder somewhere short, e.g. `C:\VoxDub`, and re-run.
- **"could not install uv automatically"** — a work/school PC's policy is likely blocking
  PowerShell script downloads. Install uv manually from
  [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/), then re-run
  `Start VoxDub.bat`.
- **Stuck after a previous failed attempt** — delete the `.venv` folder next to the launcher
  and re-run; it rebuilds cleanly.

</details>

<details>
<summary><b>macOS</b></summary>

- **"cannot be opened because it is from an unidentified developer"** — right-click
  `Start VoxDub.command` → **Open** (only needed the first time).
- **`uv sync` fails with a compiler error** — install the Xcode Command Line Tools:
  `xcode-select --install`.

</details>

<details>
<summary><b>Linux</b></summary>

- **"Permission denied" running the script** — `chmod +x start-voxdub.sh` first.
- **`uv sync` fails on a package with no prebuilt wheel** — install build tools for your
  distro, e.g. `sudo apt install build-essential` on Debian/Ubuntu.

</details>

<details>
<summary><b>Any OS</b></summary>

- **Dependency install or first dub fails with a network error** — VoxDub needs internet
  the first time you run it (to install Python packages) and every time you translate (Google
  Translate + edge-tts are free but not local); a corporate firewall/proxy blocking `pypi.org`,
  `huggingface.co`, or Microsoft's TTS endpoint will cause this.
- Still stuck? [Open an issue](https://github.com/devganeshg/voxdub/issues/new) with the exact
  error text — the launchers are designed to print an actionable message, so please paste it in.

</details>

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
uv run voxdub input.mp4 --to hi --srt                    # dub to Hindi + subtitles
uv run voxdub input.mp4 --to es --keep-bg                # keep music/ambience underneath
uv run voxdub input.mp4 --to ja --model medium            # better transcription, slower
uv run voxdub --list-voices th                            # see voices for a language
uv run voxdub input.mp4 --to zh-TW --voice zh-TW-YunJheNeural
uv run voxdub input.mp4 --to hi,es,ja --subtitles srt,vtt # dub into 3 languages in one pass
uv run voxdub input.mp4 --to hi --burn-subtitles          # hardcode subtitles into the video
uv run voxdub input.mp4 --to hi --embed-subtitles         # soft subtitle track (toggleable, lossless)
uv run voxdub input.mp4 --to hi --srt --subtitle-content both  # bilingual subtitles
uv run voxdub input.mp4 --to hi --no-dub --subtitles srt  # translated subtitles only, no dubbing
uv run voxdub input.mp4 --to hi --from-subs fixed.srt     # dub from your hand-corrected transcript
uv run voxdub --no-dub --from-subs movie.srt --to es      # translate a subtitle file (no video)
uv run voxdub input.mp4 --to hi --rate +15% --pitch -10Hz # faster, deeper voice
```

A tip for best quality: run once with `--no-dub --subtitles srt`, fix any transcription
mistakes in the SRT, then dub with `--from-subs your_fixed.srt` — Whisper isn't re-run.

(`videotranslate` still works as an alias.)

Output defaults to `input_<lang>.mp4` next to the input. Source language is auto-detected
(`--from en` to force it).

### Web UI

```bash
uv run python app.py       # opens http://127.0.0.1:7860 in your browser
```

Drag in a video, pick one or more target languages, press Dub it. Advanced options let you
choose subtitle formats and content (including bilingual), burn or soft-embed them into the
video, dub from your own SRT/VTT transcript, skip dubbing entirely (subtitles only), and
tweak voice speed/pitch/volume.

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
- `--burn-subtitles` re-encodes the video (subtitle burn-in can't be a lossless copy) and
  needs an ffmpeg build with libass (the `subtitles` filter). If your system ffmpeg lacks
  it, VoxDub automatically falls back to the auto-downloaded static build, which has it.
- **Burned subtitles showing □□□ boxes instead of text?** That means no font with the
  target script's glyphs was found. VoxDub automatically picks an installed font that
  covers the target language (Nirmala UI / Leelawadee on Windows, Arial Unicode on macOS,
  Noto Sans on Linux) and warns if none exists — installing
  [Noto Sans](https://fonts.google.com/noto) for your target script fixes it.
- **Embedded subtitles unreadable in your player?** Some players (notably QuickTime)
  render `mov_text` tracks in a plain box and handle non-Latin scripts poorly. Use
  `--burn-subtitles` instead (drawn by VoxDub itself, works everywhere), or play the
  video+SRT pair in VLC/mpv.
- `--rate`/`--pitch`/`--volume` adjust the synthesized voice itself; they're independent of
  the automatic per-segment speed-up VoxDub applies to keep segments from overlapping.
- `--embed-subtitles` picks the subtitle codec from the output container: `mov_text` for
  MP4/MOV/M4V, SRT for MKV, WebVTT for WebM. Some players (notably VLC on certain
  platforms) hide `mov_text` tracks by default — check the subtitle menu.
- `--device cuda` needs an NVIDIA GPU and a CUDA-enabled ctranslate2; the default
  `auto` tries the GPU and silently falls back to CPU, so it's always safe.
- `--from-subs` accepts SRT and VTT. Timings come from the file, so if you edit them,
  the dub follows your edits.
- Translation quality is Google Translate quality; dubbing timing is synced to segment
  starts, not lip movements.

## Contributing

Contributions are welcome — bug fixes, new languages/voices, docs, anything. See
[CONTRIBUTING.md](CONTRIBUTING.md) for how to set up a dev environment and submit a PR, and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community guidelines.

- 🐛 Found a bug? [Open an issue](https://github.com/devganeshg/voxdub/issues/new/choose).
- 💡 Have an idea? [Start a discussion](https://github.com/devganeshg/voxdub/discussions) or
  open a feature-request issue.
- 🔀 Ready to code? Fork the repo, make your change, and open a pull request.

## Third-party services and your responsibilities

VoxDub is a client. It does not host translation or speech synthesis — it talks to services
run by other companies. Please read this before depending on it for anything important.

**The translation and TTS endpoints are unofficial.** `deep-translator`'s free
`GoogleTranslator` backend uses the public `translate.google.com` web endpoint, and
`edge-tts` uses the private endpoint behind Microsoft Edge's "Read Aloud" feature. Neither
is a documented, supported API for third-party applications, and using them may not be
consistent with Google's or Microsoft's terms of service. Both can change, rate-limit, or
stop working at any time without notice — that is the single most likely reason VoxDub will
break for you. For commercial or production use, use an official paid API (Google Cloud
Translation, DeepL, Azure Speech) instead.

**You are responsible for the content you process.** Only dub videos you own or have the
rights to translate, adapt, and distribute. Dubbing produces a derivative work, and
translating or re-voicing someone else's video without permission may infringe copyright or
personality/voice rights depending on your jurisdiction. VoxDub's authors are not
responsible for how you use it.

**Machine translation is not accurate translation.** Do not rely on VoxDub's output for
legal, medical, safety, or other consequential material without human review.

## License

VoxDub itself is [MIT licensed](LICENSE) — use it, modify it, and ship it however you like.

It depends on third-party projects under their own licenses, and two are worth calling out
because they are **not** permissive:

- **[edge-tts](https://github.com/rany2/edge-tts) is LGPL-3.0.** VoxDub imports it as an
  unmodified, separately-installed library, so VoxDub stays MIT. If you redistribute VoxDub
  bundled with edge-tts, LGPL-3.0 §4 requires that your users be able to replace it with
  their own modified copy — installing it normally via `uv`/`pip` satisfies this.
- **ffmpeg builds are typically GPL-licensed.** VoxDub does not ship ffmpeg; it uses your
  system ffmpeg, or `static-ffmpeg` downloads a build onto *your* machine at runtime, so
  plain use carries no distribution obligation. If you package VoxDub into an installer that
  bundles an ffmpeg binary, the GPL terms of that build apply to what you distribute.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the full dependency list.
