#!/usr/bin/env python3
"""
Build one concatenated SRT per language from shot VO text + WAV durations.

Timeline is the continuous VO track: each shot with audio starts when the
previous ends (no gap). Within a shot, long narration is split on sentence
punctuation into multiple cues; cue durations share the shot WAV length by
character-count weight.

Usage
-----
    .dependency/python/python \\
        .cursor/skills/storyboard-tts/scripts/write_subtitles.py \\
        --audio-dir path/to/output \\
        --shots path/to/output/shots.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from duration_report import (  # noqa: E402
    audio_duration_seconds,
    find_audio,
)
from parse_storyboard import parse_storyboard  # noqa: E402


LANG_SPECS = (
    ("chinese", "Chinese", "chinese", "chinese_skip", "Chinese.srt"),
    ("english", "English", "english", "english_skip", "English.srt"),
)

# Chinese / fullwidth terminators always end a sentence.
# ASCII .!? end a sentence only at EOS or before whitespace / closing quote.
_SENTENCE_END_RE = re.compile(
    r".+?(?:"
    r"[。！？；…]+|"
    r"[.!?]+(?=\s|$|[\"'”’」』）\)】])|"
    r"[.!?]+$"
    r")",
    re.DOTALL,
)


def srt_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000.0))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def char_weight(text: str) -> int:
    """Non-whitespace length; minimum 1 so empty-looking scraps still get time."""
    n = len(re.sub(r"\s+", "", text))
    return n if n > 0 else 1


def split_sentences(text: str) -> list[str]:
    """Split VO text on sentence punctuation; keep terminators with the sentence."""
    text = text.strip()
    if not text:
        return []

    parts: list[str] = []
    pos = 0
    while pos < len(text):
        match = _SENTENCE_END_RE.search(text, pos)
        if match is None:
            tail = text[pos:].strip()
            if tail:
                parts.append(tail)
            break
        if match.start() > pos:
            gap = text[pos : match.start()].strip()
            if gap:
                parts.append(gap)
        piece = match.group(0).strip()
        if piece:
            parts.append(piece)
        pos = match.end()
        while pos < len(text) and text[pos].isspace():
            pos += 1

    return parts if parts else [text]


def allocate_durations(weights: list[int], total: float) -> list[float]:
    """Split total seconds by integer weights; last slice absorbs rounding residue."""
    if not weights:
        return []
    if total <= 0:
        return [0.0] * len(weights)
    if len(weights) == 1:
        return [total]

    wsum = float(sum(weights))
    durs: list[float] = []
    used = 0.0
    for w in weights[:-1]:
        d = total * (w / wsum)
        durs.append(d)
        used += d
    durs.append(max(total - used, 0.0))
    return durs


def cues_for_shot(text: str, shot_start: float, shot_dur: float) -> list[tuple[float, float, str]]:
    """Return (start, end, cue_text) rows inside one shot window."""
    sentences = split_sentences(text)
    weights = [char_weight(s) for s in sentences]
    durs = allocate_durations(weights, shot_dur)
    shot_end = shot_start + shot_dur

    rows: list[tuple[float, float, str]] = []
    cursor = shot_start
    for i, (sentence, dur) in enumerate(zip(sentences, durs)):
        start = cursor
        end = shot_end if i == len(sentences) - 1 else cursor + dur
        if end <= start:
            end = start + 0.001
        rows.append((start, end, sentence))
        cursor = end
    return rows


def load_shots(storyboard: Path | None, shots_json: Path | None) -> dict:
    if shots_json is not None:
        if not shots_json.is_file():
            print(f"Shots JSON not found: {shots_json}", file=sys.stderr)
            sys.exit(1)
        return json.loads(shots_json.read_text(encoding="utf-8-sig"))
    if storyboard is None or not storyboard.is_file():
        print("Provide --shots or an existing --storyboard.", file=sys.stderr)
        sys.exit(1)
    data = parse_storyboard(storyboard.read_text(encoding="utf-8-sig"))
    if data["shot_count"] == 0:
        print(f"No shots found in {storyboard}", file=sys.stderr)
        sys.exit(1)
    return data


def build_srt_for_lang(
    shots: list[dict],
    audio_dir: Path,
    lang_dir_name: str,
    text_key: str,
    skip_key: str,
) -> tuple[str, int, float]:
    """Return (srt_body, cue_count, total_seconds)."""
    lang_dir = audio_dir / lang_dir_name
    cues: list[str] = []
    cursor = 0.0
    index = 0

    for shot in shots:
        if shot.get(skip_key):
            continue
        text = (shot.get(text_key) or "").strip()
        if not text:
            continue
        path = find_audio(lang_dir, shot["id"])
        dur = audio_duration_seconds(path)
        if dur is None or dur <= 0:
            print(
                f"[skip subtitle] {lang_dir_name} shot {shot['id']}: missing audio",
                file=sys.stderr,
            )
            continue

        shot_start = cursor
        for start, end, cue_text in cues_for_shot(text, shot_start, dur):
            index += 1
            cues.append(
                "\n".join(
                    [
                        str(index),
                        f"{srt_timestamp(start)} --> {srt_timestamp(end)}",
                        cue_text,
                        "",
                    ]
                )
            )
        cursor = shot_start + dur

    body = "\n".join(cues).rstrip() + ("\n" if cues else "")
    return body, index, cursor


def write_subtitles(
    data: dict,
    audio_dir: Path,
    languages: str = "both",
) -> list[Path]:
    written: list[Path] = []
    do_zh = languages in ("both", "chinese")
    do_en = languages in ("both", "english")
    shots = data.get("shots", [])

    for lang_flag, dir_name, text_key, skip_key, filename in LANG_SPECS:
        if lang_flag == "chinese" and not do_zh:
            continue
        if lang_flag == "english" and not do_en:
            continue
        body, count, total = build_srt_for_lang(
            shots, audio_dir, dir_name, text_key, skip_key
        )
        out = audio_dir / filename
        if count == 0:
            print(f"No subtitle cues for {filename} (skipped).", file=sys.stderr)
            continue
        out.write_text(body, encoding="utf-8")
        print(f"Wrote {out} ({count} cues, {total:.3f} s)")
        written.append(out)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Write concatenated Chinese.srt / English.srt from shot VO + WAV durations.",
    )
    parser.add_argument(
        "--storyboard",
        help="Storyboard markdown (used when --shots is omitted)",
    )
    parser.add_argument(
        "--shots",
        help="shots.json from parse_storyboard / synthesize",
    )
    parser.add_argument(
        "--audio-dir",
        required=True,
        help="Directory containing Chinese/ and English/ WAV folders",
    )
    parser.add_argument(
        "--lang",
        choices=("both", "chinese", "english"),
        default="both",
        help="Which language SRT files to write (default: both)",
    )
    args = parser.parse_args(argv)

    if not args.storyboard and not args.shots:
        print("Provide --storyboard and/or --shots.", file=sys.stderr)
        return 1

    audio_dir = Path(args.audio_dir).expanduser()
    if not audio_dir.is_dir():
        print(f"Audio directory not found: {audio_dir}", file=sys.stderr)
        return 1

    storyboard = Path(args.storyboard).expanduser() if args.storyboard else None
    shots_json = Path(args.shots).expanduser() if args.shots else None
    if shots_json is None:
        candidate = audio_dir / "shots.json"
        if candidate.is_file():
            shots_json = candidate

    data = load_shots(storyboard, shots_json)
    written = write_subtitles(data, audio_dir, args.lang)
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
