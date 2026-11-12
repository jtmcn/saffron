# Feedback on run-saffron-spec-loop (run 65, 2026-11-12)

Run 65 kept the goal of runs 55 to 64: implement every backlog item. It ran
the four specs the chain wrote on 2026-11-11.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0375` | #1169 | `READY_FOR_REVIEW` | $24.53 of $40 |
| `SA-0376` | #1170 | `READY_FOR_REVIEW` | $15.60 of $32 |
| `SA-0377` | #1171 | `READY_FOR_REVIEW` | $24.99 of $30 |
| `SA-0378` | #1172 | `READY_FOR_REVIEW` | $77.22 of $40 |

Batch 83 ran at `--budget 350` with `--stack --defer-end-review`. With finish
83 it spent $163.79. The finish committed a finishing layer (#1173) and
went green.

## What the run found

1. **`SA-0378` overran its budget by $37.** Its first attempt failed the
   gates, and REPAIR plus a second attempt followed. IMPLEMENT took 331
   turns across both attempts, against 170 per attempt. §3 allows one
   attempt's overrun, so the overrun was accepted.
2. **Finish 83 pooled three follow-ups for `depends_on`.** `SA-0378`
   declares `depends_on`, and each follow-up draft copied it, twice per
   group. `_validate` refuses a follow-up's `depends_on`. b-4a9207 has the
   Record line.
3. **All three pooled findings were already fixed.** Each was a hash
   concern a REBUT or review commit had fixed. The finish ran main's code,
   which lacks `SA-0378`'s drop.
4. **Two of four PRs left a criterion's input undriven.** `SA-0377` never
   drove the one-failure suite. `SA-0378`'s control concern never anchored,
   so it could not tell a drop from no drop.
5. **The token file vanished mid-run.** The scratchpad's `cell.env` was
   gone when finish 83 started, so the first finish exited 2 before any
   cell. It was rebuilt from `~/.secrets`. The cause is unknown.
6. **The b-6dd608 flake hit a sixth time,** in `test_qualify`. It passed
   alone.
7. **`driver.py rebase` found nothing to rebase.** It reads each branch at
   origin, so local review commits held during the batch are invisible to
   it. The layers were rebased by hand with `git rebase --onto`.

## What the reviews found

- **#1169:** 2 notes, both comment wording. Every adequacy probe was killed
  at the head.
- **#1170:** 1 Standards note, a restated test double. The Spec seat's 22
  probes were all killed.
- **#1171:** 1 Spec blocker, the one-failure suite. Three Standards notes and
  the in-cell docstring concern were fixed.
- **#1172:** 1 Spec blocker, the control concern. Five notes and the in-cell
  hash concern were fixed, and b-19f43a was filed.

`.saffron/rejections.md` holds nine lines for this run.

## Run 64's items, checked

- [ ] **`census` reads a renamed parametrize id as a removed test:** open,
  on b-f30189.
- [ ] **REVIEW probes each guard the diff adds:** open. Run 65's two
  blockers were inputs a criterion named and its witness never drove.
- [ ] **A lens reads for a helper the diff restates:** open. Run 65 had
  three more: a test double, `hash_artifact` twice.
- [ ] **A wrong version's edit changes only the case it names:** open, on
  b-f06097.
- [ ] **A cell that dies after green is an `error`:** open, on b-f582ee.

## Summary: what Saffron should absorb next

1. **A follow-up writer never copies its origin's `depends_on`.** A phase
   change, on b-4a9207. It cost finish 83 all three follow-ups.
2. **A lens reads for a helper the diff restates.** A lens change. Six
   restated helpers across runs 64 and 65.
3. **REVIEW drives every input a criterion names.** A lens change. Four
   blockers in two runs were inputs the witness never drove.
4. **`driver.py rebase` sees local review commits.** A skill-tool change.
   It found nothing to move after a batch held its review commits.
5. **`census` reads a renamed parametrize id as a rename.** A gate change,
   on b-f30189.

This PR changes no skill text.

## Next run

No queued spec is left. Run 66 starts from the backlog's tier 1 items.
