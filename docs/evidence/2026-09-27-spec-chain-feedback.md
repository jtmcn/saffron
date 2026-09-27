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
