# Feedback on run-saffron-spec-loop (run 42, 2026-10-16)

Run 42's order was `SA-0275` and `SA-0294`. The other 14 queued specs wait on
a chain that starts at `SA-0275`.

`SA-0275` ended `READY_FOR_REVIEW` at $14.99 of $30, its spec review
included. Batch 35 ran at $90 with `--stack`, spent $18.53 and stopped at
`BUDGET`. PACKAGE opened #893. `SA-0294` did not run.

## Before the run

Four by-hand pull requests landed between run 41 and this run.

- **#891 makes `driver.py check` run `cite` (b-d31930).** It reads each
  citation at the branch the spec's cell would be cut from.
- **#890 adds `SA-0294` and `SA-0295`.** They are the batch's arm of the
  same item.
- **#892 refreshed 18 citations and one criterion.** `check` blocked
  `SA-0275` on 16 citations and `SA-0294` on two, which #891 had moved. The
  criterion was run 41's item 3: `SA-0275` named four asked states and left
  out `NOT_IMPLEMENTED`.
- **`cite`'s match is loose both ways (b-2da959).** It passed ranges that
  had drifted, such as `ledger.py:314-321`, now 318-324. It flagged four
  ranges that were right, because the quoted name sat on the `def` line
  above.

## What happened, in order

1. **The ceilings check cleared both specs.** `SA-0275` cited 30 lines and
   all resolved, at 1132 of 3000 tokens. `SA-0294` cited 35, at 800 of 1300.
2. **The baseline found `main` red.** One test failed at the cell's base. It
   was #891's: a `check` test read the host's `origin/main`, and a cell's
   checkout has none. `make check` on the host had passed it three times.
3. **The spec review found one note and no blocker ($2.28).** It said
   `ledger.py` is in `elevate_on`, so the task runs `elevated`.
4. **IMPLEMENT took 124 turns of 150.** The first gate attempt was green.
5. **The lenses found nothing, then a probe found a blocker.** The host
   filed one: the ledger witness survived deleting `DELETE FROM regates`.
   REBUT added a raw read of the table for $1.95, and the lens withdrew it.
6. **The batch then stopped at `BUDGET` (b-f73cd0).** It listed 16
   candidates, not the order's two. `SA-0284` came second and needs $42.
   $26.47 was left, so the batch stopped. `SA-0294` needs $25 and fit.
7. **The end review raised one concern ($1.92 to draft a follow-up).**
   `Ledger.regate` returns `None` for an id naming no task. The draft was
   pooled, because it declared a `depends_on`.

## What the reviews found

Both seats said ready. The Spec seat ran 27 probes over the three criteria
and killed all 27, the lens's probe included.

- `regate` read an unknown id as a task with no re-gate. The end review and
  the Standards seat both raised it. Fixed in a review commit.
- Making it raise showed a vacuous check. The witness's reopen assertion
  passed because a fold had renumbered the tasks. Fixed in the same commit.
- The summary built a re-gate's count twice. Fixed in a review commit.
- `reconcile`'s `head_moved` comment is now false. Kept as b-60317d.

## Run 41's items, checked

1. **The batch's preflight runs the citation check (b-d31930)**: the
   driver's arm landed in #891. It caught 18 drifted citations before any
   money was spent. The batch's arm, `SA-0294`, did not run.
2. **The loop's size readout reads the suite's test paths**: did not recur.
   `size` reported 441 tokens and left 1123 test tokens out, as the gate does.
3. **The spec writer checks every state a set names**: done by hand in
   #892. The spec review found no such defect this time.

The loop's own gaps from run 41:

- **The batch scans every candidate, not the order**: recurred, and it cost
  `SA-0294` its run (b-f73cd0).
- **`stack --execute --top` refuses a stack of one layer**: recurred. The
  delegate marked #893 ready by hand.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-16 under
`SA-0275` are the evidence.

1. **A batch runs the loop's order, and a stop names what it could not pay
   for (b-f73cd0).** A phase change. The operator approved two specs, and
   the batch chose between 16 by budget alone.
2. **`cite` judges a citation by the construct it names (b-2da959).** A gate
   change, before `SA-0294` ports the check into core. The delegate read 18
   ranges by eye to tell real drift from noise.
3. **A test that reads the host's own repository fails on the host too.** A
   gate change. The cell's baseline caught #891's leak. A suite run in a
   checkout with no remote, before merge, would have caught it first.

## Next run

The reserve and the writer's share each take a quarter of `--budget`
(`saffron/cli.py:1782-1783`). Each candidate is checked against the other
half, less what the batch has spent.

Once #893 merges, `SA-0284` ($42) heads the chain and `SA-0294` ($25) sits
behind all 14 of its specs in a stack batch's order. So a batch reaches
`SA-0294` only after the chain stops, until b-f73cd0 lands. To run
`SA-0294` next, the operator can run it as one attended cell.
