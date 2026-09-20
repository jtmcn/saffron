---
id: b-b69bb6
title: A spec's line citations and the directories it adds files to are checked by eye, and both are computable
status: open
tier: 2
filed: 2026-09-20
specs: [SA-0114]
prs: []
commits: []
cites: []
related: [b-281f0a, 130, b-865399]
---

## Problem

Filed 2026-09-20 from one spec taken end to end outside a loop run. `SA-0113`
was drafted by the `spec-writer` agent, read by `spec-reviewer`, revised, and
read again by a second reviewer. Branch `joel/spec-criterion-mutation`.

Three of the first review's six findings needed no judgement.

- The blocker. The spec added a file to `saffron/agents/prompts/turns/`, and
  `tests/test_context.py:383` globs that directory and compares it to a
  hand-written list of nine names. The test passes at base, so baseline
  subtraction does not absolve it, and the blocking `tests` gate fails every
  attempt. The file sat in `forbidden`, so the cell could not repair it.
- Two notes of citation drift. `saffron/agents/findings.py:41` was cited for a
  line that sits at `:42`, and `saffron/phases/review.py:413` for a helper
  ending at `:411`.

The second review then spent one of its six checks confirming by hand that
every citation resolves. Runs 8, 9 and 10 each recorded stale line numbers in
every spec they carried.

Both questions are computable. Resolve each `file:line` the spec quotes against
the base commit and report the ones that moved. For each directory the spec
adds a file to, find the tests that glob, iterate or enumerate it.

What the rounds cost, measured on this spec: the draft 35.7 minutes, the first
review 6.2, the revision 17.9, the second review 9.5.

## Done looks like

A command takes a spec path and a base commit. It prints the citations that no
longer say what the spec quotes, and the tests that enumerate a directory the
spec adds a file to. The `spec-writer` agent runs it before its own
self-review. The `spec-reviewer` agent's checks 2 and 6 then read its output in
place of deriving both by hand.

## Record

- 2026-09-20: filed from `SA-0113`'s two reviews. `SA-0092` and `SA-0112` are
  the precedent for the shape: a cell builds the command, and the prompt that
  reads it is a hand edit.
- 2026-09-20: where the command lives is open. `records/` is this repo's
  project-document package, "backlog items today, specs next", and item 170
  builds `saffron/record/` for the run record. The two names stand, settled
  with the session building 170, and a `CONTEXT.md` §8 entry separates them.
  `records/load.py:48` also holds a class `Record`, which the run record's
  protocol repeats.
- 2026-09-20: `SA-0114` is queued for the command. It goes in the spec loop's
  `.claude/skills/run-saffron-spec-loop/driver.py`, beside `check`, as
  `driver.py cite <spec-path> --base <commit>`. `records/` was the other
  candidate and is declined. It parses record frontmatter and reads no commit,
  where the driver already reads a tree at one (`_git`, `_spec_at`). `dead`'s
  roots cover `records/` and not `.claude/`. The prose half stays
  open here, as item `b-281f0a` left its own: the `spec-writer` agent running
  the command, and checks 2 and 6 reading its output, are by-hand edits after
  the cell lands.
