"""Lexicon loading and validation."""

from __future__ import annotations

import tomllib
from collections.abc import Iterable
from importlib.resources import files
from pathlib import Path
from typing import Any

from wordup.errors import (
    BaseInAlternativesError,
    DuplicateAlternativeError,
    DuplicateBaseWordError,
    EmptyAlternativesError,
    MalformedLexiconError,
    SelfReferentialAlternativeError,
)
from wordup.models import Lexicon


def _validate(pairs: Iterable[tuple[str, Any]]) -> dict[str, list[str]]:
    """Return a validated entries dict from an iterable of (base, alts) pairs.

    Accepts an iterable rather than a plain dict so that tests can pass
    duplicate-key pairs, which Python dicts and TOML files both deduplicate
    before this function could see them.

    Raises a typed :class:`~wordup.errors.WordupError` subclass for each
    data invariant violation.
    """
    entries: dict[str, list[str]] = {}
    seen_alternatives: dict[str, str] = {}  # alternative -> owning base word

    for base, alts_raw in pairs:
        # Invariant 1: no duplicate base words.
        if base in entries:
            raise DuplicateBaseWordError(f"Duplicate base word: {base!r}")

        # Invariant 3a: a word that was already seen as an alternative cannot
        # also appear as a base word.
        if base in seen_alternatives:
            raise BaseInAlternativesError(
                f"Word {base!r} is both a base word and an alternative"
                f" under {seen_alternatives[base]!r}"
            )

        # Structural check: value must be a non-empty list.
        if not isinstance(alts_raw, list):
            raise MalformedLexiconError(
                f"Entry {base!r} value must be a list, got {type(alts_raw).__name__!r}"
            )

        # Invariant 5: alternatives list must not be empty.
        if not alts_raw:
            raise EmptyAlternativesError(
                f"Entry {base!r} has an empty alternatives list"
            )

        alts: list[str] = [str(a) for a in alts_raw]

        # Invariant 4: a base word must not appear among its own alternatives.
        if base in alts:
            raise SelfReferentialAlternativeError(
                f"Entry {base!r} lists itself among its alternatives"
            )

        for alt in alts:
            # Invariant 3b: an alternative that is also a base word elsewhere.
            if alt in entries:
                raise BaseInAlternativesError(
                    f"Alternative {alt!r} in entry {base!r} is also a base word"
                )
            # Invariant 2: an alternative that appears in more than one entry.
            if alt in seen_alternatives:
                raise DuplicateAlternativeError(
                    f"Alternative {alt!r} appears in both"
                    f" {seen_alternatives[alt]!r} and {base!r}"
                )
            seen_alternatives[alt] = base

        entries[base] = alts

    return entries


def load(path: Path) -> Lexicon:
    """Load and validate a lexicon from the TOML file at *path*."""
    try:
        with open(path, "rb") as f:
            raw: dict[str, Any] = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise MalformedLexiconError(f"Malformed TOML in {path}: {exc}") from exc
    entries = _validate(raw.items())
    return Lexicon(entries=entries)


def default() -> Lexicon:
    """Load the lexicon bundled with the package via importlib.resources."""
    ref = files("wordup") / "data" / "lexicon.toml"
    try:
        with ref.open("rb") as f:
            raw: dict[str, Any] = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise MalformedLexiconError(f"Malformed bundled lexicon TOML: {exc}") from exc
    entries = _validate(raw.items())
    return Lexicon(entries=entries)
