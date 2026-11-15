---
id: SA-0397
title: "The inert-edit witness names every `None` case's own category, and a note no gate reads still keeps CLAUDE.md's sentence limit"
type: bug
priority: 4
risk: standard
estimated_lines: 70
estimate_measured: true
touches:
  - tests/test_probe_check.py
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
  - saffron/**
  - tests/test_constant_mutants.py
  - tests/test_integrity.py
  - tests/test_mirror.py
  - tests/test_package.py
  - tests/test_review.py
  - tests/test_session.py
  - tests/test_suite.py
  - tests/test_worktree.py
budget_usd: 18
max_attempts: 2
max_turns: 60
acceptance:
  - claim: >-
      `tests/test_probe_check.py:794` builds one flat `none` dict handed to
      `inert_edit`'s refusal loop, and `tests/test_probe_check.py:905`
      checks only `len(none) == 21`. No grouping in the file ties that
      count to the breakdown `SA-0395`'s acceptance criterion declares:
      three bound-name cases, six unmatched-line cases, three
      adopted-line cases, three find-rule cases and one no-pattern case,
      sixteen in all. Five more cases, added later by that spec's own
      review commit at `tests/test_probe_check.py:873-896`, sit inside
      that same flat dict, named by nothing but their own keys: a call
      before the find, a def and pass before an indented find, and three
      cases where a find ends, starts or opens mid-line. The dict instead
      splits into six named dicts, `none_bound_name`,
      `none_unmatched_line`, `none_adopts_kept_line`, `none_find_rule`,
      `none_splits_kept_line` and `none_no_patterns`, merged into `none`
      for the existing refusal loop. Each dict's own `len` is asserted
      before the merge, as 3, 6, 3, 3, 5 and 1. The file then states the
      breakdown its own structure holds, and a case moved to the wrong
      group fails that group's own assertion.
    witness: tests/test_probe_check.py::test_an_edit_that_keeps_its_find_and_adds_only_inert_lines_is_refused
    preserves: true
    wrong_versions:
      - "Two of the five split-guard cases, 'a call before the find' and 'a def and pass added before an indented find', kept inside none_find_rule's own dict literal, so that group holds five entries and none_splits_kept_line holds three."
      - "'a find not held whole in the replace' moved into none_splits_kept_line's own dict literal instead of none_find_rule's, so the find-rule group holds two entries and the split-guard group holds six."
      - "'a call default' moved into none_adopts_kept_line's own dict literal instead of none_unmatched_line's, so that group holds four entries and none_unmatched_line holds five."
  - claim: >-
      `tests/test_probe_check.py:725` holds a bare string statement,
      directly below `INERT_PATTERNS`'s closing paren at
      `tests/test_probe_check.py:724`. `.saffron/gates/prose.py:275`'s
      `_documented` walks a parsed module for `ast.Module`,
      `ast.FunctionDef`, `ast.AsyncFunctionDef` and `ast.ClassDef` nodes
      only (`.saffron/gates/prose.py:272`), and keeps a node only where
      `ast.get_docstring` finds one (`.saffron/gates/prose.py:282-286`).
      A bare statement following an assignment is none of those, so
      `_python_prose` never reads its text and the `prose` gate never
      sees it. Its second sentence, at `tests/test_probe_check.py:726`,
      runs twenty-six words long, and `CLAUDE.md:238` states the limit
      for new comments as twenty-five. The note's sentences are reworded
      so each stays within that limit, with its meaning unchanged. A new
      test reads the note from this file's own source with `ast.parse`
      and asserts every one of its sentences stays within the limit by
      hand, so a later rewrite that grows one past it fails here instead
      of passing unseen.
    witness: tests/test_probe_check.py::test_the_inert_patterns_note_obeys_claude_mds_sentence_limit_by_hand
    wrong_versions:
      - "The note left at its base wording, twenty-six words in its second sentence, so the new test's own word count assertion sees 26 and fails."
      - "The note split after its first clause instead of after its third shape, so the back half still reads thirty-three words and fails the same assertion."
---
## Context

Backlog record `b-7fc792`, continued by both `SA-0395` and `SA-0396`.
Both findings below were read at `677f32f9`, the head of this stack.

**The breakdown no longer matches the dict.** `SA-0395`'s acceptance
criterion says its witness "drives sixteen edits that return `None`".
It names three bound-name cases, six unmatched-line cases, three
adopted-line cases, three find-rule cases and one no-pattern case. That
spec's own review commit then widened the guard so an added side cannot
split a kept line either. It added five more cases to the same test, at
`tests/test_probe_check.py:873-896`: a call before the find, a def and
pass before an indented find, and three cases where a find ends, starts
or opens mid-line. The flat `none` dict at `tests/test_probe_check.py:794`
now holds all twenty-one, and the single assertion at
`tests/test_probe_check.py:905` only checks the total. A reader who
checks the acceptance criterion against the dict finds a count that
disagrees with the prose. No comment anywhere names the five cases the
prose leaves out.

**A convention the gate cannot reach here.** `tests/test_probe_check.py:725`
holds a bare string statement, directly below `INERT_PATTERNS`'s closing
paren at `tests/test_probe_check.py:724`. `.saffron/gates/prose.py:275`'s
`_documented` walks a parsed module for `ast.Module`, `ast.FunctionDef`,
`ast.AsyncFunctionDef` and `ast.ClassDef` nodes only
(`.saffron/gates/prose.py:272`), and keeps a node only where
`ast.get_docstring` finds one (`.saffron/gates/prose.py:282-286`). A bare
statement following an assignment is none of those, so `_python_prose`
never reads its text, and the `prose` gate never sees it. Its second
sentence, at `tests/test_probe_check.py:726`, runs twenty-six words long.
`CLAUDE.md:238` states the limit for new comments as twenty-five.

## Problem

Split the flat `none` dict at `tests/test_probe_check.py:794` into six
dicts, named `none_bound_name`, `none_unmatched_line`,
`none_adopts_kept_line`, `none_find_rule`, `none_splits_kept_line` and
`none_no_patterns`. Keep every case's key, `before`, edit and patterns
exactly as they stand today, moving each into the dict its own shape
names. Build `none` by merging the six, in that order, for the existing
refusal loop. Assert each dict's own length before the merge, 3, 6, 3, 3,
5 and 1, and keep the existing `assert len(none) == 21` after it.

Reword the note below `INERT_PATTERNS` so each of its sentences stays
within `CLAUDE.md:238`'s own limit. Keep its meaning: four shapes, a
`def`, a `pass`, a docstring and a comment, declared here so a change to
the repo's own patterns leaves the witness unmoved.

Add a small helper that reads this file's own source with `ast.parse`,
finds the bare statement that follows the `INERT_PATTERNS` assignment,
and returns its string. Add one test that splits that string into
sentences the same way `.saffron/gates/prose.py`'s own break pattern
would, and asserts each stays within the limit. The gate cannot check
this note on its own, so this test stands in for it by hand.

## Out of scope

- **Any other prose this stack grew.** This spec reads only the two
  findings above. A sentence elsewhere in `tests/test_probe_check.py`
  that the `prose` gate already does not flag is not this spec's to fix.
- **`saffron/probe.py` and `saffron/repos/policy.py`.** `inert_edit` and
  `ProbePatterns` behave correctly under every case the witness drives,
  at base and after this change. Neither file moves.
- **A general sentence-length check for every bare string statement in
  this repo.** The new test reads one specific note. A gate rule that
  finds every such statement is a later spec's to write. It would need to
  tell a stray string literal from one left as a note by hand.
- **Moving the note into a real docstring.** Turning it into a comment
  block would put it under the two-line comment limit instead. Shrinking
  four sentences of explanation to two lines loses more than this spec's
  findings ask it to fix.

## Notes for the agent

**One witness carries `preserves: true`.** The function it names already
exists in the tree, and it already passes today. This spec restructures
its body. It changes no edit the function refuses. Keep its node id, so
the rewritten body still reports under the name where the dict mismatch
surfaced.

**The other witness is wholly new.** At base,
`test_the_inert_patterns_note_obeys_claude_mds_sentence_limit_by_hand`
does not exist, so `witness` reports `skip` for that criterion.

**Keep every case's `before` and edit text unchanged.** Moving a case
into its named dict is a cut and paste, not a rewrite.
`none_splits_kept_line` holds five cases: the call before the find, the
def and pass before an indented find, and three mid-line or newline
cases. Keep them in the order they sit in today's flat dict.

**The new test reads its own file.** `Path(__file__).read_text()`, parsed
with `ast.parse`, gives a module whose body is a list of statements. That
list holds the `INERT_PATTERNS` assignment and the bare string right
after it. Walk the list in pairs, find the assignment by its target's
name, and read the next statement's constant value. Split that string on
a period or a colon followed by whitespace, with newlines read as spaces
first, and assert each piece's word count.

**The `prose` gate** counts every new comment and docstring this spec
adds to `tests/test_probe_check.py`, such as the one-line comments above
each new dict. Write none with an em dash, a semicolon, a contraction, a
hedge, the perfect tense or a sentence over twenty-five words.

**Size.** A prototype measured sixty-five inserted and five deleted lines
in `tests/test_probe_check.py`, about six hundred thirty changed tokens,
all of it test code.
