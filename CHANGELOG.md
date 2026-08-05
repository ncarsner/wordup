# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-08-05

First working version. wordup reviews text interactively, showing each lexicon
match in its containing sentence and offering alternatives to choose from.
Nothing is ever replaced without the reader accepting it.

### Added

- Add the interactive review session: every match is shown in its sentence with
  a numbered menu, option `0` is NO CHANGE, and a previously chosen alternative
  is pre-selected as the default at later occurrences of the same base word.
- Add the `wordup` command, taking quoted text directly or a file via `-f`, with
  `-o` to write elsewhere and `--in-place` to overwrite. Prompts go to stderr so
  the result can be redirected cleanly.
- Add the pure library API: `suggest`, `apply_choices`, `Lexicon`, and `Match`,
  none of which touch the terminal or filesystem at import time.
- Add span-based scanning that preserves the document exactly, replacing only
  the matched word and leaving punctuation, case, newlines, and indentation
  untouched.
- Add suffix-rule inflection, so `requires` matches `require` and the
  alternatives are offered as `demands`, `necessitates`, `compels`. Alternatives
  that cannot be inflected confidently are withheld rather than emitted
  malformed.
- Add protected regions: fenced code blocks, indented code, inline backtick
  spans, and bare URLs are never prompted.
- Add sentence-window extraction with an abbreviation guard, so `e.g.` and
  decimals do not split the displayed context.
- Add `NO_COLOR` support with a caret underline that marks the match in both the
  color and no-color paths.
- Add the curated lexicon as shipped package data at
  `src/wordup/data/lexicon.toml`: 86 base words and 526 alternatives, validated
  on load against five invariants.
- Add a PyPI trusted-publishing workflow using OIDC, with no stored API token.
- Add the README, covering installation, both invocation forms, every flag,
  prompt behavior, and the known limits.
- Add 313 tests at 100% branch coverage, with `fail_under = 100` enforced.

### Changed

- Match directionally against base words only. The original script matched both
  sides of each dictionary entry inconsistently, so an alternative could suggest
  the plainer base word back. This drops the trigger surface from 612 words
  to 86.
- Exit `2` with an explanatory message when there is no controlling terminal,
  rather than failing on a closed stdin.
- Exit `130` on `Ctrl-C`, applying every decision made so far and emitting the
  remainder untouched.
- Redisplay the prompt on invalid input instead of treating it as no-change, so
  a mistyped key cannot silently skip a word.
- Lower `requires-python` from `>=3.14` to `>=3.11`.

### Fixed

- Fix the wheel target, which was `packages = ["src"]` and produced a wheel
  installing as the import path `src.wordup`, breaking `import wordup` and the
  console script.

### Removed

- Remove the legacy `GrammarReviewer` implementation. Its dictionary survives as
  shipped TOML data; nothing else does.

## [0.1.0] - 2026-08-03

### Added

- Initialize the repository as a `src`-layout Python package under
  `src/wordup/`.

### Changed

- Move the original `grammar_reviewer.py` script to `src/wordup/__init__.py`.
  The curated dictionary of 86 base words and 526 alternatives is preserved
  verbatim. No behavior change; the module is unmodified apart from location.
- Rename the default branch from `master` to `main`.
