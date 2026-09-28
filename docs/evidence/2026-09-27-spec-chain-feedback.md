# Spec chain feedback, 2026-09-27: splitting SA-0169 and pricing the rest

The spec loop's run 19 started `SA-0169`'s cell. The cell ended
`PLAN_REJECTED` after $1.44. Its plan priced 8400 changed tokens against the
`feature` ceiling of 3000. The whole change later measured 2094 tokens. The
plan had read the spec's "about 2080 tokens" as 2100 lines, and the checkpoint
multiplies lines by four.

The operator had it split, and had the sixteen specs after it priced before
their cells. The pricing agent calibrated against this run's eight landed
cells, which came in at about 1.4 times each spec's own estimate. It found
seven specs over the ceiling and five within 20% of it. Only a spec that
touches `saffron/ledger.py` runs at `elevated`, where `size` can refuse a
plan. The operator chose to fix only those.

## What changed

| Spec | Change | Tier | Measured, times 1.4 |
|---|---|---|---|
| `SA-0181` | new: the account, prefix, capabilities and self-check | elevated | 54% |
| `SA-0169` | rescoped to the `layer_cell` keyword | standard | 44% |
| `SA-0182` | new: `SA-0150`'s ledger part | elevated | 44% |
| `SA-0150` | rescoped to `run_task` | standard | 67% |
| `SA-0156` | drops its one `ledger.py` docstring edit | standard | 67% |
| `SA-0183` | new: `SA-0152`'s three ledger reads | elevated | 19% |
| `SA-0152` | reads through `SA-0183` | standard | about 108% |

## Rounds

| Step | Wall time | Result |
|---|---|---|
| Writer, SA-0169 split | 38 min | two specs, measured |
| Pricing agent, 16 specs | 4 min | 7 over, 5 tight |
| Writer, three more changes | 70 min | two new specs, four latent defects found |
| Review round 1, seven in parallel | 2.5 to 7 min each | no blocker, 14 concerns |
| Writer, round 1 answered | 10 min | 8 wrong versions let through before, killed now |
| Review round 2, seven in parallel | 1 to 3.5 min each | no blocker, 1 concern |
| Writer, round 2 answered | 17 min | 26 more wrong versions measured |

## Findings by class

| Class | Round | Check that should have caught it |
|---|---|---|
| A witness pins one element of a tuple | 1 | pre-flight 1 |
| A wrong version measured on the host, not in the cell image | 1 | pre-flight 10 |
| A test double the next spec cannot reach | 1 | pre-flight 4 |
| Text the split left stale | 1, 2 | pre-flight 5 |
| An arrangement marked reasoned, never run | 1, 2 | pre-flight 10 |

## What the prototypes found before any review

Building each part found four latent defects in the old `SA-0150`: a
module-scope import that `revert` reads as a skip, an existing `SA-0168` test
the change breaks, a retirement marker literal a live test refuses, and a
keyword-only field. It also found that `SA-0152` asked for a ledger method
that already exists.

## Not settled

- `SA-0152` still prices above the ceiling at standard. The operator accepted
  that.
- `SA-0175`, `SA-0160`, `SA-0176`, `SA-0151`, `SA-0161`, `SA-0162`, `SA-0164`,
  `SA-0173` and `SA-0174` still credit `SA-0169` or `SA-0150` with work
  `SA-0181` or `SA-0182` now does. Each spec's tree base holds the names.

# Second chain, same day: three specs off `main` for run 19's top items

The operator asked for specs for b-bf0c91, b-efdf1f and b-877e93 ahead of the
sixteen queued specs. Each declares no `depends_on`, so all three sit on one
branch and one pull request. Three pull requests would each have stepped the
queue smoke test's pinned candidate list, and the second and third would have
conflicted there.

## Rounds

| Step | Wall time | Result |
|---|---|---|
| Writers, three in parallel | 15 to 19 min | three specs, none split |
| Review round 1, three in parallel | 3 to 5 min | no blocker, 12 concerns |
| Writers, round 1 answered | 8 to 10 min | wrong versions measured on each prototype |
| Review round 2, three in parallel | 3 to 4 min | no blocker, 9 concerns |
| Writers, round 2 answered | 8 to 13 min | SA-0186 redesigned by an operator call |

## Findings by class

| Class | Spec | Round | Check that should have caught it |
|---|---|---|---|
| A claim over every turn, a witness over four kinds | SA-0184 | 1 | pre-flight 1 |
| A witness derived from the constant its mutant changes | SA-0184 | 1 | pre-flight 1 |
| A design argument citing a rule §4.3 does not state | SA-0184 | 1 | pre-flight 8 |
| A value placed past a 500-character event bound | SA-0184 | 1 | pre-flight 3 |
| A cell that its own defect would cut | SA-0184 | 1 | pre-flight 11 |
| A keyword witness passing an inverted sentence | SA-0185 | 1, 2 | pre-flight 1 |
| An appended section gluing a later heading | SA-0185 | 1 | pre-flight 4 |
| Witness rules refusing correct wordings | SA-0185 | 2 | none |
| A parent outcome no criterion names | SA-0186 | 1 | pre-flight 1 |
| A stored state re-asked on every run | SA-0186 | 2 | pre-flight 4 |
| A design choice labelled the operator's that was not | SA-0186 | 1, 2 | none |

## What this chain adds to the skill

- **A prose witness needs a correct-wording check as well as a wrong-wording
  one.** SA-0185's round-1 fix tightened its witness until the round-2 review
  found three correct bullets it refused. A cell writes the bullet and the
  witness together, so an over-strict rule costs turns. The writer now runs
  both lists. Pre-flight 1 gains that line next.
- **Mark who decided.** In round 1 the delegate told the reviewers a design
  arm was the operator's call. It was the delegate's. The round-2 reviewer
  argued against §4.2.1, and the operator reversed it. A decision block names
  whose decision each line is.
- **Parallel writers in one tree work if each owns one file.** The smoke test
  and the `DESIGN.md` amendment were the delegate's. Two writers still reached
  for `git stash` in scratch worktrees and applied the shared stack's top
  entry. No entry was lost, but the dispatch now forbids `git stash`,
  `git init` and `git worktree` by name.

## Not settled

- `SA-0186`'s round-2 revision changed its design at the operator's call. No
  third review read it. The writer's wrong-version table is the only check.
- `SA-0186` declares 214 raw lines. At the 1.4 overrun that is about 92% of
  the `bug` ceiling. `size` is advisory at `standard`, so it runs.
- `SA-0185` and `SA-0186` both touch `saffron/task.py`. The operator orders
  them.
