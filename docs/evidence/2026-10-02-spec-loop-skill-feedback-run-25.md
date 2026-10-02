# Feedback on run-saffron-spec-loop (run 25, 2026-10-01 to 10-02)

Run 25 picked up the `SA-0161` chain at `SA-0177`. The operator scoped it to
`SA-0177` and `SA-0167`, held the other three specs, and asked for
`wrong_versions:` lists trimmed at step 1b. Run 24's feedback is checked
below.

**Outcome:** two cells, both `READY_FOR_REVIEW`.
- `SA-0177` reached #636 on its first attempt.
- `SA-0167` reached #638 on its second attempt. The first was killed at PLAN
  by the idle bound.
- Three spec PRs merged: #634, #635 and #637.
- The stack is #636, then #638, with step 5 on top.
- The cells cost **$34.30** against $48 of budget, as the ledger records it.
  The killed PLAN session recorded $0.00, though it ran for 18 minutes.

| Spec | PR | Spent | Green at | In-cell blockers | Seat blockers the critic passed | Review commits |
|---|---|---|---|---|---|---|
| `SA-0177` | #636 | $7.44 of $20 | $3.91 | 0 | 0 | 1 |
| `SA-0167` | #638 | $26.86 of $28 | $10.37 | 2, fixed in REBUT ($6.40) | 0 | 1 |

## What happened, in order

1. **`SA-0177`'s spec took two more rounds after run 24's parent-branch
   review.** The writer applied both blockers. Round 3 found a witness hole:
   no step read the record after the last write. Round 4 found nothing
   blocking. #634 merged.
2. **`SA-0177`'s arrangement was measured at `main`.** Only
   `ORDER BY position DESC` reaches the top layer. The re-fold hangs every
   task on `b1`'s run, which is what drives the run-derived stamp.
3. **`SA-0177`'s cell went green at $3.91, and every lens was clean.** All 7
   declared wrong versions were killed. The Spec seat then ran all 12 step 1b
   builds. Every one that differs from the correct build was killed, except
   the `task_key` build the spec flagged as flaky.
4. **`SA-0167` took four spec rounds.** Each round found a criterion 4 witness
   that drove one member of a set:
   - a substring match of the commit line;
   - a catch of two exception types;
   - a policy check on `protected` alone.
   The operator merged #635, and #637 merged on the operator's yes.
5. **The empty-lease push was measured, not argued.** Host git 2.54.0 and the
   image's git 2.47.3 both reject with `stale info`. The review had named git
   2.39.5.
6. **`SA-0167`'s first cell died at PLAN** (b-d4e015). The gaps between
   events grew to 150 seconds, then one reached the 300-second idle bound.
   `next` skipped the `NOT_IMPLEMENTED` spec, so the re-run started by path.
7. **The re-run went green at $10.37.** Two adequacy probes survived, and
   REBUT fixed both inside the budget at $26.86 of $28. The 16 declared
   versions were all expressed and killed.
8. **#638's Spec seat ran 71 probes, and every one was killed.** This is the
   chain's first pull request whose seats found no witness hole past the
   critic.
9. **`SA-0167` measured 3462 tokens against the 3000 ceiling.** The operator
   kept it whole.

## Run 24's items, checked

1. **A green cell spends past its budget on REVIEW (b-4c5dc7)**: not seen.
   Both cells answered REVIEW inside their budgets. `SA-0167` left $1.14.
2. **An `EXHAUSTED` green cell opens no PR (b-038aef)**: not seen.
3. **`next` and a merged parent (b-dc5212)**: not seen. Each parent was
   `READY_FOR_REVIEW`.
4. **The parent-branch review belongs in `next`**: not absorbed. It found a
   witness blocker in `SA-0167` again. That makes six runs of six.
5. **A Problem-item obligation with no witness (b-426db4)**: not seen.
6. **A spec's numbers in prose**: not seen.
7. **Price the declared wrong versions**: still by hand. Trimming `SA-0167`
   from 20 to 16 left REBUT room again.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` are the evidence.

1. **The idle bound must not kill a session that is still writing
   (b-d4e015).** An unattended night loses the task, and its ledger reads
   $0.00. The runner can stream partial messages or emit a heartbeat.
2. **Run the spec's step 1b builds in REVIEW (b-ef8543).** The seats ran 96
   probes across both PRs, most of them builds REVIEW never ran. REVIEW runs
   only the declared ones. A seat is a hand step a phase could take over.
3. **The parent-branch review belongs in `next`**, carried from run 23.
4. **Keep holds across `snapshot --force` (b-8a6f43).** A scoped loop
   re-held three specs four times.
5. **A child's tree and its prompt carry different spec texts (b-1068ea).**
6. **`driver.py status --line` (b-a7e315).** The operator asks where the
   queue stands often enough to want it in the status line.

## The loop's own gaps

- `next` treats `NOT_IMPLEMENTED` as decided, so a re-run the operator asks
  for starts by path.
- Jev numbers rounds by its own count, so its round 5 was the delegate's
  round 4.
- The delegate's first dispatch to a writer carried a placeholder where the
  verbatim review belonged. A message with the report's path fixed it.
- The worktree guard refused `$VAR` arguments to `sed`, `python3` and `uv`,
  and compound commands that name git. Literal paths and scratchpad scripts
  passed.
- The operator's status line parses `driver.py status`'s table
  (`~/.claude/saffron-loop-line.py`). It breaks when the columns change.
