"""Gradio web UI for the video voice translator. Run: uv run python app.py"""

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
                voice=voice.strip() or None,
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


with gr.Blocks(title="Video Voice Translator") as demo:
    gr.Markdown(
        "# 🎬 Video Voice Translator\n"
        "Upload a video, pick a language, and get it back dubbed with a natural neural voice. "
        "Transcription runs locally (Whisper); translation and voices use free online services."
    )
    with gr.Row():
        with gr.Column():
            video_in = gr.Video(label="Input video")
            source = gr.Dropdown(SOURCE_CHOICES, value="auto", label="Source language")
            target = gr.Dropdown(LANG_CHOICES, value="hi", label="Target language")
            voice = gr.Textbox(
                label="Voice (optional)",
                placeholder="Leave empty for the default voice, e.g. hi-IN-MadhurNeural",
            )
            model = gr.Dropdown(MODEL_CHOICES, value="small", label="Whisper model")
            keep_bg = gr.Checkbox(label="Keep original audio as quiet background (music/ambience)")
            want_srt = gr.Checkbox(label="Also generate translated subtitles (.srt)")
            btn = gr.Button("Translate", variant="primary")
        with gr.Column():
            video_out = gr.Video(label="Dubbed video")
            downloads = gr.File(label="Downloads", file_count="multiple")
            info = gr.Markdown()
            transcript = gr.Textbox(label="Transcript & translation", lines=14)

    btn.click(run, [video_in, source, target, voice, model, keep_bg, want_srt],
              [video_out, downloads, info, transcript])

if __name__ == "__main__":
    demo.launch(inbrowser=True)
