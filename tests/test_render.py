"""Tests for wordup.render."""

from __future__ import annotations

import pytest

from wordup.render import color_enabled, render_prompt


# ---------------------------------------------------------------------------
# color_enabled
# ---------------------------------------------------------------------------


def test_color_enabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Color is on when NO_COLOR is absent."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert color_enabled() is True


def test_color_disabled_when_no_color_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """NO_COLOR set to empty string disables color."""
    monkeypatch.setenv("NO_COLOR", "")
    assert color_enabled() is False


def test_color_disabled_when_no_color_nonempty(monkeypatch: pytest.MonkeyPatch) -> None:
    """NO_COLOR set to any non-empty value disables color."""
    monkeypatch.setenv("NO_COLOR", "1")
    assert color_enabled() is False


# ---------------------------------------------------------------------------
# render_prompt - color path
# ---------------------------------------------------------------------------


def test_ansi_present_when_color_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """ANSI escape bytes appear in the output when color is enabled."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    out = render_prompt("Use simpler words.", (4, 11), ["plain", "basic"])
    assert "\x1b" in out


def test_match_wrapped_with_bold(monkeypatch: pytest.MonkeyPatch) -> None:
    """The matched word is wrapped between bold-on and reset sequences."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    out = render_prompt("Use simpler words.", (4, 11), [])
    assert "\x1b[1msimpler\x1b[0m" in out


# ---------------------------------------------------------------------------
# render_prompt - no-color path
# ---------------------------------------------------------------------------


def test_no_ansi_when_no_color_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """No \\x1b byte appears in the output when NO_COLOR is set."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use simpler words.", (4, 11), ["plain"])
    assert "\x1b" not in out


def test_caret_present_without_color(monkeypatch: pytest.MonkeyPatch) -> None:
    """The caret underline is present in the no-color path."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use simpler words.", (4, 11), [])
    assert "^" in out


def test_caret_present_with_color(monkeypatch: pytest.MonkeyPatch) -> None:
    """The caret underline is present in the color path."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    out = render_prompt("Use simpler words.", (4, 11), [])
    assert "^" in out


# ---------------------------------------------------------------------------
# Caret alignment
# ---------------------------------------------------------------------------


def test_caret_aligns_with_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """The caret appears directly below the matched word."""
    monkeypatch.setenv("NO_COLOR", "1")
    sentence = "Use simpler words."
    # "simpler" is at positions 4..11
    out = render_prompt(sentence, (4, 11), [])
    lines = out.splitlines()
    sentence_line = lines[0]
    caret_line = lines[1]
    # Find the start of "simpler" in the sentence line (no ANSI, plain text)
    word_start = sentence_line.index("simpler")
    assert caret_line[word_start] == "^"
    assert caret_line[word_start + 6] == "^"
    # Positions before the word are spaces
    assert caret_line[:word_start] == " " * word_start


def test_caret_aligns_at_sentence_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """A match at position 0 produces a caret with no leading spaces."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Access the data.", (0, 6), [])
    lines = out.splitlines()
    caret_line = lines[1]
    assert caret_line.startswith("^^^^^^")
    assert caret_line[0] != " "


def test_caret_aligns_when_window_clipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Caret position is computed from match_span, independent of what precedes it.

    This simulates the sentence window being clipped: the sentence passed to
    render_prompt starts mid-document, and match_span is already adjusted to
    be relative to the sentence start.
    """
    monkeypatch.setenv("NO_COLOR", "1")
    # Pretend the sentence is clipped to start at position 10 in the document.
    # The match was at doc positions 15..21 ("simpler"), so relative to the
    # clipped sentence it is at positions 5..11.
    sentence = "use simpler words."
    out = render_prompt(sentence, (4, 11), [])
    lines = out.splitlines()
    caret_line = lines[1]
    assert caret_line == "    ^^^^^^^"


# ---------------------------------------------------------------------------
# Option list
# ---------------------------------------------------------------------------


def test_option_zero_is_no_change(monkeypatch: pytest.MonkeyPatch) -> None:
    """Option 0 is always labeled NO CHANGE."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use simpler words.", (4, 11), ["plain"])
    assert "0) NO CHANGE" in out


def test_alternatives_as_options(monkeypatch: pytest.MonkeyPatch) -> None:
    """Alternatives appear as options 1..n in the given order."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use simpler words.", (4, 11), ["plain", "basic", "easy"])
    assert "1) plain" in out
    assert "2) basic" in out
    assert "3) easy" in out


def test_no_alternatives_only_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no alternatives, only option 0 appears."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use simpler words.", (4, 11), [])
    assert "0) NO CHANGE" in out
    assert "1)" not in out


def test_default_none_no_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    """When default is None, no [default] annotation appears."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use simpler words.", (4, 11), ["plain"], default=None)
    assert "[default]" not in out


def test_default_zero_marked(monkeypatch: pytest.MonkeyPatch) -> None:
    """default=0 marks the NO CHANGE option with [default]."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use simpler words.", (4, 11), ["plain"], default=0)
    assert "0) NO CHANGE [default]" in out
    assert "1) plain" in out
    assert "[default]" not in out.split("0) NO CHANGE [default]")[1]


def test_default_alternative_marked(monkeypatch: pytest.MonkeyPatch) -> None:
    """default=2 marks alternative index 2 and leaves others unmarked."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt(
        "Use simpler words.", (4, 11), ["plain", "basic", "easy"], default=2
    )
    assert "2) basic [default]" in out
    assert "1) plain\n" in out or "1) plain" in out.split("2) basic")[0]
    assert "3) easy" in out
    # Only one [default] annotation total
    assert out.count("[default]") == 1


# ---------------------------------------------------------------------------
# Purity: render_prompt returns a string and does not write to a stream
# ---------------------------------------------------------------------------


def test_render_is_pure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """render_prompt does not write to stdout or stderr."""
    monkeypatch.setenv("NO_COLOR", "1")
    result = render_prompt("Use simpler words.", (4, 11), ["plain"])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert isinstance(result, str)


def test_result_ends_with_newline(monkeypatch: pytest.MonkeyPatch) -> None:
    """The returned string always ends with a newline."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use simpler words.", (4, 11), ["plain"])
    assert out.endswith("\n")


# ---------------------------------------------------------------------------
# Trailing newline in sentence is stripped
# ---------------------------------------------------------------------------


def test_trailing_newline_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    """A trailing newline in the sentence is stripped before display."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use simpler words.\n", (4, 11), [])
    lines = out.splitlines()
    assert lines[0] == "Use simpler words."


# ---------------------------------------------------------------------------
# Minimum caret width of 1 for zero-length match spans
# ---------------------------------------------------------------------------


def test_empty_match_span_caret_width_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """A zero-length match span still renders a single caret character."""
    monkeypatch.setenv("NO_COLOR", "1")
    out = render_prompt("Use words.", (3, 3), [])
    lines = out.splitlines()
    caret_line = lines[1]
    assert caret_line == "   ^"
