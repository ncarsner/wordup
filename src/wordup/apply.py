"""Span-slicing replacement with case transfer.

A ``Choice`` is a ``(span, replacement)`` pair where *span* is a
``(start, end)`` half-open offset pair from a :class:`~wordup.scanner.Match`
and *replacement* is the raw lexicon alternative string (always lowercase).

:func:`apply_choices` rebuilds the original text, substituting each chosen
replacement and transferring the capitalisation pattern of the matched surface
onto the replacement string.  All other characters, including newlines, tabs,
blank lines, and runs of spaces, are preserved exactly.
"""

from __future__ import annotations

from typing import Sequence

# A single choice: the span to replace and the raw replacement string.
Choice = tuple[tuple[int, int], str]


def transfer_case(surface: str, replacement: str) -> str:
    """Transfer the capitalisation pattern of *surface* onto *replacement*.

    Three patterns are recognised:

    - ALL UPPERCASE: every character of *replacement* is uppercased.
    - Title case (first character upper, rest lower): first character of
      *replacement* is uppercased, remainder is left as-is.  This preserves
      multi-word alternatives correctly (e.g. "Deal with", not "Deal With").
    - lowercase: *replacement* is lowercased.

    Any other pattern (mixed case) is passed through unchanged.
    """
    if surface.isupper():
        return replacement.upper()
    if surface[0].isupper():
        # Title-ish: capitalise only the first character.
        return replacement[0].upper() + replacement[1:]
    if surface.islower():
        return replacement.lower()
    # Mixed case: return replacement unchanged.
    return replacement


def apply_choices(text: str, choices: Sequence[Choice]) -> str:
    """Return *text* with each accepted choice substituted.

    Parameters
    ----------
    text:
        The original document string.
    choices:
        A sequence of ``(span, replacement)`` pairs, where *span* is a
        half-open ``(start, end)`` offset pair and *replacement* is the raw
        lexicon alternative.  Pairs must be in document order (ascending
        start) and must not overlap.  The function raises :class:`ValueError`
        when either condition is violated.

    Returns
    -------
    str
        The rebuilt document.  When *choices* is empty the return value is
        byte-identical to *text*.  Surrounding characters such as punctuation,
        parentheses, hyphens, and whitespace are never altered.
    """
    # Validate: choices must be sorted and non-overlapping.
    for i in range(len(choices) - 1):
        (start_a, end_a), _ = choices[i]
        (start_b, _), _ = choices[i + 1]
        if start_a > start_b:
            raise ValueError(
                f"choices are not in document order: span starting at {start_a}"
                f" appears before span starting at {start_b}"
            )
        if end_a > start_b:
            raise ValueError(
                f"choices overlap: span ({start_a}, {end_a})"
                f" overlaps span starting at {start_b}"
            )

    # Rebuild in a single forward pass using string accumulation.
    # The implementation avoids str.split and str.join by design.
    result = ""
    cursor = 0
    for (start, end), replacement in choices:
        # Copy everything between the previous replacement and this span.
        result += text[cursor:start]
        # Extract the original surface form to determine case.
        surface = text[start:end]
        # Substitute the case-transferred replacement.
        result += transfer_case(surface, replacement)
        cursor = end
    # Append any trailing text after the last replacement.
    result += text[cursor:]
    return result
