"""VoxDub — Gradio web UI for the video voice translator. Run: uv run python app.py"""

import warnings
from pathlib import Path

# pydub 0.25 trips SyntaxWarning on import under Python 3.12
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")

import gradio as gr

from video_translator.pipeline import Options, translate_video, translate_video_batch
from video_translator.subtitles import FORMATS as SUBTITLE_FORMATS
from video_translator.voices import LANGUAGES

LANG_CHOICES = [(f"{lang.name} ({code})", code) for code, lang in LANGUAGES.items()]
SOURCE_CHOICES = [("Auto-detect", "auto")] + LANG_CHOICES
MODEL_CHOICES = ["tiny", "base", "small", "medium", "large-v3"]
SUBTITLE_CHOICES = [(fmt.upper(), fmt) for fmt in SUBTITLE_FORMATS]
SUBTITLE_CONTENT_CHOICES = [("Translated", "translated"), ("Original", "original"),
                            ("Both (bilingual)", "both")]

ASSETS = Path(__file__).parent / "assets"

LOGO_SVG = """\
<svg viewBox="0 0 128 128" width="52" height="52" aria-hidden="true">
  <defs>
    <linearGradient id="vox-g" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8B5CF6"/><stop offset="100%" stop-color="#06B6D4"/>
    </linearGradient>
  </defs>
  <rect width="128" height="128" rx="28" fill="url(#vox-g)"/>
  <path d="M38 42.5v43c0 3.9 4.3 6.3 7.6 4.2l34-21.5c3.1-2 3.1-6.5 0-8.4l-34-21.5c-3.3-2.1-7.6.3-7.6 4.2z" fill="#fff"/>
  <g fill="#fff">
    <rect x="88" y="54" width="8" height="20" rx="4" opacity="0.85"/>
    <rect x="100" y="44" width="8" height="40" rx="4" opacity="0.95"/>
    <rect x="112" y="51" width="8" height="26" rx="4" opacity="0.7"/>
  </g>
</svg>"""

HEADER_HTML = f"""
<div id="vox-header">
  {LOGO_SVG}
  <div>
    <div class="vox-name">VoxDub</div>
    <div class="vox-tag">Dub any video into another language — natural neural voices, no API keys.</div>
  </div>
</div>
"""

FOOTER_HTML = """
<div id="vox-footer">
  🎙️ Transcription runs locally (Whisper) &nbsp;·&nbsp; 🌐 Translation &amp; voices use free online services
  &nbsp;·&nbsp; 🔑 No accounts, no API keys
</div>
"""

CSS = """
#vox-header { display: flex; align-items: center; gap: 16px; padding: 6px 0 2px; }
#vox-header .vox-name {
  font-size: 2.1rem; font-weight: 800; letter-spacing: -0.5px; line-height: 1.15;
  background: linear-gradient(90deg, #8B5CF6, #06B6D4);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
#vox-header .vox-tag { color: var(--body-text-color-subdued, #64748b); font-size: 0.95rem; }
#vox-translate {
  background: linear-gradient(90deg, #7C3AED, #0891B2); color: #fff; border: none;
  font-weight: 700; letter-spacing: 0.2px;
}
#vox-translate:hover { filter: brightness(1.12); }
#vox-footer {
  text-align: center; color: var(--body-text-color-subdued, #64748b);
  font-size: 0.85rem; padding-top: 10px;
}
"""

THEME = gr.themes.Soft(
    primary_hue="violet",
    secondary_hue="cyan",
    neutral_hue="slate",
)


def _pct(delta: float) -> str:
    """Slider value in [-50, 50] -> edge-tts percent delta string, e.g. '+15%'."""
    return f"{delta:+.0f}%"


def _hz(delta: float) -> str:
    """Slider value in [-50, 50] -> edge-tts Hz delta string, e.g. '+20Hz'."""
    return f"{delta:+.0f}Hz"


