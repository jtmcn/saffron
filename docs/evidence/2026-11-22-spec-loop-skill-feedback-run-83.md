# Feedback on run-saffron-spec-loop (run 83, 2026-11-22)

Run 83 kept the goal of runs 55 to 82: implement every backlog item. It ran
`SA-0421`, then `SA-0422`, which depends on it, in one batch.

| Batch | Spec | PR | Outcome | Spend of budget |
|---|---|---|---|---|
| 103 | `SA-0421` | #1296 | `READY_FOR_REVIEW` | $22.29 of $60 |
| 103 | `SA-0422` | #1299 | `READY_FOR_REVIEW` | $31.85 of $60 |

The batch ran at $280 with `--stack --defer-end-review` and drained. Its
deferred finish spent $9.16 of the $70 reserve. It drafted one follow-up
and pooled all four findings, so it pushed nothing.

Beside the loop, the spec chain merged `SA-0423` (#1295), `SA-0424`
(#1298) and `SA-0425` (#1300). b-60f950 landed by hand as #1297.

## What the run found

1. **The finish pooled every finding over its own draft.** The writer's
   `SA-0426` cited bare file names, so 11 citations did not resolve. The
   redraft failed `test_the_backlog_records_hold` in the finishing suite.
   The log names the test and not the violation. Recorded on b-4a9207.
2. **The seats found seven blockers the critic and REBUT left.** Five were
   members a claim names that no witness drove. One was a witness that took
   the host's real lock root and deleted live locks there. One was a spy
   interrupt that escaped `pytest.raises`.
3. **REBUT answered six adequacy probes on `SA-0422`.** Each probe died on
   a plain failure after the cell's second attempt.
4. **The stack fell behind `main` while it waited.** Three spec PRs and
   #1297 merged under it. Step 5's base then lacked `driver.py priority`,
   so the delegate rebased both layers onto `main` by hand.
5. **Two suites at once failed two timing tests.** The delegate ran
   `make check` while the finish ran its own suites. Both tests passed
   alone and in CI. The skill already says to run one suite at a time.

## What the reviews found

- `SA-0421`: the Spec seat found three blockers, each a `None` half or a
  suffix no witness asserted. The Standards seat found a backwards
  docstring and a comment. All five were fixed. Jev scored 6 answers on
  the cell review and 24 on the PR review.
- `SA-0422`: the Spec seat found four blockers and the Standards seat one,
  with the same root. The seats' concerns on a test citation and a copied
  helper were fixed. The end review's two pooled concerns went to
  b-708b05. Jev scored 24 and 42.

## Run 82's items, checked

- [ ] **REBUT retries an agent that exited on an API error:** open, on
  b-53354f. `SA-0425` reads the death's budget signal instead, and drops
  the retry for want of a measured trigger.
- [ ] **The host checks a spec's mutants before its spec review:** open,
  on b-216235.
- [ ] **A record push runs under a time limit:** open, on b-65eb8f. No
  push stalled this run.
- [ ] **The `witness` gate reads an exception-only kill as a survivor
  where the claim expects success:** open, on b-c2f264.
- [ ] **`saffron adopt` takes a halted task:** open, on b-619b7d. No task
  halted this run.

## Summary: what Saffron should absorb next

1. **The finish logs the violation that failed its suite, and resolves a
   bare file name in a draft's citations.** A phase change, on b-4a9207.
   Item 1 is the evidence.
2. **The adequacy lens drives each member a claim names.** A lens change.
   Item 2 is the evidence, and run 82's item 6 is the same class.
3. **A test that writes outside `tmp_path` fails a gate.** A gate change.
   Item 2's lock root is the evidence.
4. **REBUT retries an agent that exited on an API error.** A phase change,
   on b-53354f.
5. **The host checks a spec's mutants before its spec review.** A phase
   change, on b-216235.

This PR changes no skill text.

## Next run

Run 84 runs `SA-0423`, `SA-0424` and `SA-0425` as one chain.
