#!/usr/bin/env python3
"""Upscale below-4K video with Video2X, then encode unified 4K H.265 Main10 masters.

Preserves source frame rate. Does not interpolate or duplicate frames to 60fps.
"""

from __future__ import annotations

import argparse
import json
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

TARGET_WIDTH = 3840
TARGET_HEIGHT = 2160
VIDEO_BITRATE = "40M"
AUDIO_BITRATE = "320k"
DEFAULT_MODEL = "realesrgan-plus"
ANIME_MODEL = "realesr-animevideov3"


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


def is_already_4k(width: int, height: int) -> bool:
    return width >= TARGET_WIDTH and height >= TARGET_HEIGHT


# Video2X ships limited Real-ESRGAN weights; pick only scales that exist.
MODEL_SCALES: dict[str, tuple[int, ...]] = {
    "realesrgan-plus": (4,),
    "realesrgan-plus-anime": (4,),
    "realesr-animevideov3": (2, 3, 4),
}


def pick_scale(width: int, height: int, model: str = DEFAULT_MODEL) -> int:
    scales = MODEL_SCALES.get(model, (2, 4))
    for scale in scales:
        if width * scale >= TARGET_WIDTH and height * scale >= TARGET_HEIGHT:
            return scale
    return scales[-1]


def run_checked(cmd: list[str], label: str) -> None:
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"{label} failed" + (f"\n{detail}" if detail else "")
        )


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
        "Video2X upscale failed" + (f"\n{detail}" if detail else "")
    )


def build_video2x_args(
    video2x: Path,
    file_path: Path,
    out_path: Path,
    scale: int,
    model: str,
    gpu: int | None,
) -> list[str]:
    cmd = [
        str(video2x),
        "-i",
        str(file_path),
        "-o",
        str(out_path),
        "-p",
        "realesrgan",
        "-s",
        str(scale),
        "--realesrgan-model",
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
    if gpu is not None:
        cmd.extend(["-d", str(gpu)])
    return cmd


def build_ffmpeg_final_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    has_audio: bool,
) -> list[str]:
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
        "-vf",
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos,format=yuv420p10le",
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
        "profile=main10",
    ]
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
    upscaled_path: Path,
    model: str,
    gpu: int | None,
    clean_upscaled: bool,
    dry_run: bool,
) -> str:
    payload = probe_video(ffprobe, file_path)
    width, height, fps, has_audio = stream_info(payload)
    already_4k = is_already_4k(width, height)
    fps_label = f"{fps:.3g}" if fps else "?"

    if already_4k:
        plan = f"ffmpeg-only ({width}x{height} @{fps_label}fps → 4K Main10, fps kept)"
        encode_src = file_path
        if dry_run:
            return plan
        out_path.parent.mkdir(parents=True, exist_ok=True)
        run_checked(
            build_ffmpeg_final_args(ffmpeg, encode_src, out_path, has_audio),
            "FFmpeg final encode",
        )
        return plan

    scale = pick_scale(width, height, model)
    plan = (
        f"video2x×{scale} ({width}x{height} @{fps_label}fps, {model}) → "
        f"ffmpeg 4K Main10 (fps kept)"
    )
    if dry_run:
        return plan

    upscaled_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write via a sibling temp file so a failed run does not leave a bad final.
    # Must stay on the same drive as upscaled_path (Video2X crashes after write
    # are common on Windows; we still need a durable path to validate).
    tmp_upscaled = upscaled_path.with_name(
        f".{upscaled_path.stem}.tmp{upscaled_path.suffix}"
    )
    if tmp_upscaled.exists():
        tmp_upscaled.unlink()
    try:
        run_video2x(
            build_video2x_args(video2x, file_path, tmp_upscaled, scale, model, gpu),
            tmp_upscaled,
        )
        if upscaled_path.exists():
            upscaled_path.unlink()
        shutil.move(str(tmp_upscaled), str(upscaled_path))
    finally:
        if tmp_upscaled.exists():
            tmp_upscaled.unlink()

    # Re-probe upscaled for audio (should match source).
    up_payload = probe_video(ffprobe, upscaled_path)
    _, _, _, up_has_audio = stream_info(up_payload)

    run_checked(
        build_ffmpeg_final_args(ffmpeg, upscaled_path, out_path, up_has_audio),
        "FFmpeg final encode",
    )

    if clean_upscaled and upscaled_path.exists():
        upscaled_path.unlink()

    return plan


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upscale below-4K video with Video2X, then encode unified "
            "3840x2160 H.265 Main10 40Mbps + AAC 320kbps MP4 "
            "(source frame rate preserved)."
        )
    )
    parser.add_argument("input", help="Path to a single video file or directory")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="",
        help="Final output directory (default: <input>/4k)",
    )
    parser.add_argument(
        "--upscaled-dir",
        default="",
        help="Video2X intermediate directory (default: <input>/4k-upscaled)",
    )
    parser.add_argument(
        "-r", "--recurse", action="store_true", help="Process subdirectories"
    )
    parser.add_argument(
        "--anime",
        action="store_true",
        help=f"Use Real-ESRGAN anime model ({ANIME_MODEL})",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=None,
        help="Vulkan GPU index for Video2X (-d)",
    )
    parser.add_argument(
        "--clean-upscaled",
        action="store_true",
        help="Delete Video2X intermediate after successful final encode",
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
        Path(args.output_dir).resolve() if args.output_dir else input_root / "4k"
    )
    upscaled_dir = (
        Path(args.upscaled_dir).resolve()
        if args.upscaled_dir
        else input_root / "4k-upscaled"
    )

    initial_count = len(files)
    files = filter_output_files(files, output_dir, upscaled_dir)
    if not files:
        if initial_count:
            print(
                "No source files to process: all inputs lie under output directories. "
                "Choose separate output directories (default: 4k/ and 4k-upscaled/).",
                file=sys.stderr,
            )
            return 1
        print(f"No supported video files found under: {args.input}")
        return 0

    collisions = find_source_collisions(files, input_root, output_dir)
    if collisions:
        print(
            "Refusing to overwrite source files. Use a separate output directory "
            "(default: 4k/).",
            file=sys.stderr,
        )
        for source, dest in collisions:
            print(f"  {source} -> {dest}", file=sys.stderr)
        return 1

    model = ANIME_MODEL if args.anime else DEFAULT_MODEL
    print(f"Input:     {args.input}")
    print(f"Files:     {len(files)}")
    print(f"Model:     {model}")
    print(
        f"Target:    {TARGET_WIDTH}x{TARGET_HEIGHT} H.265 Main10 {VIDEO_BITRATE} "
        f"+ AAC {AUDIO_BITRATE} (source fps kept)"
    )
    print(f"Output:    {output_dir}")
    print(f"Upscaled:  {upscaled_dir}")
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
        upscaled_path = upscaled_dir / Path(rel).with_suffix(".mkv")

        if out_path.exists() and not args.overwrite and not args.dry_run:
            print(f"[skip] {out_rel} (exists)")
            skip += 1
            continue

        try:
            if args.dry_run:
                plan = convert_file(
                    ffmpeg,
                    ffprobe,
                    video2x,
                    file_path,
                    out_path,
                    upscaled_path,
                    model,
                    args.gpu,
                    args.clean_upscaled,
                    dry_run=True,
                )
                print(f"[plan] {rel} -> {out_rel} ({plan})")
                ok += 1
                continue

            print(f"[run]  {rel} -> {out_rel}")
            plan = convert_file(
                ffmpeg,
                ffprobe,
                video2x,
                file_path,
                out_path,
                upscaled_path,
                model,
                args.gpu,
                args.clean_upscaled,
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
