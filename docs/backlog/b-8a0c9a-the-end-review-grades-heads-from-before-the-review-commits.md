---
id: b-8a0c9a
title: "A stack batch's end review grades the packaged heads, before the loop's review commits"
status: done
tier: 2
filed: 2026-10-09
closed: 2026-10-23
specs: [SA-0301, SA-0302, SA-0303, SA-0304, SA-0305, SA-0306]
prs: [789, 932, 937, 939, 941, 944, 934]
commits: []
cites: []
related: [b-792ab2, b-d96f14, b-f71105]
---

## Problem

Found in the spec loop's run 32, reading
`~/.saffron/batches/v0/finish/20/findings.json`.

The end review reads each layer's `pushed_sha` as the batch recorded it
(`saffron/end_review.py:84-131`). The delegate's review commits land after
PACKAGE, so the end review graded heads from before them. Of the twelve
findings it kept, most were already fixed on the branches by then. Examples
are the print-order blocker on `SA-0232`, the `_qualify_range` docstring on
`SA-0238` and the `_SNAPSHOT_SENTENCE` restatement on `SA-0229`.

Its two follow-ups cost $6.06 between them. `SA-0256` (#789) answered a point
the loop's review had made harder to change, and the operator closed it.
`SA-0257` ended `EXHAUSTED`. Two findings stayed real at the top head: the
test name `test_a_seed_whose_fetch_fails_twice_raises_after_two_attempts`
uses "attempts" (`tests/test_worktree.py:672`), and `_draft` hashes the spec
text by hand (`saffron/cli.py:1122` and `:1234`).

## Done looks like

The end review reads each layer's current branch head, or it runs only after
the loop's review commits land. A finding fixed on the branch is not pooled. A
test drives an end review over a layer whose branch moved after PACKAGE.

## Record

- 2026-10-09: filed from the spec loop's run 32.
- 2026-10-10: recurred in the spec loop's run 33. Batch 21's end review graded
  the packaged heads again. Seven of its eight findings were already fixed
  on the branches. The eighth became b-55186d.
- 2026-10-12: recurred in the spec loop's run 35, batch 24. The end
  review graded the packaged heads and raised a `SA-0262` docstring concern
  a held review commit had fixed. Three of its four blockers were new and
  real, on `SA-0262` and `SA-0267`. The delegate fixed them before the push.
- 2026-10-19: recurred in the spec loop's run 44. Batch 38's end review drafted `SA-0296` from the critic's citation note on #911. The delegate held that fix as a local review commit on #911, which the writer could not see. So `SA-0296` (#915) redid it, and the restack conflicted on the same line. Review kept #911's wording.
- 2026-10-20: recurred in the spec loop's run 45. Batch 39's end review drafted `SA-0297` from #919's packaged head. Its three items were two held review commits and one new finding. The draft was refused before any cell.
- 2026-10-23: closed by the spec loop's run 46. #932 (`SA-0301`) adds `--defer-end-review`. #937 (`SA-0302`) grades each layer's branch head. #939 (`SA-0303`) and #941 (`SA-0306`) qualify, write and finish at the graded heads. #934 (`SA-0304`) and #944 (`SA-0305`) run a deferred tail later with `saffron finish`.
