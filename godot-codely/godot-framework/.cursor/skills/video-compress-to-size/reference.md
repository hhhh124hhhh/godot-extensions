# Video Compress To Size — Reference

## Encoder Selection

At startup the script probes a 2-frame encode for each candidate (in order) and picks the first that succeeds:

| Preference | H.264 | HEVC (`--hevc`) |
|------------|-------|-----------------|
| 1 | `h264_nvenc` | `hevc_nvenc` |
| 2 | `h264_amf` | `hevc_amf` |
| 3 | `h264_qsv` | `hevc_qsv` |
| 4 | `libx264` (CPU two-pass) | `libx265` (CPU two-pass) |

`--cpu` skips probes and forces the software encoder.

Decode accel (best-effort, falls back to software decode if it fails):

| Encoder | `-hwaccel` |
|---------|------------|
| NVENC | `cuda` |
| QSV | `qsv` |
| AMF | `d3d11va` |

## Size Budget → Bitrate

```
budget_bits = S * 8 * M
video_bitrate = max(0, budget_bits / T - A)
```

| Path | Safety `M` |
|------|------------|
| GPU VBR | `0.90` |
| CPU two-pass | `0.92` |

## GPU Path (single-pass VBR)

```bash
ffmpeg -y -hwaccel cuda -i input \
  -map 0:v:0 -c:v h264_nvenc -rc vbr -b:v {V} -maxrate {V*1.05} -bufsize {2V} \
  -preset p4 -multipass fullres \
  -map 0:a:0? -c:a aac -b:a 128k -movflags +faststart output.mp4
```

AMF uses `-rc vbr_peak` + `-quality`; QSV uses `-maxrate` / `-bufsize` / `-preset`.

## CPU Path (two-pass)

```bash
ffmpeg -y -i input -c:v libx264 -b:v {V} -pass 1 -an -f null NUL
ffmpeg -y -i input -c:v libx264 -b:v {V} -pass 2 -c:a aac -b:a {A} output.mp4
```

## Preset Mapping

| User `--preset` | NVENC | AMF | QSV / CPU |
|-----------------|-------|-----|-----------|
| ultrafast / superfast | p1 | speed | veryfast |
| veryfast | p2 | speed | veryfast |
| faster / fast | p3 | balanced / speed | faster / fast |
| medium (default) | p4 | balanced | medium |
| slow | p5 | quality | slow |
| slower / veryslow | p6 / p7 | quality | slower / veryslow |

NVENC also accepts raw `p1`…`p7`.

## Retry When Over Limit

If `output_size > S`, scale bitrate by `(S * M) / output_size` and re-encode (up to 3 attempts).

## Notes

- Outputs are always `.mp4`.
- Resolution and frame rate are preserved.
- GPU VBR is faster but slightly less size-accurate than CPU two-pass; the safety margin and retry loop compensate.
- 10-bit sources (e.g. HEVC Main10) are converted to **8-bit `yuv420p`** for H.264/HEVC GPU encoders that lack 10-bit encode support.
