# Feedback on run-saffron-spec-loop (run 72, 2026-11-15)

Run 72 kept the goal of runs 55 to 71: implement every backlog item. Run 71
wrote `SA-0393` to `SA-0396` through the spec chain and ran no loop, so its
findings are folded in here.

| Spec | PR | Outcome | Spend of budget | Turns of ceiling |
|---|---|---|---|---|
| `SA-0393` | #1214 | `READY_FOR_REVIEW` | $29.14 of $48 | 550 of 200 |
| `SA-0394` | #1215 | `READY_FOR_REVIEW` | $8.90 of $36 | 197 of 240 |
| `SA-0395` | #1216 | `READY_FOR_REVIEW` | $13.86 of $26 | 262 of 150 |
| `SA-0396` | #1217 | `READY_FOR_REVIEW` | $24.97 of $48 | 423 of 200 |
| `SA-0397` | #1218 | `READY_FOR_REVIEW` | $13.14 of $18 | 192 of 60 |
| `SA-0398` | #1219 | `READY_FOR_REVIEW` | $15.99 of $10 | 343 of 40 |

Batch 89 ran at `--budget 380` with `--stack --defer-end-review`. It spent
$76.88 and held a $95 reserve. Finish 89 spent about $39.49: $10.36 on the
end review and $29.13 on two follow-ups. The run spent about $116.37 of $380.
Turns count every phase, so REVIEW and REBUT sit inside each figure.

## What the run found

1. **A gate's own fixtures fail the gate.** `SA-0393` adds an `integrity`
   check for cited spec ids. Its test fixtures cite fake ids such as
   `SA-0399` in source text the check reads. A regate of #1214 fails the
   check 17 times. The PR accepts this once. A gate that reads source text
   needs a fixture spelling it skips.
2. **Six host criterion probes on test-only follow-ups were noise.**
   `SA-0397` and `SA-0398` touch one test file each. Their criterion probes
   edited production files the claims cite only as background. Each
   witness stayed green, which was right. REBUT withdrew four. Two stayed as
   recorded disagreement. Both seats on each PR dismissed all six. Filed as
   b-11e2ac.
3. **A follow-up's ceilings sit below what its REVIEW alone costs.** Finish
   89 gave `SA-0398` $10 and 40 turns. It spent $15.99 and 343 turns, and
   IMPLEMENT took $0.54 of that. A follow-up's ceilings price IMPLEMENT and
   leave out the four lenses and REBUT.
4. **The in-cell critic passed a guard with two holes.** `SA-0395`'s inert
   rule let an added side split a kept line. A call before the find, and a
   find that ends mid-line, both read as inert. Both seats found it. The
   correctness lens did not.
5. **Run 71's chain caught a §2.1 breach before any cell.** `SA-0395`'s
   first draft parsed Python with `ast` inside `saffron/`. Its first review
   blocked it. The rule now reads line patterns the repo declares in
   `.saffron/policy.yaml`, as `witness:` does.
6. **The finish's findings carry in-cell findings the review already
   settled.** Four correctness and conventions findings name each cell's
   own head and read `unverified`. Review commits fixed three of them, and
   b-e447ea holds the fourth. Nothing in the file says so, so step 5
   matches them by hand.
7. **`driver.py stack --top` leaves out the finishing layer.** Its link
   named #1214 to #1219 and #1222, and `gh stack link` refused to drop
   #1220 from the stack finish 89 linked. I ran the link by hand with all
   eight. A tool change: the driver reads the finish's layer as one of the
   stack's own.

## What the reviews found

- **#1214:** three claim members no witness drove. Two docstrings misstated
  `spec_ids`. A test helper restated `_exec_in`. All were fixed. A README
  under `done/` now contributes no id. `SPEC_ID_DIRS` spells `done` again,
  filed as b-e447ea.
- **#1215:** a file that is not UTF-8 now reads `None`. The critic raised
  it. Two comments now say "git index".
- **#1216:** the split-line guard and the witness's patterns, both fixed.
- **#1217:** the inert read named a file once per edit, and its comment did
  not say what it refuses. Both fixed. The cell's three adequacy blockers,
  withdrawn at REBUT, all die now.
- **#1218:** the note test restated the `prose` gate's limit and a narrower
  split. It now hands the note to the gate's own `check`.
- **#1219:** the witness matched one exact `git grep` argv. It now refuses
  any `grep` exec. A stale comment was reworded.

`.saffron/rejections.md` holds eleven lines for this run.

## Run 70's items, checked

- [ ] **A later commit reruns a task's recorded wrong versions:** open, on
  b-9efbe2.
- [x] **REVIEW refuses a wrong version's edit that removes nothing:**
  `SA-0394` to `SA-0396` (#1215 to #1217) close b-7fc792.
- [ ] **`driver.py check` refuses a spec body that quotes a mutant's
  `find`:** open, on item 080.
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.
- [ ] **`cite` flags a bare citation into a parent's changed file:** open,
  the other half of b-b664d1.

## Summary: what Saffron should absorb next

1. **A later commit reruns a task's recorded wrong versions.** A gate
   change, on b-9efbe2. Every layer here took review commits that no host
   probe reran.
2. **A criterion probe stays inside `touches` or its `subject:`.** A phase
   change, on b-11e2ac. All six host blockers on the follow-ups were noise.
3. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.
4. **A finish prices a follow-up's ceilings from past follow-ups.** A phase
   change, with no item yet. Item 3 measured REVIEW at most of the spend.
5. **`driver.py check` refuses a spec body that quotes a mutant's
   `find`.** A gate change, on item 080.
6. **`cite` flags a bare citation into a parent's changed file.** A tool
   change, the open half of b-b664d1.
7. **`driver.py stack` links a finish's layer.** A tool change, with no
   item yet. Item 7 linked it by hand.

This PR changes no skill text. It records `SA-0397` and `SA-0398` from
finish 89's ran texts.

## Next run

Run 73 takes the next items from `PRIORITY.md` through the spec chain.
