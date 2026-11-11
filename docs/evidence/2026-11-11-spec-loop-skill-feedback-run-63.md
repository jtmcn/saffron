# Feedback on run-saffron-spec-loop (run 63, 2026-11-11)

Run 63 kept the goal of runs 55 to 62: implement every backlog item. It ran
one spec the chain wrote this session, `SA-0371` (#1153), for b-7c88f8.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0371` | #1158 | `READY_FOR_REVIEW` | $31.32 of $45 |

Batch 81 ran at `--budget 110` with `--stack --defer-end-review`. One $45
spec needs $106 before it is admitted. The cell spent $28.22, and the batch's
spec review spent $3.10. IMPLEMENT took 137 of its 160 turns.

## What the run found

1. **REVIEW asked every probe it named.** This is the fix's own subject. It
   named 30 criterion probes and expressed all 25 wrong versions. None was
   filed `unproven`.
2. **REBUT answered every blocker.** The adequacy probes filed 5. REBUT moved
   the head, and its re-probe killed all 5.
3. **A `killed` wrong version still hid a witness gap.** The spec declared
   "the fresh cell is handed a fresh `created` set". REVIEW's edit changed
   both cells, so the first cell's identity assert killed it. The Spec seat
   changed only the fresh cell, and the witness passed. b-f06097 is filed.
4. **`terms` passed an avoided word again.** The new text called the fresh
   cell "one retry". "Retry" is on two `_Avoid_` lines. b-8220e6 has the
   Record line.
5. **The b-6dd608 flake hit four times today.** It failed one test per full
   suite, in `test_qualify` and `test_batch`. Each passed alone.
6. **Finish 81 drafted a follow-up its own suite refused.** It turned the
   settled Not covered concern into `SA-0375`. The draft failed `prose` on 27
   lines and the records check, so the finding was pooled and nothing was
   committed. b-4a9207 has the Record line.
7. **#1157 merged before any CI check reported.** The watch returned at
   once, since no check had started yet.

## What the reviews found

- **Spec seat:** 1 blocker. The witness checked the fresh cell's `created`
  set by equality. It ran 28 probes, and 27 died.
- **Standards seat:** 2 concerns and 1 note. "Retry" and "attempt" named a
  cell entry. A comment framed an old constant as the new path's alone.
- Review commit `d754074f` fixed all four. The second entry's identity is
  now asserted in four scenarios, and the seat's probe now dies.

`.saffron/rejections.md` holds four lines for this run. One item was filed,
b-f06097. Record lines went to b-7c88f8, b-8220e6, b-4a9207 and b-6dd608.

## Run 62's items, checked

- [x] **REVIEW does not reach `READY_FOR_REVIEW` on a probe set it never
  asked:** partial, by #1158. A stopped probe cell earns one fresh cell. A
  session that errors is still open on b-7c88f8.
- [ ] **The finish drops a critic finding that REBUT or a review commit
  changed:** open. b-1b05be is partial again, and its fix waits on REVIEW
  recording the tree the critic read.
- [ ] **A cell that dies after green is an `error`, not `EXHAUSTED`:** open,
  on b-f582ee.
- [ ] **An adopted task joins its batch's stack:** specced as `SA-0373`.
- [ ] **A finish fixes a one-line finding in its finishing layer:** open, on
  b-4a9207.

## Summary: what Saffron should absorb next

1. **A wrong version's edit changes only the case it names.** A phase
   change, on b-f06097. Run 63's one blocker was a version REVIEW filed
   `killed`.
2. **REVIEW records the tree the critic read.** A phase change, on b-1b05be.
   The finish can then drop what REBUT fixed.
3. **`terms` reads every `_Avoid_` line.** A gate change, on b-8220e6. It
   missed "retry" in run 63 and "parent" in run 49.
4. **An adopted task joins its batch's stack.** `SA-0373`, queued.
5. **A cell that dies after green is an `error`.** A phase change, on
   b-f582ee.

This PR changes no skill text.

## Next run

`SA-0372`, `SA-0373` and `SA-0374` are queued for run 64.
