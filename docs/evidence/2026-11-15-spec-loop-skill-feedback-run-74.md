# Feedback on run-saffron-spec-loop (run 74, 2026-11-15)

Run 74 kept the goal of runs 55 to 73: implement every backlog item. Run 73
wrote `SA-0399` to `SA-0402` through the spec chain. This run took the first
two, since `SA-0401` and `SA-0402` depend on them.

| Spec | PR | Outcome | Spend of budget | Turns of ceiling |
|---|---|---|---|---|
| `SA-0399` | #1227 | `READY_FOR_REVIEW` | $12.83 of $22 | 200 of 150 |
| `SA-0400` | #1228 | `READY_FOR_REVIEW` | $11.54 of $48 | 188 of 200 |

Batch 92 ran at `--budget 172` with `--stack --defer-end-review`. It held a
$43 reserve. Finish 92 spent $3.88 on the end review, found nothing and ran
no follow-up. The run spent about $28.25 of $172. Turns count every phase.

## What the run found

1. **Both cells passed four clean lenses, and both PRs held a blocker.** Each
   Spec seat found a declared claim member that no witness drove. `SA-0399`'s
   sample had no line that tells exact part comparison from a stripped one.
   `SA-0400`'s claim named a second call that the cell put in a separate test.
   This is the class runs 13 to 72 keep naming.
2. **REVIEW filed a wrong version `killed` for a reason the version does not
   name.** `SA-0400`'s wrong version 14 says the refusal is made inside the
   probe cell. The cell's edit also sent refused pairs to the mutator, and the
   witness caught that. The seat's faithful edit passed. This is b-f06097
   again, now with a Record line.
3. **The host's adequacy blocker on `SA-0399` was real, and REBUT fixed it.**
   The fix counts reads per file. Both seats ran it and called it a real
   strengthening. A stray read in the same file still passes it, but
   criteria 1 and 3 hold that case.
4. **Another project's database stopped the batch at preflight.** Colima
   forwarded the `chili` project's Supabase ports on every interface. Batch 91
   refused, which was right. The operator chose to stop those containers.
   Nothing in Saffron needs to change.
5. **A reboot wiped the scratchpad.** It took the env files, the worktrees, a
   spec draft and the seat-prompt helpers. The helpers were rebuilt by hand.
   Filling `REVIEW-PROMPT.md` and saving each seat's report are both still
   hand steps. My rebuilt saver first kept the hand-back's indent, so Jev
   refused the report until it was fixed.
6. **`driver.py bookkeeping` said the smoke test owed no change.** It
   did owe one. The smoke test lays every retired spec out in one directory.
   There `SA-0151` and `SA-0399` both name `RETIRED_DIRNAME`, so the scheduler
   refused `SA-0399` for an undeclared parent. `make check` found it after
   eleven minutes. A step 5 commit pins that refusal by id.
7. **The finish had no layer to link.** Finish 92 changed nothing, so run 72's
   item 7 went unexercised.

## What the reviews found

- **#1227:** a detector that strips each part passed the sample. The
  tripwire assertion had no message. A comment said a retired spec ships to
  the directory. All three were fixed.
- **#1228:** the declared witness left out the claim's second call, so a
  refusal inside the cell passed it. Three docstrings called the refusal a
  check. Both were fixed. The seat's own wrong-version edit now fails the
  witness on its `log` assertion.

`.saffron/rejections.md` holds five lines for this run.

## Run 72's items, checked

- [ ] **A later commit reruns a task's recorded wrong versions:** open, on
  b-9efbe2.
- [x] **A criterion probe stays inside `touches` or its `subject:`:**
  `SA-0400` (#1228) closes b-11e2ac.
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.
- [ ] **A finish prices a follow-up's ceilings from past follow-ups:** open,
  with no item. Finish 92 ran no follow-up.
- [ ] **`driver.py check` refuses a spec body that quotes a mutant's
  `find`:** open, on item 080.
- [ ] **`cite` flags a bare citation into a parent's changed file:** open,
  the other half of b-b664d1.
- [ ] **`driver.py stack` links a finish's layer:** open, with no item. This
  run had no finish layer.

## Summary: what Saffron should absorb next

1. **A wrong version's edit changes only the case it names.** A phase
   change, on b-f06097. Item 2 is its second instance, and both hid a
   surviving version behind `killed`.
2. **A later commit reruns a task's recorded wrong versions.** A gate
   change, on b-9efbe2. Both layers took review commits no host probe reran.
3. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.
4. **A finish prices a follow-up's ceilings from past follow-ups.** A phase
   change, with no item yet.
5. **`driver.py check` refuses a spec body that quotes a mutant's
   `find`.** A gate change, on item 080.
6. **The driver fills the seat prompts and saves the reports.** A tool
   change, with no item yet. Item 5 rebuilt both by hand.
7. **`cite` flags a bare citation into a parent's changed file.** A tool
   change, the open half of b-b664d1.
8. **`driver.py stack` links a finish's layer.** A tool change, with no
   item yet.
9. **`bookkeeping` runs the smoke test's flat corpus.** A tool change, with
   no item yet. Item 6 left it to the suite.

This PR changes no skill text. It pins one smoke-test refusal.

## Next run

Run 75 takes `SA-0401` and `SA-0402` once this stack merges.
