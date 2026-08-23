#!/usr/bin/env python3
"""Compress video files to stay under a max file size via FFmpeg (GPU-first)."""

from __future__ import annotations

import argparse
import json
import re
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

SIZE_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(B|K|KB|KiB|M|MB|MiB|G|GB|GiB)?\s*$",
    re.IGNORECASE,
)

# Leave headroom for container/mux overhead vs declared max size.
SAFETY_FACTOR_CPU = 0.92
SAFETY_FACTOR_GPU = 0.90  # VBR is less precise than two-pass
MIN_VIDEO_BITRATE = 50_000  # 50 kbps
MAX_ATTEMPTS = 3
KIB = 1024
MIB = 1024 * 1024
GIB = 1024 * 1024 * 1024

# Map common x264-style names → NVENC/AMF/QSV presets.
NVENC_PRESET_MAP = {
    "ultrafast": "p1",
    "superfast": "p1",
    "veryfast": "p2",
    "faster": "p3",
    "fast": "p3",
    "medium": "p4",
    "slow": "p5",
    "slower": "p6",
    "veryslow": "p7",
    "placebo": "p7",
}
AMF_PRESET_MAP = {
    "ultrafast": "speed",
    "superfast": "speed",
    "veryfast": "speed",
    "faster": "speed",
    "fast": "balanced",
    "medium": "balanced",
    "slow": "quality",
    "slower": "quality",
    "veryslow": "quality",
    "placebo": "quality",
}
QSV_PRESET_MAP = {
    "ultrafast": "veryfast",
    "superfast": "veryfast",
    "veryfast": "veryfast",
    "faster": "faster",
    "fast": "fast",
    "medium": "medium",
    "slow": "slow",
    "slower": "slower",
    "veryslow": "veryslow",
    "placebo": "veryslow",
}


@dataclass(frozen=True)
class EncoderChoice:
    name: str  # ffmpeg -c:v name
    kind: str  # nvenc | amf | qsv | cpu
    hevc: bool
    label: str


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


def parse_size(text: str) -> int:
    match = SIZE_RE.match(text)
    if not match:
        raise ValueError(
            f"Invalid --max-size '{text}'. Examples: 50, 50MB, 500KB, 1GB, 52428800B"
        )

    value = float(match.group(1))
    unit = (match.group(2) or "MB").upper()
    if unit in {"K", "KB", "KIB"}:
        return int(value * KIB)
    if unit in {"M", "MB", "MIB"}:
        return int(value * MIB)
    if unit in {"G", "GB", "GIB"}:
        return int(value * GIB)
    if unit == "B":
        return int(value)
    raise ValueError(f"Unknown size unit in --max-size '{text}'")


def parse_bitrate(text: str) -> int:
    raw = text.strip().lower()
    if raw.endswith("k"):
        return int(float(raw[:-1]) * 1000)
    if raw.endswith("m"):
        return int(float(raw[:-1]) * 1_000_000)
    return int(float(raw))


def format_bytes(num: int) -> str:
    if num >= GIB:
        return f"{num / GIB:.2f} GiB"
    if num >= MIB:
        return f"{num / MIB:.2f} MiB"
    if num >= KIB:
        return f"{num / KIB:.1f} KiB"
    return f"{num} B"


def format_bitrate(bits_per_sec: int) -> str:
    if bits_per_sec >= 1_000_000:
        return f"{bits_per_sec / 1_000_000:.3f}M"
    return f"{max(1, bits_per_sec // 1000)}k"


