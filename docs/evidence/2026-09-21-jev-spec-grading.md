# Jev against spec outcomes and review rounds (2026-09-21)

A spike. The question: do grades from TypeSafe's Jev model, read from a spec's
text alone, predict whether a cell lands that spec?

**Answer:** two of six grades carry a signal, and both measure the size of the
change. None of the four spec-quality grades separates landed from missed. The
size signal mostly repeats the count of files the spec's `touches` list names.
A second backtest asks whether Jev can tell a review loop to stop. Pooled over
git history it cannot, but the history mixes review processes that changed
under it, so that result is not final. See [Review rounds](#review-rounds).

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

## Against the frontmatter

A spec already declares its own size. `scripts/2026-09-21-jev-vs-frontmatter.py`
compares `change_size` with those fields. AUC here is the chance a missed spec
scores higher than a landed one.

| Signal | AUC | 95% interval | rho with `change_size` |
|---|---|---|---|
| `change_size` | 0.752 | 0.599 to 0.877 | +1.00 |
| `max_turns` | 0.705 | 0.556 to 0.843 | +0.63 |
| `touches` count | 0.672 | 0.512 to 0.824 | +0.85 |
| `budget_usd` | 0.652 | 0.502 to 0.792 | +0.49 |
| `risk` is `elevated` | 0.531 | 0.391 to 0.673 | +0.09 |
| acceptance criteria count | 0.435 | 0.248 to 0.613 | -0.09 |

A paired bootstrap scores both signals on the same 2,000 resamples.

| `change_size` minus | Difference | 95% interval | Resamples at or below 0 |
|---|---|---|---|
| `touches` count | +0.080 | -0.013 to +0.174 | 5% |
| `max_turns` | +0.047 | -0.074 to +0.162 | 22% |
| `budget_usd` | +0.100 | -0.044 to +0.229 | 8% |

1. `change_size` correlates +0.85 with the `touches` count. The grade mostly
   reads the file list. `agent_lands_it` correlates -0.77 with `change_size`,
   so it is the same signal and not a second one.
2. The lead over the `touches` count is +0.080, and its interval includes 0.
   Sixteen misses cannot settle it.
3. A leave-one-out logistic model of `touches`, criteria count, `budget_usd`
   and `risk` scores 0.584. Adding `change_size` gives 0.631, below
   `change_size` alone at 0.712. Sixteen misses are too few to fit five
   features.
4. The criteria count is unreliable. Twenty-three older specs use another key
   and count as zero.

## Limits

- Sixteen misses make every interval wide.
- Jev reads only the text it is sent. It cannot check scope or witnesses against
  the repo, which is what `spec-reviewer` checks 2 and 3 do. The four quality
  grades fail for that reason.
- `SA-0019`, `SA-0043` and `SA-0110` each have a missed version and a later
  landed version. Each version counts once.
- A miss can come from a prompt or gate change rather than the spec itself.

## What it would be good for

Little beyond what the frontmatter gives for free. A count of `touches` carries
most of the signal with no network call. Jev's lead over it is unproven, and
only grades recorded for new specs before their cells run could test it. The
spec-grading question stops here.

## Review rounds

A second question comes from a proposal to log Jev beside every review round.
After a round, can Jev tell whether another round will find a defect? That
answer would be the loop's stop signal.

`scripts/2026-09-21-jev-review-rounds.py` reads every `review(SA-NNNN)` commit
on main as one round that found something. A loop is one spec's rounds of one
kind. Spec rounds edit `.saffron/specs/`, and code rounds edit anything else.
Round N is labelled `more` when round N+1 exists in its loop. The state holds
the spec at that commit, the subjects of earlier rounds, and the round's own
message and diff. Two Nouls ask whether another round would find a defect, and
whether the round's diff settles what it names.

That gives 80 loops and 131 rounds. 51 rounds have a successor and 80 end their
loop. The run cost $0.043 for 1,022,901 input tokens.
`scripts/2026-09-21-jev-review-rounds-eras.py` computes the intervals below.
AUC is the chance a round with a successor outscores a final round.

| Rounds | `another_round_blocks` | `fix_settles` | baseline: round number |
|---|---|---|---|
| All 131 | 0.442 (0.341 to 0.543) | 0.559 (0.459 to 0.664) | 0.587 (0.497 to 0.677) |
| Spec loops, 29 | 0.524 (0.234 to 0.792) | 0.411 (0.133 to 0.674) | 0.452 (0.192 to 0.717) |
| Code loops, 102 | 0.516 (0.389 to 0.646) | 0.513 (0.381 to 0.638) | 0.511 (0.422 to 0.616) |
| Aug 26 to Sep 3, 43 | 0.501 (0.324 to 0.694) | 0.656 (0.486 to 0.811) | 0.255 (0.116 to 0.416) |
| Sep 3 to Sep 17, 43 | 0.678 (0.442 to 0.895) | 0.315 (0.086 to 0.613) | 0.419 (0.355 to 0.474) |
| Sep 18 to Sep 21, 45 | 0.289 (0.143 to 0.459) | 0.616 (0.441 to 0.778) | 0.722 (0.573 to 0.862) |

1. Pooled, neither Noul separates the two classes. Every pooled interval
   includes 0.5.
2. Jev rarely commits. Half of its `another_round_blocks` answers fall between
   0.46 and 0.61, around a median of 0.54.
3. The pooled null is not a clean negative. Split by date, the relationship
   changes sign. In the oldest third a late round is the one that ends a loop.
   In the newest third a late round is the one that continues. Jev's
   `another_round_blocks` moves from 0.678 in the middle third to 0.289 in the
   newest. Its newest-third interval excludes 0.5 on the wrong side.
4. The operator reports that the review process changed continuously across
   these dates. The label then means something different in each era, so
   pooling averages opposite effects.

Limits of this backtest:

- A loop ends at a round cap or on the operator's call as well as when
  nothing is left. Such a round is labelled final either way.
- 72 of the 80 final rounds come from code loops with a single round.
- `review(specs)` commits span many specs, so they are left out.
- Each Noul has one phrasing. The state is truncated at 45,000 characters of
  spec and 30,000 of diff.

This does not show the stop signal is worthless. It shows that git history
cannot answer the question, because the process that made the history kept
changing. A fixed process can. Log `another_round_blocks` for each round under
the current review process, run one extra round after each loop stops, and
compare the prediction with what that round finds. The label then comes from
the next round and needs no hand labelling.
