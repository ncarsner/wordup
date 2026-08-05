"""Sentence window extraction for wordup.

Given a character offset into a document, :func:`sentence_span` returns the
half-open ``[start, end)`` offsets of the sentence that contains that offset.

The function splits on terminal punctuation (``'.'``, ``'!'``, ``'?'``) when
followed by whitespace and an uppercase letter, but guards against:

* Common abbreviations (``e.g.``, ``i.e.``, ``Dr.``, ``Mr.``, ``Mrs.``,
  ``vs.``, ``etc.``).
* Decimal numbers (e.g. ``3.14``): a decimal dot is always followed by
  digits, never by whitespace and a capital letter, so the boundary pattern
  cannot match it -- the guard is implicit in the regex.

When no terminal punctuation boundary is found the function falls back to the
surrounding block, defined as the run of text between blank lines.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Abbreviation guard
# ---------------------------------------------------------------------------

# All abbreviation stems (the part before the final dot) that should never
# trigger a sentence split, stored as a frozenset for O(1) lookup.
_ABBREV_STEMS: frozenset[str] = frozenset(
    [
        # Latin phrases
        "e.g",
        "i.e",
        "etc",
        "vs",
        # Titles
        "dr",
        "mr",
        "mrs",
        "ms",
        "prof",
        "sr",
        "jr",
        "st",
        # More common abbreviations
        "no",
        "vol",
        "fig",
        "dept",
        "approx",
        "corp",
        "inc",
        "ltd",
        "est",
    ]
)

# Match a potential sentence boundary: one of .!? followed by whitespace and
# then an uppercase letter.  The decimal-dot case (e.g. "3.14") is implicitly
# excluded because a decimal dot is followed by digits, not by whitespace.
_BOUNDARY = re.compile(r"([.!?])(\s+)(?=[A-Z])")


def _is_abbreviation(text: str, dot_pos: int) -> bool:
    """Return True if the dot at *dot_pos* ends a known abbreviation.

    Looks backward from the dot to find the preceding word and checks it
    against :data:`_ABBREV_STEMS`.
    """
    # Walk backwards to find the start of the preceding word.
    i = dot_pos - 1
    while i >= 0 and (text[i].isalpha() or text[i] == "."):
        i -= 1
    stem = text[i + 1 : dot_pos].lower()
    return stem in _ABBREV_STEMS


def sentence_span(text: str, offset: int) -> tuple[int, int]:
    """Return the ``[start, end)`` span of the sentence containing *offset*.

    Parameters
    ----------
    text:
        The full document text.
    offset:
        A character offset into *text* (e.g. the start of a match).

    Returns
    -------
    tuple[int, int]
        Half-open offsets of the containing sentence.  When no boundary can be
        detected, the offsets of the surrounding block (text between blank
        lines) are returned instead.
    """
    length = len(text)

    # Collect all valid sentence-boundary positions (index of the character
    # immediately after the terminal punctuation + whitespace, i.e. the first
    # character of the new sentence).
    boundaries: list[int] = []
    for m in _BOUNDARY.finditer(text):
        dot_pos = m.start(1)
        if m.group(1) == "." and _is_abbreviation(text, dot_pos):
            continue
        # The boundary starts at the first character of the next sentence.
        boundaries.append(m.end())

    if not boundaries:
        # Fallback: find the block delimited by blank lines.
        return _block_span(text, offset)

    # Find the sentence whose range contains offset.
    # Sentence i spans from boundaries[i-1] to boundaries[i] (exclusive end).
    # Sentence 0 starts at 0.
    # The last sentence runs to the end of the document.

    # Build sentence start/end pairs.
    starts = [0] + boundaries
    ends = boundaries + [length]

    for start, end in zip(starts, ends):
        if start <= offset < end:
            return (start, end)

    # Offset equals or exceeds length (e.g. caller passed len(text)).
    return (starts[-1], length)


def _block_span(text: str, offset: int) -> tuple[int, int]:
    """Return the ``[start, end)`` span of the blank-line-delimited block
    containing *offset*.
    """
    # A blank line is two consecutive newlines (possibly with whitespace
    # between them).
    blank = re.compile(r"\n[ \t]*\n")

    # Find all blank-line positions.
    split_points = [0]
    for m in blank.finditer(text):
        split_points.append(m.end())
    split_points.append(len(text))

    for i in range(len(split_points) - 1):
        start = split_points[i]
        end = split_points[i + 1]
        if start <= offset < end:
            return (start, end)

    return (0, len(text))