def get_video_files(path: Path, recurse: bool) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            print(f"Not a supported video file: {path}", file=sys.stderr)
            sys.exit(1)
        return [path.resolve()]

    if not path.is_dir():
        print(f"Input path not found: {path}", file=sys.stderr)
        sys.exit(1)

    if recurse:
        candidates = path.rglob("*")
    else:
        candidates = path.iterdir()

    files = [
        item.resolve()
        for item in candidates
        if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(files)


def relative_path(file_path: Path, input_root: Path) -> str:
    try:
        return file_path.relative_to(input_root).as_posix()
    except ValueError:
        return file_path.name


def filter_output_files(files: list[Path], output_dir: Path) -> list[Path]:
    out = output_dir.resolve()
    kept: list[Path] = []
    for file_path in files:
        try:
            file_path.resolve().relative_to(out)
        except ValueError:
            kept.append(file_path)
    return kept


def find_source_collisions(
    files: list[Path], input_root: Path, output_dir: Path
) -> list[tuple[Path, Path]]:
    collisions: list[tuple[Path, Path]] = []
    for file_path in files:
        rel = Path(relative_path(file_path, input_root)).with_suffix(".mp4")
        out_path = output_dir / rel
        if out_path.resolve() == file_path.resolve():
            collisions.append((file_path, out_path))
    return collisions


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
        raise RuntimeError(f"ffprobe failed for: {file_path}\n{result.stderr.strip()}")

    payload = json.loads(result.stdout)
    duration = 0.0
    fmt = payload.get("format") or {}
    if fmt.get("duration"):
        duration = float(fmt["duration"])
    if duration <= 0:
        for stream in payload.get("streams") or []:
            if stream.get("codec_type") == "video" and stream.get("duration"):
                duration = float(stream["duration"])
                break
    if duration <= 0:
        raise RuntimeError(f"Could not determine duration for: {file_path}")
    return duration


def has_audio_streams(ffprobe: Path, file_path: Path) -> bool:
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


def null_output() -> str:
    return "NUL" if sys.platform == "win32" else "/dev/null"


def run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            "FFmpeg failed:"
            + (f"\n{detail}" if detail else "")
            + f"\nCommand: {' '.join(cmd)}"
        )


def encoder_works(ffmpeg: Path, codec: str) -> bool:
    """Tiny probe encode to a temp mp4 (null mux is unreliable for hw encoders).

    Use ≥256x256 — NVENC rejects very small frames (e.g. 64x64).
    """
    with tempfile.TemporaryDirectory(prefix="vcompress_probe_") as tmp:
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
            "-frames:v",
            "5",
            "-c:v",
            codec,
            "-b:v",
            "500k",
            "-y",
            str(out),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return result.returncode == 0 and out.is_file() and out.stat().st_size > 0


def list_gpu_candidates(hevc: bool) -> list[EncoderChoice]:
    if hevc:
        return [
            EncoderChoice("hevc_nvenc", "nvenc", True, "NVIDIA NVENC HEVC"),
            EncoderChoice("hevc_amf", "amf", True, "AMD AMF HEVC"),
            EncoderChoice("hevc_qsv", "qsv", True, "Intel QSV HEVC"),
        ]
    return [
        EncoderChoice("h264_nvenc", "nvenc", False, "NVIDIA NVENC H.264"),
        EncoderChoice("h264_amf", "amf", False, "AMD AMF H.264"),
        EncoderChoice("h264_qsv", "qsv", False, "Intel QSV H.264"),
    ]


def select_encoder(ffmpeg: Path, hevc: bool, force_cpu: bool) -> EncoderChoice:
    if not force_cpu:
        for candidate in list_gpu_candidates(hevc):
            if encoder_works(ffmpeg, candidate.name):
                return candidate
    if hevc:
        return EncoderChoice("libx265", "cpu", True, "libx265 (CPU)")
    return EncoderChoice("libx264", "cpu", False, "libx264 (CPU)")


def map_preset(encoder: EncoderChoice, preset: str) -> str:
    key = preset.strip().lower()
    if encoder.kind == "nvenc":
        if key in NVENC_PRESET_MAP:
            return NVENC_PRESET_MAP[key]
        if re.fullmatch(r"p[1-7]", key):
            return key
        return "p4"
    if encoder.kind == "amf":
        if key in {"speed", "balanced", "quality"}:
            return key
        return AMF_PRESET_MAP.get(key, "balanced")
    if encoder.kind == "qsv":
        return QSV_PRESET_MAP.get(key, key if key else "medium")
    return preset


def compute_video_bitrate(
    max_bytes: int,
    duration: float,
    audio_bitrate: int,
    has_audio: bool,
    safety: float,
) -> int:
    budget_bits = max_bytes * 8 * safety
    audio_bits = audio_bitrate if has_audio else 0
    return int(budget_bits / duration - audio_bits)


def build_hwaccel_args(encoder: EncoderChoice) -> list[str]:
    if encoder.kind == "nvenc":
        return ["-hwaccel", "cuda"]
    if encoder.kind == "qsv":
        return ["-hwaccel", "qsv"]
    if encoder.kind == "amf":
        return ["-hwaccel", "d3d11va"]
    return []


