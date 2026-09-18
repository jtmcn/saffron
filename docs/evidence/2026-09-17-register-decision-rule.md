# The rule a register comparison is judged against

2026-09-17. Written before any two-arm comparison has been run.

## The metric

`RunScore.per_1k` from `harness/register_scoring.py`: house-style hits per
thousand words of claim text, over one pass. Hits per claim would move with a
prompt that files longer claims, and a raw total moves with one that files
fewer findings.

## The noise floor

Three runs of `2026-09-11-lens-corpus-spread` used one unchanged prompt tree.
Their `per_1k` figures spanned 38.4 to 41.7, a range of 3.3
(`docs/evidence/2026-09-17-register-noise-floor.md`).

## The rule

A prompt change counts as **measured** when the treatment arm's `per_1k` differs
from the control arm's by more than 6.6 per 1k, twice the observed range, in
the direction stated in the pull request before the arms were run.

A delta between 3.3 and 6.6 per 1k is **suggestive**, and buys another pass
rather than a conclusion.

A delta below 3.3 per 1k is **unmeasured**. That is not a failure and it is
not "no effect": it is a change this instrument cannot see. `error` is not
`fail` and `RATE_LIMITED` is not `EXHAUSTED`.

Both arms use one model, one corpus and one driver, and differ only in
`prompt_sha`.

## What this rule is not

Eight fixtures is a small corpus. §8 already says the statistics are noise at
this volume and to reread monthly rather than weekly. This is a guard against a
large regression, not an instrument for a small win, and a delta near the floor
should be reported as unmeasured rather than argued up.
