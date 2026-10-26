# Spec chain feedback, 2026-10-24

Six backlog items came out of ADR 11 and the controlled vocabulary review
(#963). Three could not be specs. b-8220e6 and b-541e9a edit
`.saffron/gates/prose.py`, `CONTEXT.md`, `DESIGN.md` and `.saffron/policy.yaml`,
which are all protected. b-8e14fb is a protection decision for the operator.
The other three went through the chain at base `b2acd68f`, the head of #963.

- **b-545741.** `SA-0317`: the cross-check reads a first sentence through
  `definition_sentence` and keeps no rule of its own.
- **b-c16c6c.** `SA-0318`: a test holds every `factory:` class to one
  `CONTEXT.md` entry, and class comments stop restating entries. Five new
  entries land by hand in its pull request.
- **b-7aefb8.** `SA-0319`: a principle's claim moves to
  `factory:principleClaim`, and no property carries two domains.

They ship as one stack, `SA-0317`, `SA-0318` and `SA-0319`, bottom to top, on
#963. Three writers drafted in parallel, one scratchpad worktree each.

| Spec | Round 1 | Round 2 | Size |
|---|---|---|---|
| `SA-0317` | 0B 1C 4N | none | 176 tokens, measured |
| `SA-0318` | 0B 6C 5N | 0B 1C 6N | 320 tokens, measured |
| `SA-0319` | 0B 2C 3N | 0B 0C 3N | 356 tokens, measured |

Drafts took 19 to 26 minutes. Revisions took 9 to 12, and each review took
2 to 7. No first review raised a blocker, which no run before this one
managed. No first review came back empty either. `SA-0317` stopped after
one round, because an independent probe answered its one concern. The other
two stopped at two rounds, each round-2 concern settled by a probe run.

## Each finding by class

- **An arrangement argued rather than run.** 3 concerns. Only the writer had
  run `SA-0317`'s five wrong versions. `SA-0318`'s mid-line case killed two
  wrong versions on paper, and its first count predated the case. Each was
  settled by rerunning the probes from the session, which takes minutes. A
  writer's own probe counts as unmeasured until someone else runs it.
- **A witness drives one member of its set.** 2 findings. `SA-0319`'s
  domain check read only typed subjects. `SA-0318`'s bullet case had no
  colon, so the unanchored pattern survived.
- **An edit in `touches` that no witness holds.** A new class, 1 concern.
  `SA-0319` moved a negative fixture that no assertion read, so a cell that
  skipped it stayed green. The second review was told to read for this
  class, and found one more unheld instruction, recorded as a note.
- **A precondition no cell can make true.** A new class, 2 concerns, both on
  `SA-0318`. A stacked task is cut from its parent's head, so entries landed
  by hand in a child's pull request can miss the parent's tree. The hand
  entries also had four format constraints the spec had not stated.
- **A claim about the tree that stopped being true.** 3 findings: a
  `SpecType` reason that missed b-60d804, a count of two that was four, and a
  stale docstring count.
- **A deleted comment's content with no new home.** 1 concern. `SA-0318`
  deleted the Plan class comment as definitional, and no entry yet held it.

## What the run itself got wrong

- **The base carried a failing test.** #963 cited a twelfth ADR, and only
  eleven exist. Its last push ran only the records and ontology suites. Every
  writer's `make check` found it, and #963 fixed it at `b192ce53`.
- **Parallel writers shared a scratch folder.** One writer rsynced over a
  `proto` folder another was using. The brief now needs a per-spec folder
  name, given up front.
- **Stacked specs collide in the queue smoke test.** All three edited the
  same docstring line and list in `tests/test_scheduler.py`. Each rebase
  needed a hand merge.

## Checks to add

- Pre-flight 1 gains a line: list each file in `touches`, and name the
  witness that fails when the cell skips that file's edit.
- Pre-flight 4 gains a line: for a stacked spec, name every fact its tree
  needs that its parent's head must already hold.
- Pre-flight 10 gains a line: rerun the writer's probes from the session
  before the first review, rather than quoting the writer's count.
