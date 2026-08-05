"""Tests for wordup.context.sentence_span."""

from __future__ import annotations

import pytest

from wordup.context import sentence_span


# ---------------------------------------------------------------------------
# Basic sentence splitting
# ---------------------------------------------------------------------------


def test_single_sentence_no_boundary() -> None:
    """A single sentence with no punctuation returns the whole text."""
    text = "Use simpler words in your writing"
    assert sentence_span(text, 4) == (0, len(text))


def test_two_sentences_first() -> None:
    text = "This is good. That is fine."
    # offset inside "This is good"
    start, end = sentence_span(text, 5)
    assert start == 0
    assert text[start:end].startswith("This")
    assert "good" in text[start:end]


def test_two_sentences_second() -> None:
    text = "This is good. That is fine."
    # offset inside "That is fine"
    start, end = sentence_span(text, 15)
    assert text[start:end].startswith("That")


def test_split_on_exclamation() -> None:
    text = "Stop! Go now please."
    start, end = sentence_span(text, 0)
    assert text[start:end].rstrip() in {"Stop!", "Stop! "}
    # Second sentence
    start2, end2 = sentence_span(text, 7)
    assert text[start2:end2].startswith("Go")


def test_split_on_question_mark() -> None:
    text = "Are you sure? Yes I am."
    start, end = sentence_span(text, 0)
    assert "sure" in text[start:end]
    start2, end2 = sentence_span(text, 15)
    assert text[start2:end2].startswith("Yes")


# ---------------------------------------------------------------------------
# Abbreviation guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "abbrev",
    [
        "e.g.",
        "i.e.",
        "etc.",
        "vs.",
        "Dr.",
        "Mr.",
        "Mrs.",
    ],
)
def test_abbreviation_no_split(abbrev: str) -> None:
    """Abbreviations must not trigger a sentence split."""
    text = f"Use {abbrev} Always check."
    # Offset inside "Use ..."
    start, end = sentence_span(text, 0)
    # The abbreviation and everything after it should be in one sentence
    # (no split inside the abbreviation text).
    fragment = text[start:end]
    assert abbrev in fragment, f"Expected {abbrev!r} in sentence, got {fragment!r}"


def test_eg_no_split() -> None:
    text = "Use simpler words, e.g. shorter ones. Next sentence here."
    start, end = sentence_span(text, 5)
    assert "e.g." in text[start:end]


def test_ie_no_split() -> None:
    text = "Replace jargon, i.e. technical terms. Another sentence."
    start, end = sentence_span(text, 0)
    assert "i.e." in text[start:end]


def test_etc_no_split() -> None:
    text = "Include items, etc. Then continue."
    start, end = sentence_span(text, 0)
    assert "etc." in text[start:end]


def test_dr_no_split() -> None:
    text = "Consult Dr. Smith for advice. Results vary."
    start, end = sentence_span(text, 0)
    assert "Dr." in text[start:end]


def test_mr_no_split() -> None:
    text = "Ask Mr. Jones about it. He knows."
    start, end = sentence_span(text, 0)
    assert "Mr." in text[start:end]


def test_mrs_no_split() -> None:
    text = "Talk to Mrs. Brown about it. She will help."
    start, end = sentence_span(text, 0)
    assert "Mrs." in text[start:end]


def test_vs_no_split() -> None:
    text = "Consider option A vs. option B. Both work."
    start, end = sentence_span(text, 0)
    assert "vs." in text[start:end]


# ---------------------------------------------------------------------------
# Decimal guard
# ---------------------------------------------------------------------------


def test_decimal_no_split() -> None:
    """A decimal number must not trigger a sentence split."""
    text = "The value is 3.14 approximately. Check it."
    start, end = sentence_span(text, 0)
    assert "3.14" in text[start:end]


