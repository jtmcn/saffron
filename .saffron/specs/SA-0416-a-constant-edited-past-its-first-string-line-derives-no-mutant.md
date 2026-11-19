---
id: SA-0416
title: "A multi-line constant edited past its first string line derives no constant mutant, so its read-back witness passes"
type: bug
priority: 2
estimated_lines: 81
estimate_measured: true
removes:
  - saffron/gates/core/witness.py:_overlaps_added
touches:
  - saffron/gates/core/witness.py
  - saffron/gates/suite.py
  - saffron/cell/worktree.py
  - saffron/repos/policy.py
  - tests/test_constant_mutants.py
  - tests/test_suite.py
  - tests/test_worktree.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/intake.py
  - tests/test_intake.py
  - saffron/agents/**
  - saffron/phases/**
  - saffron/cell/session.py
  - saffron/gates/runner.py
  - saffron/gates/core/integrity.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 62
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      With the notes' `witness:` patterns verbatim, a gate suite over a real
      git tree derives the mutant of a constant whose edit sits deep inside
      its value. The constant `LONG` is a name, ` = (`, nine string lines
      and a closing paren. The head edits its fifth string line and no other
      line of it, so that edit's hunk holds neither `LONG`'s opening line
      nor its closing line. The same commit edits a function body above
      `LONG` and one below it, so the diff holds three hunks and `LONG`'s
      edit is the middle one. A constant `AFTER` follows the closing paren
      unedited. The witness that compares the code's output with `LONG`
      also names `AFTER`. `witness` reports `fail` with exactly one
      `survived-mutant` failure, filed under that witness, and its message
      names `LONG`. The witness that pins the literal dies under the same
      edit. The tree shows no change afterwards. The witness drives
      `GateSuite._run` with a real `tests` gate.
    witness: tests/test_constant_mutants.py::test_an_edit_deep_inside_a_long_constant_derives_its_mutant
    wrong_versions:
      - "`constant_mutants` searches each hunk's new side as before, so a hunk holding neither end of `LONG` derives nothing and `witness` reports `skip`."
      - "`GateSuite._run` passes a reader that returns `None` for every path, so nothing is derived."
      - The added lines are read from the first hunk alone, so `LONG`'s edit in the second hunk is missed.
      - The added lines are read from the last hunk alone.
      - A match counts only on the lines up to the end of its `value` group, so an edit on `LONG`'s fifth string line is missed.
  - claim: >-
      `constant_mutants` searches each constant pattern over the head text of
      each file outside the test paths that the diff adds a line to. A match
      counts when any line it spans is an added line. Its `find` spans from
      the match's start to the end of its `value` group, and its `replace`
      is that text with the `value` span expanded. The witness's module is
      the notes' fixture, nine constants back to back, one per spelling.
      They are a triple-quoted string whose body sits at column 0 and holds
      a blank line, a parenthesized concatenation of eight strings, a
      one-line implicit concatenation, the same in single quotes, a
      parenthesized tuple of eight strings, an integer, a string in
      single-quote triple quotes, a parenthesized sum of a string and a
      name, and a parenthesized concatenation that ends the file. Each of
      the module's 56 lines is edited alone, by a trailing space, in its own commit, and
      read through the diff `git` gives with `worktree.DIFF_FLAGS`. An edit
      to any line of a constant derives that constant alone, with the
      notes' `find` and `replace` for it. That covers its opening line,
      each middle line, its last string line and its closing line. An edit to a blank line
      between two constants, to the `def` line or to its body derives
      nothing, and the module holds five such lines. The witness compares
      the whole derived list for each line.
    witness: tests/test_constant_mutants.py::test_an_edit_to_any_line_of_a_constant_derives_its_mutant
    wrong_versions:
      - "`constant_mutants` searches each hunk's new side as before, so an edit five lines into the triple-quoted constant derives nothing."
      - The `find` is the whole match, so it reaches the constant's last line.
      - A match counts only on the lines up to the end of its `value` group.
      - The last line a match spans is counted one too far, so an edit to the line after a constant derives it.
      - The first line a match spans is counted one too early, so an edit to the line before a constant derives it.
      - Context lines count as added, so an edit beside a constant derives it.
      - The `replace` keeps the match's text past `value`, so applying it writes the rest of the constant twice.
      - "`PATTERNS` copies the YAML spelling of the string pattern, so the single-quote branches match doubled quotes and `QUOTED` and `SINGLE` derive nothing."
  - claim: >-
      `CellTree.head_text(path)` returns the file's text at `HEAD` for a
      regular file and for an executable one, never the working copy's
      uncommitted edit. It returns `None` for a symlink, a gitlink and a
      path absent at `HEAD`. A refused read raises `CellRuntimeError`
      carrying git's stderr, whether `ls-tree` or the blob read is refused.
      In the second case `ls-tree` reaches the real repo. The witness drives `worktree` over a real git
      repo through `runtime.exec_`. It reads seven paths in this order. They
      are a symlink, the edited regular file, a regular file named
      `:odd.py`, a gitlink, a regular file one directory down, the
      executable and an absent path.
    witness: tests/test_worktree.py::test_head_text_reads_a_regular_file_at_head_and_nothing_else
    wrong_versions:
      - The reader reads the working copy, so the uncommitted edit comes back.
      - A refused `ls-tree` returns `None`, so a broken git reads as a file with no text.
      - The blob read's refusal returns `None`, as `read_at_head` does.
      - A symlink is read as a regular file, so its target's name comes back as text.
      - Only mode `100644` reads, so the executable comes back `None`.
      - "`ls-tree` reads its path as a pathspec, so `:odd.py` comes back `None`."
---

## Context

Backlog item **b-32b3db**, filed 2026-10-19 from review of #908 (`SA-0280`),
with **b-5b1f8a**. It cites `DESIGN.md` §5.4.1 and §2.1. Every line below
was read at `fa96c212`.

**Where the gap sits.** `_candidate_constants` searches each constant pattern
over each hunk's new side (`saffron/gates/core/witness.py:434-437`). A
match counts only when it overlaps an added line (`:438`), and its `find`
is the whole match (`:441`). The export pins `--unified=3`
(`saffron/cell/worktree.py:213`). So two things stop an edit from deriving.

- Both declared constant patterns end at their `value` group
  (`.saffron/policy.yaml:157-160`). The string pattern stops at the first
  opening quote. An edit to a later line of the value overlaps no match.
- An edit four or more lines below the opening line leaves the opening
  outside its hunk. No pattern can match there, whatever it spans.

Measured at `fa96c212` with this repo's declared patterns: a trailing
space on line 200 of `SCHEMA` in `saffron/ledger.py` (lines 94 to 351)
derives no mutant, against a witness that names `SCHEMA`. The prototype
with the notes' pattern derives it.

**What the language fact is.** Where a constant's value ends is Python
knowledge, so it comes from the repo's pattern (§2.1). The notes' pattern
matches past `value` to the constant's end. Core then counts every line the
match spans, and searches the file's head text rather than one hunk.
`ConstantPattern` already takes any `re` with `name` and `value` groups
(`saffron/repos/policy.py:80-117`). So no policy field is added.

**Who reads what this changes.**

- `GateSuite._run` is the only caller of `constant_mutants`
  (`saffron/gates/suite.py:191-193`). It holds a `Tree`, the protocol at
  `saffron/gates/suite.py:59-75`.
- `CellTree` is the production `Tree` (`saffron/gates/suite.py:78-108`).
  GATE and PACKAGE's reverify both build one.
- `tests/test_suite.py:21` defines `_Tree`, a fake `Tree`. Its users
  include `tests/test_finish.py:2955`, which loads this repo's own
  policy, `witness:` block included.
- `tests/test_constant_mutants.py:54-104` defines `_GitTree`, another
  fake. Its three `constant_mutants` callers pass four arguments
  (`tests/test_constant_mutants.py:327`, `:369-385`, `:397`).
- `source_mutated` already refuses any path whose `ls-tree` mode is not
  `100644` or `100755` (`saffron/cell/worktree.py:800-815`).

## Problem

Make an added line on any line of a constant's match derive its mutant.

1. Add `head_text(target, path) -> str | None` to
   `saffron/cell/worktree.py`. It returns the file's text at `HEAD`, the
   new side `export_patch` reads. Ask `git --literal-pathspecs ls-tree
   HEAD -- <path>` first. Return `None` unless the entry's mode is
   `100644` or `100755`, then read that blob. Raise
   `runtime.CellRuntimeError` with git's stderr when either call exits
   non-zero.
2. Add `head_text(self, path: str) -> str | None` to the `Tree` protocol,
   and to `CellTree`, which calls the function above.
3. Give `constant_mutants` a fifth parameter, a callable from a path to its
   head text or `None`. `GateSuite._run` passes `tree.head_text`. In
   `_candidate_constants`, for each readable file outside the test paths,
   collect the new line numbers of its added lines over all its hunks.
   Skip a file with none, and a file whose head text is `None`. Search
   each pattern over the head text. Keep a match when an added line lies
   between the first and the last line it spans, both included. Its
   `find` spans from the match's start to the end of its `value` group.
   Its `replace` is that `find` with the `value` span replaced by the
   expanded template. `constant_mutants`' docstring promises `[]` and no
   raise in two cases (`saffron/gates/core/witness.py:485-486`). It gains
   a sentence saying a refused read raises out of the reader.
4. In `ConstantPattern`'s docstring, say two things. Text the pattern
   matches past `value` is the rest of the constant. An added line
   anywhere in the match derives the mutant.
5. Give `tests/test_suite.py`'s `_Tree` a `head_text` that returns `None`,
   and `tests/test_constant_mutants.py`'s `_GitTree` one that reads
   `git show HEAD:<path>`.

## Out of scope

- **A pure removal derives nothing.** A deleted line has no line at head,
  so a segment removed with no line added stays undetected. Narrowed here.
- **A witness's text stays hunk-bound.** `_witness_text` still reads only
  the hunks' new sides (`saffron/gates/core/witness.py:458`).
- **Hand edits in this spec's own pull request.** `DESIGN.md` §5.4.1 has
  a paragraph that opens "An edit the gate derives". It says core applies
  the patterns "to the diff as text". It becomes: to each changed file's
  text at head, counting a match the diff adds a line to. The setup
  skill's template comments on `constants` in one line
  (`.claude/skills/setup-saffron/templates/policy.yaml:37`). It gains the
  rest of the match after `value`. A cell cannot write under `.claude/`.
- **No `retired_first`.** The core change widens nothing under this
  repo's declared patterns. Each match there ends on its first value
  line, so its opening line already sits in any hunk an edit to it makes.
  Only the hand-edited pattern widens what `witness` derives. `SA-0415`,
  the one queued spec, adds `NEGATION_WORDS` with its opening line, so
  it derives that constant's mutant today as well.
- **Hand edit once this spec merges.** `.saffron/policy.yaml`'s
  `witness:` block takes the notes' string pattern in place of its first
  entry. Before the merge, the widened pattern searched over one hunk
  finds no triple-quoted constant whose closing quotes sit outside that
  hunk. So it lands after the code.

## Notes for the agent

**This change edits existing code, and its spelling is not forced.** The
new search text, the line test and the reader are written fresh. A
declared `find` that is absent fails the gate. So the ref holds no
mutant, and `witness` reports `skip` for these criteria. Each criterion's
`wrong_versions` carries what its witness must kill.

**The string pattern.** Replace the first `constants` entry's
`pattern` in `PATTERNS`, in `tests/test_constant_mutants.py`, and keep
its `replace`. That dict is Python, so write it with the existing
`_NAME` prefix and raw strings, as below. The existing pins there hold
unchanged, because each `find` still stops at `value`'s end. Fix the
comment above `PATTERNS` so it says this repo declares the same block by
hand once this spec merges.

```python
            "pattern": _NAME
            + r"\(?\s*(?P<value>[rbfuRBFU]{0,2}(?:(?P<t>\"\"\"|''')|\"|'))"
            + r"(?(t)[\s\S]*?(?P=t)).*(?:\n(?:[ \t]+\S|\)).*)*",
```

The same pattern in YAML spelling is the policy's hand edit, not the
test's. YAML doubles each single quote inside a single-quoted scalar.

```yaml
  - pattern: '(?m)^(?P<name>[A-Z][A-Z0-9_]*)(?:: [^=\n]+)? = \(?\s*(?P<value>[rbfuRBFU]{0,2}(?:(?P<t>\"\"\"|'''''')|\"|''))(?(t)[\s\S]*?(?P=t)).*(?:\n(?:[ \t]+\S|\)).*)*'
    replace: '\g<value>saffron constant mutant '
```

Past `value`, a triple-quoted string extends to its closing quotes. Every
spelling then takes the rest of that line. It also takes each next line
that starts with `)`, or with a space or tab before a visible character.

**What it spans on this tree.** At `fa96c212` it matches 184 constants.
For each one, its match ends on the value's last line as Python's `ast`
reads it. 136 are one line. 48 span more. That is 11
parenthesized concatenations, 17 parenthesized tuples, 2 parenthesized
sums and 18 triple-quoted strings. A backslash continuation occurs zero
times, so no witness drives it. A blank line or a column-0 comment inside
parentheses would end the span early. The tree holds neither.

**Criterion 1's fixture.** `prompts.py` at base opens with `def first()`
and a one-line body, then six blank lines, `LONG` and `AFTER = "after"`.
Then come `def long()` returning `LONG`, six blank lines, and `def
last()` with a one-line body. The head changes both one-line bodies and `LONG`'s fifth
string. Assert three `@@ ` lines in the diff, and that no hunk line is
`LONG = (` or `)`. Both witnesses are new in the head commit, so
`witness_body` finds them in the diff. Copy the environment pins and the
`tests` gate from the first test in that file.

**Criterion 2's fixture.** Write this module verbatim as `consts.py`. It
holds both quote kinds, so `_MODULE` cannot be one triple-quoted Python
string. Build it from a tuple of line strings. The test's table maps
each constant to its first and last line.

```python
FIRST = """
alpha
beta

gamma
delta
epsilon
zeta
"""
PAREN = (
    "one "
    "two "
    "three "
    "four "
    "five "
    "six "
    "seven "
    "eight"
)
ONE_LINE = "a" "b"
QUOTED = 'q' 'r'
TUPLE = (
    "t1",
    "t2",
    "t3",
    "t4",
    "t5",
    "t6",
    "t7",
    "t8",
)
LIMIT = 7

SINGLE = '''
one
two
three
'''
SUM = (
    "s1 "
    + ONE_LINE
)


def f():
    return FIRST
LAST = (
    "l1 "
    "l2 "
    "l3 "
    "l4 "
    "l5 "
    "l6 "
    "l7 "
    "l8"
)
```

The spans are `FIRST` 1 to 9, `PAREN` 10 to 19, `ONE_LINE` 20 and
`QUOTED` 21. Then `TUPLE` 22 to 31, `LIMIT` 32, `SINGLE` 34 to 38, `SUM`
39 to 42 and `LAST` 47 to 56. Lines 33, 43, 44, 45 and 46 derive nothing. Each `find` spans from the name through
the first opening quote, as `'PAREN = (\n    "'`, or is `LIMIT = 7` for
the integer. Each `replace` puts `saffron constant mutant ` after that
quote, or reads `LIMIT = (7 + 1)`. A trailing space on the opening line
of `PAREN`, `TUPLE`, `SUM` or `LAST` falls inside its `find`, after the
paren. On the other five openings it falls past the `find`.
The witness names all nine constants in one new test file, added in
each commit. Commit each edit and reset to base after, so each diff
holds one module line.

**The worktree witness.** Reuse `_exec_in` and `_commit` in
`tests/test_worktree.py`. Build the gitlink with `git update-index --add
--cacheinfo 160000,<sha>,sub`, and commit it without `_commit`, whose
`add -A` drops a gitlink with no checkout. `git show` exits 128 on a
gitlink, measured with git 2.54 on the host. The reader never calls it
there. On the cell image's git 2.47.3 `ls-tree` prints each fixture
path's mode as on the host, and prints nothing for `:odd.py` without
`--literal-pathspecs`. Drive two refusals. First stub `runtime.exec_` to
return exit 128 for every call. Then let a call holding `ls-tree` reach
`_exec_in`, and return 128 with its own stderr for any other call.
Assert each raise and that its message carries that stderr.

**Why not `read_at_head`.** `worktree.read_at_head`
(`saffron/cell/worktree.py:405-411`) reads a symlink's target as text,
and returns `None` on any refusal.

**Imports.** Import `constant_mutants` and `CellTree` inside each test
body, as the existing tests in these files do.

**The existing callers.** The three tests that call `constant_mutants`
over `_DIFF` need a reader. Give them a mapping from `a.py` and `b.py` to
text whose lines match `_DIFF`'s hunk numbering, since each hunk there
covers its whole file. Only `tests/test_finish.py:2955` drives a reader
that returns `None`, through `_Tree`, with this repo's own patterns.

**Cost.** Each file with an added line costs two git calls in the cell
when the repo declares patterns. A repo with none still returns before
any read.

**Size.** The prototype measured 321 changed tokens on `size_gate`
outside `tests/**`, and 1498 with the tests. The `bug` ceiling is 1300,
and `saffron/gates/**` is in `elevate_on`, so `size` blocks here.
`estimated_lines` is the first count over four.
