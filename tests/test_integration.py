"""End-to-end integration tests for wordup.

Covers:
- Full interactive session over a multi-paragraph Markdown fixture
- Protected-region exclusion: fenced code, inline code, and URLs
- Multi-word alternative exclusion: no "deal withs" or "apply fored" in output
- Zero-choice session returns byte-identical text
"""

from __future__ import annotations

import io
import textwrap

from wordup.interactive import run_session
from wordup.models import Lexicon

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

# Multi-paragraph Markdown document.  "use" appears in prose (matches), in a
# fenced code block (protected), in an inline code span (protected), and inside
# a bare URL (protected).  "address" appears in prose so multi-word filtering
# can be tested at the output level.
MARKDOWN_FIXTURE = textwrap.dedent(
    """\
    # Introduction

    We use plain language whenever we can.
    The goal is to address every reader's needs directly.

    ## Code examples

    ```python
    def use(value):
        return value
    ```

    The inline form `use` is also common, as is the URL
    https://example.com/use/reference.

    ## Summary

    To use the tool, run the command shown above.
    Teams that address feedback promptly build trust.
    """
)


# ---------------------------------------------------------------------------
# Full session -- end to end over the Markdown fixture
# ---------------------------------------------------------------------------


def test_full_session_completes_with_exit_code_zero() -> None:
    """A complete session over the Markdown fixture returns exit code 0."""
    # Accept NO CHANGE for every match (option "0") so nothing is rewritten.
    # Use a lambda so the reader never exhausts regardless of match count.
    result, code = run_session(
        MARKDOWN_FIXTURE,
        read_fn=lambda: "0",
        err=io.StringIO(),
    )
    assert code == 0
    assert result == MARKDOWN_FIXTURE


def test_full_session_applies_choice_to_prose_match() -> None:
    """Accepting an alternative in the first prose match rewrites that word."""
    # The fixture starts with "We use plain language".
    # Accept option 1 for "use" on every occurrence; refuse (0) for others.
    responses = iter(["1", "0", "1", "0"])
    result, code = run_session(
        MARKDOWN_FIXTURE,
        read_fn=lambda: next(responses),
        err=io.StringIO(),
    )
    assert code == 0
    # The first occurrence of "use" in prose should be replaced.
    # "use" alternatives include "utilize", "employ", "apply", "operate".
    first_alt = Lexicon.default().entries["use"][0]  # "utilize"
    assert first_alt in result


def test_full_session_accepts_all_alternatives() -> None:
    """Accepting option 1 for every match produces a document free of base words."""
    result, code = run_session(
        MARKDOWN_FIXTURE,
        read_fn=lambda: "1",
        err=io.StringIO(),
    )
    assert code == 0
    # "use" in prose was replaced; confirm it is gone from prose positions.
    # The fenced and inline occurrences are protected and never prompted.
    assert "We use plain" not in result
    assert "To use the tool" not in result


# ---------------------------------------------------------------------------
# Protected-region exclusion
# ---------------------------------------------------------------------------


def test_protected_regions_never_prompted() -> None:
    """Words inside fenced code, inline code, and URLs are never offered.

    The word 'use' appears in:
      1. Prose: 'We use the library.'       -- prompted
      2. Fenced code block                  -- protected, not prompted
      3. Inline code: '`use`'               -- protected, not prompted
      4. Bare URL: https://example.com/use/ -- protected, not prompted

    Only the one prose occurrence should be prompted.
    """
    fixture = textwrap.dedent(
        """\
        We use the library.

        ```python
        use("example")
        ```

        See `use` for details.

        Reference: https://example.com/use/guide
        """
    )
    lex = Lexicon(entries={"use": ["employ", "apply"]})
    prompt_count: list[str] = []

    def counting_reader() -> str:
        prompt_count.append("0")
        return "0"

    err = io.StringIO()
    result, code = run_session(fixture, lexicon=lex, read_fn=counting_reader, err=err)
    assert code == 0
    # Exactly one prompt: the prose "use" only.
    assert len(prompt_count) == 1
    assert result == fixture


def test_fenced_word_not_matched_while_prose_word_is() -> None:
    """Same word in a fenced block is excluded; the prose occurrence is matched."""
    fixture = textwrap.dedent(
        """\
        We use the library.

        ```python
        use("example")
        ```
        """
    )
    lex = Lexicon(entries={"use": ["employ", "apply"]})
    prompts: list[str] = []

    def capture_reader() -> str:
        prompts.append("0")
        return "0"

    err = io.StringIO()
    result, code = run_session(fixture, lexicon=lex, read_fn=capture_reader, err=err)
    assert code == 0
    # Exactly one prompt: the prose "use", not the fenced one.
    assert len(prompts) == 1
    assert result == fixture


