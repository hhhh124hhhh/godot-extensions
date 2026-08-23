#!/usr/bin/env python3
"""Merge folder videos (filename sort) with random 0.5s xfade into 4K60 GPU HEVC Main10."""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".wmv",
    ".flv",
    ".m4v",
    ".mpeg",
    ".mpg",
    ".ts",
    ".mts",
    ".m2ts",
    ".3gp",
    ".ogv",
    ".ogg",
}

TRANSITION_DURATION = 0.5
OUTPUT_WIDTH = 3840
OUTPUT_HEIGHT = 2160
OUTPUT_FPS = 60
VIDEO_BITRATE = "40M"
AUDIO_BITRATE = "320k"
AUDIO_RATE = 48000
# One filtergraph with many 4K10 streams OOMs (~50GB+). Cap inputs per encode.
MAX_INPUTS_PER_GRAPH = 8

TRANSITIONS = (
    "fade",
    "dissolve",
    "wipeleft",
    "wiperight",
    "wipeup",
    "wipedown",
    "slideleft",
    "slideright",
    "circlecrop",
    "pixelize",
    "distance",
    "radial",
    "smoothleft",
    "smoothright",
    "circleopen",
    "circleclose",
    "diagtl",
    "diagtr",
    "hblur",
    "zoomin",
)


@dataclass(frozen=True)
class EncoderChoice:
    name: str  # ffmpeg -c:v name
    kind: str  # nvenc | amf | qsv
    label: str
    pix_fmt: str


def find_repo_root(start: Path) -> Path | None:
    for parent in [start.resolve(), *start.resolve().parents]:
        if (parent / ".dependency" / "manifest.json").is_file():
            return parent
    return None


def resolve_executable(path: Path) -> Path:
    if path.is_file():
        return path
    if sys.platform == "win32" and path.suffix.lower() != ".exe":
        candidate = path.with_name(f"{path.name}.exe")
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(path)


def resolve_tool_bin(repo_root: Path, tool_name: str) -> Path:
    manifest_path = repo_root / ".dependency" / "manifest.json"
    entry = json.loads(manifest_path.read_text(encoding="utf-8")).get(tool_name)
    if not entry:
        print(
            f"Tool '{tool_name}' not found in .dependency/manifest.json. "
            "See .cursor/skills/skill-dependency-manager.md",
            file=sys.stderr,
        )
        sys.exit(1)
    if not entry.get("populated", False):
        print(
            f"Tool '{tool_name}' is not populated. "
            f"Install it under {repo_root / '.dependency' / tool_name} and set populated: true "
            "in .dependency/manifest.json.",
            file=sys.stderr,
        )
        sys.exit(1)

    bin_rel = entry["bin"]
    if isinstance(bin_rel, list):
        bin_rel = bin_rel[0]
    try:
        return resolve_executable(repo_root / bin_rel)
    except FileNotFoundError:
        print(
            f"Executable for '{tool_name}' not found at {repo_root / bin_rel}. "
            "Check .dependency/manifest.json bin path.",
            file=sys.stderr,
        )
        sys.exit(1)


def resolve_ffmpeg() -> Path:
    repo_root = find_repo_root(Path(__file__))
    if repo_root is None:
        print(
            "Could not find .dependency/manifest.json by walking up from this script. "
            "Run from a repo that follows .cursor/skills/skill-dependency-manager.md.",
            file=sys.stderr,
        )
        sys.exit(1)
    return resolve_tool_bin(repo_root, "ffmpeg")


def resolve_ffprobe(ffmpeg: Path) -> Path:
    name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    candidate = ffmpeg.with_name(name)
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(candidate)


