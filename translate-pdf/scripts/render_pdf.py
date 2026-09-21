#!/usr/bin/env python
"""Render an already-translated UTF-8 HTML document to PDF with Chrome or Edge."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

CANDIDATES = (
    os.environ.get("CHROME_BIN", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium",
    "chrome",
)


def find_browser() -> str | None:
    for item in CANDIDATES:
        if item and (Path(item).is_file() or shutil.which(item)):
            return item
    return None


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {Path(sys.argv[0]).name} INPUT.html OUTPUT.pdf", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    if not source.is_file():
        print(f"Input HTML not found: {source}", file=sys.stderr)
        return 2
    browser = find_browser()
    if not browser:
        print("Chrome or Edge was not found. Set CHROME_BIN to its executable path.", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={output}", source.as_uri()],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        print(result.stderr[-4000:], file=sys.stderr)
        return result.returncode
    if not output.is_file() or output.stat().st_size == 0:
        print("Browser exited successfully but did not create a PDF.", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
