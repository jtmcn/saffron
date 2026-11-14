# Spec chain feedback, 2026-11-13

Continues `docs/evidence/2026-11-12-spec-chain-feedback.md`. Check numbers
carry on from its 42. Three writers drafted in parallel during spec loop
run 67, each in its own worktree cut from `cb4ad504`.

## SA-0384 (b-b664d1)

`cite` refuses a citation that no single construct it names holds. The
writer measured the rule over 55 past specs: it flags 108 of 2165
citations, in 43 specs. The delegate accepted that burden.

**Review 1: 0 blockers, 0 concerns, 4 notes.** The chain ended. One note
was applied by hand: the title said "parent" for a predecessor, which
`CONTEXT.md` avoids.

## SA-0385 (b-45783e)

A rate-limit reset past six hours waits the six-hour cap.

**Review 1: 1 blocker, 2 concerns, 3 notes.** The writer revised.

- Criterion 3 claimed `unknown` for a reset at the clock, but no witness
  drove one. Pre-flight 1 missed the boundary member.
- No mutant guarded the kept `until` comparison. `refs/saffron/mutants`
  does not exist on origin, so no spec carries one.

**Review 2: 1 blocker, 0 concerns, 3 notes.** The caught set named
`OSError`, but no driven reset raised it. The delegate measured `10**17`
raising `OSError` on macOS and on Linux glibc, and the writer added it.

## SA-0386 (b-19f43a)

One constant names the reviewed-diff phase line. `session.py` writes it and
`qualify.py` reads it.

**Review 1: 1 blocker, 2 concerns, 2 notes.** The writer revised.

- No log varied the hash, so a prefix match that ignored it passed.
  Pre-flight 1 missed the member that differs only in the hash.

**Review 2: 0 blockers, 2 concerns, 2 notes.** Both notes were applied by
hand. The concerns asked for a mutant the ref cannot yet hold.

## Checks to build

43. For each value in a caught exception set, the witness drives an input
    that raises it.
44. For a matcher over a prefix and a value, the witness varies each part
    alone.
45. A boundary named in a claim, such as "at or before", is driven at the
    boundary itself.

## SA-0387 (b-f30189)

A spec declares `renames`, and `census` accepts exactly the pairs head
carried out.

**Review 1: 0 blockers, 3 concerns, 4 notes.** The writer revised.

- No call held a missing new name with nothing removed. The writer measured
  two builds that pass whenever nothing is removed, and both passed. Pre-flight
  1 missed a member that one call's other contents masked.
- One member left its old name's head state open, so it told no build
  apart. Pre-flight 1 missed the open state.
- Out of scope claimed every recurrence changed its test's assertion. The
  item's own record says `revert` still refused #1099. Pre-flight 5 missed a
  claim about the item, not the tree.

**Review 2: 1 blocker, 2 concerns, 2 notes.** Applied by hand. The witness
compared only `file` and `code`, so a wrong version about the message
passed. The budget cleared review and rebut by $1.51, and rose to $48.

## SA-0388 (b-e11fb7)

One function in `events.py` renders a reset stamp, with the clock's `now` as
a parameter. Both callers use it.

**Review 1: 0 blockers, 2 concerns, 4 notes.** The writer revised.

- A claim named "at most six hours", and no witness drove 21600 seconds.
  Pre-flight 1 missed the boundary member. Check 45 names it.
- A claim named "the same object", and the witness compared by equality.
  Pre-flight 1 missed object identity.
- The body quoted the new code's text, so a later mutant could not pin it
  (§5.4.1). No check reads a body for a future mutant's text.

**Review 2: 1 blocker, 2 concerns, 2 notes.** Applied by hand. A wrong
version said the clock is read twice, but the test clock returns one
object, so no witness could tell. Two claim words, "always with the day"
and "keyword-only", had no driven member.

## Checks to build

46. For each field a failure carries, a wrong version that changes it has a
    witness that reads that field.
47. Each wrong version is checked against the test double the witness uses.
    A fake that returns one object cannot tell a second read apart.
48. A claim about the item's own history is read against the item's
    Record.
