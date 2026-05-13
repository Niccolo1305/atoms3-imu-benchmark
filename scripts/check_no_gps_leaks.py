#!/usr/bin/env python3
"""Repository privacy gate for the public Atom IMU benchmark package."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


SKIP_DIRS = {
    ".git",
    ".pio",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    "raw_private_NOT_COMMITTED",
}

FORBIDDEN_SUFFIXES = {".bin", ".BIN", ".ld"}
RAW_CSV_NAME = re.compile(r"^(tel_\d+|MPU6886_\d+)\.csv$", re.IGNORECASE)
WINDOWS_USER_PREFIX = "C:" + "\\" + "Users" + "\\"
JSON_ESCAPED_WINDOWS_USER_PREFIX = WINDOWS_USER_PREFIX.replace("\\", "\\\\")
LOCAL_PATH_RE = re.compile(
    f"({re.escape(WINDOWS_USER_PREFIX)}|{re.escape(JSON_ESCAPED_WINDOWS_USER_PREFIX)})",
    re.IGNORECASE,
)
PRIVATE_SOURCE_FRAGMENT = "esp32" + "-telemetry-clean"
PRIVATE_SOURCE_RE = re.compile(re.escape(PRIVATE_SOURCE_FRAGMENT), re.IGNORECASE)
GPS_HEADER_RE = re.compile(
    r"(gps_|nav_fix|dhv_fix|latitude|longitude|gps_lat|gps_lon|nmea)",
    re.IGNORECASE,
)

def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = set(path.relative_to(root).parts)
        if rel_parts & SKIP_DIRS:
            continue
        yield path


def check_csv_header(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            sample_lines = []
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                sample_lines.append(line)
                break
            if not sample_lines:
                return errors
            header = next(csv.reader(sample_lines))
    except UnicodeDecodeError:
        return errors
    except OSError as exc:
        return [f"{path}: cannot read CSV header: {exc}"]

    forbidden = [col for col in header if GPS_HEADER_RE.search(col)]
    if forbidden:
        errors.append(f"{path}: forbidden GPS/navigation columns: {', '.join(forbidden)}")
    return errors


def check_text_content(path: Path) -> list[str]:
    if path.suffix.lower() not in {".md", ".json", ".csv", ".txt", ".py", ".ini"}:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return [f"{path}: cannot read text: {exc}"]

    errors: list[str] = []
    if LOCAL_PATH_RE.search(text):
        errors.append(f"{path}: contains a local Windows user path")
    if PRIVATE_SOURCE_RE.search(text):
        errors.append(f"{path}: contains a private source repository path fragment")
    if GPS_HEADER_RE.search(text) and path.suffix.lower() == ".csv":
        errors.append(f"{path}: contains GPS/navigation-looking header text")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail if public repo files look privacy-sensitive.")
    parser.add_argument("root", nargs="?", default=Path.cwd(), type=Path)
    args = parser.parse_args()
    root = args.root.resolve()

    errors: list[str] = []
    for path in iter_files(root):
        rel = path.relative_to(root)
        if path.suffix in FORBIDDEN_SUFFIXES:
            errors.append(f"{rel}: forbidden raw/binary suffix")
        if RAW_CSV_NAME.match(path.name):
            errors.append(f"{rel}: raw telemetry CSV name is forbidden")
        if path.suffix.lower() == ".csv":
            errors.extend(str(Path(e).relative_to(root)) if e.startswith(str(root)) else e for e in check_csv_header(path))
        errors.extend(str(Path(e).relative_to(root)) if e.startswith(str(root)) else e for e in check_text_content(path))

    if errors:
        print("Privacy check FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Privacy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
