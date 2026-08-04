"""Typed exceptions for the wordup package."""

from __future__ import annotations


class WordupError(Exception):
    """Base class for all wordup exceptions."""


class DuplicateBaseWordError(WordupError):
    """A base word appears more than once in the lexicon."""


class DuplicateAlternativeError(WordupError):
    """An alternative appears in more than one lexicon entry."""


class BaseInAlternativesError(WordupError):
    """A word is both a base word and an alternative in another entry."""


class SelfReferentialAlternativeError(WordupError):
    """An entry lists its own base word among its alternatives."""


class EmptyAlternativesError(WordupError):
    """An entry has an empty alternatives list."""


class MalformedLexiconError(WordupError):
    """The lexicon TOML is malformed or structurally invalid."""
