---
name: image-remove-watermark-by-lama-inpainting
description: >-
  Removes corner or region watermarks from images with LaMa inpainting (IOPaint):
  feathered circular mask over the mark, then fill from surrounding pixels.
  Use when reverse-alpha Gemini removal leaves a dark remnant, when the user
  wants LaMa / IOPaint / inpaint 去水印 / 局部修复, or for general corner logos
  that are not a semi-transparent Gemini sparkle overlay.
---

# Image Remove Watermark by LaMa Inpainting

Erase a **region watermark** (default: bottom-right corner sparkle) with **[IOPaint](https://github.com/Sanster/IOPaint) LaMa**. Builds a feathered circular mask, then inpaints from surrounding pixels.

**When to use this instead of** [image-remove-watermark-gemini](../image-remove-watermark-gemini/SKILL.md): reverse alpha blending failed (dark remnant, skipped detection) or the mark is an opaque/baked-in corner logo. Prefer the Gemini skill first for typical semi-transparent Gemini sparkles.

## Rules

When this skill applies, read and follow [skill-dependency-manager](../skill-dependency-manager.md) — run scripts as documented, install missing tools into `.dependency/`.

- Run `inpaint.py` through the **`iopaint` manifest entry** (`.dependency/iopaint/.venv/`). Never use host `python`, `py`, `python3`, or any interpreter outside `.dependency/`.
- Do not hand-write `iopaint run` / ImageMagick mask commands — use the bundled script.
- `populated: false` for `iopaint` is not a reason to skip. Install first, set `populated: true`, retry the same command.
- **Never overwrite sources.** Output goes into a `no-watermark/` subfolder beside each source image.
- **Never copy or move input images.** Pass the user's actual file or directory path.
- **Never use Cursor attachment cache paths.** Use the path the user provides (e.g. `C:\Users\...\Downloads\foo.png`) or ask if unclear.

## Setup (first run)

IOPaint needs **Python 3.11** and PyTorch. From project root:

```bash
.dependency/python-3.11/python.exe -m venv .dependency/iopaint/.venv
.dependency/iopaint/.venv/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
.dependency/iopaint/.venv/Scripts/python.exe -m pip install iopaint
```

CPU-only: skip the CUDA torch line and `pip install iopaint` (pulls CPU torch). Use `bin/python` on Unix.

Register in `.dependency/manifest.json`:

```json
"iopaint": {
  "populated": true,
  "bin": ".dependency/iopaint/.venv/Scripts/python.exe"
}
```

LaMa weights (`big-lama.pt`) download on first run.

## Quick Start

**Default: create `<source-dir>/no-watermark/` next to each input file** (never overwrites sources). Default region is bottom-right **96×96** with **64px** inset (Gemini V1 large-logo geometry on 2752×1536 → `(2592, 1376)`), circle radius 48, mask blur 3.

```bash
# Single file — output beside the source
.dependency/iopaint/.venv/Scripts/python.exe .cursor/skills/image-remove-watermark-by-lama-inpainting/scripts/inpaint.py C:\Users\...\Downloads\foo.png

# Directory batch (flat)
.dependency/iopaint/.venv/Scripts/python.exe .cursor/skills/image-remove-watermark-by-lama-inpainting/scripts/inpaint.py image/title-screens

# Recursive batch
.dependency/iopaint/.venv/Scripts/python.exe .cursor/skills/image-remove-watermark-by-lama-inpainting/scripts/inpaint.py image --recursive
```

Explicit box (pixels, `x,y,w,h`):

```bash
.dependency/iopaint/.venv/Scripts/python.exe .cursor/skills/image-remove-watermark-by-lama-inpainting/scripts/inpaint.py image/foo.png \
  --region 2592,1376,96,96
```

CPU:

```bash
.dependency/iopaint/.venv/Scripts/python.exe .cursor/skills/image-remove-watermark-by-lama-inpainting/scripts/inpaint.py image/foo.png \
  --device cpu
```

## How it works

1. Open each image; compute a region box (`br` or `x,y,w,h`).
2. Draw a white circle centered in that box; Gaussian-blur the mask (then binary threshold at 127).
3. Run IOPaint **LaMa** once (model loaded once per batch) on RGB pixels.
4. Write PNG to `no-watermark/` beside the source.

Default `br` box: `x = width - inset - size`, `y = height - inset - size` (`size=96`, `inset=64`).

## Options

| Option | Default | Notes |
|--------|---------|-------|
| Output folder | `<source-dir>/no-watermark/` per image | Sibling folder beside each source file |
| `--output-subdir` | `no-watermark` | Subfolder name beside each source file |
| `--output-dir` | *(none)* | Shared output root under input path |
| `--region` | `br` | `br` or `x,y,w,h` |
| `--size` | `96` | Box size for `br` |
| `--inset` | `64` | Right/bottom margin for `br` |
| `--radius` | half of box | Circle radius in pixels |
| `--blur` | `3` | Mask Gaussian blur |
| `--model` | `lama` | IOPaint model (`lama`, `anime-lama`, …) |
| `--device` | `cuda` | Falls back to `cpu` if CUDA is missing |
| `--pattern` | `*.png` | Also matches `.jpg`, `.jpeg`, `.webp`, `.bmp` |
| `--recursive` | off | Search subdirectories |

## Agent workflow

1. **Confirm source** — user path only; do not copy into `image/` or use chat attachment cache.
2. **Region** — default `br` for Gemini-style bottom-right sparkle. If the mark is elsewhere, crop/inspect and pass `--region x,y,w,h`.
3. **Trial first** — run one file, inspect `<source-dir>/no-watermark/` before a large batch.
4. **Inspect** — check the former watermark area; leftover tips → larger `--radius` or `--size`; leftover box → smaller radius / more `--blur`.
5. **Revert** — delete the output folder; sources are never modified.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `iopaint` missing / not populated | Follow **Setup**; update manifest |
| CUDA not available | Script falls back to `--device cpu` |
| Sparkle still visible | Increase `--radius` or `--size`; confirm `--region` covers the mark |
| Nearby art eaten | Smaller `--radius`; tighter `--region x,y,w,h` |
| Dark remnant after Gemini skill | This skill is the fallback — run it on the **originals**, not the reverse-alpha output |
| Wrong interpreter | Must use `.dependency/iopaint/.venv/Scripts/python.exe` |

## Related

- Script: [scripts/inpaint.py](scripts/inpaint.py)
- Gemini reverse-alpha (try first for sparkle overlays): [image-remove-watermark-gemini](../image-remove-watermark-gemini/SKILL.md)
- Engine: [Sanster/IOPaint](https://github.com/Sanster/IOPaint) (LaMa)
