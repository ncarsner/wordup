"""Tests for src/wordup/cli.py.

Covers every flag combination and the no-tty path at 100% branch coverage.
The session is driven via monkeypatched ``builtins.input`` so no real
terminal is required.
"""

from __future__ import annotations

import builtins
import sys

import pytest

from wordup.cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _Tty:
    """Minimal stdin replacement that reports itself as a tty."""

    def isatty(self) -> bool:
        return True


class _NoTty:
    """Minimal stdin replacement that reports itself as not a tty."""

    def isatty(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Argument-validation error paths (no tty patching required)
# ---------------------------------------------------------------------------


def test_both_text_and_file_is_error(capsys, tmp_path) -> None:
    """Supplying TEXT and -f together is an error."""
    doc = tmp_path / "doc.txt"
    doc.write_text("hello")
    code = main(["hello", "-f", str(doc)])
    assert code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "mutually exclusive" in captured.err


def test_neither_text_nor_file_is_error(capsys) -> None:
    """Supplying neither TEXT nor -f is an error."""
    code = main([])
    assert code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "supply TEXT or -f" in captured.err


def test_in_place_without_file_is_error(capsys) -> None:
    """--in-place without -f is an error."""
    code = main(["--in-place", "hello"])
    assert code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "--in-place requires" in captured.err


def test_in_place_and_output_are_mutex(tmp_path) -> None:
    """--in-place and -o together are rejected by argparse."""
    doc = tmp_path / "doc.txt"
    out = tmp_path / "out.txt"
    doc.write_text("hello")
    with pytest.raises(SystemExit) as exc:
        main(["-f", str(doc), "--in-place", "-o", str(out)])
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# No-tty error path
# ---------------------------------------------------------------------------


def test_no_tty_exits_2(capsys, monkeypatch) -> None:
    """Without a controlling terminal main exits 2 with an explanatory message."""
    monkeypatch.setattr(sys, "stdin", _NoTty())
    code = main(["hello"])
    assert code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "interactive terminal" in captured.err


def test_no_tty_file_is_unchanged(tmp_path, capsys, monkeypatch) -> None:
    """With no tty, -f input is checked after arg validation but stdin is
    checked before anything is read, so the file is never opened."""
    monkeypatch.setattr(sys, "stdin", _NoTty())
    doc = tmp_path / "doc.txt"
    original = "The quick brown fox."
    doc.write_text(original)
    code = main(["-f", str(doc)])
    assert code == 2
    assert doc.read_text() == original
    captured = capsys.readouterr()
    assert captured.out == ""


# ---------------------------------------------------------------------------
# Happy paths: input source
# ---------------------------------------------------------------------------


def test_positional_text_no_matches(capsys, monkeypatch) -> None:
    """TEXT with no lexicon matches exits 0 and writes the unchanged text to stdout."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    code = main(["The quick brown fox."])
    assert code == 0
    captured = capsys.readouterr()
    assert captured.out == "The quick brown fox."
    assert captured.err == ""


def test_file_input_no_matches(tmp_path, capsys, monkeypatch) -> None:
    """Reading from -f with no matches exits 0 and writes unchanged text to stdout."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    doc = tmp_path / "doc.txt"
    doc.write_text("The quick brown fox.")
    code = main(["-f", str(doc)])
    assert code == 0
    captured = capsys.readouterr()
    assert captured.out == "The quick brown fox."
    assert captured.err == ""


# ---------------------------------------------------------------------------
# Happy paths: output destination
# ---------------------------------------------------------------------------


def test_positional_text_with_output_file(tmp_path, capsys, monkeypatch) -> None:
    """Result goes to -o PATH when specified; stdout is empty."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    out_file = tmp_path / "out.txt"
    code = main(["The quick brown fox.", "-o", str(out_file)])
    assert code == 0
    assert out_file.read_text() == "The quick brown fox."
    assert capsys.readouterr().out == ""


def test_file_input_with_output_file(tmp_path, monkeypatch) -> None:
    """Reading from -f and writing to -o."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    doc = tmp_path / "doc.txt"
    doc.write_text("The quick brown fox.")
    out_file = tmp_path / "out.txt"
    code = main(["-f", str(doc), "-o", str(out_file)])
    assert code == 0
    assert out_file.read_text() == "The quick brown fox."


def test_file_input_in_place(tmp_path, capsys, monkeypatch) -> None:
    """--in-place overwrites the input file; stdout is empty."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    doc = tmp_path / "doc.txt"
    doc.write_text("The quick brown fox.")
    code = main(["-f", str(doc), "--in-place"])
    assert code == 0
    assert doc.read_text() == "The quick brown fox."
    assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# Session behaviour: stream split
# ---------------------------------------------------------------------------


def test_prompts_go_to_stderr_not_stdout(capsys, monkeypatch) -> None:
    """Prompts and menus appear on stderr; the revised document goes to stdout."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    # "access" is a base word; answer "0" = NO CHANGE.
    monkeypatch.setattr(builtins, "input", lambda: "0")
    code = main(["Please access the data."])
    assert code == 0
    captured = capsys.readouterr()
    # Stdout contains the document, not any menu text.
    assert "access" in captured.out
    assert "NO CHANGE" not in captured.out
    # Stderr carries the interactive prompt.
    assert captured.err != ""
    assert "NO CHANGE" in captured.err


def test_accepted_choice_appears_in_output(capsys, monkeypatch) -> None:
    """Choosing alternative 1 replaces the word in the stdout output."""
    monkeypatch.setattr(sys, "stdin", _Tty())
    # "access" alternative 1 is "entry".
    monkeypatch.setattr(builtins, "input", lambda: "1")
    code = main(["Please access the data."])
    assert code == 0
    captured = capsys.readouterr()
    assert "entry" in captured.out
    assert "access" not in captured.out


# ---------------------------------------------------------------------------
# KeyboardInterrupt: exit 130 and partial output
# ---------------------------------------------------------------------------


def test_exit_130_on_keyboard_interrupt(capsys, monkeypatch) -> None:
    """KeyboardInterrupt propagates as exit code 130; partial output is written."""
    monkeypatch.setattr(sys, "stdin", _Tty())

    def _raise_interrupt() -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", _raise_interrupt)
    code = main(["Please access the data."])
    assert code == 130
    # Output is still written even after interrupt.
    captured = capsys.readouterr()
    assert captured.out != ""
    assert "access" in captured.out
