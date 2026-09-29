---
id: b-78ccc7
title: The conventions lens prompt asks nothing that finds what the Standards seat caught in run 21
status: open
tier: 2
filed: 2026-09-29
closed:
specs: []
prs: []
commits: []
cites: [§5.5, §5.6]
related: [b-abeb74, 162, b-17d0d5, b-5b1f8a, b-66d1c3]
---

## Problem

Found in the spec loop's run 21, 2026-09-29, by the Standards seat on #580
(`SA-0191`) and #581 (`SA-0192`). This is ADR 8 evidence by reading only. The
lens ran live in no cell.

`saffron/agents/prompts/review-conventions.md` misses these.

- **Text made stale elsewhere.** It asks its four questions of every hunk.
  `SA-0191` left "3 lenses = 7 turns" at `tests/test_session.py:6103` and
  `:6273`, lines no hunk touched. The Standards seat filed it as a blocker.
- **The `_Avoid_` lists.** `saffron/agents/context.py:38-41` strips them from
  the vocabulary the lens reads (item 162).
- **The spec's own directives.** It never reads the spec.
- **Message and prompt strings.** Its remit names comments, docstrings and
  citations. `SA-0192`'s "no CLAUDE.md stood" string was false for a blank
  `CLAUDE.md`, and the remit does not reach it.
- **One source against a witness.** Its "One source" question calls a restated
  constant a finding. Read literally, it pushes a witness to import the
  constant it tests (item b-5b1f8a).

Two neighbours differ from the remit.

- The other three prompts say "a constant or helper restated rather than
  imported" (`review-correctness.md:59`, `review-contract.md:64`,
  `review-adequacy.md:80`). The remit says "a type, constant or helper"
  (`review-conventions.md:34`).
- REBUT's verdict prompt for a conventions blocker gets an empty
  standing-instructions section (`saffron/phases/rebut.py:280`). Item b-17d0d5
  holds the lens prompt's half of that, and not the verdict prompt's.

## Done looks like

The prompt asks for any comment, docstring, count or string elsewhere that the
change makes false. It shows the `_Avoid_` lists, or names the terms they rule
out. A witness is exempt from "One source" for the value it pins. The three
bullets say "a type, constant or helper". The verdict prompt carries the
standing instructions. Each change is scored against the fixture ADR 8's
measured pass builds (item b-abeb74).

## Record

- 2026-09-29: filed from the spec loop's run 21.
