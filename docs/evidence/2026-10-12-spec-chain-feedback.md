# Spec chain feedback, 2026-10-12

Eleven backlog items went through the chain at base `bc879e2c`, in priority
order. They are b-a8270f, b-4a63b7, 40, 97, 120, 46, 170, b-e471bd, b-5b1f8a,
b-2e0b97 and b-0569f7. Three split, so the run wrote fourteen specs: `SA-0272`
to `SA-0285`. Twelve land as one stack. `SA-0279` is parked until its three
siblings retire, as its second review found.

Five items in the same priority band became no spec. Items 79 and 119 owe a
measured pass. Item 80 needs §5.4.1 written by hand first. Items b-da550a and
b-a9ec4b are infrastructure and `.claude/` work.

## How the run went

Two read-only triage agents read all sixteen items first. None was ready for a
writer, because each one held an open design choice. The operator took every
recommended arm in one answer. Then eleven writers drafted in parallel, one
worktree each.

| Spec | Item | Round 1 | Round 2 | Measured tokens |
|---|---|---|---|---|
| `SA-0272` | b-a8270f | 0B 8C 5N | 0B 5C 7N | 1991 |
| `SA-0285` | b-a8270f | split out | 0B (with 0272) | 624 |
| `SA-0273` | b-4a63b7 | 1B 6C 7N | 1B 2C 6N | 1913 |
| `SA-0274` | 40 | 0B 2C 4N | 0B 1C 3N | 616 |
| `SA-0275` | 97 | 0B 3C 3N | 0B 2C 3N | 1131 |
| `SA-0284` | 97 | 0B 4C 6N | none | 1910 |
| `SA-0276` | 120 | 0B 2C 3N | 0B 3C 3N | 523 |
| `SA-0277` | 46 | 1B 6C 7N | 0B 2C 6N | 1725 |
| `SA-0278` | 170 | 1B 10C 3N | 1B 5C 4N | 2131 |
| `SA-0279` | b-e471bd | 1B 3C 2N | 1B 1C 2N | 470 |
| `SA-0280` | b-5b1f8a | 3B 7C 7N | 1B 6C 7N | 1743 |
| `SA-0281` | b-2e0b97 | 0B 4C 2N | none | 1348 |
| `SA-0282` | b-0569f7 | 0B 4C 6N | 0B 1C 6N | 582 |
| `SA-0283` | b-0569f7 | 0B 1C 4N | none | 444 |

No first review found nothing. Six specs drew a blocker in some round. A second
review found a blocker four times, so a second round still earns its cost.
Drafts took 25 to 45 minutes and reviews took 4 to 12.

## Each finding by class

- **A claim over a set whose witness drives one member.** The largest class
  again, in nine of fourteen specs. The new shapes were sharper than before.
  - A member hidden by an upstream transform: the cell clips a key block before
    the host sees it (`SA-0277`), and round 2 found the clip marker itself.
  - A value type's coercions: `1.0` passes a check that reads `1` (`SA-0283`).
  - The motivating shape, not a synthetic one: SA-0192's parenthesized constant
    (`SA-0280`).
  - A promise in Out of scope, or "leave X unchanged", is a claim too
    (`SA-0274`, `SA-0280`).
- **A hand edit to a protected file that overclaims.** Seen on six specs, five
  of them more than once. It says a branch is always pushed, says behaviour
  exists before the cell lands it, or leaves a sentence the change makes false.
  Pre-flight 12 names the class and still did not prevent it.
- **The delegate's own decision was wrong.** Twice. An empty `thread_env` that
  "counts as declared" made `SA-0282`'s warning unreachable for every templated
  repo. An infrastructure `unproven` that ends `GATE_ERROR` collapsed `fail`
  into `error` beside another red gate (`SA-0273`). Neither decision was read
  against the files or the invariant that would exercise it.
- **The design does not serve its own item.** `SA-0272`'s history cell could
  not run `chains`, the item's own example, because mirrors are host paths.
  The writer then ran it in a real cell over the real ledger. With the mirrors
  mounted and their paths rewritten it compared 137 merged tasks. Without that
  it compared none.
- **Run order across siblings.** `SA-0279`'s refusal would refuse its own
  queued siblings. A spec measured without its dependencies' tests named a
  closed list of tests to repair (`SA-0278`).
- **A fake's default hides a wrong build.** It recurred in `SA-0280` and
  `SA-0284` although the brief named it.
- **A new call site inherits a callee's exceptions.** The probe cell's patch
  faults escaped `SA-0273`'s REBUT to `ORPHANED`.

## What the delegate did by hand

- Fixed prose and vocabulary hits in four committed drafts. A writer's
  `make check` skips an untracked spec, so a retired word reached the commit.
- Reversed the `thread_env` decision and narrowed `SA-0273`'s `GATE_ERROR`.
- Parked `SA-0279` out of the stack.
- Restacked twelve branches linearly and put each one's parent first in
  `depends_on`. It merged the fact kinds of `SA-0275` and `SA-0281` and kept
  both dated bullets in ADR 3.
- Found a defect on main outside this run. `SA-0268` writes `runtime.GATEWAY`
  into `task.py`, and `SA-0271` deletes it while it forbids `task.py`. The
  two sit in separate chains, so whichever lands second breaks.

## The next checks

1. **Run the item's own example through the prototype.** Pre-flight 10 should
   require it as an arrangement before the first review.
2. **Read each brief decision against its inputs.** Name the real files and
   invariants that will exercise a decision before a writer gets it.
3. **Grep protected text for the negation of the change.** Every sentence that
   says the old behaviour, not only the ones the brief names.
