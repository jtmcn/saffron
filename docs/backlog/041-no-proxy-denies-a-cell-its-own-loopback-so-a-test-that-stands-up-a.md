---
id: 41
title: '`NO_PROXY=""` denies a cell its own loopback, so a test that stands up a local server fails at baseline forever'
status: done
tier: null
closed: 2026-09-01
specs: [SA-0040]
prs: [95]
commits: []
cites: [§5.1]
related: []
by_hand: true
---

## Problem

**Status:** **done**, by hand, on `joel/cell-loopback-not-proxied`. `proxy_env`
returns `NO_PROXY: "127.0.0.1,localhost"`, and a driven test asserts the probe
reaches a server started beside it while the upstream stays proxied. The
alternative this item offered — marking the failing test `cell` — was **not**
taken: it passes on the host, and excluding it would have hidden the defect
rather than fixed it. One correction to the reasoning below, from review: the
open question is not whether `--internal` makes these variables inert.
`DESIGN.md` §5.1 records that an `--internal` network still routes to the host
gateway, which is why `assert_host_is_unreachable` exists. What makes the
change safe is narrower and measured — `10.88.0.1` matches neither `NO_PROXY`
entry, so nothing the gateway exposes becomes reachable.

`saffron/cell/proxy.py:proxy_env` returned `{"HTTPS_PROXY": url, "HTTP_PROXY":
url, "NO_PROXY": ""}`. Empty means *nothing* bypasses squid — `127.0.0.1`
included. `test_the_probe_script_itself_answers_a_401` binds an `HTTPServer` on
loopback and probes it
with `preflight._UPSTREAM_PROBE`, which uses `urllib` and so honours the proxy
variables. The container's request to itself is routed out to squid, which
allowlists only the upstream, and is denied.

Measured on `SA-0040`, 2026-09-01. In-cell baseline: `1 failed, 1094 passed`.
Same commit on the host: `1 passed`. That run's teardown printed ten of these,
one per suite execution across baseline, two gate attempts and the
post-rebuttal run:

```
teardown: proxy DENIED … TCP_DENIED/403 3367 GET http://127.0.0.1:37283/v1/models
```

Three costs, in increasing order of seriousness:

- **Every cell run starts with a red `tests` gate.** Baseline subtraction
  absorbs it correctly, which is exactly why it has gone unnoticed since the
  proxy was wired.
- **It misleads the critic.** `SA-0040`'s correctness lens opened its blocker
  with "the `tests` gate reports 1 failure in this run", reasoned to the
  nearest new test, and raised a blocker against the golden fixture's digest.
  The digest was fine — mutating it fails the assertion — but the rebuttal
  turn's artifact was itself lost to a JSON parse error, so the pull request
  shipped a `confirmed` disagreement founded on this line. One environment
  papercut cost a lens finding, a rebuttal, and an operator adjudication.
- **It trains the operator to skim the denials.** `teardown: proxy DENIED` is
  the channel that would show a cell trying to reach something it should not.
  Ten lines per run that are one repo test talking to itself is noise in the
  one place noise is most expensive.

## Done looks like

a decision, not a patch. `NO_PROXY=""` is the correct isolation
posture for anything off-box and must not be widened to hosts. The open
question is whether loopback *inside the container* — which is the cell
itself, and reaches nothing the cell does not already have — belongs behind
the boundary at all. If it does, the alternative is that `saffron`'s own suite
cannot contain a test that binds a socket, and `test_the_probe_script_itself _answers_a_401` should carry the `cell` marker and say so.
