# Third-party notices

VoxDub is distributed under the [MIT License](LICENSE). It depends on the projects below,
each under its own license. Nothing here is legal advice; if you redistribute VoxDub, verify
the terms of everything you bundle with it.

## Direct dependencies

| Project | License | Notes |
|---|---|---|
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT | Runs locally. Whisper model weights are downloaded from Hugging Face under their own terms (OpenAI's Whisper models are MIT). |
| [deep-translator](https://github.com/nidhaloff/deep-translator) | MIT | See the service note below. |
| [edge-tts](https://github.com/rany2/edge-tts) | **LGPL-3.0** | See "Copyleft dependencies" below. |
| [pydub](https://github.com/jiaaro/pydub) | MIT | |
| [gradio](https://github.com/gradio-app/gradio) | Apache-2.0 | Web UI only. |
| [static-ffmpeg](https://github.com/zackees/static_ffmpeg) | MIT | The wrapper is MIT; the ffmpeg binaries it downloads are not. See below. |
| [ctranslate2](https://github.com/OpenNMT/CTranslate2) | MIT | Transitive, via faster-whisper. |
| [PyAV](https://github.com/PyAV-Org/PyAV) | BSD-3-Clause | Transitive, via faster-whisper. |

The full resolved dependency tree, with pinned versions, is in `uv.lock`.

## Copyleft dependencies

### edge-tts — LGPL-3.0

VoxDub calls edge-tts through its public Python API as an unmodified library installed
separately by `uv`/`pip`. Under LGPL-3.0 this makes VoxDub a "work that uses the Library",
so VoxDub remains MIT-licensed.

If you redistribute VoxDub together with a copy of edge-tts, LGPL-3.0 §4 applies to your
distribution: recipients must be able to replace edge-tts with a modified version and have
VoxDub still work. A normal Python install (edge-tts in `site-packages`, importable and
replaceable) satisfies this. A frozen single-file binary with edge-tts statically embedded
generally does not, without extra steps.

VoxDub does not modify edge-tts. Its source is at https://github.com/rany2/edge-tts.

### ffmpeg — GPL (typically) or LGPL

VoxDub does not ship ffmpeg. It invokes whatever `ffmpeg` is on your `PATH`, and falls back
to `static-ffmpeg`, which downloads a prebuilt binary to your machine at runtime. Because
the download happens on the end user's machine and VoxDub communicates with ffmpeg only as a
separate process via the command line, ordinary use of VoxDub creates no ffmpeg distribution
obligation for you.

Most prebuilt static ffmpeg builds — including those with `libass`, which VoxDub's
`--burn-subtitles` requires — are compiled with GPL-licensed components and are therefore
GPL-licensed as a whole. **If you build an installer or bundle that includes an ffmpeg
binary, you are distributing ffmpeg, and that build's license (usually GPL-2.0-or-later or
GPL-3.0-or-later) governs what you must provide.** See https://ffmpeg.org/legal.html.

## Network services

These are services, not licensed code, so no software license governs them — their terms of
service do.

- **Google Translate**, reached via deep-translator's free `GoogleTranslator` backend, which
  uses the public `translate.google.com` web endpoint rather than the paid Cloud Translation
  API. This is not a documented third-party API and its use may not be consistent with
  Google's terms of service.
- **Microsoft Edge "Read Aloud" TTS**, reached via edge-tts, which uses the private endpoint
  Edge itself uses. This is not a public API and its use may not be consistent with
  Microsoft's terms of service.

Both may rate-limit, change, or stop working without notice. For commercial or production
use, switch to an official API (Google Cloud Translation, DeepL, Azure Speech).

## Fonts

VoxDub bundles no fonts. For burned-in subtitles it locates a font already installed on your
system that covers the target script (see `video_translator/fonts.py`) and points libass at
that file. Those fonts are licensed by their vendors — Microsoft, Apple, or your Linux
distribution's Noto packages (SIL Open Font License 1.1) — and VoxDub neither copies nor
redistributes them.

## Sample media

Any sample videos under `examples/` are local development fixtures and are excluded from
version control via `.gitignore`. No third-party media is distributed with VoxDub.
