#!/usr/bin/env python3
"""
Copies run-scanner hook into .git/hooks and makes it executable.
"""

import shutil, stat, os, sys
from pathlib import Path

HOOK_SRC = Path(__file__).with_name("run-scanner")
GIT_DIR = Path.cwd() / ".git"

def main() -> None:
    if not GIT_DIR.exists():
        sys.exit("❌  Not inside a Git repository.")
    hooks_dir = GIT_DIR / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    dest = hooks_dir / "run-scanner"
    shutil.copy2(HOOK_SRC, dest)
    dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
    print("✅  Pre‑push secret scanner installed!")

if __name__ == "__main__":
    main()
