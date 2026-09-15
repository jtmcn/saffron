---
id: 55
title: '`dist/` is not gitignored, so a build artifact is one `git add -A` from being committed'
status: open
tier: 3
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

`uv build` writes `dist/` and nothing ignores it. It is not present in a clean
tree, so it is invisible until someone runs a build — and `pyproject.toml`'s
`packages = ["saffron"]` is a claim worth checking by building, which is how this
was found.

## Done looks like

one line in `.gitignore`. Filed rather than fixed in passing
because it belongs to no branch in flight; it is a two-minute item for whoever
touches packaging next.
