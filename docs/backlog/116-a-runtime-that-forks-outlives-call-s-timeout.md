---
id: 116
title: A runtime that forks outlives `_call`'s timeout
status: open
tier: 3
filed: 2026-09-14
specs: [SA-0079]
prs: [245]
commits: []
cites: []
related: []
---

## Problem

**Tier 3.** Found reviewing `SA-0079` (PR #245), 2026-09-14. `saffron/cell/runtime.py:255`
runs every runtime command through `subprocess.run(..., timeout=...)`, which kills
only the direct child. `SA-0079`'s hang witness showed the mechanism on its own
stub: `sh` running `sleep 300` left the sleep orphaned under PID 1 for five minutes
on every run, until #245 made it `exec sleep`. `container` and `podman` (via
conmon) both fork, so a runtime that hangs past a timeout can leave its children
running on the host. Unverified against a real runtime.

## Done looks like

`_call` starting the runtime in its own process group and
killing the group on timeout, with a witness whose stub forks and whose child is
gone once `_call` returns.
