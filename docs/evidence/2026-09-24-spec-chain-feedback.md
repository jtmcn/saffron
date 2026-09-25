# Spec chain feedback, 2026-09-24: the stack batch's build specs

Backlog item b-792ab2, ADR 7's build order. The chain ran from 2026-09-23 into
2026-09-24 and stopped when the account hit its weekly limit. Nineteen specs
went through the writer and reviewer agents: `SA-0142` to `SA-0149`,
`SA-0152` to `SA-0157` and `SA-0159`. Six build steps split, into fourteen
specs from the nine the design named.

## Where it stopped

- Committed, two review rounds done: `SA-0142` to `SA-0149`, `SA-0153` to
  `SA-0156`, `SA-0159`.
- `SA-0157`: round 2 found no blocker. Its final fixes were sent and not
  applied, because the limit hit first.
- `SA-0156`: committed. Its first review did not run.
- `SA-0152`: final and uncommitted in the worktree. It waits on `SA-0151`,
  because a queued spec may not name an undeclared parent.
- `SA-0150` and `SA-0151`: not written.

## Findings by class

Every review round but three found a blocker. Each blocker but one was the
same class: a plausible wrong implementation, unnamed in the notes, that
passed a witness arrangement.

| Class | Rounds that found it | Check that should have caught it |
|---|---|---|
| A wrong build passes the arrangement | nearly every round | none, then a simulation |
| A test double's default hides a missing pass-through | `SA-0144`, `SA-0154` | none |
| A shared fixture default collides on a key | `SA-0148`, `SA-0149` | none |
| Per-ledger state passes on a fresh ledger | `SA-0145` | none |
| An arithmetic coincidence in the arrangement | `SA-0157` | none |
| A cross-spec contract mismatch | `SA-0147`, `SA-0155`, `SA-0157` | none |
| A size estimate by line rate | `SA-0152`, `SA-0154` | pre-flight 7, measured wrongly |

## What changed the rate

From `SA-0145` on, each writer ran a throwaway simulation of the right build
and each named wrong build against the arrangement. The first one caught a
wrong build no review named. Blockers after that were narrower, and the last
rounds of `SA-0146`, `SA-0152`, `SA-0153`, `SA-0154` and `SA-0159` found
none.

Size estimates by line rate ran high. A prototype counted by the `size`
gate itself settled `SA-0152` at 74% where the rate said 85%.

## Items for Saffron to absorb, ranked

1. **A simulation step in the pre-flight.** Check 1 reads each claim against
   its witness. It should also run the right build and each named wrong
   build against the arrangement, where the arrangement exists at base. This
   is the one change that moved the blocker count.
2. **Size by prototype.** Pre-flight 7 should count a prototype with
   `saffron/gates/core/size.py`, not multiply lines by a rate.
3. **A forward `depends_on` blocks a commit.** Parallel writers draft a chain
   out of order, and `tests/test_queued_specs.py` refuses a spec whose parent
   is undeclared. Drafts waited uncommitted. A spec review can read an
   uncommitted file, which kept the chain moving.
4. **Parallel writers collide on shared files.** The queue smoke test and the
   backlog records took every writer's lines. Writers reported their lines,
   and the delegate applied them in one commit. Writers also need scratch
   directories of their own; one overwrote another's.
5. **The prose hook misfires in a worktree.** The `PostToolUse` hook runs
   from the main checkout, so every file edited in a worktree counts against
   zero and prints every existing hit.
6. **Intake reads a literal `/work` in a claim as a path.** A claim had to
   name `worktree.WORKTREE_MOUNT` instead.

## Hand work the chain needed

Four by-hand ontology changes landed ahead of their writers, because no cell
may edit `CONTEXT.md` or `ontology/**`: `stack_layer` (`75edb212`),
`end_review` (`8a41411c`), `qualification` (`f3f10f7b`), and `SPEC_WITHHELD`
with `spec_review` (`ccfa1553`). Each is a step a later spec could take if
the vocabulary allowed a pending kind.
