# Feedback on run-saffron-spec-loop (run 67, 2026-11-13)

Run 67 kept the goal of runs 55 to 66: implement every backlog item. It
queued one spec, `SA-0381`, whose citations #1182 moved after run 66.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0381` | #1183 | `READY_FOR_REVIEW` | $17.12 of $30 |

Batch 85 ran at `--budget 76` with `--stack --defer-end-review`. The batch
refused $75, since it needs the spec's budget plus its reserve. Finish 85's
end review spent $1.15, wrote no follow-up and committed no finishing layer.
The cell used 242 turns across its phases, 90 of them in IMPLEMENT, against
a ceiling of 200.

## What the run found

1. **REBUT closed a probe by tuning the witness to one character.** The
   host's probe skipped the cut for any draft holding `&`. The implementer
   added an unused `&flow_deps` anchor, and the lens withdrew its blocker.
   The same probe with `#` or `*` survived. Both seats found it. Filed as
   b-7f6ce2.
2. **A lens cited a tree REBUT then moved.** The conventions lens named a
   helper that the head no longer held. Finish 85 marked it `unverified`,
   since its line changed after the critic read it. That is b-1b05be working.
3. **No spec carries a mutant on the ref.** `refs/saffron/mutants` does not
   exist on origin. Three spec reviews asked for one. Recorded on item 080.
4. **The spec chain ran beside the loop.** Three writers drafted `SA-0384`,
   `SA-0385` and `SA-0386` while the cell and its review ran. Each first
   review found one blocker or none.
5. **The finish found a note the seats missed.** Its standards lens saw a
   witness import `hash_artifact` beside the module's own import. It was
   fixed in a review commit.

## What the reviews found

- **#1183:** 1 Spec blocker, the `#` sniff mutant. Three notes on the same
  class and on stale lens text. Two were fixed, with the finish's import
  note. One note was kept: the module docstring gained three sentences where
  the spec asked for one.

`.saffron/rejections.md` holds three lines for this run.

## Run 66's items, checked

- [ ] **`driver.py check` runs `cite` at each layer's base:** open, with
  progress. `SA-0384` is written for b-b664d1 and makes `cite` refuse a
  citation no single construct holds.
- [ ] **REVIEW drives every input a criterion names:** open. #1183's
  blocker was again an input no witness drove.
- [x] **A follow-up writer never copies its origin's `depends_on`:**
  `SA-0381` (#1183) cuts those lines before `_validate` reads them.
- [ ] **A reset past six hours waits six hours:** open. `SA-0385` is written
  for b-45783e.
- [ ] **`census` reads a renamed parametrize id as a rename:** open, on
  b-f30189.

## Summary: what Saffron should absorb next

1. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2. A witness tuned to one mutant's text still lets its class
   through.
2. **`cite` refuses a citation no single construct holds.** A tool change,
   on b-b664d1, and `SA-0384` is its spec.
3. **A reset past six hours waits six hours.** A batch change, on b-45783e,
   and `SA-0385` is its spec.
4. **Specs that edit code put a mutant on the ref.** A gate change, on item
   080. No spec does today.
5. **`census` reads a renamed parametrize id as a rename.** A gate change,
   on b-f30189.

This PR changes no skill text.

## Next run

Run 68 runs `SA-0384`, `SA-0385` and `SA-0386` once their spec PRs merge.
