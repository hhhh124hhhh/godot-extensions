#!/usr/bin/env python3
"""Interpolate below-60fps video to 60fps with Video2X RIFE. Already ~60fps is skipped."""

from __future__ import annotations

import argparse
import json
import math
import shutil
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

TARGET_FPS = 60.0
FPS_TOLERANCE = 0.5
DEFAULT_RIFE_MODEL = "rife-v4.6"
AUDIO_BITRATE = "320k"
UHD_MIN_WIDTH = 1920


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


def resolve_repo_tools() -> tuple[Path, Path, Path]:
    repo_root = find_repo_root(Path(__file__))
    if repo_root is None:
        print(
            "Could not find .dependency/manifest.json by walking up from this script. "
            "Run from a repo that follows .cursor/skills/skill-dependency-manager.md.",
            file=sys.stderr,
        )
        sys.exit(1)
    ffmpeg = resolve_tool_bin(repo_root, "ffmpeg")
    video2x = resolve_tool_bin(repo_root, "video2x")
    return ffmpeg, resolve_ffprobe(ffmpeg), video2x


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


def filter_output_files(files: list[Path], *output_dirs: Path) -> list[Path]:
    outs = [d.resolve() for d in output_dirs]
    kept: list[Path] = []
    for file_path in files:
        under_output = False
        for out in outs:
            try:
                file_path.resolve().relative_to(out)
                under_output = True
                break
            except ValueError:
                pass
        if not under_output:
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


def stream_info(payload: dict) -> tuple[int, int, float | None, bool]:
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
    return width, height, fps, has_audio


def is_already_60(fps: float) -> bool:
    return abs(fps - TARGET_FPS) <= FPS_TOLERANCE


def rife_multiplier(fps: float) -> int:
    """Integer Video2X -m so src*mul is at least ~60 (minimum 2×)."""
    rounded = max(2, round(TARGET_FPS / fps))
    if abs(fps * rounded - TARGET_FPS) <= FPS_TOLERANCE:
        return rounded
    return max(2, math.ceil(TARGET_FPS / fps - 1e-9))


def run_checked(cmd: list[str], label: str) -> None:
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{label} failed" + (f"\n{detail}" if detail else ""))


def run_video2x(cmd: list[str], out_path: Path) -> None:
    """Run Video2X; accept output if the process crashes after writing the file.

    Video2X 6.x on Windows sometimes exits with STATUS_ACCESS_VIOLATION
    (-1073741819) after a successful encode.
    """
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    detail = (result.stderr or "") + "\n" + (result.stdout or "")
    ok_marker = "Video processed successfully" in detail
    usable = out_path.is_file() and out_path.stat().st_size > 0

    if result.returncode == 0 and usable:
        return
    if usable and (ok_marker or result.returncode == -1073741819):
        print(
            f"[warn] Video2X exited {result.returncode} after writing output; continuing"
        )
        return

    detail = detail.strip()
    raise RuntimeError(
        "Video2X interpolate failed" + (f"\n{detail}" if detail else "")
    )


def build_video2x_rife_args(
    video2x: Path,
    file_path: Path,
    out_path: Path,
    mul: int,
    model: str,
    uhd: bool,
    gpu: int | None,
) -> list[str]:
    cmd = [
        str(video2x),
        "-i",
        str(file_path),
        "-o",
        str(out_path),
        "-p",
        "rife",
        "-m",
        str(mul),
        "--rife-model",
        model,
        "-c",
        "libx265",
        "--pix-fmt",
        "yuv420p10le",
        "-e",
        "preset=medium",
        "-e",
        "crf=12",
    ]
    if uhd:
        cmd.append("--rife-uhd")
    if gpu is not None:
        cmd.extend(["-d", str(gpu)])
    return cmd


def build_ffmpeg_fps_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    has_audio: bool,
    copy_video: bool,
) -> list[str]:
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
    ]
    if copy_video:
        cmd.extend(["-c:v", "copy", "-tag:v", "hvc1"])
    else:
        cmd.extend(
            [
                "-vf",
                f"fps={int(TARGET_FPS)},format=yuv420p10le",
                "-c:v",
                "libx265",
                "-profile:v",
                "main10",
                "-pix_fmt",
                "yuv420p10le",
                "-crf",
                "12",
                "-preset",
                "medium",
                "-tag:v",
                "hvc1",
                "-x265-params",
                "profile=main10",
            ]
        )
    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", AUDIO_BITRATE])
    else:
        cmd.append("-an")
    cmd.extend(["-movflags", "+faststart", str(out_path)])
    return cmd


