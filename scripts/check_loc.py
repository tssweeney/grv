#!/usr/bin/env python3
"""Check that all Python files are under the line limit."""

import sys
from pathlib import Path

MAX_LINES = 150
SKIP_MARKER = "# loc-skip"


def check_file(path: Path) -> tuple[bool, int]:
    """Check if file is under line limit. Returns (ok, line_count)."""
    content = path.read_text()
    if SKIP_MARKER in content.split("\n")[0]:
        return True, 0
    line_count = len(content.split("\n"))
    return line_count <= MAX_LINES, line_count


def main() -> int:
    """Check all Python files in src/."""
    src_dir = Path("src")
    if not src_dir.exists():
        print("No src/ directory found")
        return 1

    failed = []
    for py_file in src_dir.rglob("*.py"):
        ok, count = check_file(py_file)
        if not ok:
            failed.append((py_file, count))

    if failed:
        print(f"Files exceeding {MAX_LINES} lines:")
        for path, count in failed:
            print(f"  {path}: {count} lines")
        print(f"\nAdd '{SKIP_MARKER}' to first line to skip (use sparingly)")
        return 1

    print(f"All files under {MAX_LINES} lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
