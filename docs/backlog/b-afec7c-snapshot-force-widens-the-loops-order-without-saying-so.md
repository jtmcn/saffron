---
id: b-afec7c
title: '`snapshot --force` widens the loop''s order without saying so'
status: done
closed: 2026-09-18
tier: 2
filed: 2026-09-18
specs: []
prs: [346]
commits: []
cites: []
related: [157, 172]
---

## Problem

Found in the spec loop's run 7, 2026-09-18.

The operator scoped the loop to five specs. The first snapshot refused `SA-0101`
and `SA-0102` on an unmet `depends_on`. `SA-0101` depends on `SA-0099`, and
`SA-0102` on `SA-0101`.

After a spec edit merged, `driver.py snapshot --force` re-scanned. `SA-0099`
had reached `READY_FOR_REVIEW` by then, so both specs were admitted. The output
listed them in the order with no line saying they were new. `next` then named
`SA-0101`, which had no step-1b spec review. The operator dropped both by hand.

`cmd_snapshot` in `.claude/skills/run-saffron-spec-loop/driver.py:813` prints
the order it saved and nothing about how it differs from the previous one.

## Done looks like

`snapshot --force` names each spec it adds to the loop's previous order. It
keeps new specs out unless the operator asks for them, for example with a flag.
A spec added that way still needs its spec review before `next` names it.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced while stacking #340.
- 2026-09-18: done by #346. `snapshot --force` names each spec that became
  runnable since the last snapshot and leaves it out unless `--add`.
  `--add SA-NNNN` takes one spec at a time. Its step 1b review is the operator's
  to run first: `next` does not check that a review happened.
