# Feedback on run-saffron-spec-loop (run 40, 2026-10-14 to 2026-10-15)

Run 40's order was `SA-0273` then `SA-0274`. The 15 specs behind them form
one chain, and each waits on the one before it.

`SA-0273` ended `EXHAUSTED` at $50.91 of $45, its second spec review
included. Both batches spent $53.23. PACKAGE still opened draft #881. The operator chose to review it as
it stood. `SA-0274` never started, because its parent was not reviewable.

## What happened, in order

1. **The ceilings check blocked `SA-0273` before the run.** Its 180 turns sat
   below a past peak of 201. The operator raised it to 240 turns and $45 in
   #879.
2. **Batch 32 ran at $134 and no cell started.** The batch's spec review
   found 15 citations that had moved since the spec was written ($2.32). A
   revision needed $71.50, and $64.68 was left, because the batch charges the
   writer on top of the writer's share it holds back (b-b24cf7). Run 39's
   handoff had named the refresh as optional (b-d31930).
3. **The delegate refreshed the citations by hand in #880.** `driver.py
   cite` checked all 36.
4. **Batch 33 ran at $148.** The spec review found two notes and no blocker
   ($2.99). IMPLEMENT took 160 turns and $17.71 against a 240-turn ceiling,
   then one repair round cleared 27 new failures.
5. **REVIEW found two blockers.** The correctness lens said the exemption
   could never fire, because the `tests` gate keys failures on exception
   types. The delegate measured node ids instead, and so did the Spec seat.
   A host criterion probe found a witness that missed a `code` for `file`
   swap.
6. **REBUT ran out of its $10.** The rebuttal turn spent $7.53 and moved
   HEAD. Its extraction was cut at $3.07, so no rebuttal was recorded, and
   both verdicts were refused. The gates re-ran green, and the task ended
   `EXHAUSTED` (b-4901d2).
7. **The driver refused the PR again.** The delegate measured size through
   `_size` by hand: 2313 tokens as packaged, 2410 after review, against 3000
   (b-d5db52).

## What the reviews found

The seats found these defects that the critic missed. The delegate verified
each by a probe or by reading the line.

- Criterion 5's empty-patch leg asserted only a non-empty `why`. A build
  that kept the gates-are-red text survived. It is killed now.
- `revert` skipped an all-exempt diff saying it added no new test, and named
  only the first three exempt tests. A new witness fails at base.
- A comment cited a §5.4 note that section never makes. A clause restated
  `revert`'s failure code. Three test docstrings described their stubs
  wrongly.

The REBUT commit fixed the criterion probe's `code` for `file` swap. The
Spec seat killed it at head.

The Spec seat also found that the `tests` gate's regex can take a warning a
subprocess prints for every failure in the run (b-bba47a). That is outside
the spec's `touches`.

## Run 39's items, checked

1. **REBUT holds back the verdict's money (b-4901d2)**: recurred, and specced
   as `SA-0293`. This run cut the extraction, not the verdict. The reserve
   in `SA-0293` would not have saved it.
2. **The adequacy lens names a witness that drives only some cases**:
   recurred. The empty-patch leg drove the state but not the reason.
3. **The `terms` gate carries each _Avoid_ line**: did not recur.
4. **Every spec a batch's writer returns passes `prose` (b-703e64)**: not
   tested. No writer ran.
5. **The driver takes an `EXHAUSTED` task with an open PR (b-d5db52)**:
   recurred.
6. **Step 5's branch is cut from the top layer**: applied. It was cut from
   #881's head.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-15 are the
evidence.

1. **REBUT's extraction and verdicts draw on money the rebuttal turn cannot
   spend (b-4901d2).** A phase change. Two runs in a row ended `EXHAUSTED`
   with green gates, and `SA-0293` covers the verdicts only.
2. **A batch's revision draws on the writer's share it holds back
   (b-b24cf7).** A phase change. It stopped a whole batch here.
3. **The batch's preflight runs the citation check over each spec
   (b-d31930).** A gate change. A $0 check found what a $2.32 review found.
4. **The `tests` gate keys failures on node ids whatever its output holds
   (b-bba47a).** A gate change. A lens filed a false blocker from the
   comment that says otherwise.

## The loop's own gaps

- **`snapshot --new` names only the order, but the batch scans every
  candidate.** The batch listed all 17 specs. It stops only on budget or a
  refusal, so a cheap pair could start the next spec in the chain.
- **The ceilings check ignores the batch's revision cost.** A batch sized at
  twice the order cannot revise its largest spec until b-b24cf7 lands.
