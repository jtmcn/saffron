---
id: 93
title: Requiring a probe may have cost the adequacy lens recall, and nothing measured it
status: open
tier: 1
specs: [SA-0063]
prs: []
commits: []
cites: []
related: [7, 88]
---

## Problem

**Tier 1 — it bears on whether the corpus's own number means anything.** The
adequacy prompt gained a required `probe` field
(`saffron/agents/prompts/review-adequacy.md`) between pass 1 and the baseline
pass. Adequacy owns **10 of the corpus's 12** declared defects, and it went
**3/10 to 2/10** across that change — both defects in the difference are
adequacy-owned (`SA-0063`'s pair). n=1 each side, so the drop is neither noise
nor a measured regression: it is *confounded*, and
`docs/evidence/2026-09-09-lens-corpus-baseline.md` claims neither reading.

What makes it answerable: pass 1's runs are on disk, but re-scoring them cannot
help — the prompt changes the *runs*, not the predicate that reads them. It needs
a pass under each prompt at the same `--runs`, or a higher `--runs` under the
current one to establish the spread first. The second is cheaper and comes first:
at `--runs 1` over eight fixtures nobody knows this metric's resolution, and two
passes disagreeing by 1 of 12 is all the evidence there is.

Until then, no prompt change should be read off a single corpus pass — the same
instruction item 88 left on the one-fixture harness, now owed by its replacement.

**Status, 2026-09-11: the cheap half is done, the confound half is not.**
`docs/evidence/2026-09-11-lens-corpus-spread.md` is a `--runs 3` pass under the
*current* (post-probe) prompt, unchanged from the baseline's. Four samples of
that one configuration are now on record — the baseline's `3/12` plus this
pass's per-run `1/12`, `2/12`, `3/12` — a range of `1/12` to `3/12`. That
establishes the metric's resolution at n=1; it says nothing about the
pre-probe prompt, so the confound this item opened (whether requiring a probe
cost adequacy recall) is still open and still needs a pass under pass 1's
prompt at the same `--runs` to answer. The lens prompt now also carries
`CLAUDE.md` (item 7), so these four samples describe a configuration that is
no longer current; `docs/evidence/2026-09-11-lens-corpus-claude-md.md` is the
first pass under the new one, and a future confound pass must compare against
that record, not this one.
