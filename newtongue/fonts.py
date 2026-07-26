"""Find an installed font that can render the target language's script.

Burned-in subtitles are drawn by libass. If the subtitle style names a font
without glyphs for the target script (Arial has no Devanagari, Thai, CJK, ...)
and the ffmpeg build can't do system font fallback — static builds often
can't — every character renders as a tofu box. Naming an installed font that
covers the script, and pointing libass straight at its file via `fontsdir`,
sidesteps both problems.
"""

import os
import platform
from glob import glob
from pathlib import Path

# Writing system per language code; anything missing is Latin-based.
SCRIPTS = {
    "hi": "Devanagari", "th": "Thai", "ar": "Arabic", "ru": "Cyrillic",
    "zh": "CJK (Simplified Chinese)", "zh-TW": "CJK (Traditional Chinese)",
    "ja": "CJK (Japanese)", "ko": "Korean",
}


def _macos_candidates(lang: str) -> list[tuple[str, str]]:
    supp = "/System/Library/Fonts/Supplemental"
    # Arial Unicode MS ships with macOS and covers every script Newtongue dubs into.
    universal = [("Arial Unicode MS", f"{supp}/Arial Unicode.ttf")]
    preferred = {
        "hi": [("Devanagari Sangam MN", f"{supp}/Devanagari Sangam MN.ttc")],
        "th": [("Ayuthaya", f"{supp}/Ayuthaya.ttf")],
    }
    return preferred.get(lang, []) + universal


def _windows_candidates(lang: str) -> list[tuple[str, str]]:
    fonts = str(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")
    by_lang = {
        "hi": [("Nirmala UI", "Nirmala.ttf"), ("Mangal", "mangal.ttf")],
        "th": [("Leelawadee UI", "LeelawUI.ttf"), ("Leelawadee", "Leelawad.ttf"),
               ("Tahoma", "tahoma.ttf")],
        "ar": [("Segoe UI", "segoeui.ttf"), ("Tahoma", "tahoma.ttf")],
        "ru": [("Segoe UI", "segoeui.ttf"), ("Arial", "arial.ttf")],
        "zh": [("Microsoft YaHei", "msyh.ttc"), ("SimSun", "simsun.ttc")],
        "zh-TW": [("Microsoft JhengHei", "msjh.ttc"), ("MingLiU", "mingliu.ttc")],
        "ja": [("Meiryo", "meiryo.ttc"), ("Yu Gothic", "YuGothM.ttc"),
               ("MS Gothic", "msgothic.ttc")],
        "ko": [("Malgun Gothic", "malgun.ttf"), ("Gulim", "gulim.ttc")],
    }
    default = [("Segoe UI", "segoeui.ttf"), ("Arial", "arial.ttf")]
    return [(family, f"{fonts}\\{name}") for family, name in by_lang.get(lang, default)]


def _linux_candidates(lang: str) -> list[tuple[str, str]]:
    # Paths vary by distro, so these are recursive globs (resolved in find_font).
    by_lang = {
        "hi": [("Noto Sans Devanagari", "NotoSansDevanagari*")],
        "th": [("Noto Sans Thai", "NotoSansThai*")],
        "ar": [("Noto Sans Arabic", "NotoSansArabic*"), ("Noto Naskh Arabic", "NotoNaskhArabic*")],
        "zh": [("Noto Sans CJK SC", "NotoSansCJK*")],
        "zh-TW": [("Noto Sans CJK TC", "NotoSansCJK*")],
        "ja": [("Noto Sans CJK JP", "NotoSansCJK*")],
        "ko": [("Noto Sans CJK KR", "NotoSansCJK*")],
    }
    default = [("Noto Sans", "NotoSans-*"), ("DejaVu Sans", "DejaVuSans.ttf")]
    dirs = ["/usr/share/fonts", "/usr/local/share/fonts",
            str(Path.home() / ".local/share/fonts"), str(Path.home() / ".fonts")]
    return [(family, f"{d}/**/{pattern}")
            for family, pattern in by_lang.get(lang, default) for d in dirs]


def find_font(lang: str) -> tuple[str, Path] | None:
    """(font family, font file) able to render `lang`, or None if none is installed."""
    system = platform.system()
    if system == "Darwin":
        candidates = _macos_candidates(lang)
    elif system == "Windows":
        candidates = _windows_candidates(lang)
    else:
        candidates = _linux_candidates(lang)
    for family, pattern in candidates:
        if "*" in pattern:
            matches = glob(pattern, recursive=True)
            if matches:
                return family, Path(sorted(matches)[0])
        elif Path(pattern).exists():
            return family, Path(pattern)
    return None
