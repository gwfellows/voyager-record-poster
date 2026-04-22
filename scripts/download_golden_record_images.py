#!/usr/bin/env python3

"""Download the Voyager Golden Record image set."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve


DEFAULT_BASE_URL = "https://goldenrecord.org/png"
DEFAULT_START = 1
DEFAULT_END = 122


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download numbered Golden Record PNG images."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL that serves numbered PNG files (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=DEFAULT_START,
        help=f"First image number to download (default: {DEFAULT_START})",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=DEFAULT_END,
        help=f"Last image number to download (default: {DEFAULT_END})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("downloads/golden-record"),
        help="Directory to write images into (default: downloads/golden-record)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace files that already exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the downloads without fetching them",
    )
    return parser


def iter_image_numbers(start: int, end: int) -> range:
    if start < 0 or end < 0:
        raise ValueError("start and end must be non-negative")
    if start > end:
        raise ValueError("start must be less than or equal to end")
    return range(start, end + 1)


def image_name(number: int) -> str:
    return f"{number:03d}.png"


def image_url(base_url: str, number: int) -> str:
    return f"{base_url.rstrip('/')}/{image_name(number)}"


def download_images(
    *,
    base_url: str,
    start: int,
    end: int,
    output_dir: Path,
    overwrite: bool,
    dry_run: bool,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    failures = 0

    for number in iter_image_numbers(start, end):
        filename = image_name(number)
        target_path = output_dir / filename
        source_url = image_url(base_url, number)

        if target_path.exists() and not overwrite:
            print(f"skip  {target_path} (already exists)")
            continue

        if dry_run:
            print(f"would download {source_url} -> {target_path}")
            continue

        try:
            print(f"fetch {source_url}")
            urlretrieve(source_url, target_path)
        except HTTPError as exc:
            failures += 1
            print(
                f"error {filename}: server returned HTTP {exc.code} for {source_url}",
                file=sys.stderr,
            )
        except URLError as exc:
            failures += 1
            print(
                f"error {filename}: could not reach {source_url} ({exc.reason})",
                file=sys.stderr,
            )

    return failures


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        failures = download_images(
            base_url=args.base_url,
            start=args.start,
            end=args.end,
            output_dir=args.output_dir,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if failures:
        print(f"completed with {failures} failed download(s)", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
