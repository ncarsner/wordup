"""Tests for wordup.apply -- span-slicing replacement with case transfer."""

from __future__ import annotations

import pytest

from wordup.apply import Choice, apply_choices, transfer_case


# ---------------------------------------------------------------------------
# transfer_case
# ---------------------------------------------------------------------------


class TestTransferCase:
    def test_lowercase_surface(self) -> None:
        assert transfer_case("access", "entry") == "entry"

    def test_title_case_surface(self) -> None:
        # "Access" is title-ish: first char upper, rest lower.
        assert transfer_case("Access", "entry") == "Entry"

    def test_uppercase_surface(self) -> None:
        assert transfer_case("ACCESS", "entry") == "ENTRY"

    def test_single_uppercase_char(self) -> None:
        # A single uppercase letter satisfies isupper() and is treated as UPPER.
        assert transfer_case("A", "entry") == "ENTRY"

    def test_single_lowercase_char(self) -> None:
        assert transfer_case("a", "entry") == "entry"

    def test_mixed_case_passthrough(self) -> None:
        # Mixed case is returned unchanged.
        assert transfer_case("aCCess", "entry") == "entry"

    def test_title_multiword_replacement(self) -> None:
        # Only the first character is uppercased; internal words are not touched.
        assert transfer_case("Address", "deal with") == "Deal with"

    def test_uppercase_multiword_replacement(self) -> None:
        assert transfer_case("ADDRESS", "deal with") == "DEAL WITH"

    def test_lowercase_multiword_replacement(self) -> None:
        assert transfer_case("address", "deal with") == "deal with"

    def test_hyphenated_replacement_title(self) -> None:
        assert transfer_case("Attempt", "clear-cut") == "Clear-cut"

    def test_hyphenated_replacement_upper(self) -> None:
        assert transfer_case("ATTEMPT", "clear-cut") == "CLEAR-CUT"


# ---------------------------------------------------------------------------
# apply_choices -- zero choices
# ---------------------------------------------------------------------------


MULTI_PARAGRAPH = (
    "First paragraph with\taccess and   multiple spaces.\n"
    "\n"
    "Second paragraph with\nsome newlines.\n"
    "\n"
    "\tIndented line with a tab stop.\n"
)


class TestApplyZeroChoices:
    def test_empty_choices_byte_identical(self) -> None:
        result = apply_choices(MULTI_PARAGRAPH, [])
        assert result == MULTI_PARAGRAPH

    def test_tabs_preserved(self) -> None:
        text = "word\taccess\tword"
        result = apply_choices(text, [])
        assert result == text

    def test_blank_lines_preserved(self) -> None:
        text = "line one\n\nline two\n\nline three\n"
        result = apply_choices(text, [])
        assert result == text

    def test_multiple_spaces_preserved(self) -> None:
        text = "one   two   three"
        result = apply_choices(text, [])
        assert result == text

    def test_trailing_newline_preserved(self) -> None:
        text = "paragraph\n"
        result = apply_choices(text, [])
        assert result == text


# ---------------------------------------------------------------------------
# apply_choices -- case and punctuation acceptance criteria
# ---------------------------------------------------------------------------


class TestApplyCaseAndPunctuation:
    # "Access, becomes Entry, with the comma intact"
    def test_title_case_comma_preserved(self) -> None:
        # "Access" is at offsets 0..6; the comma is preserved outside the span.
        text = "Access, the building."
        choices: list[Choice] = [((0, 6), "entry")]
        result = apply_choices(text, choices)
        assert result == "Entry, the building."

    # "ACCESS. transfers to uppercase and keeps the period"
    def test_uppercase_period_preserved(self) -> None:
        # "ACCESS" is at offsets 5..11; the period is preserved outside the span.
        text = "Deny ACCESS."
        choices: list[Choice] = [((5, 11), "entry")]
        result = apply_choices(text, choices)
        assert result == "Deny ENTRY."

    # "(access) keeps both parentheses"
    def test_parens_preserved(self) -> None:
        text = "See (access) policy."
        choices: list[Choice] = [((5, 11), "entry")]
        result = apply_choices(text, choices)
        assert result == "See (entry) policy."

    # "access-control is handled without corrupting the hyphenated remainder"
    def test_hyphenated_suffix_preserved(self) -> None:
        # The scanner matches only "access" (span 0..6); the rest is untouched.
        text = "access-control lists"
        choices: list[Choice] = [((0, 6), "entry")]
        result = apply_choices(text, choices)
        assert result == "entry-control lists"

    def test_lowercase_replacement(self) -> None:
        text = "use access now"
        choices: list[Choice] = [((4, 10), "entry")]
        result = apply_choices(text, choices)
        assert result == "use entry now"

    def test_title_case_replacement(self) -> None:
        text = "Use Access Now"
        choices: list[Choice] = [((4, 10), "entry")]
        result = apply_choices(text, choices)
        assert result == "Use Entry Now"

    def test_uppercase_replacement(self) -> None:
        text = "USE ACCESS NOW"
        choices: list[Choice] = [((4, 10), "entry")]
        result = apply_choices(text, choices)
        assert result == "USE ENTRY NOW"


