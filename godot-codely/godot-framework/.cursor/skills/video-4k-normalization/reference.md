# Video 4K Normalization — Reference

## Decision tree

```
ffprobe source
  ├─ HDR? (PQ / HLG / BT.2020 primaries or transfer)
  │    → tonemap (hable) → BT.709 SDR → scale 3840×2160 → fps=60 → encode
  └─ else (SDR / unknown)
       → scale 3840×2160 → fps=60 → format yuv420p10le → encode
           + write BT.709 / tv color tags
```

## HDR detection

Treat as HDR when any of these hold (case-insensitive):

| Field | Values |
|-------|--------|
| `color_transfer` | `smpte2084`, `arib-std-b67`, `smpte2084` (PQ), HLG |
| `color_primaries` | `bt2020` |
| `color_space` | `bt2020nc`, `bt2020c` |
| Side data | Mastering display / content light level metadata present |

Otherwise use the SDR path (still force BT.709 tags on output).

## FFmpeg — SDR path

```bash
ffmpeg -i SOURCE \
  -vf "scale=3840:2160:flags=lanczos,fps=60,format=yuv420p10le" \
  -c:v libx265 -profile:v main10 -pix_fmt yuv420p10le \
  -b:v 40M -maxrate 40M -bufsize 80M \
  -tag:v hvc1 \
  -x265-params "profile=main10:colorprim=bt709:transfer=bt709:colormatrix=bt709" \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -c:a aac -b:a 320k \
  -movflags +faststart \
  normalized/clip.mp4
```

## FFmpeg — HDR → SDR path

Tone-map at source resolution, then scale/fps:

```bash
ffmpeg -i SOURCE \
  -vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p10le,scale=3840:2160:flags=lanczos,fps=60" \
  -c:v libx265 -profile:v main10 -pix_fmt yuv420p10le \
  -b:v 40M -maxrate 40M -bufsize 80M \
  -tag:v hvc1 \
  -x265-params "profile=main10:colorprim=bt709:transfer=bt709:colormatrix=bt709" \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -c:a aac -b:a 320k \
  -movflags +faststart \
  normalized/clip.mp4
```

No audio → `-an`.

## vs video-to-4k

| | `video-4k-normalization` | `video-to-4k` |
|--|--------------------------|---------------|
| Below 4K | FFmpeg lanczos | Video2X Real-ESRGAN |
| Color | Force BT.709 SDR (+ HDR tone map) | Final encode only (no explicit color conform) |
| Goal | Merge-safe unified 4K masters | Quality upscale + same bitrate/size/fps |

Typical storyboard flow: upscale with `video-to-4k` if needed → `video-4k-normalization` if HDR/SDR still mixed → `video-merge` hard-cut.

## vs video-merge

`video-merge` never re-encodes. If concat looks wrong (saturation jump) or `-c copy` fails, run this skill on the sources, then merge `normalized/`.
