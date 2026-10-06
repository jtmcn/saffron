---
id: b-2e0b97
title: The engine ships only as a checkout, so no other operator can install it and no task records which engine judged it
status: open
tier: 2
filed: 2026-10-06
specs: []
prs: []
commits: []
cites: [§1.4, §2, §5.1.2]
related: [b-da550a, 170, 108]
---

## Problem

ADR 10 ships Saffron as an engine that each operator deploys. Today the engine
is a git checkout, run with `uv run saffron`. Every `saffron cell` rebuilds the
base image and the repo's image from that checkout (§5.1.2). So another
operator can only clone this repo and run its working tree.

A task records `policy_sha` and `prompt_sha` (`saffron/ledger.py:672`). It
records no engine commit. Two tasks judged by different engines read the same
in the ledger. The difference surfaces later as a gate that seems flaky.

On the laptop the engine and the target are one checkout. A merge to `main`
that breaks a gate path breaks the next night, including the night that would
repair it.

## Done looks like

An image is built from `main` and pushed to a registry, pinned by digest. It
carries the CLI and the base images it builds cells from. An operator runs
`saffron` from it with their home mounted.

Each task's record carries the engine commit, and the morning queue shows it.
A merge to `main` changes no deployment until its digest is bumped, and
rolling back is a digest bump too.
