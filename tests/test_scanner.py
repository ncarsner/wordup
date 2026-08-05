"""Tests for the span-based lexicon scanner.

Coverage targets
----------------
- scan(): exact match, stemmed match (each suffix), multi-word filter, case
  folding, document ordering, protected-span exclusion (all four region types),
  no-match discard, empty text, multiple occurrences, hyphenated remainder.
- Match dataclass: all fields populated correctly.
- Directionality: exhaustive check that none of the 526 alternatives triggers
  a match when scanned against the full lexicon.
- No terminal or filesystem I/O: monkeypatched builtins proof.
"""

from __future__ import annotations

import builtins

import pytest

from wordup.lexicon import default as default_lexicon
from wordup.models import Lexicon
from wordup.scanner import scan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def lex() -> Lexicon:
    """Shipped lexicon, loaded once per test module."""
    return default_lexicon()


def _mini() -> Lexicon:
    """Tiny deterministic lexicon for isolated unit tests."""
    return Lexicon(
        entries={
            "access": ["entry", "admittance"],
            "address": ["tackle", "handle", "deal with"],
            "create": ["generate", "produce"],
            "bias": ["prejudice", "partiality", "preconception", "slant"],
            "discuss": ["debate", "deliberate"],
            "use": ["utilize", "employ", "apply"],
            # "grant" ends in a consonant cluster (-nt) so _ing_ed_restore
            # leaves the stem intact, giving a clean -ing inflection test.
            "grant": ["bestow", "award"],
        }
    )


# ---------------------------------------------------------------------------
# Match dataclass sanity
# ---------------------------------------------------------------------------


