# Jev grades of spec text against cell outcomes (2026-09-21)

A spike. The question: do grades from TypeSafe's Jev model, read from a spec's
text alone, predict whether a cell lands that spec?

**Answer:** two of six grades carry a signal, and both measure the size of the
change. None of the four spec-quality grades separates landed from missed.

## Method

`scripts/2026-09-21-jev-spec-grading.py` builds one row per spec version. The
ledger's `tasks` table gives each `spec_sha` and its states. The text is the
committed blob whose sha256 equals `spec_sha`.

- **Landed:** any task on that version reached `MERGED`.
- **Missed:** none merged, and one reached `EXHAUSTED`, `PLAN_REJECTED` or
  `NOT_IMPLEMENTED`.
- **Dropped:** only infrastructure or in-flight states, such as `ORPHANED`,
  `GATE_ERROR` or `RATE_LIMITED`.

That gives 104 versions: 88 landed and 16 missed. Each spec went to
`jev-1.13.0` in one request with six questions. Four are Scores and two are
Nouls. The script prints each question's AUC, the chance a landed spec outscores
a missed one. Spec length and spec number are the two baselines.

Cost was $0.0153 for 364,966 input tokens. Median latency was 0.15s.

## Results

AUC is oriented so that 0.5 is no signal and higher predicts landing. The two
grades and the length baseline where a higher value predicts a miss are flipped.
Intervals are 95% bootstrap intervals over 2,000 resamples. The two correlation
columns are Spearman rho against spec length and spec number.

| Grade | AUC | 95% interval | rho length | rho number |
|---|---|---|---|---|
| `change_size`, flipped | 0.752 | 0.604 to 0.881 | +0.28 | -0.29 |
| `agent_lands_it` | 0.715 | 0.571 to 0.846 | -0.34 | +0.29 |
| `one_reading`, flipped | 0.618 | 0.458 to 0.771 | +0.04 | -0.19 |
| `criteria_checkable` | 0.605 | 0.423 to 0.783 | +0.45 | +0.72 |
| `scope_bounded` | 0.603 | 0.422 to 0.774 | -0.17 | +0.24 |
| `wrong_impl_excluded` | 0.569 | 0.399 to 0.720 | +0.40 | +0.46 |
| baseline: spec number | 0.641 | 0.466 to 0.809 | | |
| baseline: length, flipped | 0.627 | 0.485 to 0.768 | | |

1. Only `change_size` and `agent_lands_it` have intervals that exclude 0.5.
   Both beat the baselines and correlate weakly with them.
2. The signal survives on later specs. From `SA-0045`, 68 landed and 7 missed.
   There `agent_lands_it` scores 0.653 and flipped `change_size` scores 0.642.
   From `SA-0080`, 36 landed and 4 missed, and `agent_lands_it` scores 0.722.
3. `criteria_checkable` tracks spec number at rho +0.72. It reads the newer spec
   format, not spec quality.
4. As a flag, `change_size` at 2.5 or more marks 19 specs. Eight of them missed,
   against a base rate of 15%. That is half of all 16 misses.

## Limits

- Sixteen misses make every interval wide.
- Jev reads only the text it is sent. It cannot check scope or witnesses against
  the repo, which is what `spec-reviewer` checks 2 and 3 do. The four quality
  grades fail for that reason.
- `SA-0019`, `SA-0043` and `SA-0110` each have a missed version and a later
  landed version. Each version counts once.
- A miss can come from a prompt or gate change rather than the spec itself.

## What it would be good for

A cheap size warning before `spec-reviewer` or a cell runs. It replaces none of
the six review checks.
