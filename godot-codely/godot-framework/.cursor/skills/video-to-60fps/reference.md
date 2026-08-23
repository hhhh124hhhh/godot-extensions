# Video to 60fps — Reference

## Decision tree

```
ffprobe source fps
  ├─ |fps − 60| ≤ 0.5   → skip (already ~60, including 59.94)
  ├─ fps > 60.5         → FFmpeg fps=60 drop → 60fps/*.mp4
  └─ fps < 59.5         → Video2X RIFE ×m → FFmpeg 60fps MP4
```

## RIFE multiplier (`-m`)

Video2X only accepts an **integer** frame-rate multiplier, not a target fps.

Pick the smallest `m ≥ 2` such that `src_fps × m` is within 0.5 of 60 when rounding works; otherwise `ceil(60 / src_fps)`:

| Source | `-m` | After RIFE | FFmpeg |
|--------|------|------------|--------|
| 30 / 29.97 | 2 | 60 / 59.94 | remux (already ~60) |
| 24 / 23.976 | 3 | 72 / ~72 | `fps=60` (drop extras) |
| 25 | 3 | 75 | `fps=60` |
| 15 | 4 | 60 | remux |
| 50 | 2 | 100 | `fps=60` |

Do not use FFmpeg `fps=60` on the **source** when fps < 60 — that duplicates frames. RIFE generates intermediate frames first.

## Video2X interpolate (below 60)

```bash
video2x -i input.mp4 -o tmp.mkv \
  -p rife -m 3 --rife-model rife-v4.6 \
  -c libx265 --pix-fmt yuv420p10le \
  -e preset=medium -e crf=12
```

`--rife-uhd` when width ≥ 1920 (or `--uhd`). Audio/subtitles are copied by Video2X unless `--no-copy-streams`.

## FFmpeg final

Already ~60 after RIFE (stream copy to MP4):

```bash
ffmpeg -i tmp.mkv -c:v copy -tag:v hvc1 -c:a aac -b:a 320k -movflags +faststart 60fps/clip.mp4
```

Need an exact 60 (or source was above 60):

```bash
ffmpeg -i SOURCE \
  -vf "fps=60,format=yuv420p10le" \
  -c:v libx265 -profile:v main10 -pix_fmt yuv420p10le \
  -crf 12 -preset medium -tag:v hvc1 \
  -c:a aac -b:a 320k \
  -movflags +faststart \
  60fps/clip.mp4
```

No audio streams → `-an`. Resolution is never scaled.

## Order vs video-to-4k

Interpolate at source resolution, then upscale. RIFE on 4K is much heavier; Real-ESRGAN detail is not temporally stable and confuses optical flow.

## Hardware

Video2X needs Vulkan + AVX2. List GPUs:

```bash
.dependency/video2x/video2x.exe --list-gpus
```

Pass `--gpu N` to the skill script to select device index.
