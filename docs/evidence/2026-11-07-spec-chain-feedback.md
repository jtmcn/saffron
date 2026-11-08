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

## `SA-0352`, from b-a714d2 (spec loop run 55)

One writer, two reviews and one revision, beside a running batch. The draft
took 33 minutes and about 180k tokens. The revision built a prototype and ran
each wrong version it doubted.

The design is one exclusive `flock` on a file beside the home ledger. A batch,
a cell and a draft each hold it. A second command on the same home exits 2
and names the holder's pid.

**Review 1: one blocker, four concerns.**

- The witness shape the notes cited starts its child with the default
  `close_fds`. That closes an inheritable descriptor too, so the wrong
  version "the lock is inheritable" passed. The prototype measured it. This
  is pre-flight 10, an arrangement argued rather than run.
- A file object closed only on a normal return still passed the raise case,
  since refcounting closes it as the raise unwinds. The prototype measured
  this too. Pre-flight 10 again.
- The cited lock precedent opens with mode `w`, so a contender would erase
  the holder's pid before its refusal. This is pre-flight 3, a name the spec
  leans on that means something else at base.

**Review 2: no blocker, two concerns.** A holder flag the stub never cleared
let a reverted contender recurse until `main` returned 2. The delegate added
the sentence by hand. The first criterion's six wrong versions were reasoned
and not run.

**What this run adds.** Both blockers in this run were arrangements, and each
cost one prototype run to settle. A writer brief should ask for a prototype
run of every wrong version that turns on process or descriptor behaviour.


## `SA-0350`, from b-e7898b (spec loop run 55)

One writer, two reviews and two revisions, beside a running batch. The draft
took 23 minutes and about 198k tokens. Each review took 5 to 6 minutes.

The design is a declared field. A spec that adds a refusal names the specs it
would refuse in `retired_first`, and intake refuses it until each is in
`done/`. The brief ruled out running the new rule on the host.

**Review 1: no blocker, three concerns.**

- A corpus test asserts every refusal reason holds `depends_on`. The first
  retired spec that declares the field would fail it. This is pre-flight 6,
  a change that breaks a live test. The writer had not read that assert.
- An unreadable `done/` file gave a reason the filesystem contradicts. This is
  pre-flight 4. The base already carries a suffix for this case.
- The stack-mode witness never made its parent a stack base, so a wrong
  version that credits the base passed. This is pre-flight 1, a set member
  the witness never drove.

**Review 2: no blocker, three concerns.**

- `saffron cell` exited 1 on a failed base export, though `cli.py`'s contract
  gives a setup failure 2. Pre-flight 8 missed it. The first revision added
  the branch, so this class came from a fix.
- The cell path passed the unreadable count with no witness. This is
  pre-flight 1 again, on the branch the first revision added.
- Whether the parent becomes the stack base was unmeasured. The writer ran
  `build_queue` and confirmed it, which is pre-flight 10.

**What this run adds.** Both review 2 concerns sat on code the first revision
wrote. A revision brief should ask the writer to run pre-flight 1 and 8 on
each branch it adds, not only on the findings it answers.
