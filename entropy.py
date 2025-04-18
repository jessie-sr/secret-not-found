# entropy.py
"""
Simple Shannon‑entropy calculation for an ASCII string.
"""

from math import log2
from collections import Counter

def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((c/length) * log2(c/length) for c in counts.values())

def looks_random(s: str, threshold: float = 4.0) -> bool:
    """Heuristic: ≥4 bits/char is suspicious for secrets."""
    return shannon_entropy(s) >= threshold and len(s) >= 20
