---
id: b-1c59c3
title: A spec that removes a name can leave a reader of it outside its touches, so its cell ends EXHAUSTED
status: open
tier: 1
filed: 2026-10-12
specs: [SA-0269]
prs: [853]
commits: []
cites: [§4.3, §5.4]
related: [b-e773d9]
---

## Problem

Found in the spec loop's run 35, and answered by hand in run 36.

`SA-0269` removed `CRITIC_NETWORK` from `saffron/cell/session.py`.
`tests/test_sigterm.py` imports it and asserts the old network name. That
file was not in the spec's `touches`. The spec review passed it.

The cell could not finish. Attempt 2 fixed the test, and `scope` refused
the edit. Attempt 3 reverted it, and `tests` failed. The task ended
`EXHAUSTED` at $41.03 of $36. PR #853 added the file to `touches` and raised
the ceilings, and the rerun reached `READY_FOR_REVIEW` at $35.95.

`b-e773d9` covers two specs that clash on a name. This is one spec against
the tree. A spec that says a name "goes" can be checked with one `git grep`
before any cell runs.

## Done looks like

A spec names each identifier it removes. Before its cell, the queue or the
spec review greps the base for every reader of each one. A reader outside
`touches` refuses the spec, and the refusal names the file and the name. No
model call decides it.

## Record

- 2026-10-12: filed from the spec loop's run 36. #853 fixed `SA-0269` by hand.
