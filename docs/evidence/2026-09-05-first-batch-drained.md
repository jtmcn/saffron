# The first night: an empty queue, drained

**Run:** `saffron batch --repo . --budget 50 --until 06:30`, 2026-09-05 11:29 PDT,
against this repo, immediately after the batch orchestration stack merged (`57b676c`).
**Result:** `DRAINED`, exit `0`, $0.00, no cell started.

The first time anything in Saffron ran a batch. Deliberately against an empty
queue: `DRAINED` in seconds costs nothing and still exercises readiness, the
mirror fetch, the scan, `reconcile`, the ledger row and the exit code. A night
with work in it tests all of that *plus* the parts that spend money, and there
was no reason to test them together the first time.

## What it printed

```
reconcile: task 44 → ORPHANED
batch: 0 candidate(s), budget $50.00, until 2026-09-06 06:30
refusals: 0
batch: DRAINED
```

## What the ledger holds

```
batch_id  started_at           ended_at             budget  spent  until_ts             status
1         2026-09-05 18:29:23  2026-09-05 18:29:23  50.0    0.0    2026-09-06 13:30:00  DRAINED
2         2026-09-05 18:29:59  2026-09-05 18:29:59  50.0    0.0    2026-09-06 13:30:00  DRAINED
```

Two rows because the run was repeated once to capture the exit code separately
from the output; both are the same night against the same empty queue.

No run carries a `batch_id` — nothing was minted, because no candidate ran. The
derived `batch_spend(1)` is `0.0`, read through the join rather than off the
stored column.

## Three things this confirmed, each a fix from the review round

**The `ORPHANED` line is the first line of the first night.** Before `SA-0051`'s
review fix, `orphaned` counted toward "something moved" — suppressing the
"nothing moved" fallback — while having no bucket of its own, so a resolution
that *only* orphaned printed nothing whatsoever. `saffron queue` never orphans;
the unattended night is the only caller that reaches it. The first real run
would have opened with silence.

**`until_ts` is UTC and sorts against the `started_at` beside it.** Local time
was 11:29 PDT and the deadline 06:30 PDT tomorrow; the row holds `18:29:23` and
`2026-09-06 13:30:00`, and `started_at < until_ts` is true as text. Stored as
`until.isoformat()` on a naive local datetime — what shipped — it would have
read `2026-09-06T06:30:00`: seven hours wrong, in a different format from every
other timestamp in the module, and sorting *before* an `ended_at` at 23:00 on
the same night.

**The plan header exists.** `batch: 0 candidate(s), budget $50.00, until …` is
`SA-0054`'s review fix. Without it the log's first word about the night is its
last, and "an empty queue" reads identically to "three specs all refused".

## The one substantive finding: task 44

`SA-0053` — the `saffron watch` verb — was stamped `ORPHANED` by this scan and
not by the `saffron queue` run four minutes earlier. That difference is
`stamp_orphaned`, and it is working as designed: `queue` may be run at will,
mid-phase, and must never stamp a live task; a batch asserts §4.2.1's premise
that one batch runs at a time, so an in-flight row it finds is a corpse.

Task 44 really is a corpse. Its cell stopped at `REVIEWING`, and its work
merged on a `joel/` branch rather than a `saffron/` one, so no pull request can
be matched to it and `reconcile` cannot learn what became of it.

**`ORPHANED` is in `REQUEUE_STATES`, so it would have produced a candidate — and
did not, because the spec had already been retired to `.saffron/specs/done/`.**
Had it still been at the top level, this first batch would have re-run merged
work whose witnesses are green at base: a full cell, real money, for nothing.
The retirement was made by hand two days earlier on the reasoning that a task
stopping at `REVIEWING` is in flight rather than done; this run is the
confirmation that it mattered.

## What this is not evidence of

No cell started. So nothing here says anything about the budget gate, the
breaker, `--until` firing, packaging, the orphan sweep after a runner raises,
or what a night costs. Every one of those is tested and none is measured.

The next thing worth running is a night with one cheap spec in it.
