"""Text translation via deep-translator's free Google Translate engine."""

import time

from deep_translator import GoogleTranslator

from .stt import Segment

_BATCH_SIZE = 25
_RETRIES = 3


def translate_segments(segments: list[Segment], source: str, target: str) -> None:
    """Fill segment.translated in place. `source`/`target` are Google language codes."""
    if source == target:
        for seg in segments:
            seg.translated = seg.text
        return

    translator = GoogleTranslator(source=source, target=target)
    for i in range(0, len(segments), _BATCH_SIZE):
        batch = segments[i:i + _BATCH_SIZE]
        texts = [seg.text for seg in batch]
        for attempt in range(_RETRIES):
            try:
                results = translator.translate_batch(texts)
                break
            except Exception:
                if attempt == _RETRIES - 1:
                    raise RuntimeError(
                        "Translation failed after retries — check your internet connection."
                    )
                time.sleep(2 ** attempt)
        for seg, translated in zip(batch, results):
            seg.translated = (translated or "").strip()