def test_match_fields_populated():
    """Every Match field is set to the correct value on an exact hit."""
    lex = _mini()
    matches = scan("You can access the data.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "access"
    assert m.suffix == ""
    assert m.surface == "access"
    assert isinstance(m.span, tuple) and len(m.span) == 2
    assert m.alternatives == ["entry", "admittance"]


def test_match_span_indexes_original_string():
    """span[start:end] reproduces the surface form in the original text."""
    lex = _mini()
    text = "First access the data."
    matches = scan(text, lex)
    assert len(matches) == 1
    s, e = matches[0].span
    assert text[s:e] == matches[0].surface


# ---------------------------------------------------------------------------
# Exact base-word matches
# ---------------------------------------------------------------------------


def test_exact_match_single_word_alternatives():
    """Single-word alternatives are offered on an exact base match."""
    lex = _mini()
    matches = scan("We discuss the plan.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "discuss"
    assert m.suffix == ""
    assert "debate" in m.alternatives


def test_exact_match_multi_word_alternative_offered():
    """Multi-word alternative 'deal with' is offered on an exact 'address' match."""
    lex = _mini()
    matches = scan("We must address the issue.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "address"
    assert m.suffix == ""
    assert "deal with" in m.alternatives


# ---------------------------------------------------------------------------
# Inflected surface forms
# ---------------------------------------------------------------------------


def test_inflected_ing_terminal_e():
    """'creating' stems to 'create' via terminal-e restoration."""
    lex = _mini()
    matches = scan("She is creating a report.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "create"
    assert m.suffix == "-ing"
    assert m.surface == "creating"
    # Alternatives are re-inflected: generate -> generating, produce -> producing
    assert "generating" in m.alternatives
    assert "producing" in m.alternatives


def test_inflected_es_sibilant():
    """'accesses' stems to 'access' via the -es sibilant guard."""
    lex = _mini()
    matches = scan("She accesses the file.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "access"
    assert m.suffix == "-es"
    assert m.surface == "accesses"


def test_inflected_s_creates():
    """'creates' stems to 'create' via the -s rule."""
    lex = _mini()
    matches = scan("He creates documents.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "create"
    assert m.suffix == "-s"
    assert m.surface == "creates"
    assert "generates" in m.alternatives


def test_inflected_ed():
    """'created' stems to 'create' via the -ed rule with terminal-e restoration."""
    lex = _mini()
    matches = scan("They created a draft.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "create"
    assert m.suffix == "-ed"
    assert m.surface == "created"


def test_inflected_ing_regular():
    """'granting' stems to 'grant' via the -ing rule (no terminal-e, no doubling)."""
    lex = _mini()
    # "grant" ends in "-nt"; _ing_ed_restore leaves it intact.
    matches = scan("We are granting access.", lex)
    # Both 'granting' (-> 'grant') and 'access' are base words in _mini().
    grant_matches = [m for m in matches if m.base == "grant"]
    assert len(grant_matches) == 1
    m = grant_matches[0]
    assert m.suffix == "-ing"
    assert m.surface == "granting"


# ---------------------------------------------------------------------------
# Exact-before-stem ordering
# ---------------------------------------------------------------------------


def test_exact_before_stem_bias():
    """'bias' matches via exact lookup; suffix is empty, not '-s'-stripped."""
    lex = _mini()
    matches = scan("Cognitive bias is common.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "bias"
    assert m.suffix == ""
    assert m.surface == "bias"
    assert "prejudice" in m.alternatives


# ---------------------------------------------------------------------------
# Multi-word and hyphenated alternative filtering
# ---------------------------------------------------------------------------


def test_inflected_withholds_multi_word_alternative():
    """Inflected 'addresses' withholds multi-word 'deal with'."""
    lex = _mini()
    matches = scan("The plan addresses the concern.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "address"
    assert m.suffix != ""
    # No alternative should contain a space.
    assert all(" " not in alt for alt in m.alternatives), (
        f"Multi-word alternative leaked: {m.alternatives}"
    )


def test_exact_match_includes_multi_word_alternative():
    """Exact 'address' offers the multi-word alternative 'deal with'."""
    lex = _mini()
    matches = scan("We must address the issue.", lex)
    m = matches[0]
    assert m.suffix == ""
    assert any(" " in alt for alt in m.alternatives)


def test_alternatives_preserve_lexicon_order():
    """The alternative list preserves the order declared in the lexicon."""
    lex = _mini()
    matches = scan("We must address the issue.", lex)
    assert len(matches) == 1
    m = matches[0]
    # Lexicon order: ["tackle", "handle", "deal with"]
    assert m.alternatives == ["tackle", "handle", "deal with"]


# ---------------------------------------------------------------------------
# Case-insensitivity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("word", ["access", "ACCESS", "Access", "aCcEsS"])
def test_case_insensitive_match(word: str):
    """Scanner matches regardless of surface capitalisation."""
    lex = _mini()
    matches = scan(f"To {word} the data.", lex)
    assert len(matches) == 1
    m = matches[0]
    assert m.base == "access"
    # Surface form preserves original casing.
    assert m.surface == word


# ---------------------------------------------------------------------------
# Document ordering
# ---------------------------------------------------------------------------


def test_document_order_multiple_bases():
    """Matches are returned in ascending start-offset order."""
    lex = _mini()
    text = "We create new ways to access and address problems."
    matches = scan(text, lex)
    starts = [m.span[0] for m in matches]
    assert starts == sorted(starts)
    assert len(matches) == 3


def test_multiple_occurrences_of_same_base():
    """Each occurrence of a base word produces a separate Match."""
    lex = _mini()
    text = "access then access again"
    matches = scan(text, lex)
    assert len(matches) == 2
    assert matches[0].surface == "access"
    assert matches[1].surface == "access"
    assert matches[0].span[0] < matches[1].span[0]


# ---------------------------------------------------------------------------
# Directionality: alternatives never trigger a match
# ---------------------------------------------------------------------------


def test_alternatives_never_match(lex: Lexicon):
    """None of the 526 alternatives produces a match when scanned alone.

    This exhaustive sweep is the primary proof that the scanner is
    directional: only base words trigger; alternatives do not.
    """
    failing: list[str] = []
    for alts in lex.entries.values():
        for alt in alts:
            result = scan(alt, lex)
            if result:
                failing.append(alt)

    assert failing == [], (
        f"These alternatives triggered matches (scanner is non-directional): {failing}"
    )


# ---------------------------------------------------------------------------
# Protected span exclusion
# ---------------------------------------------------------------------------

# Fixture text containing 'access' once in prose and once in each protected
# region type.  Only the prose occurrence should produce a match.
_PROTECTED_FIXTURE = (
    "Prose access here.\n"
    "```\naccess in fence\n```\n"
    "    access in indent\n"
    "And `access` inline.\n"
    "See https://example.com/access for details.\n"
)


def test_protected_only_prose_matches():
    """Words in all four protected region types are excluded; prose match survives."""
    lex = _mini()
    matches = scan(_PROTECTED_FIXTURE, lex)
    assert len(matches) == 1, (
        f"Expected 1 match (prose only), got {len(matches)}: {matches}"
    )
    m = matches[0]
    assert m.surface == "access"
    # Confirm the match is the prose occurrence, not a protected one.
    assert _PROTECTED_FIXTURE[m.span[0] : m.span[1]] == "access"
    # The prose line is the very first line, so the offset should be small.
    assert m.span[0] < len("Prose access here.\n")


def test_protected_fenced_block():
    """'access' inside a fenced code block is not scanned."""
    lex = _mini()
    text = "Normal prose.\n```\naccess\n```\n"
    matches = scan(text, lex)
    assert matches == []


def test_protected_indented_block():
    """'access' on an indented-code line is not scanned."""
    lex = _mini()
    text = "    access\n"
    matches = scan(text, lex)
    assert matches == []


def test_protected_inline_code():
    """'access' inside inline backtick code is not scanned."""
    lex = _mini()
    text = "`access`"
    matches = scan(text, lex)
    assert matches == []


def test_protected_url():
    """'access' embedded in a URL is not scanned."""
    lex = _mini()
    text = "See https://example.com/access for more."
    matches = scan(text, lex)
    assert matches == []


# ---------------------------------------------------------------------------
# No terminal or filesystem I/O
# ---------------------------------------------------------------------------


def test_scan_does_not_call_print(monkeypatch: pytest.MonkeyPatch):
    """scan() does not call builtins.print."""
    lex = _mini()

    def _no_print(*args: object, **kwargs: object) -> None:
        raise AssertionError("scan() called print()")

    monkeypatch.setattr(builtins, "print", _no_print)
    result = scan("access the data", lex)
    assert isinstance(result, list)


def test_scan_does_not_call_input(monkeypatch: pytest.MonkeyPatch):
    """scan() does not call builtins.input."""
    lex = _mini()

    def _no_input(*args: object, **kwargs: object) -> str:
        raise AssertionError("scan() called input()")

    monkeypatch.setattr(builtins, "input", _no_input)
    result = scan("access the data", lex)
    assert isinstance(result, list)


def test_scan_does_not_open_files(monkeypatch: pytest.MonkeyPatch):
    """scan() does not access the filesystem via open()."""
    lex = _mini()

    def _no_open(*args: object, **kwargs: object) -> object:
        raise AssertionError(f"scan() called open() with args={args}")

    monkeypatch.setattr(builtins, "open", _no_open)
    result = scan("access the data", lex)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_text():
    """Scanning an empty string returns an empty list."""
    lex = _mini()
    assert scan("", lex) == []


def test_no_base_words_in_text():
    """Text that contains no base words returns an empty list."""
    lex = _mini()
    assert scan("The quick brown fox jumps.", lex) == []


def test_hyphenated_remainder_not_corrupted():
    """'access-control' splits at '-'; 'access' matches, 'control' does not."""
    lex = _mini()
    text = "the access-control policy"
    matches = scan(text, lex)
    assert len(matches) == 1
    assert matches[0].base == "access"
    # 'control' is not in the mini lexicon; if it appeared it would be a bug.
    bases = [m.base for m in matches]
    assert "control" not in bases


def test_alternative_word_not_matched():
    """An alternative such as 'entry' never triggers a match."""
    lex = _mini()
    # 'entry' is an alternative for 'access', never a base.
    matches = scan("Please use the entry point.", lex)
    # 'use' is a base in _mini(), but 'entry' should not be matched.
    base_words = {m.base for m in matches}
    assert "entry" not in base_words


def test_scan_with_full_lexicon_prose(lex: Lexicon):
    """A real sentence with a known base word returns at least one match."""
    matches = scan("Please use the correct term.", lex)
    bases = {m.base for m in matches}
    assert "use" in bases


def test_requires_stems_to_require(lex: Lexicon):
    """'requires' stems to 'require' and carries alternatives."""
    matches = scan("The task requires attention.", lex)
    bases = {m.base for m in matches}
    assert "require" in bases
    for m in matches:
        if m.base == "require":
            assert m.suffix == "-s"
            assert m.surface == "requires"
            assert m.alternatives  # at least one alternative
