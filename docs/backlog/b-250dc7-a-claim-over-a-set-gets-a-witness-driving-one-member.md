---
id: b-250dc7
title: A claim quantifying over a set keeps getting a witness that drives one member, and a first review keeps passing it
status: done
tier: 2
filed: 2026-09-20
closed: 2026-09-20
by_hand: true
specs: []
prs: [395]
commits: []
cites: []
related: [b-ea1d13, b-b69bb6, b-2750d5]
---

## Problem

Filed 2026-09-20 from three specs written and reviewed in one chain:
`SA-0113`, `SA-0114` and `SA-0115`. The same defect appeared in two of them,
five times over four criteria.

A criterion quantifies over a set. Its witness drives one member. A cell that
handles that one member passes, and the claim the pull request renders says
more than the code does.

- `SA-0114`, criterion 2: a bare line number anchors to a path named earlier,
  and the fixture cited only full `path:line` forms.
- `SA-0114`, criterion 4: the command finds tests that enumerate a directory,
  and the fixture drove `.glob` alone, so `rglob`, `iterdir` and `os.walk`
  went unread.
- `SA-0115`, criterion 2: three recursing forms named, one driven.
- `SA-0115`, criterion 2: a call counted by the name its file imported `os`
  under, with no fixture forcing an alias.
- `SA-0115`, criterion 3: two members, one driven, and the undriven one fires
  on every real invocation of the command.

Three of the five passed a first review, all three in `SA-0115`. Its second
review found them only after this session named the axis to read for. That
pass raised three blockers on a spec a first reviewer called runnable.
`SA-0114`'s own first review caught its two.

Nothing an author reads said otherwise. `docs/agents/issue-tracker.md`'s
Conventions carry the witness rules, and none of them asks whether a claim's
fixture covers the set the claim names.

## Done looks like

The authoring contract carries the rule, and a later chain produces a spec
whose reviews raise no finding of this shape. The check belongs to the author
rather than the reviewer. A reviewer reading for it costs a round, and the
author already holds both the claim and the fixture.

## Record

- 2026-09-20: filed and fixed in the same change, as a Conventions bullet in
  `docs/agents/issue-tracker.md`, beside the mutant and witness rules.
  `by_hand` because no cell can write there. It went first into
  `.claude/agents/spec-writer.md` and moved. The contract binds the writer by
  its own "Read first". The `spec-reviewer` agent reads the same Conventions
  as its own third Read-first item, and a person writing a spec by hand is
  bound too. A rule in the agent file alone reaches one of those three.
- 2026-09-20: whether the rule works is unmeasured. The evidence is five
  instances before it, and the next spec through the chain is the first test
  of it.
