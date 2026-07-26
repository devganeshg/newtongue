# Example clips

`demo_en.mp4` is the source: a title card with an English narration. Both the visuals
and the narration were generated for this project, so the clip carries no third-party
rights — it exists specifically so the demo can be redistributed freely.

The other files are Newtongue's real output, produced by one command:

```bash
newtongue examples/demo_en.mp4 --to hi,es --subtitles srt,vtt --subtitle-content both
```

| File | What it is |
|---|---|
| `demo_en.mp4` | Source clip, English narration |
| `demo_en_hi.mp4` | Dubbed into Hindi |
| `demo_en_es.mp4` | Dubbed into Spanish |
| `demo_en_hi.srt` / `.vtt` | Hindi subtitles, bilingual (translation above original) |
| `demo_en_es.srt` / `.vtt` | Spanish subtitles, bilingual |

Note the video stream is byte-identical across all three MP4s — Newtongue copies it
untouched and replaces only the audio.

Anything else you drop in this directory is gitignored. Please keep it that way:
only dub videos you have the rights to, and don't commit third-party media here.