4. **Prefer a rule to a list when the cell's base adds files.** A list measured
   at an older base misses what the dependencies add.
5. **Run `prek run --files` on a new spec before commit.** The writer agent's
   step 7 should say so.

## Second run: the tier-1 items with no spec

Six tier-1 items had no spec, queued or retired. They are 79, b-032c3e,
b-cab612, b-02d328, b-1c20da and b-e773d9. Five became specs, `SA-0286` to
`SA-0290`, at base `cf3db797`. b-cab612 lives wholly under `.claude/`, so it
lands by hand. The core arm of b-e773d9 became `SA-0290`, and its driver arm
lands by hand too.

The operator settled three design choices in one answer before any writer
ran. b-032c3e ends in a new state, `REVIEW_INCOMPLETE`. b-02d328 makes
`witness` block at every tier. The `.claude/` work lands by hand.

| Spec | Item | Round 1 | Round 2 | Measured tokens |
|---|---|---|---|---|
| `SA-0286` | 79 | 0B 3C 5N | 0B 2C 2N | 781 |
| `SA-0287` | b-032c3e | 0B 3C 5N | 0B 1C 3N | 341 |
| `SA-0288` | b-02d328 | 0B 3C 5N | 0B 2C 4N | 837 |
| `SA-0289` | b-1c20da | 0B 4C 5N | 1B 5C 2N | 986 |
| `SA-0290` | b-e773d9 | 3B 3C 2N | 0B 4C 2N | 1354 |

`SA-0288` also drew an ADR review of its ADR 3 edit, with 0B 4C 2N. Drafts
took 21 to 32 minutes and reviews took 4 to 8. No spec went to a third
review. Four second rounds held only mechanical fixes. The delegate applied
those through the writer and checked each one by hand.

## Each finding by class, second run

- **A mutant outside the diff drops its witness from `revert`.** A new class,
  and the most important. `SA-0286` round 2 found it, and the delegate then
  caught it in `SA-0287` before review. `issue-tracker.md:128` tells a writer
  to list a mutant's file under `forbidden`. `revert.py:195-216` then exempts
  that witness, because its mutant file is outside the diff's source. At
  `standard`, an advisory `witness` gate was the only check left on it.
  `SA-0191`, `SA-0195` and `SA-0247` carry the same shape and merged.
- **What a component receives at run time.** Dictated prompt text described a
  ticked box the lens never sees (`SA-0286`). A witness leaned on a token from
  the host environment, and a build command was relative to the wrong
  directory (`SA-0289`). Pre-flight 4 reads where values flow, but not what a
  prompt or a printed line claims about its reader.
- **A writer probed its own wrong versions and missed a reviewer's.** Each
  writer ran `driver.py probe` over its list. Reviewers then named versions
  that survived: a walk over the first parent only, two word boundaries, and a
  working directory equal to the root.
- **A hand edit states unbuilt behaviour as built.** The fourth run in a row.
  `SA-0288`'s ADR 3, CONTEXT.md and ontology comments each said `witness`
  already blocks at every tier. Another edit contradicted a queued parent's
  notes (`SA-0280`). Pre-flight 12 names the class and did not prevent it.
- **`depends_on[0]` is not the last parent to land.** Stacking reads slot zero
  alone (`task.py:211`). `SA-0289` listed seven parents with the earliest first,
  so it could never stack. Five of them shared only test files, which the open
  pull request overlap refusal already orders.
- **A refusal reason feeds a reader outside `touches`.** The spec loop's
  driver defers any refusal whose reason holds the literal `depends_on`
  (`driver.py:302`). `SA-0290`'s first reason would have put every held spec
  back in the order.
- **A writer called an edit new code.** `SA-0290` rewrote the `consumes`
  validator and declared no mutant. Its first mutant also hung on one exact
  spelling, which a backticked field name defeats.
- **A partner set missed a state the batch reaches.** `SA-0290` drew clash
  partners from candidates only. A batch rescans after each task and drops a
  spec at `READY_FOR_REVIEW`, so the filed pair still clashed the same night.

## What the delegate did by hand, second run

- Measured `apple/container`'s answer to `image inspect` through
  `runtime.call` for `SA-0289`. A miss exits 1 with the text on stderr alone.
- Landed the independent review beside the `SA-0062` fixture.
- Set the rule for this run's `depends_on`: source overlaps and semantic
  parents only, with the last to land first.
- Restacked five branches cut from one base and merged the queue smoke test's
  pinned lists at each layer.
- Saw three collisions in the shared scratchpad. One writer applied another's
  prototype diff to its tree and reverted it before commit.
- Saw `test_a_live_saffron_cell_is_found_by_its_spec_id` fail once while two
  writers ran `make check` at the same moment. It passed alone.

## The next checks, ranked by what Saffron absorbs

1. **`revert` judges a new witness whose subject is in the diff.** A gate
   change. Where the mutant points says nothing about what the witness reads.
   Until then, `driver.py check` names each criterion whose mutant file is
   outside `touches`.
2. **The queue warns when `depends_on[0]` lands before another parent.** A
   queue change. The ancestry is already in hand when `build_queue` runs.
3. **The driver keys on a refusal's kind, not its text.** A driver change,
   by hand, under `.claude/`.
4. **A command greps protected text and queued specs for the old claim.**
   Pre-flight 12 as a command, run on every hand edit.
5. **Each parallel writer gets its own scratch directory.** A dispatch change.
   A name prefix held for the rest of this run.
6. **The live-cell test claims its probe name per process.** A test change,
   so two suites can run at once.
