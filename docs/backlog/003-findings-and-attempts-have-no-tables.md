---
id: 3
title: '`findings` and `attempts` have no tables'
status: done
tier: null
closed: 2026-08-23
by_hand: true
specs: [SA-0003]
prs: []
commits: [229c4b2]
cites: [§4.1, §4.2, §4.6, §5.4, §6, §8]
related: [9]
---

## Problem

`DESIGN.md` §4.1 declares both. Neither exists, so:

- REVIEW's findings and REBUT's verdicts and rebuttals live in `rebuttal.json`
  in the batch tree. §4.1 is explicit that `verdict`, `adjudication` and
  `rebuttal` are three distinct columns that must not collapse — they are three
  distinct JSON keys instead, which is the right shape in the wrong place.
- every attempt's gate results share one `attempt_id`, so "which attempt produced
  this failure?" has no join to stand on — the question §5.4's no-progress rule
  and §8's flywheel both assume is answerable.
- `tasks.spent_usd_est` does not exist, so a run ends with no persisted record of
  what it cost. Fine while an operator is watching; not fine for §4.2's budget
  gate.

`SA-0003` produced an `attempts` implementation, unreviewed, in the batch tree —
its patch no longer applies (see item 9).

## Done looks like

both tables, the drop-rate-per-lens query answerable in SQL,
and cost on the task row.

## Record

**Status:** **done**, in `229c4b2` (*feat(ledger): an attempt had no identity,
so every one of them shared the task's*). Both tables exist — `attempts` at
`saffron/ledger.py:54`, `findings` at `:98`.

**Done, 2026-08-23.** All three, by hand; `SA-0003`'s stale patch was not
reopened, and two review rounds followed. What is worth carrying forward, in the
order it was learned:

**The column had no `REFERENCES`, and that is what made the convention
possible.** `gate_results.attempt_id` was a bare `INTEGER`, so holding a
`task_id` in it was not a shortcut the schema tolerated — it was one the schema
could not see. It points at `attempts(attempt_id)` now, and the old convention
is unrepresentable rather than merely discouraged — though that took two more
commits than the schema line, and this paragraph claimed it a round early
(below). Two existing ledger tests asserted it directly and had to change;
`SA-0003`'s "every existing test still passes unchanged" was written before it
was clear that two of them encoded the defect.

**Attempts are opened by wrapping the agent callable, not at the call sites.**
`record_attempts` sits inside `stop_on_rejected`, so a turn the provider walled
records its cost before the rate limit is raised. The consequence is the reason
for the shape: the lens sessions inside `review.run_review` and the rebuttal and
verdict turns inside `rebut.run_rebut` all get rows without either phase
learning what a ledger is — they still take an `agent` and nothing else. A
turn that fails is still recorded; one that raises something neither layer
expects leaves its row open, which is an honest reading of what happened.

**`phase` is the state the task is in, and `spent_usd_est` is derived.**
`open_attempt` reads `tasks.state` rather than taking a phase, because the
caller already sets it at every phase boundary and tracking it twice is how the
two drift. `set_task_state` rolls the spend up from `attempts` in the same
statement, so the figure cannot disagree with the rows it is made of and no
terminal path can forget it — there are seven of them. The equality between
`tasks.spent_usd_est` and `CellOutcome.spent_usd` is asserted, because it is
what proves no spending turn is missing a row.

**`SA-0003` deferred `spent_usd_est` on a question that was already answered.**
It said the sum depends on "whether a resumed session reports per-turn or
whole-session cost, which is not yet known". `session.py` had since measured it
— $0.00396 fresh, $0.00199 on resume of the same `session_id`, so summing is
correct and cumulative would never fall. The deferral outlived its reason.

**Review found the migration, and the obvious repair is illegal.** A ledger
written before `attempts` existed holds a *task_id* in `gate_results.attempt_id`
— and a new attempt's id starts at 1 in that same integer namespace, so task 1's
v0.5 results reattach to whichever attempt draws id 1. Reproduced on a copy of
this machine's own `~/.saffron/ledger.db`, which is exactly such a ledger.
Nulling the legacy values out is not available: the `CHECK` that keeps exactly
one of `attempt_id` and `run_id` set rejects a row with neither, on `UPDATE` as
much as on insert. What shipped was the backfill the old schema comment promised
— one attempt row per legacy value, carrying that value as its own id, so the
ids stay taken and nothing is lost or moved. Measured on that copy: five
backfilled, zero dangling, every task still holding its own results.

**And the backfill protected the data without delivering the constraint.** A
second review round found the paragraph above true only of a ledger created from
scratch: `CREATE TABLE IF NOT EXISTS` is a no-op on an existing `gate_results`,
and SQLite has no `ADD CONSTRAINT`, so on an upgraded ledger the column still
read `attempt_id INTEGER` and a dangling `attempt_id` inserted silently. The
test that was supposed to prove otherwise passed because its fixture builds a
fresh file — the same shape of gap as the one this item exists to end, one level
up: a check that reads as enforcement and is a convention. What ships now is
SQLite's documented 12-step rebuild, after the backfill so every copied row
already has an attempt to point at, `foreign_keys` off across it because
`failures` references `gate_results`, which does not exist between the DROP and
the RENAME.

Dangling rows are copied in rather than refused. SQLite checks a reference when
a row is written, not when it is rebuilt, so a `PRAGMA foreign_key_check` gate
here is theatre: the rebuild has already committed by the time it runs, and the
next open takes the early-return path and lets the row through anyway. The
constraint governs what can be recorded from here on, which is what made the
collision possible. Measured on the copy again: 49 gate results, 12 failures,
5 tasks and 5 runs identical across the migration, a dangling write rejected.
The rewrite happens on first open, so the ledger is worth copying aside before
the next run.

**Two more from that round, both in what the ledger is told.** `task_spend`
selected `tasks.spent_usd_est`, which only `set_task_state` refreshes — correct
only when a state change happened to precede it, which today's one caller
arranges and a read from inside the repair loop would not. It sums `attempts`
now; the column stays, because it is what `queue_lines` reports without a join.
And the rebuttal write was lossy twice: `run_verdict` rejects a verdict set that
is not exactly its own blockers, but nothing validates the *rebuttal* turn's
numbering, so two entries for blocker 1 and none for blocker 2 left blocker 2
reading as unanswered against an artifact that says otherwise. Validated at the
write now. `Rebuttal.action` was dropped outright, which made a claimed fix and
an argument indistinguishable in `findings.rebuttal` — the distinction §4.6's
critic-ROI query is the whole reason for the column.

Two smaller ones from the same review. `open_attempt` against a task that does
not exist selected nothing and still returned `lastrowid` — an id that exists,
belongs to another attempt, and satisfies the foreign key; silent
misattribution, which is the failure this item exists to end. And `RATE_LIMITED`
was the one exit where the ledger and `CellOutcome` disagreed: the raise comes
from outside the turn, so it lands past the `spent +=`. The outcome reads the
attempts back now, which also closes the older gap where a window closing inside
`plan_checkpoint` lost the whole tally with its frame.

Still open, by choice: `findings.adjudication` has no producer — it is the
operator's, and the morning queue (§6) is where it comes from. `attempts.model`
is declared and never written: the runner's `result` event does not carry it and
only assistant messages do, so recording it means changing the event schema.
`batches` and `decisions` remain the two tables of the ten with nothing to put
in them.
