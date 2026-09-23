---
id: b-cd4de2
title: The spec loop numbers its passes as runs, and run is a ledger term
status: open
filed: 2026-09-22
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found 2026-09-22 in the review of PR #477, which gave the spec loop a
`CONTEXT.md` entry.

**Run** is one task's pin in the ledger. The glossary says run is reused only
as the qualified **scoring run**. The spec loop numbers each of its passes as a
bare run all the same. `run-saffron-spec-loop/SKILL.md`, `GOTCHAS.md`,
`REVIEW-PROMPT.md`, `driver.py`, `delegate.md`, `spec-writer.md` and many
backlog records write "run 11". The feedback files are named
`docs/evidence/<date>-spec-loop-skill-feedback-run-<N>.md`.

A grep for "run" followed by a number, `run-NN` or `run <N>` over `.claude/` and
`docs/` matched 343 lines in 137 files on 2026-09-22. That count includes some
unrelated phrases.

PR #477 first listed bare "run" under the spec loop's `_Avoid_`. It named no
word to use instead, so the review took that line out. The collision is older
than the entry.

## Done looks like

One of the two is made true, and `CONTEXT.md` says which:

- A spec loop pass gets a name of its own, such as "spec loop 13". The skill,
  the agent files, `docs/agents/` and the driver use it from then on. Closed
  records and existing evidence file names keep the old wording as history.
- Or "spec loop run" joins **scoring run** as a qualified reuse. The note under
  **Review round** then names three qualified runs, and bare "run N" in
  forward-facing files gains the qualifier.

## Record

**Filed 2026-09-22** from the code review of PR #477.
