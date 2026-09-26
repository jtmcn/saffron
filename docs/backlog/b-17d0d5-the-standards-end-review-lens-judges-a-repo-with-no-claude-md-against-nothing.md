---
id: b-17d0d5
title: The Standards end-review lens runs over a repo with no `CLAUDE.md` and judges its diff against nothing
status: open
tier: 3
filed: 2026-09-26
specs: []
prs: []
commits: []
cites: [§6]
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 18, 2026-09-26, reviewing #526 (`SA-0146`).

`context.standing_instructions(None)` returns `""`. The Standards prompt still
says to judge the diff against the standing instructions below, over an empty
section. `saffron/agents/context.py:137-138` warns against exactly that
invitation. `SA-0153` was named to decide it and did not.

## Done looks like

- A repo with no `CLAUDE.md` skips the Standards lens, and its row says so.
- Or the prompt says the repo declares none, and a test covers the choice.

## Record

- 2026-09-26: filed from the spec loop's run 18 (stack #531).
