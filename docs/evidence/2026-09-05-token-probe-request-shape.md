# What `/v1/models` answers a subscription OAuth token

**Measured 2026-09-05**, live `CLAUDE_CODE_OAUTH_TOKEN` from `claude
setup-token`, against `https://api.anthropic.com/v1/models`.

## Results

| Headers sent | Live token |
|---|---|
| `Authorization` only | **400** `anthropic-version: header is required` |
| `+ anthropic-version: 2023-06-01` | **200** |
| `+ anthropic-beta: oauth-2025-04-20` (no version) | **400** same message |
| all three | **200** |

Two facts, and the first is the one that matters:

**`anthropic-version` is required, and it is validated before the
credential.** A request without it gets `400` regardless of what the token is
— the endpoint never looks. `anthropic-beta` is not required at all; a
subscription OAuth token authenticates on `anthropic-version` alone.

## What this found

The probe as originally written sent `Authorization: Bearer` and nothing else,
and read its result as `return exc.code not in (401, 403)`. Against the real
endpoint that is `400 -> not in (401, 403) -> True -> valid`.

**It would have called every token valid.** Not just an expired one — any
string at all, since the version header is checked first and the credential is
never reached. The function written to catch Appendix J's silent-dead-token
failure reproduced it exactly: `check_readiness` would have passed, the night
would have started, and every cell would have burned its attempts against a
credential nobody had verified.

It was also untested in that branch — `exc.code not in (401, 403)` could be
mutated to `not in (999,)` with 89 tests still passing — so nothing would have
said so.

## What changed as a result

- The probe sends `anthropic-version: 2023-06-01`
  (`preflight._TOKEN_PROBE_HEADERS`), and a test asserts the header *arrives*
  at a live loopback server rather than merely being constructed.
- `400` is pinned as `UNKNOWN`, beside `404` and `500`. Reading it as VALID is
  the specific mistake above.
- The verdict is tri-state, so anything the probe cannot turn into an answer
  refuses the night while naming the network or the endpoint, never the
  credential.

## Still unmeasured, and why it is safe

**A revoked token was not measured** — only a live one, with and without the
header. The expected `401` is inference.

It is a safe gap in one direction only, and that is a property of the
tri-state rather than luck: any status other than `401`/`403` is `UNKNOWN`,
which still refuses to run. So if a revoked token answers something
unexpected, the failure is a night that declines to start and says why —
never a night that starts on a dead credential. The reverse gap, a valid token
being refused, is what the `200` above closes.

Worth measuring the next time a token is rotated: revoke, run
`docs/evidence/scripts/2026-09-05-token-probe-shape.py`, and record the status
here.
