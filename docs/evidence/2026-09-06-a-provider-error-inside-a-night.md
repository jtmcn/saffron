# What a provider error does to an unattended night

**Run:** `saffron batch --repo . --budget 18 --until 06:30`, 2026-09-06,
driving `SA-0057` against this repo. **Result:** `DRAINED`, exit `0`, $3.75
spent, no pull request, task left in `REBUTTING`.

The first unattended run here to lose a task to something other than its own
code. Recorded because the night reported success and the failure is only
visible in a state field.

## What happened

```
PLAN: accepted, sha256 c2dd82a9020d
IMPLEMENT: 1 commit(s), $1.46 spent
gates: attempt 1, 1 new failures -> repair
gates: attempt 2, 0 new failures -> green
REVIEW: adequacy: 1 blocker, 0 concern, 1 note
REVIEW: 1 blocker(s) — the implementer rebuts
agent: API Error: Server error mid-response. The response above may be incomplete.
agent: success in 7 turns, $0.34896779999999994 (api_error)
REBUT: 0 rebuttal(s), HEAD did not move, the agent exited 1 (success/api_error): no output
SA-0057    REBUTTING
batch: DRAINED
```

Everything up to REBUT worked, including a repair round. The provider erred
mid-response, the agent exited 1 having produced nothing, and the phase left
the task in an in-flight state.

## The ledger

```
batch 5   status DRAINED   spent 3.7454214   ended 2026-09-06 00:34:40
task 52   SA-0057   state REBUTTING   pr_url None
```

## Why the night called that a success

`batch.ABORT_STATES` is `{GATE_ERROR, PREFLIGHT_FAILED, RATE_LIMITED}`.
`REBUTTING` is in none of them, so `run_batch` read it as a state the task
*earned*, reset the consecutive-abort counter, and drained the queue. Nothing
downstream looks: the loop compares `outcome.state` against two sets and
neither of them describes "the task did not finish".

Measured:

```
REBUTTING in ABORT_STATES?   False
REBUTTING in REQUEUE_STATES? False
REBUTTING in IN_FLIGHT_STATES? True
```

## Recovery works, and nothing said it was needed

The third membership above is the one that saves it. `REBUTTING` is in
`reconcile.IN_FLIGHT_STATES`, so a batch scan — which asserts §4.2.1's
one-batch-at-a-time premise with `stamp_orphaned=True` — stamps it `ORPHANED`,
and `ORPHANED` *is* in `REQUEUE_STATES`.

Measured on the very next run, unaided:

```
reconcile: task 52 → ORPHANED
batch: 1 candidate(s), budget $18.00, until 2026-09-06 06:30
PLAN: accepted, sha256 7651d3b1fa0c
gates: attempt 1, 4 new failures -> repair
gates: attempt 2, 0 new failures -> green
REVIEW: no blockers, 2 concern(s)
READY_FOR_REVIEW: $3.58 spent
PACKAGE: https://github.com/jtmcn/saffron/pull/136
```

`SA-0057` cost **$3.75 + $3.58 = $7.33** against a $12 declared ceiling. The
self-healing is real and it is not free.

## What this says and does not say

**It says** the corpse-stamping path works end to end on a failure nobody
staged, which is the first evidence of that. `stamp_orphaned=True` was argued
for from §4.2.1's premise and had only ever been exercised against `SA-0053`, a
task this session had already reasoned about by hand.

**It does not say** the loop handles provider errors. It says the *scan* does,
one night later. Within the night, a lost task is indistinguishable from a
finished one in every signal an unattended caller has: stop reason, exit code,
and the presence of a `batches` row. `docs/BACKLOG.md` item 70.

**A note on the second attempt's plan.** Different `spec_sha`-identical spec,
different plan sha (`7651d3b1fa0c` vs `c2dd82a9020d`), and four new gate
failures on attempt 1 where the first run had one. The re-run is not a replay;
it is a fresh attempt at the same spec, and its cost is not predictable from
the first.
