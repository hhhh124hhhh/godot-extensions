#!/usr/bin/env python3
"""
Build a shot-to-audio duration report from Chinese/ and English/ WAV folders.

Usage
-----
    .dependency/python/python \\
        .cursor/skills/storyboard-tts/scripts/duration_report.py \\
        --storyboard path/to/storyboard.md \\
        --audio-dir path/to/output \\
        -o path/to/output/speech-timeline.md

Optional shots JSON from parse_storyboard.py (else re-parses storyboard):

    --shots path/to/shots.json
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path


# Import sibling parser when run as a file
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from parse_storyboard import parse_storyboard  # noqa: E402


AUDIO_EXTS = (".wav", ".mp3", ".ogg", ".flac", ".m4a")


def wav_duration_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                return None
            return frames / float(rate)
    except wave.Error:
        return None
    except Exception:
        return None


def pcm_duration_fallback(path: Path) -> float | None:
    """Best-effort for non-WAV using file size is unreliable — skip."""
    return None


def audio_duration_seconds(path: Path | None) -> float | None:
    if path is None or not path.is_file():
        return None
    if path.suffix.lower() == ".wav":
        return wav_duration_seconds(path)
    return pcm_duration_fallback(path)


def find_audio(lang_dir: Path, shot_id: str) -> Path | None:
    if not lang_dir.is_dir():
        return None
    for ext in AUDIO_EXTS:
        candidate = lang_dir / f"{shot_id}{ext}"
        if candidate.is_file():
            return candidate
    # Also accept unpadded numeric ids
    if shot_id.isdigit():
        bare = str(int(shot_id))
        for ext in AUDIO_EXTS:
            candidate = lang_dir / f"{bare}{ext}"
            if candidate.is_file():
                return candidate
    return None


def fmt_seconds(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}"


def rel_display(path: Path | None, base: Path) -> str:
    if path is None:
        return "—"
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def load_shots(storyboard: Path, shots_json: Path | None) -> dict:
    if shots_json is not None:
        if not shots_json.is_file():
            print(f"Shots JSON not found: {shots_json}", file=sys.stderr)
            sys.exit(1)
        return json.loads(shots_json.read_text(encoding="utf-8-sig"))
    if not storyboard.is_file():
        print(f"Storyboard not found: {storyboard}", file=sys.stderr)
        sys.exit(1)
    data = parse_storyboard(storyboard.read_text(encoding="utf-8-sig"))
    if data["shot_count"] == 0:
        print(f"No shots found in {storyboard}", file=sys.stderr)
        sys.exit(1)
    return data


def build_report(data: dict, audio_dir: Path) -> str:
    chinese_dir = audio_dir / "Chinese"
    english_dir = audio_dir / "English"
    title = data.get("title", "Untitled")
    shots = data.get("shots", [])

    rows: list[str] = []
    detail_blocks: list[str] = []
    total_zh = 0.0
    total_en = 0.0
    count_zh = 0
    count_en = 0

    for shot in shots:
        shot_id = shot["id"]
        shot_title = shot.get("title", "")
        zh_path = None if shot.get("chinese_skip") else find_audio(chinese_dir, shot_id)
        en_path = None if shot.get("english_skip") else find_audio(english_dir, shot_id)
        zh_dur = audio_duration_seconds(zh_path)
        en_dur = audio_duration_seconds(en_path)

        if zh_dur is not None:
            total_zh += zh_dur
            count_zh += 1
        if en_dur is not None:
            total_en += en_dur
            count_en += 1

        zh_status = "skipped (no VO)" if shot.get("chinese_skip") else rel_display(zh_path, audio_dir)
        en_status = "skipped (no VO)" if shot.get("english_skip") else rel_display(en_path, audio_dir)
        if not shot.get("chinese_skip") and zh_path is None:
            zh_status = "missing"
        if not shot.get("english_skip") and en_path is None:
            en_status = "missing"

        rows.append(
            f"| {shot_id} | {shot_title} | {zh_status} | {fmt_seconds(zh_dur)} | "
            f"{en_status} | {fmt_seconds(en_dur)} |"
        )

        lines = [
            f"### Shot {shot_id} — {shot_title}",
            f"- **Chinese audio:** {zh_status}"
            + (f" ({fmt_seconds(zh_dur)} s)" if zh_dur is not None else ""),
            f"- **English audio:** {en_status}"
            + (f" ({fmt_seconds(en_dur)} s)" if en_dur is not None else ""),
        ]
        if shot.get("chinese"):
            lines.append(f"- **Chinese text:** {shot['chinese']}")
        if shot.get("english"):
            lines.append(f"- **English text:** {shot['english']}")
        if shot.get("duration_hint"):
            lines.append(f"- **Storyboard duration hint:** {shot['duration_hint']}")
        detail_blocks.append("\n".join(lines))

    body = [
        f"# Storyboard Speech — {title}",
        "",
        f"- **Audio root:** `{audio_dir.as_posix()}`",
        f"- **Shots:** {len(shots)}",
        f"- **Chinese total duration:** {fmt_seconds(total_zh)} s ({count_zh} files)",
        f"- **English total duration:** {fmt_seconds(total_en)} s ({count_en} files)",
        "",
        "## Timeline",
        "",
        "| Shot | Title | Chinese file | Chinese (s) | English file | English (s) |",
        "|------|-------|--------------|-------------|----------------|-------------|",
        *rows,
        "",
        "## Shots",
        "",
        "\n\n".join(detail_blocks),
        "",
    ]
    return "\n".join(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write shot-to-audio duration markdown report.",
    )
    parser.add_argument(
        "--storyboard",
        required=True,
        help="Path to storyboard markdown (for titles / VO text)",
    )
    parser.add_argument(
        "--audio-dir",
        required=True,
        help="Directory containing Chinese/ and English/ subfolders",
    )
    parser.add_argument(
        "--shots",
        help="Optional shots JSON from parse_storyboard.py",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output markdown path (default: <audio-dir>/speech-timeline.md)",
    )
    args = parser.parse_args(argv)

    storyboard = Path(args.storyboard).expanduser()
    audio_dir = Path(args.audio_dir).expanduser()
    shots_json = Path(args.shots).expanduser() if args.shots else None
    output = (
        Path(args.output).expanduser()
        if args.output
        else (audio_dir / "speech-timeline.md")
    )

    if not audio_dir.is_dir():
        print(f"Audio directory not found: {audio_dir}", file=sys.stderr)
        return 1

    data = load_shots(storyboard, shots_json)
    report = build_report(data, audio_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
