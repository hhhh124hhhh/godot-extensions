"""
Remove a corner / region watermark by LaMa inpainting (IOPaint).

Builds a feathered circular mask over the watermark, then fills it with
surrounding pixels. Default region matches Gemini-style bottom-right sparkle
geometry (96x96 box, 64px inset).

Run via the iopaint venv — see SKILL.md and skill-dependency-manager.
Never use host python outside .dependency/ for this skill.

Usage
-----
    .dependency/iopaint/.venv/Scripts/python.exe \\
        .cursor/skills/image-remove-watermark-by-lama-inpainting/scripts/inpaint.py \\
        path/to/image_or_folder

Default output: ``<source-dir>/no-watermark/`` beside each input file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFilter

DEFAULT_PATTERN = "*.png"
DEFAULT_OUTPUT_SUBDIR = "no-watermark"
DEFAULT_REGION = "br"
DEFAULT_SIZE = 96
DEFAULT_INSET = 64
DEFAULT_BLUR = 3.0
DEFAULT_MODEL = "lama"
DEFAULT_DEVICE = "cuda"
DEFAULT_EXCLUDES: tuple[str, ...] = (
    "*_sheet.png",
    "*_mask.png",
    f"{DEFAULT_OUTPUT_SUBDIR}/*",
    f"**/{DEFAULT_OUTPUT_SUBDIR}/**",
)
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def find_repo_root(start: Path) -> Path | None:
    for parent in [start.resolve(), *start.resolve().parents]:
        if (parent / ".dependency" / "manifest.json").is_file():
            return parent
    return None


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
            f"Install it under {repo_root / '.dependency' / tool_name} "
            "and set populated: true in .dependency/manifest.json.",
            file=sys.stderr,
        )
        sys.exit(1)
    bin_path = repo_root / entry["bin"]
    if not bin_path.is_file():
        print(f"Interpreter not found: {bin_path}", file=sys.stderr)
        sys.exit(1)
    return bin_path.resolve()


def collect_images(
    target_dir: Path,
    pattern: str,
    excludes: tuple[str, ...],
    recursive: bool,
) -> list[Path]:
    excluded: set[Path] = set()
    for exclude in excludes:
        excluded.update(
            target_dir.rglob(exclude) if recursive else target_dir.glob(exclude)
        )

    globber = target_dir.rglob if recursive else target_dir.glob
    patterns = {pattern}
    if pattern == "*.png":
        patterns.update({"*.jpg", "*.jpeg", "*.webp", "*.bmp"})

    images: list[Path] = []
    seen: set[Path] = set()
    for pat in patterns:
        for path in globber(pat):
            resolved = path.resolve()
            if resolved in seen or resolved in excluded or not path.is_file():
                continue
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            seen.add(resolved)
            images.append(resolved)
    return sorted(images)


def resolve_input(
    input_path: Path,
    pattern: str,
    excludes: tuple[str, ...],
    recursive: bool,
) -> tuple[Path | None, list[Path]]:
    if input_path.is_file():
        if input_path.suffix.lower() not in IMAGE_EXTENSIONS:
            print(f"Unsupported image type: {input_path}", file=sys.stderr)
            return None, []
        return input_path.parent, [input_path]

    if not input_path.is_dir():
        print(f"Path not found: {input_path}", file=sys.stderr)
        return None, []

    return input_path, collect_images(input_path, pattern, excludes, recursive)


def resolve_output_dir(
    input_root: Path,
    output_dir: Path | None,
    output_subdir: str,
) -> Path | None:
    if output_dir is None:
        return None
    if output_dir.is_absolute():
        return output_dir.resolve()
    return (input_root / output_dir).resolve()


def resolve_dest(
    image_path: Path,
    input_root: Path,
    output_dir: Path | None,
    output_subdir: str,
) -> Path:
    name = image_path.name
    if image_path.suffix.lower() != ".png":
        name = f"{image_path.stem}.png"
    if output_dir is not None:
        try:
            rel = image_path.parent.relative_to(input_root)
        except ValueError:
            rel = Path()
        dest = output_dir / rel / name
    else:
        dest = image_path.parent / output_subdir / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest.resolve()


def parse_box_region(region: str) -> tuple[int, int, int, int] | None:
    parts = [p.strip() for p in region.split(",")]
    if len(parts) != 4:
        return None
    try:
        x, y, width, height = (int(p) for p in parts)
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return x, y, width, height


def bottom_right_box(
    image_width: int,
    image_height: int,
    size: int,
    inset: int,
) -> tuple[int, int, int, int]:
    box_w = min(size, image_width)
    box_h = min(size, image_height)
    x = max(0, image_width - inset - box_w)
    y = max(0, image_height - inset - box_h)
    return x, y, box_w, box_h


def make_circle_mask(
    image_width: int,
    image_height: int,
    box: tuple[int, int, int, int],
    radius: float,
    blur: float,
) -> Image.Image:
    x, y, width, height = box
    cx = x + width / 2.0
    cy = y + height / 2.0
    mask = Image.new("L", (image_width, image_height), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=255,
    )
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=blur))
    return mask


def mask_to_binary(mask: Image.Image) -> np.ndarray:
    mask_img = np.array(mask, dtype=np.uint8)
    mask_img[mask_img >= 127] = 255
    mask_img[mask_img < 127] = 0
    return mask_img


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove a region watermark with LaMa inpainting (IOPaint).",
    )
    parser.add_argument(
        "path",
        help="Image file or directory",
    )
    parser.add_argument("--pattern", default=DEFAULT_PATTERN, help="Input glob pattern")
    parser.add_argument("--recursive", action="store_true", help="Search subdirectories")
    parser.add_argument("--exclude", action="append", default=[], help="Extra glob excludes")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=f"Shared output directory (default: <source-dir>/{DEFAULT_OUTPUT_SUBDIR}/ per file)",
    )
    parser.add_argument(
        "--output-subdir",
        default=DEFAULT_OUTPUT_SUBDIR,
        help=f"Subfolder beside each source file when --output-dir is omitted (default: {DEFAULT_OUTPUT_SUBDIR})",
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_REGION,
        help="br (bottom-right, default) or x,y,w,h in pixels",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_SIZE,
        help=f"Box size in pixels for --region br (default: {DEFAULT_SIZE})",
    )
    parser.add_argument(
        "--inset",
        type=int,
        default=DEFAULT_INSET,
        help=f"Right/bottom inset in pixels for --region br (default: {DEFAULT_INSET})",
    )
    parser.add_argument(
        "--radius",
        type=float,
        default=None,
        help="Circle radius in pixels (default: half of the region box)",
    )
    parser.add_argument(
        "--blur",
        type=float,
        default=DEFAULT_BLUR,
        help=f"Gaussian blur sigma on the mask (default: {DEFAULT_BLUR})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"IOPaint model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--device",
        choices=("cuda", "cpu"),
        default=DEFAULT_DEVICE,
        help="Inference device (default: cuda, falls back to cpu)",
    )
    return parser.parse_args(argv)


def resolve_device(requested: str) -> torch.device:
    if requested == "cuda" and not torch.cuda.is_available():
        print("CUDA not available; falling back to cpu")
        return torch.device("cpu")
    return torch.device(requested)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    try:
        from iopaint.helper import pil_to_bytes
        from iopaint.model.utils import torch_gc
        from iopaint.model_manager import ModelManager
        from iopaint.schema import InpaintRequest
    except ImportError:
        print(
            "Run this script with the iopaint venv interpreter:\n"
            "  .dependency/iopaint/.venv/Scripts/python.exe "
            ".cursor/skills/image-remove-watermark-by-lama-inpainting/scripts/inpaint.py",
            file=sys.stderr,
        )
        return 1

    project_root = find_repo_root(Path(__file__))
    if project_root is None:
        print(
            "Could not find .dependency/manifest.json. "
            "Run from a repo that follows .cursor/skills/skill-dependency-manager.md.",
            file=sys.stderr,
        )
        return 1

    resolve_tool_bin(project_root, "iopaint")

    explicit_box = None
    if args.region != DEFAULT_REGION:
        explicit_box = parse_box_region(args.region)
        if explicit_box is None:
            print(
                f"Invalid --region {args.region!r}. Use 'br' or x,y,w,h.",
                file=sys.stderr,
            )
            return 1

    input_path = Path(args.path).expanduser().resolve()
    input_root, image_paths = resolve_input(
        input_path,
        args.pattern,
        tuple(DEFAULT_EXCLUDES) + tuple(args.exclude),
        args.recursive,
    )
    if input_root is None:
        return 1
    if not image_paths:
        print(f"No images found under {input_root} (pattern: {args.pattern})")
        return 1

    output_dir = resolve_output_dir(input_root, args.output_dir, args.output_subdir)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    device = resolve_device(args.device)
    print(f"Input: {input_path}")
    print(f"Images: {len(image_paths)}")
    print(f"Engine: IOPaint LaMa ({args.model})")
    print(f"Device: {device}")
    print(f"Region: {args.region}")
    if output_dir is not None:
        print(f"Output folder: {output_dir}")
    else:
        print(f"Output: <each-source-dir>/{args.output_subdir}/")

    model_manager = ModelManager(name=args.model, device=device)
    inpaint_request = InpaintRequest()
    errors = 0

    for image_path in image_paths:
        dest = resolve_dest(image_path, input_root, output_dir, args.output_subdir)
        print(f"Processing {image_path.name} ...")
        try:
            source = Image.open(image_path)
            infos = source.info
            rgb = source.convert("RGB")
            width, height = rgb.size
            box = explicit_box or bottom_right_box(
                width, height, args.size, args.inset
            )
            radius = args.radius if args.radius is not None else min(box[2], box[3]) / 2.0
            mask = make_circle_mask(width, height, box, radius, args.blur)
            mask_img = mask_to_binary(mask)
            img = np.array(rgb)
            result_bgr = model_manager(img, mask_img, inpaint_request)
            result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
            payload = pil_to_bytes(Image.fromarray(result_rgb), "png", 100, infos)
            dest.write_bytes(payload)
            x, y, box_w, box_h = box
            print(
                f"  region ({x}, {y}) {box_w}x{box_h}; "
                f"circle r={radius:.0f}; saved {dest}"
            )
        except Exception as exc:
            print(f"  ERROR {image_path.name}: {exc}", file=sys.stderr)
            errors += 1
        finally:
            torch_gc()

    if errors:
        print(f"Done with {errors} error(s).", file=sys.stderr)
        return 1

    if output_dir is not None:
        print(f"Done. Processed {len(image_paths)} image(s) in {output_dir}")
    else:
        print(f"Done. Processed {len(image_paths)} image(s) beside their sources")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
