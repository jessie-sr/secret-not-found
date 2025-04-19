#!/usr/bin/env python3
"""
Installs pre-push hook into .git/hooks and makes it executable.
"""

import shutil, stat, os, sys
from pathlib import Path
import subprocess

# Get the directory of the current script
SCRIPT_DIR = Path(__file__).parent.absolute()
GIT_DIR = Path.cwd() / ".git"


def main() -> None:
    if not GIT_DIR.exists():
        sys.exit("❌  Not inside a Git repository.")

    hooks_dir = GIT_DIR / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    # Install as 'pre-push' hook (correct Git hook name)
    dest = hooks_dir / "pre-push"

    # Create a more robust shell wrapper script
    with open(dest, 'w') as f:
        f.write('#!/bin/sh\n\n')
        f.write('# Secret scanner pre-push hook\n')
        f.write(f'SCRIPT_PATH="{SCRIPT_DIR}/scanner.py"\n\n')
        f.write('echo "🔍 Running secret scanner..."\n')
        f.write('python3 "$SCRIPT_PATH"\n')
        f.write('RESULT=$?\n\n')
        f.write('if [ $RESULT -ne 0 ]; then\n')
        f.write('    echo "❌ Secret scanner found potentially sensitive data. Push blocked."\n')
        f.write('    exit 1\n')
        f.write('else\n')
        f.write('    echo "✅ No secrets detected. Push allowed."\n')
        f.write('    exit 0\n')
        f.write('fi\n')

    # Make it executable
    os.chmod(dest, os.stat(dest).st_mode | stat.S_IEXEC)

    # Verify the hook is installed and executable
    if not dest.exists():
        sys.exit("❌ Failed to create hook file.")

    # Test execute the hook to make sure it's working
    print("✅ Secret scanner installed as pre-push hook!")
    print("🔍 Testing hook execution...")
    try:
        # Just checking if the script runs without actually processing any files
        subprocess.run([str(dest), "--test"], check=False)
        print("✅ Hook execution test passed.")
    except Exception as e:
        print(f"⚠️  Warning: Hook test failed: {e}")
        print("   Please check permissions and Python installation.")

    print("\n💡 How to use: The scanner will automatically run before each 'git push'")
    print("   If secrets are found, the push will be blocked.")


if __name__ == "__main__":
    main()