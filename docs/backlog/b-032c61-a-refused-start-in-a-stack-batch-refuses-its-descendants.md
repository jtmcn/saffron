---
id: b-032c61
title: "A start preflight refuses in a stack batch is a miss, so the batch refuses its descendants"
status: open
tier: 1
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§4.2.1, §5.1.1]
related: [b-60a399, b-e0cd57]
---

## Problem

Found by the first review of `SA-0244` on 2026-10-07.

Today an N1 refusal raises `CellRuntimeError` out of `cell_up`. `SA-0234`
makes a stack batch offer a spec again on that raise, so its descendants
are not refused. `SA-0244` turns the refusal into a returned
`PREFLIGHT_FAILED` outcome instead.

A stack batch's `wrapped()` offers a spec again only on a returned
`RATE_LIMITED` or `PROVIDER_UNREACHABLE` (`saffron/batch.py:736-742`). Any
other result that is not a layer is a miss, and `resolve_prefix` refuses
every descendant (`saffron/batch.py:507-518`). Once both specs land, a host
refusal in a stack batch refuses the rest of the stack. That is b-60a399's
defect again, for preflight refusals.

## Done looks like

A stack batch treats a returned `PREFLIGHT_FAILED` as it treats a raised
`CellRuntimeError`. It offers the spec again under the breaker and refuses
no descendant.

## Record

- 2026-10-07: filed from `SA-0244`'s first review.
