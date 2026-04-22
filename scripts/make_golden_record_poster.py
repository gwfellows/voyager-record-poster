#!/usr/bin/env python3

"""Build a printable poster PDF from the Golden Record image set."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


A_SERIES_MM = {
    "A4": (210, 297),
    "A3": (297, 420),
    "A2": (420, 594),
    "A1": (594, 841),
}

DEFAULT_QUOTE = (
    "This is a present from a small, distant world, a token of our sounds, "
    "our science, our images, our music, our thoughts and our feelings. "
    "We are attempting to survive our time so we may live into yours."
)
DEFAULT_FONT = Path("/System/Library/Fonts/Helvetica.ttc")
DEFAULT_FONT_INDEX = 1


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
        help="Page margin in millimeters",
    )
    parser.add_argument(
        "--background",
        default="black",
        help="Poster background color",
    )
    parser.add_argument(
        "--quote",
        default=DEFAULT_QUOTE,
        help="Optional quote to place in the unused final-row space",
    )
    parser.add_argument(
        "--quote-font",
        type=Path,
        default=DEFAULT_FONT,
        help=f"Font file for the quote (default: {DEFAULT_FONT})",
    )
    parser.add_argument(
        "--quote-color",
        default="white",
        help="Quote text color",
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


def fit_quote(
    *,
    draw: ImageDraw.ImageDraw,
    quote: str,
    font_path: Path,
    font_index: int,
    box_width: int,
    box_height: int,
) -> tuple[ImageFont.FreeTypeFont, str, int]:
    if box_width <= 0 or box_height <= 0:
        raise ValueError("quote box must be positive")

    for font_size in range(min(box_height, box_width), 11, -1):
        font = ImageFont.truetype(str(font_path), font_size, index=font_index)
        average_character_width = max(font_size * 0.55, 1)
        wrap_width = max(1, int(box_width / average_character_width))
        lines = wrap(quote, width=wrap_width)
        wrapped_quote = "\n".join(lines)
        spacing = max(4, font_size // 5)
        bbox = draw.multiline_textbbox(
            (0, 0),
            wrapped_quote,
            font=font,
            spacing=spacing,
            align="left",
        )
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_width <= box_width and text_height <= box_height:
            return font, wrapped_quote, spacing

    raise ValueError("quote does not fit in the available space")


def draw_quote(
    *,
    poster: Image.Image,
    quote: str,
    font_path: Path,
    font_index: int,
    text_color: str,
    quote_box: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = quote_box
    padding_x = max(8, (right - left) // 40)
    padding_y = max(12, (bottom - top) // 12)
    inner_box = (
        left + padding_x,
        top + padding_y,
        right - padding_x,
        bottom - padding_y,
    )
    draw = ImageDraw.Draw(poster)
    font, wrapped_quote, spacing = fit_quote(
        draw=draw,
        quote=quote,
        font_path=font_path,
        font_index=font_index,
        box_width=inner_box[2] - inner_box[0],
        box_height=inner_box[3] - inner_box[1],
    )
    bbox = draw.multiline_textbbox(
        (0, 0),
        wrapped_quote,
        font=font,
        spacing=spacing,
        align="left",
    )
    text_height = bbox[3] - bbox[1]
    text_y = inner_box[1] + ((inner_box[3] - inner_box[1] - text_height) // 2)
    draw.multiline_text(
        (inner_box[0], text_y),
        wrapped_quote,
        fill=text_color,
        font=font,
        spacing=spacing,
        align="left",
    )


def build_poster(
    *,
    image_paths: list[Path],
    page_size: tuple[int, int],
    columns: int,
    margin_px: int,
    background: str,
    quote: str,
    quote_font: Path,
    quote_font_index: int,
    quote_color: str,
) -> Image.Image:
    with Image.open(image_paths[0]) as sample:
        image_size = sample.size

    rows, cell_width, cell_height, grid_width, _, origin_x, origin_y = compute_layout(
        image_size=image_size,
        page_size=page_size,
        columns=columns,
        image_count=len(image_paths),
        margin_px=margin_px,
    )

    poster = Image.new("RGB", page_size, background)
    for index, image_path in enumerate(image_paths):
        row = index // columns
        col = index % columns
        x = origin_x + (col * cell_width)
        y = origin_y + (row * cell_height)

        with Image.open(image_path) as source:
            tile = source.convert("RGB").resize((cell_width, cell_height), Image.Resampling.LANCZOS)
            poster.paste(tile, (x, y))

    remainder = len(image_paths) % columns
    if quote and remainder:
        quote_box = (
            origin_x + (remainder * cell_width),
            origin_y + ((rows - 1) * cell_height),
            origin_x + grid_width,
            origin_y + (rows * cell_height),
        )
        draw_quote(
            poster=poster,
            quote=quote,
            font_path=quote_font,
            font_index=quote_font_index,
            text_color=quote_color,
            quote_box=quote_box,
        )

    return poster


def main() -> int:
    args = build_parser().parse_args()

    if args.columns <= 0:
        raise SystemExit("--columns must be positive")
    if args.dpi <= 0:
        raise SystemExit("--dpi must be positive")
    if args.margin_mm < 0:
        raise SystemExit("--margin-mm must be non-negative")
    if args.quote and not args.quote_font.exists():
        raise SystemExit(f"--quote-font does not exist: {args.quote_font}")

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
        background=args.background,
        quote=args.quote,
        quote_font=args.quote_font,
        quote_font_index=DEFAULT_FONT_INDEX,
        quote_color=args.quote_color,
    )
    poster.save(args.output_image, format="PNG")
    poster.save(args.output_pdf, format="PDF", resolution=args.dpi)

    print(f"saved {args.output_image}")
    print(f"saved {args.output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
