# Video Merge GPU — FFmpeg Notes

## Normalize + xfade

CPU filtergraph (same as `video-merge`). Each input is normalized before transitions:

```
scale=3840:2160:force_original_aspect_ratio=decrease
pad=3840:2160:(ow-iw)/2:(oh-ih)/2:black
fps=60
format=yuv420p10le
setpts=PTS-STARTPTS
```

Audio:

```
aformat=sample_rates=48000:channel_layouts=stereo
aresample=48000
asetpts=PTS-STARTPTS
```

Clips with no audio stream get a matching silent stereo track (`anullsrc`).

## Duration-preserving transitions

Plain `xfade` overlaps by `T` and shortens the timeline by `T` per cut. To keep
**output duration = sum(source durations)**, pad the outgoing side before each cut:

```
tpad=stop_mode=clone:stop_duration=T   # freeze last frame
apad=pad_dur=T                         # pad silence for acrossfade
```

Transition duration `T = 0.5`. For clips with durations `d0, d1, …`:

- Before cut `i`, pad the current chain by `T`
- Cut offset = cumulative **content** length so far (`sum(d[0..i])`) — transition runs over the freeze/silence pad
- After cut `i`, cumulative content length = `sum(d[0..i+1])` (no `-T`)

Audio uses `acrossfade=d=0.5:c1=tri:c2=tri` on the padded streams in the same order.

## GPU encoder (no CPU fallback)

At startup the script probes a short HEVC Main10 encode and picks the first that succeeds:

| Preference | Codec | Typical GPU |
|------------|-------|-------------|
| 1 | `hevc_nvenc` | NVIDIA NVENC |
| 2 | `hevc_amf` | AMD AMF |
| 3 | `hevc_qsv` | Intel QSV |

If all three fail, the script exits. There is **no** `libx265` path.

Probe uses ≥320×240, `-profile:v main10`, and tries `p010le` then `yuv420p10le`.

xfade has no CUDA equivalent, so decode + filters stay on CPU. Do **not** add `-hwaccel` (it fights `filter_complex`).

## Encode

NVENC:

```
-c:v hevc_nvenc -profile:v main10 -pix_fmt p010le
-rc vbr -b:v 40M -maxrate 40M -bufsize 80M
-preset p4 -multipass fullres
-r 60 -tag:v hvc1
-c:a aac -b:a 320k -ar 48000 -ac 2
```

AMF uses `-rc vbr_peak` + `-quality balanced`. QSV uses `-preset medium`. Pixel format is whatever the probe accepted (`p010le` preferred).

## Filtergraph size / RAM

Prefer one filtergraph when the clip count is small so quality is not degraded by
repeated HEVC passes. With many 4K Main10 inputs, a single graph can exceed tens
of GB of RAM (`Cannot allocate memory`). `merge.py` therefore caps each encode at
**4 inputs** and recursively merges chunks (boundary transitions preserved).
