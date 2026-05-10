#!/usr/bin/env python3
"""Remove GPS/navigation columns from a telemetry CSV.

This is a utility for future public samples. The v1 repository does not commit
raw telemetry CSVs, sanitized or otherwise.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


DEFAULT_DROP_RE = re.compile(
    r"(gps_|nav_|dhv_|lat|lon|hdop|sats|fix|nmea|speed_source)",
    re.IGNORECASE,
)


def scrub_csv(src: Path, dst: Path, drop_re: re.Pattern[str]) -> None:
    with src.open("r", encoding="utf-8-sig", newline="") as in_f, dst.open(
        "w", encoding="utf-8", newline=""
    ) as out_f:
        comments = []
        first_data_line = None
        for line in in_f:
            if line.startswith("#"):
                if not any(token in line.lower() for token in ("gps", "lat", "lon", "fix")):
                    comments.append(line)
                continue
            if line.strip():
                first_data_line = line
                break

        if first_data_line is None:
            return

        reader = csv.reader([first_data_line] + list(in_f))
        writer = csv.writer(out_f, lineterminator="\n")

        for comment in comments:
            out_f.write(comment)

        header = next(reader)
        keep_indexes = [idx for idx, col in enumerate(header) if not drop_re.search(col)]
        writer.writerow([header[idx] for idx in keep_indexes])

        for row in reader:
            writer.writerow([row[idx] if idx < len(row) else "" for idx in keep_indexes])


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a GPS-scrubbed CSV copy.")
    parser.add_argument("src", type=Path)
    parser.add_argument("dst", type=Path)
    parser.add_argument(
        "--drop-regex",
        default=DEFAULT_DROP_RE.pattern,
        help="Case-insensitive regex for columns to remove.",
    )
    args = parser.parse_args()

    if args.dst.exists():
        raise SystemExit(f"Refusing to overwrite existing output: {args.dst}")

    args.dst.parent.mkdir(parents=True, exist_ok=True)
    scrub_csv(args.src, args.dst, re.compile(args.drop_regex, re.IGNORECASE))
    print(f"Wrote sanitized CSV: {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
