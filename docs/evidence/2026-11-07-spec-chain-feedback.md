# Spec chain feedback, 2026-11-07

Four tier 1 items became six specs in one stack: item 80 as `SA-0338` and
`SA-0339`, item 42 as `SA-0340` and `SA-0341`, item 49 as `SA-0342`, and
b-d39d9a as `SA-0343`. Read-only triage agents read each item first. Each item
needed an operator ruling, and one question settled all four on the
recommended arms. The delegate wrote each spec's `DESIGN.md` and `CONTEXT.md`
edits by hand before its writer ran. Six writers then drafted in parallel, one
worktree each, and the stack was rebuilt after every round.

## Rounds

| Spec | First review | Second review | After the second |
|---|---|---|---|
| `SA-0338` | 0 blockers, 7 concerns | 0 blockers, 3 concerns | fixed by hand |
| `SA-0339` | 0 blockers, 5 concerns | 0 blockers, 3 concerns | fixed by hand |
| `SA-0340` | 2 blockers, 3 concerns | 0 blockers, 3 concerns | fixed by hand |
| `SA-0341` | 0 blockers, 2 concerns | 0 blockers, 2 concerns | fixed by hand |
| `SA-0342` | 0 blockers, 9 concerns | 1 blocker, 3 concerns | a third writer pass |
| `SA-0343` | 0 blockers, 3 concerns | 0 blockers, 2 concerns | fixed by hand |

No spec had a third review. Drafts took 30 to 45 minutes each, reviews 4 to 11
minutes, and revisions 2 to 36 minutes.

## Findings by class

**A witness drives one member of a set (pre-flight 1).** Seven findings, three
of them blockers.

- `SA-0340`'s first review found no readable turn with an empty answer list,
  and no empty error string. Both were blockers.
- `SA-0342`'s second review found no diff with neither subset. It was a
  blocker the revision introduced, since the revision moved a skip.
- `SA-0343` left a failed lens's cost and then its own `budget_usd` unpinned.
  `SA-0340`'s count could not tell blockers from every finding. `SA-0339`'s
  forced fetch had no diverged case.

The brief named this class for every writer, and the reviews still found it.

**The delegate's own hand edits overclaimed (pre-flight 8).** Six findings.
`SA-0338`'s §5.4.1 kept three sentences saying the spec declares the mutant.
`SA-0342`'s "hunk" sentence read as context-inclusive, and its "one extra test
run" turned false, which a second edit then got wrong again. `SA-0343`'s
"every lens can start" was false of its own rule. `SA-0340` left §6 and §5.7
naming no unread blocker. Each hand edit was written before any prototype
existed, so none was read against the build.

**A parallel parent's names (pre-flight 3).** Two findings. `SA-0339` assumed a
text parser `SA-0338` never built. `SA-0341`'s test-edit rule ignored the
tests `SA-0340` adds. Briefing each writer with its siblings' end states
caught the rest, but not names a sibling had yet to choose.

**A data flow the change breaks (pre-flight 4).** Three findings. `SA-0340`'s
payload keys made `migrate` refuse every live ref, since it compares whole
payloads. `SA-0338`'s refusal of inline mutants reached the follow-up writer,
a follow-up's origin scan and a corpus guard. Two of the three were outside the
first draft's `touches`.

**Ceilings over a floor (pre-flight 7).** Every first review raised one. The
`history` line names a peak as "a floor" and still clears it. Four budgets
cleared the worst review plus rebut row by $0.33 to $1.36.

**Stale commit ids (pre-flight 5).** Four specs cited commits a restack had
replaced. `cite` resolves lines, not commit ids, so it passed them.

**Writers ignored a brief rule.** Two of six filed a `by_hand` glossary item
though the brief said not to. The delegate deleted each and edited
`CONTEXT.md` by hand.

## Checks to build

1. `driver.py check` should block when a turns ceiling sits over a floor
   peak, or when the budget clears the worst review plus rebut row by under
   $2. It prints both facts today and passes.
2. `driver.py cite` should resolve each commit id a spec names as an ancestor
   of the branch it is read at.
3. A hand edit to a protected file goes in after the writer's prototype and
   is read against it. Six of this run's findings came from edits written
   first.
4. A child spec drafted in parallel gets its parent's chosen names before its
   draft ends, not after the first review.

## SA-0353 (b-ffb930), spec loop run 55

Three writer sessions: the draft took 47 minutes and 298k tokens. Two reviews. The writer ran 33, 41 and then 44 wrong versions on a prototype, and every one was killed.

**Review 1: 1 blocker, 4 concerns, 4 notes.** The blocker was the delegate's own brief. It told the writer to have core name the repo's `prose` gate, and core names no repo gate (§2.1, `rebut.py:208-209`). No pre-flight check reads a brief against §2.1. The concerns were a session cost the admission checks undercount (pre-flight 7), a failed send-back discarding a parsed draft (pre-flight 2), a refusal SA-0338 adds that the check never ran (pre-flight 4), and a set member no witness drove (pre-flight 1).

**Review 2: 2 blockers, 4 concerns, 5 notes.** The send-back turn did work and emitted the block in one turn, against principle 18 (pre-flight 8, the design read). Nothing witnessed the cost of a failed send-back (pre-flight 1). The concerns were which text survives a send-back (pre-flight 2), a regression on a draft that never parsed, an untested bound of 2, and an inline prompt outside `prompt_sha`. The delegate settled every one in a final revision, with no third review: a send-back is a work turn and then the existing extraction turn.

## Checks to build (SA-0353)

5. Read the delegate's `decisions:` block against §2.1 and the principles before dispatch. The first review's blocker came from a decision, not the writer.
6. Pre-flight 8 should name principle 18 for any new turn that both does work and emits a schema.
