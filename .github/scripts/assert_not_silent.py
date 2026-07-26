"""Fail if ffmpeg's volumedetect output describes a silent track.

Used by the live end-to-end CI job: the dub can "succeed" (a well-formed mp4
appears) while every TTS segment quietly failed, leaving pure silence. Only the
measured volume catches that.

Usage: assert_not_silent.py <volumedetect-output-file>
"""

import re
import sys

# -91 dBFS is digital silence for 16-bit audio; real speech sits far above it.
SILENCE_DBFS = -80.0


def main(path: str) -> int:
    text = open(path, encoding="utf-8", errors="replace").read()
    match = re.search(r"mean_volume:\s*(-?[\d.]+) dB", text)
    if not match:
        print(f"error: no volumedetect output found in {path}", file=sys.stderr)
        return 1

    mean = float(match.group(1))
    if mean <= SILENCE_DBFS:
        print(f"error: dubbed audio is silent ({mean} dB) — every TTS segment "
              f"probably failed", file=sys.stderr)
        return 1

    print(f"dubbed audio mean volume: {mean} dB")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
