---
id: 70
title: A task lost to a provider error leaves the night reporting `DRAINED`, exit 0
status: done
tier: 1
closed: 2026-09-12
specs: [SA-0048, SA-0057, SA-0067]
prs: [136, 216]
commits: []
cites: [§4.2.1]
related: [65]
---

## Problem

**Status:** **done** — `SA-0067`, PR #216, merged 2026-09-12. A fifth
stop reason, `INCOMPLETE`: it outranks `DRAINED`, `BUDGET` and `UNTIL`, and
`INFRASTRUCTURE` outranks it. It exits 2 and leaves the breaker alone. **The
by-hand half is done:** the vocabulary, `CONTEXT.md`, §4.2.1, `batch.StopReason`
and the `CHECK` on `batches.status` landed together, because
`tests/ontology/test_vocabulary_agrees_with_code.py` holds the vocabulary, the
`Literal` and the `CHECK` equal, and `CONTEXT.md` and §4.2.1, which move with the
vocabulary, are `protected`. The `CHECK` needed a table rebuild
(`Ledger._widen_batch_status`), because `CREATE TABLE IF NOT EXISTS` leaves an
existing ledger's old `CHECK` in force. Measured before the rebuild existed: a
ledger with the old `CHECK` raised `IntegrityError` closing an `INCOMPLETE`
night. What is left is `SA-0067`'s: the loop returning the value, and the command
mapping it to exit 2.

**Tier 1.** Measured 2026-09-06, driving `SA-0057` — the first unattended run
in this repo to lose a task to something other than its own code.

The provider erred mid-response during REBUT. The agent exited 1 with no
output, and `run_one_cell` returned an outcome in state `REBUTTING`:

```
agent: API Error: Server error mid-response. The response above may be incomplete.
agent: success in 7 turns, $0.34 (api_error)
REBUT: the rebuttal moved no commit and made no argument
SA-0057    REBUTTING
batch: DRAINED
```

Exit `0`. $3.75 spent, no pull request, and a night an unattended caller
records as clean.

**Why.** `batch.ABORT_STATES` is `GATE_ERROR`, `PREFLIGHT_FAILED`,
`RATE_LIMITED`. `REBUTTING` is in none of them, so the breaker did not count
it — the loop treated it as a state the task *earned*, reset the consecutive
count, and drained. Nothing else looks: `run_batch` reads `outcome.state`
against two sets and neither describes "the task did not finish".

That is the shape this repo keeps finding and keeps having to name again — a
control that reads as success when the work did not happen. Appendix J is the
same shape in a cell, `SA-0048`'s token probe the same shape in preflight, and
this is it in the loop.

**What is *not* broken, and should be said before anyone fixes the wrong
half.** Recovery works, unaided. `REBUTTING` is in
`reconcile.IN_FLIGHT_STATES`, so the next batch scan stamps it `ORPHANED`;
`ORPHANED` is in `scheduler.REQUEUE_STATES`, so it requeues. Measured on the
very next run — `reconcile: task 52 -> ORPHANED`, re-run, `READY_FOR_REVIEW`,
PR #136. The machine healed itself. What it did not do is *say* that it had to,
or that the first attempt's $3.75 bought nothing.

**Done looks like** an in-flight terminal state being visible in how the night
ends. Three parts, and the third is the one to argue about:

- **The stop reason.** `DRAINED` means the queue emptied. A queue that emptied
  with a task left mid-phase is not the same night, and §4.2.1's four reasons
  have no word for it. Either a fifth reason or `INFRASTRUCTURE` — and note a
  fifth touches `factory:BatchStopReason`, `CONTEXT.md`, `factory:BatchShape`
  and the `CHECK` on `batches.status`, all of which item 65 made agree.
- **The exit code.** `0` is "the night made it". This one did not.
- **The breaker.** Less clear-cut. Counting every in-flight outcome as an abort
  would fire the breaker on two consecutive provider blips, ending a night that
  would have recovered on its third task. Counting none of them is what
  happened here. The honest answer may be that the breaker is right and only
  the reporting is wrong — resolve this deliberately rather than by editing
  `ABORT_STATES` because it is the nearest set to hand.

**Not** re-running inside the same night. The scan is resolved once, before the
loop, and that is what makes termination structural (`saffron/batch.py`). A
retry inside the loop reintroduces the "does the queue change" question the
`for` was written to avoid.
