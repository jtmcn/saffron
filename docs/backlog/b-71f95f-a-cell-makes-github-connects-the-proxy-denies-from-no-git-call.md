---
id: b-71f95f
title: "A cell makes CONNECTs to github.com that the proxy denies, and no git call makes them"
status: open
tier: 2
filed: 2026-11-06
specs: [SA-0334, SA-0335]
prs: []
commits: []
cites: [§2]
related: []
---

## Problem

Found in the spec loop's run 54.

`SA-0334`'s teardown logged 14 proxy-denied CONNECTs to github.com:443, and
`SA-0335`'s logged 2. Both seats checked the test suite.

- The full default suite passes under `GIT_ALLOW_PROTOCOL=file`.
- A git PATH shim over the suite logged 2061 calls, none to an https, ssh or
  `git@` URL.
- A `GIT_TRACE` run logged 100 pushes and fetches to https URLs and no
  `remote-https` helper start, so git refused each one before any transport.

So the CONNECTs came from something other than git. The proxy denied them, so
nothing left the cell. What made them is unknown.

## Done looks like

Each denied CONNECT in a teardown log names the process that made it, and the
cell's own runs make none to the forge.

## Record

- 2026-11-06: filed from the spec loop's run 54.
