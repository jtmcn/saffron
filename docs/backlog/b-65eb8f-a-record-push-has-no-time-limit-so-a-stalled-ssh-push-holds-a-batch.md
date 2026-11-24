---
id: b-65eb8f
title: A record push has no time limit, so a stalled ssh push holds a batch for hours
status: open
tier: 2
filed: 2026-11-22
specs: [SA-0432]
prs: []
commits: []
cites: [§4.1]
related: [170]
---

## Problem

Found in the spec loop's run 82, batch 102.

After PACKAGE pushed `saffron/SA-0419`, teardown pushed the task's record
ref to GitHub over ssh. The push stalled for 2 hours 11 minutes and never
failed. The batch waited on it with no output. Killing the push by hand
let the batch go on, and it printed "record push refused". A second push
then stalled for 30 minutes and was killed the same way. A fresh
`ssh -T git@github.com` answered at once both times.

`saffron/record/refs.py` passes no time limit to its `git push`.

## Done looks like

Each record push runs under a time limit, and ssh gets keepalive options,
so a stalled connection fails. A failed push is the same refusal it is
today, and the next push or `saffron reconcile` sends the ref again. A
test stubs a push that never returns and asserts that the caller gets the
refusal within the limit.

## Record

- 2026-11-22: filed from the spec loop's run 82.
