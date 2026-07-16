"""Supported target languages and their default edge-tts neural voices."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str          # our canonical code (used on CLI / UI)
    name: str
    google_code: str   # code understood by Google Translate
    whisper_code: str  # code understood by Whisper (source-language hint)
    default_voice: str # edge-tts voice
    iso639_2: str      # 3-letter code players show on embedded subtitle tracks


LANGUAGES: dict[str, Language] = {
    lang.code: lang
    for lang in [
        Language("en", "English", "en", "en", "en-US-AriaNeural", "eng"),
        Language("hi", "Hindi", "hi", "hi", "hi-IN-SwaraNeural", "hin"),
        Language("es", "Spanish", "es", "es", "es-ES-ElviraNeural", "spa"),
        Language("fr", "French", "fr", "fr", "fr-FR-DeniseNeural", "fra"),
        Language("de", "German", "de", "de", "de-DE-KatjaNeural", "deu"),
        Language("it", "Italian", "it", "it", "it-IT-ElsaNeural", "ita"),
        Language("pt", "Portuguese", "pt", "pt", "pt-BR-FranciscaNeural", "por"),
        Language("ja", "Japanese", "ja", "ja", "ja-JP-NanamiNeural", "jpn"),
        Language("ko", "Korean", "ko", "ko", "ko-KR-SunHiNeural", "kor"),
        Language("zh", "Chinese (Simplified)", "zh-CN", "zh", "zh-CN-XiaoxiaoNeural", "chi"),
        Language("zh-TW", "Chinese (Taiwan)", "zh-TW", "zh", "zh-TW-HsiaoChenNeural", "chi"),
        # Premwadee (female) currently fails on many inputs server-side; Niwat is reliable
        Language("th", "Thai", "th", "th", "th-TH-NiwatNeural", "tha"),
        Language("vi", "Vietnamese", "vi", "vi", "vi-VN-HoaiMyNeural", "vie"),
        Language("ar", "Arabic (Gulf)", "ar", "ar", "ar-AE-FatimaNeural", "ara"),
        Language("ru", "Russian", "ru", "ru", "ru-RU-SvetlanaNeural", "rus"),
    ]
}


def get_language(code: str) -> Language:
    try:
        return LANGUAGES[code]
    except KeyError:
        supported = ", ".join(sorted(LANGUAGES))
        raise ValueError(f"Unsupported language {code!r}. Supported: {supported}") from None
