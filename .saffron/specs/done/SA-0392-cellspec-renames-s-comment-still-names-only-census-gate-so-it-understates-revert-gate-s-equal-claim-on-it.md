---
id: SA-0392
title: "`CellSpec.renames`'s comment still names only `census_gate`, so it understates `revert_gate`'s equal claim on it"
type: bug
priority: 4
risk: elevated
estimated_lines: 27
estimate_measured: true
touches:
  - saffron/cell/session.py
  - tests/test_suite.py
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
  - records/**
  - hooks/**
  - harness/**
  - saffron/gates/**
  - saffron/intake.py
  - saffron/cli.py
  - saffron/task.py
  - saffron/phases/**
  - saffron/report/**
  - saffron/finish.py
  - saffron/regate.py
  - saffron/batch.py
  - tests/test_revert.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_census.py
  - tests/test_regate.py
budget_usd: 10
max_attempts: 2
max_turns: 30
acceptance:
  - claim: >-
      `saffron/cell/session.py:375-376`'s comment above `CellSpec.renames`
      reads "`intake.Spec.renames`, read by `census_gate` through the
      suite's `SuiteSpec` protocol (`SA-0387`). Empty where the spec
      declares none." It names one consumer. `SA-0389`
      (`e2b2a0b0`) gave `GateSuite._run` a second: `revert_gate`, handed
      `spec.renames` at `saffron/gates/suite.py:202`, the same keyword
      `census_gate` is handed at `saffron/gates/suite.py:234`. Rewrite the
      comment to name both gates by their literal names, still citing
      `SA-0387`, and now `SA-0389` too. Change no other line of the class.
      The witness reads `saffron/cell/session.py`'s own source at import
      time, finds the line assigning `renames: dict[str, str] =
      field(default_factory=dict)`, and walks backward from it collecting
      every contiguous line immediately above that starts with `#`. It
      asserts the literal substrings `census_gate` and `revert_gate` both
      sit inside that collected run. A comment that drops either name, that
      names neither by a vaguer phrase, that is deleted outright, or that
      sits somewhere else in the file instead of directly above the field,
      fails one of the two assertions or leaves the collected run empty.
    witness: tests/test_suite.py::test_cellspecs_renames_comment_names_both_its_readers
    wrong_versions:
      - "The comment is left exactly as it reads at base, naming only `census_gate`."
      - "The comment is rewritten to name only `revert_gate`, dropping `census_gate` entirely."
      - "The comment is replaced with `read by every gate the suite declares`, naming neither gate by its literal name."
      - "The comment is deleted outright, leaving the field with no line above it."
      - "The fix is written above `declared_risk` or another field instead of directly above `renames`."
      - "The comment is split so one gate's name sits on a line that does not start with `#`, falling outside the collected run."
---

## Context

Finding filed against `SA-0389` (#1200), which `revert_gate`'s cell closed
at `e2b2a0b000aabf17c1e3fd7ace017f026d15cf98`. The finding reads, in full:

> `saffron/cell/session.py:375`: This comment says `CellSpec.renames` is
> read by `census_gate` through the suite's `SuiteSpec` protocol. After
> this diff, `GateSuite._run` also hands `spec.renames` straight to
> `revert_gate` (`saffron/gates/suite.py:202`). The comment now
> understates who consumes this field. No gate checks this, since the
> gate set only judges format, lint, types and tests. A future reader
> relying on the comment to gauge the blast radius of changing `renames`
> would miss `revert_gate`'s now-equal dependence on it.

Every line number below was read at `241b6fbc57d924f2ec8a8f407de28224eb954f55`,
the current head of this stack.

**The stale comment.** `CellSpec.renames` (`saffron/cell/session.py:377`)
carries the comment at `:375-376`:

```
# `intake.Spec.renames`, read by `census_gate` through the suite's
# `SuiteSpec` protocol (`SA-0387`). Empty where the spec declares none.
```

It names `census_gate` and cites `SA-0387`, the spec that added `renames`
and its first consumer. It was accurate then: at that point `census_gate`
was the field's only reader, through `GateSuite._run`'s call at what is
now `saffron/gates/suite.py:234`.

**The second reader.** `SA-0389` added a second keyword at
`saffron/gates/suite.py:202`, inside the same `GateSuite._run`: `revert_gate`
is now called with `renames=spec.renames`, the identical expression
`census_gate` receives seven lines later at `:234`. The two calls read the
same field off the same `spec` object, through the same `SuiteSpec`
protocol method (`saffron/gates/suite.py:54`) `CellSpec.renames` already
cites. Neither call reads a copy or a derived mapping. Both reads are
the field itself.

**Why no gate catches the drift.** The repo's declared gates judge
`format`, `lint`, `types` and `tests` (and the others this spec's own
gate set lists). None of them reads a comment's prose against the code
it sits beside. A comment naming the wrong set of callers compiles,
type-checks and passes every test exactly as the correct one would.
Such a comment needs a reader, or a test built to pin its words. That
keeps it accurate past the next change to its field's callers.

## Problem

Rewrite the comment at `saffron/cell/session.py:375-376` to name both
readers `GateSuite._run` hands `spec.renames` to, `census_gate` and
`revert_gate`. Cite both specs that gave it a reader, `SA-0387` and
`SA-0389`. Change nothing else in `saffron/cell/session.py`: the field's
type, its default, and every other field's comment stay as they are.

Add one witness to `tests/test_suite.py`. It reads the comment back out
of the module's own source file, and pins both names inside it. A future
change that adds or drops a reader without updating this comment then
fails a test rather than waiting on a second finding.

## Out of scope

- **`saffron/gates/suite.py`'s own comments.** The suite's two call sites
  already name their own gate by the function they call. Neither needs a
  rewrite.
- **If `intake.Spec.renames`'s own docstring names readers too, that
  docstring is untouched here.** This finding cites only `CellSpec`'s
  copy of the comment.
- **A gate that reads comments against code.** Backlog item b-d2b6b3
  raises the same gap. No such gate exists in this repo, and building
  one is a separate change this spec does not ask for.
- **A further reader of `renames`.** Neither `revert_gate` nor
  `census_gate` passes the field on today. If a later change adds
  another reader, that change updates this comment too, the way this one
  does for `SA-0389`.

## Notes for the agent

**The witness is new code with no mutant**, so `witness` reports `skip`.
At base it fails on its second assertion: the comment holds `census_gate`
but not `revert_gate`. Use `Path(session_module.__file__).read_text()` to
read the live source. Import `saffron.cell.session` as a local name
inside the test function. Match the style already used by
`test_the_suite_hands_census_the_specs_own_renames` and
`test_the_suite_hands_revert_the_specs_own_renames`, both above it in the
same file. `Path` is already imported at module scope.

**Walk backward from the field's assignment line.** Match it by its
exact text, `renames: dict[str, str] = field(default_factory=dict)`.
Collect every line immediately above it that starts with `#` after
stripping leading whitespace. Stop at the first line that does not. Join
the collected lines and assert both literal substrings sit inside the
join.
This is robust to the comment's exact wrapping across two or three
lines, but not to it moving away from directly above the field.

**Prose.** Keep every sentence in the new comment to 25 words or fewer.
Keep every line to 88 characters or fewer. Use no em dash, no semicolon,
no contraction and no perfect tense, matching the comment it replaces.
The new witness's docstring is held to the same rules.

**Size.** This is a two-line comment edit and one new test. It measures
27 changed lines and under 300 changed tokens outside the frontmatter,
far under the `bug` ceiling of 1300 tokens. `saffron/cell/session.py`
sits under `saffron/cell/**`, one of the paths that raises this spec's
risk tier on its own. So `risk: elevated` is declared to match. The size
gate applies at the `bug` ceiling regardless.
