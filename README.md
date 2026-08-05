# wordup

Read through your own writing one word at a time, and choose better ones in
context.

wordup carries a small curated lexicon of 86 common base words. Whenever one
appears in your text, it shows you the sentence it sits in and offers
alternatives. You pick, or you decline. It never rewrites anything on its own,
because whether a word is an improvement depends entirely on the sentence around
it, and that is a judgment only the person reading it can make.

## Installation

Run it without installing anything:

```bash
uvx wordup "the big problem with this approach"
```

Or install it as a persistent tool:

```bash
uv tool install wordup
```

Or add it to a project environment:

```bash
uv add wordup
```

Requires Python 3.11 or newer. wordup has no runtime dependencies.

## Usage

Review a quoted string:

```bash
wordup "we need to get a specific result from this"
```

Review a file:

```bash
wordup -f draft.md
```

One file per invocation.

### Where the output goes

The improved text is written to stdout. Every prompt, menu, and message goes to
stderr, so redirection captures clean text and nothing else:

```bash
wordup -f draft.md > improved.md
```

Write to a file directly:

```bash
wordup -f draft.md -o improved.md
```

Overwrite the original, which requires an explicit flag:

```bash
wordup -f draft.md --in-place
```

### Flags

| Flag | Meaning |
|------|---------|
| *(positional)* | The text to review, quoted. Mutually exclusive with `-f`. |
| `-f PATH` | Read the document from a file instead. |
| `-o PATH` | Write the result to a file. Defaults to stdout. |
| `--in-place` | Overwrite the input file. Valid only with `-f`. |

## The prompt

For each match, wordup prints the containing sentence with the word marked, then
a numbered menu:

```
  it was a big problem for the team
            ^^^
  0: NO CHANGE
  1: large
  2: huge
  3: massive
  4: immense
  > _
```

Enter `0` to leave the word alone, or the number of the alternative you want.

Alternatives are shown in the exact form that will be inserted. If the word in
your text is inflected, the alternatives are inflected to match, so choosing an
option never produces a form you did not see.

### Repeated words

If you have already chosen a replacement for a word, that choice is pre-selected
as the default the next time the same word appears. Press Enter to accept it, or
type a different number:

```
  the plan was big enough to matter
                ^^^
  0: NO CHANGE
  1: large
  2: huge
  3: massive  [default]
  > _
```

Declining is never remembered. Answering `0` applies to that one occurrence
only, and it does not clear a default you set earlier. Every occurrence is
prompted, every time, because the right answer changes with the sentence.

### Code and links are skipped

Fenced code blocks, indented code blocks, inline backtick spans, and bare URLs
are left alone. A word inside `get_result()` is a variable name, not prose, so
wordup does not ask about it.

## Color

The matched word is marked with bold or reverse video, plus a caret underline
beneath it. Setting [`NO_COLOR`](https://no-color.org) to any value suppresses
all ANSI escape sequences; the caret underline remains, so the match is still
unambiguous:

```bash
NO_COLOR=1 wordup -f draft.md
```

## Requires a terminal

wordup works by asking you questions, so it cannot run unattended. In a cron
job, a CI step, or a container started without a TTY, it exits with status `2`,
writes nothing, and explains why rather than silently accepting defaults.

## Known limits

- **Irregular verbs are not matched.** Inflection uses suffix rules only, so
  `requires` reaches `require`, but `ran` does not reach `run`.
- **Multi-word alternatives are withheld from inflected matches.** A few entries
  offer phrases such as `deal with`. These appear for `address` but not for
  `addresses`, because inflecting a phrase correctly is beyond the suffix rules
  and a wrong guess is worse than a missing option.
- **The lexicon is fixed.** There is no way to add, override, or replace the
  shipped word list. It is deliberately small and curated rather than
  comprehensive.

## What wordup is not

It is not a grammar or style checker. Nothing parses sentence structure, and no
text is ever changed without you choosing the change.

## License

TBD
