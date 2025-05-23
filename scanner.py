#!/usr/bin/env python3
"""
Pre-push Secret Scanner
Scans staged files for hard-coded secrets.
Blocks push if anything fishy is found.
"""

from __future__ import annotations
import subprocess
import sys
import os
from pathlib import Path
import re
import importlib.util
import time
import shutil

# Get the directory of the current script
SCRIPT_DIR = Path(__file__).parent.absolute()

# Files/dirs to ignore outright
IGNORE_PATHS = {".git/", "node_modules/", "__pycache__/"}


# Load patterns module from the same directory
def load_patterns():
    pattern_path = SCRIPT_DIR / "patterns.py"
    spec = importlib.util.spec_from_file_location("patterns", pattern_path)
    patterns = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patterns)
    return patterns.REGEX_PATTERNS


# Load entropy module from the same directory
def load_entropy():
    entropy_path = SCRIPT_DIR / "entropy.py"
    spec = importlib.util.spec_from_file_location("entropy", entropy_path)
    entropy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entropy)
    return entropy.looks_random


def staged_files() -> list[Path]:
    """Return list of staged (added/modified) files."""
    try:
        # First get all files that would be pushed
        diff_cmd = ["git", "diff", "--name-only", "--cached"]
        out = subprocess.check_output(diff_cmd, text=True)

        # Also get files that are committed but not pushed yet
        branch_cmd = ["git", "branch", "--show-current"]
        branch = subprocess.check_output(branch_cmd, text=True).strip()

        remote_cmd = ["git", "rev-parse", "--abbrev-ref", f"{branch}@{{u}}"]
        try:
            remote = subprocess.check_output(remote_cmd, text=True).strip()
            diff_unpushed_cmd = ["git", "diff", "--name-only", f"{remote}..HEAD"]
            unpushed_out = subprocess.check_output(diff_unpushed_cmd, text=True)
            out += unpushed_out
        except subprocess.CalledProcessError:
            # Likely a new branch with no upstream yet
            log_cmd = ["git", "log", "--name-only", "--pretty=format:", "HEAD"]
            unpushed_out = subprocess.check_output(log_cmd, text=True)
            out += unpushed_out

        files = [Path(line.strip()) for line in out.splitlines() if line.strip()]
        return [f for f in files if f.exists() and not any(p in str(f) for p in IGNORE_PATHS)]
    except subprocess.CalledProcessError as e:
        print(f"Error getting staged files: {e}", file=sys.stderr)
        # If we can't determine files, assume all tracked files
        try:
            ls_cmd = ["git", "ls-files"]
            out = subprocess.check_output(ls_cmd, text=True)
            files = [Path(line.strip()) for line in out.splitlines() if line.strip()]
            return [f for f in files if f.exists() and not any(p in str(f) for p in IGNORE_PATHS)]
        except subprocess.CalledProcessError:
            print("Unable to determine files to scan!", file=sys.stderr)
            return []


def scan_file(path: Path, patterns, looks_random_fn) -> list[tuple[int, str, str]]:
    """
    Return list of (line_no, detector_name, line_text) hits in a file.
    """
    hits = []
    try:
        with open(path, 'r', errors='ignore') as f:
            for ln, line in enumerate(f, 1):
                # Regex scans
                for name, pattern in patterns.items():
                    if pattern.search(line):
                        hits.append((ln, name, line.strip()))

                # Entropy scan
                for token in line.split():
                    if looks_random_fn(token):
                        hits.append((ln, "High entropy", line.strip()))
    except Exception as e:
        # Binary or unreadable file; skip
        print(f"Warning: Could not scan {path}: {e}", file=sys.stderr)
    return hits


def main() -> None:
    # Test mode - just verify we can run
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Hook test OK")
        sys.exit(0)

    # print("🔍 Scanning for secrets in files to be pushed...")

    # Load our patterns and entropy function
    patterns = load_patterns()
    looks_random_fn = load_entropy()

    offenders = {}
    files = staged_files()

    if not files:
        print("No files to scan.")
        sys.exit(0)

    print(f"Scanning {len(files)} files...")

    for file in files:
        file_hits = scan_file(file, patterns, looks_random_fn)
        if file_hits:
            offenders[file] = file_hits

    if not offenders:
        print("✅ No secrets detected.")
        sys.exit(0)  # All clear → allow push

    # Pretty CLI output
    print("\n🚨  Secret(s) detected! Push blocked to protect your keys.\n")
    for path, hits in offenders.items():
        for ln, detector, snippet in hits:
            print(f"{path}:{ln} [{detector}]\n  {snippet}\n")
    # print("💡  Suggestion: Move secrets to environment variables (.env) and reference them, "
    #       "or add false positives to an ignore list.\n")
    print("👉  Bypass (not recommended): git push --no-verify\n")

    choice = input("\n🛡️  Do you want to add these files to .gitignore to prevent accidental commits? (y/N): ").strip().lower()
    if choice == 'y':
        gitignore_path = Path(".gitignore")
        existing_ignores = set()
        if gitignore_path.exists():
            existing_ignores = set(gitignore_path.read_text().splitlines())

        with gitignore_path.open("a") as f:
            for file in offenders:
                if str(file) not in existing_ignores:
                    f.write(f"\n{file}")

        print("✅ Added to .gitignore.")
        print("ℹ️  Reminder: These files are now ignored, but if they were previously tracked by Git, you should unstage them:")
        for file in offenders:
            print(f"   git rm --cached {file}")
        print("💡 Then commit the removal to fully stop tracking them.")

    
    # choice = input("\n🧹 Do you want to remove these files from your Git history? (y/N): ").strip().lower()
    # if choice == 'y':
    #     for file in offenders:
    #         rel_path = str(file)
    #         backup_path = Path(f"{rel_path}.backup")

    #         # Step 1: Back up the file
    #         try:
    #             shutil.copy(rel_path, backup_path)
    #             print(f"📦 Backed up {rel_path} to {backup_path}")
    #         except Exception as e:
    #             print(f"⚠️ Failed to back up {rel_path}: {e}")
    #             continue

    #         # Step 2: Remove from history
    #         print(f"🔨 Rewriting history to remove {rel_path}...")
    #         try:
    #             subprocess.run(
    #                 ["git", "filter-repo", "--force", "--path", rel_path, "--invert-paths"],
    #                 check=True
    #             )
    #             print(f"✅ Removed {rel_path} from history.")
    #         except subprocess.CalledProcessError:
    #             print(f"❌ Failed to remove {rel_path} from history.", file=sys.stderr)
    #             continue

    #         # Step 3: Restore the file
    #         try:
    #             shutil.move(backup_path, rel_path)
    #             print(f"♻️ Restored {rel_path} from backup.")
    #         except Exception as e:
    #             print(f"⚠️ Failed to restore {rel_path}: {e}")

    sys.exit(1)  # Block push


if __name__ == "__main__":
    main()