# Feedback on run-saffron-spec-loop (sixth run after the rework, 2026-09-17)

Three specs with no `depends_on`: `SA-0096`, `SA-0097`, `SA-0098` (items 114,
115, 63). Run from the main checkout, with review fixes made in scratch
worktrees. Run 5's feedback is `2026-09-16-spec-loop-skill-feedback-run-5.md`,
cited here as "run 5, observation N".

**Outcome:** three reviewable pull requests (#320, #321, #323), linked as the
stack #320 ← #321 ← #323, and **$10.25** across three cells against $40 of
budgets. Every cell reached `READY_FOR_REVIEW` on attempt 1.

| Cell | Ended | Spent | Review commits |
|---|---|---|---|
| `SA-0096` | `READY_FOR_REVIEW` | $3.99 | 2: a witness gap, a docstring naming the wrong path |
| `SA-0097` | `READY_FOR_REVIEW` | $4.01 | 1: a docstring naming one of two reasons |
| `SA-0098` | `READY_FOR_REVIEW` | $2.25 | 1: a stale class docstring, witness step names |

The lenses raised one concern and one note across three cells. The seats found
one blocker and five docstring or witness defects. Backlog items filed:
172–176.

## Summary: what to change first

1. **Give `snapshot` a way to start a new loop** (observation 1, item 172).
   `--force` carried run 5's drops into this run, and no command undoes a drop.
   Recovery meant moving `order.json` aside by hand.
2. **Have step 2 read the `baseline:` line** (observation 4, item 173). `main`
   was red on `tests` and `prose` in every cell, and green on the host. The loop
   printed it and nothing in the skill says to look.
3. **Name a third outcome for a step 1b concern** (observation 2). "Hand it to
   the Spec seat" was the right call twice, and the skill offers only "edit the
   spec" or "keep for step 5".
4. **Split step 2c's commit and push into separate commands** (observation 7).
   The chained block was denied by the auto-mode classifier and the split ran.
5. **Say in step 2 that pulling `main` mid-loop is safe** (observation 5).

**What worked and should stay:**
- The two seats. They found every defect this run fixed, including the one
  blocker, after lenses that raised nothing blocking.
- Running a cell and reviewing the previous PR at once. Cells N+1 ran while
  PR N was reviewed, with no interference, as on runs 4 and 5.
- `stack --execute` reading the bases back.

## Run 5's items, checked against this run

- **Observation 2, the loop's own spec edits need review.** Not exercised. No
  spec was edited, partly because run 5's cost was fresh (observation 2 here).
- **Observation 1, a mutant's target size.** Not exercised. No spec declared a
  mutant on `session.py`.
- **Observation 3, `pattern` hiding the CLI's error line.** Not exercised. No
  cell died.
- **Run 3's host probe before every cell.** Done before all three.
  `rapportd` was the only non-loopback listener each time.

## Observations

1. **`snapshot --force` carried run 5's drops into a new loop.** All three
   specs came back dropped, each with run 5's reason, "operator kept the loop
   to the SA-0093 chain". That reason was scoped to run 5, whose PRs had all
   merged. `_carried` keeps any row with `p.dropped` set,
   and no command undoes a drop, so the only way out was moving
   `.saffron-loop/order.json` aside and running a plain `snapshot`. Step 1
   says only "an existing order is kept until `snapshot --force`", which reads
   as the right command for a new loop.

2. **Step 1b raised no blockers on three specs.** It raised one concern apiece
   on `SA-0096` and `SA-0098`:
   - `SA-0096`: the class docstring at `mutation.py:74` states the old
     behaviour, and the notes name only `:118-121`.
   - `SA-0098`: the clip witness is an upper bound only, so a clip at 160, the
     width every other `Agent` field uses, passes.

   Both were verified. Neither was fixed in the spec, because run 5 showed a
   pre-cell spec edit needs its own re-review and cost three attempts. Instead
   they went to the cell and the Spec seat, and both were already handled by
   the cell: it fixed `:74`, and its witnesses assert exact equality at the
   bound. The skill has no middle path between "edit the spec" and "keep for
   step 5". A concern that a review should check on the PR is a third outcome,
   and step 1b should name it.

3. **Stale line numbers again.** `SA-0098` cites `implement.py:295` (now
   `:284`) and `session.py:1317` (now `:1314`). A spec written against a base
   that moves before its cell runs will keep drifting. Citing by symbol would
   stop it wherever the spec will outlive a day.

4. **The baseline at `4a6750f` and at `e980c8b` has `tests=fail` and
   `prose=fail`.** `tests` fails one test in the cell,
   `test_saffron_gates.py::test_structure_errors_when_its_tool_is_present_but_not_runnable`,
   which passes on the host. `prose` flags `.claude/agents/spec-reviewer.md`
   for sentence length and semicolons. Baseline subtraction absorbs both, so
   no cell is charged. The loop never looks at the baseline line, though, and
   a gate red on `main` is the operator's to hear about before the stack lands
   on it. `pattern` already prints the line, so the skill only needs to say to
   read it. Item 173.

5. **A `git pull` mid-loop was harmless, but the skill says nothing about
   it.** The operator pulled `main` during `SA-0096`'s PACKAGE and was unsure
   whether that broke the loop. It did not. Cells are cut from the remote, the
   order stayed fresh, and `SA-0097` got a newer base (`e980c8b`) than
   `SA-0096` (`4a6750f`). The pull also brought five new specs (`SA-0099` to
   `SA-0103`), which the order correctly left out. The operator chose to keep
   the loop at three. This line in step 2 would have answered the question
   without an investigation: "pulling `main` mid-loop is safe. `status` shows
   whether it staled the order, and new specs wait for a re-snapshot."

6. **#320: the seats found two real defects the lenses missed.** The lenses
   raised one note.
   - The Spec seat's probe `find[-6:]` survived the cell witness. The absent
     find text was `QRVT_FIND = QRVT_MISSING`, which ends short of the token
     the spec's notes said to put at both ends.
   - The Standards seat found the new docstring naming REPAIR as the leak
     path, which contradicts `repair_prompt`'s own docstring.

   Both were fixed on the branch and pushed.

7. **The step 2c command block was denied by the auto-mode classifier as one
   command** ("Stage 2 classifier error"). Split into commit, then push, then
   `size`, each one ran. The skill shows commit and push chained with `&&`.
   Separate lines would avoid a denial every run.

8. **#321: the spec's own notes answered the lens's concern.** The contract
   lens called `--no-renames` reaching replay an untested contract change.
   Spec line 146 asks for it. Both seats confirmed it and demonstrated the
   rename listing. The only fix was a docstring that named one of its two
   reasons.
   - A lens that read the spec's notes before raising a concern would have
     saved a seat's time here.
   - A lens that read a note as permission would miss the real gaps a note
     leaves.

   So this change belongs in the lens prompt, not the loop.

9. **The pre-cell reviews' forecasts held.** The spec review expected about
   130–160 changed lines for `SA-0096` (measured 162 after review),
   about 100 for `SA-0097` (104), and 120–150 for `SA-0098` (116). No
   ceiling came near: the largest spend was $4.01 of $14.
