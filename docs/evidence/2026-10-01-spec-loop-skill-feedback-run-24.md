# Feedback on run-saffron-spec-loop (run 24, 2026-09-30 to 10-01)

Run 24 queued the eight specs run 23 left of the `SA-0161` chain, `SA-0162`
through `SA-0152`. The operator asked for `SA-0162`'s spec revision first, and
then as far down the chain as the loop could go. Run 23's feedback is checked
below.

**Outcome:** three cells.
- The first two ended `EXHAUSTED` in REVIEW after green gates. The operator
  adopted both branches. The delegate opened each pull request by hand, added
  two review commits to each, and merged them: #626 for `SA-0162` and #628
  for `SA-0151`.
- The third, `SA-0174`, reached `READY_FOR_REVIEW` (#630). Its REBUT fixed a
  blocker inside the budget, the chain's first since `SA-0165`.
- Three spec PRs merged: #625, #627 and #629.
- The stack is #630 with step 5 on top.
- The cells cost **$105.40** against $85 of budget.

| Spec | PR | Spent | Green at | Implement turns | In-cell blockers | Seat blockers the critic passed | Review commits |
|---|---|---|---|---|---|---|---|
| `SA-0162` | #626 | $57.36 of $37 | $39.72 | 130 of 130, then 128 | 1, host probe | 1 witness | 2 |
| `SA-0151` | #628 | $30.67 of $25 | $21.31 | 164 of 200, then 39 | 2, host probes | 2 witness, 1 standards | 2 |
| `SA-0174` | #630 | $17.37 of $23 | $9.89 | 98 of 130, then 17 | 1 conventions, fixed in REBUT | 1 witness | 1 |

## What happened, in order

1. **The token files were refused, then approved.** The auto-mode classifier
   refused to write `cell.env` and `jev.env`, calling it credential leakage.
   The worktree guard also refused the skill's own inline `source ~/.secrets`
   form. Once the operator approved, two wrapper scripts (`cell.sh` and
   `jev.sh`) passed the guard.
2. **`SA-0162`'s spec took two more review rounds and two writer passes.**
   No round found a blocker. Measuring the arrangements at `main` found three
   false consequences that no review had caught. Round 4 found a "measured"
   label with no kept output. #625 merged on the operator's prior yes, and
   auto mode allowed it this run.
3. **`SA-0162`'s cell ended `EXHAUSTED` at $57.36 of $37.**
   - IMPLEMENT reached its 130-turn ceiling, and the repair went green.
   - The budget line printed "stopping" at $39.72. REVIEW then spent $17.64
     more, on four lenses and the wrong-version sweep.
   - The sweep found one witness blocker, and the budget refused REBUT.
   - The blocker needed a one-line test fix. The spec's "ready at a budget of
     1" was ambiguous, and the cell read it as the batch budget.
4. **The operator adopted the branch.** PACKAGE opens no pull request for an
   `EXHAUSTED` task, so the delegate opened #626 by hand. Two review commits
   fixed the cell's blocker, a seat blocker and four Standards concerns. The
   seat blocker was criterion 6's order, which had no `touches`. #626 merged.
5. **`SA-0151`'s parent-branch review found a parent built against its own
   spec.** `SA-0162`'s Problem item 4 asked for unrun task ids. The cell kept
   spec ids, and no lens or seat raised it as more than a note. `SA-0151`
   assumed task ids. The operator put the fix in `SA-0151` (#627).
6. **The cell image's git is 2.47.3, not the 2.39.5 two reviews and a writer
   quoted.** Running the measurement inside `saffron/cell:saffron` settled it.
7. **`next` held `SA-0151` back** because its parent was `EXHAUSTED`, though
   the parent's code was on `main`. The delegate started the cell by path.
8. **`SA-0151`'s cell went the same way: green at $21.31 of $25, `EXHAUSTED`
   at $30.67.** The four lenses raised no blocker. The host's probes raised
   two witness blockers, and REBUT was refused. The operator adopted it
   (#628). The seats then found three more blockers, among them a path check
   with no end anchor that would write outside `.saffron/specs/`. #628
   merged.
9. **`SA-0174`'s spec took four review rounds.** Round 2 found its parent's
   `stack_layers` carries no `task_key`. Round 3 found 60 declared wrong
   versions, which would starve one REVIEW session at the $2 floor. The writer
   trimmed them to 25 and kept the measurement output.
10. **`SA-0174`'s cell reached `READY_FOR_REVIEW` at $17.37 of $23.**
    - Its REVIEW cost about $6.43, and REBUT about $1.76.
    - 24 of its 25 declared versions were killed, and REBUT fixed a
      citation blocker.
    - The one version left unproven needed two edits, as round 4 predicted.
      The Spec seat built it, and it was killed.
    - The seats found one witness hole, a decoy the spec named but the
      witness never recorded.
11. **`SA-0177`'s parent-branch review found two blockers**, and it is
    handed to the next loop. One is a build blocker: its finish row takes its
    batch key from the task's run, not the selected layer. The other is a
    witness blocker.

## Run 23's items, checked

1. **REVIEW's adequacy lens misses witness holes the Spec seat finds**: partly
   absorbed. Both cells' host probe sweeps found real survivors, three
   blockers in all. The seats still found three more witness holes past them.
2. **b-f582ee, a transient seed failure after green**: not seen.
3. **The parent-branch review in the loop's machinery**: not absorbed. It
   found something real on every child again (`SA-0151`, `SA-0174`). That
   makes five runs of five.
4. **b-c07b92, `snapshot` takes the operator's order**: no `hold` was needed.
   The order was the chain.
5. **b-2dc561, preflight names the listener's process**: no new listener
   appeared.
6. **b-4ddb5b, `terms` passes at base**: still red at base in both cells.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` are the evidence.

1. **A green cell should never spend past its budget on a REVIEW it cannot
   answer (b-4c5dc7).** Both cells printed "stopping", spent $9 to $18 more,
   and could not fix a blocker of a few lines. Holding REBUT's share before
   REVIEW starts turns both nights into reviewable PRs.
2. **An `EXHAUSTED` task with green gates should still open a draft PR
   (b-038aef).** The delegate rebuilt two PR bodies by hand from the ledger.
3. **`next` should read a merged parent as merged (b-dc5212).**
4. **The parent-branch review belongs in `next`**, carried from run 23. It
   found a blocker or a build concern on every child this run as well.
5. **A Problem-item obligation needs a witness or a lens (b-426db4).** "Keep
   the task ids, as `int`s" had no criterion, so the cell dropped it, and the
   cost landed on the next spec.
6. **A spec's numbers in prose should be arguments, not sentences.** A
   witness budget and a `touches` list stated in prose were each built
   otherwise (witness C, criterion 6's order).
7. **The cost of declared wrong versions should be priced, not guessed.** One
   REVIEW session per criterion at a $2 floor means a long `wrong_versions:`
   list is cheap to write and costly to run. `check` could price it.
   `SA-0174`, trimmed to 25, spent about $6.43 on REVIEW and had room to
   REBUT. `SA-0162`, with 35, spent $17.64 and had none.

## The loop's own gaps

- The worktree guard refuses many plain compound shell commands. Among them
  are `container run … sh -c 'git …'`, a `sed` on a variable path and a
  heredoc into Python that names git. Scripts in the scratchpad pass.
- Seats emitted their findings blocks as YAML, or with text criteria and
  `file:line` paths. Jev refused them until the seat re-emitted the block.
  `REVIEW-PROMPT.md` should spell out the JSON shape Jev reads.
- Jev filed a round as `round-3` because run 23 left an empty `round-2`.
- The skill has no path for an `EXHAUSTED` cell the operator adopts: no PR
  body, no `stack` entry and no `size` (it refuses a non-reviewable task).
- The delegate's first commit carried a `Co-Authored-By` line, against the
  operator's global rule. The session's attribution reminder asks for one.
  It was amended before the push.
