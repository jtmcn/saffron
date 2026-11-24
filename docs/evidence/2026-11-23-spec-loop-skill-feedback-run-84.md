# Feedback on run-saffron-spec-loop (run 84, 2026-11-23)

Run 84 kept the goal of runs 55 to 83: implement every backlog item. It ran
two batches.

| Batch | Spec | PR | Outcome | Spend of budget |
|---|---|---|---|---|
| 104 | `SA-0423` | #1305 | `ORPHANED` twice, taken by hand | $55.84 of $60 |
| 105 | `SA-0426` | #1308 | `READY_FOR_REVIEW` | $17.77 of $64 |
| 105 | `SA-0424` | #1310 | `REBUTTAL_UNJUDGED`, taken by hand | $53.13 of $62 |
| 105 | `SA-0427` | #1309 | `READY_FOR_REVIEW` | $16.04 of $56 |
| finish 105 | `SA-0428` | #1311 | `READY_FOR_REVIEW` | $7.35 of $15 |

Batch 104 ran at $360 and exited 2. Batch 105 ran at $500 with
`--stack --defer-end-review` and drained. `SA-0425` did not run, because its
parent `SA-0424` ended with no pull request. Its deferred finish drafted one
follow-up from one concern on `SA-0426`.

Beside the loop, the spec chain merged `SA-0426` (#1303) and `SA-0427`
(#1304). #1306 refreshed two citations, and #1307 retired `SA-0423`.

## What the run found

1. **The container refused an exec after REBUT, twice.** Each run of
   `SA-0423` raised "no PID data from sync pipe" and ended `ORPHANED`. The
   runtime kept no logs, and the proxy and two networks outlived teardown.
   Recorded on b-f582ee.
2. **REBUT's agent exited on code -6.** `SA-0424` ended
   `REBUTTAL_UNJUDGED` with both blockers unanswered. Recorded on b-53354f.
3. **`saffron adopt` refused both by-hand pull requests.** It takes neither
   `ORPHANED` nor `REBUTTAL_UNJUDGED`. So `SA-0425` stays refused behind
   `SA-0424`, and the end review never read `SA-0424`. Recorded on b-619b7d.
4. **Three wrong versions could not fail their own witness.** `SA-0426`'s
   criterion 3 version widened `_DIGITS` and left `identity` alone. Finish
   105's draft declared two `migrate` versions its witness could not reach.
   REBUT left both for the operator. Recorded on b-216235.
5. **Batch 104 refused `--budget 300`.** Three specs needed $352. This is
   the same guess as batch 101.
6. **Two seats handed back their report as a message.** The delegate saved
   each one, with its findings block verbatim. Later prompts asked for the
   file, and every seat wrote it.

## What the reviews found

- `SA-0426`: the Spec seat ran 30 probes, and each died. The Standards
  seat found an em-dash in an attribute docstring that no gate reads
  (b-e0e720). Four fixes landed. Jev scored 3 answers on the cell review
  and 15 on the PR review.
- `SA-0427`: the Spec seat found one blocker. The release probe missed an
  unlock spelled `LOCK_UN | LOCK_NB`. Three fixes landed. Jev scored 9.
- `SA-0424`: the delegate closed both host probes in a review commit. The
  Spec seat then found one survivor in 49, a warning naming another path.
  The Standards seat found three wording notes and two drifts in protected
  files (b-1349d9). Jev scored 6 and 12.
- `SA-0428`: the delegate probed its refactored witness, and the probe
  died. Its patch was accepted.

## Run 83's items, checked

- [x] **The finish logs the violation that failed its suite:** observed.
  Finish 105's log named a `prose` hedge with its line and three citations
  with the lines they should name. The bare file name half was not tested.
- [ ] **The adequacy lens drives each member a claim names:** open. Two
  seat blockers this run were members no witness drove.
- [ ] **A test that writes outside `tmp_path` fails a gate:** open. It did
  not recur.
- [ ] **REBUT retries an agent that exited on an API error:** open, on
  b-53354f. It recurred on `SA-0424`.
- [ ] **The host checks a spec's mutants before its spec review:** open,
  on b-216235. It recurred three times.

## Summary: what Saffron should absorb next

1. **`saffron adopt` takes an `ORPHANED` or `REBUTTAL_UNJUDGED` task.** A
   tool change, on b-619b7d. Item 3 is the evidence. It blocks a child spec
   and the end review.
2. **REBUT retries an agent that exited with no result event.** A phase
   change, on b-53354f. Item 2 is the evidence.
3. **The host checks each declared wrong version against its own witness
   before the cell.** A phase change, on b-216235. Item 4 is the evidence.
4. **The adequacy lens drives each member a claim names.** A lens change.
   The `SA-0424` and `SA-0427` seat blockers are the evidence.
5. **The `prose` gate reads attribute docstrings.** A gate change, on
   b-e0e720.

This PR changes no skill text.

## Next run

Run 85 runs `SA-0425` on top of `SA-0424`. b-c2f264's spec follows.
