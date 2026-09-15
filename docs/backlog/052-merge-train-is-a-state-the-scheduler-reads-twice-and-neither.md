---
id: 52
title: '`MERGE_TRAIN` is a state the scheduler reads twice and neither authoritative document declares'
status: open
tier: 2
specs: []
prs: []
commits: [6938c41, a4324f0]
cites: [§3.3, §4.2.1, §6]
related: [72, 75]
---

## Problem

`DESIGN.md:259` shows a task entering it, `saffron/scheduler.py:67` has it in
`DONE_STATES` and `:91` in `DEPENDENCY_WAITING_STATES`, and §4.2.1 names it twice
— in the queue filter and in the list of parents that admit a dependent. It
appears in **neither** `CONTEXT.md` nor `ontology/factory.ttl`.

Found by Appendix O's spike (rev 19), while counting what a shape form would need.
It is the fourth defect the modelling exercise has found in these documents, which
is Appendix O's own argument *for* the vocabulary landing on the same page as the
verdict that closed the operational question against it.

**It is not obvious which set it joins, and that is the work.** `CONTEXT.md` §6 is
careful that a state a task *ends in* is a wider set than the states that *reach
you* — `MERGED` ends a task and reaches nobody. `MERGE_TRAIN` is a re-queue arrow
in §3.3 and "done with the spec" to the scheduler, so it is plainly an `EndState`;
whether it is a `TerminalState` needs deciding rather than assuming, and that
decision is exactly the one item this document keeps getting wrong.

Phase A makes the propagation free once decided: `factory:MERGE_TRAIN a
factory:EndState` in the vocabulary and `uv run python -m ontology.render` writes
`CONTEXT.md` and the shapes. `TaskShape`'s `endedInState` list is the one hand
edit, and `test_every_terminal_state_is_a_state_a_task_can_end_in` names the file
if it is forgotten.

Two soft copies are worth knowing about and are **not** part of this: `cli.py`'s
exit-code map and `report/index.py`'s `_STATE_RANK` both fall through to a
documented default rather than raising, so an undeclared state degrades there
rather than breaking. That is by design and stays.

**Done looks like** `MERGE_TRAIN` declared once in `ontology/factory.ttl`, the
derived surfaces regenerated, `TaskShape` updated, and a one-line note in §3.3 or
§6 saying which of the two sets it joined and why.

### Decided 2026-09-08, and the item grew

`MERGE_TRAIN` is an **`EndState`**, not a terminal one — this item's own
"plainly an `EndState`" was right, and it survived an argument that it was not.
The argument was that a task in the merge train has not ended: it becomes
`MERGED` or `MERGE_FAILED`, so it is in flight. That is true and it is not the
rule, because it is equally true of `APPROVED`, which is already an `EndState`.

**What the rule actually is, because `EndState`'s own comment says otherwise.**
The comment reads "a state a task can finish in", which implies the row stops
changing. It does not: `CHANGES_REQUESTED`, `ORPHANED`, `RATE_LIMITED`,
`GATE_ERROR` and `PREFLIGHT_FAILED` all resume *the same row* —
`Candidate.task_id` is set for `REQUEUE_STATES` precisely so "the resumed work
reattaches to the row it was sent back to fix rather than a fresh one"
(`scheduler.py`). Five of `EndState`'s members contradict its definition. The
rule that fits every member is **whether the task is Saffron's to advance**:
`DRAFT` and `QUEUED` because it will be advanced tonight, `DIAGNOSING` through
`REBUTTING` because it is being advanced now; everything else waits on the
operator, on GitHub, on the merge train, or on `gc`. Sharpening that comment is
part of this item now — the wording sent two readers to the wrong answer in one
sitting, which is item **75**'s failure mode in the file that is supposed to be
authoritative.

**The item is no longer one state.** Declaring `MERGE_TRAIN` needs a class to
declare it *into*, and the vocabulary has none: `EndState` and `TerminalState`
model the states a task ends in, and nothing models the eight §4.2.1 names a
task passes through. So:

- `ontology/factory.ttl` gains **`TaskState`** as a supertype over `EndState`
  and a new **`InFlightState`** — exactly §4.2.1's eight (`DRAFT`, `QUEUED`,
  `DIAGNOSING`, `IMPLEMENTING`, `GATING`, `REPAIRING`, `REVIEWING`,
  `REBUTTING`), every one of them a state where a cell is Saffron's to run.
- `CONTEXT.md` gains **Task state** as its own term enumerating all of them.
  **Terminal state** is untouched, so §6's "everything else is internal" stays
  true as written. Both join `CLOSED_SETS`; no carve-out, for item **72**'s
  reason — a set excluded from the cross-check on a plausible-sounding basis
  cost three pull requests once already.
