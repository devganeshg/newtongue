"""VoxDub — Gradio web UI for the video voice translator. Run: uv run python app.py"""

import warnings
from pathlib import Path

# pydub 0.25 trips SyntaxWarning on import under Python 3.12
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")

import gradio as gr

from video_translator.pipeline import Options, translate_video
from video_translator.voices import LANGUAGES

LANG_CHOICES = [(f"{lang.name} ({code})", code) for code, lang in LANGUAGES.items()]
SOURCE_CHOICES = [("Auto-detect", "auto")] + LANG_CHOICES
MODEL_CHOICES = ["tiny", "base", "small", "medium", "large-v3"]

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


def run(video, source_lang, target_lang, voice, model_size, keep_bg, want_srt,
        progress=gr.Progress()):
    if video is None:
        raise gr.Error("Please upload a video first.")

    def report(fraction, message):
        progress(fraction, desc=message)

    try:
        result = translate_video(
            Path(video),
            Options(
                target_lang=target_lang,
                source_lang=None if source_lang == "auto" else source_lang,
                voice=(voice or "").strip() or None,
                model_size=model_size,
                keep_background=keep_bg,
                write_srt=want_srt,
            ),
            progress=report,
        )
    except (ValueError, RuntimeError) as exc:
        raise gr.Error(str(exc))

    transcript = "\n".join(
        f"[{seg.start:7.2f}s] {seg.text}\n          → {seg.translated}"
        for seg in result.segments
    )
    files = [str(result.video)] + ([str(result.srt)] if result.srt else [])
    info_md = (
        f"Source language detected: **{result.source_lang}** · "
        f"{len(result.segments)} speech segments"
    )
    if result.warnings:
        info_md += "\n\n⚠️ " + "\n\n⚠️ ".join(result.warnings)
    return str(result.video), files, info_md, transcript


with gr.Blocks(title="VoxDub — dub videos into any language") as demo:
    gr.HTML(HEADER_HTML)
    with gr.Row():
        with gr.Column():
            video_in = gr.Video(label="1 · Upload your video")
            with gr.Row():
                source = gr.Dropdown(SOURCE_CHOICES, value="auto", label="From")
                target = gr.Dropdown(LANG_CHOICES, value="hi", label="2 · Dub into")
            with gr.Accordion("Advanced options", open=False):
                voice = gr.Textbox(
                    label="Voice",
                    placeholder="Leave empty for the default voice, e.g. hi-IN-MadhurNeural",
                )
                model = gr.Dropdown(
                    MODEL_CHOICES, value="small", label="Whisper model",
                    info="tiny/base = fast & rough · small = balanced · medium/large-v3 = best, slower",
                )
                keep_bg = gr.Checkbox(
                    label="Keep original audio as quiet background (music/ambience)")
                want_srt = gr.Checkbox(label="Also generate translated subtitles (.srt)")
            btn = gr.Button("3 · Dub it ✨", variant="primary", size="lg",
                            elem_id="vox-translate")
        with gr.Column():
            video_out = gr.Video(label="Dubbed video")
            downloads = gr.File(label="Downloads", file_count="multiple")
            info = gr.Markdown()
            with gr.Accordion("Transcript & translation", open=False):
                transcript = gr.Textbox(show_label=False, lines=14)
    gr.HTML(FOOTER_HTML)

    btn.click(run, [video_in, source, target, voice, model, keep_bg, want_srt],
              [video_out, downloads, info, transcript])

if __name__ == "__main__":
    demo.launch(
        inbrowser=True,
        theme=THEME,
        css=CSS,
        favicon_path=str(ASSETS / "logo.svg"),
        show_error=True,
    )
