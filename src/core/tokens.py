"""Deterministic token estimation used for bundle budgeting.

Bundle budgets are counted in tokens rather than characters because a
character budget means very different things per language: 6000 characters is
roughly 1800 tokens of English prose but roughly 4200 tokens of Chinese, so the
same config carries 2.3x more truncation risk on a Chinese document. Counting
tokens keeps the budget — and therefore the risk — language independent.

This is a heuristic, not a tokenizer. It must stay dependency free and
deterministic (the resolved budget ends up in checkpoint fingerprints, so the
same text has to produce the same number every run), and it deliberately errs
slightly high: an overestimate trims one bundle, an underestimate truncates a
response and loses the whole bundle.

Bump ``TOKEN_ESTIMATOR_VERSION`` whenever the weights change; it is part of the
checkpoint fingerprint so stale bundles are never resumed against new counts.
"""

from __future__ import annotations

import math

TOKEN_ESTIMATOR_VERSION = "tokens-v1"

# Roughly 1 token per 1.4 CJK characters, and 1 token per 3.3 characters of
# Latin prose/Markdown syntax. Both are slightly above what current
# BPE vocabularies produce, which is the safe direction for a ceiling.
_CJK_WEIGHT = 0.7
_OTHER_WEIGHT = 0.3

_CJK_RANGES: tuple[tuple[int, int], ...] = (
    (0x1100, 0x11FF),  # Hangul Jamo
    (0x2E80, 0x303F),  # CJK radicals and punctuation
    (0x3040, 0x30FF),  # Hiragana / Katakana
    (0x3400, 0x4DBF),  # CJK extension A
    (0x4E00, 0x9FFF),  # CJK unified ideographs
    (0xAC00, 0xD7AF),  # Hangul syllables
    (0xF900, 0xFAFF),  # CJK compatibility ideographs
    (0xFF00, 0xFF60),  # Fullwidth forms
    (0x20000, 0x3FFFF),  # CJK extensions B and beyond
)


def char_weight(char: str) -> float:
    """Estimated tokens contributed by a single character."""
    code = ord(char)
    for start, end in _CJK_RANGES:
        if start <= code <= end:
            return _CJK_WEIGHT
    return _OTHER_WEIGHT


def token_costs(text: str) -> list[float]:
    """Per-character token cost, the same length as ``text``."""
    if text.isascii():
        return [_OTHER_WEIGHT] * len(text)
    return [char_weight(char) for char in text]


def estimate_tokens(text: str) -> int:
    """Estimated token count of ``text`` (0 for empty input)."""
    if not text:
        return 0
    if text.isascii():
        return max(1, math.ceil(len(text) * _OTHER_WEIGHT))
    return max(1, math.ceil(sum(char_weight(char) for char in text)))


def prefix_costs(text: str) -> list[float]:
    """Cumulative token cost, ``prefix[i]`` covering ``text[:i]``.

    Sorted non-decreasing by construction, so the character window that fits a
    token budget can be located with a binary search instead of rescanning the
    text once per candidate cut.
    """
    prefix = [0.0] * (len(text) + 1)
    total = 0.0
    for index, cost in enumerate(token_costs(text)):
        total += cost
        prefix[index + 1] = total
    return prefix
