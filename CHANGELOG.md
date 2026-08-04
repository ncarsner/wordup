# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initialize the repository as a `src`-layout Python package under
  `src/wordup/`.

### Changed

- Move the original `grammar_reviewer.py` script to `src/wordup/__init__.py`.
  The curated dictionary of 86 base words and 526 alternatives is preserved
  verbatim. No behavior change; the module is unmodified apart from location.
- Rename the default branch from `master` to `main`.