def build_video_encode_args(
    encoder: EncoderChoice,
    video_bitrate: int,
    preset: str,
) -> list[str]:
    vb = format_bitrate(video_bitrate)
    maxrate = format_bitrate(int(video_bitrate * 1.05))
    bufsize = format_bitrate(video_bitrate * 2)
    mapped = map_preset(encoder, preset)
    args = ["-c:v", encoder.name, "-b:v", vb]

    # h264_* NVENC/AMF/QSV are 8-bit only; 10-bit sources (e.g. Main10 HEVC) must convert.
    if not encoder.hevc:
        args.extend(["-pix_fmt", "yuv420p"])
    elif encoder.kind == "nvenc":
        # Prefer 8-bit for size targets; Main10 → 8-bit is fine for compression.
        args.extend(["-pix_fmt", "yuv420p"])

    if encoder.kind == "nvenc":
        args.extend(
            [
                "-rc",
                "vbr",
                "-maxrate",
                maxrate,
                "-bufsize",
                bufsize,
                "-preset",
                mapped,
                "-multipass",
                "fullres",
            ]
        )
    elif encoder.kind == "amf":
        args.extend(
            [
                "-rc",
                "vbr_peak",
                "-maxrate",
                maxrate,
                "-bufsize",
                bufsize,
                "-quality",
                mapped,
            ]
        )
    elif encoder.kind == "qsv":
        args.extend(
            [
                "-maxrate",
                maxrate,
                "-bufsize",
                bufsize,
                "-preset",
                mapped,
            ]
        )
    else:
        args.extend(["-preset", mapped])

    if encoder.hevc:
        args.extend(["-tag:v", "hvc1"])
    return args


def compress_file_gpu(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    encoder: EncoderChoice,
    max_bytes: int,
    video_bitrate: int,
    effective_audio: int,
    has_audio: bool,
    preset: str,
) -> tuple[int, int]:
    last_size = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        cmd = [str(ffmpeg), "-hide_banner", "-nostats", "-y"]
        cmd.extend(build_hwaccel_args(encoder))
        cmd.extend(["-i", str(file_path), "-map", "0:v:0"])
        cmd.extend(build_video_encode_args(encoder, video_bitrate, preset))
        if has_audio:
            cmd.extend(
                [
                    "-map",
                    "0:a:0?",
                    "-c:a",
                    "aac",
                    "-b:a",
                    format_bitrate(effective_audio),
                    "-ac",
                    "2",
                ]
            )
        else:
            cmd.append("-an")
        cmd.extend(["-movflags", "+faststart", str(out_path)])

        try:
            run_ffmpeg(cmd)
        except RuntimeError:
            # Retry once without hwaccel decode (encode-only GPU).
            if build_hwaccel_args(encoder):
                cmd = [str(ffmpeg), "-hide_banner", "-nostats", "-y", "-i", str(file_path)]
                cmd.extend(["-map", "0:v:0"])
                cmd.extend(build_video_encode_args(encoder, video_bitrate, preset))
                if has_audio:
                    cmd.extend(
                        [
                            "-map",
                            "0:a:0?",
                            "-c:a",
                            "aac",
                            "-b:a",
                            format_bitrate(effective_audio),
                            "-ac",
                            "2",
                        ]
                    )
                else:
                    cmd.append("-an")
                cmd.extend(["-movflags", "+faststart", str(out_path)])
                run_ffmpeg(cmd)
            else:
                raise

        last_size = out_path.stat().st_size
        if last_size <= max_bytes:
            return last_size, video_bitrate

        scale = (max_bytes * SAFETY_FACTOR_GPU) / last_size
        video_bitrate = max(MIN_VIDEO_BITRATE, int(video_bitrate * scale))
        print(
            f"  [retry {attempt}/{MAX_ATTEMPTS}] "
            f"{format_bytes(last_size)} > {format_bytes(max_bytes)}; "
            f"next video bitrate {format_bitrate(video_bitrate)}"
        )

    raise RuntimeError(
        f"Could not get under {format_bytes(max_bytes)} after {MAX_ATTEMPTS} attempts "
        f"(last size {format_bytes(last_size)})."
    )


