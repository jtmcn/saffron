---
id: 42
title: A rebuttal lost to a trailing comma is recorded as a confirmed disagreement
status: open
tier: 1
specs: [SA-0034, SA-0040, SA-0071]
prs: [93, 215]
commits: []
cites: []
related: [41]
---

## Problem

**Status: the visible half is done — `SA-0071`, PR #215, merged
2026-09-12.** The recording half is right only in `rebuttal.json`, and that is what stays
open. The ledger writes no rebuttal for an errored turn or for an unanswered
blocker, and `sustained_blockers` and `unkept_fixes` count both as zero. An
earlier version of this line said the queue's counts already told them apart,
and they do not (found reviewing `SA-0071`, 2026-09-11). Whether a malformed
rebuttal is worth a re-prompt also stays open here.

`phases/rebut.py:207` discards a rebuttal artifact that is not the schema and
returns `RebuttalTurn(error=...)`. That is deliberate, and the comment says
why: the plan checkpoint re-prompts once (`cell/session.py:404`) because a
rejected plan costs an attempt that has not happened yet, whereas *"this
attempt is already made, and HEAD already says what it did."*

`SA-0040` (PR #93) is the case where the second half of that sentence does not
hold. Measured 2026-09-01:

```
REBUT: 0 rebuttal(s), HEAD moved, not the schema: Illegal trailing comma
       before end of object: line 6 column 1116 (char 1186)
```

The turn cost $2.59, edited the branch, and conceded one of the two blockers —
`describe`'s `Baseline` branch was rewritten and a test added, and the critic's
re-read correctly marked that one `withdrawn`. Its *arguments* were what the
trailing comma destroyed. On the other blocker the critic then wrote
`confirmed: The implementer offered no argument and made no visible change`,
and that finding was false: the fixture digest it doubted is captured, not
typed, and mutating it fails the assertion at `tests/test_events.py:798`.
Nothing needed to change, and there was no surviving argument to say so.

So the operator inherits a pull request body asserting a confirmed
disagreement, founded on a lens finding that was itself founded on the
unrelated red baseline in item 41. "HEAD already says what it did" is true only
for a reader who re-reads the diff against every finding; the generated body
says the opposite, and the body is what gets read.

`SA-0034` (plan Task 6) is the natural home for the *recording* half — it is
already a bug spec about a rebuttal outcome that is not written down — but its
`forbidden` list excludes `saffron/report/**`, and no spec in part 3 touches
`pr_body.py` either. The visible half has no home in that plan yet.

Done looks like the artifact's *shape* failure not being silently equivalent to
the agent having no answer. Cheapest honest fix is not a re-prompt: it is that a
`RebuttalTurn` carrying `error` renders in the pull request body as
**"the rebuttal was unreadable"** rather than as an implementer who declined to
argue, and that `HEAD moved` — already recorded in `rebuttal.json` — is shown
next to it. Whether a malformed rebuttal is also worth one re-prompt is a
separate question from whether the record should imply an answer that was never
read.
