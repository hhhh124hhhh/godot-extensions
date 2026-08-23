---
name: video-to-4k
description: >-
  Upscales low-resolution video to 4K with Video2X (Real-ESRGAN), then encodes
  to a unified 3840×2160 H.265 Main10 40Mbps + AAC 320kbps MP4. Source frame
  rate is preserved (no fps=60 duplication, no RIFE). Already-4K sources skip
  Video2X and go straight to FFmpeg. Use when the user wants video-to-4k, 4K
  upscale, UHD export, Video2X, Real-ESRGAN, H.265 Main10, or batch convert
  SD/HD clips to 4K.
---

# Video to 4K

Convert supported videos to a **unified 4K master**:

| Spec | Value |
|------|-------|
| Resolution | 3840×2160 |
| Frame rate | **Source fps kept** (no `fps=` filter, no RIFE) |
| Video | H.265 Main10 (`libx265`, `yuv420p10le`) |
| Video bitrate | 40 Mbps |
| Audio | AAC 320 kbps |
| Container | MP4 (`.mp4`, `hvc1` tag) |

## Pipeline

1. **Probe** with ffprobe (width, height, fps, audio).
2. **Already 4K?** (`width ≥ 3840` and `height ≥ 2160`) → skip Video2X.
3. **Below 4K** → [Video2X](https://github.com/k4yt3x/video2x) Real-ESRGAN upscale (scale 2 or 4) to intermediate under `4k-upscaled/`.
4. **Always** FFmpeg final encode → `4k/` at the unified specs above.

## Rules

When this skill applies, read and follow [skill-dependency-manager](../skill-dependency-manager.md) — run scripts as documented, install missing tools into `.dependency/`.

- Run `convert.py` through **`.dependency/python/python.exe`**. Never use host `python` / `ffmpeg` / `video2x`.
- **Never overwrite sources.** Outputs go under `4k/` (final) and `4k-upscaled/` (Video2X intermediate).
- Use the bundled script — do not hand-write equivalent `video2x` / `ffmpeg` commands.

## Setup (first run)

### FFmpeg + Python

Populate `ffmpeg` and `python` under `.dependency/` per skill-dependency-manager.

### Video2X (CLI)

Download the **CLI** release (not the Qt6 installer) from [video2x releases](https://github.com/k4yt3x/video2x/releases/latest) and extract to `.dependency/video2x/`:

| Platform | Release asset |
|----------|---------------|
| Windows | `video2x-windows-amd64.zip` → `video2x.exe` |
| Linux | `Video2X-x86_64.AppImage` (or distro package) → register as `bin` |

Register in `.dependency/manifest.json`:

```json
"video2x": {
  "populated": true,
  "bin": ".dependency/video2x/video2x.exe"
}
```

Use `video2x` (no `.exe`) or the AppImage path on Unix. Requires a **Vulkan** GPU and AVX2 CPU. Docs: [Command Line](https://docs.video2x.org/running/command-line.html).

## Quick Start

```bash
.dependency/python/python.exe .cursor/skills/video-to-4k/scripts/convert.py path/to/video_or_folder
```

Example:

```
assets/video/clip.mp4
  → assets/video/4k-upscaled/clip.mkv   (Video2X, only if below 4K)
  → assets/video/4k/clip.mp4            (final master)
```

Already-4K source → only `4k/clip.mp4` (FFmpeg only).

Batch with subfolders:

```bash
.dependency/python/python.exe .cursor/skills/video-to-4k/scripts/convert.py Video/Cutscenes -r
```

Anime / cartoon content (Real-ESRGAN anime model):

```bash
.dependency/python/python.exe .cursor/skills/video-to-4k/scripts/convert.py clip.mp4 --anime
```

## Defaults

| Setting | Default | Notes |
|---------|---------|-------|
| Upscaler | Real-ESRGAN `realesrgan-plus` | General / live-action |
| `--anime` | `realesr-animevideov3` | Anime / illustration |
| Scale | Auto 2 or 4 | Smallest factor that meets or exceeds 4K |
| Intermediate | High-bitrate HEVC MKV in `4k-upscaled/` | Kept for re-encode; delete manually or `--clean-upscaled` |
| Final | Always re-encode | Even if source already matches specs |
| Existing `4k/` file | Skipped | Pass `--overwrite` to replace |

## Common Flags

`-r` · `-o` / `--output-dir` · `--upscaled-dir` · `--clean-upscaled` · `--anime` · `--gpu` · `--dry-run` · `--overwrite`

**Never overwrite source files.** Supported inputs: `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`, `.wmv`, `.flv`, `.m4v`, `.mpeg`, `.mpg`, `.ts`, `.mts`, `.m2ts`, `.3gp`, `.ogv`, `.ogg`.

## Agent Notes

1. Use the bundled script only.
2. Missing Python / FFmpeg / Video2X → populate `.dependency/`, set `populated: true`, retry the same command.
3. Tell the user where `4k/` (and `4k-upscaled/` if used) outputs are; they swap assets manually.
4. Default model is **general** (`realesrgan-plus`). Pass `--anime` for anime/cartoon.
5. Do **not** force fps. Keep the source frame rate. Need 60fps interpolation → **video-to-60fps** first (RIFE at source resolution).
6. Pipeline / FFmpeg / Video2X details: [reference.md](reference.md)
