# Feedback on run-saffron-spec-loop (fourth run after the rework, 2026-09-16)

Five specs, all of run 3's leftovers: `SA-0088` → `SA-0089` → `SA-0091` (a chain)
plus `SA-0090` and `SA-0092`. Run from the main checkout, driver as of `d48e466`'s
parent. Run 3's feedback is `2026-09-15-spec-loop-skill-feedback-run-3.md`; its
items are cited here as "run 3, item N".

**Outcome:** five reviewable pull requests (#277, #278, #279, #282, #284), linked
as stack #285, and **$39.17** spent across five cells. Every cell passed its gate
suite on attempt 1; no repair round ran anywhere in the run. Backlog items filed:
137–150.

## Summary: what to change first

1. **`size` is wrong for a stacked branch** (observation 3). It measures from the
   merge base with the default branch, so a child counts its parents' diff:
   `SA-0089` was reported as 776 of 600, "ask the operator (item 40)", when the
   in-cell gate had recorded 477. The skill's step 2c routes that number to the
   operator as a judgement call, so the loop asks the operator to rule on a
   number that means nothing — and a three-deep stack triples it. Item 138.
2. **Editing a spec whose pull request is open silently refuses its dependents**
   (observation 1). Cost two pull requests and a round trip. Nothing warns at
   edit time; both explanatory messages appear only on the next
   `snapshot --force`, after the edit has merged. Worse, the held-out spec loses
   its recorded outcome, so `stack` later printed a stack with its pull request
   missing — which would have retargeted a child off its parent onto `main`.
   Item 137.
3. **`pattern` omits `SALVAGE`** (observation 4). The Monitor showed
   `IMPLEMENT: cut off at the turn ceiling with nothing committed — spending one
   turn to salvage it` and then nothing. Whether the cell had anything left to
   gate was invisible without tailing the log. Item 139.

**What worked and should stay:** the up-front push question; `snapshot`'s table;
`record`'s spend line; the two seats, which again found what the lenses did not;
and step 1b, which paid for itself twice this run (observation 2).

## Run 3's items, checked against this run

- **Item 1, the N1 host probe mid-loop.** Re-run before every cell, as run 3
  asked. `rapportd` was the only non-loopback listener at all five checks; no
  cell was refused. The GOTCHAS line run 3 wanted is still unwritten, but the
  practice worked.
- **Item 2, `stack`'s dry run on a single reviewable pull request.** Not
  exercised — the run never had exactly one. Still open.
- **Item 3, a mutation probe reverting with `git checkout --`.** Followed run 3's
  fix throughout: every probe backed the file up with `cp` and restored from
  that. No edits were lost. Closed as far as this run can close it.

## Observations

1. **A spec edit mid-loop broke the dependency chain, and the recovery was
   incomplete.** After reading `SA-0088`'s review the operator retyped its spec
   `bug` → `feature` — a legitimate thing to want, since the review is what
   produced the evidence. The next `snapshot --force` held `SA-0088` out of the
   order and refused `SA-0089` and `SA-0091` behind it. Reverting the two lines
   restored the exact sha (verified by hashing before committing), but
   `--force` could not put `SA-0088` back: its pull request was open, so the
   queue's conflict set refuses it. `driver.py stack` then printed
   `gh stack link 282 284 278 279` — without #277 — which would have retargeted
   #282 from `saffron/SA-0088` onto `main`, a base `PACKAGE` had already set
   correctly. The stack was linked by hand as `277 282 284 278 279` and every
   base read back.

2. **Step 1b paid for itself twice, and both were visible in the plan.**
   `SA-0089`'s notes named one holder of the subnet space; the obvious next pick
   after reading `10.88.0.0/24` is the proxy's `10.89.0.0/24`, and
   `_stub_the_runtime` stubs `create_network` to a no-op so no witness could see
   the collision. Live it raises at REVIEW, after IMPLEMENT is paid, as exit 2
   charged to nobody. `SA-0091` made the reviewed diff's *position* load-bearing
   while telling the agent block order was out of scope. Both were amended before
   their cells, and both fixes were visible in the resulting plans — the
   `SA-0089` plan named all three subnets, and the `SA-0091` plan said it would
   name the block "by heading rather than position" and flagged the positional
   wording as a risk to guard against.

   Neither is in the two classes the backtest discredited. That discount should
   stay scoped to check-4 ceilings and "witness already green at base".

3. **`size` double-counts a stacked branch.** `driver.py size SA-0089` →
   `776 changed lines exceeds the feature ceiling of 600; ask the operator`. Its
   real base is `saffron/SA-0088`, against which it is 477 — which is what the
   in-cell gate recorded. 477 + 299 = 776 exactly.

4. **`pattern` shows a phase starting and not its outcome.** `SALVAGE` is absent
   from `WATCH_PREFIXES`, so the line reporting that salvage recovered one commit
   for $0.15 never reached the Monitor. The `IMPLEMENT:` line announcing the
   attempt did.

5. **The lenses have high precision and low recall; the seats are the recall.**
   Across five cells the three in-cell lenses filed one blocker and five
   concerns. The two seats filed twelve blockers, and **eight of those mutants
   passed the entire default suite**. On `SA-0088` three clean lenses preceded a
   real blocker. On `SA-0092` all three lenses independently hit the same line,
   which was a genuine defect but not the one that mattered most. The one lens
   blocker — `SA-0091`'s heading/diff swap — was real, and the Spec seat's
   independent re-run confirmed the implementer's fix closed it.

6. **Three of item 118's four slices shipped the same omission.** A witness that
   records the fact its criterion turns on and never asserts it. This is the
   defect `SA-0087` was amended for, and both later specs carry a paragraph
   warning about it by name. It happened anyway, three times, and each time the
   mutant passed every test. That is the strongest argument this run produced for
   the two seats, and for item 140–150's cluster.

7. **A check-4 ceiling blocker was raised on measured evidence and the outcome
   still contradicted it.** `SA-0091`'s `max_turns: 80` was called a blocker
   because `SA-0088` — editing five of its six files — had just exhausted exactly
   80 turns and needed a salvage. Raised to 90 and $16 on that evidence; the cell
   peaked at **60** turns and $8.39. Neither raise bound. Recorded because the
   reasoning was sound before the fact and the raise was free, which is the shape
   item 123 should expect: check 4 is weak in both directions.

8. **Rewrapping a prompt template broke a witness that pinned it as a contiguous
   string.** The assertion was right to pin the heading names literally, so it was
   made whitespace-insensitive rather than weakened — `hooks/retired_vocabulary.py`
   joins for the same reason. A prose-wrapped template and a substring-matching
   witness are in tension, and the next spec editing one of these files will meet
   it.

9. **`record`, `status`, `next` and the dependency resolver all read correctly.**
   `next` held `SA-0091` back until its parent's review commits were pushed and
   named it; `task.py`'s `_stacked_on` cut each child from its parent's *branch
   head*, review commits included, which its own docstring promises and the logs
   confirmed (`stacked on saffron/SA-0088 @ 78dae0cd`). `--force` kept every
   recorded outcome except the one described in observation 1.
