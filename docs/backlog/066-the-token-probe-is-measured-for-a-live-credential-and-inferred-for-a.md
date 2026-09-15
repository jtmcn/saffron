---
id: 66
title: The token probe is measured for a live credential and inferred for a dead one
status: open
tier: 2
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

**Tier 2.** Filed 2026-09-05 alongside the measurement in
`docs/evidence/2026-09-05-token-probe-request-shape.md`.

That measurement established what `/v1/models` answers a *live* subscription
token, and it mattered: without `anthropic-version` the endpoint returns `400`
for any token at all, because it validates the header before the credential —
so the probe's original boolean form (`exc.code not in (401, 403)`) called every
credential valid, including a revoked one. That is fixed.

What is still inferred is the other half. Nothing has observed what a
**revoked** token answers with the header present. `401` is the expectation and
the code treats `401`/`403` as the only INVALID verdicts.

The gap is safe in one direction by construction: any other status is
`UNKNOWN`, which refuses the night while naming the endpoint rather than the
credential. So a wrong guess costs a night that declines to start and says why
— never a night that starts on a dead token. That is why this is Tier 2 rather
than Tier 1.

**Done looks like** the results table in that evidence file having a revoked
column, filled from a real run. The moment to do it is a token rotation, when a
dead token exists anyway: revoke, run
`docs/evidence/scripts/2026-09-05-token-probe-shape.py`, record the status. If
it is not `401`/`403`, add it to the INVALID set and say in the comment that it
was measured.
