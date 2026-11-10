# Spec chain feedback, 2026-11-10

## SA-0362 (b-66e82d), after spec loop run 58

The writer drafted in 25 minutes with no question back. Its prototype killed all 23 wrong versions with assertion failures. One review took 4 minutes and ended the chain.

**Review 1: 0 blockers, 1 concern, 5 notes.**

- The new `failures` text reaches `events.jsonl` unredacted, since `EventLog.append` redacts only `Agent` events (§4.7). The delegate recorded the choice as out of scope, beside the unredacted `detail` fields. Pre-flight 8 missed it: §4.7's redaction sentence covers every field that carries cell text.
- Two notes were wrong citations: a test quoted as declaring `dead` declares `lint`, and a `def` cited two lines low. Pre-flight 5 missed both, since `cite` resolves a line and does not read what the spec says is on it.
- One note named the second REBUT re-run, which only criterion 4 drives. Both re-runs share `_judge`, so no wrong version tells them apart.
- One note was the multi-task `watch` line, which matches how `Baseline` already prints.
- The mutant ref was absent locally. The spec declares new behaviour with no mutants.

The delegate applied the concern's answer and both citations by hand, with no second round.

## Checks to build (SA-0362)

16. Pre-flight 8 should ask, for every new field that carries cell text, what §4.7 says about redacting it.
17. `cite` should compare a quoted token beside a citation with the cited line's text, not only resolve the line.

## SA-0363 (b-c5da95), after spec loop run 59

The writer drafted in 18 minutes with no question back. Its prototype failed all 7 new witnesses at base and killed 16 wrong versions. The revision took 5 minutes and killed 8 more. Two reviews took 5 and 2.5 minutes.

**Review 1: 0 blockers, 2 concerns, 5 notes.**

- The shared helper refused inline mutants, so regate, package and review would decline every task from before `SA-0338`. §5.4.1 gives a cell's read from `HEAD` as the only reason, and none of the three starts one. Pre-flight 8 missed it. The delegate's own brief chose one helper for four callers and never asked whether each caller needs every step.
- Attaching mutants also arms the `witness` gate inside `reverify`, which the Context never named. The delegate accepted it, since PACKAGE already works that way. Pre-flight 4 missed it: the data flow stops at `revert`, the reader the item names, and never asks who else reads `Criterion.mutant`.
- The notes were a missing "on one line", a module docstring, a turn margin of 0.8, the review lenses never reading a mutant, and the absent ref.

The writer revised once.

**Review 2: 0 blockers, 1 concern, 3 notes.**

- The revision's inline cases made criteria 2, 5 and 7 answer one input two ways: an inline spec that pins a missing commit. Pre-flight 2 missed it, since it was not re-run after the revision added cases to the sibling criteria.
- One note was a witness gap: the review inline case had to differ from the pinned commit's mutant. The other two were the reordered refusal reason and the absent ref.

The delegate applied the concern and two notes by hand, with no third round.

## Checks to build (SA-0363)

18. Pre-flight 4 should list every reader of a field the change starts to fill, not only the reader the item names.
19. After a revision adds a case to one criterion, re-run pre-flight 2 against each criterion that shares its input.
