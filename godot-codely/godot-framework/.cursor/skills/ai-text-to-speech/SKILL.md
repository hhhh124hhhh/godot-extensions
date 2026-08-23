---
name: ai-text-to-speech
description: >-
  Zero-shot text-to-speech with voice cloning via IndexTTS2 (index-tts).
  Synthesizes speech from text using a user-provided reference audio for timbre.
  Use when the user wants TTS, text-to-speech, 文本转语音, voice clone, 音色克隆,
  IndexTTS, IndexTTS2, or generating narration/voice lines from a reference WAV.
---

# AI Text-to-Speech (IndexTTS2)

Clone a speaker from a **reference audio**, then synthesize speech from **text** with **[IndexTTS2](https://github.com/index-tts/index-tts)**.

## Rules

When this skill applies, read and follow [skill-dependency-manager](../skill-dependency-manager.md) — run scripts as documented, install missing tools into `.dependency/`.

- Run `tts.py` through the **`index-tts` manifest entry** (`.dependency/index-tts/.venv/`). Never use host `python`, `py`, `python3`, or any interpreter outside `.dependency/`.
- Do not hand-write IndexTTS Python snippets or `uv run webui.py` for synthesis — use the bundled script.
- IndexTTS **requires `uv`** for install (`pip`/`conda` are unsupported upstream). Python must be **`>=3.10,<3.12`** (use **`python-3.11`**).
- `populated: false` for `index-tts` (or missing models) is not a reason to skip. Install / download first, set `populated: true`, retry the same command.
- **Never overwrite sources.** Pass the user's real voice path and text; write only to `-o` / `--output`.
- **Never use Cursor attachment cache paths** under `.cursor/projects/.../assets/` as the voice source — use the path the user provides.

## Setup (first run)

From project root.

### 1. Python 3.11 + uv

Ensure `python-3.11` and `uv` are populated under `.dependency/` (see skill-dependency-manager). Register:

```json
"python-3.11": {
  "populated": true,
  "bin": ".dependency/python-3.11/python.exe"
},
"uv": {
  "populated": true,
  "bin": ".dependency/uv/uv.exe"
}
```

Use `python` / `uv` (no `.exe`) on Unix.

### 2. Clone IndexTTS

```bash
git clone https://github.com/index-tts/index-tts.git .dependency/index-tts
cd .dependency/index-tts
git lfs install
git lfs pull
```

### 3. Install deps with uv (required)

```bash
# from .dependency/index-tts
# Windows: skip deepspeed extras if install fails
.dependency/uv/uv.exe sync --extra webui
```

Slow PyPI (China mirrors):

```bash
.dependency/uv/uv.exe sync --extra webui --default-index "https://mirrors.aliyun.com/pypi/simple"
```

CUDA Toolkit **12.8+** is needed for GPU. CPU works but is slow.

### 4. Download IndexTTS-2 checkpoints

```bash
cd .dependency/index-tts
.dependency/uv/uv.exe tool install "huggingface-hub[cli,hf_xet]"
hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints
```

Or ModelScope:

```bash
.dependency/uv/uv.exe tool install "modelscope"
modelscope download --model IndexTeam/IndexTTS-2 --local_dir checkpoints
```

If HuggingFace is slow: `HF_ENDPOINT=https://hf-mirror.com` (Unix) / `$env:HF_ENDPOINT="https://hf-mirror.com"` (PowerShell).

### 5. Register manifest

```json
"index-tts": {
  "populated": true,
  "bin": ".dependency/index-tts/.venv/Scripts/python.exe"
}
```

Use `.dependency/index-tts/.venv/bin/python` on Unix. Confirm `checkpoints/config.yaml` exists before synthesizing.

## Quick Start

**Voice reference + text → WAV** (default output: `<voice-dir>/tts/speech.wav`):

```bash
.dependency/index-tts/.venv/Scripts/python.exe .cursor/skills/ai-text-to-speech/scripts/tts.py \
  --voice audio/voice/ref.wav \
  --text "你好，欢迎来到这个世界。"
# → audio/voice/tts/speech.wav
```

Explicit output path:

```bash
.dependency/index-tts/.venv/Scripts/python.exe .cursor/skills/ai-text-to-speech/scripts/tts.py \
  --voice audio/voice/ref.wav \
  --text "Hello, this is a test." \
  --output audio/voice/tts/hello.wav
```

Long script from a UTF-8 text file:

```bash
.dependency/index-tts/.venv/Scripts/python.exe .cursor/skills/ai-text-to-speech/scripts/tts.py \
  --voice audio/voice/ref.wav \
  --text-file script/lines/intro.txt \
  --output audio/voice/tts/intro.wav
```

FP16 (faster, less VRAM):

```bash
.dependency/index-tts/.venv/Scripts/python.exe .cursor/skills/ai-text-to-speech/scripts/tts.py \
  --voice audio/voice/ref.wav \
  --text "测试半精度推理。" \
  --fp16
```

## Emotion control (optional)

| Mode | Flags | Notes |
|------|-------|-------|
| Emotion reference audio | `--emotion-audio path.wav` | Separate clip for emotion; timbre still from `--voice` |
| Emotion weight | `--emotion-weight 0.6` | Maps to `emo_alpha` (`0.0`–`1.0`, default `1.0`) |
| Emotion from text | `--emotion-from-text` | Infer emotion from synthesis text; prefer `--emotion-weight` ≈ `0.6` |
| Emotion description | `--emotion-text "..."` | Natural-language emotion; implies text emotion mode |
| Emotion vector | `--emotion-vector 0,0,0.8,0,0,0,0,0` | 8 floats: happy, angry, sad, afraid, disgusted, melancholic, surprised, calm |

```bash
# Emotion reference audio
.dependency/index-tts/.venv/Scripts/python.exe .cursor/skills/ai-text-to-speech/scripts/tts.py \
  --voice audio/voice/ref.wav \
  --emotion-audio audio/voice/emo_sad.wav \
  --emotion-weight 0.9 \
  --text "酒楼丧尽天良，开始借机竞拍房间。" \
  --output audio/voice/tts/sad_line.wav

# Emotion description text
.dependency/index-tts/.venv/Scripts/python.exe .cursor/skills/ai-text-to-speech/scripts/tts.py \
  --voice audio/voice/ref.wav \
  --emotion-text "害怕、紧张" \
  --emotion-weight 0.6 \
  --text "快躲起来！是他要来了！" \
  --output audio/voice/tts/afraid_line.wav
```

Do not combine `--emotion-audio`, `--emotion-vector`, and `--emotion-text` / `--emotion-from-text` in conflicting ways — pick one emotion source.

## Defaults

| Option | Default | Notes |
|--------|---------|-------|
| Output | `<voice-dir>/tts/speech.wav` | Auto-create `tts/`; use `--output` to override |
| Model | `.dependency/index-tts/checkpoints` | IndexTTS-2 |
| `--fp16` | off | Enable on GPU when VRAM is tight |
| `--emotion-weight` | `1.0` | Lower (~0.6) for text emotion modes |
| Overwrite | off | Pass `--force` to replace an existing output |

## Agent workflow

1. **Confirm inputs** — need a clear reference voice WAV/MP3 and the text (or `--text-file`). Ask if either is missing.
2. **Use the user's real paths** — do not copy voice files into the repo unless asked.
3. **Trial first** — synthesize one short line, play/inspect before long scripts.
4. **Reference audio tips** — clean, single-speaker, little noise; a few seconds of clear speech works best.
5. **Missing install** — follow **Setup**; register `index-tts` in `manifest.json`; retry the same command.
6. **GPU** — prefer CUDA + `--fp16` for speed; CPU is acceptable for short tests only.
7. **Revert** — delete files under `tts/`; sources are never modified.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `index-tts` not populated | Clone + `uv sync` + download checkpoints; update manifest |
| `checkpoints/config.yaml` missing | Re-run `hf download IndexTeam/IndexTTS-2 --local-dir=checkpoints` |
| CUDA / torch errors | Install CUDA 12.8+; or run on CPU (slow) |
| OOM / VRAM | Pass `--fp16`; shorten text; close other GPU apps |
| Slow HuggingFace | Set `HF_ENDPOINT=https://hf-mirror.com`; or use ModelScope |
| `uv sync` / DeepSpeed fail on Windows | Use `uv sync --extra webui` without deepspeed |
| Unnatural emotion | Lower `--emotion-weight` to ~0.6; try a clearer `--emotion-audio` |

## Related

- Upstream: https://github.com/index-tts/index-tts
- Models: [IndexTTS-2 (HuggingFace)](https://huggingface.co/IndexTeam/IndexTTS-2)
- Post-process loudness / format: [audio-loudness-normalization](../audio-loudness-normalization/SKILL.md), [audio-to-ogg](../audio-to-ogg/SKILL.md), [audio-to-wav](../audio-to-wav/SKILL.md)
