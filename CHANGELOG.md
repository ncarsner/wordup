# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Release procedure

Notes recorded here because both of the following cost a failed release or a
misleading debugging session, and neither is obvious from the file being edited.

**Verify the action *ref*, not the version number.** The broken pin came from
querying the `releases/latest` API, which returns `v9.0.0`, and assuming a
floating `v9` alias existed because that is the near-universal convention. It
does not for every action. Check that the exact ref resolves before relying on
it:

```bash
for r in actions/checkout astral-sh/setup-uv actions/upload-artifact \
         actions/download-artifact pypa/gh-action-pypi-publish; do
  curl -s "https://api.github.com/repos/$r/git/matching-refs/tags/v" \
    | grep -o '"ref": "[^"]*"'
done
```

Note that `pypa/gh-action-pypi-publish@release/v1` is a **branch**, not a tag,
so it will not appear in a tag listing. Verify it separately.

**A failed release run cannot be fixed by re-running it.** GitHub reads the
workflow file as it existed at trigger time, so a re-run repeats the same
failure with the same broken file. After merging a workflow fix, trigger
`workflow_dispatch` on `main` instead. The version comes from `pyproject.toml`,
so the existing tag and release need no recreating:

```bash
gh workflow run workflow.yml --repo ncarsner/wordup --ref main
```

**Bump the version before testing a rebuilt wheel locally.** uv keys its
unpacked archive store on name plus version, so rebuilding an unchanged version
resolves to the *first* wheel ever built under it. Neither `--refresh` nor
`uv cache clean <pkg>` reliably evicts it. This presents as
`Package 'wordup' does not provide any executables` or a module missing its
exports, which looks exactly like a packaging bug and is not one. A plain venv
with `pip --no-cache-dir` is the reliable check.

## [Unreleased]

### Fixed

- Pin `astral-sh/setup-uv` to `v9.0.0`. The `v0.2.0` release workflow failed in
  two seconds at `Set up job` with `Unable to resolve action
  astral-sh/setup-uv@v9, unable to find version v9`. That repository publishes
  floating major tags only up to `v7`; `v8` and `v9` exist as full tags with no
  major alias, unlike `actions/checkout` and the artifact actions.

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
