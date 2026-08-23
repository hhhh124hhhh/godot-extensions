---
name: video-merge
description: >-
  Merges multiple videos from a folder (sorted by filename) into one clip with a
  random xfade transition (0.5s) between each pair; freeze-pads so total duration
  equals the sum of sources. Exports 3840×2160 60fps H.265 Main10 40Mbps + AAC
  320kbps. Use when the user wants video merge, concatenate videos, 视频拼接,
  过场动画, xfade, join clips, or batch stitch clips with transitions.
disable-model-invocation: true
---

# Video Merge

Concatenate every video in a folder (filename sort) into **one** high-quality MP4. Between each pair, pick a **random** FFmpeg `xfade` transition (0.5s). Audio uses matching `acrossfade`.

**Duration is preserved:** each cut freeze-pads the outgoing clip by 0.5s (last frame + silence) before the overlap, so output length equals the sum of source clip durations (not shortened by transitions).

## Rules

When this skill applies, read and follow [skill-dependency-manager](../skill-dependency-manager.md) — run scripts as documented, install missing tools into `.dependency/`.

## Quick Start

```bash
.dependency/python/python .cursor/skills/video-merge/scripts/merge.py path/to/clips
```

Example:

```
assets/shots/
  01.mp4
  02.mp4
  03.mp4
→ assets/shots/merged/shots.mp4
```

## Output Spec (fixed)

| Setting | Value |
|---------|-------|
| Resolution | 3840×2160 (scale + letterbox pad) |
| Frame rate | 60 fps |
| Video | H.265 Main10 (`libx265`, `yuv420p10le`) @ **40 Mbps** |
| Audio | AAC **320 kbps**, 48 kHz stereo |
| Transition | **0.5 s**, random from the pool below (freeze-pad; duration preserved) |
| Container | `.mp4` (`hvc1` tag) |

## Transition Pool (random per cut)

`fade` · `dissolve` · `wipeleft` · `wiperight` · `wipeup` · `wipedown` · `slideleft` · `slideright` · `circlecrop` · `pixelize` · `distance` · `radial` · `smoothleft` · `smoothright` · `circleopen` · `circleclose` · `diagtl` · `diagtr` · `hblur` · `zoomin`

Each cut independently samples one transition. Printed in the run log.

## Common Flags

`-o` / `--output` · `--overwrite` · `--dry-run` · `--seed`

```bash
.dependency/python/python .cursor/skills/video-merge/scripts/merge.py clips --seed 42
.dependency/python/python .cursor/skills/video-merge/scripts/merge.py clips -o out/final.mp4 --overwrite
```

**Never overwrite source files.** Default output: `<folder>/merged/<folder-name>.mp4`. Only top-level videos in the folder (no recurse). Supported: `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`, `.wmv`, `.flv`, `.m4v`, `.mpeg`, `.mpg`, `.ts`, `.mts`, `.m2ts`, `.3gp`, `.ogv`, `.ogg`.

## Agent Notes

1. Use the bundled script — do **not** hand-write `ffmpeg` xfade chains.
2. Transition duration is fixed at **0.5s** — no duration override flag.
3. Every clip **except the first** must be **longer than 0.5s** (incoming side of `xfade`).
4. Single file in the folder → re-encode to the output spec with no transition.
5. Many clips (4K10) auto-chunk (max 4 inputs per filtergraph) to avoid OOM; transitions stay correct across chunk boundaries.
6. Missing Python/FFmpeg → populate `.dependency/` per skill-dependency-manager, retry.
7. FFmpeg filter details: [reference.md](reference.md)