def compress_file_cpu(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    encoder: EncoderChoice,
    max_bytes: int,
    video_bitrate: int,
    effective_audio: int,
    has_audio: bool,
    preset: str,
) -> tuple[int, int]:
    last_size = 0
    with tempfile.TemporaryDirectory(prefix="vcompress_") as tmp:
        passlog = Path(tmp) / "ffmpeg2pass"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            vb = format_bitrate(video_bitrate)

            pass1 = [
                str(ffmpeg),
                "-hide_banner",
                "-nostats",
                "-y",
                "-i",
                str(file_path),
                "-map",
                "0:v:0",
                "-c:v",
                encoder.name,
                "-b:v",
                vb,
                "-preset",
                preset,
                "-pass",
                "1",
                "-passlogfile",
                str(passlog),
                "-an",
                "-f",
                "null",
                null_output(),
            ]
            run_ffmpeg(pass1)

            pass2 = [
                str(ffmpeg),
                "-hide_banner",
                "-nostats",
                "-y",
                "-i",
                str(file_path),
                "-map",
                "0:v:0",
                "-c:v",
                encoder.name,
                "-b:v",
                vb,
                "-preset",
                preset,
                "-pass",
                "2",
                "-passlogfile",
                str(passlog),
            ]
            if encoder.hevc:
                pass2.extend(["-tag:v", "hvc1"])
            if has_audio:
                pass2.extend(
                    [
                        "-map",
                        "0:a:0?",
                        "-c:a",
                        "aac",
                        "-b:a",
                        format_bitrate(effective_audio),
                        "-ac",
                        "2",
                    ]
                )
            else:
                pass2.append("-an")
            pass2.extend(["-movflags", "+faststart", str(out_path)])
            run_ffmpeg(pass2)

            last_size = out_path.stat().st_size
            if last_size <= max_bytes:
                return last_size, video_bitrate

            scale = (max_bytes * SAFETY_FACTOR_CPU) / last_size
            video_bitrate = max(MIN_VIDEO_BITRATE, int(video_bitrate * scale))
            print(
                f"  [retry {attempt}/{MAX_ATTEMPTS}] "
                f"{format_bytes(last_size)} > {format_bytes(max_bytes)}; "
                f"next video bitrate {format_bitrate(video_bitrate)}"
            )

    raise RuntimeError(
        f"Could not get under {format_bytes(max_bytes)} after {MAX_ATTEMPTS} attempts "
        f"(last size {format_bytes(last_size)})."
    )


