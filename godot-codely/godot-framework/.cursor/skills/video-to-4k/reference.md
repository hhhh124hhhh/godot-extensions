# Video to 4K — Reference

## Decision tree

```
ffprobe source
  ├─ width ≥ 3840 AND height ≥ 2160  →  FFmpeg final only
  └─ otherwise                       →  Video2X upscale → FFmpeg final
```

## Scale factor (Video2X Real-ESRGAN)

Pick the smallest scale the selected Real-ESRGAN model ships (`realesrgan-plus` / `realesrgan-plus-anime`: `{4}` only; `realesr-animevideov3`: `{2, 3, 4}`) such that `width * s ≥ 3840` and `height * s ≥ 2160`. If none is enough (e.g. very low-res), use the model's largest scale and let FFmpeg finish the remaining scale to 3840×2160.

| Source | Scale (`realesrgan-plus`) | After Video2X | FFmpeg |
|--------|---------------------------|---------------|--------|
| 2560×1440 | 4 | 10240×5760 | Downscale to 3840×2160 |
| 1920×1080 | 4 | 7680×4320 | Downscale to 3840×2160 |
| 1280×720 | 4 | 5120×2880 | Downscale to 3840×2160 |
| 640×360 | 4 | 2560×1440 | Upscale remainder to 3840×2160 |

With `--anime` (`realesr-animevideov3`), 1920×1080 / 2560×1440 can use scale `2` because that model ships x2 weights.

## Video2X intermediate (below 4K)

```bash
video2x -i input.mp4 -o 4k-upscaled/clip.mkv \
  -p realesrgan -s 4 \
  --realesrgan-model realesrgan-plus \
  -c libx265 --pix-fmt yuv420p10le \
  -e preset=medium -e crf=12
```

`--anime` swaps the model to `realesr-animevideov3`.

Intermediate aims for quality over size so the final 40 Mbps encode has a clean source. Audio is passed through by Video2X when present.

## FFmpeg final (always)

```bash
ffmpeg -i SOURCE \
  -vf "scale=3840:2160:flags=lanczos,format=yuv420p10le" \
  -c:v libx265 -profile:v main10 -pix_fmt yuv420p10le \
  -b:v 40M -maxrate 40M -bufsize 80M \
  -tag:v hvc1 -x265-params "profile=main10" \
  -c:a aac -b:a 320k \
  -movflags +faststart \
  4k/clip.mp4
```

No `fps=` filter: timestamps and frame count stay with the source. 24fps in → 24fps out.

`SOURCE` is the Video2X intermediate when upscaling ran; otherwise the original file.

No audio streams → video-only output (`-an`).

## Why split Video2X and FFmpeg?

Video2X owns ML upscaling. The unified master (exact 3840×2160, source fps, Main10 @ 40 Mbps, AAC 320k) is enforced in one FFmpeg pass so already-4K and upscaled paths share identical output specs. Frame-rate conversion (RIFE or `fps=`) is out of scope.

## Hardware

Video2X needs Vulkan + AVX2. List GPUs:

```bash
.dependency/video2x/video2x.exe --list-gpus
```

Pass `--gpu N` to the skill script to select device index.
