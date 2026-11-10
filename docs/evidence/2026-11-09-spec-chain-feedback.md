# Spec chain feedback, 2026-11-09

## SA-0360 (b-31e3c8), during the goal after spec loop run 57

The first chain under #1104's flow. The writer prototyped in its own worktree and staged nothing. The delegate committed the spec and its bookkeeping, and the tree was clean after each commit. The writer drafted in 21 minutes and revised in 4. Two reviews took 8 and 6 minutes. The prototype ran 28 wrong versions on the draft and 30 after the first revision, and every one was killed.

The delegate settled six design arms in `decisions:`, and no review re-argued one. Concerns only, anchored only, concerns ride a REBUT that blockers start, numbered after the blockers, no verdict on a concern, and a concern's answer never changes the state.

**Review 1: 0 blockers, 3 concerns, 3 notes.**

- With concern entries filtered out, a turn that answered only concerns and moved nothing ended with "made no argument: recorded nothing". That line is false. Pre-flight 2 missed it, since it reads criteria against each other and not against a rendered line.
- `max_turns` rested on SA-0351's 241-turn peak, a floor. Pre-flight 7 passed it, and #1105's new floor rule now blocks that shape.
- The delegate's DESIGN.md §5.6 hand edit said a concern's answer is always shown in the pull request. A REBUT pool cut drops the result, so it is not. Pre-flight 12 missed it.

**Review 2: 0 blockers, 3 concerns, 3 notes.**

- The first fix covered half the false line. A claimed blocker fix beside an argued concern still said "made no argument". This is the same class as review 1's first finding, and naming the class to the reviewer found it.
- DESIGN.md §5.6's rule that a rebuttal with no argument earns nothing now read as if a concern's argument earns judging. It was a sentence the hand edit left standing. Pre-flight 12 missed it again.
- `as_dict`'s new argument needed a default, because a `forbidden` test file calls it four times. Pre-flight 4 missed it: the data flow check reads callers inside `touches`.

The delegate applied review 2's findings by hand, with no third round.

## Checks to build (SA-0360)

10. Pre-flight 2 should read every rendered line a changed count feeds. A filter on what a count reads makes each line built on that count a claim, and two review rounds found the same false line.
11. Pre-flight 4 should list every caller of a changed signature in a `forbidden` file. A required parameter there breaks a file the cell cannot edit.
12. Check 9 recurs. Both of this chain's hand-edit findings came from sentences the delegate wrote or left standing. A hand edit should be read against every sentence of its section, not only the one it changes.
