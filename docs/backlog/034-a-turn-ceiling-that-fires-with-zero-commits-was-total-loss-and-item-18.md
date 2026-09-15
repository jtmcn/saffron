---
id: 34
title: A turn ceiling that fires with zero commits was total loss, and item 18's prompt was not enough
status: done
tier: null
closed: 2026-09-01
specs: [SA-0025, SA-0028]
prs: [87]
commits: []
cites: [§4.1, §4.3, §5.3]
related: [4, 18]
---

## Problem

**Measured, once, and it cost a whole task.** `SA-0025` ran `NOT_IMPLEMENTED`
at $14.61 — the first zero-commit run of the eight logged at the time. Its two
attempt rows:

| n | turns | cost | subtype | terminal_reason |
|---|---|---|---|---|
| 1 | 36 | $2.93 | `success` | `completed` |
| 2 | 141 | $11.68 | `error_max_turns` | `max_turns` |

The plan was accepted and was good. The implement turn ran to its ceiling
trimming the diff to fit `size`, committed nothing, and `teardown: no commits,
nothing to export` threw all of it away — with $5.39 of the budget still
unspent. **The turn ceiling bound, not the dollars**, which is the fact a
prompt cannot answer: `implement.md` already said "commit your work," and the
agent still ran to 141 turns without doing it. Telling an agent to behave
differently is not a control; it did not become one the second time either.

**The control is structural, at the one boundary the host already owns.**
`session.py` already reads `terminal_reason` off the closed turn and
`commits_ahead` off the worktree — the two facts together are unambiguous: a
turn that ended with `terminal_reason == "max_turns"` and zero commits was cut
off, not finished. When both hold, and only then, the host now spends one more
turn — resumed on the same `session_id`, so the agent keeps the context it
already paid for — whose only instruction is to commit what already exists.
Bounded at `SALVAGE_MAX_TURNS` (five, against `intake`'s default ceiling of
sixty — the spec that measured this set its own to 120), and clamped to the
spec's own `max_turns` so it can never exceed the turn it salvages: a salvage
that could itself run to 140 turns is the defect
this item closes, one level down. The budget ceiling is checked before the
salvage turn is spent, never after — a task with no room left ends exactly as
it did before this existed, and the watch line says the budget stopped it
rather than silently skipping the turn. A turn that finished on its own with
nothing gets no salvage: the agent decided it was done, and §4.3's "doneness is
measured, never reported" does not become "measured, then argued with."

**What this does not cover, on purpose.** It is one turn at one boundary
(IMPLEMENT only — not the REPAIR loop's own turns, which already checkpoint
dirty work on a bound firing, item 4). Two neighbouring branches lose an
uncommitted tree exactly as before, and both are decisions rather than
oversights. A run *over budget* when the ceiling fires takes no host checkpoint:
committing there would push a task with no money left into GATE and spend the
suite it cannot pay for, and `EXHAUSTED` is the outcome it earned. A run ended
by some *other* bound — idle, wall-clock, a crash — takes none either: the
salvage turn is spent on one measured pair of facts, and widening the free
checkpoint to every abnormal ending is a separate argument from the one this
item makes, on a path whose retry is already warranted. Neither is free of
cost, and both are worth revisiting with a measurement rather than a guess. It
also does not raise `max_turns` or spend
the leftover budget on more implementation (the failed run did not need more
turns; it needed to have committed at turn 20), and it does not steer a turn
while it is running — the host cannot inject an instruction mid-turn, only
resume at the boundary it already owns.

**The decision this item also records: a dirty, uncommitted `/work` at
teardown is still never packaged, even after this exists.** The tempting
second half — when the salvage turn also produces nothing, export the working
tree's diff anyway, on the theory that *some* record beats none — was
considered and rejected. Control artifacts are extracted and hashed the moment
they are produced and never re-read from `/work`; a file left in the workspace
is a claim, not a record. A working-tree diff that reached `patch.diff` would
be packaged as though it had passed gates it never faced, and `committed`
exists precisely to refuse that at GATE. If a diagnostic dump of the dirty tree
turns out to be worth having for triage, it needs its own name, its own place
PACKAGE never reads, and its own spec — not a quiet exception carved into the
one artifact the operator trusts.

**What review added after the cell, and what it left open.** Three holes the
gates could not see: the host checkpoint fired only when the salvage turn was
*cut off*, so a salvage that returned cleanly having committed nothing — a
commit hook rejecting it is the likely shape — lost the work it was spent to
save; the crashed-turn watch line keyed on `is_error`, one of the four things
`run_agent`'s own failure predicate ORs, so a turn that crashed after emitting
a clean result still read as "finished and produced nothing"; and the salvage
turn inherited the implement turn's cost as `_reconcile_cost`'s fallback,
which bills a five-turn `git commit` at a 120-turn turn's price and can book
`EXHAUSTED` on a task the salvage just rescued.

**What the second review round found, all four in the same shape.** The cost
scaling was applied in one direction only: the salvage turn was correctly given
a scaled-down fallback, and then its own small figure was carried forward as
`last_cost`, becoming the crash fallback for the *next* turn — which runs on the
full ceiling. That reopens §4.1's budget-that-stops-counting one hop downstream
of where the scaling closed it, so `last_cost` now keeps the implement turn's
figure across the salvage. `commit_dirty` raises rather than returns when a hook
rejects the commit, so a host checkpoint on a tree the repo's own `prek` hooks
refuse converted an earned `NOT_IMPLEMENTED` into an infrastructure abort,
charged to nobody: the salvage path now catches `CellRuntimeError`, says so on
the watch line, and lets the `commits_ahead` re-measure decide. The same shape
is still live in the repair loop's own checkpoint, where the tree is not known
dirty and so is less likely to fire — it needs its own spec (closed by hand
2026-09-10 instead — see Status). And
`cut_off_at_turn_ceiling` read `terminal_reason` alone where `run_agent` keys on
`subtype`; the ledger row carried both, and a result event arriving without the
one field would have skipped the salvage in silence, which is indistinguishable
from a control that ran and found nothing.

**Owed to an operator, by design.** `DESIGN.md` and `CONTEXT.md` are `forbidden`
to `SA-0028`, and three edits are outstanding: §5.3's account of IMPLEMENT
describes one checkpoint and there are now two; §4.3's "doneness is measured,
never reported" gains the qualification this item argues for (a turn cut off is
not a turn that reported doneness), and its own table still says IMPLEMENT is
measured `base..HEAD` when the code has measured from the plan turn's head since
item 18; and `CONTEXT.md` grants bare-caps status to phases plus the plan
checkpoint by name, which `SALVAGE:` now needs too — it is a turn at a boundary,
deliberately not a phase, the same entry the plan checkpoint carries.

## Record

**Status:** **done** — `SA-0028` (PR #87), 2026-09-01. The item's own
closure paragraph is below. Its one residual — the repair loop's own checkpoint
letting a hook's refusal out as an infrastructure abort — closed by hand
2026-09-10, on the salvage path's rule and with a test watched failing first.

**Closed by `SA-0028`, 2026-09-01.** Item 18 closed `SA-0005`'s turn-ceiling gap
by making `max_turns` a real, per-spec, printed ceiling and asking
`implement.md` for a commit per coherent step, "with the measurement." That was
necessary and it was not sufficient: `SA-0025`, ledger task 24, hit the same
shape it was written about and died the same way.
