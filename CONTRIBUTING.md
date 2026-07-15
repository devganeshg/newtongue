# Contributing to VoxDub

Thanks for considering a contribution! VoxDub is a small, focused tool — most contributions
fall into a few clear categories below.

## Dev setup

```bash
git clone https://github.com/devganeshg/voxdub.git
cd voxdub
uv sync                    # creates .venv with Python 3.11/3.12 and installs deps
uv run python app.py       # web UI
uv run voxdub --help       # CLI
```

ffmpeg is picked up from PATH if installed, otherwise VoxDub downloads a static build
automatically the first time it's needed.

## Ways to contribute

### Add a language or voice

Languages live in `video_translator/voices.py` as a flat list of `Language` entries (code,
name, Google Translate code, Whisper code, default edge-tts voice). To add one:

1. Add a `Language(...)` line.
2. Find a good default voice: `uv run voxdub --list-voices <prefix>` lists every edge-tts
   voice for that locale.
3. Sanity-check it end-to-end: `uv run voxdub examples/sample.mp4 --to <code>` and listen to
   the result.

### Fix a bug

Please include repro steps (input video characteristics, target language, CLI/UI, the exact
error) — see the bug report issue template for the shape that's most useful.

### Everything else (features, docs, refactors)

Open an issue first for anything non-trivial so we can agree on the approach before you put
time into it. Small, focused PRs are much easier to review than large ones.

## Code style

- No new abstractions or config knobs unless the feature actually needs them — this codebase
  favors a handful of straightforward modules (`media.py`, `stt.py`, `translate.py`, `tts.py`,
  `timeline.py`, `subtitles.py`, `pipeline.py`) over layers of indirection.
- Comments explain *why*, not *what* — skip comments that just restate the code.
- Match existing formatting; there's no linter/formatter enforced yet, just keep it consistent
  with the surrounding file.

## Testing your change

There's no formal test suite yet (contributions welcome here too). At minimum, before opening
a PR:

```bash
uv run python -m py_compile app.py video_translator/*.py   # no syntax errors
uv run voxdub examples/sample.mp4 --to hi --model tiny      # pipeline still runs end-to-end
```

CI (`.github/workflows/ci.yml`) runs a smoke test on Windows, macOS, and Linux on every PR.

## Pull requests

- Keep PRs focused on one change.
- Describe *why* the change is needed in the description, not just what changed.
- Reference the issue it resolves, if any (`Fixes #123`).

## Reporting security issues

Please don't open a public issue for a security vulnerability — see
[SECURITY.md](.github/SECURITY.md) for how to report it privately.
