# Feedback on run-saffron-spec-loop (fifth run after the rework, 2026-09-16 to 2026-09-17)

Three specs, one chain: `SA-0093` → `SA-0094` → `SA-0095` (items 140, 143,
141). Run from the main checkout. Run 4's feedback is
`2026-09-16-spec-loop-skill-feedback-run-4.md`, cited here as "run 4, item N".

**Outcome:** three reviewable pull requests (#303, #305, #307), linked as stack
#308, and **$24.00** across five cells. `SA-0093` took three:

| Cell | Ended | Spent | Why |
|---|---|---|---|
| `SA-0093` 1 | `GATE_ERROR` | $4.42 | `witness` could not write a mutant of `session.py`; `revert` failed on two tests the spec asked for |
| `SA-0093` 2 | `ORPHANED` | $3.23 | apple/container refused `saffron-gate-net-SA-0093` at REVIEW (a bug on `main`) |
| `SA-0093` 3 | `READY_FOR_REVIEW` | $6.43 | attempt 1 |
| `SA-0094` | `READY_FOR_REVIEW` | $5.06 | attempt 1 |
| `SA-0095` | `READY_FOR_REVIEW` | $4.86 | attempt 2, after a `criteria` repair |

Two of the five cells failed for reasons outside the implementer's work, and a
third spent a repair on one. All three were caused by text or code the
operator's side wrote. Backlog items filed: 154–159.

Merged along the way, all by hand: spec fixes #292, #293, #304 and #306, and
#298, the network-name fix.

## Summary: what to change first

1. **The loop's own spec edits need the review a spec gets** (observation 2,
   item 159). The loop's edits caused three of this run's four lost attempts:
   tests that pass at base, a widened claim with no witness, and a
   "parametrise it" suggestion that renames the witness. Each of these had
   passed a first review. Two were caught only because a child spec happened
   to be reviewed again.
2. **Check a mutant's target size before a cell is paid for** (observation 1,
   item 154). `session.py` is over `witness`'s write ceiling, so no spec can
   declare a mutant on the file this loop edits most. On apple/container the
   failed write also wedged the cell, and it had to be cleared by hand before
   any other cell could start.
3. **`pattern` should show the CLI's error line** (observation 3, item 158).
   The one cell that died on a real bug showed a teardown survival line as the
   last thing before `teardown`. The cause needed a log read.

**What worked and should stay:**
- Step 1b, and the re-review at the parent branch. That re-review found a
  blocker in both child specs, after their first review and after the loop's
  own fixes.
- The two seats. They filed blockers on #303 (1), #305 (2, one of them the
  lens's own concern) and #307 (1, the same as the lens's concern, widened).
  The lenses raised no blockers and two concerns, both real.
- `next` holding each child back until its parent's review commits were
  pushed.
- `stack --execute` reading the bases back.

## Run 4's items, checked against this run

