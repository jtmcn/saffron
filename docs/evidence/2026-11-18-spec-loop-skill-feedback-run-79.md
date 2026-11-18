# Feedback on run-saffron-spec-loop (run 79, 2026-11-18)

Run 79 kept the goal of runs 55 to 78: implement every backlog item. It ran
the five specs the chain merged during run 78 in one `--stack` batch.

| Spec | PR | Outcome | Spend of budget | Turns of ceiling |
|---|---|---|---|---|
| `SA-0408` | #1258 | `READY_FOR_REVIEW` | $38.65 of $64 | 529 of 300 |
| `SA-0409` | #1259 | `READY_FOR_REVIEW` | $17.21 of $31 | 327 of 135 |
| `SA-0410` | #1260 | `READY_FOR_REVIEW` | $21.70 of $56 | 340 of 245 |
| `SA-0411` | #1261 | `READY_FOR_REVIEW` | $13.70 of $34 | 319 of 190 |
| `SA-0414` | #1262 | `READY_FOR_REVIEW` | $39.15 of $64 | 572 of 300 |

Batch 96 ran at `--budget 550` with `--partial --stack --defer-end-review`.
At $330 it refused, since its admission total was $578. With `--partial` it
admitted four specs up front, and the fifth fit once the first four came in
under budget. The tasks spent $130.41, and finish 96's end review spent
$13.69 of the $137.50 reserve. Turns count every phase.

Finish 96 ran no follow-up. Its finishing layer, #1263, refreshes three
citations in `SA-0411`'s spec. It pooled two concerns, which b-15c480 and
b-2cf94c now hold.

## What the run found

1. **Every cell passed its review, and two PRs still held seat blockers.**
   `SA-0408`'s critic filed no blocker. The Spec seat found four witnesses
   that left a claimed arrangement undriven, each measured with a surviving
   probe. `SA-0414`'s REBUT fixed four host blockers, and the seat found two
   more gaps in the same witness. Run 78 saw the same shape.
2. **A host probe realized its wrong version as a no-op.** `SA-0410`'s host
   applied "matches each entry as a shell pattern" by deleting
   `--literal-pathspecs`. `ls-tree` never globs, so the edit changed
   nothing and REBUT was right to argue it down. Nobody asked what the flag
   does. The Spec seat measured it: it keeps a path that starts with `:`
   literal, and no witness pinned it.
3. **A finish read the reviewed heads and changed nothing.** Run 78's
   finish undid a review decision. Finish 96 read every layer after its
   review commit and raised only findings the reviews had settled.
4. **zsh broke two leased pushes.** `"saffron/SA-$n:$old"` reads `$n:` as a
   history modifier, so neither push ran. The loop ran under `bash -c`.
5. **Records statuses are `done`, not `closed`.** The first close of four
   items failed `tests/records` on the status value and then on a missing
   `closed:` key.

## What the reviews found

- `SA-0408`: four Spec blockers, all witness gaps. Two citation fixes, one
  of which the critic raised. A stale docstring list is filed as b-ce832b.
- `SA-0409`: no blocker. A comment lost its quotes in an em-dash rewrite.
- `SA-0410`: no blocker. A witness for the `:` path, a docstring that gave
  a false reason, and a sentence with no verb. All fixed.
- `SA-0411`: no blocker. Two comments overclaimed, and a fixture restated
  a helper. All fixed. The third copy of the policy read is b-8d3de1.
- `SA-0414`: two Spec blockers, both witness gaps. A deleted `ponytail:`
  comment is restored. The bare-task fold is b-15c480.

## Run 78's items, checked

- [ ] **A lens judges whether REBUT's fix observes behaviour:** open. Run
  79's REBUT fixes did observe behaviour, but `SA-0414`'s witness still
  missed two claimed parts.
- [x] **A finish reads a review commit's rationale before it grades:**
  held this run. Finish 96 read the reviewed heads and committed only a
  citation refresh. One clean run is not yet evidence of the fix.
- [ ] **`next-id` reserves an id for a draft:** open, on b-90c8fa. No chain
  ran this run, so it did not arise.
- [ ] **A wrong version's edit changes only the case it names:** open, on
  b-f06097.
- [ ] **REBUT re-runs a withdrawn probe's siblings:** open, on b-7f6ce2.
- [ ] **The `prose` gate reads an irregular participle:** open, on
  b-6b8896.
- [ ] **`integrity` reads a fixture's spec id as data:** open, on b-988eb9.
- [ ] **`driver.py check` refuses a spec body that quotes a mutant's
  `find`:** open.
- [ ] **The driver fills the seat prompts and lints a seat's patch:** open.
  This run used fixer agents, which ran the linters themselves.
- [ ] **`cite` flags a bare citation into a parent's changed file:** open.
  `SA-0411` needed a citation PR (#1257) before the batch.
- [x] **`driver.py stack` links a finish's layer:** the finish linked all
  six PRs itself this run.
- [ ] **`bookkeeping` runs the smoke test's flat corpus:** open.

## Summary: what Saffron should absorb next

1. **A host probe asks what the code it edits is for.** A lens change, with
   no item yet. Item 2 is the evidence: the probe chose a no-op edit, and
   the flag's real job went unwitnessed until a seat asked.
2. **The adequacy lens reads every arrangement a claim names.** A lens
   change, with no item yet. Item 1 is the evidence, for the second run.
3. **`next-id` reserves an id for a draft.** A tool change, on b-90c8fa.
4. **A wrong version's edit changes only the case it names.** A phase
   change, on b-f06097.
5. **REBUT re-runs a withdrawn probe's siblings.** A phase change, on
   b-7f6ce2.
6. **The `prose` gate reads an irregular participle.** A gate change, on
   b-6b8896.
7. **`integrity` reads a fixture's spec id as data.** A gate change, on
   b-988eb9.
8. **The driver pushes a reviewed layer with its lease.** A tool change,
   with no item yet. Item 4 is the evidence.
9. **`cite` flags a bare citation into a parent's changed file.** A tool
   change, the open half of b-b664d1.
10. **`bookkeeping` runs the smoke test's flat corpus.** A tool change,
    with no item yet.

This PR changes no skill text.

## Next run

Run 80 needs specs. No spec is queued, so the chain writes the next ones
from `PRIORITY.md`.
