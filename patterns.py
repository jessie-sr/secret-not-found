# patterns.py
"""
Common API‑key / secret patterns.
Extend as needed (AWS, Twilio, etc.).
"""

import re

REGEX_PATTERNS: dict[str, re.Pattern] = {
    # Stripe: sk_live_...
    "Stripe secret": re.compile(r"sk_live_[0-9a-zA-Z]{24,}"),
    # GitHub personal access token: ghp_...
    "GitHub PAT":   re.compile(r"ghp_[0-9A-Za-z]{36,}"),
    # AWS access key ID: AKIA...
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    # Slack token: xox[baprs]-...
    "Slack token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,48}"),
}
