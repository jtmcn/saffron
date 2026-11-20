# Feedback on run-saffron-spec-loop (run 80, 2026-11-20)

Run 80 kept the goal of runs 55 to 79: implement every backlog item. It ran
`SA-0415`, the one spec the chain merged after run 79.

| Spec | PR | Outcome | Spend of budget | Turns of ceiling |
|---|---|---|---|---|
| `SA-0415` | #1271 | `READY_FOR_REVIEW` | $17.91 of $48 | 242 of 200 |

Batch 97 ran at `--budget 120` with `--stack --defer-end-review`. The weekly
usage limit stopped its cell at `RATE_LIMITED`, after $16.29 by the ledger.
The batch then refused the retry, since the spec's $48 budget exceeded the
$43.71 left. Batch 98 ran the spec again with the same flags and drained.
Finish 98's end review spent $1.49 of its $30 reserve. It committed nothing
and ran no follow-up. Turns count every phase.

The spec chain ran beside both batches. It merged `SA-0416` (#1270) and
`SA-0417` (#1272), which run 81 runs.

## What the run found

1. **The usage limit stopped the loop for 34 hours.** It cut off the cell
   and a spec review together. The review resumed where it stopped. The
   cell started over in a new batch, and the first cell's $16.29 bought
   nothing that reached the PR.
2. **The pause also emptied part of the scratchpad.** The token files and
   the seat-prompt script were gone. Batch 98's first start failed at once
   on the missing token file. The seat prompts were rebuilt by hand from
   `REVIEW-PROMPT.md`.
3. **A critic that withdrew every blocker still left three for the Spec
   seat.** REBUT fixed seven adequacy blockers. The Spec seat then ran 68
   probes and found eight survivors. Six put a check on the first set or
   the first member alone, because each refused shape held its deciding
   entry first. Runs 78 and 79 saw the same shape.
4. **The finish read the reviewed head.** Its one finding was the critic's
   conventions concern, already fixed, and it marked that one unverified
   because the cited line had moved.
5. **`saffron mutant` refused a writer's mutant.** The writer drafted a
   mutant whose `find` exists only after the change. The command refused
   it, so the spec carries none. The writer's own check did not run the
   command.

## What the reviews found

- `SA-0415`: three Spec blockers, all witness gaps. Refused shapes sat at
  an edge, a docstring witness checked one literal phrase, and two claims
  that the spec called twins were not twins. All three are fixed, each
  measured with a probe that survived and then died. The Standards seat
  found three docstrings that said less than the code does, all fixed.

## Run 79's items, checked

- [ ] **A host probe asks what the code it edits is for:** open. No probe
  this run chose a no-op edit.
- [ ] **The adequacy lens reads every arrangement a claim names:** open.
  Item 3 is the third run of evidence.
- [ ] **`next-id` reserves an id for a draft:** open, on b-90c8fa. Two
  chains ran one at a time, so no id collided.
- [ ] **A wrong version's edit changes only the case it names:** open, on
  b-f06097.
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.
- [ ] **The `prose` gate reads an irregular participle:** open, on
  b-6b8896.
- [ ] **`integrity` reads a fixture's spec id as data:** open, on b-988eb9.
- [ ] **The driver pushes a reviewed layer with its lease:** open. One
  layer this run, so no lease push ran.
- [ ] **`cite` flags a bare citation into a parent's changed file:** open,
  on b-b664d1.
- [ ] **`bookkeeping` runs the smoke test's flat corpus:** open.
- [x] **`driver.py check` refuses a spec body that quotes a mutant's
  `find`:** landed in #1266.

## Summary: what Saffron should absorb next

1. **The adequacy lens moves a claim's deciding case off each edge.** A
   lens change, with no item yet. Item 3 is the evidence, for the third
   run. The spec chain has added checks 72 to 75 for the same class.
2. **A rate-limited task resumes its cell instead of starting over.** A
   phase change, with no item yet. Item 1 is the evidence.
3. **The driver fills the seat prompts.** A tool change, with no item yet.
   Item 2 is the evidence: a script outside the repo held the step, and a
   pause erased it.
4. **The spec writer's tree checks run `saffron mutant` on each drafted
   mutant.** An agent change, with no item yet. Item 5 is the evidence.
5. **A host probe asks what the code it edits is for.** A lens change,
   with no item yet, carried from run 79.
6. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.

This PR changes no skill text.

## Next run

Run 81 runs `SA-0416` and `SA-0417`. Neither touches the other's files.
