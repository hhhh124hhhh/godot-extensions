---
name: storyboard-tts
description: >-
  Converts storyboard markdown (bilingual Chinese + English narration per shot)
  into speech audio via IndexTTS2 (same stack as ai-text-to-speech). Batch-writes
  WAVs under Chinese/ and English/ named by shot id (model loaded once), pads
  0.4 s edge silence in place, then a speech-timeline.md and one concatenated
  SRT per language (Chinese.srt / English.srt). Use when the user wants
  storyboard TTS, 分镜转语音, 旁白配音, storyboard-to-speech, bilingual VO export,
  subtitles, 字幕, or batch TTS from a storyboard.md.
---

# Storyboard TTS

Take a **[storyboard](../storyboard/SKILL.md)** deliverable and batch-synthesize **Chinese + English** voice-over with IndexTTS2 (shared setup with **[ai-text-to-speech](../ai-text-to-speech/SKILL.md)**).

| Output | Path |
|--------|------|
| Chinese VO | `<storyboard-dir>/<voice-stem>/Chinese/<shot-id>.wav` |
| English VO | `<storyboard-dir>/<voice-stem>/English/<shot-id>.wav` |
| Duration doc | `<storyboard-dir>/<voice-stem>/speech-timeline.md` |
| Chinese subs | `<storyboard-dir>/<voice-stem>/Chinese.srt` |
| English subs | `<storyboard-dir>/<voice-stem>/English.srt` |

Shot id from headers (`### Shot 01 — …` → `01.wav`).

Subtitles: **one SRT per language**. Shots are laid end-to-end on the VO timeline (shot N starts when N−1 ends). Inside a shot, text is split on sentence punctuation (`。！？；…` / `.!?`) into multiple cues; cue lengths share that shot’s WAV duration by **non-whitespace character weight**. Skip `(no VO)` / missing audio.

## Rules

1. Follow [skill-dependency-manager](../skill-dependency-manager.md).
2. **Batch synthesis only via** `scripts/synthesize.py` with the **`index-tts`** interpreter. Do **not** hand-write IndexTTS loops, temporary batch drivers, or N× single `tts.py` calls for a full storyboard.
3. **Trial / single-line** checks may use [ai-text-to-speech](../ai-text-to-speech/SKILL.md) `tts.py`, or `synthesize.py --limit 1`.
4. Parse-only / report-only / subtitle-only steps use stdlib **`python`** (`.dependency/python/python`).
5. Never overwrite the storyboard source. Write only under `<audio-dir>/`.
6. Skip `(no VO)` / empty lines — no empty WAVs or empty subtitle cues.
7. Confirm **voice reference** (and output dir if unclear) before a full batch.
8. 第一层目录使用音频的名字作为第一层目录的名字。子目录的名字都是不变. Default `<audio-dir>` is `<storyboard-dir>/<voice-stem>/`. Do **not** use `<storyboard-stem>-speech`.

## Inputs

| Required | Notes |
|----------|--------|
| Storyboard `.md` | `### Shot NN — title` with `- **Chinese:**` / `- **English:**` |
| Reference voice | WAV/MP3 for IndexTTS (`--voice`, or `--voice-zh` / `--voice-en`) |

| Optional | Default |
|----------|---------|
| Output dir | `<storyboard-dir>/<voice-stem>/` (reference audio filename, no extension) |
| Language | both (`--lang chinese` / `english`) |
| `--fp16` / emotion / `--device` | same meaning as ai-text-to-speech |
| `--force` | off (skip existing WAVs) |
| `--limit N` | 0 = all jobs (use `1` for trial) |
| `--report` | write `speech-timeline.md` + `Chinese.srt` / `English.srt` after synth |
| `--no-subtitles` | with `--report`, skip SRT files |
| Edge pad | on (`0.4` s); `--no-pad` / `--pad-duration` / `--pad-threshold` |

## Layout

```
<storyboard-dir>/<voice-stem>/   # e.g. 哪吒-自己-快/ from 哪吒-自己-快.wav
  Chinese/
    01.wav
    …
  English/
    01.wav
    …
  shots.json
  speech-timeline.md
  Chinese.srt            # all Chinese cues, continuous timeline
  English.srt            # all English cues, continuous timeline
  _text/                 # only with --write-text
```

## Workflow

```
Task Progress:
- [ ] Confirm storyboard path + voice (+ audio-dir if needed)
- [ ] Ensure index-tts populated (ai-text-to-speech Setup if missing)
- [ ] Ensure ffmpeg populated (needed for in-place edge padding)
- [ ] Optional trial: synthesize.py --limit 1 --fp16
- [ ] Full batch: synthesize.py --fp16 --report
- [ ] Chat: audio-dir, shot count, totals from speech-timeline.md, SRT paths
```

### One command (preferred)

From project root (Windows; use `.venv/bin/python` on Unix):

