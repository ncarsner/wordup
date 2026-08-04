"""Tests for lexicon loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from wordup.errors import (
    BaseInAlternativesError,
    DuplicateAlternativeError,
    DuplicateBaseWordError,
    EmptyAlternativesError,
    MalformedLexiconError,
    SelfReferentialAlternativeError,
)
from wordup.lexicon import _validate
from wordup.models import Lexicon


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def toml_file(tmp_path: Path):
    """Write TOML content to a temporary file and return the path."""

    def _write(content: str) -> Path:
        p = tmp_path / "lexicon.toml"
        p.write_text(content, encoding="utf-8")
        return p

    return _write


# ---------------------------------------------------------------------------
# Lexicon.load -- happy path
# ---------------------------------------------------------------------------


def test_load_returns_lexicon(toml_file: Path) -> None:
    path = toml_file('word = ["alt1", "alt2"]\n')
    lex = Lexicon.load(path)
    assert isinstance(lex, Lexicon)
    assert lex.entries == {"word": ["alt1", "alt2"]}


def test_load_preserves_multiword_alternatives(toml_file: Path) -> None:
    path = toml_file('address = ["tackle", "handle", "deal with"]\n')
    lex = Lexicon.load(path)
    assert "deal with" in lex.entries["address"]


def test_load_preserves_hyphenated_alternative(toml_file: Path) -> None:
    path = toml_file('decisive = ["conclusive", "clear-cut", "deciding"]\n')
    lex = Lexicon.load(path)
    assert "clear-cut" in lex.entries["decisive"]


# ---------------------------------------------------------------------------
# Lexicon.load -- malformed TOML
# ---------------------------------------------------------------------------


def test_load_malformed_toml_raises_typed_error(toml_file: Path) -> None:
    path = toml_file("word = [unclosed\n")
    with pytest.raises(MalformedLexiconError):
        Lexicon.load(path)


def test_load_malformed_toml_not_bare_tomllib_error(toml_file: Path) -> None:
    import tomllib

    path = toml_file("word = [unclosed\n")
    with pytest.raises(MalformedLexiconError):
        Lexicon.load(path)
    # Confirm the raw tomllib error is NOT what surfaces
    with pytest.raises(MalformedLexiconError) as exc_info:
        Lexicon.load(path)
    assert not isinstance(exc_info.value, tomllib.TOMLDecodeError)


def test_load_malformed_toml_message_names_path(toml_file: Path) -> None:
    path = toml_file("word = [unclosed\n")
    with pytest.raises(MalformedLexiconError, match=str(path)):
        Lexicon.load(path)


# ---------------------------------------------------------------------------
# _validate -- invariant 1: duplicate base word
# (TOML forbids duplicate keys at parse time; tested via _validate directly)
# ---------------------------------------------------------------------------


def test_duplicate_base_word_raises() -> None:
    with pytest.raises(DuplicateBaseWordError, match="word"):
        _validate([("word", ["alt1"]), ("word", ["alt2"])])


# ---------------------------------------------------------------------------
# _validate -- invariant 2: alternative appears in more than one entry
# ---------------------------------------------------------------------------


def test_duplicate_alternative_raises() -> None:
    with pytest.raises(DuplicateAlternativeError, match="shared"):
        _validate(
            [
                ("word1", ["shared", "unique1"]),
                ("word2", ["shared", "unique2"]),
            ]
        )


# ---------------------------------------------------------------------------
# _validate -- invariant 3: word is both a base and an alternative
# (two reachable code paths)
# ---------------------------------------------------------------------------


def test_alternative_is_also_a_base_word_raises() -> None:
    """An alternative in one entry is the base word of an earlier entry."""
    with pytest.raises(BaseInAlternativesError, match="word1"):
        _validate(
            [
                ("word1", ["alt1", "alt2"]),
                ("word2", ["word1", "alt3"]),  # "word1" is a base
            ]
        )


def test_base_word_was_earlier_alternative_raises() -> None:
    """A base word was already listed as an alternative under an earlier entry."""
    with pytest.raises(BaseInAlternativesError, match="handle"):
        _validate(
            [
                ("word", ["alt1", "handle"]),  # "handle" used as alternative
                ("handle", ["grip", "hold"]),  # "handle" then used as base
            ]
        )


# ---------------------------------------------------------------------------
# _validate -- invariant 4: entry lists its own base among alternatives
# ---------------------------------------------------------------------------


def test_self_referential_alternative_raises() -> None:
    with pytest.raises(SelfReferentialAlternativeError, match="word"):
        _validate([("word", ["word", "other"])])


# ---------------------------------------------------------------------------
# _validate -- invariant 5: empty alternatives list
# ---------------------------------------------------------------------------


def test_empty_alternatives_list_raises() -> None:
    with pytest.raises(EmptyAlternativesError, match="word"):
        _validate([("word", [])])


# ---------------------------------------------------------------------------
# _validate -- structural: non-list value
# ---------------------------------------------------------------------------


def test_non_list_value_raises_malformed_error() -> None:
    with pytest.raises(MalformedLexiconError, match="word"):
        _validate([("word", "not-a-list")])


# ---------------------------------------------------------------------------
# Lexicon.default -- shipped data
# ---------------------------------------------------------------------------


def test_default_loads_shipped_lexicon() -> None:
    lex = Lexicon.default()
    assert isinstance(lex, Lexicon)
    assert len(lex.entries) == 86


def test_default_shipped_lexicon_has_526_alternatives() -> None:
    lex = Lexicon.default()
    total = sum(len(alts) for alts in lex.entries.values())
    assert total == 526


def test_default_preserves_multiword_alternatives() -> None:
    lex = Lexicon.default()
    assert "deal with" in lex.entries["address"]


# ---------------------------------------------------------------------------
# Lexicon.default -- malformed bundled TOML (monkeypatched)
# ---------------------------------------------------------------------------


def test_default_malformed_bundled_toml_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import tomllib

    import wordup.lexicon as lex_module

    def _raise_decode_error(f: object) -> object:
        raise tomllib.TOMLDecodeError(msg="bad TOML", doc="", pos=0)

    monkeypatch.setattr(lex_module.tomllib, "load", _raise_decode_error)
    with pytest.raises(MalformedLexiconError, match="Malformed bundled"):
        Lexicon.default()
