"""Interactive prompt session for wordup.

:func:`run_session` drives a full interactive review of every lexicon match
in *text*, prompting the user once per occurrence and collecting accepted
replacements.  Prompts are written to *err* (stderr by default); the revised
document is returned so the caller can route it to stdout or a file.

The ``read_fn`` parameter is injectable so tests can drive the session
without a real terminal.
"""

from __future__ import annotations

import sys
from typing import Callable, TextIO

from wordup.apply import Choice, apply_choices
from wordup.context import sentence_span
from wordup.inflect import reinflect
from wordup.models import Lexicon
from wordup.render import render_prompt
from wordup.scanner import Match, scan


def _read_line() -> str:
    """Read one line from stdin via the built-in ``input``."""
    return input()


def run_session(
    text: str,
    lexicon: Lexicon | None = None,
    *,
    read_fn: Callable[[], str] = _read_line,
    err: TextIO | None = None,
) -> tuple[str, int]:
    """Run an interactive replacement session over *text*.

    Scans *text* for lexicon matches and presents an interactive prompt for
    each one in document order.  Every occurrence of every match is shown;
    there is no suppression mechanism.

    The user is offered numbered options: option ``0`` is NO CHANGE; options
    ``1..n`` are the available alternatives.  Pressing Enter with a remembered
    default accepts that default.  Pressing Enter with no default is treated as
    NO CHANGE (records nothing, leaves remembered state unchanged).  Choosing
    NO CHANGE neither creates nor clears a remembered default.

    Parameters
    ----------
    text:
        The document to scan and prompt for.
    lexicon:
        The lexicon to use.  When ``None``, the default shipped lexicon is
        loaded via :meth:`~wordup.models.Lexicon.default`.
    read_fn:
        Callable that reads one line of user input and returns it as a string.
        Defaults to the built-in ``input`` (via :func:`_read_line`).  Inject a
        scripted callable in tests so no real terminal is required.
    err:
        Stream where prompts and menus are written.  Defaults to
        ``sys.stderr`` so that nothing prompt-related appears on stdout.

    Returns
    -------
    tuple[str, int]
        The revised document and an integer exit code.  The exit code is ``0``
        for a completed session and ``130`` when the user interrupted with
        Ctrl+C (``KeyboardInterrupt``).  On interrupt, every accepted choice up
        to the interruption point is applied; the remainder of the text is
        emitted unchanged.
    """
    if err is None:
        err = sys.stderr
    if lexicon is None:
        lexicon = Lexicon.default()

    matches = scan(text, lexicon)
    choices: list[Choice] = []
    # Maps base word to the RAW (un-inflected) lexicon alternative the user
    # accepted at a prior occurrence.  Storing the raw form allows the default
    # to be re-inflected correctly when the same base word appears later in a
    # different surface form (e.g. first "create", later "creating").
    remembered: dict[str, str] = {}

    try:
        for match in matches:
            _prompt_match(text, match, lexicon, remembered, choices, read_fn, err)
    except KeyboardInterrupt:
        return apply_choices(text, choices), 130

    return apply_choices(text, choices), 0


def _prompt_match(
    text: str,
    match: Match,
    lexicon: Lexicon,
    remembered: dict[str, str],
    choices: list[Choice],
    read_fn: Callable[[], str],
    err: TextIO,
) -> None:
    """Prompt the user for one match, updating *choices* and *remembered*.

    Loops until the user supplies valid input (``0``..``n`` or Enter).  Invalid
    input displays a short error message and redisplays the same prompt without
    recording any decision.  ``KeyboardInterrupt`` propagates to the caller
    unchanged.
    """
    sent_start, sent_end = sentence_span(text, match.span[0])
    sentence = text[sent_start:sent_end]
    rel_start = match.span[0] - sent_start
    rel_end = match.span[1] - sent_start

    # Inflected alternatives offered to the user (already re-inflected by the
    # scanner to match the surface form's grammatical number or tense).
    alternatives = match.alternatives
    n = len(alternatives)

    # Raw (un-inflected) alternatives parallel to match.alternatives.
    # raws[i] is the raw lexicon form of alternatives[i].  Both are filtered
    # from lexicon.entries[match.base] by the same reinflect predicate, so
    # their indices stay aligned.
    raws: list[str] = [
        alt
        for alt in lexicon.entries[match.base]
        if reinflect(alt, match.suffix) is not None
    ]

    while True:
        # Compute the pre-selected default from remembered state.
        # remembered holds a RAW alternative; re-inflect it for the current
        # surface form and find its position in the alternatives list.
        default: int | None = None
        remembered_raw = remembered.get(match.base)
        if remembered_raw is not None:
            want = reinflect(remembered_raw, match.suffix)
            if want is not None and want in alternatives:
                default = alternatives.index(want) + 1

        prompt_text = render_prompt(
            sentence, (rel_start, rel_end), alternatives, default
        )
        err.write(prompt_text)
        err.flush()

        raw_line = read_fn().strip()

        if raw_line == "":
            # Enter: accept the pre-selected default, or NO CHANGE if no default.
            chosen_idx = default if default is not None else 0
        else:
            try:
                chosen_idx = int(raw_line)
            except ValueError:
                err.write(f"  Invalid: enter a number from 0 to {n}.\n")
                err.flush()
                continue

        if 0 <= chosen_idx <= n:
            if chosen_idx == 0:
                # NO CHANGE: leave remembered unchanged; record no choice.
                break
            # Store the RAW alternative so it can be re-inflected later.
            remembered[match.base] = raws[chosen_idx - 1]
            # Record the INFLECTED alternative for apply_choices.
            choices.append((match.span, alternatives[chosen_idx - 1]))
            break
        else:
            err.write(f"  Invalid: enter a number from 0 to {n}.\n")
            err.flush()
