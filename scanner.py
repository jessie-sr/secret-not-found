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
import signal

# 1) Define SCRIPT_DIR first
SCRIPT_DIR = Path(__file__).parent.absolute()

# 2) Then point to the repo’s .gitignore (one level up from the scanner folder)
GITIGNORE_PATH = SCRIPT_DIR.parent / ".gitignore"

# 3) Your “should‑ignore” candidates
CANDIDATE_IGNORES = {".env", "secrets.yaml", "config.json", "*.local"}



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


# def staged_files() -> list[Path]:
#     """Return list of staged (added/modified) files."""
#     try:
#         # First get all files that would be pushed
#         diff_cmd = ["git", "diff", "--name-only", "--cached"]
#         out = subprocess.check_output(diff_cmd, text=True)

#         # Also get files that are committed but not pushed yet
#         branch_cmd = ["git", "branch", "--show-current"]
#         branch = subprocess.check_output(branch_cmd, text=True).strip()

#         remote_cmd = ["git", "rev-parse", "--abbrev-ref", f"{branch}@{{u}}"]
#         try:
#             remote = subprocess.check_output(remote_cmd, text=True).strip()
#             diff_unpushed_cmd = ["git", "diff", "--name-only", f"{remote}..HEAD"]
#             unpushed_out = subprocess.check_output(diff_unpushed_cmd, text=True)
#             out += unpushed_out
#         except subprocess.CalledProcessError:
#             # Likely a new branch with no upstream yet
#             log_cmd = ["git", "log", "--name-only", "--pretty=format:", "HEAD"]
#             unpushed_out = subprocess.check_output(log_cmd, text=True)
#             out += unpushed_out

#         # files = [Path(line.strip()) for line in out.splitlines() if line.strip()]
#         # return [f for f in files if f.exists() and not any(p in str(f) for p in IGNORE_PATHS)]
#             files = [Path(line.strip()) for line in out.splitlines() if line.strip()]
#     # only keep real files, not dirs, and skip ignored paths
#             return [
#                 f for f in files
#                 if f.exists()
#                 and f.is_file()
#                 and not any(p in str(f) for p in IGNORE_PATHS)
#             ]

#     except subprocess.CalledProcessError as e:
#         print(f"Error getting staged files: {e}", file=sys.stderr)
#         # If we can't determine files, assume all tracked files
#         try:
#             ls_cmd = ["git", "ls-files"]
#             out = subprocess.check_output(ls_cmd, text=True)
#             files = [Path(line.strip()) for line in out.splitlines() if line.strip()]
#             return [f for f in files if f.exists() and not any(p in str(f) for p in IGNORE_PATHS)]
#         except subprocess.CalledProcessError:
#             print("Unable to determine files to scan!", file=sys.stderr)
#             return []
def staged_files() -> list[Path]:
    """Return list of staged (added/modified) files."""
    try:
        # First get all files that would be pushed
        diff_cmd = ["git", "diff", "--name-only", "--cached"]
        out = subprocess.check_output(diff_cmd, text=True)

        # Also get files that are committed but not pushed yet
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], text=True
        ).strip()

        remote_cmd = ["git", "rev-parse", "--abbrev-ref", f"{branch}@{{u}}"]
        try:
            # <-- suppress stderr here so we don’t see “fatal: no upstream…”
            remote = subprocess.check_output(
                remote_cmd,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
            diff_unpushed_cmd = ["git", "diff", "--name-only", f"{remote}..HEAD"]
            unpushed_out = subprocess.check_output(
                diff_unpushed_cmd,
                stderr=subprocess.DEVNULL,
                text=True
            )
            out += unpushed_out
        except subprocess.CalledProcessError:
            # new branch with no upstream yet
            log_cmd = ["git", "log", "--name-only", "--pretty=format:", "HEAD"]
            unpushed_out = subprocess.check_output(
                log_cmd,
                stderr=subprocess.DEVNULL,
                text=True
            )
            out += unpushed_out

        files = [Path(line.strip()) for line in out.splitlines() if line.strip()]
        return [
            f for f in files
            if f.exists()
            and f.is_file()
            and not any(p in str(f) for p in IGNORE_PATHS)
        ]
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

def _update_gitignore_and_unstage(to_ignore: list[Path]) -> None:
    # 1) Read existing .gitignore entries
    existing = set()
    if GITIGNORE_PATH.exists():
        existing = {
            line.strip()
            for line in GITIGNORE_PATH.read_text().splitlines()
        }

    # 2) Append any missing entries to .gitignore
    with open(GITIGNORE_PATH, "a") as gi:
        for path in to_ignore:
            entry = path.name
            if entry not in existing:
                gi.write(entry + "\n")
                print(f"  → Added to .gitignore: {entry}")

    # 3) Unstage each of those files
    for path in to_ignore:
        subprocess.run(["git", "rm", "--cached", str(path)], check=False)
        print(f"  → Unstaged: {path}")

def timeout_handler(signum, frame):
    raise TimeoutError
import threading

def input_with_timeout(prompt, timeout=10, default="n"):
    user_input = [default]

    def ask():
        try:
            user_input[0] = input(prompt).strip().lower()
        except EOFError:
            pass  # Happens in some terminal environments

    thread = threading.Thread(target=ask)
    thread.daemon = True
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        print(f"\n⏱️  No input received in {timeout}s. Defaulting to [{default.upper()}].")
    return user_input[0] or default


def main() -> None:
    # Test mode – skip everything else
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Hook test OK")
        sys.exit(0)

    files = staged_files()
    if not files:
        print("No files to scan.")
        sys.exit(0)

    # --- Detect files that should be .gitignore'd (like .env, secrets.yaml etc.) ---
    pending = [
        f for f in files
        if any(f.match(p) for p in CANDIDATE_IGNORES)
    ]
    if pending:
        print("⚠️  The following configuration/secret files may not be intended for push:")
        for f in pending:
            print(f"  · {f}")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)  # ⏳ Wait up to 10 seconds for user input

        try:
            choice = input_with_timeout("Add them to .gitignore & unstage? [y/N, timeout in 10s]: ", timeout=10, default="n")
            signal.alarm(0)  # 🛑 Cancel timeout if user responded
        except TimeoutError:
            print("\n⏱️  No input received. Defaulting to [N].")
            choice = "n"

        if choice == "y":
            _update_gitignore_and_unstage(pending)
            print("✅ .gitignore updated and files unstaged. Please review, then re-stage and commit.")
            sys.exit(1)
        else:
            print("📦  Continuing with the normal scan (you chose not to ignore these files).")

    # --- Secret scanning begins here ---
    patterns = load_patterns()
    looks_random_fn = load_entropy()

    print(f"Scanning {len(files)} files...")

    offenders = {}
    for file in files:
        file_hits = scan_file(file, patterns, looks_random_fn)
        if file_hits:
            offenders[file] = file_hits

    if not offenders:
        print("✅ No secrets detected.")
        sys.exit(0)  # Allow push

    # Output detected secrets
    print("\n🚨  Secret(s) detected! Push blocked to protect your keys.\n")
    for path, hits in offenders.items():
        for ln, detector, snippet in hits:
            print(f"{path}:{ln} [{detector}]\n  {snippet}\n")

    print("👉  Bypass (not recommended): git push --no-verify\n")
    sys.exit(1)  # Block push

if __name__ == "__main__":
    main()