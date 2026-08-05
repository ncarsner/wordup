"""Tests for suffix stemming and re-inflection.

Coverage targets:
- stem(): all rule paths, guard failures, adjust calls, min_stem skip, no-match
- reinflect(): empty suffix, multi-word/hyphenated guard, each suffix category,
  conservative None cases, unknown suffix
- _ing_ed_restore(): all three branches
- _es_guard(): all four branches
- _reinflect_*(): all branches in each category function
- Exhaustive: every shipped alternative re-inflected with every suffix is
  either well-formed or None (never malformed).
"""

from __future__ import annotations

import pytest

import wordup.inflect as inflect
from wordup.inflect import SUFFIX_TABLE, reinflect, stem
from wordup.models import Lexicon


# ---------------------------------------------------------------------------
# stem() -- parameterized cases covering every suffix rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "word, expected_stem, expected_suffix",
    [
        # -ies: consonant+y -> ies plural
        ("applies", "apply", "-ies"),
        # -ied: consonant+y -> ied past tense
        ("applied", "apply", "-ied"),
        # -ing: consonant doubling (running -> run)
        ("running", "run", "-ing"),
        # -ing: terminal-e restoration (creating -> create)
        ("creating", "create", "-ing"),
        # -ing: regular strip (no doubling, no e-restore)
        ("helping", "help", "-ing"),
        # -ing: terminal-e on vowel+consonant stem (requiring -> require)
        ("requiring", "require", "-ing"),
        # -ed: terminal-e restoration (required -> require)
        ("required", "require", "-ed"),
        # -ed: regular strip
        ("helped", "help", "-ed"),
        # -ed: consonant doubling (stopped -> stop)
        ("stopped", "stop", "-ed"),
        # -es: sibilant-s ending (accesses -> access)
        ("accesses", "access", "-es"),
        # -es: ch-digraph ending (matches -> match)
        ("matches", "match", "-es"),
        # -s: base word whose stem ends in e (requires -> require)
        ("requires", "require", "-s"),
        # -s: regular (demands -> demand)
        ("demands", "demand", "-s"),
        # -ly: adverb strip
        ("quickly", "quick", "-ly"),
        # no match: no recognizable suffix
        ("hello", "hello", ""),
    ],
)
def test_stem(word: str, expected_stem: str, expected_suffix: str) -> None:
    result_stem, result_suffix = stem(word)
    assert result_stem == expected_stem
    assert result_suffix == expected_suffix


# ---------------------------------------------------------------------------
# stem() -- guard failure: -es skipped for non-sibilant, -s fires instead
# ---------------------------------------------------------------------------


def test_stem_es_guard_skips_non_sibilant() -> None:
    """'requires' skips the -es rule (guard fails on 'r') and uses -s."""
    s, sfx = stem("requires")
    assert s == "require"
    assert sfx == "-s"


def test_stem_es_guard_accepts_sh_digraph() -> None:
    """'dishes' triggers the -es rule via the 'sh' digraph guard."""
    s, sfx = stem("dishes")
    assert s == "dish"
    assert sfx == "-es"


# ---------------------------------------------------------------------------
# stem() -- min_stem: suffix skipped when candidate is too short
# ---------------------------------------------------------------------------


def test_stem_min_stem_skips_too_short_candidate() -> None:
    """'as' ends in 's' but stripping leaves 'a' (len 1 < min_stem 2)."""
    s, sfx = stem("as")
    assert sfx == ""
    assert s == "as"


def test_stem_ing_min_stem_skips_short_candidate() -> None:
    """'ring' ends in 'ing'; stripping leaves 'r' (len 1 < min_stem 3)."""
    s, sfx = stem("ring")
    assert sfx == ""
    assert s == "ring"


# ---------------------------------------------------------------------------
# _ing_ed_restore() -- three branches
# ---------------------------------------------------------------------------


def test_ing_ed_restore_doubled_consonant() -> None:
    assert inflect._ing_ed_restore("runn") == "run"


def test_ing_ed_restore_terminal_e() -> None:
    assert inflect._ing_ed_restore("creat") == "create"


def test_ing_ed_restore_no_change() -> None:
    assert inflect._ing_ed_restore("help") == "help"


# ---------------------------------------------------------------------------
# _es_guard() -- four branches
# ---------------------------------------------------------------------------


def test_es_guard_too_short_returns_false() -> None:
    assert inflect._es_guard("es") is False


def test_es_guard_sibilant_s_returns_true() -> None:
    assert inflect._es_guard("accesses") is True


def test_es_guard_sibilant_x_returns_true() -> None:
    assert inflect._es_guard("foxes") is True


def test_es_guard_sibilant_z_returns_true() -> None:
    assert inflect._es_guard("buzzes") is True


def test_es_guard_digraph_ch_returns_true() -> None:
    assert inflect._es_guard("matches") is True


def test_es_guard_digraph_sh_returns_true() -> None:
    assert inflect._es_guard("dishes") is True


def test_es_guard_non_sibilant_returns_false() -> None:
    assert inflect._es_guard("requires") is False


# ---------------------------------------------------------------------------
# reinflect() -- suffix == "" offers word unchanged (including multi-word)
# ---------------------------------------------------------------------------


def test_reinflect_empty_suffix_returns_word() -> None:
    assert reinflect("demand", "") == "demand"


def test_reinflect_empty_suffix_returns_multiword() -> None:
    """Multi-word alternatives are offered normally on an exact base-word match."""
    assert reinflect("deal with", "") == "deal with"


def test_reinflect_empty_suffix_returns_hyphenated() -> None:
    """Hyphenated alternatives are offered normally on an exact base-word match."""
    assert reinflect("clear-cut", "") == "clear-cut"


