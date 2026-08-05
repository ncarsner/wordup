"""Tests for wordup.interactive.

Every acceptance criterion for the interactive-session task is covered here.
A scripted ``read_fn`` drives the session so no real terminal is required.
"""

from __future__ import annotations

import io
from typing import Any

import pytest

from wordup.interactive import _read_line, run_session
from wordup.models import Lexicon

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# Minimal lexicon: two base words, two alternatives each.
LEXICON = Lexicon(
    entries={
        "use": ["employ", "apply"],
        "help": ["assist", "support"],
        "create": ["generate", "produce"],
        "address": ["tackle", "deal with"],
    }
)

# Single-sentence texts to keep sentence_span results predictable.
TEXT_ONE = "Please use it."  # one match: "use"
TEXT_TWO = "Please use and help."  # two matches: "use", "help"


def make_reader(*responses: str | BaseException) -> Any:
    """Return a scripted ``read_fn`` that yields each response in turn.

    A ``BaseException`` instance in *responses* is raised instead of returned.
    """
    it = iter(responses)

    def read() -> str:
        val = next(it)
        if isinstance(val, BaseException):
            raise val
        return str(val)

    return read


# ---------------------------------------------------------------------------
# _read_line unit test
# ---------------------------------------------------------------------------


def test_read_line_delegates_to_builtin_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """_read_line returns whatever builtins.input returns."""
    monkeypatch.setattr("builtins.input", lambda: "hello")
    assert _read_line() == "hello"


# ---------------------------------------------------------------------------
# Default parameter tests
# ---------------------------------------------------------------------------


def test_default_err_writes_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    """When err=None, prompts go to sys.stderr; stdout is untouched."""
    run_session(TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("0"))
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "use" in captured.err


def test_default_lexicon_when_none_uses_shipped_data() -> None:
    """When lexicon=None, the shipped lexicon is loaded and scan runs."""
    # "access" is a base word in the shipped lexicon.
    result, code = run_session(
        "Please access it.",
        read_fn=make_reader("0"),
        err=io.StringIO(),
    )
    assert code == 0
    assert result == "Please access it."


# ---------------------------------------------------------------------------
# No-match cases
# ---------------------------------------------------------------------------


def test_no_matches_returns_identical_text() -> None:
    """Text with no lexicon hits is returned byte-identical."""
    result, code = run_session("Hello world.", lexicon=LEXICON, err=io.StringIO())
    assert result == "Hello world."
    assert code == 0


# ---------------------------------------------------------------------------
# Single-match prompting
# ---------------------------------------------------------------------------


def test_option_1_replaces_word() -> None:
    """Choosing option 1 replaces the matched word with the first alternative."""
    result, code = run_session(
        TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("1"), err=io.StringIO()
    )
    assert result == "Please employ it."
    assert code == 0


def test_option_2_replaces_word_with_second_alternative() -> None:
    """Choosing option 2 replaces the matched word with the second alternative."""
    result, code = run_session(
        TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("2"), err=io.StringIO()
    )
    assert result == "Please apply it."
    assert code == 0


def test_option_0_no_change_leaves_text_identical() -> None:
    """Choosing option 0 (NO CHANGE) leaves the text identical to the input."""
    result, code = run_session(
        TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("0"), err=io.StringIO()
    )
    assert result == TEXT_ONE
    assert code == 0


# ---------------------------------------------------------------------------
# Two-match session
# ---------------------------------------------------------------------------


def test_two_matches_both_replaced() -> None:
    """Each match is prompted; both replacements are applied."""
    result, code = run_session(
        TEXT_TWO, lexicon=LEXICON, read_fn=make_reader("1", "1"), err=io.StringIO()
    )
    assert "employ" in result
    assert "assist" in result
    assert code == 0


def test_two_matches_one_replaced_one_skipped() -> None:
    """A NO CHANGE on the second match applies only the first replacement."""
    result, code = run_session(
        TEXT_TWO, lexicon=LEXICON, read_fn=make_reader("1", "0"), err=io.StringIO()
    )
    assert "employ" in result
    assert "help" in result
    assert code == 0