def test_inline_code_word_not_matched_while_prose_word_is() -> None:
    """Same word in inline code is excluded; the prose occurrence is matched."""
    fixture = "We use `use` here."
    lex = Lexicon(entries={"use": ["employ", "apply"]})
    prompts: list[str] = []

    def capture_reader() -> str:
        prompts.append("0")
        return "0"

    err = io.StringIO()
    result, code = run_session(fixture, lexicon=lex, read_fn=capture_reader, err=err)
    assert code == 0
    # Exactly one prompt: the prose "use" before the inline code span.
    assert len(prompts) == 1


def test_url_word_not_matched_while_prose_word_is() -> None:
    """Same word inside a bare URL is excluded; the prose occurrence is matched."""
    fixture = "We use https://example.com/use/guide every day."
    lex = Lexicon(entries={"use": ["employ", "apply"]})
    prompts: list[str] = []

    def capture_reader() -> str:
        prompts.append("0")
        return "0"

    err = io.StringIO()
    result, code = run_session(fixture, lexicon=lex, read_fn=capture_reader, err=err)
    assert code == 0
    # Exactly one prompt: the prose "use" before the URL.
    assert len(prompts) == 1


# ---------------------------------------------------------------------------
# Multi-word alternative exclusion from output
# ---------------------------------------------------------------------------


def test_output_never_contains_deal_withs() -> None:
    """Accepting every option for 'addresses' never produces 'deal withs' in output."""
    # "address" has "deal with" as an alternative; "addresses" (-s suffix)
    # must not produce "deal withs" when alternative 1 is accepted.
    # The scanner withholds multi-word alternatives when a suffix is stripped.
    # All available alternatives for "addresses" are safe single-word forms.
    lex = Lexicon(entries={"address": ["tackle", "handle", "deal with"]})
    fixture = "The team addresses every concern."
    result, code = run_session(
        fixture,
        lexicon=lex,
        read_fn=lambda: "1",
        err=io.StringIO(),
    )
    assert code == 0
    assert "deal withs" not in result
    assert "deal with" not in result


def test_output_never_contains_apply_fored() -> None:
    """Accepting every option for 'requested' never produces 'apply fored' in output."""
    # "request" has "apply for" as an alternative; "requested" (-ed suffix)
    # must not produce "apply fored".
    lex = Lexicon(entries={"request": ["ask", "solicit", "apply for"]})
    fixture = "She requested a meeting."
    result, code = run_session(
        fixture,
        lexicon=lex,
        read_fn=lambda: "1",
        err=io.StringIO(),
    )
    assert code == 0
    assert "apply fored" not in result
    assert "apply for" not in result


def test_multi_word_alternative_offered_on_exact_base_match() -> None:
    """Multi-word alternatives ARE offered for an exact (uninflected) base match."""
    lex = Lexicon(entries={"address": ["tackle", "handle", "deal with"]})
    fixture = "We must address the issue."
    # Options are [1=tackle, 2=handle, 3=deal with]; accept option 3.
    result, code = run_session(
        fixture,
        lexicon=lex,
        read_fn=lambda: "3",
        err=io.StringIO(),
    )
    assert code == 0
    assert "deal with" in result


# ---------------------------------------------------------------------------
# Zero-choice session returns byte-identical text
# ---------------------------------------------------------------------------


def test_zero_choice_session_returns_byte_identical_text() -> None:
    """A session where every match is refused (option 0) returns the exact input."""
    result, code = run_session(
        MARKDOWN_FIXTURE,
        read_fn=lambda: "0",
        err=io.StringIO(),
    )
    assert code == 0
    # Byte-identical: not just equal content but the same object value.
    assert result == MARKDOWN_FIXTURE


def test_zero_choice_preserves_whitespace_exactly() -> None:
    """Newlines, blank lines, tabs, and multiple spaces survive a zero-choice session."""
    fixture = "We use\t a tool.\n\nThe tool\naddresses needs.\n"
    lex = Lexicon(entries={"use": ["employ"], "address": ["tackle", "deal with"]})
    result, code = run_session(
        fixture,
        lexicon=lex,
        read_fn=lambda: "0",
        err=io.StringIO(),
    )
    assert code == 0
    assert result == fixture
