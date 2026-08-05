"""wordup public API.

Exports a small, pure library surface with no terminal or filesystem I/O
at import time.  All lexicon loading is deferred to first call.

Exported names
--------------
suggest(text, lexicon=None) -> list[Match]
    Scan *text* for base words in the lexicon and return every match.
    When *lexicon* is ``None`` the shipped lexicon is loaded on first call.

apply_choices(text, choices) -> str
    Apply a sequence of accepted (span, replacement) choices to *text*,
    transferring the original casing and preserving all surrounding characters.

Lexicon
    Dataclass with classmethods ``default()`` and ``load(path)``.

Match
    Dataclass describing a single lexicon hit: span, surface, base, suffix,
    and a list of offered alternatives.
"""

from __future__ import annotations

from wordup.apply import apply_choices
from wordup.models import Lexicon
from wordup.scanner import Match, scan

__all__ = [
    "suggest",
    "apply_choices",
    "Lexicon",
    "Match",
]


def suggest(text: str, lexicon: Lexicon | None = None) -> list[Match]:
    """Scan *text* and return every lexicon match in document order.

    Parameters
    ----------
    text:
        The document to scan.
    lexicon:
        The :class:`Lexicon` to use.  When ``None`` the lexicon shipped with
        the package is loaded via :meth:`Lexicon.default`.  The caller can
        pass an explicit lexicon to avoid reloading on every call or to use a
        custom lexicon file.

    Returns
    -------
    list[Match]
        Matches in document order.  Tokens inside protected spans (fenced code
        blocks, inline code, URLs) are excluded.  Inflected alternatives that
        cannot be safely re-inflected are excluded.
    """
    if lexicon is None:
        lexicon = Lexicon.default()
    return scan(text, lexicon)
