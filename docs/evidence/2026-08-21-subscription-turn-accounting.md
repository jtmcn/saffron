# What a subscription session actually reports

**Run:** `SA-0004-integrity-gate`, one attended cell, 2026-08-21.
**Credential:** `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`, forwarded by `cell_env`.
**Terminal state:** `READY_FOR_REVIEW`, 25147-byte patch exported.
**Preflight:** `rapportd:49152` tolerated via `SAFFRON_ALLOW_HOST_PROCESS` — reachable at both `10.88.0.1` and `10.0.0.108`, so N1 does not hold on this host without the tolerance.

## Per-turn accounting

| Phase | `num_turns` | `total_cost_usd` |
|---|---|---|
| PLAN | 11 | $0.6243 |
| IMPLEMENT | 23 | $1.2418 |
| REVIEW — correctness | 3 | $0.2561 |
| REVIEW — contract | 8 | $0.5267 |
| REBUT — rebuttal | 13 | $0.8658 |
| REBUT — extraction | 1 | $0.0559 |
| REBUT — verdicts | 6 | $0.3076 |
| **total** | **65** | **$3.8783** |

The spec declared `budget_usd: 4.5`. The task finished at $3.88 — the existing dollar budgets are better calibrated than assumed, and the ceiling came within 14% of binding.

## Conclusion 1 — `total_cost_usd` is NOT zero under subscription auth

This is the finding that matters, and it contradicts the assumption the turn re-base was planned on.

The runtime reports a real, plausible, per-turn dollar figure on a subscription session. It is **notional** — an API-rate valuation of tokens nobody is billed for — but it is present, monotonic per turn, and usable. `spent` therefore still accumulates a meaningful quantity, and `_over_budget` still fires against something real.

**What this invalidates:** the premise that the host was summing a number that had stopped meaning anything. It had not. It stopped meaning *money*, which is a narrower claim than the one the plan was built on.

**What survives:** DESIGN.md §5.1's ceiling argument still cannot lean on the dollar figure, because a notional cost is not a provider-side cap. The reasoning needs correcting; the mechanism does not.

## Conclusion 2 — one complete elevated-risk task costs 65 turns

Distribution matters more than the total: IMPLEMENT (23) and REBUT (13) dominate, and the three REBUT sub-turns are separately reported rather than folded into one figure. A turn ceiling set below ~80 would cut a task that the dollar ceiling would have let finish.

## Conclusion 3 — `max_budget_usd` was never observed firing, and cannot be shown inert

No turn terminated on the in-cell budget; every one reported `(completed)`. Because cost is non-zero, **the knob still works** and the plan's Task 7 guard fires: do not delete it.

## Conclusion 4 — `RateLimitEvent` is emitted and discarded

Three or more `agent: passthrough RateLimitEvent` lines appear in the stream. `agent_runner.events()` has no branch for it, so its `status`, `utilization` and `resets_at` never reach the host.

`RateLimitInfo`, verified inside `saffron/cell-base:python`:

```
status: "allowed" | "allowed_warning" | "rejected"
utilization: float 0.0-1.0
resets_at: int | None      # unix timestamp, window reset
rate_limit_type: str | None
```

**The gap this leaves is not observability, it is diagnosis.** Because the events are dropped, this run cannot report what its own rate-limit utilization was — the data existed and was thrown away. Worse, a `rejected` window would fail every turn, the repair loop would spend all four attempts against it, and the task would terminate `EXHAUSTED`: a provider limit reported as task difficulty, which is the one-state-for-two-causes failure §3.3 exists to prevent.

This is the only ceiling in the design the cell is *subject to* rather than merely *reporting*, and it is the property §5.1 has wanted since rev 1.

## Recommendation

1. **Do** surface `RateLimitInfo` and give `rejected` its own terminal state (plan Task 4).
2. **Do** correct §5.1's ceiling reasoning: the dollar figure is notional, not billed.
3. **Do not** re-base the ceilings onto turns. It was proposed on the belief that cost had stopped being reported. It has not. The re-base is churn across nine files that buys a unit change and no new guarantee.
