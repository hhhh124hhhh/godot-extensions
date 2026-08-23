#!/usr/bin/env python3
"""
Zero-shot TTS with voice cloning via IndexTTS2.

Run through the index-tts manifest entry (.dependency/index-tts/.venv/) —
see SKILL.md and skill-dependency-manager. Never use host python/py.

Usage
-----
    .dependency/index-tts/.venv/Scripts/python \\
        .cursor/skills/ai-text-to-speech/scripts/tts.py \\
        --voice audio/voice/ref.wav \\
        --text "你好"

    .dependency/index-tts/.venv/Scripts/python \\
        .cursor/skills/ai-text-to-speech/scripts/tts.py \\
        --voice audio/voice/ref.wav \\
        --text-file script.txt \\
        --output audio/voice/tts/line.wav
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


TOOL_NAME = "index-tts"
DEFAULT_OUTPUT_NAME = "speech.wav"
DEFAULT_OUTPUT_SUBDIR = "tts"
EMO_VECTOR_SIZE = 8


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


def resolve_tool_entry(repo_root: Path, tool_name: str) -> dict:
    manifest_path = repo_root / ".dependency" / "manifest.json"
    entry = json.loads(manifest_path.read_text(encoding="utf-8")).get(tool_name)
    if not entry:
        print(
            f"Tool '{tool_name}' not found in .dependency/manifest.json. "
            "See .cursor/skills/skill-dependency-manager.md and "
            ".cursor/skills/ai-text-to-speech/SKILL.md Setup.",
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
    return entry


def resolve_tool_bin(repo_root: Path, tool_name: str) -> Path:
    entry = resolve_tool_entry(repo_root, tool_name)
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


def resolve_index_tts_root(repo_root: Path, python_bin: Path) -> Path:
    # .dependency/index-tts/.venv/Scripts/python.exe → .dependency/index-tts
    # .dependency/index-tts/.venv/bin/python → .dependency/index-tts
    for parent in python_bin.resolve().parents:
        if (parent / "checkpoints").is_dir() or (parent / "indextts").is_dir():
            return parent
        if parent.name == ".venv":
            return parent.parent
    fallback = repo_root / ".dependency" / "index-tts"
    if fallback.is_dir():
        return fallback
    print(
        f"Could not locate IndexTTS install from {python_bin}. "
        "Expected .dependency/index-tts with checkpoints/.",
        file=sys.stderr,
    )
    sys.exit(1)


def read_text_arg(args: argparse.Namespace) -> str:
    sources = [bool(args.text), bool(args.text_file)]
    if sum(sources) != 1:
        print("Provide exactly one of --text or --text-file.", file=sys.stderr)
        sys.exit(1)
    if args.text is not None:
        text = args.text.strip()
    else:
        path = Path(args.text_file)
        if not path.is_file():
            print(f"Text file not found: {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8").strip()
    if not text:
        print("ERROR: Text is empty.", file=sys.stderr)
        sys.exit(1)
    return text


def parse_emotion_vector(raw: str) -> list[float]:
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != EMO_VECTOR_SIZE:
        print(
            f"--emotion-vector needs {EMO_VECTOR_SIZE} comma-separated floats "
            f"(got {len(parts)}): happy,angry,sad,afraid,disgusted,melancholic,surprised,calm",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        return [float(p) for p in parts]
    except ValueError as exc:
        print(f"Invalid --emotion-vector value: {exc}", file=sys.stderr)
        sys.exit(1)


def default_output_path(voice: Path) -> Path:
    return voice.parent / DEFAULT_OUTPUT_SUBDIR / DEFAULT_OUTPUT_NAME


def build_infer_kwargs(args: argparse.Namespace, text: str, voice: Path, output: Path) -> dict:
    kwargs: dict = {
        "spk_audio_prompt": str(voice),
        "text": text,
        "output_path": str(output),
        "verbose": bool(args.verbose),
        "emo_alpha": float(args.emotion_weight),
        "use_random": bool(args.random),
    }

    emotion_modes = sum(
        [
            bool(args.emotion_audio),
            bool(args.emotion_vector),
            bool(args.emotion_text) or bool(args.emotion_from_text),
        ]
    )
    if emotion_modes > 1:
        print(
            "Pick one emotion source: --emotion-audio, --emotion-vector, "
            "or --emotion-text / --emotion-from-text.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.emotion_audio:
        emo_path = Path(args.emotion_audio)
        if not emo_path.is_file():
            print(f"Emotion audio not found: {emo_path}", file=sys.stderr)
            sys.exit(1)
        kwargs["emo_audio_prompt"] = str(emo_path)
    elif args.emotion_vector:
        kwargs["emo_vector"] = parse_emotion_vector(args.emotion_vector)
    elif args.emotion_text or args.emotion_from_text:
        kwargs["use_emo_text"] = True
        if args.emotion_text:
            kwargs["emo_text"] = args.emotion_text

    return kwargs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synthesize speech with IndexTTS2 voice cloning.",
    )
    parser.add_argument(
        "--voice",
        required=True,
        help="Speaker reference audio (timbre prompt)",
    )
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument("--text", help="Text to synthesize")
    text_group.add_argument("--text-file", help="UTF-8 text file to synthesize")
    parser.add_argument(
        "-o",
        "--output",
        help=f"Output WAV path (default: <voice-dir>/{DEFAULT_OUTPUT_SUBDIR}/{DEFAULT_OUTPUT_NAME})",
    )
    parser.add_argument(
        "--model-dir",
        default=None,
        help="IndexTTS-2 checkpoints dir (default: <index-tts>/checkpoints)",
    )
    parser.add_argument(
        "--fp16",
        action="store_true",
        help="Use FP16 inference (faster, less VRAM)",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Runtime device, e.g. cpu, cuda, cuda:0, mps",
    )
    parser.add_argument(
        "--emotion-audio",
        help="Emotion reference audio (separate from speaker timbre)",
    )
    parser.add_argument(
        "--emotion-text",
        help="Natural-language emotion description",
    )
    parser.add_argument(
        "--emotion-from-text",
        action="store_true",
        help="Infer emotion vectors from the synthesis text",
    )
    parser.add_argument(
        "--emotion-vector",
        help="Comma-separated 8-dim emotion vector",
    )
    parser.add_argument(
        "--emotion-weight",
        type=float,
        default=1.0,
        help="Emotion strength emo_alpha in [0, 1] (default: 1.0)",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Enable stochastic sampling (may reduce voice clone fidelity)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose IndexTTS inference logs",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not (0.0 <= args.emotion_weight <= 1.0):
        print("--emotion-weight must be between 0.0 and 1.0", file=sys.stderr)
        return 1

    repo_root = find_repo_root(Path(__file__))
    if repo_root is None:
        print(
            "Could not find repo root (.dependency/manifest.json). "
            "Run from the Godot project that owns this skill.",
            file=sys.stderr,
        )
        return 1

    # Validate install is registered even though we are already running under its venv.
    python_bin = resolve_tool_bin(repo_root, TOOL_NAME)
    index_tts_root = resolve_index_tts_root(repo_root, python_bin)

    voice = Path(args.voice).expanduser()
    if not voice.is_file():
        print(f"Voice reference not found: {voice}", file=sys.stderr)
        return 1

    text = read_text_arg(args)
    output = Path(args.output).expanduser() if args.output else default_output_path(voice)
    if output.exists() and not args.force:
        print(
            f"Output already exists: {output}. Pass --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    model_dir = Path(args.model_dir).expanduser() if args.model_dir else (index_tts_root / "checkpoints")
    cfg_path = model_dir / "config.yaml"
    if not cfg_path.is_file():
        print(
            f"Missing model config: {cfg_path}. "
            "Download IndexTTS-2 checkpoints (see SKILL.md Setup).",
            file=sys.stderr,
        )
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)

    # Prefer importing from the installed package; fall back to repo layout.
    if str(index_tts_root) not in sys.path:
        sys.path.insert(0, str(index_tts_root))

    try:
        from indextts.infer_v2 import IndexTTS2
    except ImportError as exc:
        print(
            f"Failed to import IndexTTS2 from {index_tts_root}: {exc}\n"
            "Run uv sync under .dependency/index-tts (see SKILL.md Setup).",
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

    print(f"Voice:  {voice}")
    print(f"Output: {output}")
    print(f"Model:  {model_dir}")
    print(f"Text:   {text[:80]}{'…' if len(text) > 80 else ''}")

    try:
        try:
            tts = IndexTTS2(**init_kwargs)
        except TypeError:
            # Some builds omit device= from __init__.
            init_kwargs.pop("device", None)
            tts = IndexTTS2(**init_kwargs)
        tts.infer(**build_infer_kwargs(args, text, voice, output))
    except Exception as exc:
        print(f"IndexTTS inference failed: {exc}", file=sys.stderr)
        return 1

    if not output.is_file():
        print(f"Inference finished but output missing: {output}", file=sys.stderr)
        return 1

    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
