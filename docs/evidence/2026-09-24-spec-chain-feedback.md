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

## The second session, 2026-09-24 to 2026-09-25

The limit reset early, and the chain finished. It wrote `SA-0150` to
`SA-0152`, `SA-0160` to `SA-0162`, `SA-0164`, `SA-0165`, `SA-0167` to
`SA-0170`, `SA-0173` and `SA-0174`. It revised `SA-0155` to `SA-0157`. The
three build steps left split into sixteen specs.

### How it ran

- **Contracts first, writers in parallel.** The delegate split the remaining
  work into five specs and wrote their interfaces into one shared brief
  before any writer started. Five writers then drafted at once. Later
  decisions went into a second shared file every writer read.
- **Reviews were batched per wave.** Up to eight reviews ran at once. Each
  review brief listed the decided changes not yet applied, so no reviewer
  reported them.
- **Final rounds applied without a third review.** That kept the two-round
  stop rule. Specs split from a reviewed parent took one round.

### What the reviews found

| Class | Specs where a blocker came from it |
|---|---|
| A wrong build passes the arrangement | nearly every spec, again |
| One spec id per task hides a key collision | `SA-0150`, `SA-0161` |
| Spend that lands outside tonight's batch | `SA-0162`, `SA-0164`, `SA-0168`, `SA-0151` |
| A cross-spec contract mismatch | `SA-0160`, `SA-0165`, `SA-0151`, `SA-0162` |
| A fail-open default | `SA-0170` (links unless escalated), `SA-0169` (no self-check) |
| A design claim with no measurement | `SA-0169` (the shell prefix) |

The held-run class was one root cause, found as five separate blockers
across four specs. A resumed task kept an earlier night's run. The
operator's decision to mint a fresh task each night removed all five at
once. A reviewer reads one spec, so it cannot see that five findings share
a cause. The delegate can, and should look for it whenever one wave's
blockers cite the same sibling rule.

### Operator decisions taken

1. Prompt paths come from `policy.yaml`, not a hard-coded agent file.
2. The spec review and writer sessions hold `Bash` in their critic cell.
3. That `Bash` runs as an unprivileged account. Only a spec session's cell
   gets `CAP_SETUID` and `CAP_SETGID` for it.
4. A stack batch mints a fresh task for each spec every night.

The first framing of decision 2 was wrong. It called the critic cell the
isolation boundary, and DESIGN §5.5 says why it is not one for code the
verdict's runner sits beside. A reviewer caught it, and decision 3 is the
correction.

### Items for Saffron to absorb, ranked

1. **Name the shared cause.** When several blockers in one wave cite the
   same sibling rule, the delegate settles that rule once. The skill should
   say so, beside the stop rule.
2. **A fail-open check in the pre-flight.** For each gate a spec adds, ask
   what happens when its signal is absent: a missing line, a raise, `None`.
   Two blockers this session were a check that passed on silence.
3. **A contracts file for split specs.** Writing interfaces before writers
   start let five drafts run in parallel with few mismatches. The skill's
   dispatch reference should carry it as a template.
4. **Run a security control's claims in a real cell before review.**
   `SA-0169`'s review found nine concerns, most of them claims about the
   CLI no one ran.
