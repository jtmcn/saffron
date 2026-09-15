---
id: 68
title: Readiness and the scan each fetch the same mirror, once per night
status: done
tier: 3
closed: 2026-09-05
specs: [SA-0055]
prs: [131]
commits: [819cbff]
cites: [§4.2.1, §4.4]
related: [58]
---

## Problem

**The first spec Saffron ran unattended.** `saffron batch` picked it up,
drove the cell, packaged it and opened the pull request: 25 minutes, $6.68
against a $15 budget, `READY_FOR_REVIEW`, `batch: DRAINED`, exit 0. It also
found a third duplicated `real_remote` call this item did not know about.

Two things the review round found afterwards are worth carrying, because both
are about a claim outrunning its evidence rather than about this fix. The
`PinnedBase` docstring said it avoided adjacent same-typed parameters and did
not — measured, `PinnedBase(mirror, base_sha, url)` type-checked cleanly and
put the URL in `base_sha`, now fixed with `kw_only`. And the narrowing at the
call site called "a passing `Readiness` carries all three" a contract, which
`Readiness` does not enforce and nothing asserted; it does now.

**Tier 3.** Found reviewing `SA-0054` (PR #123).

`check_readiness` and `_resolve_queue` both call `ensure_mirror`, `real_remote`
and `fetch_default_branch`, and `saffron batch` calls both — readiness first
(§4.4 step 1), then the scan. §4.2.1's whole argument for hoisting preflight
was that a batch does these once per run rather than once per task; it now does
them twice per run.

`Readiness` already returns `mirror`, `url` and `base_sha` precisely so a caller
need not re-derive them, and `_resolve_queue` recomputes all three anyway.

Harmless at K=1 against one repo — two mirror fetches, seconds apart, the second
a no-op fetch — which is why this is Tier 3 rather than urgent. It stops being
harmless at multi-repo, where it doubles the network cost of starting a night.

## Done looks like

`_resolve_queue` accepting the mirror, url and base_sha a
readiness check already established, rather than deriving its own. Note the
ordering constraint that makes this awkward and worth doing carefully:
readiness must run *first* (a scan that raises before the batch row exists is
what item 58's review fixed), so the seam is readiness handing its results
down, never the scan handing them up.

## Record

**Status: done** — `SA-0055`, PR #131, merge `819cbff`. `_resolve_queue` takes
an optional `PinnedBase`; `_batch` hands down the mirror, url and base_sha that
`check_readiness` already established, and `saffron queue` — which runs no
readiness check on purpose — still derives its own.
