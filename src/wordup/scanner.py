"""Span-based lexicon scanner for wordup.

The scanner finds every occurrence of a lexicon base word (or a common
inflected form of one) in *text*, excluding spans that are protected by the
:mod:`wordup.protect` module, and returns them as a list of :class:`Match`
objects in document order.

The scanner never calls ``print``, ``input``, or any filesystem function.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from wordup.inflect import reinflect, stem
from wordup.models import Lexicon
from wordup.protect import overlaps, protected_spans

# One compiled pattern that grabs every word-like token in the document.
# We do not embed base words in the pattern because terminal-e dropping and
# consonant+y changes mean the base word is not always a literal prefix of the
# inflected surface form.  For example, "create" surfaces as "creating" (not
# "create" + chars), and "fortify" surfaces as "fortifies" (not "fortify" +
# chars).  Case-folding is handled with .lower() before lookup, so
# re.IGNORECASE is not used here.
_TOKEN = re.compile(r"\b\w+\b")


@dataclass
class Match:
    """A single lexicon match within the scanned text.

    Attributes
    ----------
    span:
        Half-open ``[start, end)`` offsets into the original string.
    surface:
        The matched word exactly as it appeared in the source text,
        preserving the original casing.
    base:
        The lexicon key (always lowercase).
    suffix:
        The stripped suffix label (e.g. ``"-s"``, ``"-ing"``), or ``""``
        when the surface form was an exact base-word match.
    alternatives:
        Offered alternatives, already re-inflected to match the surface
        form's grammatical number or tense.  Multi-word and hyphenated
        entries that cannot be safely re-inflected are excluded when
        *suffix* is non-empty.  Lexicon order is preserved.
    """

    span: tuple[int, int]
    surface: str
    base: str
    suffix: str
    alternatives: list[str] = field(default_factory=list)


def scan(text: str, lexicon: Lexicon) -> list[Match]:
    """Return every lexicon match in *text* in document order.

    Parameters
    ----------
    text:
        The document to scan.
    lexicon:
        The :class:`~wordup.models.Lexicon` to use for lookup.  The caller
        is responsible for loading the lexicon (e.g. via
        :meth:`~wordup.models.Lexicon.default`).

    Returns
    -------
    list[Match]
        Matches in document order (ascending start offset).  Tokens that
        overlap a protected span (code blocks, URLs) are excluded.
        Alternatives are filtered so that multi-word and hyphenated entries
        are withheld when *suffix* is non-empty.
    """
    protected = protected_spans(text)
    matches: list[Match] = []

    for m in _TOKEN.finditer(text):
        span = (m.start(), m.end())

        # Skip tokens inside protected regions (code blocks, URLs).
        if overlaps(span, protected):
            continue

        surface = m.group(0)
        lower = surface.lower()

        # Try exact lookup first, then stemmed lookup.
        # Exact-before-stem is load-bearing: words like "bias" (which ends in
        # the same character sequence as the -s suffix strip) would produce a
        # garbage stem ("bia") if we tried stemming first.
        if lower in lexicon.entries:
            base = lower
            suffix = ""
        else:
            base_candidate, stripped_suffix = stem(lower)
            if base_candidate in lexicon.entries:
                base = base_candidate
                suffix = stripped_suffix
            else:
                # Token does not resolve to a base word; skip it.
                continue

        # Build the alternative list, filtering through the reinflect guard.
        # reinflect() returns None for multi-word and hyphenated entries when
        # suffix is non-empty, so those are naturally excluded.
        # Lexicon alternative order is preserved.
        alternatives: list[str] = [
            inflected
            for alt in lexicon.entries[base]
            if (inflected := reinflect(alt, suffix)) is not None
        ]

        matches.append(
            Match(
                span=span,
                surface=surface,
                base=base,
                suffix=suffix,
                alternatives=alternatives,
            )
        )

    return matches
