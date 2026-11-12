# Spec chain feedback, SA-0380, 2026-11-12

Continues `docs/evidence/2026-11-12-spec-chain-feedback.md`, which `SA-0381`'s
pull request adds. Check numbers carry on from its 42.

## SA-0380 (b-f582ee), after spec loop run 65

`saffron package` takes an `ORPHANED` task whose cell went green and whose
review would end `READY_FOR_REVIEW`. `run_task` names that command when a
cell raises past such a task. The green fact is a `REVIEWING` attempt row,
which only a green `repair_loop` reaches.

**Review 1: 1 blocker, 5 concerns, 5 notes.** The writer revised.

- `CONTEXT.md`'s `INFRASTRUCTURE` definition became false, since the reused
  mark closes a night for a cell raise. The delegate amended it by hand.
  Check 40 covers refusals but not the outcomes a reused mark reaches.
- Two `batch.py` docstrings and three more sentences became false.
- The witness missed an unanchored host-filed survivor and a pool-cut
  review.

**Review 2: 1 blocker, 3 concerns, 4 notes.** The delegate applied them by
hand with no third review.

- REBUT also files `GATE_ERROR`, which no witness drove, so a deny-list of
  two states passed. Pre-flight 1 missed a member of the rebuttal states.
- `ready_task` raising a non-git exception was undriven.
- Two protected sentences said `ORPHANED` never reaches the operator.

## Checks to build (SA-0380)

43. A spec that reuses a mark or flag lists every outcome its readers
    produce, and each protected sentence that defines those outcomes.
44. A claim over a task's states enumerates the closed set from the code
    that writes them, not from the states the spec has in mind.
