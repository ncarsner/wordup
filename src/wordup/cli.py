"""Command-line entry point for wordup."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wordup.errors import WordupError
from wordup.interactive import run_session


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="wordup",
        description="Interactive plain-language reviewer.",
    )

    # Input: positional text or -f (mutual exclusivity validated in main).
    parser.add_argument(
        "text",
        nargs="?",
        default=None,
        metavar="TEXT",
        help="Text to review directly.",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=None,
        metavar="PATH",
        help="Read document from PATH.",
    )

    # Output: -o and --in-place are mutually exclusive.
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write result to PATH (default: stdout).",
    )
    output_group.add_argument(
        "--in-place",
        action="store_true",
        default=False,
        help="Overwrite the input file. Requires -f.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns an integer exit code."""
    args = build_parser().parse_args(argv)

    # Validate input source: TEXT and -f are mutually exclusive.
    if args.text is not None and args.file is not None:
        print(
            "error: TEXT and -f/--file are mutually exclusive",
            file=sys.stderr,
        )
        return 2

    if args.text is None and args.file is None:
        print(
            "error: supply TEXT or -f/--file",
            file=sys.stderr,
        )
        return 2

    # --in-place is only valid with -f.
    if args.in_place and args.file is None:
        print(
            "error: --in-place requires -f/--file",
            file=sys.stderr,
        )
        return 2

    # Require an interactive terminal for the prompt session.
    if not sys.stdin.isatty():
        print(
            "error: wordup requires an interactive terminal (stdin is not a tty)",
            file=sys.stderr,
        )
        return 2

    # Read input.
    if args.text is not None:
        text = args.text
    else:
        try:
            text = args.file.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"error: file not found: {args.file}", file=sys.stderr)
            return 1
        except IsADirectoryError:
            print(f"error: {args.file} is a directory", file=sys.stderr)
            return 1
        except PermissionError:
            print(f"error: permission denied: {args.file}", file=sys.stderr)
            return 1
        except UnicodeDecodeError as exc:
            print(
                f"error: {args.file}: cannot decode as {exc.encoding}: {exc.reason}",
                file=sys.stderr,
            )
            return 1

    # Run the interactive session. The partial result is written even on
    # KeyboardInterrupt (exit code 130) so no accepted choice is lost.
    try:
        result, exit_code = run_session(text)
    except WordupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Write output.
    if args.in_place:
        try:
            args.file.write_text(result, encoding="utf-8")
        except PermissionError:
            print(
                f"error: cannot write to {args.file}: permission denied",
                file=sys.stderr,
            )
            return 1
    elif args.output is not None:
        try:
            args.output.write_text(result, encoding="utf-8")
        except PermissionError:
            print(
                f"error: cannot write to {args.output}: permission denied",
                file=sys.stderr,
            )
            return 1
    else:
        sys.stdout.write(result)

    return exit_code
