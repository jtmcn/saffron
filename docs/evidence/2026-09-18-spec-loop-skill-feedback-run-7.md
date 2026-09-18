# Feedback on run-saffron-spec-loop (seventh run after the rework, 2026-09-17/18)

Five specs: `SA-0104`, `SA-0099`, `SA-0100`, `SA-0103` (on `SA-0100`) and
`SA-0105` (items 154, 164, 165, 167, 176). Run from the main checkout, with
review fixes and spec edits made in scratch worktrees. Run 6's feedback is
`2026-09-17-spec-loop-skill-feedback-run-6.md`, cited here as "run 6,
observation N".

**Outcome:** five reviewable pull requests, linked as the stack
#335 ← #338 ← #339 ← #342 ← #340. The cells cost **$19.12** against $68 of
budgets. Every cell reached `READY_FOR_REVIEW` on attempt 1, the first loop
where all of them did.

| Cell | Spent | Spec reviews | Review commits |
|---|---|---|---|
| `SA-0104` | $3.43 of $14 | 1 | 2: scratch cleanup unwitnessed and stale comments, then 64 KiB pieces |
| `SA-0099` | $5.26 of $16 | 1 | 1: `CHECK` a second list, two witness gaps, comments |
| `SA-0100` | $4.01 of $16 | 5 | 1: note unpinned, row counts untested, 314 lines over 300 |
| `SA-0103` | $3.43 of $12 | 3 | 1: warning wording, redundant flag, comments |
| `SA-0105` | $2.99 of $10 | 2 | 1: an 18-line docstring |

Two spec pull requests ran before the cells they fixed: #333 (`SA-0100`,
`SA-0105`) and #341 (`SA-0103`). Step 1b found six verified blockers across
three specs. Backlog items are filed in the same pull request as this file.

## Summary: what to change first

1. **Stop `snapshot --force` widening the loop without saying so**
   (observation 1). It added two specs the operator had not scoped, with no
   spec review, and `next` named one of them.
2. **Give step 1b a stop rule and a cheaper edit loop** (observations 2–4).
   `SA-0100` took five spec reviews. Each of reviews two to four found a new
   hole, and two came from the delegate's own edits.
3. **Add a spec-review check for tools measured on the host** (observation 5).
   `SA-0105` measured git on the host (2.54) for a cell that runs 2.39.5. It
   would have failed every witness. Item b-b5f379 covers the image.
4. **Put the comment-length rule where a cell reads it** (observation 7). All
   five cells wrote comment preambles, and every one was cut in review. This is
   the third loop running with that rejection.
5. **Let `next` respect a spec edit in flight** (observation 6).

**What worked and should stay:**
- Step 1b. It found six blockers that would each have cost a cell attempt, and
  all five cells then passed on attempt 1.
- The `{KNOWN}` outcome from run 6, observation 2. `SA-0104`'s step 1b concern
  about scratch cleanup reached the Spec seat, and the adequacy lens raised the
  same gap in the cell.
- The two seats. They found a defect in every pull request, including four
  witness holes that three lenses missed.
- REBUT. `SA-0103`'s adequacy blocker was fixed in the cell with a new test,
  and the lens withdrew it after checking the fix.
- Reviewing PR N while cell N+1 ran, as in runs 4 to 6.

## Run 6's items, checked against this run

- **Observation 1, `snapshot --new`.** Worked on the first try.
- **Observation 2, a third outcome for a step 1b concern.** Used for `SA-0099`,
  `SA-0103` and `SA-0104`.
- **Observation 4, read the `baseline:` line.** Read in every cell. Main is
  still red on `tests` and `prose` with the same two failures. Item 173 is
  open.
