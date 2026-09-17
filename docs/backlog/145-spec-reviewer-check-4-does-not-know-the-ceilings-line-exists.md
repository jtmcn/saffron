---
id: 145
title: The spec review's check 4 still says to compare ceilings by eye, and does not know the line that does it now exists
status: done
tier: 1
filed: 2026-09-16
closed: 2026-09-16
by_hand: true
specs: [SA-0092]
prs: [279, 287]
commits: []
cites: []
related: [123, 124, 144]
---

## Problem

**Tier 1.** By hand: `.claude/**` is `forbidden` to `SA-0092`, which is what
built the line.

`SA-0092` exists because check 4 — ceilings against history — read the rows wrong
in both directions, missing every recorded ceilings defect and raising two
blockers the cells contradicted. Its answer is a `ceilings:` line that does the
comparison in code: the max peak among the rows *it printed*, the max pre-REVIEW
spend, the direction and magnitude against each declared ceiling, and a cut-off
row's peak called a floor rather than a use.

`.claude/agents/spec-reviewer.md` check 4 still tells the model to do all of that
by eye, and does not mention the line. Until the prompt points at it, the line is
computed and ignored — the work is done and the reader is still guessing.

This is the by-hand half of item 123, and it is the whole payoff of `SA-0092`.

## Done looks like

Check 4 rewritten to read the `ceilings:` line as its input — quote it, and
report the check against what it says — with the by-eye instruction removed so
the two cannot disagree.

## Record

**Filed 2026-09-16** from the spec loop's run of that day (stack #285).

**2026-09-16, a fix is open as PR #287.** Check 4 reads the `ceilings:` line instead of comparing by eye. It stays `open` until that merges.

**2026-09-16, done.** PR #287 merged (`1f64a99`). Check 4 in
`.claude/agents/spec-reviewer.md` reads `history`'s `ceilings:` line and says
not to redo it by eye. Closed 2026-09-16 on review of the backlog: #287 wrote this record's "stays `open` until that merges" line itself, so the line could only land by the merge that should have closed it.
