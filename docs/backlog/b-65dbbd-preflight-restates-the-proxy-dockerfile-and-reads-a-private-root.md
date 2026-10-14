---
id: b-65dbbd
title: Preflight spells the proxy's Dockerfile as a literal and reads a private root, because no module names either
status: open
tier: 3
filed: 2026-10-14
specs: [SA-0289]
prs: [871]
commits: []
cites: [§5.1.2]
related: [b-1c20da]
---

## Problem

Found by the Standards seat on #871 in the spec loop's run 38.

`SA-0289`'s `images` step pairs each tag with its Dockerfile. Review made the
base's path derive from `image.BASE_DOCKERFILE`. The proxy has `PROXY_TAG` in
`saffron/cell/proxy.py` but no Dockerfile constant, so `preflight.py` and its
witness spell `images/proxy.Dockerfile` by hand. The step also reads
`image._SAFFRON_ROOT`, a private name. `_SAFFRON_ROOT` is defined twice, in
`saffron/cell/session.py` and `saffron/repos/image.py`.

## Done looks like

`proxy.py` names its Dockerfile beside its tag. One module defines the Saffron
root under a public name, and every reader imports it.

## Record

- 2026-10-14: filed from the spec loop's run 38.