- **Observation 5, pulling `main` mid-loop.** Main moved three times (#333,
  #336, #341) with no effect on the loop.
- **Observation 7, split commit and push.** No push was denied this run.
- **Observation 3, stale line numbers.** Recurred in four of five specs. See
  observation 8.

## Observations

1. **`snapshot --force` added specs to the order silently.** The first
   snapshot refused `SA-0101` and `SA-0102` on an unmet `depends_on`. After
   #341 merged, `snapshot --force` picked up `SA-0103`'s new `spec_sha`, and it
   also added both refused specs, because `SA-0099` had reached
   `READY_FOR_REVIEW` by then. Its output listed them in the order with no
   "added" line. `next` then named `SA-0101`, which had no spec review. The
   operator had scoped the loop to five, and dropped both. Item b-afec7c.
   - `--force` should print each spec it adds.
   - `--force` should keep new specs out of the order unless asked.
   - `next` could refuse a spec with no recorded step 1b review.

2. **`SA-0100` took five spec reviews, and each of reviews two to four found a
   new witness hole.**
   - Review 1 found two blockers: a witness that passed at base, and a claim the
     production note contradicts.
   - Review 2 promoted a concern from review 1 to a blocker, once the edit had
     pinned a neighbouring criterion.
   - Review 3 found a false claim that the delegate's own edit had introduced:
     `REBUTTING` "never reaches the `else:`". It does, and the claim invited a
     state-list guard.
   - Review 4 found that a write guarded on a successful push passed every
     witness.
   - Review 5 was clean.

   Each review cost about four minutes and no cell money. The cell then passed
   on attempt 1, so the reviews paid. What the skill lacks is a stop rule.
   This run used "a review with no blocker and no concern ends it", and the
   operator chose a fifth review. The skill should also say:
   - Before sending an edited spec back for review, walk every concern from
     earlier reviews against the edit. Review 2's blocker was review 1's concern.
   - The re-review prompt lists the operator's decisions and the deferred items
     so the reviewer does not raise them again. Reviews 4 and 5 used this, and
     it cut noise.

3. **Re-review on the spec branch, before merge.** The skill says to re-review
   after the edit merges and `snapshot --force` runs. This run pointed the
   reviewer at the spec file on the unmerged branch, with `base: origin/main`,
   and merged only once the review was clean. That saved one merge per round:
   #333 carried four edits and merged once.

4. **The delegate's spec edits are code that nobody else has checked.** Two of
   the six blockers step 1b found after the first round were introduced by the
   delegate's own edits: `SA-0105`'s first-line read raised on an empty range,
   and `SA-0100`'s `REBUTTING` claim. Run 5, observation 2 found the same. The
   re-review rule holds, and it is what caught both.

5. **A git behaviour measured on the host broke in the cell.** `SA-0105` told
   the cell to splice `--no-patch` between `DIFF_FLAGS` and `--shortstat`, as
   measured on git 2.54. The cell image is `python:3.12-slim-bookworm` with
   Debian's git 2.39.5, and there the recipe prints nothing in either position.
   Measured in `saffron/cell:saffron`. The spec reviewer found it by reading
   the Dockerfile and an old evidence script, not by a rule. The Spec seat on
   #340 then found the reverse: the same edit passes every witness on the host.
   - Spec-review check: a claim about a tool's behaviour must say which side it
     was measured on. The cell runs the `tests` gate.
   - Item b-b5f379 moves the image to trixie (git 2.47.3, measured) and
     proposes a host/cell version check.

6. **`next` named a spec whose edit was still open.** While #333 was unmerged,
   `next` named `SA-0100`. A cell started then would have run the old spec
   text. The delegate started `SA-0099` by hand instead. `status` also showed a
   running cell as `pending`. A `hold SA-NNNN --why` command, or `next`
   skipping a spec file that differs from an open pull request's head, would
   stop this.

7. **Every cell wrote a comment preamble.** The preambles ran 4, 15 plus 13,
   11, 7 and 18 lines. `SA-0105`'s 18-line docstring answered a spec note that
   asked for "a short comment on the read". The operator's rule ("1–2 lines
   covering only the non-obvious why") lives in their private instructions. No
   line in this repo's `CLAUDE.md` says it, and a cell reads only that. This is
   the third loop with this rejection. A spec's long notes also seem to become
   the cell's long comments. Item b-122686.

8. **Stale line numbers in four of five specs, again.** The worst pointed at
   the wrong code (`SA-0099`'s `session.py:2317` landed in an unrelated
   return). The drift came both from `main` moving and from stacking:
   `SA-0100` added three import lines, and every `task.py` cite in `SA-0103`
   moved. Citing a symbol in place of a line would stop both.

9. **The delegate's own probes failed silently twice.** Two find-and-replace
   probes on #338 did not apply, and the script still printed a test result
   (`1 passed`). REVIEW-PROMPT.md warns the seats about this. The delegate
   needs the same guard. A `driver.py probe FILE FIND REPLACE -- <pytest args>`
   that refuses when the find misses would make it mechanical.

10. **Size estimates did not track the witnesses the reviews added.** Step 1b
    estimated 150–220 lines for `SA-0100`. The reviews then asked for five
    scenarios in one file, and the cell landed at 314. The review trimmed it to
    293. A re-review could re-estimate size after each edit.

11. **Small corrections to SKILL.md and REVIEW-PROMPT.md.**
    - Step 5 says "next id = highest existing + 1". Since #336, items after 177
      take `uv run python -m records new-id`.
    - Step 2c(1): a finding's `probe` is `{file, find, replace}`, not a string.
    - `{BASE}` is the merge base. After PACKAGE, that is `main` at packaging
      time, not the base the cell was cut from. The "new witness fails at base"
      check should use the base from the log's `cell:` line.
    - `stack`'s dry run errors with one pull request ("a stack needs two or
      more"), yet step 2c runs it after every push.
    - `make check` exits 2 when `ruff format` rewrites a file. Running
      `make fmt` first avoids a second run.
