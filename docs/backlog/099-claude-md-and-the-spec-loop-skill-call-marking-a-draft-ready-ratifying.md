---
id: 99
title: '`CLAUDE.md` and the spec-loop skill call marking a draft ready "ratifying" it'
status: done
tier: 3
closed: 2026-09-17
by_hand: true
specs: []
prs: [322]
commits: []
cites: [§5.7]
related: []
---

## Problem

**Tier 3.** Found naming the delegate. `CONTEXT.md` §6 reserves **Ratify** for what
the operator does to a proposed `touches` set at `SCOPE_REVIEW`, and **Approve**
for what the operator does to a pull request in GitHub. `CLAUDE.md` ("ratifying one
means `gh pr ready <n>` before `gh pr merge`") and the spec-loop driver
(`.claude/skills/run-saffron-spec-loop/driver.py:472`, whose output `SKILL.md:241`
quotes) use it for `gh pr ready`, which
is neither: it lifts PACKAGE's draft (§5.7) into review. The retired-vocabulary
hook cannot see this — **ratify** is live vocabulary in the wrong sense, not a
retired word.

## Done looks like

`CLAUDE.md` and the driver saying "mark ready", and the skill's
quoted output regenerated to match — or, if that act turns out to carry a judgement
worth a word, an entry under `CONTEXT.md`'s open naming decisions rather than a
third sense arriving in prose.

## Record

**Closed 2026-09-17, by hand.** `CLAUDE.md`, `SKILL.md` and `driver.py` now say
"mark ready". The driver's line had moved to `:1140`, and `SKILL.md` no longer
quotes its output. The copies of the old line in `docs/evidence/fixtures/*/claude.md`
are frozen records and keep it.

Marking ready carries no judgement today. GitHub merges no draft, so it is the
step before `gh pr merge`, and the ledger never reads it: `reconcile._next_state`
reads `state` and `reviewDecision`, never `isDraft`. It could become the signal
for **Approve** once a merge train exists, which is `CONTEXT.md`'s open naming
decision 2 and item 52's record. The word would then be "approve", not "ratify".
