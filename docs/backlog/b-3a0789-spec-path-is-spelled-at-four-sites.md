---
id: b-3a0789
title: "The queued spec's repo path is spelled `f\".saffron/specs/{candidate.path.name}\"` at four sites"
status: open
tier: 3
filed: 2026-10-27
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 49, by the Standards seat on #977.

`saffron/batch.py:865` and `saffron/cli.py:752`, `:1237` and `:1352` each
build the same path. A change to where queued specs live has to find all four.

## Done looks like

One function names a queued spec's repo path, and each site calls it.

## Record

- 2026-10-27: filed from the spec loop's run 49.
