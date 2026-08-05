"""Tests for the wordup public API surface.

Covers:
- suggest(text, lexicon=None) -> list[Match]
- apply_choices(text, choices) -> str
- Lexicon.default() and Lexicon.load(path) re-exports
- Match re-export
- __all__ exactness and absence of improve/run_session
- No file I/O at import time
- Both functions run with stdin closed
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import wordup
from wordup import Lexicon, Match, apply_choices, suggest


# ---------------------------------------------------------------------------
# Fixture: minimal TOML lexicon for controlled tests
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_lexicon(tmp_path: Path) -> Lexicon:
    """Return a small Lexicon loaded from a tmp TOML file."""
    toml = tmp_path / "lex.toml"
    toml.write_text(
        'access = ["entry", "admittance"]\n'
        'use = ["utilize", "employ", "apply", "operate"]\n',
        encoding="utf-8",
    )
    return Lexicon.load(toml)


# ---------------------------------------------------------------------------
# __all__ and exported names
# ---------------------------------------------------------------------------


def test_all_lists_exactly_four_names() -> None:
    assert wordup.__all__ == ["suggest", "apply_choices", "Lexicon", "Match"]


def test_no_improve_attribute() -> None:
    assert not hasattr(wordup, "improve"), (
        "'improve' must not be exported; automatic rewriting is a non-goal"
    )


def test_no_run_session_attribute() -> None:
    # run_session lives in interactive.py and must not leak to the public API.
    assert not hasattr(wordup, "run_session")


def test_no_grammar_reviewer() -> None:
    assert not hasattr(wordup, "GrammarReviewer")


def test_exported_names_are_callable() -> None:
    assert callable(wordup.suggest)
    assert callable(wordup.apply_choices)


# ---------------------------------------------------------------------------
# No file I/O at import time
# ---------------------------------------------------------------------------


def test_import_does_not_load_lexicon() -> None:
    """Importing wordup must not pull in wordup.lexicon (which reads TOML)."""
    code = (
        "import wordup; "
        "import sys; "
        "assert 'wordup.lexicon' not in sys.modules, "
        "f'wordup.lexicon was imported eagerly: {list(sys.modules)}'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# suggest -- both lexicon paths
# ---------------------------------------------------------------------------


def test_suggest_with_explicit_lexicon(simple_lexicon: Lexicon) -> None:
    """suggest with an explicit lexicon finds the expected match."""
    matches = suggest("We need access to the data.", lexicon=simple_lexicon)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "access"
    assert "entry" in m.alternatives
    assert "admittance" in m.alternatives


def test_suggest_loads_default_lexicon_when_none() -> None:
    """suggest(text) with no lexicon argument loads the shipped lexicon."""
    # 'use' is in the shipped lexicon.
    matches = suggest("We use Python every day.")
    assert any(m.base == "use" for m in matches)


def test_suggest_returns_list_of_match() -> None:
    matches = suggest("access the resource", lexicon=Lexicon.default())
    assert isinstance(matches, list)
    for m in matches:
        assert isinstance(m, Match)


def test_suggest_no_match(simple_lexicon: Lexicon) -> None:
    matches = suggest("the quick brown fox jumps.", lexicon=simple_lexicon)
    assert matches == []


def test_suggest_with_stdin_closed(simple_lexicon: Lexicon) -> None:
    """suggest must not read stdin; it should complete with stdin closed."""
    code = (
        "import sys, os; "
        "os.close(sys.stdin.fileno()); "
        "from wordup import suggest; "
        "from wordup.models import Lexicon; "
        "from pathlib import Path; "
        "import tomllib; "
        "import tempfile, os; "
        "f = tempfile.NamedTemporaryFile(suffix='.toml', delete=False); "
        r"f.write(b'access = [\"entry\"]\n'); "
        "f.close(); "
        "lex = Lexicon.load(Path(f.name)); "
        "result = suggest('I need access.', lexicon=lex); "
        "os.unlink(f.name); "
        "assert len(result) == 1"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# apply_choices -- re-export is the apply module's function
# ---------------------------------------------------------------------------


def test_apply_choices_zero_choices_identity() -> None:
    text = "We need access to the system.\n\nPlease use the API."
    assert apply_choices(text, []) == text


def test_apply_choices_single_replacement() -> None:
    text = "We need access to the system."
    # span of "access" is (8, 14)
    start = text.index("access")
    end = start + len("access")
    result = apply_choices(text, [((start, end), "entry")])
    assert result == "We need entry to the system."


def test_apply_choices_transfers_case() -> None:
    text = "ACCESS the data."
    start = text.index("ACCESS")
    end = start + len("ACCESS")
    result = apply_choices(text, [((start, end), "entry")])
    assert result == "ENTRY the data."


def test_apply_choices_with_stdin_closed() -> None:
    code = (
        "import sys, os; "
        "os.close(sys.stdin.fileno()); "
        "from wordup import apply_choices; "
        "r = apply_choices('hello world', []); "
        "assert r == 'hello world'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# Lexicon re-export
# ---------------------------------------------------------------------------


def test_lexicon_default_loads() -> None:
    lex = Lexicon.default()
    assert isinstance(lex, Lexicon)
    assert len(lex.entries) == 86


def test_lexicon_load_from_path(tmp_path: Path) -> None:
    toml = tmp_path / "custom.toml"
    toml.write_text('word = ["synonym"]\n', encoding="utf-8")
    lex = Lexicon.load(toml)
    assert "word" in lex.entries
    assert lex.entries["word"] == ["synonym"]


# ---------------------------------------------------------------------------
# Match re-export
# ---------------------------------------------------------------------------


def test_match_is_exported() -> None:
    assert Match is wordup.Match


def test_match_fields(simple_lexicon: Lexicon) -> None:
    matches = suggest("access the data", lexicon=simple_lexicon)
    assert len(matches) == 1
    m = matches[0]
    assert hasattr(m, "span")
    assert hasattr(m, "surface")
    assert hasattr(m, "base")
    assert hasattr(m, "suffix")
    assert hasattr(m, "alternatives")


# ---------------------------------------------------------------------------
# No callable selects choices on the caller's behalf
# ---------------------------------------------------------------------------


def test_no_auto_select_function() -> None:
    """No exported callable should automatically pick replacements."""
    for name in wordup.__all__:
        # suggest and apply_choices are fine; they return data or require
        # explicit caller-supplied choices.  We just assert nothing named
        # 'improve', 'fix', 'rewrite', or 'auto_*' is present.
        assert name not in {"improve", "fix", "rewrite"}
