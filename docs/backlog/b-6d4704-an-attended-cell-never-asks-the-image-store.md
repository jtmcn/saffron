---
id: b-6d4704
title: An attended cell never asks the image store, and the glossary's Preflight lists none of readiness's newer steps
status: open
tier: 3
filed: 2026-10-14
specs: [SA-0289]
prs: [871]
commits: []
cites: [§4.2.1, §5.1.2]
related: [b-1c20da]
---

## Problem

Found by both seats on #871 in the spec loop's run 38.

`SA-0289` added the `images` step to `check_readiness`, which `saffron batch`
and `saffron draft` call. `saffron cell` never calls it, so an attended cell
on an empty store still asks a registry for the proxy. The spec left this out
on purpose.

`CONTEXT.md`'s **Preflight** entry lists mirror fetch, policy parse, image
rebuild and baseline. It names neither auth, disk headroom nor `images`.

## Done looks like

An attended cell runs the `images` step before its first container, or the
skill says why it does not. The **Preflight** entry names the steps readiness
runs.

## Record

- 2026-10-14: filed from the spec loop's run 38.
