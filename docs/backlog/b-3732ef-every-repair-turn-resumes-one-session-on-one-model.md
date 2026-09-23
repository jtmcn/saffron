---
id: b-3732ef
title: Every repair turn resumes the implementer's session on the default model, and the ledger cannot say which model ran
status: open
tier: 3
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: ["§5.4"]
related: [b-e1afbb]
---

## Problem

Filed 2026-09-21 from a comparison of Saffron with the superpowers
executor's fix loop.

**One session carries every attempt.** `_repair` resumes the implementer's
session on each attempt (`saffron/cell/session.py:2076`).
`implement.agent_options` takes no model (`saffron/phases/implement.py:94`),
so every turn runs on the SDK's default.

**The superpowers executor changes both on late rounds.** Rounds 1 to 3
resume the implementer. Rounds 4 and 5 start a fresh implementer on a
stronger model, with the findings and a report of what was tried. Its reason:
a loop that survives three resumes usually means the implementer cannot see
its own problem. That is a reasoned claim, not a measured one.

**Saffron cannot measure it yet.** `_close_attempt` writes `model=None`,
because the runner's result event carries no model
(`saffron/cell/session.py:222`).

## Done looks like

The ledger records the model of every attempt. Then a measurement reruns
`EXHAUSTED` tasks under a variant. From attempt 3 onward, the variant starts
a fresh session on a stronger model with the new failures and the prior diff.
The variant ships only if it turns more tasks green per dollar.

## Record

- 2026-09-21: filed. Recording the model can go through a cell. The
  comparison spends real money on live runs, so it runs by hand from
  `docs/evidence/scripts/`.
