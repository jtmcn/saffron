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
