# Video Merge — FFmpeg Notes

## Normalize + xfade

Each input is normalized in the same `filter_complex` before transitions:

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

## Encode

```
-c:v libx265 -profile:v main10 -pix_fmt yuv420p10le
-b:v 40M -maxrate 40M -bufsize 80M
-r 60 -tag:v hvc1
-c:a aac -b:a 320k -ar 48000 -ac 2
```

## Filtergraph size / RAM

Prefer one filtergraph when the clip count is small so quality is not degraded by
repeated H.265 passes. With many 4K Main10 inputs, a single graph can exceed tens
of GB of RAM (`Cannot allocate memory`). `merge.py` therefore caps each encode at
**4 inputs** and recursively merges chunks (boundary transitions preserved).
