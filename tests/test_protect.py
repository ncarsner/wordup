"""Tests for wordup.protect -- protected region detection."""

from __future__ import annotations


from wordup.protect import overlaps, protected_spans

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MARKDOWN = """\
Here is a fenced code block:

```python
def hello():
    print("world")
```

Here is an indented code block:

    indented line one
    indented line two

Here is an inline code span: `rm -rf /` in the middle.

Here is a URL: https://example.com/path?q=1 in a sentence.

Normal prose that should not be protected.
"""


# ---------------------------------------------------------------------------
# Fenced code blocks
# ---------------------------------------------------------------------------


def test_fenced_block_includes_fence_lines() -> None:
    text = "```\nfoo\n```"
    spans = protected_spans(text)
    assert spans == [(0, len(text))]


def test_fenced_block_detected() -> None:
    text = "before\n```\ncode here\n```\nafter"
    spans = protected_spans(text)
    first_fence = text.index("```")
    last_fence_end = text.rindex("```") + 3
    assert any(s <= first_fence and e >= last_fence_end for s, e in spans)


def test_fenced_block_with_language_identifier() -> None:
    text = "```python\nx = 1\n```"
    spans = protected_spans(text)
    assert spans == [(0, len(text))]


def test_two_fenced_blocks_detected_separately() -> None:
    text = "```\na\n```\n\n```\nb\n```"
    spans = protected_spans(text)
    # Both blocks are protected; verify no prose between them is swallowed.
    assert len(spans) == 2


def test_word_inside_fenced_block_overlaps() -> None:
    text = "```\nutilize\n```"
    spans = protected_spans(text)
    offset = text.index("utilize")
    assert overlaps((offset, offset + len("utilize")), spans)


def test_word_outside_fenced_block_does_not_overlap() -> None:
    text = "```\ncode\n```\nutilize"
    spans = protected_spans(text)
    offset = text.index("utilize")
    assert not overlaps((offset, offset + len("utilize")), spans)


# ---------------------------------------------------------------------------
# Indented code blocks
# ---------------------------------------------------------------------------


def test_indented_four_spaces_protected() -> None:
    text = "prose\n    code line\nmore prose"
    spans = protected_spans(text)
    offset = text.index("    code line")
    assert overlaps((offset, offset + len("    code line")), spans)


def test_indented_tab_protected() -> None:
    text = "prose\n\tcode line\nmore prose"
    spans = protected_spans(text)
    offset = text.index("\tcode line")
    assert overlaps((offset, offset + len("\tcode line")), spans)


def test_word_inside_indented_block_overlaps() -> None:
    text = "    utilize\n"
    spans = protected_spans(text)
    offset = text.index("utilize")
    assert overlaps((offset, offset + len("utilize")), spans)


def test_prose_line_not_protected() -> None:
    text = "utilize is a plain prose word\n"
    spans = protected_spans(text)
    offset = text.index("utilize")
    assert not overlaps((offset, offset + len("utilize")), spans)


# ---------------------------------------------------------------------------
# Inline backtick spans
# ---------------------------------------------------------------------------


def test_inline_backtick_detected() -> None:
    text = "See `rm -rf /` for details."
    spans = protected_spans(text)
    start = text.index("`rm")
    end = text.index("/`") + 2
    assert any(s <= start and e >= end for s, e in spans)


def test_word_inside_inline_code_overlaps() -> None:
    text = "Use `utilize` not that."
    spans = protected_spans(text)
    offset = text.index("utilize")
    assert overlaps((offset, offset + len("utilize")), spans)


def test_word_outside_inline_code_does_not_overlap() -> None:
    text = "`code` utilize"
    spans = protected_spans(text)
    offset = text.index("utilize")
    assert not overlaps((offset, offset + len("utilize")), spans)


def test_inline_code_no_newline_match() -> None:
    # A backtick followed by a newline should not form an inline code span.
    text = "`unclosed\nutilize`"
    spans = protected_spans(text)
    offset = text.index("utilize")
    # "utilize" at end of second line should not be protected by the inline pattern.
    assert not overlaps((offset, offset + len("utilize")), spans)


# ---------------------------------------------------------------------------
# Bare URLs
# ---------------------------------------------------------------------------


def test_http_url_detected() -> None:
    text = "Visit http://example.com for more."
    spans = protected_spans(text)
    start = text.index("http://")
    end = text.index("com") + 3
    assert any(s <= start and e >= end for s, e in spans)


def test_https_url_detected() -> None:
    text = "Visit https://example.com/path?q=1 for more."
    spans = protected_spans(text)
    start = text.index("https://")
    end = text.index("?q=1") + 4
    assert any(s <= start and e >= end for s, e in spans)


def test_word_inside_url_overlaps() -> None:
    text = "See https://utilize.example.com/path for info."
    spans = protected_spans(text)
    offset = text.index("utilize")
    assert overlaps((offset, offset + len("utilize")), spans)


def test_word_after_url_does_not_overlap() -> None:
    text = "See https://example.com then utilize something."
    spans = protected_spans(text)
    offset = text.index("utilize")
    assert not overlaps((offset, offset + len("utilize")), spans)


# ---------------------------------------------------------------------------
# Overlap and adjacency merging
# ---------------------------------------------------------------------------


def test_overlapping_spans_merged() -> None:
    # A URL inside backtick code: two patterns match overlapping regions.
    text = "`https://example.com`"
    spans = protected_spans(text)
    assert len(spans) == 1
    assert spans[0] == (0, len(text))


def test_adjacent_spans_merged() -> None:
    # Inline code ends where the URL begins -- adjacent spans merge.
    text = "`foo`https://bar.com"
    spans = protected_spans(text)
    assert len(spans) == 1
    assert spans[0] == (0, len(text))


def test_non_overlapping_spans_preserved() -> None:
    text = "`foo` bar `baz`"
    spans = protected_spans(text)
    assert len(spans) == 2
    assert spans[0] == (0, 5)
    assert spans[1] == (10, 15)


def test_empty_text_returns_empty() -> None:
    assert protected_spans("") == []


def test_no_protected_regions_returns_empty() -> None:
    assert protected_spans("plain prose with no code or URLs") == []


def test_full_markdown_fixture_sorted_non_overlapping() -> None:
    spans = protected_spans(MARKDOWN)
    for i in range(len(spans) - 1):
        assert spans[i][1] <= spans[i + 1][0], (
            f"spans overlap or out of order: {spans[i]} and {spans[i + 1]}"
        )


# ---------------------------------------------------------------------------
# overlaps() helper
# ---------------------------------------------------------------------------


def test_overlaps_true_contained() -> None:
    protected = [(10, 20), (30, 40)]
    assert overlaps((12, 18), protected) is True


def test_overlaps_true_partial_start() -> None:
    protected = [(10, 20)]
    assert overlaps((5, 15), protected) is True


def test_overlaps_true_partial_end() -> None:
    protected = [(10, 20)]
    assert overlaps((15, 25), protected) is True


def test_overlaps_false_adjacent_after() -> None:
    # Span starts exactly where protected ends -- no overlap.
    protected = [(10, 20)]
    assert overlaps((20, 25), protected) is False


def test_overlaps_false_before() -> None:
    protected = [(10, 20)]
    assert overlaps((0, 5), protected) is False


def test_overlaps_false_between_two() -> None:
    protected = [(10, 20), (30, 40)]
    assert overlaps((22, 28), protected) is False


def test_overlaps_empty_protected() -> None:
    assert overlaps((0, 10), []) is False


def test_overlaps_span_after_all_protected() -> None:
    protected = [(0, 5), (10, 15)]
    assert overlaps((20, 30), protected) is False
