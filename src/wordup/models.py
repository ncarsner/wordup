"""Data types shared across the wordup package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Lexicon:
    """Mapping of base words to their curated alternatives.

    Use :meth:`default` to load the lexicon shipped with the package, or
    :meth:`load` to load a TOML file by path (useful for tests and custom
    lexicons).
    """

    entries: dict[str, list[str]]

    @classmethod
    def load(cls, path: Path) -> Lexicon:
        """Load and validate a lexicon from the TOML file at *path*."""
        from wordup.lexicon import load as _load  # deferred: avoids circular import

        return _load(path)

    @classmethod
    def default(cls) -> Lexicon:
        """Load the lexicon shipped with the package via importlib.resources."""
        from wordup.lexicon import (
            default as _default,
        )  # deferred: avoids circular import

        return _default()
