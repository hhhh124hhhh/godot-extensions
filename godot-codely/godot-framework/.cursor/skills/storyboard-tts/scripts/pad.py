#!/usr/bin/env python3
"""In-place leading/trailing silence padding used by synthesize.py after TTS."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SILENCE_START_RE = re.compile(r"silence_start:\s*([-\d.]+)")
SILENCE_END_RE = re.compile(r"silence_end:\s*([-\d.]+)")
EDGE_EPSILON = 0.02
DEFAULT_DURATION = 0.4
DEFAULT_THRESHOLD = -50.0


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
    probe = ffmpeg.parent / name
    if probe.is_file():
        return probe
    print(
        f"ffprobe not found next to ffmpeg at {ffmpeg.parent}. "
        "Install a full FFmpeg build that includes ffprobe.",
        file=sys.stderr,
    )
    sys.exit(1)


def get_duration(ffprobe: Path, file_path: Path) -> float:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Could not read duration for: {file_path}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Invalid duration for: {file_path}") from exc


def parse_silence_intervals(ffmpeg_stderr: str) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    current_start: float | None = None
    for line in ffmpeg_stderr.splitlines():
        start_match = SILENCE_START_RE.search(line)
        if start_match:
            current_start = float(start_match.group(1))
            continue
        end_match = SILENCE_END_RE.search(line)
        if end_match and current_start is not None:
            intervals.append((current_start, float(end_match.group(1))))
            current_start = None
    if current_start is not None:
        intervals.append((current_start, -1.0))
    return intervals


def measure_edge_silence(
    ffmpeg: Path, file_path: Path, duration: float, threshold: float
) -> tuple[float, float]:
    result = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-i",
            str(file_path),
            "-af",
            f"silencedetect=noise={threshold}dB:d=0.01",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg silencedetect failed for: {file_path}")

    intervals = parse_silence_intervals(result.stderr)
    leading = 0.0
    trailing = 0.0

    for start, end in intervals:
        if end < 0:
            end = duration
        if start <= EDGE_EPSILON:
            leading = max(leading, end - max(0.0, start))
        if end >= duration - EDGE_EPSILON:
            trailing = max(trailing, end - start)

    leading = min(leading, duration)
    trailing = min(trailing, duration)
    return leading, trailing


def compute_pads(
    leading: float,
    trailing: float,
    target: float,
    pad_start: bool,
    pad_end: bool,
) -> tuple[float, float]:
    start_pad = max(0.0, target - leading) if pad_start else 0.0
    end_pad = max(0.0, target - trailing) if pad_end else 0.0
    return start_pad, end_pad


def build_filter(start_pad: float, end_pad: float) -> str | None:
    if start_pad <= 0 and end_pad <= 0:
        return None
    parts: list[str] = []
    if start_pad > 0:
        parts.append(f"areverse,apad=pad_dur={start_pad:.6f},areverse")
    if end_pad > 0:
        parts.append(f"apad=pad_dur={end_pad:.6f}")
    return ",".join(parts)


def pad_file(ffmpeg: Path, file_path: Path, out_path: Path, filter_str: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-y",
            "-i",
            str(file_path),
            "-af",
            filter_str,
            str(out_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"FFmpeg pad failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def ensure_padded(
    file_path: Path,
    *,
    duration: float = DEFAULT_DURATION,
    threshold: float = DEFAULT_THRESHOLD,
    pad_start: bool = True,
    pad_end: bool = True,
    ffmpeg: Path | None = None,
    ffprobe: Path | None = None,
) -> tuple[float, float]:
    """Pad a file in place so each enabled edge has at least `duration` seconds of silence.

    Returns ``(start_pad, end_pad)`` actually added. Both ``0`` means the file
    already met the target and was left unchanged.
    """
    if duration <= 0:
        raise ValueError("duration must be greater than 0")
    if not pad_start and not pad_end:
        raise ValueError("at least one of pad_start or pad_end must be enabled")

    if ffmpeg is None:
        ffmpeg = resolve_ffmpeg()
    if ffprobe is None:
        ffprobe = resolve_ffprobe(ffmpeg)

    file_path = file_path.resolve()
    total = get_duration(ffprobe, file_path)
    leading, trailing = measure_edge_silence(ffmpeg, file_path, total, threshold)
    start_pad, end_pad = compute_pads(
        leading, trailing, duration, pad_start, pad_end
    )
    filter_str = build_filter(start_pad, end_pad)
    if filter_str is None:
        return 0.0, 0.0

    tmp_path = file_path.with_name(f"{file_path.stem}.__padtmp{file_path.suffix}")
    try:
        pad_file(ffmpeg, file_path, tmp_path, filter_str)
        tmp_path.replace(file_path)
    except Exception:
        if tmp_path.is_file():
            tmp_path.unlink(missing_ok=True)
        raise
    return start_pad, end_pad