def get_video_files(folder: Path) -> list[Path]:
    files = [
        item.resolve()
        for item in folder.iterdir()
        if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(files, key=lambda p: p.name.lower())


def probe_duration(ffprobe: Path, file_path: Path) -> float:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"ffprobe failed for: {file_path}" + (f"\n{detail}" if detail else "")
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe JSON parse failed for: {file_path}") from exc

    for stream in payload.get("streams") or []:
        if stream.get("codec_type") == "video":
            dur = stream.get("duration")
            if dur is not None:
                return float(dur)

    fmt = payload.get("format") or {}
    if fmt.get("duration") is not None:
        return float(fmt["duration"])

    raise RuntimeError(f"Could not determine duration for: {file_path}")


def has_audio_stream(ffprobe: Path, file_path: Path) -> bool:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return bool(payload.get("streams"))


def encoder_works(ffmpeg: Path, codec: str, pix_fmt: str) -> bool:
    """Tiny HEVC Main10 probe. Use ≥256x256 — NVENC rejects very small frames."""
    with tempfile.TemporaryDirectory(prefix="vmerge_gpu_probe_") as tmp:
        out = Path(tmp) / "probe.mp4"
        cmd = [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=0.2",
            "-vf",
            f"format={pix_fmt}",
            "-frames:v",
            "5",
            "-c:v",
            codec,
            "-profile:v",
            "main10",
            "-pix_fmt",
            pix_fmt,
            "-b:v",
            "500k",
            "-tag:v",
            "hvc1",
            "-y",
            str(out),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return result.returncode == 0 and out.is_file() and out.stat().st_size > 0


def list_gpu_candidates() -> list[tuple[str, str, str]]:
    return [
        ("hevc_nvenc", "nvenc", "NVIDIA NVENC HEVC Main10"),
        ("hevc_amf", "amf", "AMD AMF HEVC Main10"),
        ("hevc_qsv", "qsv", "Intel QSV HEVC Main10"),
    ]


def select_gpu_encoder(ffmpeg: Path) -> EncoderChoice:
    pix_fmts = ("p010le", "yuv420p10le")
    tried: list[str] = []
    for name, kind, label in list_gpu_candidates():
        for pix_fmt in pix_fmts:
            tried.append(f"{name}/{pix_fmt}")
            if encoder_works(ffmpeg, name, pix_fmt):
                return EncoderChoice(name, kind, label, pix_fmt)

    print(
        "No GPU HEVC Main10 encoder available "
        f"(tried: {', '.join(tried)}). "
        "This skill does not fall back to CPU libx265. "
        "Install NVIDIA/AMD/Intel GPU drivers and an FFmpeg build with "
        "NVENC/AMF/QSV, or use video-merge for CPU encode.",
        file=sys.stderr,
    )
    sys.exit(1)


def encode_args(encoder: EncoderChoice, out_path: Path) -> list[str]:
    args = [
        "-c:v",
        encoder.name,
        "-profile:v",
        "main10",
        "-pix_fmt",
        encoder.pix_fmt,
        "-b:v",
        VIDEO_BITRATE,
        "-maxrate",
        VIDEO_BITRATE,
        "-bufsize",
        "80M",
    ]
    if encoder.kind == "nvenc":
        args.extend(
            [
                "-rc",
                "vbr",
                "-preset",
                "p4",
                "-multipass",
                "fullres",
            ]
        )
    elif encoder.kind == "amf":
        args.extend(
            [
                "-rc",
                "vbr_peak",
                "-quality",
                "balanced",
            ]
        )
    elif encoder.kind == "qsv":
        args.extend(["-preset", "medium"])

    args.extend(
        [
            "-r",
            str(OUTPUT_FPS),
            "-tag:v",
            "hvc1",
            "-c:a",
            "aac",
            "-b:a",
            AUDIO_BITRATE,
            "-ar",
            str(AUDIO_RATE),
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
    )
    return args


def video_normalize_filter(label_in: str, label_out: str) -> str:
    return (
        f"[{label_in}]scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={OUTPUT_FPS},format=yuv420p10le,setpts=PTS-STARTPTS[{label_out}]"
    )


def audio_normalize_filter(label_in: str, label_out: str) -> str:
    return (
        f"[{label_in}]aformat=sample_rates={AUDIO_RATE}:channel_layouts=stereo,"
        f"aresample={AUDIO_RATE},asetpts=PTS-STARTPTS[{label_out}]"
    )


def build_filter_complex(
    files: list[Path],
    durations: list[float],
    has_audio: list[bool],
    transitions: list[str],
) -> tuple[str, list[str]]:
    """Return (filter_complex, extra_ffmpeg_inputs before -i files)."""
    parts: list[str] = []
    extra_inputs: list[str] = []
    silent_index = 0

    for i, file_path in enumerate(files):
        parts.append(video_normalize_filter(f"{i}:v", f"v{i}"))
        if has_audio[i]:
            parts.append(audio_normalize_filter(f"{i}:a", f"a{i}"))
        else:
            # anullsrc as extra input after all video inputs
            dur = durations[i]
            extra_inputs.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    f"{dur:.6f}",
                    "-i",
                    f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_RATE}",
                ]
            )
            src_idx = len(files) + silent_index
            parts.append(audio_normalize_filter(f"{src_idx}:a", f"a{i}"))
            silent_index += 1

    if len(files) == 1:
        parts.append("[v0]null[vout]")
        parts.append("[a0]anull[aout]")
        return ";".join(parts), extra_inputs

    # Chain xfade / acrossfade. Pad the outgoing side by T (freeze last frame /
    # silence) so each overlap does not shorten total duration vs sum(clips).
    cur_v = "v0"
    cur_a = "a0"
    cum = durations[0]

    for i in range(1, len(files)):
        transition = transitions[i - 1]
        next_v = f"vx{i}"
        next_a = f"ax{i}"
        pad_v = f"vp{i}"
        pad_a = f"ap{i}"
        parts.append(
            f"[{cur_v}]tpad=stop_mode=clone:stop_duration={TRANSITION_DURATION}[{pad_v}]"
        )
        parts.append(f"[{cur_a}]apad=pad_dur={TRANSITION_DURATION}[{pad_a}]")
        # Transition begins after all real content of the outgoing chain.
        offset = cum
        parts.append(
            f"[{pad_v}][v{i}]xfade=transition={transition}:"
            f"duration={TRANSITION_DURATION}:offset={offset:.6f}[{next_v}]"
        )
        parts.append(
            f"[{pad_a}][a{i}]acrossfade=d={TRANSITION_DURATION}:c1=tri:c2=tri[{next_a}]"
        )
        cur_v = next_v
        cur_a = next_a
        cum = cum + durations[i]

    parts.append(f"[{cur_v}]null[vout]")
    parts.append(f"[{cur_a}]anull[aout]")
    return ";".join(parts), extra_inputs