```bash
.dependency/index-tts/.venv/Scripts/python.exe \
  .cursor/skills/storyboard-tts/scripts/synthesize.py \
  --storyboard path/to/storyboard.md \
  --voice path/to/ref.wav \
  --fp16 --report
```

Writes under `<storyboard-dir>/<voice-stem>/` (override with `--audio-dir` only when needed).

This will:

1. Parse the storyboard → `<audio-dir>/shots.json`
2. Load IndexTTS2 **once**
3. Write `Chinese/<id>.wav` and `English/<id>.wav` (skip existing unless `--force`)
4. Pad each WAV in place to **0.4 s** leading/trailing silence (`--no-pad` to skip)
5. Write `speech-timeline.md` and `Chinese.srt` / `English.srt` when `--report`

### Trial one line

```bash
.dependency/index-tts/.venv/Scripts/python.exe \
  .cursor/skills/storyboard-tts/scripts/synthesize.py \
  --storyboard path/to/storyboard.md \
  --voice path/to/ref.wav \
  --fp16 --limit 1
```

### Separate voices / language

```bash
# Chinese and English different refs
--voice-zh path/to/zh_ref.wav --voice-en path/to/en_ref.wav

# Only Chinese track
--lang chinese
```

### Parse, report, or subtitles alone (stdlib python)

```bash
.dependency/python/python .cursor/skills/storyboard-tts/scripts/parse_storyboard.py \
  path/to/storyboard.md -o path/to/<audio-dir>/shots.json

.dependency/python/python .cursor/skills/storyboard-tts/scripts/duration_report.py \
  --storyboard path/to/storyboard.md \
  --audio-dir path/to/<audio-dir> \
  --shots path/to/<audio-dir>/shots.json \
  -o path/to/<audio-dir>/speech-timeline.md

# Subtitles only (after WAVs exist) — one Chinese.srt + one English.srt
.dependency/python/python .cursor/skills/storyboard-tts/scripts/write_subtitles.py \
  --audio-dir path/to/<audio-dir> \
  --shots path/to/<audio-dir>/shots.json
```

Resume from an existing `shots.json`:

```bash
.dependency/index-tts/.venv/Scripts/python.exe \
  .cursor/skills/storyboard-tts/scripts/synthesize.py \
  --shots path/to/<audio-dir>/shots.json \
  --voice path/to/ref.wav \
  --fp16 --report
```

## Flags (synthesize.py)

| Flag | Notes |
|------|--------|
| `--storyboard` / `--shots` | Source (one required) |
| `--audio-dir` | Output root (default: `<storyboard-dir>/<voice-stem>/`) |
| `--voice` | Shared speaker ref |
| `--voice-zh` / `--voice-en` | Per-language refs |
| `--lang` | `both` (default), `chinese`, `english` |
| `--limit N` | First N pending jobs only |
| `--force` | Overwrite existing WAVs |
| `--report` | Write timeline + SRT subtitles |
| `--report-out` | Custom timeline path |
| `--no-subtitles` | Skip SRT when using `--report` |
| `--write-text` | Dump lines under `_text/` |
| `--no-pad` | Skip in-place 0.4 s edge padding (off by default — padding is on) |
| `--pad-duration` | Target silence per edge in seconds (default: `0.4`) |
| `--pad-threshold` | Silence detect threshold in dB (default: `-50`) |
| `--fp16` / `--device` | Runtime |
| `--emotion-*` / `--random` / `--verbose` | Same role as `tts.py` |

On partial failure: script continues remaining jobs, prints `Failed jobs: …`, exit code `1`. Fix install/voice per ai-text-to-speech troubleshooting, re-run (existing OK files are skipped).

## Agent notes

1. Do **not** invent narration — use storyboard Chinese/English fields as-is (audio and subtitles).
2. Prefer **one** `synthesize.py` invocation for a full board; model reload cost is the reason.
3. Chat summary: `audio-dir` (`<storyboard-dir>/<voice-stem>/`), counts, path to `speech-timeline.md`, `Chinese.srt` / `English.srt`, Chinese/English total seconds — no full transcripts unless asked. Omit `--audio-dir` unless overriding.
4. IndexTTS install lives in [ai-text-to-speech](../ai-text-to-speech/SKILL.md); do not duplicate Setup here beyond “populate index-tts if missing”.
5. Edge padding is **built in** (default 0.4 s, in place via `scripts/pad.py`). Use `--no-pad` only when they want raw TTS with no extra silence; `--pad-duration` if they want a different length.
6. Loudnorm / OGG / trim remain separate skills after this one.
7. If audio already exists and only subtitles are needed, run `write_subtitles.py` alone (stdlib python). Re-running `synthesize.py --report` without `--force` still pads existing WAVs, then rewrites the timeline/SRT.

## Related

- [storyboard](../storyboard/SKILL.md) — source markdown
- [ai-text-to-speech](../ai-text-to-speech/SKILL.md) — single-line TTS + IndexTTS setup
- Optional after: [audio-loudness-normalization](../audio-loudness-normalization/SKILL.md)
