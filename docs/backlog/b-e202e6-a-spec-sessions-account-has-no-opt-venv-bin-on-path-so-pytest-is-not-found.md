---
id: b-e202e6
title: A spec session's unprivileged account has no `/opt/venv/bin` on `PATH`, so plain `pytest` is not found
status: open
tier: 2
filed: 2026-09-27
closed:
specs: []
prs: []
commits: []
cites: [§5.1]
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 19, 2026-09-27, in `SA-0169`'s cell test (#550).

`SA-0181` runs a spec session's `Bash` as an unprivileged account. That
account's `PATH` lacks `/opt/venv/bin`, so a plain `pytest` is not found. ADR 7
bars core's prompts from naming a repo's tools, so the prompt cannot tell the
session where `pytest` lives. The Standards seats on #551 and #553 met the
same gap.

## Done looks like

The account's `PATH` matches root's in the image or in `SA-0181`'s wrapper.
Or a policy field declares the tool path. A cell-marked test runs `pytest` as
the account.

## Record

- 2026-09-27: filed from the spec loop's run 19.
