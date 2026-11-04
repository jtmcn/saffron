---
id: b-249808
title: No gate checks the spec ids a diff cites, so a cell cited another spec at 20 sites
status: open
tier: 2
filed: 2026-11-04
specs: []
prs: []
commits: []
cites: [§5.4]
related: []
---

## Problem

Found by both review seats on #1016, in the spec loop's run 53.

`SA-0330`'s cell cited `SA-0332` at every new comment and docstring, 20
sites in seven files. It cited `SA-0330` at none. `SA-0332` is a different
draft, named in b-4a9207. Every gate passed it, and review commit `cf2e73fe`
fixed it.

## Done looks like

A gate fails a diff that cites a spec id it cannot find. The id must be the
task's own, or a spec in `.saffron/specs/` or `done/`.

## Record

- 2026-11-04: filed from the spec loop's run 53.