def default_output_path(folder: Path) -> Path:
    return folder / "merged-gpu" / f"{folder.name}.mp4"


def run_ffmpeg_merge(
    ffmpeg: Path,
    encoder: EncoderChoice,
    files: list[Path],
    durations: list[float],
    has_audio: list[bool],
    transitions: list[str],
    out_path: Path,
) -> None:
    filter_complex, extra_inputs = build_filter_complex(
        files, durations, has_audio, transitions
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = [str(ffmpeg), "-hide_banner", "-y"]
    for file_path in files:
        cmd.extend(["-i", str(file_path)])
    cmd.extend(extra_inputs)
    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
        ]
    )
    cmd.extend(encode_args(encoder, out_path))

    log_path = out_path.with_suffix(out_path.suffix + ".ffmpeg.log")
    with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
        result = subprocess.run(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    if result.returncode != 0:
        detail = ""
        if log_path.is_file():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            detail = "\n".join(lines[-40:])
        raise RuntimeError(
            f"ffmpeg merge failed (exit {result.returncode})"
            + (f"\n{detail}" if detail else "")
        )
    if log_path.is_file():
        log_path.unlink(missing_ok=True)


def merge_chunked(
    ffmpeg: Path,
    encoder: EncoderChoice,
    files: list[Path],
    durations: list[float],
    has_audio: list[bool],
    transitions: list[str],
    out_path: Path,
    work_dir: Path,
    depth: int = 0,
) -> None:
    """Merge with at most MAX_INPUTS_PER_GRAPH inputs per filtergraph."""
    if len(files) <= MAX_INPUTS_PER_GRAPH:
        run_ffmpeg_merge(
            ffmpeg, encoder, files, durations, has_audio, transitions, out_path
        )
        return

    work_dir.mkdir(parents=True, exist_ok=True)
    chunk_files: list[Path] = []
    chunk_durations: list[float] = []
    chunk_audio: list[bool] = []
    boundary_transitions: list[str] = []

    start = 0
    chunk_idx = 0
    while start < len(files):
        end = min(start + MAX_INPUTS_PER_GRAPH, len(files))
        part_files = files[start:end]
        part_durs = durations[start:end]
        part_audio = has_audio[start:end]
        part_trans = transitions[start : end - 1] if end - start > 1 else []

        if end - start == 1 and depth == 0:
            # Single leftover source still needs normalize encode when joining later.
            chunk_out = work_dir / f"d{depth}_{chunk_idx:03d}.mp4"
            print(
                f"[chunk] d{depth} clip {start + 1}/{len(files)} "
                f"→ {chunk_out.name}"
            )
            run_ffmpeg_merge(
                ffmpeg,
                encoder,
                part_files,
                part_durs,
                part_audio,
                part_trans,
                chunk_out,
            )
        elif end - start == 1:
            chunk_out = part_files[0]
        else:
            chunk_out = work_dir / f"d{depth}_{chunk_idx:03d}.mp4"
            print(
                f"[chunk] d{depth} clips {start + 1}-{end}/{len(files)} "
                f"→ {chunk_out.name}"
            )
            merge_chunked(
                ffmpeg,
                encoder,
                part_files,
                part_durs,
                part_audio,
                part_trans,
                chunk_out,
                work_dir,
                depth + 1,
            )

        chunk_files.append(chunk_out)
        chunk_durations.append(sum(part_durs))
        chunk_audio.append(True)
        if end < len(files):
            boundary_transitions.append(transitions[end - 1])
        start = end
        chunk_idx += 1

    print(
        f"[chunk] d{depth} join {len(chunk_files)} parts → {out_path.name}"
    )
    merge_chunked(
        ffmpeg,
        encoder,
        chunk_files,
        chunk_durations,
        chunk_audio,
        boundary_transitions,
        out_path,
        work_dir,
        depth + 1,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge videos in a folder (filename sort) with random 0.5s transitions "
            "(freeze-pad; duration = sum of clips) into 3840x2160 60fps "
            "H.265 Main10 40Mbps + AAC 320kbps using GPU encode only "
            "(hevc_nvenc / hevc_amf / hevc_qsv; no CPU fallback)."
        )
    )
    parser.add_argument("input", help="Directory containing videos to merge")
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help="Output MP4 path (default: <folder>/merged-gpu/<folder-name>.mp4)",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace existing output file"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing files"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed for reproducible transition picks",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)

    ffmpeg = resolve_ffmpeg()
    ffprobe = resolve_ffprobe(ffmpeg)
    encoder = select_gpu_encoder(ffmpeg)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input path not found: {args.input}", file=sys.stderr)
        return 1
    if not input_path.is_dir():
        print(f"Input must be a directory: {args.input}", file=sys.stderr)
        return 1

    folder = input_path.resolve()
    files = get_video_files(folder)
    if not files:
        print(f"No supported video files found under: {args.input}")
        return 0

    out_path = Path(args.output).resolve() if args.output else default_output_path(folder)
    if out_path.suffix.lower() != ".mp4":
        print(f"Output must be an .mp4 file: {out_path}", file=sys.stderr)
        return 1

    # Refuse writing onto a source
    for src in files:
        if out_path.resolve() == src.resolve():
            print(
                "Refusing to overwrite a source file. Choose a different -o path.",
                file=sys.stderr,
            )
            return 1

    if out_path.exists() and not args.overwrite and not args.dry_run:
        print(f"Output exists (pass --overwrite): {out_path}", file=sys.stderr)
        return 1

    durations: list[float] = []
    audio_flags: list[bool] = []
    for file_path in files:
        try:
            dur = probe_duration(ffprobe, file_path)
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            return 1
        # Incoming (right) side of xfade must be longer than the transition.
        if len(files) > 1 and file_path != files[0] and dur <= TRANSITION_DURATION:
            print(
                f"Clip shorter than transition ({TRANSITION_DURATION}s): "
                f"{file_path.name} ({dur:.3f}s)",
                file=sys.stderr,
            )
            return 1
        durations.append(dur)
        audio_flags.append(has_audio_stream(ffprobe, file_path))

    transitions: list[str] = []
    if len(files) > 1:
        transitions = [rng.choice(TRANSITIONS) for _ in range(len(files) - 1)]

    total_duration = sum(durations)
    print(f"Input:       {folder}")
    print(f"Clips:       {len(files)}")
    print(
        f"Transition:  {TRANSITION_DURATION}s (random xfade, "
        "freeze-pad — total duration = sum of clips)"
    )
    print(f"Duration:    {total_duration:.3f}s (preserved)")
    print(
        f"Encoder:     {encoder.label} ({encoder.name}, {encoder.pix_fmt}) — GPU only"
    )
    print(
        f"Output spec: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT} @{OUTPUT_FPS} "
        f"H.265 Main10 {VIDEO_BITRATE} + AAC {AUDIO_BITRATE}"
    )
    print(f"Output:      {out_path}")
    if args.seed is not None:
        print(f"Seed:        {args.seed}")
    if args.dry_run:
        print("Run:         DRY RUN")
    print()

    for i, file_path in enumerate(files):
        audio_note = "audio" if audio_flags[i] else "silent→anullsrc"
        print(f"  [{i + 1:02d}] {file_path.name}  {durations[i]:.3f}s  ({audio_note})")
        if i < len(transitions):
            print(f"       └─ xfade: {transitions[i]} (freeze-pad {TRANSITION_DURATION}s)")

    if args.dry_run:
        print()
        print("Done. dry-run ok")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir = out_path.parent / f".tmp-{out_path.stem}"
    if work_dir.exists():
        for stale in work_dir.glob("*"):
            if stale.is_file():
                stale.unlink(missing_ok=True)

    print()
    if len(files) > MAX_INPUTS_PER_GRAPH:
        print(
            f"[run] ffmpeg merge GPU ({encoder.name}, chunked, max {MAX_INPUTS_PER_GRAPH} "
            "inputs/graph to limit RAM) …"
        )
    else:
        print(f"[run] ffmpeg merge GPU ({encoder.name}) …")

    try:
        merge_chunked(
            ffmpeg,
            encoder,
            files,
            durations,
            audio_flags,
            transitions,
            out_path,
            work_dir,
        )
    except RuntimeError as exc:
        print("[fail] merge failed", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1
    finally:
        if work_dir.exists():
            for stale in work_dir.glob("*"):
                if stale.is_file():
                    stale.unlink(missing_ok=True)
            try:
                work_dir.rmdir()
            except OSError:
                pass

    print(f"[ok]  {out_path}")
    print()
    print("Done. merged=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