# ---------------------------------------------------------------------------
# Remembered default behavior
# ---------------------------------------------------------------------------


def test_remembered_default_shown_at_second_occurrence() -> None:
    """A chosen alternative becomes the default on the next occurrence."""
    # "use" appears twice; user picks employ on first, presses Enter on second.
    text = "I use it. I use it."
    err = io.StringIO()
    result, code = run_session(
        text, lexicon=LEXICON, read_fn=make_reader("1", ""), err=err
    )
    # "[default]" must appear in the second prompt.
    assert "[default]" in err.getvalue()
    # Both occurrences should be replaced with "employ".
    assert result == "I employ it. I employ it."
    assert code == 0


def test_enter_accepts_remembered_default() -> None:
    """Pressing Enter when a default is set accepts that default."""
    text = "I use it. I use it."
    result, _ = run_session(
        text, lexicon=LEXICON, read_fn=make_reader("1", ""), err=io.StringIO()
    )
    assert result == "I employ it. I employ it."


def test_enter_without_default_is_no_change() -> None:
    """Pressing Enter with no remembered default is treated as NO CHANGE."""
    result, code = run_session(
        TEXT_ONE, lexicon=LEXICON, read_fn=make_reader(""), err=io.StringIO()
    )
    assert result == TEXT_ONE
    assert code == 0


# ---------------------------------------------------------------------------
# NO CHANGE does not update remembered state
# ---------------------------------------------------------------------------


def test_no_change_does_not_set_remembered_default() -> None:
    """Refusing at the first occurrence leaves no default at the second."""
    text = "I use it. I use it."
    err = io.StringIO()
    run_session(text, lexicon=LEXICON, read_fn=make_reader("0", "0"), err=err)
    assert "[default]" not in err.getvalue()


def test_no_change_does_not_clear_existing_remembered_default() -> None:
    """Choosing NO CHANGE after accepting an alternative preserves the default.

    Sequence: accept (employ) -> NO CHANGE -> third occurrence shows employ
    as the default and the user presses Enter to confirm.
    """
    # Three occurrences of "use".
    text = "I use it. I use it. I use it."
    err = io.StringIO()
    result, code = run_session(
        text, lexicon=LEXICON, read_fn=make_reader("1", "0", ""), err=err
    )
    # First occurrence: replaced with "employ".
    # Second occurrence: NO CHANGE (text stays "use").
    # Third occurrence: Enter -> remembered default "employ" accepted.
    assert result == "I employ it. I use it. I employ it."
    assert code == 0
    # "[default]" must appear: at the third prompt (default from first choice).
    assert "[default]" in err.getvalue()


# ---------------------------------------------------------------------------
# Remembered default across different surface forms (inflection-aware)
# ---------------------------------------------------------------------------


def test_remembered_raw_alt_reinflected_for_different_suffix() -> None:
    """The remembered raw alternative is re-inflected for a later inflected surface.

    e.g. user accepts "generate" for "create"; later "Creating" shows
    "generating" as the default.
    """
    lex = Lexicon(entries={"create": ["generate", "produce"]})
    # "create" (exact) then "Creating" (-ing form, capitalized).
    text = "We create. Creating is different."
    err = io.StringIO()
    result, code = run_session(text, lexicon=lex, read_fn=make_reader("1", ""), err=err)
    # First: "create" -> "generate".
    # Second: "Creating" -> Enter -> "Generating" (re-inflected, title-cased).
    assert result == "We generate. Generating is different."
    assert "[default]" in err.getvalue()
    assert code == 0


def test_multiword_remembered_alt_no_default_on_inflected_surface() -> None:
    """A remembered multi-word alternative produces no default for an inflected form."""
    # "address" has "deal with" as an alternative.
    lex = Lexicon(entries={"address": ["tackle", "deal with"]})
    # User accepts "deal with" for "address" (exact match).
    # "addresses" has "-s" suffix; reinflect("deal with", "-s") = None -> no default.
    text = "They address it. She addresses it."
    err = io.StringIO()
    result, code = run_session(
        text, lexicon=lex, read_fn=make_reader("2", "0"), err=err
    )
    # "[default]" should not appear in the second prompt.
    assert "[default]" not in err.getvalue()
    assert code == 0


