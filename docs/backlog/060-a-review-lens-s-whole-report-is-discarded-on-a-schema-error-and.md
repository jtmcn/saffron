---
id: 60
title: A review lens's whole report is discarded on a schema error, and nothing re-prompts
status: done
tier: 2
closed: 2026-09-10
specs: []
prs: []
commits: [4139fbb]
cites: []
related: []
---

## Problem

The correctness lens returned a well-argued finding about `saffron/watch.py`
and omitted one field:

```
correctness produced nothing — not the schema: 1 validation error for _Report
findings.0.severity
  Field required [type=missing]
```

`review.py:168` turns that exception straight into `LensReview(..., error=...)`.
The finding is gone — recoverable only by grepping `events.jsonl` by hand,
which is how the text above was retrieved.

**The stop is correct and is not the defect.** `review.py:274` makes an errored
lens a stop at `REVIEWING`: *"A lens that errored **is** a stop"*. So a
vanished lens can never read as a clean review, which is the Appendix I
discipline working exactly as designed. Nothing here argues for softening it.

**The gap is the missing re-prompt.** The plan artifact re-prompts once on a
schema failure — `session.py:451`, *"not the schema, re-prompting once"* — and
a lens does not, though both are a fresh session returning JSON against a
declared shape and both cost roughly the same to ask again. One malformed
enum field ended the attempt at $3.61 with a correct finding thrown away.

**Done looks like** `review.py` re-prompting a lens once on `NotSchema`, the
way `artifacts.py` already does for the plan, with the second failure still
producing the stop it produces today. The re-prompt must carry the validation
error itself: the lens omitted a required field, and being told which one is
most of the fix.

**Not** relaxing the schema to make `severity` optional. The severity is what
`_describe` counts and what decides whether a finding blocks; a report whose
findings have no severity is not a report that can be acted on.

## Record

**Tier 2.** Measured 2026-09-04 on `SA-0053`, and the finding it cost was a
real one.

**Status: done in code, found open here on 2026-09-10.** `4139fbb` (*fix(review):
a lens whose output is not the schema gets one re-prompt*) re-prompts once on a
schema failure. A second failure still stops at `REVIEWING`. The item was never
closed.
