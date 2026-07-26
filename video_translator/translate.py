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
            except Exception as exc:
                if attempt == _RETRIES - 1:
                    # Keep the original error visible: a rate-limit, an unsupported
                    # language pair and a dead endpoint all land here, and "check
                    # your internet connection" is misleading for all three.
                    raise RuntimeError(
                        f"Translation failed after {_RETRIES} attempts "
                        f"({source} → {target}). This is usually a lost internet "
                        f"connection, or Google rate-limiting the free endpoint — "
                        f"wait a minute and retry. Underlying error: "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
                time.sleep(2 ** attempt)
        for seg, translated in zip(batch, results):
            seg.translated = (translated or "").strip()
