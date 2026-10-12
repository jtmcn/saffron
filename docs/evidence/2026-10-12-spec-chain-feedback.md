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
