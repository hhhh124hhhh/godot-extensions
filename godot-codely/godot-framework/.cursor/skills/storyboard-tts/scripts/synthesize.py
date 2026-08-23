#!/usr/bin/env python3
"""
Batch-synthesize storyboard VO (Chinese + English) with IndexTTS2.

Loads the model **once**, then writes:

    <storyboard-dir>/<voice-stem>/Chinese/<shot-id>.wav
    <storyboard-dir>/<voice-stem>/English/<shot-id>.wav

Each WAV is padded in place (default 0.4 s leading/trailing silence) via
`pad.py` `ensure_padded`, unless `--no-pad`.

Run through the **index-tts** interpreter only:

    .dependency/index-tts/.venv/Scripts/python.exe \\
        .cursor/skills/storyboard-tts/scripts/synthesize.py \\
        --storyboard path/to/storyboard.md \\
        --voice path/to/ref.wav \\
        --fp16 --report
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace


TOOL_NAME = "index-tts"
SCRIPT_DIR = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_tts_helpers(repo_root: Path):
    tts_path = repo_root / ".cursor" / "skills" / "ai-text-to-speech" / "scripts" / "tts.py"
    if not tts_path.is_file():
        print(f"ai-text-to-speech tts.py not found: {tts_path}", file=sys.stderr)
        sys.exit(1)
    return load_module("ai_tts_single", tts_path)


def load_parse_storyboard():
    return load_module("parse_storyboard", SCRIPT_DIR / "parse_storyboard.py")


def load_duration_report():
    return load_module("duration_report", SCRIPT_DIR / "duration_report.py")


def load_write_subtitles():
    return load_module("write_subtitles", SCRIPT_DIR / "write_subtitles.py")


def load_pad():
    pad_path = SCRIPT_DIR / "pad.py"
    if not pad_path.is_file():
        print(f"storyboard-tts pad.py not found: {pad_path}", file=sys.stderr)
        sys.exit(1)
    return load_module("storyboard_tts_pad", pad_path)


@dataclass
class Job:
    shot_id: str
    lang: str  # "zh" | "en"
    text: str
    voice: Path
    output: Path


def build_jobs(
    data: dict,
    audio_dir: Path,
    voice_default: Path,
    voice_zh: Path | None,
    voice_en: Path | None,
    languages: str,
) -> list[Job]:
    jobs: list[Job] = []
    zh_voice = voice_zh or voice_default
    en_voice = voice_en or voice_default
    do_zh = languages in ("both", "chinese")
    do_en = languages in ("both", "english")

    for shot in data.get("shots", []):
        sid = shot["id"]
        if do_zh and not shot.get("chinese_skip"):
            text = (shot.get("chinese") or "").strip()
            if text:
                jobs.append(
                    Job(
                        shot_id=sid,
                        lang="zh",
                        text=text,
                        voice=zh_voice,
                        output=audio_dir / "Chinese" / f"{sid}.wav",
                    )
                )
        if do_en and not shot.get("english_skip"):
            text = (shot.get("english") or "").strip()
            if text:
                jobs.append(
                    Job(
                        shot_id=sid,
                        lang="en",
                        text=text,
                        voice=en_voice,
                        output=audio_dir / "English" / f"{sid}.wav",
                    )
                )
    return jobs


def voice_stem_for_audio_dir(
    voice: Path | None,
    voice_zh: Path | None,
    voice_en: Path | None,
    languages: str,
) -> str | None:
    if voice is not None:
        return voice.stem
    if languages == "english" and voice_en is not None:
        return voice_en.stem
    if voice_zh is not None:
        return voice_zh.stem
    if voice_en is not None:
        return voice_en.stem
    return None


def resolve_audio_dir(
    args: argparse.Namespace,
    storyboard_path: Path | None,
    shots_path: Path | None,
    voice: Path | None,
    voice_zh: Path | None,
    voice_en: Path | None,
) -> Path | None:
    if args.audio_dir:
        return Path(args.audio_dir).expanduser()
    stem = voice_stem_for_audio_dir(voice, voice_zh, voice_en, args.lang)
    if storyboard_path is not None and stem:
        return storyboard_path.parent / stem
    if shots_path is not None:
        return shots_path.parent
    return None


def parse_emotion_args(args: argparse.Namespace) -> SimpleNamespace:
    return SimpleNamespace(
        emotion_audio=args.emotion_audio,
        emotion_vector=args.emotion_vector,
        emotion_text=args.emotion_text,
        emotion_from_text=args.emotion_from_text,
        emotion_weight=args.emotion_weight,
        random=args.random,
        verbose=args.verbose,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch storyboard TTS (Chinese/English) with one model load.",
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--storyboard", help="storyboard markdown path")
    src.add_argument("--shots", help="shots.json from parse_storyboard.py")

    parser.add_argument(
        "--audio-dir",
        help="Output root (default: <storyboard-dir>/<voice-stem>/; creates Chinese/ and English/)",
    )
    parser.add_argument(
        "--voice",
        help="Default speaker reference for both languages",
    )
    parser.add_argument(
        "--voice-zh",
        help="Chinese speaker reference (overrides --voice for Chinese/)",
    )
    parser.add_argument(
        "--voice-en",
        help="English speaker reference (overrides --voice for English/)",
    )
    parser.add_argument(
        "--lang",
        choices=("both", "chinese", "english"),
        default="both",
        help="Which language folders to synthesize (default: both)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process the first N jobs (0 = all; use 1 for a trial line)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing WAV files",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write speech-timeline.md and language SRT subtitles after synthesis",
    )
    parser.add_argument(
        "--report-out",
        help="Timeline path (default: <audio-dir>/speech-timeline.md)",
    )
    parser.add_argument(
        "--no-subtitles",
        action="store_true",
        help="With --report, skip Chinese.srt / English.srt",
    )
    parser.add_argument(
        "--write-text",
        action="store_true",
        help="Also save line text under <audio-dir>/_text/ (debug)",
    )
    parser.add_argument(
        "--no-pad",
        action="store_true",
        help="Skip in-place edge silence padding after synthesis",
    )
    parser.add_argument(
        "--pad-duration",
        type=float,
        default=0.4,
        help="Target leading/trailing silence in seconds (default: 0.4)",
    )
    parser.add_argument(
        "--pad-threshold",
        type=float,
        default=-50.0,
        help="Silence threshold in dB for padding (default: -50)",
    )
    parser.add_argument(
        "--model-dir",
        default=None,
        help="IndexTTS-2 checkpoints dir (default: <index-tts>/checkpoints)",
    )
    parser.add_argument("--fp16", action="store_true", help="FP16 inference")
    parser.add_argument("--device", default=None, help="cpu, cuda, cuda:0, mps, …")
    parser.add_argument("--emotion-audio", help="Emotion reference audio")
    parser.add_argument("--emotion-text", help="Natural-language emotion description")
    parser.add_argument(
        "--emotion-from-text",
        action="store_true",
        help="Infer emotion from synthesis text",
    )
    parser.add_argument("--emotion-vector", help="8-float emotion vector")
    parser.add_argument(
        "--emotion-weight",
        type=float,
        default=1.0,
        help="emo_alpha in [0, 1] (default: 1.0)",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Stochastic sampling (may reduce clone fidelity)",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not (0.0 <= args.emotion_weight <= 1.0):
        print("--emotion-weight must be between 0.0 and 1.0", file=sys.stderr)
        return 1

    if not args.voice and not (args.voice_zh and args.voice_en):
        # Allow --voice alone, or both --voice-zh and --voice-en without --voice
        if not args.voice_zh and not args.voice_en:
            print("Provide --voice, or --voice-zh / --voice-en.", file=sys.stderr)
            return 1
        if args.lang == "both" and not (args.voice_zh and args.voice_en) and not args.voice:
            print(
                "For --lang both without --voice, both --voice-zh and --voice-en are required.",
                file=sys.stderr,
            )
            return 1
        if args.lang == "chinese" and not (args.voice or args.voice_zh):
            print("Chinese synthesis needs --voice or --voice-zh.", file=sys.stderr)
            return 1
        if args.lang == "english" and not (args.voice or args.voice_en):
            print("English synthesis needs --voice or --voice-en.", file=sys.stderr)
            return 1

    # Find repo root without tts helpers first
    repo_root = None
    for parent in [SCRIPT_DIR, *SCRIPT_DIR.parents]:
        if (parent / ".dependency" / "manifest.json").is_file():
            repo_root = parent
            break
    if repo_root is None:
        print(
            "Could not find repo root (.dependency/manifest.json).",
            file=sys.stderr,
        )
        return 1

    tts_lib = load_tts_helpers(repo_root)
    # Validate index-tts is registered
    python_bin = tts_lib.resolve_tool_bin(repo_root, TOOL_NAME)
    index_tts_root = tts_lib.resolve_index_tts_root(repo_root, python_bin)

    storyboard_path: Path | None = None
    shots_path: Path | None = None
    if args.shots:
        shots_path = Path(args.shots).expanduser()
        if not shots_path.is_file():
            print(f"Shots JSON not found: {shots_path}", file=sys.stderr)
            return 1
        data = json.loads(shots_path.read_text(encoding="utf-8-sig"))
    else:
        storyboard_path = Path(args.storyboard).expanduser()
        if not storyboard_path.is_file():
            print(f"Storyboard not found: {storyboard_path}", file=sys.stderr)
            return 1
        parse_mod = load_parse_storyboard()
        data = parse_mod.parse_storyboard(storyboard_path.read_text(encoding="utf-8-sig"))
        if data["shot_count"] == 0:
            print(f"No shots found in {storyboard_path}", file=sys.stderr)
            return 1

    voice_default = Path(args.voice).expanduser() if args.voice else None
    voice_zh = Path(args.voice_zh).expanduser() if args.voice_zh else None
    voice_en = Path(args.voice_en).expanduser() if args.voice_en else None

    for label, path in (("voice", voice_default), ("voice-zh", voice_zh), ("voice-en", voice_en)):
        if path is not None and not path.is_file():
            print(f"Voice not found ({label}): {path}", file=sys.stderr)
            return 1

    audio_dir = resolve_audio_dir(
        args, storyboard_path, shots_path, voice_default, voice_zh, voice_en
    )
    if audio_dir is None:
        print(
            "Need --audio-dir, or --storyboard plus a voice path to name "
            "<storyboard-dir>/<voice-stem>/.",
            file=sys.stderr,
        )
        return 1
    audio_dir.mkdir(parents=True, exist_ok=True)
    (audio_dir / "Chinese").mkdir(parents=True, exist_ok=True)
    (audio_dir / "English").mkdir(parents=True, exist_ok=True)

    if storyboard_path is not None:
        shots_out = audio_dir / "shots.json"
        shots_out.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {shots_out} ({data['shot_count']} shots)")

    if voice_default is None:
        # Dummy not used when both langs have dedicated voices; pick any existing for default fallback
        voice_default = voice_zh or voice_en
        assert voice_default is not None

    jobs = build_jobs(data, audio_dir, voice_default, voice_zh, voice_en, args.lang)
    if not jobs:
        print("No VO jobs to run (all skipped or empty).", file=sys.stderr)
        return 1

    pad_mod = None
    ffmpeg = None
    ffprobe = None
    if not args.no_pad:
        if args.pad_duration <= 0:
            print("--pad-duration must be greater than 0.", file=sys.stderr)
            return 1
        pad_mod = load_pad()
        ffmpeg = pad_mod.resolve_ffmpeg()
        ffprobe = pad_mod.resolve_ffprobe(ffmpeg)
        print(
            f"Pad:     {args.pad_duration} s each edge "
            f"(threshold {args.pad_threshold} dB)"
        )

    pending: list[Job] = []
    skipped_jobs: list[Job] = []
    for job in jobs:
        if job.output.is_file() and not args.force:
            skipped_jobs.append(job)
            print(f"[skip exists] {job.lang} {job.shot_id} -> {job.output.name}")
            continue
        pending.append(job)
    skipped = len(skipped_jobs)

    if args.limit and args.limit > 0:
        pending = pending[: args.limit]
        print(f"Limit: processing {len(pending)} job(s)")

    pad_failed: list[str] = []
    if pad_mod is not None and skipped_jobs:
        print(f"Padding {len(skipped_jobs)} existing WAV(s)…")
        for job in skipped_jobs:
            if not apply_padding(
                pad_mod,
                ffmpeg,
                ffprobe,
                job,
                args.pad_duration,
                args.pad_threshold,
            ):
                pad_failed.append(f"{job.shot_id}.{job.lang}")

    if not pending:
        print(f"Nothing to synthesize (skipped={skipped}, total={len(jobs)}).")
        if args.report:
            report_rc = write_report(args, data, audio_dir, storyboard_path)
            return 1 if pad_failed else report_rc
        return 1 if pad_failed else 0

    model_dir = (
        Path(args.model_dir).expanduser()
        if args.model_dir
        else (index_tts_root / "checkpoints")
    )
    cfg_path = model_dir / "config.yaml"
    if not cfg_path.is_file():
        print(
            f"Missing model config: {cfg_path}. "
            "Download IndexTTS-2 checkpoints (see ai-text-to-speech Setup).",
            file=sys.stderr,
        )
        return 1

    if str(index_tts_root) not in sys.path:
        sys.path.insert(0, str(index_tts_root))

    try:
        from indextts.infer_v2 import IndexTTS2
    except ImportError as exc:
        print(
            f"Failed to import IndexTTS2 from {index_tts_root}: {exc}\n"
            "Run this script with the index-tts interpreter, after uv sync.",
            file=sys.stderr,
        )
        return 1

    init_kwargs: dict = {
        "cfg_path": str(cfg_path),
        "model_dir": str(model_dir),
        "use_fp16": bool(args.fp16),
        "use_cuda_kernel": False,
        "use_deepspeed": False,
    }
    if args.device:
        init_kwargs["device"] = args.device

    print(f"Model:   {model_dir}")
    print(f"Audio:   {audio_dir}")
    print(f"Jobs:    {len(pending)} pending / {len(jobs)} total / {skipped} skipped")
    print("Loading IndexTTS2 once…")

    try:
        try:
            tts = IndexTTS2(**init_kwargs)
        except TypeError:
            init_kwargs.pop("device", None)
            tts = IndexTTS2(**init_kwargs)
    except Exception as exc:
        print(f"Failed to load IndexTTS2: {exc}", file=sys.stderr)
        return 1

    emo_ns = parse_emotion_args(args)
    text_dir = audio_dir / "_text"
    if args.write_text:
        text_dir.mkdir(parents=True, exist_ok=True)

    failed: list[str] = []
    ok = 0
    for i, job in enumerate(pending, 1):
        label = f"{job.shot_id}.{job.lang}"
        print(f"\n=== [{i}/{len(pending)}] {label} ===")
        print(f"Voice:  {job.voice}")
        print(f"Output: {job.output}")
        print(f"Text:   {job.text[:80]}{'…' if len(job.text) > 80 else ''}")

        if args.write_text:
            (text_dir / f"{job.shot_id}.{job.lang}.txt").write_text(
                job.text,
                encoding="utf-8",
            )

        job.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            kwargs = tts_lib.build_infer_kwargs(emo_ns, job.text, job.voice, job.output)
            tts.infer(**kwargs)
        except Exception as exc:
            print(f"FAILED {label}: {exc}", file=sys.stderr)
            failed.append(label)
            continue

        if not job.output.is_file():
            print(f"FAILED {label}: output missing after infer", file=sys.stderr)
            failed.append(label)
            continue

        print(f"Wrote {job.output}")
        if pad_mod is not None:
            if not apply_padding(
                pad_mod,
                ffmpeg,
                ffprobe,
                job,
                args.pad_duration,
                args.pad_threshold,
            ):
                pad_failed.append(label)
                failed.append(label)
                continue
        ok += 1

    print(f"\nDone. ok={ok} failed={len(failed)} skipped={skipped}")
    if failed:
        print(f"Failed jobs: {', '.join(failed)}", file=sys.stderr)
    if pad_failed:
        print(f"Failed padding: {', '.join(pad_failed)}", file=sys.stderr)

    report_rc = 0
    if args.report:
        report_rc = write_report(args, data, audio_dir, storyboard_path)

    return 1 if failed or pad_failed else report_rc


def apply_padding(
    pad_mod,
    ffmpeg: Path,
    ffprobe: Path,
    job: Job,
    duration: float,
    threshold: float,
) -> bool:
    try:
        start_pad, end_pad = pad_mod.ensure_padded(
            job.output,
            duration=duration,
            threshold=threshold,
            ffmpeg=ffmpeg,
            ffprobe=ffprobe,
        )
    except Exception as exc:
        print(f"FAILED pad {job.shot_id}.{job.lang}: {exc}", file=sys.stderr)
        return False
    if start_pad > 0 or end_pad > 0:
        print(
            f"Padded {job.output.name} "
            f"start={start_pad:.3f}s end={end_pad:.3f}s"
        )
    else:
        print(f"Pad ok (enough silence) {job.output.name}")
    return True


def write_report(
    args: argparse.Namespace,
    data: dict,
    audio_dir: Path,
    storyboard_path: Path | None,
) -> int:
    report_mod = load_duration_report()
    output = (
        Path(args.report_out).expanduser()
        if args.report_out
        else (audio_dir / "speech-timeline.md")
    )
    # duration_report needs storyboard only when it re-parses; we pass data via temp shots
    shots_path = audio_dir / "shots.json"
    if not shots_path.is_file():
        shots_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # Prefer real storyboard path for hints; fall back to a dummy path when only shots given
    sb = storyboard_path
    if sb is None:
        # build_report only needs audio + data; use load via --shots path API
        report = report_mod.build_report(data, audio_dir)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(f"Wrote {output}")
        rc = 0
    else:
        argv = [
            "--storyboard",
            str(sb),
            "--audio-dir",
            str(audio_dir),
            "--shots",
            str(shots_path),
            "-o",
            str(output),
        ]
        rc = int(report_mod.main(argv))

    if not getattr(args, "no_subtitles", False):
        sub_rc = write_subtitles_files(data, audio_dir, args.lang)
        if sub_rc != 0 and rc == 0:
            rc = sub_rc
    return rc


def write_subtitles_files(data: dict, audio_dir: Path, languages: str) -> int:
    sub_mod = load_write_subtitles()
    written = sub_mod.write_subtitles(data, audio_dir, languages)
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
