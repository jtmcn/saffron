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
