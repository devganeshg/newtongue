"""Supported target languages and their default edge-tts neural voices."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str          # our canonical code (used on CLI / UI)
    name: str
    google_code: str   # code understood by Google Translate
    whisper_code: str  # code understood by Whisper (source-language hint)
    default_voice: str # edge-tts voice


LANGUAGES: dict[str, Language] = {
    lang.code: lang
    for lang in [
        Language("en", "English", "en", "en", "en-US-AriaNeural"),
        Language("hi", "Hindi", "hi", "hi", "hi-IN-SwaraNeural"),
        Language("es", "Spanish", "es", "es", "es-ES-ElviraNeural"),
        Language("fr", "French", "fr", "fr", "fr-FR-DeniseNeural"),
        Language("de", "German", "de", "de", "de-DE-KatjaNeural"),
        Language("it", "Italian", "it", "it", "it-IT-ElsaNeural"),
        Language("pt", "Portuguese", "pt", "pt", "pt-BR-FranciscaNeural"),
        Language("ja", "Japanese", "ja", "ja", "ja-JP-NanamiNeural"),
        Language("ko", "Korean", "ko", "ko", "ko-KR-SunHiNeural"),
        Language("zh", "Chinese (Simplified)", "zh-CN", "zh", "zh-CN-XiaoxiaoNeural"),
        Language("zh-TW", "Chinese (Taiwan)", "zh-TW", "zh", "zh-TW-HsiaoChenNeural"),
        # Premwadee (female) currently fails on many inputs server-side; Niwat is reliable
        Language("th", "Thai", "th", "th", "th-TH-NiwatNeural"),
        Language("vi", "Vietnamese", "vi", "vi", "vi-VN-HoaiMyNeural"),
        Language("ar", "Arabic (Gulf)", "ar", "ar", "ar-AE-FatimaNeural"),
        Language("ru", "Russian", "ru", "ru", "ru-RU-SvetlanaNeural"),
    ]
}


def get_language(code: str) -> Language:
    try:
        return LANGUAGES[code]
    except KeyError:
        supported = ", ".join(sorted(LANGUAGES))
        raise ValueError(f"Unsupported language {code!r}. Supported: {supported}") from None