- **Item 1, `size` on a stacked branch.** Fixed. `size SA-0094` printed
  `since dfaf8986` (the parent's head), `158 changed lines`, and `SA-0095`
  printed `since d2528e28`. No false overrun reached the operator.
- **Item 2, editing a spec whose pull request is open.** Not repeated: every
  spec edit in this run landed before that spec's cell. But see observation 4:
  `status` now warns about it, and it warned falsely.
- **Item 3, `pattern` and `SALVAGE`.** No salvage happened, so it was not
  exercised. The new gap is observation 3.
- **Run 3's item 2, `stack` with one reviewable pull request.** Closed:
  `error: a stack needs two or more reviewable pull requests; have 1`, exit 1.
- **Run 3's item 1, the host probe before every cell.** Done before all five
  cells. `rapportd` was the only non-loopback listener each time.

## Observations

1. **A mutant on `session.py` aborted the first cell and wedged it.**
   `session.py` is 105,076 bytes. `_write_file`'s base64 argument is about
   140 KB, over the 131,072-byte `MAX_ARG_STRLEN` its `ponytail:` names. The
   `ponytail:` says the exec never starts. Measured here, the exec failed with
   `Stream unexpectedly closed`, and `saffron-cell-SA-0093` was left listed
   `running` while refusing exec as "not running". Teardown could not remove
   it, `saffron-cells`, or its two volumes. They came off with `container
   stop`/`rm`, `volume rm` and `network rm`, with no runtime restart. Neither
   step 1b's reviewer nor intake looks at a mutant's target size.

2. **The loop's own spec edits caused three lost attempts.**
   - #292 asked `SA-0093` for two guard tests that are true at base. `revert`
     judges every new test, so it failed them: `2 of 5 new test(s) passed
     without their source`.
   - #292 widened `SA-0095`'s criterion 1 to cover aborted and drifted suites,
     with no witness.
   - #306 fixed that and offered "parametrise the witness". The cell took the
     offer, and `criteria` reported the bare id as `witness-not-collected`.
     Attempt 2 fixed it with a plain helper.

   The pattern: a review finding gets a sentence of fix, and the sentence
   is not held to the rules the spec is. The guard tests moved into review
   commits (#303), where each was run against a mutant.

3. **The watch pattern hid the only real bug's cause.** Cell 2's Monitor
   showed `teardown: network saffron-gate-net-SA-0093 survived` and then
   `teardown`. The line naming the cause was
   `saffron: CellRuntimeError: … invalid network name`, and it is not in
   `pattern`. Every later Monitor had `|^saffron: ` added by hand.

4. **`status` read specs from the checked-out review branch.** With
   `saffron/SA-0095` checked out (cut before #304 and #306), `status` called
   both child specs stale and printed item 137's advice to revert the edit.
   From `main`, nothing was stale. Acting on that advice would have reverted
   two merged spec fixes. Item 157.

5. **A bug on `main` could only be fixed by hand.** Since #285, every live
   REVIEW on apple/container ended `ORPHANED`, because the Gate-only cell's
   network name carried the uppercase spec id. A spec cannot fix code that
   REVIEW runs host-side: its own cell would die in the same place. #298
   fixed it. Its test makes the shared stub refuse an uppercase network name,
   and 86 tests failed against the old name. This loop was the first live run
   of the Gate-only cell (item 131).

6. **The lenses were precise again, and the seats were the recall.** Across
   three reviewable cells the lenses filed two concerns and no blockers. Both
   concerns were real:
   - a split literal passing `SA-0094`'s one-place witness;
   - a subset write passing `SA-0095`'s.

   The seats' blockers beyond those two concerns were three, and in each the
   whole default suite, or the named witness, stayed green under the wrong
   code:
   - a container on the wrong network;
   - a pre-clean filter narrower than its prefix;
   - a table missing gates, or a skipped drifted suite.

   One Standards seat said `ruff format` closes the split-literal concern. It
   closes the implicit-concatenation form only; `"10.89.0.0" + "/24"` survives
   the formatter and passed the test file.

7. **A seat's proposed mutant was a no-op.** The #303 Spec seat's "network
   removed before the container" probe reordered an eagerly evaluated list
   literal, which does not move the call. Running it as written showed nothing.
   The real mutant calls `remove_network` before the list is built, and the
   new test killed it. This run's later seat prompts carried a warning about
   it; `REVIEW-PROMPT.md` does not yet.

8. **A seat's `is` identity check was declined.** For the split-literal
   witness, the #305 Spec seat proposed `assert EGRESS_SUBNET is
   runtime.SUBNETS["egress"]`. Whether two equal non-identifier strings are
   one object depends on the interpreter, so the witness instead parses each
   module and requires the value to be a `runtime.SUBNETS[...]` subscript. It
   killed the `+` form and an f-string.

9. **`record`, `next`, `drop` and `stack` read correctly.**
   - `record` called both failed cells undecided and left `SA-0093` pending;
     `next --again` named it.
   - `snapshot --force` picked up three specs queued mid-run
     (`SA-0096`–`SA-0098`), and `drop` kept them out on the operator's word.
   - Each child's cell logged `stacked on saffron/<parent> @ <reviewed sha>`.
   - `reconcile` printed `task 97's pull request head differs from what
     PACKAGE pushed` after the review commit. That is expected, but it reads
     like an alarm.