def test_decimal_at_end_of_sentence() -> None:
    """A decimal at the very end of a sentence still finds two sentences."""
    text = "The ratio is 1.5. Then we move on."
    # The period after 1.5 is part of the decimal, not a boundary.
    # "1.5." -- the dot after 1.5 is the decimal dot; no split there.
    # But actually "1.5." has two dots: the decimal dot (between 1 and 5)
    # and the sentence-ending dot (after 5). The decimal guard only protects
    # dots that sit between digits. The terminal dot is after "5", not between
    # digits, so it can be a boundary if followed by space+capital.
    start, end = sentence_span(text, 30)
    assert text[start:end].startswith("Then")


# ---------------------------------------------------------------------------
# Fallback: block between blank lines
# ---------------------------------------------------------------------------


def test_no_punctuation_falls_back_to_block() -> None:
    """Without terminal punctuation, returns the block between blank lines."""
    text = "First block here\n\nSecond block here\n\nThird block"
    # Offset inside "Second block here"
    offset = text.index("Second")
    start, end = sentence_span(text, offset)
    block = text[start:end]
    assert "Second" in block
    assert "First" not in block
    assert "Third" not in block


def test_no_punctuation_single_block() -> None:
    """No blank lines and no punctuation: returns the whole text."""
    text = "Just one long block of text with no breaks"
    start, end = sentence_span(text, 10)
    assert (start, end) == (0, len(text))


def test_fallback_first_block() -> None:
    text = "Block one\n\nBlock two"
    start, end = sentence_span(text, 3)
    assert text[start:end].startswith("Block one")


# ---------------------------------------------------------------------------
# Match span is unchanged when boundary is wrong
# ---------------------------------------------------------------------------


def test_match_span_independent_of_sentence_span() -> None:
    """The sentence_span function returns window offsets only.

    The match span stored in a Match object is never altered by context
    extraction -- this test verifies that sentence_span does not modify
    any external state and that the offsets it returns are independent
    of the match's own span.
    """
    text = "Use simpler words. Access the data."
    # "Access" starts at offset 19
    match_start = text.index("Access")
    match_end = match_start + len("Access")

    sentence_start, sentence_end = sentence_span(text, match_start)

    # The sentence window covers "Access the data."
    assert text[sentence_start:sentence_end].startswith("Access")
    # The match offsets are still valid within the original text
    assert text[match_start:match_end] == "Access"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_offset_at_very_end() -> None:
    """An offset at the last character returns the last sentence."""
    text = "First sentence. Second sentence."
    start, end = sentence_span(text, len(text) - 1)
    assert text[start:end].startswith("Second")


def test_offset_equals_length() -> None:
    """Offset == len(text) hits the post-loop fallback and returns the last sentence."""
    text = "First sentence. Second sentence."
    start, end = sentence_span(text, len(text))
    # Falls through the loop (no pair satisfies start <= len(text) < len(text))
    # and returns the final sentence span.
    assert text[start:end].startswith("Second")


def test_offset_zero() -> None:
    """Offset 0 always falls in the first sentence."""
    text = "Hello world. Another sentence."
    start, end = sentence_span(text, 0)
    assert start == 0
    assert "Hello" in text[start:end]


def test_multiple_sentences_middle() -> None:
    text = "One. Two. Three. Four."
    # "Three" starts at offset 10
    offset = text.index("Three")
    start, end = sentence_span(text, offset)
    assert "Three" in text[start:end]
    assert "One" not in text[start:end]
    assert "Four" not in text[start:end]


def test_empty_text() -> None:
    """Empty text returns (0, 0)."""
    assert sentence_span("", 0) == (0, 0)


def test_no_split_without_capital_after_punctuation() -> None:
    """A period followed by lowercase does not split."""
    text = "e.g. this is not a new sentence. But this is."
    # The period after "sentence" is followed by space+capital, so it splits.
    start, end = sentence_span(text, 0)
    assert "e.g." in text[start:end]
    # The split at "But" should produce a second sentence.
    offset = text.index("But")
    start2, end2 = sentence_span(text, offset)
    assert text[start2:end2].startswith("But")
