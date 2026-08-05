"""Tests for R13: explicit typed error handling in the CLI.

Every condition listed in the R13 acceptance criteria is triggered here,
including file-not-found, permission errors, directory-as-file, unicode
decode failure, unwritable output path, and malformed-lexicon errors.
Tests confirm the exit code, that a message naming the path appears on
stderr, and that no traceback text reaches the user.
"""

from __future__ import annotations

import sys

import pytest

from wordup.cli import main
from wordup.errors import MalformedLexiconError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Tty:
    """Minimal stdin replacement that reports itself as a tty."""

    def isatty(self) -> bool:
        return True


def _no_traceback(text: str) -> None:
    """Assert that *text* contains no Python traceback header."""
    assert "Traceback (most recent call last)" not in text


# ---------------------------------------------------------------------------
# FileNotFoundError on -f
# ---------------------------------------------------------------------------


def test_file_not_found(tmp_path, capsys, monkeypatch) -> None:
    """A missing input file produces a message naming the path and exits 1."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    missing = tmp_path / "ghost.txt"
    code = main(["-f", str(missing)])
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ghost.txt" in captured.err
    assert "file not found" in captured.err
    _no_traceback(captured.err)


# ---------------------------------------------------------------------------
# IsADirectoryError on -f
# ---------------------------------------------------------------------------


def test_directory_as_file(tmp_path, capsys, monkeypatch) -> None:
    """Passing a directory as -f produces a message naming the path and exits 1."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    code = main(["-f", str(tmp_path)])
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(tmp_path) in captured.err
    assert "directory" in captured.err
    _no_traceback(captured.err)


# ---------------------------------------------------------------------------
# PermissionError on -f (read)
# ---------------------------------------------------------------------------


def test_permission_denied_read(tmp_path, capsys, monkeypatch) -> None:
    """An unreadable input file produces a message naming the path and exits 1."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    doc = tmp_path / "secret.txt"
    doc.write_text("hello")
    doc.chmod(0o000)
    try:
        code = main(["-f", str(doc)])
    finally:
        doc.chmod(0o644)
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "secret.txt" in captured.err
    assert "permission denied" in captured.err
    _no_traceback(captured.err)


# ---------------------------------------------------------------------------
# UnicodeDecodeError on -f
# ---------------------------------------------------------------------------


def test_unicode_decode_error(tmp_path, capsys, monkeypatch) -> None:
    """A file with invalid UTF-8 produces a message naming the path and encoding."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    doc = tmp_path / "mojibake.txt"
    doc.write_bytes(b"caf\xe9")  # invalid UTF-8 continuation byte
    code = main(["-f", str(doc)])
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "mojibake.txt" in captured.err
    # Message must name both the path and the encoding problem.
    assert "utf-8" in captured.err.lower() or "decode" in captured.err.lower()
    _no_traceback(captured.err)


# ---------------------------------------------------------------------------
# PermissionError on -o (write)
# ---------------------------------------------------------------------------


def test_permission_denied_output(tmp_path, capsys, monkeypatch) -> None:
    """-o pointing at an unwritable path produces a message naming the path."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    # Make the directory unwritable so the output file cannot be created.
    out_dir = tmp_path / "readonly"
    out_dir.mkdir()
    out_dir.chmod(0o500)
    out_file = out_dir / "out.txt"
    try:
        code = main(["The quick brown fox.", "-o", str(out_file)])
    finally:
        out_dir.chmod(0o700)
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "out.txt" in captured.err
    assert "permission denied" in captured.err
    _no_traceback(captured.err)


# ---------------------------------------------------------------------------
# PermissionError on --in-place (write)
# ---------------------------------------------------------------------------


def test_permission_denied_in_place(tmp_path, capsys, monkeypatch) -> None:
    """--in-place on an unwritable file produces a message naming the path."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    doc = tmp_path / "locked.txt"
    doc.write_text("The quick brown fox.")
    doc.chmod(0o444)
    try:
        code = main(["-f", str(doc), "--in-place"])
    finally:
        doc.chmod(0o644)
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "locked.txt" in captured.err
    assert "permission denied" in captured.err
    _no_traceback(captured.err)


# ---------------------------------------------------------------------------
# WordupError: malformed lexicon TOML
# ---------------------------------------------------------------------------


def test_malformed_lexicon_produces_no_traceback(capsys, monkeypatch) -> None:
    """A MalformedLexiconError from run_session exits 1 with no traceback."""
    monkeypatch.setattr(sys, "stdin", _Tty())

    def _raise(_text: str, **_kwargs: object) -> tuple[str, int]:
        raise MalformedLexiconError("Malformed TOML in lexicon: bad key 'access'")

    monkeypatch.setattr("wordup.cli.run_session", _raise)
    code = main(["hello world"])
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Malformed" in captured.err
    assert "access" in captured.err
    _no_traceback(captured.err)


# ---------------------------------------------------------------------------
# WordupError: lexicon validation failure naming the offending word
# ---------------------------------------------------------------------------


def test_lexicon_validation_error_names_word(capsys, monkeypatch) -> None:
    """A lexicon validation WordupError surfaces with the offending word."""
    from wordup.errors import DuplicateBaseWordError

    monkeypatch.setattr(sys, "stdin", _Tty())

    def _raise(_text: str, **_kwargs: object) -> tuple[str, int]:
        raise DuplicateBaseWordError("Duplicate base word: 'use'")

    monkeypatch.setattr("wordup.cli.run_session", _raise)
    code = main(["hello world"])
    assert code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "'use'" in captured.err
    _no_traceback(captured.err)


# ---------------------------------------------------------------------------
# No bare except: confirm ruff gate passes (structural, not runtime)
# ---------------------------------------------------------------------------


def test_no_bare_except_in_cli(tmp_path) -> None:
    """cli.py must not contain any bare except clause."""
    import ast
    from pathlib import Path

    src = Path(__file__).parent.parent / "src" / "wordup" / "cli.py"
    tree = ast.parse(src.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            assert node.type is not None, (
                f"Bare except found at line {node.lineno} in cli.py"
            )