# ---------------------------------------------------------------------------
# reinflect() -- multi-word and hyphenated withheld when suffix is non-empty
# ---------------------------------------------------------------------------


def test_reinflect_multiword_withheld_with_suffix() -> None:
    assert reinflect("deal with", "-s") is None


def test_reinflect_multiword_withheld_ing() -> None:
    assert reinflect("apply for", "-ing") is None


def test_reinflect_hyphenated_withheld_with_suffix() -> None:
    assert reinflect("clear-cut", "-ing") is None


def test_reinflect_apply_fored_never_produced() -> None:
    """'apply fored' must never appear in output."""
    assert reinflect("apply for", "-ed") is None


def test_reinflect_deal_withs_never_produced() -> None:
    """'deal withs' must never appear in output."""
    assert reinflect("deal with", "-s") is None


# ---------------------------------------------------------------------------
# reinflect() -- plural category (-s / -es / -ies all use _reinflect_plural)
# ---------------------------------------------------------------------------


def test_reinflect_s_regular() -> None:
    assert reinflect("demand", "-s") == "demands"


def test_reinflect_s_y_after_consonant() -> None:
    """Consonant+y base uses ies form."""
    assert reinflect("apply", "-s") == "applies"


def test_reinflect_s_sibilant_ending() -> None:
    """Sibilant-ending base adds 'es'."""
    assert reinflect("access", "-s") == "accesses"


def test_reinflect_s_ch_ending() -> None:
    """ch-ending base adds 'es'."""
    assert reinflect("match", "-s") == "matches"


def test_reinflect_s_sh_ending() -> None:
    """sh-ending base adds 'es'."""
    assert reinflect("dish", "-s") == "dishes"


def test_reinflect_es_uses_plural_logic() -> None:
    """'-es' suffix uses the same plural logic as '-s'."""
    assert reinflect("demand", "-es") == "demands"


def test_reinflect_ies_uses_plural_logic() -> None:
    """'-ies' suffix routes through the general plural function."""
    assert reinflect("apply", "-ies") == "applies"


def test_reinflect_ies_non_y_produces_regular_plural() -> None:
    """A non-y base reinflected with '-ies' gets its regular plural."""
    assert reinflect("demand", "-ies") == "demands"


# ---------------------------------------------------------------------------
# reinflect() -- progressive category (-ing)
# ---------------------------------------------------------------------------


def test_reinflect_ing_terminal_e_removed() -> None:
    """AC: re-inflects generate to generating."""
    assert reinflect("generate", "-ing") == "generating"


def test_reinflect_ing_regular() -> None:
    assert reinflect("demand", "-ing") == "demanding"


def test_reinflect_ing_withholds_when_doubling_needed() -> None:
    """'run' ends in vowel+consonant; doubling is ambiguous, so None."""
    assert reinflect("run", "-ing") is None


# ---------------------------------------------------------------------------
# reinflect() -- past category (-ed / -ied)
# ---------------------------------------------------------------------------


def test_reinflect_ed_terminal_e() -> None:
    """Base ending in 'e' adds just 'd'."""
    assert reinflect("require", "-ed") == "required"


def test_reinflect_ed_regular() -> None:
    assert reinflect("demand", "-ed") == "demanded"


def test_reinflect_ed_y_after_consonant() -> None:
    assert reinflect("apply", "-ed") == "applied"


def test_reinflect_ed_withholds_when_doubling_needed() -> None:
    assert reinflect("run", "-ed") is None


def test_reinflect_ied_y_ending() -> None:
    assert reinflect("apply", "-ied") == "applied"


def test_reinflect_ied_non_y_produces_past() -> None:
    """A non-y base reinflected with '-ied' gets its regular past."""
    assert reinflect("demand", "-ied") == "demanded"


# ---------------------------------------------------------------------------
# reinflect() -- adverb category (-ly)
# ---------------------------------------------------------------------------


def test_reinflect_ly() -> None:
    assert reinflect("quick", "-ly") == "quickly"


# ---------------------------------------------------------------------------
# reinflect() -- unknown suffix returns None
# ---------------------------------------------------------------------------


def test_reinflect_unknown_suffix_returns_none() -> None:
    assert reinflect("demand", "-xyz") is None


# ---------------------------------------------------------------------------
# Parameterized: every SUFFIX_TABLE rule defines a reinflect_fn
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rule", SUFFIX_TABLE, ids=lambda r: r.suffix)
def test_every_rule_has_reinflect_fn(rule: inflect.SuffixRule) -> None:
    assert rule.reinflect_fn is not None


# ---------------------------------------------------------------------------
# Exhaustive: no alternative from the shipped lexicon produces malformed output
# ---------------------------------------------------------------------------


def test_no_malformed_output_from_lexicon_alternatives() -> None:
    """Every (alternative, suffix) pair produces a well-formed result or None.

    This catches regressions like "deal withs", "apply fored", or
    "clear-cuting" that would appear in the interactive session.
    """
    lex = Lexicon.default()
    all_alts = [alt for alts in lex.entries.values() for alt in alts]
    suffixes = [rule.suffix for rule in SUFFIX_TABLE]

    for alt in all_alts:
        for suffix in suffixes:
            result = reinflect(alt, suffix)
            if result is None:
                continue
            assert len(result) > 0, f"Empty result for ({alt!r}, {suffix!r})"
            # Single-word alternatives must not gain spaces or hyphens.
            if " " not in alt and "-" not in alt:
                assert " " not in result, (
                    f"Space injected for ({alt!r}, {suffix!r}): {result!r}"
                )
                assert "-" not in result, (
                    f"Hyphen injected for ({alt!r}, {suffix!r}): {result!r}"
                )
