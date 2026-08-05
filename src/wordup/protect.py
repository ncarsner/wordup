"""Detect spans in text that must never be prompted: code blocks and URLs."""

from __future__ import annotations

import re

# One compiled pattern per protected region type.

# Fenced code blocks: triple-backtick fences and everything between them.
_FENCED = re.compile(r"```.*?```", re.DOTALL)

# Indented code blocks: lines starting with four spaces or a tab.
_INDENTED = re.compile(r"^(?: {4}|\t).+$", re.MULTILINE)

# Inline code: single-backtick spans (no embedded backticks or newlines).
_INLINE = re.compile(r"`[^`\n]+`")

# Bare URLs: http:// or https:// followed by non-whitespace characters.
_URL = re.compile(r"https?://\S+")

_PATTERNS = (_FENCED, _INDENTED, _INLINE, _URL)


def protected_spans(text: str) -> list[tuple[int, int]]:
    """Return merged, sorted, non-overlapping (start, end) offsets of protected regions.

    Each tuple is a half-open interval [start, end) into *text*.  Fenced code
    blocks, indented code lines, inline backtick spans, and bare http/https
    URLs are all included.
    """
    spans: list[tuple[int, int]] = []
    for pattern in _PATTERNS:
        for m in pattern.finditer(text):
            spans.append((m.start(), m.end()))
    return _merge(spans)


def _merge(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or adjacent spans into sorted, non-overlapping intervals."""
    if not spans:
        return []
    sorted_spans = sorted(spans)
    merged: list[tuple[int, int]] = [sorted_spans[0]]
    for start, end in sorted_spans[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def overlaps(span: tuple[int, int], protected: list[tuple[int, int]]) -> bool:
    """Return True if *span* overlaps any interval in *protected*.

    *protected* must be sorted and non-overlapping, as returned by
    :func:`protected_spans`.  Both *span* and the intervals in *protected* are
    treated as half-open [start, end) intervals.
    """
    s, e = span
    for ps, pe in protected:
        if ps >= e:
            # Protected spans are sorted; nothing further can overlap.
            break
        if pe > s:
            return True
    return False
