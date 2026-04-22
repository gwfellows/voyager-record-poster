#!/usr/bin/env python3

"""Build a printable poster PDF from the Golden Record image set."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image


A_SERIES_MM = {
    "A4": (210, 297),
    "A3": (297, 420),
    "A2": (420, 594),
    "A1": (594, 841),
}


def mm_to_px(mm: float, dpi: int) -> int:
    return round(mm / 25.4 * dpi)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Arrange Golden Record PNGs into a poster grid and export PDF."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("downloads/golden-record"),
        help="Directory containing the numbered PNGs",
    )
    parser.add_argument(
        "--output-image",
        type=Path,
        default=Path("output/golden-record-poster.png"),
        help="Path for the composite poster PNG",
    )
    parser.add_argument(
        "--output-pdf",
        type=Path,
        default=Path("output/golden-record-poster.pdf"),
        help="Path for the poster PDF",
    )
    parser.add_argument(
        "--paper",
        choices=sorted(A_SERIES_MM),
        default="A2",
        help="Paper size for the poster",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Output DPI",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=9,
        help="Number of image columns in the grid",
    )
    parser.add_argument(
        "--margin-mm",
        type=float,
        default=12,
        help="White page margin in millimeters",
    )
    return parser


def load_images(input_dir: Path) -> list[Path]:
    images = sorted(input_dir.glob("*.png"))
    if not images:
        raise FileNotFoundError(f"no PNG files found in {input_dir}")
    return images


def compute_layout(
    *,
    image_size: tuple[int, int],
    page_size: tuple[int, int],
    columns: int,
    image_count: int,
    margin_px: int,
) -> tuple[int, int, int, int, int, int]:
    rows = math.ceil(image_count / columns)
    source_width, source_height = image_size
    image_ratio = source_width / source_height

    usable_width = page_size[0] - (margin_px * 2)
    usable_height = page_size[1] - (margin_px * 2)
    cell_width = usable_width // columns
    cell_height = round(cell_width / image_ratio)

    if cell_height * rows > usable_height:
        cell_height = usable_height // rows
        cell_width = round(cell_height * image_ratio)

    grid_width = cell_width * columns
    grid_height = cell_height * rows
    origin_x = (page_size[0] - grid_width) // 2
    origin_y = (page_size[1] - grid_height) // 2

    return rows, cell_width, cell_height, grid_width, grid_height, origin_x, origin_y


def build_poster(
    *,
    image_paths: list[Path],
    page_size: tuple[int, int],
    columns: int,
    margin_px: int,
) -> Image.Image:
    with Image.open(image_paths[0]) as sample:
        image_size = sample.size

    rows, cell_width, cell_height, _, _, origin_x, origin_y = compute_layout(
        image_size=image_size,
        page_size=page_size,
        columns=columns,
        image_count=len(image_paths),
        margin_px=margin_px,
    )

    poster = Image.new("RGB", page_size, "white")
    for index, image_path in enumerate(image_paths):
        row = index // columns
        col = index % columns
        x = origin_x + (col * cell_width)
        y = origin_y + (row * cell_height)

        with Image.open(image_path) as source:
            tile = source.convert("RGB").resize((cell_width, cell_height), Image.Resampling.LANCZOS)
            poster.paste(tile, (x, y))

    return poster


def main() -> int:
    args = build_parser().parse_args()

    if args.columns <= 0:
        raise SystemExit("--columns must be positive")
    if args.dpi <= 0:
        raise SystemExit("--dpi must be positive")
    if args.margin_mm < 0:
        raise SystemExit("--margin-mm must be non-negative")

    paper_width_mm, paper_height_mm = A_SERIES_MM[args.paper]
    page_size = (
        mm_to_px(paper_width_mm, args.dpi),
        mm_to_px(paper_height_mm, args.dpi),
    )
    margin_px = mm_to_px(args.margin_mm, args.dpi)

    image_paths = load_images(args.input_dir)
    args.output_image.parent.mkdir(parents=True, exist_ok=True)
    args.output_pdf.parent.mkdir(parents=True, exist_ok=True)

    poster = build_poster(
        image_paths=image_paths,
        page_size=page_size,
        columns=args.columns,
        margin_px=margin_px,
    )
    poster.save(args.output_image, format="PNG")
    poster.save(args.output_pdf, format="PDF", resolution=args.dpi)

    print(f"saved {args.output_image}")
    print(f"saved {args.output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
