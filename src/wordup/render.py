"""Prompt rendering for wordup.

All public functions are pure: they return strings and never write to a
stream.  The caller is responsible for directing output to stderr.
"""

from __future__ import annotations

import os

# ANSI bold: marks the matched word in the sentence line.
_BOLD = "\x1b[1m"
_RESET = "\x1b[0m"


def color_enabled() -> bool:
    """Return ``True`` unless ``NO_COLOR`` is present in the environment.

    Follows the `NO_COLOR <https://no-color.org>`_ specification: any value
    (including the empty string) disables color.
    """
    return "NO_COLOR" not in os.environ


def render_prompt(
    sentence: str,
    match_span: tuple[int, int],
    alternatives: list[str],
    default: int | None = None,
) -> str:
    """Render the interactive prompt for a single lexicon match.

    The returned string contains, in order:

    1. The sentence window with the matched word marked (ANSI bold when color
       is enabled, plain text otherwise).
    2. A caret underline (``^``) on the following line, aligned with the
       match position within the sentence window.
    3. A numbered option list: option 0 is ``NO CHANGE``; options 1 through n
       are the offered alternatives in lexicon order.

    When *default* is provided, the corresponding option is annotated with
    ``[default]`` so the user knows which choice pressing Enter will accept.

    Parameters
    ----------
    sentence:
        The sentence window extracted from the document (e.g. via
        :func:`~wordup.context.sentence_span`).  Any trailing newline is
        stripped before display.
    match_span:
        ``(start, end)`` character offsets of the match **within** *sentence*
        (i.e. already adjusted for the sentence window's start).
    alternatives:
        Already-inflected alternatives to offer, in lexicon order.
    default:
        The pre-selected default option index (0 for NO CHANGE, 1..n for an
        alternative), or ``None`` when no default has been remembered.

    Returns
    -------
    str
        A multi-line string ending with a newline, ready to be written to a
        stream.  No ANSI escape bytes (``\\x1b``) appear in the output when
        ``NO_COLOR`` is set.
    """
    rel_start, rel_end = match_span
    use_color = color_enabled()

    # -- Sentence display line -----------------------------------------------
    sentence_line = sentence.rstrip("\n")
    if use_color:
        highlighted = (
            sentence_line[:rel_start]
            + _BOLD
            + sentence_line[rel_start:rel_end]
            + _RESET
            + sentence_line[rel_end:]
        )
    else:
        highlighted = sentence_line

    # -- Caret underline -----------------------------------------------------
    # Width is at least 1 so an empty match span still renders a visible caret.
    width = max(1, rel_end - rel_start)
    caret_line = " " * rel_start + "^" * width

    # -- Option list ---------------------------------------------------------
    all_options = ["NO CHANGE"] + list(alternatives)
    option_lines: list[str] = []
    for i, label in enumerate(all_options):
        suffix = " [default]" if i == default else ""
        option_lines.append(f"  {i}) {label}{suffix}")

    # Assemble and return.
    parts: list[str] = [highlighted, caret_line, *option_lines]
    return "\n".join(parts) + "\n"
