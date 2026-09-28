---
id: b-64e40c
title: The spec review's re-ask witness reads its prompt by prefix and suffix, the hole #565 closed for the writer
status: open
tier: 3
filed: 2026-09-28
closed:
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [b-792ab2, b-2750d5]
---

## Problem

Found in the spec loop's run 20, 2026-09-28, by #565's Spec seat (`SA-0160`).

`test_a_spec_review_re_asks_once_when_its_extraction_is_not_the_schema`
(`tests/test_spec_review.py:970` on `main`) checks a refused value's re-ask
prompt by prefix and suffix alone (`:987` and the line after it). The re-ask
it guards is `saffron/spec_review.py:411`. At `82f0b1db` the same lines are
`:1036`, `:1053-1054` and `:429`.

On #565 two mutants of the writer's twin survived that check. One dropped the
validation error. One always sent the `None` message. Review fixed the writer's
witness. The seat did not probe the review's witness, so its hole is unmeasured.

## Done looks like

The witness asserts each refused row's whole re-ask prompt, as #565's writer
witness does. Both mutants, applied to `spec_review.py`'s re-ask line, are
killed.

## Record

- 2026-09-28: filed from the spec loop's run 20.