def compress_file(
    ffmpeg: Path,
    ffprobe: Path,
    file_path: Path,
    out_path: Path,
    encoder: EncoderChoice,
    max_bytes: int,
    audio_bitrate: int,
    preset: str,
) -> tuple[int, int]:
    duration = probe_duration(ffprobe, file_path)
    has_audio = has_audio_streams(ffprobe, file_path)
    safety = SAFETY_FACTOR_GPU if encoder.kind != "cpu" else SAFETY_FACTOR_CPU

    effective_audio = audio_bitrate if has_audio else 0
    if has_audio:
        total_budget_bps = int(max_bytes * 8 * safety / duration)
        if effective_audio > total_budget_bps // 2:
            effective_audio = max(32_000, total_budget_bps // 4)

    video_bitrate = compute_video_bitrate(
        max_bytes, duration, effective_audio, has_audio, safety
    )
    if video_bitrate < MIN_VIDEO_BITRATE:
        raise RuntimeError(
            f"Target size {format_bytes(max_bytes)} is too small for "
            f"{duration:.1f}s video (video bitrate would be {format_bitrate(video_bitrate)}). "
            "Raise --max-size or lower --audio-bitrate."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if encoder.kind == "cpu":
        return compress_file_cpu(
            ffmpeg,
            file_path,
            out_path,
            encoder,
            max_bytes,
            video_bitrate,
            effective_audio,
            has_audio,
            preset,
        )
    return compress_file_gpu(
        ffmpeg,
        file_path,
        out_path,
        encoder,
        max_bytes,
        video_bitrate,
        effective_audio,
        has_audio,
        preset,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compress videos to stay under a max file size. "
            "Prefers GPU encoders (NVENC/AMF/QSV), falls back to CPU two-pass."
        )
    )
    parser.add_argument("input", help="Path to a single video file or directory")
    parser.add_argument(
        "--max-size",
        required=True,
        help="Max output size (e.g. 50, 50MB, 500KB, 1GB). Bare number = MB.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="",
        help="Output directory (default: <input>/compressed)",
    )
    parser.add_argument(
        "-r", "--recurse", action="store_true", help="Process subdirectories"
    )
    parser.add_argument(
        "--audio-bitrate",
        default="128k",
        help="AAC audio bitrate (default: 128k)",
    )
    parser.add_argument(
        "--preset",
        default="medium",
        help="Quality/speed preset (default: medium; mapped for GPU encoders)",
    )
    parser.add_argument(
        "--hevc",
        action="store_true",
        help="Prefer HEVC (hevc_nvenc / hevc_amf / hevc_qsv / libx265)",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU encoder (libx264/libx265 two-pass); skip GPU",
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Replace existing output files"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing files"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        max_bytes = parse_size(args.max_size)
        audio_bitrate = parse_bitrate(args.audio_bitrate)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    if max_bytes <= 0:
        print("--max-size must be positive", file=sys.stderr)
        return 1

    ffmpeg = resolve_ffmpeg()
    ffprobe = resolve_ffprobe(ffmpeg)
    encoder = select_encoder(ffmpeg, args.hevc, force_cpu=args.cpu)
    mapped_preset = map_preset(encoder, args.preset)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input path not found: {args.input}", file=sys.stderr)
        return 1

    input_path = input_path.resolve()
    files = get_video_files(input_path, args.recurse)
    if not files:
        print(f"No supported video files found under: {args.input}")
        return 0

    if input_path.is_file():
        input_root = input_path.parent
    else:
        input_root = input_path

    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else input_root / "compressed"
    )

    initial_count = len(files)
    files = filter_output_files(files, output_dir)
    if not files:
        if initial_count:
            print(
                "No source files to process: all inputs lie under the output directory. "
                "Choose a separate output directory (default: compressed/).",
                file=sys.stderr,
            )
            return 1
        print(f"No supported video files found under: {args.input}")
        return 0

    collisions = find_source_collisions(files, input_root, output_dir)
    if collisions:
        print(
            "Refusing to overwrite source files. Use a separate output directory "
            "(default: compressed/).",
            file=sys.stderr,
        )
        for source, dest in collisions:
            print(f"  {source} -> {dest}", file=sys.stderr)
        return 1

    print(f"Input:    {args.input}")
    print(f"Files:    {len(files)}")
    print(f"Max size: {format_bytes(max_bytes)} ({args.max_size})")
    print(
        f"Encoder:  {encoder.label} ({encoder.name}), "
        f"preset={args.preset}→{mapped_preset}, audio={args.audio_bitrate}"
    )
    print(f"Output:   {output_dir}")
    if args.dry_run:
        print("Run:      DRY RUN")
    print()

    ok = 0
    skip = 0
    fail = 0
    safety = SAFETY_FACTOR_GPU if encoder.kind != "cpu" else SAFETY_FACTOR_CPU

    for file_path in files:
        rel_src = relative_path(file_path, input_root)
        rel_out = str(Path(rel_src).with_suffix(".mp4"))
        out_path = output_dir / rel_out
        src_size = file_path.stat().st_size

        if out_path.exists() and not args.overwrite and not args.dry_run:
            print(f"[skip] {rel_out} (exists)")
            skip += 1
            continue

        if src_size <= max_bytes:
            print(
                f"[skip] {rel_src} (already under limit: "
                f"{format_bytes(src_size)} ≤ {format_bytes(max_bytes)})"
            )
            skip += 1
            continue

        if args.dry_run:
            try:
                duration = probe_duration(ffprobe, file_path)
                has_audio = has_audio_streams(ffprobe, file_path)
                vb = compute_video_bitrate(
                    max_bytes, duration, audio_bitrate, has_audio, safety
                )
                print(
                    f"[plan] {rel_src} -> {rel_out} "
                    f"({format_bytes(src_size)} → ≤{format_bytes(max_bytes)}, "
                    f"~{format_bitrate(vb)} video, {duration:.1f}s, {encoder.name})"
                )
                ok += 1
            except RuntimeError as exc:
                print(f"[fail] {rel_src}")
                print(exc)
                fail += 1
            continue

        try:
            print(
                f"[run]  {rel_src} -> {rel_out} "
                f"({format_bytes(src_size)} → ≤{format_bytes(max_bytes)}, {encoder.name})"
            )
            out_size, used_vb = compress_file(
                ffmpeg,
                ffprobe,
                file_path,
                out_path,
                encoder,
                max_bytes,
                audio_bitrate,
                args.preset,
            )
            print(
                f"  [ok]   {format_bytes(out_size)} "
                f"(video ~{format_bitrate(used_vb)})"
            )
            ok += 1
        except RuntimeError as exc:
            print(f"[fail] {rel_src}")
            print(exc)
            fail += 1
            if out_path.exists():
                try:
                    out_path.unlink()
                except OSError:
                    pass

    print()
    print(f"Done. processed={ok} skipped={skip} failed={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    # Line-buffer logs when stdout is piped (agent / CI).
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
        sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.exit(main())
