---
id: SA-0391
title: "The rename witness never pins the mike pair's bare new name, so a startswith widening of the new-name match survives it"
type: bug
priority: 3
estimated_lines: 1
estimate_measured: true
touches:
  - tests/test_revert.py
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
  - tests/test_suite.py
  - tests/test_task.py
budget_usd: 15
max_attempts: 3
max_turns: 60
acceptance:
  - claim: >-
      `test_revert_leaves_out_exactly_the_declared_renames_census_accepts`
      declares the pair `t.py::test_mike_old` renamed to the bare
      `t.py::test_mike`, with only `t.py::test_mike[1]` collected at head.
      Its `not_left_out` list names `t.py::test_mike[1]`, so the test
      checks that collected name is absent from `result.summary`. It names
      no check for the bare string `t.py::test_mike` itself, the literal
      new name the pair declares. Add that literal string to
      `not_left_out`, changing no other line. The widened loop then
      asserts `t.py::test_mike` is absent from `result.summary` too,
      alongside every name the list already names. The test passes
      unchanged today, since `accepted_renames` matches a new name against
      `after_set` by equality, and `t.py::test_mike` is never itself
      collected.
    witness: tests/test_revert.py::test_revert_leaves_out_exactly_the_declared_renames_census_accepts
    preserves: true
    wrong_versions:
      - A build where `accepted_renames` matches a declared new name against a head-collected name by a prefix or `startswith` test rather than whole-string equality, so the mike pair is wrongly accepted and its bare new name, never itself collected at head, joins the note's declared-rename clause as if it had been.
---

## Context

`SA-0389`'s host review, read at
`24e15721a03b120f3ba3d6fb940dd5e6177ab88d`, pinned a hole in the witness
that spec's own cell landed. `b-d2b6b3` is the backlog record behind
`SA-0389`. At the current head
`241b6fbc57d924f2ec8a8f407de28224eb954f55`, `revert_gate`'s
`accepted_renames` set (`saffron/gates/core/revert.py:268-274`) matches a
declared new name against `after_set` by equality. Line 273
(`saffron/gates/core/revert.py:273`) never matches by a prefix or a
`startswith` test. `renamed_out` (`saffron/gates/core/revert.py:281`)
names every accepted new name the criteria union left out. A non-empty
`renamed_out` joins `note` as a "declared rename(s)" clause
(`saffron/gates/core/revert.py:301-302`), and `note` rides every `pass`
and `fail` summary (`saffron/gates/core/revert.py:635`).

The witness
`test_revert_leaves_out_exactly_the_declared_renames_census_accepts`
(`tests/test_revert.py:2032`) declares one pair to check this directly.
`t.py::test_mike_old` renames to `t.py::test_mike`
(`tests/test_revert.py:2065`), so a new name which is only a prefix of a
head-collected id must stay rejected. Only `t.py::test_mike[1]` is
collected at head (`tests/test_revert.py:2096`), never the bare
`t.py::test_mike`. The witness's `not_left_out` list
(`tests/test_revert.py:2143-2154`) feeds a loop
(`tests/test_revert.py:2155-2156`) that asserts each named string is
absent from `result.summary`. The list names `t.py::test_mike[1]`
(`tests/test_revert.py:2150`), the real collected name, which no correct
or widened match ever places in `note`. It names no entry for the bare
`t.py::test_mike`, the literal string a widened match would place there
instead.

A build that widens line 273's equality to a `startswith` test over
`after_set` accepts the mike pair, because `t.py::test_mike[1]` starts
with `t.py::test_mike`. The accepted value is the literal string
`t.py::test_mike`, never itself collected. Subtracting that string from
`new_only` is a no-op. The subset handed to `run_tests`, and every
assertion the witness already makes about that subset, stay the same
either way. `renamed_out` still gains the literal `t.py::test_mike`, so
it joins the "declared rename(s)" clause. `result.summary` then carries
a new name the rule never collected at head, the defect `SA-0389`'s own
wrong version for this criterion names. The present witness never checks
for that literal string, so it passes this wrong build silently.

## Problem

In `tests/test_revert.py`, add the literal string `t.py::test_mike` to
the `not_left_out` list inside
`test_revert_leaves_out_exactly_the_declared_renames_census_accepts`.
Change no other line of the test, and no production file. The loop over
`not_left_out` already asserts the same absence for every other name on
the list. It now asserts it for `t.py::test_mike` too.

## Out of scope

- **Every other wrong version `SA-0389`'s spec already lists for this
  criterion.** The host review named only the one above as unobserved by
  the present witness. A change to the list beyond the one line this
  spec asks for is not this spec's concern.
- **The symmetric widening on the old-name side.** Line 271
  (`saffron/gates/core/revert.py:271`) matches the old name against
  `before_set` the same way. A build that widens it the same way already
  fails the witness, through `t.py::test_lima`, already named in
  `not_left_out`.

## Notes for the agent

**The production code is correct already.** `saffron/gates/core/revert.py`
stays untouched. Only the witness gains a name it was missing.

**Why the criterion is `preserves`.** The test, as it stands today,
already passes against today's correct `revert_gate`, with or without
the added line: the added assertion checks for a string `note` never
holds, on either side of this spec's own edit. So the witness is green
before this cell's diff and green after it, the shape `preserves`
criteria are checked by. It is not a witness that only turns green once
the cell lands. `witness` declares no mutant here, so it reports `skip`.
The wrong version above describes the production edit this witness would
have to catch once one is attached.

**Size.** The change is one list entry inside one existing test, measured
at one changed line outside production code, far under the `bug`
ceiling.