def convert_file(
    ffmpeg: Path,
    ffprobe: Path,
    video2x: Path,
    file_path: Path,
    out_path: Path,
    model: str,
    gpu: int | None,
    force_uhd: bool | None,
    dry_run: bool,
) -> str:
    payload = probe_video(ffprobe, file_path)
    width, height, fps, has_audio = stream_info(payload)
    if fps is None or fps <= 0:
        raise RuntimeError(f"Could not probe frame rate: {file_path}")

    fps_label = f"{fps:.3g}"

    if is_already_60(fps):
        return f"skip ({width}x{height} @{fps_label}fps already ~60)"

    if fps > TARGET_FPS + FPS_TOLERANCE:
        plan = (
            f"ffmpeg drop ({width}x{height} @{fps_label}fps → 60fps, "
            "no RIFE)"
        )
        if dry_run:
            return plan
        out_path.parent.mkdir(parents=True, exist_ok=True)
        run_checked(
            build_ffmpeg_fps_args(ffmpeg, file_path, out_path, has_audio, False),
            "FFmpeg fps=60",
        )
        return plan

    mul = rife_multiplier(fps)
    uhd = force_uhd if force_uhd is not None else width >= UHD_MIN_WIDTH
    plan = (
        f"rife×{mul} ({width}x{height} @{fps_label}fps, {model}"
        f"{', uhd' if uhd else ''}) → 60fps"
    )
    if dry_run:
        return plan

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_rife = out_path.with_name(f".{out_path.stem}.rife.tmp.mkv")
    if tmp_rife.exists():
        tmp_rife.unlink()
    try:
        run_video2x(
            build_video2x_rife_args(
                video2x, file_path, tmp_rife, mul, model, uhd, gpu
            ),
            tmp_rife,
        )
        rife_payload = probe_video(ffprobe, tmp_rife)
        _, _, rife_fps, rife_audio = stream_info(rife_payload)
        copy_video = rife_fps is not None and is_already_60(rife_fps)
        run_checked(
            build_ffmpeg_fps_args(
                ffmpeg, tmp_rife, out_path, rife_audio, copy_video
            ),
            "FFmpeg 60fps master",
        )
    finally:
        if tmp_rife.exists():
            tmp_rife.unlink()

    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Interpolate video to 60fps with Video2X RIFE at source resolution. "
            "Already ~60fps files are skipped. Above 60fps is FFmpeg drop, not RIFE."
        )
    )
    parser.add_argument("input", help="Path to a single video file or directory")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="",
        help="Output directory (default: <input>/60fps)",
    )
    parser.add_argument(
        "-r", "--recurse", action="store_true", help="Process subdirectories"
    )
    parser.add_argument(
        "--rife-model",
        default=DEFAULT_RIFE_MODEL,
        help=f"RIFE model name (default: {DEFAULT_RIFE_MODEL})",
    )
    parser.add_argument(
        "--uhd",
        action="store_true",
        help="Force RIFE Ultra HD mode (default: on when width >= 1920)",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=None,
        help="Vulkan GPU index for Video2X (-d)",
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
    ffmpeg, ffprobe, video2x = resolve_repo_tools()

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
        Path(args.output_dir).resolve() if args.output_dir else input_root / "60fps"
    )

    initial_count = len(files)
    files = filter_output_files(files, output_dir)
    if not files:
        if initial_count:
            print(
                "No source files to process: all inputs lie under the output directory. "
                "Choose a separate output directory (default: 60fps/).",
                file=sys.stderr,
            )
            return 1
        print(f"No supported video files found under: {args.input}")
        return 0

    collisions = find_source_collisions(files, input_root, output_dir)
    if collisions:
        print(
            "Refusing to overwrite source files. Use a separate output directory "
            "(default: 60fps/).",
            file=sys.stderr,
        )
        for source, dest in collisions:
            print(f"  {source} -> {dest}", file=sys.stderr)
        return 1

    force_uhd = True if args.uhd else None
    print(f"Input:     {args.input}")
    print(f"Files:     {len(files)}")
    print(f"Model:     {args.rife_model}")
    print(f"Target:    {int(TARGET_FPS)}fps RIFE at source resolution")
    print(f"Output:    {output_dir}")
    if args.gpu is not None:
        print(f"GPU:       {args.gpu}")
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

        try:
            if args.dry_run:
                plan = convert_file(
                    ffmpeg,
                    ffprobe,
                    video2x,
                    file_path,
                    out_path,
                    args.rife_model,
                    args.gpu,
                    force_uhd,
                    dry_run=True,
                )
                if plan.startswith("skip "):
                    print(f"[skip] {rel} {plan}")
                    skip += 1
                else:
                    print(f"[plan] {rel} -> {out_rel} ({plan})")
                    ok += 1
                continue

            payload = probe_video(ffprobe, file_path)
            _, _, fps, _ = stream_info(payload)
            if fps is not None and is_already_60(fps):
                print(f"[skip] {rel} (already ~{fps:.3g}fps)")
                skip += 1
                continue

            if out_path.exists() and not args.overwrite:
                print(f"[skip] {out_rel} (exists)")
                skip += 1
                continue

            print(f"[run]  {rel} -> {out_rel}")
            plan = convert_file(
                ffmpeg,
                ffprobe,
                video2x,
                file_path,
                out_path,
                args.rife_model,
                args.gpu,
                force_uhd,
                dry_run=False,
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
