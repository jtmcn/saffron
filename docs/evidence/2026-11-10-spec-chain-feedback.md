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

## SA-0364 (b-3cf039) and SA-0365 (b-2bc0d5), written in parallel

The two writers drafted in 28 and 27 minutes, with no question back. Each revised once. Each spec took two reviews, and the delegate applied the second review's findings by hand.

### SA-0364

**Review 1: 1 blocker, 2 concerns, 2 notes.**

- The live cell appends every blocker's `rebuttal` fact before any concern's, while REVIEW positions findings in lens order. `migrate` derived in position order, so a concern ahead of a blocker was still refused. Pre-flight 4 missed it. The brief named the writer and the derivation but not the order each one writes in.
- An edit declared no mutant. The writer wrote two, but `refs/saffron/mutants` does not exist at origin, so none was placed. Creating it is the operator's call.
- Ending the set-aside could refuse a ref base `migrate` topped up. Measured absent on 405 refs.

**Review 2: 0 blockers, 2 concerns, 3 notes.** Both concerns were witness gaps in the new order: no task held two blockers, and no task held an unanchored host-filed blocker. Pre-flight 1 missed both, since the revision added a set (the order within a group) without naming its members.

### SA-0365

**Review 1: 1 blocker, 6 concerns, 4 notes.**

- Every origin name ended outside {., g, i, t}, so `rstrip(".git")` passed. Pre-flight 1 missed it: the set was the origin forms, and the members that tell a suffix strip from a character strip were never named.
- An unmeasured podman spelling in the `Dialect`, against its own docstring. Pre-flight 8 missed it.
- A timeout that carries stderr fell under two rules. Pre-flight 2 missed it.
- Two hazards were named in Out of scope: a tag shared across worktrees, and a delete under a build in flight.

**Review 2: 0 blockers, 4 concerns, 4 notes.** Two were more members of the origin set: `.git` inside a name, and an empty segment in a directory that matches it. Two were docstrings the new member makes false.

The delegate measured the one fact the writer could not, since it was told to stay read-only. `container builder delete --force` exits 0, and the next build starts a fresh builder in 42 s.

## Checks to build (SA-0364, SA-0365)

20. Pre-flight 4 should name the order each writer of a compared sequence writes in, as well as the writer.
21. For a string transform, pre-flight 1 should list the inputs that tell the intended transform from its near neighbours (suffix and character strip, end and anywhere).
22. The writer's brief should say whether a live measurement that changes host state is allowed. A read-only brief left a fact open that the delegate settled in a minute.
