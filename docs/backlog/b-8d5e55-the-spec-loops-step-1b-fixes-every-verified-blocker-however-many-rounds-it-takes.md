---
id: b-8d5e55
title: The spec loop's step 1b fixes every verified blocker however many rounds it takes, and the operator ruled otherwise
status: open
tier: 2
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: []
related: [b-a4df62, b-250dc7]
---

## Problem

Four decisions from the spec loop's run 11, 2026-09-20 and 2026-09-21, are not
in `.claude/skills/run-saffron-spec-loop/SKILL.md`.

1. The delegate resolves a verified blocker that is neither architectural nor
   critical without asking.
2. From a spec's fourth pre-cell review round, a blocker that would change what
   the cell builds is fixed in the spec. A blocker that only strengthens a
   witness goes to that pull request's review.
3. When the review rounds concentrate in one criterion and the size climbs toward
   the turn ceiling, that criterion is split out.
4. Every loop ends with an HTML report (item b-0de0b3).

The evidence. Every blocker in the run was one family, item b-250dc7.

- `SA-0114` took five rounds and five blockers.
- `SA-0115` took six rounds and thirteen blockers, then a split.
- `SA-0116` took five rounds and four blockers.
- After each cell, the pull request's review fixed the remaining witness holes on
  the branch in one commit.

One more fact the skill does not say: a review commit on a parent moves the line
numbers its children cite. An import added at the top moves every line below it.

## Done looks like

`SKILL.md` step 1b carries these rules, and the delegate reads them there, not
from memory.

## Record

- 2026-09-21: filed from the spec loop's run 11.
