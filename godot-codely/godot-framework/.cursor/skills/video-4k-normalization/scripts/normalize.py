#!/usr/bin/env python3
"""Normalize videos to unified 4K60 H.265 Main10 BT.709 SDR masters (FFmpeg only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
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

TARGET_WIDTH = 3840
TARGET_HEIGHT = 2160
TARGET_FPS = 60
VIDEO_BITRATE = "40M"
AUDIO_BITRATE = "320k"

HDR_TRANSFERS = {
    "smpte2084",
    "arib-std-b67",
    "smpte428",
    "smpte2085",
}
HDR_PRIMARIES = {"bt2020"}
HDR_SPACES = {"bt2020nc", "bt2020c"}


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


def resolve_repo_tools() -> tuple[Path, Path]:
    repo_root = find_repo_root(Path(__file__))
    if repo_root is None:
        print(
            "Could not find .dependency/manifest.json by walking up from this script. "
            "Run from a repo that follows .cursor/skills/skill-dependency-manager.md.",
            file=sys.stderr,
        )
        sys.exit(1)
    ffmpeg = resolve_tool_bin(repo_root, "ffmpeg")
    return ffmpeg, resolve_ffprobe(ffmpeg)


def resolve_ffprobe(ffmpeg: Path) -> Path:
    name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    candidate = ffmpeg.with_name(name)
    if candidate.is_file():
        return candidate
    raise FileNotFoundError(candidate)


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
        rel = relative_path(file_path, input_root)
        out_path = (output_dir / Path(rel).with_suffix(".mp4")).resolve()
        if out_path == file_path.resolve():
            collisions.append((file_path, out_path))
    return collisions


def probe_video(ffprobe: Path, file_path: Path) -> dict:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
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
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe returned invalid JSON for: {file_path}") from exc


def parse_frame_rate(rate: str | None) -> float | None:
    if not rate or rate in {"0/0", "N/A"}:
        return None
    if "/" in rate:
        num_s, den_s = rate.split("/", 1)
        try:
            num = float(num_s)
            den = float(den_s)
        except ValueError:
            return None
        if den == 0:
            return None
        return num / den
    try:
        return float(rate)
    except ValueError:
        return None


def stream_info(payload: dict) -> tuple[dict, bool]:
    streams = payload.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError("No video stream found")

    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video dimensions: {width}x{height}")

    fps = parse_frame_rate(video.get("avg_frame_rate"))
    if fps is None or fps <= 0:
        fps = parse_frame_rate(video.get("r_frame_rate"))

    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    return video, has_audio


def is_hdr(video: dict) -> bool:
    transfer = str(video.get("color_transfer") or "").lower()
    primaries = str(video.get("color_primaries") or "").lower()
    space = str(video.get("color_space") or "").lower()

    if transfer in HDR_TRANSFERS:
        return True
    if primaries in HDR_PRIMARIES:
        return True
    if space in HDR_SPACES:
        return True

    for side in video.get("side_data_list") or []:
        kind = str(side.get("side_data_type") or "").lower()
        if "mastering display" in kind or "content light" in kind:
            return True
    return False


def run_checked(cmd: list[str], label: str) -> None:
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{label} failed" + (f"\n{detail}" if detail else ""))


def build_vf(hdr: bool) -> str:
    scale_fps = f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos,fps={TARGET_FPS}"
    if hdr:
        return (
            "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
            "tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p10le,"
            f"{scale_fps}"
        )
    return f"{scale_fps},format=yuv420p10le"


def build_ffmpeg_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    has_audio: bool,
    hdr: bool,
) -> list[str]:
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
        "-vf",
        build_vf(hdr),
        "-c:v",
        "libx265",
        "-profile:v",
        "main10",
        "-pix_fmt",
        "yuv420p10le",
        "-b:v",
        VIDEO_BITRATE,
        "-maxrate",
        VIDEO_BITRATE,
        "-bufsize",
        "80M",
        "-tag:v",
        "hvc1",
        "-x265-params",
        "profile=main10:colorprim=bt709:transfer=bt709:colormatrix=bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-color_range",
        "tv",
    ]
    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", AUDIO_BITRATE])
    else:
        cmd.append("-an")
    cmd.extend(["-movflags", "+faststart", str(out_path)])
    return cmd


def normalize_file(
    ffmpeg: Path,
    ffprobe: Path,
    file_path: Path,
    out_path: Path,
    dry_run: bool,
) -> str:
    payload = probe_video(ffprobe, file_path)
    video, has_audio = stream_info(payload)
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    fps = parse_frame_rate(video.get("avg_frame_rate"))
    if fps is None or fps <= 0:
        fps = parse_frame_rate(video.get("r_frame_rate"))
    fps_label = f"{fps:.3g}" if fps else "?"
    hdr = is_hdr(video)
    path_label = "HDR鈫扴DR tonemap" if hdr else "SDR"

    plan = (
        f"{path_label} ({width}x{height} @{fps_label}fps 鈫?"
        f"{TARGET_WIDTH}x{TARGET_HEIGHT} @{TARGET_FPS}fps Main10 BT.709)"
    )
    if dry_run:
        return plan

    out_path.parent.mkdir(parents=True, exist_ok=True)
    run_checked(
        build_ffmpeg_args(ffmpeg, file_path, out_path, has_audio, hdr),
        "FFmpeg normalize encode",
    )
    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize videos to unified 3840x2160 60FPS H.265 Main10 40Mbps + "
            "AAC 320kbps BT.709 SDR MP4 (FFmpeg re-encode; HDR tone-mapped)."
        )
    )
    parser.add_argument("input", help="Path to a single video file or directory")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="",
        help="Output directory (default: <input>/normalized)",
    )
    parser.add_argument(
        "-r", "--recurse", action="store_true", help="Process subdirectories"
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
    ffmpeg, ffprobe = resolve_repo_tools()

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
        Path(args.output_dir).resolve() if args.output_dir else input_root / "normalized"
    )

    initial_count = len(files)
    files = filter_output_files(files, output_dir)
    if not files:
        if initial_count:
            print(
                "No source files to process: all inputs lie under the output directory. "
                "Choose a separate output directory (default: normalized/).",
                file=sys.stderr,
            )
            return 1
        print(f"No supported video files found under: {args.input}")
        return 0

    collisions = find_source_collisions(files, input_root, output_dir)
    if collisions:
        print(
            "Refusing to overwrite source files. Use a separate output directory "
            "(default: normalized/).",
            file=sys.stderr,
        )
        for source, dest in collisions:
            print(f"  {source} -> {dest}", file=sys.stderr)
        return 1

    print(f"Input:     {args.input}")
    print(f"Files:     {len(files)}")
    print(
        f"Target:    {TARGET_WIDTH}x{TARGET_HEIGHT} @{TARGET_FPS}fps "
        f"H.265 Main10 {VIDEO_BITRATE} + AAC {AUDIO_BITRATE} BT.709 SDR"
    )
    print(f"Output:    {output_dir}")
    if args.dry_run:
        print("Run:       DRY RUN")
    print()

    ok = 0
    skip = 0
    fail = 0

    for file_path in files:
        rel = relative_path(file_path, input_root)
        out_rel = str(Path(rel).with_suffix(".mp4"))
        out_path = output_dir / out_rel

        if out_path.exists() and not args.overwrite and not args.dry_run:
            print(f"[skip] {out_rel} (exists)")
            skip += 1
            continue

        try:
            if args.dry_run:
                plan = normalize_file(
                    ffmpeg, ffprobe, file_path, out_path, dry_run=True
                )
                print(f"[plan] {rel} -> {out_rel} ({plan})")
                ok += 1
                continue

            print(f"[run]  {rel} -> {out_rel}")
            plan = normalize_file(
                ffmpeg, ffprobe, file_path, out_path, dry_run=False
            )
            print(f"       {plan}")
            ok += 1
        except RuntimeError as exc:
            print(f"[fail] {rel}")
            print(exc)
            fail += 1

    print()
    print(f"Done. processed={ok} skipped={skip} failed={fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