- A hand-written `TaskState` `Literal` cross-checked in
  `tests/ontology/test_vocabulary_agrees_with_code.py`, following `Severity`
  and `StopReason`. Not generated: nothing under `saffron/` imports a graph
  library and `pyproject.toml` says so.

**`set_task_state` stays untyped.** Neither landed defect was writer-side, and
a type with no measured defect behind it is machinery this repo does not buy.

### The half of this item that was decided wrongly

This item says `cli.py`'s exit-code map and `report/index.py`'s `_STATE_RANK`
"both fall through to a documented default rather than raising, so an
undeclared state degrades there rather than breaking. That is by design and
stays." **Half of that is reopened, and the evidence is this document's own.**

Both of the landed defects were exactly that fall-through: `6938c41` ("a state
that exists only in code is half a state" — `_STATE_RANK` knew neither
`GATE_ERROR` nor `NOT_IMPLEMENTED`, and `saffron cell` exited 0 for every
terminal state) and `a4324f0` ("every abort exits 2, and every state has a
rank" — `EXHAUSTED`, `ORPHANED`, `REVIEWING` and `REBUTTING` fell to
`_ORDINARY` and sorted below elevated-risk green tasks). Two defects, both
reader-side, both in the half declared safe.

`a4324f0` mitigated itself with "nothing calls `queue_lines` in production yet,
which is the only reason this has not been seen". That is now false, and it was
about a different function: `_STATE_RANK` is reached through
`report.sort_key` ← `render_index` ← `append_queue_line`, which
`phases/package.py` calls on every packaged task. **The ranking is live.**

**The two tables are not symmetric, which is what this item missed by treating
them as one.** An unknown state exiting `1` is a true statement — "the task did
not make it" is accurate about a state nobody has classified. An unknown state
ranking as `_ORDINARY` is an active misstatement: it sorts a dead cell below a
green reviewable task on the page the whole system exists to produce. So:

- **`CELL_EXIT` keeps its default**, and the reason is now written down rather
  than assumed.
- **`_STATE_RANK` becomes total** over the row domain, as two explicit sets —
  ranked-by-state and ranked-by-risk — with a test that every state is in
  exactly one. The risk ranking stays a deliberate choice rather than a
  fallback that also absorbs the unclassified.

**The domain is rows, not tasks.** §6 designs the morning index as a table of
rows, and one kind is a skipped repo — `toolbox — SKIPPED`, spec id an em-dash,
ranked 0 because "an entire repo produced nothing, which is the most expensive
thing on the page". So `QueueLine.state` is already wider than `tasks.state`
today, by design. `report/index.py` gets `RowState = TaskState |
Literal["SKIPPED"]` and `_STATE_RANK` is exhaustive over *that*. `SKIPPED`
stays, commented as designed-and-pending until multi-repo — it has no producer
because multi-repo is v2, not because nobody thought about it, and this was
nearly deleted on the second reading.

A refusal is the third row kind §6 and `CONTEXT.md` both describe and nothing
writes: refusals reach stdout, never `index.html`. Filed separately rather than
built here — a `REFUSED` classified before anything writes it is how `SKIPPED`
happened. The exhaustiveness test above is what will force the decision when a
producer does arrive.

### The other four sets

`scheduler.DONE_STATES`, `REQUEUE_STATES`, `DEPENDENCY_WAITING_STATES`,
`DEPENDENCY_DEAD_STATES` and `reconcile.IN_FLIGHT_STATES` are five more
hand-maintained classifications of the same strings, and nothing checks any of
them against anything. Each gets subset-hood against `TaskState`;
`IN_FLIGHT_STATES` gets **equality** with `InFlightState`, because it is meant
to be the whole class; and `DONE_STATES | REQUEUE_STATES` gets a coverage
assertion over every non-in-flight state, because §4.2.1 says the in-flight
states are deliberately on neither list — which makes an *end* state on neither
a silent bug of exactly the kind this item is now about.

Subset-hood alone would have caught neither landed defect. Both were omissions,
and no subset check catches an omission.

### Also falsified by this work

`tests/ontology/test_vocabulary_agrees_with_code.py`'s docstring: "The terminal
states the code names do still fall through to a documented default rather than
a raise, so they are not a closed set on the code side and are not checked
here." That sentence states the precondition this item removes.

**By hand, and its own pull request.** It spans the vocabulary, two generated
surfaces, three modules and their tests, and `ontology.render` has to be run and
its output committed — which a cell cannot prove it did honestly.

**Tier 2 still.** Larger than when it was sorted, and it competes with tier 1's
soundness items. Sequencing it behind them is the backlog's own rule working,
not a reason to shrink the item.
