# Feedback on run-saffron-spec-loop (run 41, 2026-10-16)

Run 41's order was `SA-0274` alone. The 14 specs behind it form one chain,
and each waits on the one before it.

`SA-0274` ended `READY_FOR_REVIEW` at $14.69 of $22, its spec review
included. Batch 34 ran at $110 with `--stack` and spent $18.61. PACKAGE
opened #887.

## Before the run

Three by-hand fixes landed between run 40 and this run.

- **#884 gave REBUT's extraction and verdicts their own reserves
  (b-4901d2).** The rebuttal turn keeps its $10. The extraction gets $4 and
  the verdicts $2.
- **#885 refreshed three drifted citations in `SA-0274`.** `driver.py
  cite` found them. A batch's spec review would have paid for them again
  (b-d31930).
- **#886 lets a revision draw on the writer's share (b-b24cf7).** The
  operator chose this arm. It merged while batch 34 ran, so the batch ran
  the old rule.

## What happened, in order

1. **The ceilings check cleared `SA-0274`.** 130 turns against a peak of
   117, and $22 against $11.35.
2. **The spec review found three notes and no blocker ($1.78).** One said a
   citation had drifted. The cited range still holds the test, so it was not
   a defect.
3. **IMPLEMENT and one repair round took 80 turns of 130.** The second gate
   attempt was green.
4. **The adequacy lens raised four blockers.** Each was a probe on
   `_under_test_path` that the first witness survived: one pattern read
   alone, `fnmatch`, a substring prefix, and the first pattern only.
5. **REBUT rewrote the witness for $3.58.** It declared two globs over six
   files, and the lens withdrew all four. No pool cut anything.
6. **The batch then took up `SA-0275`.** Its spec review found a blocker
   ($2.52). The revision needed $56.50, and $37.79 was left. Under #886's
   rule $65.30 would have been left. Thirteen specs were then refused,
   because each reaches `SA-0275`.
7. **The end review left one note ($1.40).** `size_gate` runs its LCS pass
   twice. That was true at base and is b-e06dbc.

## What the reviews found

Both seats said ready. The Spec seat ran 22 probes over both criteria and
killed all 22, the lens's four included.

- A witness comment called `src/a.py` a near miss, though it is the plain
  control. Fixed in a review commit.
- `driver.py size` still counted tests after the cell's gate stopped. It
  measured #887 at 657 tokens, against 110 for the gate. Fixed in this PR.

## Run 40's items, checked

1. **REBUT's extraction and verdicts draw on money the rebuttal turn cannot
   spend (b-4901d2)**: done by hand in #884. Not tested hard, because REBUT
   spent $3.58.
2. **A batch's revision draws on the writer's share (b-b24cf7)**: done by
   hand in #886. It recurred in this batch, which started before the merge.
3. **The batch's preflight runs the citation check (b-d31930)**: recurred.
   `SA-0275`'s spec review again raised drifted citations as a concern.
4. **The `tests` gate keys failures on node ids (b-bba47a)**: did not recur.

The loop's own gaps from run 40:

- **The batch scans every candidate, not the order**: recurred. The order
  named one spec, and the batch reviewed two.
- **The ceilings check ignores revision cost**: smaller since #886. A
  revision now needs the spec's budget and $26.50 past the reserve.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-16 are the
evidence.

1. **The batch's preflight runs the citation check over each spec
   (b-d31930).** A gate change. #885 did by hand what this would do, and
   `SA-0275`'s review paid for it again.
2. **The loop's size readout reads the suite's own test paths.** A driver
   change, done by hand here. The driver still builds its own `size_gate`
   call, so the next keyword the suite adds will drift the same way.
3. **The spec writer checks every state a set names against the code that
   reads it.** A pre-flight check. `SA-0275`'s blocker was a closed list of
   four states that leaves out `NOT_IMPLEMENTED`, which `reconcile` asks
   about. It is the corpus's largest class.

## Next run

`SA-0275` needs one revision before its cell. A batch after #886 can pay
for it from the writer's share. A $30 spec's revision needs $56.50 past the
reserve and the spend so far. With two $2.50 reviews that admits at $80, so
$90 leaves a margin.
