#!/usr/bin/env python3
"""
Pre‑push Secret Scanner
Scans staged files (git diff --cached) for hard‑coded secrets.
Blocks push if anything fishy is found.
"""

from __future__ import annotations
import subprocess
import sys
from pathlib import Path

from patterns import REGEX_PATTERNS
from entropy import looks_random

# Files/dirs to ignore outright
IGNORE_PATHS = {".git/", "node_modules/", "__pycache__/"}

def staged_paths() -> list[Path]:
    """Return list of staged (added/modified) files."""
    diff_cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    out = subprocess.check_output(diff_cmd, text=True)
    files = [Path(line.strip()) for line in out.splitlines()]
    return [f for f in files if not any(p in f.parts for p in IGNORE_PATHS)]

def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """
    Return list of (line_no, detector_name, line_text) hits in a file.
    """
    hits = []
    try:
        for ln, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
            # Regex scans
            for name, pattern in REGEX_PATTERNS.items():
                if pattern.search(line):
                    hits.append((ln, name, line.strip()))
            # Entropy scan
            for token in line.split():
                if looks_random(token):
                    hits.append((ln, "High entropy", line.strip()))
    except Exception:
        # Binary or unreadable file; skip
        pass
    return hits

def main() -> None:
    offenders = {}
    for file in staged_paths():
        file_hits = scan_file(file)
        if file_hits:
            offenders[file] = file_hits

    if not offenders:
        sys.exit(0)  # All clear → allow push

    # Pretty CLI output
    print("\n🚨  Secret(s) detected! Push blocked to protect your keys.\n")
    for path, hits in offenders.items():
        for ln, detector, snippet in hits:
            print(f"{path}:{ln} [{detector}]\n  {snippet}\n")
    print("💡  Suggestion: move secrets to environment variables (.env) and reference them, "
          "or add false positives to an ignore list.\n")
    print("👉  Bypass (not recommended): git push --no-verify\n")
    sys.exit(1)  # Block push

if __name__ == "__main__":
    main()