# ---------------------------------------------------------------------------
# apply_choices -- multiple choices in one pass
# ---------------------------------------------------------------------------


class TestApplyMultipleChoices:
    def test_two_choices_forward_pass(self) -> None:
        text = "use access and address"
        #       0123456789012345678901
        #       0         1         2
        # "access" is at 4..10, "address" is at 15..22
        choices: list[Choice] = [((4, 10), "entry"), ((15, 22), "location")]
        result = apply_choices(text, choices)
        assert result == "use entry and location"

    def test_adjacent_spans(self) -> None:
        # Two replacements with no gap between them (end of one == start of next).
        text = "accessaddress"
        #       0123456789012
        # "access" 0..6, "address" 6..13
        choices: list[Choice] = [((0, 6), "entry"), ((6, 13), "location")]
        result = apply_choices(text, choices)
        assert result == "entrylocation"

    def test_choice_at_start(self) -> None:
        text = "access here"
        choices: list[Choice] = [((0, 6), "entry")]
        result = apply_choices(text, choices)
        assert result == "entry here"

    def test_choice_at_end(self) -> None:
        text = "here access"
        choices: list[Choice] = [((5, 11), "entry")]
        result = apply_choices(text, choices)
        assert result == "here entry"

    def test_multi_paragraph_fixture(self) -> None:
        text = "Use access daily.\n\nAlso address the issue.\n"
        # "access" at 4..10, "address" at 24..31
        choices: list[Choice] = [((4, 10), "entry"), ((24, 31), "location")]
        result = apply_choices(text, choices)
        assert result == "Use entry daily.\n\nAlso location the issue.\n"


# ---------------------------------------------------------------------------
# apply_choices -- validation errors
# ---------------------------------------------------------------------------


class TestApplyValidation:
    def test_unsorted_choices_raise_value_error(self) -> None:
        text = "access and address"
        choices: list[Choice] = [((11, 18), "location"), ((0, 6), "entry")]
        with pytest.raises(ValueError, match="document order"):
            apply_choices(text, choices)

    def test_overlapping_choices_raise_value_error(self) -> None:
        text = "accessing"
        # Overlapping spans: (0, 7) and (4, 9)
        choices: list[Choice] = [((0, 7), "entry"), ((4, 9), "entry")]
        with pytest.raises(ValueError, match="overlap"):
            apply_choices(text, choices)


# ---------------------------------------------------------------------------
# apply_choices -- compose with scan() output
# ---------------------------------------------------------------------------


class TestComposeWithScan:
    def test_scan_then_apply(self) -> None:
        """Prove that Choice composes with Match output before R10/R11 depend on it."""
        from wordup.models import Lexicon
        from wordup.scanner import scan

        lexicon = Lexicon.default()
        text = "Please use access to gain admittance."
        matches = scan(text, lexicon)
        # "access" should be found; pick the first alternative for it.
        access_matches = [m for m in matches if m.base == "access"]
        assert access_matches, "expected 'access' to be found by scanner"
        m = access_matches[0]
        first_alt = m.alternatives[0]
        choices: list[Choice] = [(m.span, first_alt)]
        result = apply_choices(text, choices)
        # The replacement must have appeared and be lowercase (surface is lowercase).
        assert first_alt in result
        assert "access" not in result

    def test_scan_then_apply_zero_choices(self) -> None:
        from wordup.models import Lexicon
        from wordup.scanner import scan

        lexicon = Lexicon.default()
        text = "No matches here -- just plain words."
        matches = scan(text, lexicon)
        choices: list[Choice] = []
        result = apply_choices(text, matches and choices)
        assert result == text