def run(video, source_lang, target_langs, voice, model_size, keep_bg, subtitle_formats,
        subtitle_content, burn_subs, embed_subs, subs_only, transcript_file,
        rate, pitch, volume, progress=gr.Progress()):
    if video is None and not (subs_only and transcript_file):
        raise gr.Error("Please upload a video first. (Only a subtitle file is enough when "
                       "\"Subtitles only\" is on and a transcript file is provided.)")
    if not target_langs:
        raise gr.Error("Pick at least one target language.")
    if subs_only and (burn_subs or embed_subs):
        raise gr.Error("Burning/embedding subtitles produces a video — turn off "
                       "\"Subtitles only\" to use them.")

    def report(fraction, message):
        progress(fraction, desc=message)

    opts = Options(
        target_lang=target_langs[0],
        source_lang=None if source_lang == "auto" else source_lang,
        voice=(voice or "").strip() or None,
        model_size=model_size,
        keep_background=keep_bg,
        subtitle_formats=tuple(subtitle_formats or ()),
        subtitle_content=subtitle_content,
        burn_subtitles=burn_subs,
        embed_subtitles=embed_subs,
        subtitles_only=subs_only,
        source_subtitles=Path(transcript_file) if transcript_file else None,
        speech_rate=_pct(rate),
        speech_pitch=_hz(pitch),
        speech_volume=_pct(volume),
    )

    input_path = Path(video) if video else None
    try:
        if len(target_langs) > 1:
            results = translate_video_batch(input_path, target_langs, opts, progress=report)
        else:
            results = [translate_video(input_path, opts, progress=report)]
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise gr.Error(str(exc))

    files = []
    info_lines = [f"Source language detected: **{results[0].source_lang}**"]
    transcript_parts = []
    for result in results:
        if result.video:
            files.append(str(result.video))
        files += [str(p) for p in result.subtitles.values()]
        info_lines.append(
            f"- **{result.target_lang}**: {len(result.segments)} speech segments"
            + ("".join(f"\n  - ⚠️ {w}" for w in result.warnings) if result.warnings else "")
        )
        transcript_parts.append(
            f"=== {result.target_lang} ===\n" + "\n".join(
                f"[{seg.start:7.2f}s] {seg.text}\n          → {seg.translated}"
                for seg in result.segments
            )
        )

    first_video = str(results[0].video) if results[0].video else None
    return first_video, files, "\n".join(info_lines), "\n\n".join(transcript_parts)


with gr.Blocks(title="VoxDub — dub videos into any language") as demo:
    gr.HTML(HEADER_HTML)
    with gr.Row():
        with gr.Column():
            video_in = gr.Video(label="1 · Upload your video")
            source = gr.Dropdown(SOURCE_CHOICES, value="auto", label="From")
            target = gr.Dropdown(
                LANG_CHOICES, value=["hi"], multiselect=True,
                label="2 · Dub into (pick one or more)",
            )
            with gr.Accordion("Advanced options", open=False):
                voice = gr.Textbox(
                    label="Voice",
                    placeholder="Leave empty for the default voice, e.g. hi-IN-MadhurNeural "
                                "(applies to all selected languages)",
                )
                model = gr.Dropdown(
                    MODEL_CHOICES, value="small", label="Whisper model",
                    info="tiny/base = fast & rough · small = balanced · medium/large-v3 = best, slower",
                )
                keep_bg = gr.Checkbox(
                    label="Keep original audio as quiet background (music/ambience)")
                transcript_file = gr.File(
                    label="Transcript file (optional)", file_types=[".srt", ".vtt"],
                    file_count="single")
                gr.Markdown(
                    "*Provide an SRT/VTT to dub from your own (or hand-corrected) transcript "
                    "instead of running Whisper.*")
                subs_only = gr.Checkbox(
                    label="Subtitles only — skip dubbing, just produce translated subtitle files")
                subtitle_formats = gr.CheckboxGroup(
                    SUBTITLE_CHOICES, label="Generate subtitle files",
                    info="SRT/VTT for players, ASS for styled subs, TXT for plain text")
                subtitle_content = gr.Radio(
                    SUBTITLE_CONTENT_CHOICES, value="translated", label="Subtitle content",
                    info="Both = bilingual: translation on top, original underneath")
                burn_subs = gr.Checkbox(
                    label="Burn subtitles into the video (hardcoded, re-encodes video)")
                embed_subs = gr.Checkbox(
                    label="Embed subtitles as a soft track (toggleable in the player, lossless)")
                with gr.Row():
                    rate = gr.Slider(-50, 50, value=0, step=1, label="Speech speed",
                                     info="% faster/slower")
                    pitch = gr.Slider(-50, 50, value=0, step=1, label="Speech pitch",
                                      info="Hz up/down")
                    volume = gr.Slider(-50, 50, value=0, step=1, label="Speech volume",
                                       info="% louder/quieter")
            btn = gr.Button("3 · Dub it ✨", variant="primary", size="lg",
                            elem_id="vox-translate")
        with gr.Column():
            video_out = gr.Video(label="Dubbed video (first language)")
            downloads = gr.File(label="Downloads (all videos & subtitles)", file_count="multiple")
            info = gr.Markdown()
            with gr.Accordion("Transcript & translation", open=False):
                transcript = gr.Textbox(show_label=False, lines=14)
    gr.HTML(FOOTER_HTML)

    btn.click(
        run,
        [video_in, source, target, voice, model, keep_bg, subtitle_formats,
         subtitle_content, burn_subs, embed_subs, subs_only, transcript_file,
         rate, pitch, volume],
        [video_out, downloads, info, transcript],
    )

if __name__ == "__main__":
    demo.launch(
        inbrowser=True,
        theme=THEME,
        css=CSS,
        favicon_path=str(ASSETS / "logo.svg"),
        show_error=True,
    )
