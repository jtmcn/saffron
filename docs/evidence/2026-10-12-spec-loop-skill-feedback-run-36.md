# Feedback on run-saffron-spec-loop (run 36, 2026-10-12)

Run 36 reran `SA-0269`, which run 35 left `EXHAUSTED`, and ran its child
`SA-0270`. The order held those two. The 15 specs behind them wait on
`SA-0270` or on each other.

Both became a stack, #855 and #856. `SA-0269` spent $35.95 of $52 and
`SA-0270` spent $28.25 of $52. The operator approved $156 for the stack batch
and $52 for the plain one.

## What happened, in order

1. **The first cell could not pass both `scope` and `tests`.** `SA-0269`
   removed `CRITIC_NETWORK`, and `tests/test_sigterm.py` imports it. That file
   sat outside `touches`. Attempt 2 fixed it and `scope` refused. Attempt 3
   reverted it and `tests` failed. The spec review passed the spec. #853 added
   the file and raised the ceilings to $52 and 240 turns.
2. **`test_queued_specs` misread a spec that first landed in a merge.**
   `_authored_at` used `git log -G`, which skips merge diffs. `SA-0269` and
   `SA-0270` arrived in merge `e1cff440`. So the check read the working tree,
   where the cell's own witnesses already stood. #853 reads a merge against its
   first parent. Its witness failed on both specs before the fix.
3. **`check` blocked `SA-0270`'s budget.** $37 sat below `SA-0269`'s $38.36
   before review. #854 raised it to $52. The auto mode classifier refused the
   merge until the operator said so in chat.
4. **Batch 25 found the runtime service stopped.** The network create failed
   with an XPC error. The batch exited 2 at $0 and wrote a `GATE_ERROR` row.
5. **Batch 26 found colima listening on port 53.** Preflight refused the cell.
   The operator chose to tolerate `limactl` for this run.
6. **The delegate priced the stack batch wrong.** A `--stack` batch holds back
   25% for the end review and 25% for the writer. At $156 that left $78 for
   cells. After `SA-0269`, $52 did not fit, so `SA-0270` never started.
   `saffron queue --stack` prints that arithmetic (b-0a08bf). The delegate
   did not run it.
7. **The end review found nothing new.** It read the packaged head and raised
   two import notes and the stale docstring the critic had raised. Its agent
   also read files under `/Users/scott/`, a path that exists nowhere.
8. **`SA-0270` ran in a plain batch.** `--stack` refuses a parent that is an
   open pull request from an earlier batch (b-e0e1cf). A plain batch holds
   nothing back.
9. **A review commit on the parent went stale under the child.** On #855 the
   delegate wrote three docstrings saying each script shares a subnet with
   every task. `SA-0270` moved tasks onto a pool, so all three became false.
   Two sat outside `SA-0270`'s `touches`. The operator chose to fix them on
   #856.

## What the reviews found

The seats found six defects the critic missed. The delegate verified each by
a probe.

- #855: the criterion 2 witness checked its recorders with `all()`, so two
  mutants survived.
- #855: `test_proxy.py` failed to collect at base, so its witness never ran.
- #855: three docstrings claimed a safety the code did not have.
- #856: the pool walk's witness passed with `exclude=name` dropped.
- #856: the cell deleted the setup of `SA-0269`'s witness. `SA-0269`'s own
  wrong version then passed it.
- #856: the `SUBNETS` comment the spec asked for was not written.

## Run 35's items, checked

1. **`witness` blocks at every risk tier (b-02d328)**: pending. Neither spec
   declared a mutant, so the gate reported `skip`.
2. **Preflight names a missing image (b-1c20da)**: pending. It recurred as
   item 4 above, a stopped service in place of a missing image.
3. **A lens that fails ends its task in a decided state (b-032c3e,
   b-f7a591)**: pending. It did not recur.
4. **A `terms` rule that resolves citations (b-54ad4f)**: pending. It did not
   recur.
5. **The adequacy lens names a default-valued witness (b-714ccd,
   b-20043f)**: pending. It recurred on #855 as an `all()` over an empty list.
6. **The spec reviewer checks prescribed text (b-aff9ea)**: pending. It did
   not recur.
7. **An end review over the reviewed heads (b-8a0c9a, b-27bacc)**: pending.
   It recurred as item 7 above.
8. **A driver that reads the batch's own stack (b-f10412)**: pending. A two
   layer stack linked in order.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-12 under run 36
are the evidence.

1. **The queue refuses a spec that leaves a reader of a removed name outside
   its `touches` (b-1c59c3).** A gate change, and the costliest miss here at
   $41.03. One `git grep` per removed name decides it.
2. **A child's edit to a parent's witness re-runs the parent's wrong versions
   (b-9efbe2).** A gate change. The versions are already on disk.
3. **Preflight asks whether the cell runtime is up (b-1c20da).** A gate
   change, carried over from run 35.
4. **The adequacy lens names a witness that passes on an empty recorder
   (b-20043f).** A lens change, carried over from run 35.
5. **An end review over the reviewed heads (b-8a0c9a, b-27bacc).** A phase
   change, carried over from run 33.

## The loop's own gaps

- **Price the batch with `saffron queue --stack --budget`.** The skill should
  name the command before step 2 starts a batch.
- **Ask for the merge grant with the push grant.** A spec fix merged before a
  rerun needs it, and the classifier refuses it without words in chat.
- **A review commit's text is part of the stack.** Before linking, reread
  each review commit's prose against the layers above it.
- **A tolerated listener is the operator's call per run.** `limactl` joined
  `rapportd` and `RAATServe` for this run only.
