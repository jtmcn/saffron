---
id: 99
title: '`CLAUDE.md` and the spec-loop skill call marking a draft ready "ratifying" it'
status: open
tier: 3
specs: []
prs: []
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

**Done looks like** `CLAUDE.md` and the driver saying "mark ready", and the skill's
quoted output regenerated to match — or, if that act turns out to carry a judgement
worth a word, an entry under `CONTEXT.md`'s open naming decisions rather than a
third sense arriving in prose.