# ---------------------------------------------------------------------------
# Invalid input handling
# ---------------------------------------------------------------------------


def test_invalid_alpha_input_reprompts() -> None:
    """Non-numeric input shows an error and reprompts; does not record a choice."""
    err = io.StringIO()
    result, code = run_session(
        TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("x", "0"), err=err
    )
    assert "Invalid" in err.getvalue()
    assert result == TEXT_ONE  # no choice was recorded
    assert code == 0


def test_out_of_range_number_reprompts() -> None:
    """A number outside 0..n shows an error and reprompts."""
    err = io.StringIO()
    result, code = run_session(
        TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("99", "0"), err=err
    )
    assert "Invalid" in err.getvalue()
    assert result == TEXT_ONE
    assert code == 0


def test_multiple_invalid_inputs_before_valid() -> None:
    """Multiple invalid inputs each produce an error; the final valid input applies."""
    err = io.StringIO()
    result, code = run_session(
        TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("abc", "99", "1"), err=err
    )
    assert err.getvalue().count("Invalid") == 2
    assert "employ" in result
    assert code == 0


def test_invalid_input_never_treated_as_no_change() -> None:
    """Invalid input does not advance or record a decision; it only reprompts."""
    err = io.StringIO()
    # After the invalid input we pick alternative 1, not 0.
    result, code = run_session(
        TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("!", "1"), err=err
    )
    assert "employ" in result  # the replacement WAS applied (not silently skipped)


# ---------------------------------------------------------------------------
# KeyboardInterrupt handling
# ---------------------------------------------------------------------------


def test_keyboard_interrupt_returns_exit_code_130() -> None:
    """KeyboardInterrupt exits with code 130."""
    _, code = run_session(
        TEXT_ONE,
        lexicon=LEXICON,
        read_fn=make_reader(KeyboardInterrupt()),
        err=io.StringIO(),
    )
    assert code == 130


def test_keyboard_interrupt_applies_choices_made_so_far() -> None:
    """Choices accepted before the interrupt are applied; the rest is untouched."""
    text = "Please use and help."
    result, code = run_session(
        text,
        lexicon=LEXICON,
        read_fn=make_reader("1", KeyboardInterrupt()),
        err=io.StringIO(),
    )
    assert code == 130
    assert "employ" in result  # first choice was applied
    assert "help" in result  # second was not reached


def test_keyboard_interrupt_no_choices_returns_original_text() -> None:
    """Interrupting before any choice leaves the text unchanged."""
    result, code = run_session(
        TEXT_ONE,
        lexicon=LEXICON,
        read_fn=make_reader(KeyboardInterrupt()),
        err=io.StringIO(),
    )
    assert result == TEXT_ONE
    assert code == 130


# ---------------------------------------------------------------------------
# Prompts go to stderr, not stdout
# ---------------------------------------------------------------------------


def test_prompts_go_to_err_stream_not_stdout() -> None:
    """The err stream receives prompts; nothing is written to stdout."""
    err = io.StringIO()
    run_session(TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("0"), err=err)
    assert "use" in err.getvalue()


def test_run_session_does_not_write_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """run_session never writes to sys.stdout."""
    run_session(TEXT_ONE, lexicon=LEXICON, read_fn=make_reader("0"), err=io.StringIO())
    captured = capsys.readouterr()
    assert captured.out == ""


# ---------------------------------------------------------------------------
# Case transfer (integration)
# ---------------------------------------------------------------------------


def test_uppercase_surface_transfers_to_replacement() -> None:
    """All-uppercase surface form transfers to the replacement."""
    result, _ = run_session(
        "Please USE it.", lexicon=LEXICON, read_fn=make_reader("1"), err=io.StringIO()
    )
    assert "EMPLOY" in result


def test_title_case_surface_transfers_to_replacement() -> None:
    """Title-case surface form transfers to the replacement."""
    result, _ = run_session(
        "Use it please.", lexicon=LEXICON, read_fn=make_reader("1"), err=io.StringIO()
    )
    assert "Employ" in result
