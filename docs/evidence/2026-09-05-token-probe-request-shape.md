# What `/v1/models` answers a subscription OAuth token

**Status: UNMEASURED.** This file is the skeleton for a measurement that has
not been made. It exists because `saffron/preflight.py`'s token probe is
currently a *reasoned* guard on the most consequential path in the system, and
CLAUDE.md's rule is that a measured fact beats a reasoned one and the comment
says which.

## The question

`validate_claude_token` sends:

```
GET https://api.anthropic.com/v1/models
Authorization: Bearer <CLAUDE_CODE_OAUTH_TOKEN>
```

Nothing in this repo has ever observed what that endpoint answers a
*subscription OAuth* token presented that way. `grep -rn "anthropic-version"`
over the whole repo returns nothing. A subscription token is not an API key,
and the documented API surface generally wants `anthropic-version`, with OAuth
credentials additionally wanting an `anthropic-beta` opt-in.

The header set was inferred from the fact that `session.py` forwards
`CLAUDE_CODE_OAUTH_TOKEN` into the cell — but it forwards the *environment
variable*; nothing in Saffron constructs this header. That is an inference
about the Agent SDK's internals, not an observation.

## Why it matters

`check_readiness` runs before anything else in a night (§4.4 step 1). If a
**valid** token answers 401 here, every repo is skipped, the batch produces a
night of nothing, and the operator is pointed at `claude setup-token` for a
credential that was fine — which is the same shape as the Appendix J failure
this probe was written to catch, inverted.

The tri-state verdict (`VALID` / `INVALID` / `UNKNOWN`) limits the blast radius
in the other direction only: a moved endpoint or an unreachable host no longer
reads as a dead credential. It does **not** protect against a live token being
rejected for a missing header — that answers 401, which is `INVALID` by design.

## How to measure it

Run with a live token, then with a revoked one. The token belongs in the
environment of the command itself and nowhere else (CLAUDE.md):

```fish
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
  uv run python docs/evidence/scripts/2026-09-05-token-probe-shape.py
```

The script tries each header combination and prints the status for each, so one
run answers both "does the bare Bearer form work" and "which header is missing".

## Results

| Headers sent | Live token | Revoked token |
|---|---|---|
| `Authorization` only | _unmeasured_ | _unmeasured_ |
| `+ anthropic-version: 2023-06-01` | _unmeasured_ | _unmeasured_ |
| `+ anthropic-beta: oauth-2025-04-20` | _unmeasured_ | _unmeasured_ |
| all three | _unmeasured_ | _unmeasured_ |

## What to do with the answer

- If the bare form returns 200 on a live token and 401 on a revoked one, the
  probe is correct as written — replace the `UNMEASURED` comment in
  `preflight.py` with a pointer to this file and the date.
- If it returns 401 on a **live** token, add whatever headers the table shows
  are required, and add a regression test pinning them.
- Either way, delete this "Status: UNMEASURED" banner.
