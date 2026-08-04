"""Conservative suffix stemming and re-inflection for wordup.

Suffix rules live in :data:`SUFFIX_TABLE` as data, not as branching code.
The public interface is :func:`stem` and :func:`reinflect`.

Limits
------
- Irregular verbs (go/went, be/was) are not handled.
- Consonant doubling is detected during stemming but withheld during
  re-inflection because syllable stress is unknown; words like "run"
  return ``None`` from :func:`reinflect` rather than producing "runing".
- Hyphenated alternatives (e.g. "clear-cut") are withheld when a suffix
  was stripped; they are offered normally on an exact base-word match.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

VOWELS: frozenset[str] = frozenset("aeiou")
CONSONANTS: frozenset[str] = frozenset("bcdfghjklmnpqrstvwxyz")


# ---------------------------------------------------------------------------
# Adjustment and guard functions (referenced by SUFFIX_TABLE rows)
# ---------------------------------------------------------------------------


def _ing_ed_restore(stem: str) -> str:
    """Reverse consonant doubling or restore terminal-e for -ing/-ed stems.

    Three branches:
    1. Doubled consonant (e.g. "runn" -> "run"): remove the extra copy.
    2. Vowel-consonant ending (e.g. "creat" -> "create"): restore the 'e'.
    3. Everything else: return the stem unchanged.
    """
    if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] in CONSONANTS:
        return stem[:-1]
    if len(stem) >= 2 and stem[-1] in CONSONANTS and stem[-2] in VOWELS:
        return stem + "e"
    return stem


def _es_guard(word: str) -> bool:
    """Return True when -es is a genuine suffix rather than a base-e plus -s.

    "matches" (ch + es) and "accesses" (s + es) return True.
    "requires" (r + es, base ends in 'e') returns False so the -s rule fires.
    """
    if len(word) < 3:
        return False
    pre = word[-3]  # character directly before "es"
    if pre in "sxz":
        return True
    if len(word) >= 4 and word[-4:-2] in ("ch", "sh"):
        return True
    return False


# ---------------------------------------------------------------------------
# Re-inflection functions (one per grammatical category)
# ---------------------------------------------------------------------------


def _reinflect_plural(word: str) -> str | None:
    """Produce the plural or 3rd-person-singular present form."""
    if word.endswith("y") and len(word) >= 2 and word[-2] in CONSONANTS:
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z")) or (len(word) >= 2 and word[-2:] in ("ch", "sh")):
        return word + "es"
    return word + "s"


def _reinflect_past(word: str) -> str | None:
    """Produce the simple-past form, or None when doubling would be needed."""
    if word.endswith("e"):
        return word + "d"
    if word.endswith("y") and len(word) >= 2 and word[-2] in CONSONANTS:
        return word[:-1] + "ied"
    # Conservative: vowel+consonant ending may require doubling (e.g. "run").
    if len(word) >= 2 and word[-1] in CONSONANTS and word[-2] in VOWELS:
        return None
    return word + "ed"


def _reinflect_progressive(word: str) -> str | None:
    """Produce the present-participle form, or None when doubling would be needed."""
    if word.endswith("e"):
        return word[:-1] + "ing"
    # Conservative: vowel+consonant ending may require doubling (e.g. "run").
    if len(word) >= 2 and word[-1] in CONSONANTS and word[-2] in VOWELS:
        return None
    return word + "ing"


def _reinflect_adverb(word: str) -> str | None:
    """Produce the adverbial form."""
    return word + "ly"


# ---------------------------------------------------------------------------
# Suffix rule table (module-level data, not branching code)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SuffixRule:
    """One row in :data:`SUFFIX_TABLE`."""

    suffix: str
    """Canonical suffix label, e.g. ``"-ing"``."""

    strip: int
    """Number of characters to remove from the word end during stemming."""

    restore: str
    """String appended after stripping (before *adjust* is called)."""

    reinflect_fn: Callable[[str], str | None]
    """Apply the grammatical category expressed by this suffix to a base word."""

    adjust: Callable[[str], str] | None = None
    """Optional post-strip stem adjustment (e.g. doubling/e-restore)."""

    guard: Callable[[str], bool] | None = None
    """Optional pre-match guard; the rule is skipped when this returns False."""

    min_stem: int = 2
    """Minimum stem length (after all transforms) for the rule to apply."""


SUFFIX_TABLE: list[SuffixRule] = [
    # Longer or more specific suffixes are listed first so they match before
    # their shorter sub-strings (e.g. "-ies" before "-es" before "-s").
    SuffixRule("-ies", 3, "y", _reinflect_plural),
    SuffixRule("-ied", 3, "y", _reinflect_past),
    SuffixRule(
        "-ing", 3, "", _reinflect_progressive, adjust=_ing_ed_restore, min_stem=3
    ),
    SuffixRule("-ed", 2, "", _reinflect_past, adjust=_ing_ed_restore),
    SuffixRule("-es", 2, "", _reinflect_plural, guard=_es_guard),
    SuffixRule("-s", 1, "", _reinflect_plural),
    SuffixRule("-ly", 2, "", _reinflect_adverb),
]


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def stem(word: str) -> tuple[str, str]:
    """Return ``(stem, suffix)`` for *word* by applying the first matching rule.

    Returns ``(word.lower(), "")`` when no rule matches.
    Stems are always lowercase; the suffix label uses the ``"-ing"`` form.

    Examples::

        stem("requires")  # -> ("require", "-s")
        stem("creating")  # -> ("create", "-ing")
        stem("running")   # -> ("run", "-ing")
        stem("hello")     # -> ("hello", "")
    """
    lower = word.lower()
    for rule in SUFFIX_TABLE:
        raw = rule.suffix.lstrip("-")  # "-ing" -> "ing"
        if not lower.endswith(raw):
            continue
        if rule.guard is not None and not rule.guard(lower):
            continue
        candidate = lower[: len(lower) - rule.strip] + rule.restore
        if rule.adjust is not None:
            candidate = rule.adjust(candidate)
        if len(candidate) >= rule.min_stem:
            return candidate, rule.suffix
    return lower, ""


def reinflect(word: str, suffix: str) -> str | None:
    """Apply *suffix* to *word*, returning the inflected form or ``None``.

    When *suffix* is the empty string the word is returned as-is, including
    multi-word alternatives such as "deal with" (AC: offered on exact match).

    Returns ``None`` when:
    - *suffix* is non-empty and *word* contains a space (multi-word) or a
      hyphen (e.g. "clear-cut") -- these cannot be inflected safely.
    - The inflection would require consonant doubling, which is ambiguous
      without syllable-stress information.
    - *suffix* is unrecognized.

    Examples::

        reinflect("demand",    "-s")   # -> "demands"
        reinflect("generate",  "-ing") # -> "generating"
        reinflect("deal with", "")     # -> "deal with"  (offered on exact match)
        reinflect("deal with", "-s")   # -> None         (withheld when suffix stripped)
        reinflect("clear-cut", "-ing") # -> None         (hyphenated, withheld)
        reinflect("run",       "-ing") # -> None         (doubling required, withheld)
    """
    if suffix == "":
        return word
    if " " in word or "-" in word:
        return None
    for rule in SUFFIX_TABLE:
        if rule.suffix == suffix:
            return rule.reinflect_fn(word)
    return None
