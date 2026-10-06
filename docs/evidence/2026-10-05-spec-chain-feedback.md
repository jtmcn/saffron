# Spec chain feedback, 2026-10-05

Three backlog items became three specs for the first live stack batch.
`SA-0206` comes from b-209696, `SA-0207` from b-23a149 and `SA-0208` from
b-60ff2e. They landed as #682, #683 and #684 in stack #685.

## Cost

Wall time per agent, from each agent's own report. The three writers ran
in parallel, each fenced off from the files its siblings owned.

| Spec | Draft | Revise | Review |
|---|---|---|---|
| `SA-0206` | 26.6 min | by hand | 7.1 min |
| `SA-0207` | 21.3 min | by hand | 4.5 min |
| `SA-0208` | 18.1 min | 10.3 min | 3.9 min |

The operator stopped the chain at one review a spec, with the delegate
applying findings by hand. The batch reviews each spec again before any
cell runs, so a second hand round duplicates it.

## Rounds

| Spec | Blockers | Concerns | Notes |
|---|---|---|---|
| `SA-0206` | 2 | 3 | 3 |
| `SA-0207` | 0 | 3 | 5 |
| `SA-0208` | 0 | 0 | 4 |

## Each finding by class

- **A claim's witness drives one member of a set.** `SA-0206` criterion 2
  priced every event kind and drove three. The delegate's pre-flight caught
  the same class in `SA-0207` criterion 1 before review. Pre-flight 1 ran on
  `SA-0207` and was skipped on `SA-0206`, so it missed there.
- **A delegate edit that disagreed with its spec.** The `DESIGN.md` risk
  row edit for `SA-0206` promised a floor on a path criterion 5 forbids.
  Pre-flight 2 would catch it if it read the hand edits as criteria.
- **A measurement that could not read what it claimed.** The delegate
  counted `claude-sonnet-5` in `events.jsonl`, but those names come from
  `init`, not from assistant messages. The reviewer caught it. Host
  transcripts then gave 18,652 assistant messages with that exact name.
- **A design argument the documents do not support.** `SA-0208`'s draft
  printed one turn's bound beside a row that sums three turns. The
  delegate's pre-flight 8 caught it before review.
- **A claim about the tree that stopped being true.** `DESIGN.md` §4.3
  named `asyncio.wait_for`, which nothing calls. The `SA-0207` writer found
  it. The plan commit cited an unlisted document, which `test_citations`
  refused. The delegate committed it without running `make check`.

## What the next run changes

- Run pre-flight 1 and 2 on every hand edit to a protected document.
- Name the event a measured string came from before quoting it.
- Run `make check` before a docs commit, even outside the `prose` scope.

## The run record view, `SA-0215` and `SA-0216`

Item b-a1d649 came from ADR 9 and its plan, not from the backlog. One spec
was asked for. A first writer measured a prototype of the whole at 678
lines and split it, as the brief allowed above 600. `SA-0215` states
batches, runs, tasks, phases and attempts. `SA-0216` adds gate results and
findings, and depends on `SA-0215`. Both sit on PR #688.

### Cost

Wall time per agent, from each agent's own usage line.

| Step | `SA-0215` | `SA-0216` |
|---|---|---|
| Split measurement | 7.9 min, shared | |
| Draft | 17.1 min | 15.7 min |
| Review 1 | 5.1 min | 5.3 min |
| Revise 1 | 9.0 min | 7.8 min |
| Review 2 | 4.1 min | 3.8 min |
| Revise 2 | 8.2 min | 9.1 min |

The two writers ran in parallel, one worktree each. Round 2 ended the
chain. Each writer settled its round 2 findings by running every listed
wrong version against its prototype, rather than by a third review.
`SA-0215` killed 58 of 58, and `SA-0216` killed 38 of 38.

### Rounds

| Spec | Round | Blockers | Concerns | Notes |
|---|---|---|---|---|
| `SA-0215` | 1 | 0 | 6 | 4 |
| `SA-0215` | 2 | 0 | 3 | 5 |
| `SA-0216` | 1 | 1 | 3 | 4 |
| `SA-0216` | 2 | 1 | 2 | 2 |

### Each finding by class

- **A fixture that makes a wrong build right by coincidence.** This is the
  run's largest class, at eight findings, and no pre-flight check names
  it. A fresh ledger numbers every table from 1, so `batch-<run_id>` and a
  result named by a running counter both passed. A column default stood in
  for a driven risk. Dyadic money values let `Decimal(float)` pass. A UTC
  process let a local-time read pass. A checkpointed file let an
  `immutable=1` reader pass. Pre-flight 1 asks which member a witness
  drives. It does not ask whether the fixture's values could coincide with
  a wrong build's.
- **A revision that unwitnessed a claim it did not touch.** `SA-0216`'s
  second-round blocker came from its own first revision. Giving each
  left-out task a gated attempt removed the only input that showed a
  duplicate entry. Pre-flight 2's rule to repeat after a cut covers this,
  if a fixture change counts as a cut.
- **Two specs answering one input differently.** `SA-0216` stated gate
  results for a task `SA-0215` leaves out. `SA-0215`'s own two leave-out
  criteria disagreed on a task unknown on both counts. Pre-flight 2 caught
  neither, because it ran on each spec alone.
- **A ceiling anchored on an unlike row.** `SA-0215`'s $58 budget comes
  from `SA-0162`, a 5202-token stack-batch spec that ended `EXHAUSTED`.
  Lowering it to $30 made `driver.py check` report a blocker, because its
  rule anchors on the costliest row. The budget stayed at $58.
- **A claim about a library that reading could not settle.** A read-only
  open of a missing SQLite file raises at `connect`. The operator's session
  settled it by running it. Pre-flight 10 covers this class.
- **A defect in the base the spec consumes.** The first writer's prototype
  found PR #688's V2 and V5 counting a task twice. It was fixed by hand at
  `fa4abd31`. No pre-flight reads the base PR's own artifacts against the
  data the spec will produce.

### What the next run changes

- Add a fixture-coincidence check to pre-flight 1: name each value a
  wrong build could read from a default, a shared id or an exact float.
- Run pre-flight 2 across a parent and child, not only within each spec.
- After a fixture change, re-run every listed wrong version, not only the
  new ones.
- Check new spec text against the `retired-vocabulary` hook before the
  commit. `SA-0216`'s draft named a retired term.
