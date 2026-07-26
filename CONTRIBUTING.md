# Contributing to Newtongue

Thanks for considering a contribution! Newtongue is a small, focused tool — most contributions
fall into a few clear categories below.

## Dev setup

```bash
git clone https://github.com/devganeshg/newtongue.git
cd newtongue
uv sync                    # creates .venv with Python 3.11/3.12 and installs deps
uv run python app.py       # web UI
uv run newtongue --help       # CLI
```

ffmpeg is picked up from PATH if installed, otherwise Newtongue downloads a static build
automatically the first time it's needed.

## Ways to contribute

### Add a language or voice

Languages live in `newtongue/voices.py` as a flat list of `Language` entries (code,
name, Google Translate code, Whisper code, default edge-tts voice). To add one:

1. Add a `Language(...)` line.
2. Find a good default voice: `uv run newtongue --list-voices <prefix>` lists every edge-tts
   voice for that locale.
3. Sanity-check it end-to-end: `uv run newtongue examples/sample.mp4 --to <code>` and listen to
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

`tests/` covers the pure logic — subtitle timestamp formatting/parsing and the clip-placement
math in `timeline.py`. It needs no network and no ffmpeg (tempo-shifting is stubbed), so it's
fast:

```bash
uv run pytest
```

Please add a test alongside any change to `subtitles.py` or `timeline.py` — those are the
places where a bug produces output that still *looks* valid.

Then check the pipeline itself still runs. This needs no network (`en` → `en` skips
translation, `--no-dub` skips TTS):

```bash
printf '1\n00:00:00,000 --> 00:00:02,000\nHello there.\n' > /tmp/in.srt
uv run newtongue --no-dub --from-subs /tmp/in.srt --to en --from en --subtitles srt,vtt,ass,txt
```

And, if your change touches dubbing, do one real run with a video you own:

```bash
uv run newtongue your_clip.mp4 --to hi --model tiny
```

CI (`.github/workflows/ci.yml`) runs the unit tests, a smoke test, and an offline end-to-end
run on Windows, macOS, and Linux for every PR. A fourth job, `e2e-live`, performs a real dub
against the free Google Translate and Edge TTS endpoints; it's marked `continue-on-error`
because those are unofficial services that can break without notice — a red `e2e-live` with
everything else green means an upstream endpoint changed, not that your PR is broken.

## Pull requests

- Keep PRs focused on one change.
- Describe *why* the change is needed in the description, not just what changed.
- Reference the issue it resolves, if any (`Fixes #123`).

## Reporting security issues

Please don't open a public issue for a security vulnerability — see
[SECURITY.md](.github/SECURITY.md) for how to report it privately.
