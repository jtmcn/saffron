---
id: b-7fa522
title: "The path `.saffron/policy.yaml` is spelled out in five modules"
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 47, by the Standards seat on `SA-0314` (#956).

`saffron/spec_citations.py` added `_POLICY_PATH`, a fifth copy. The others sit in
`saffron/repos/policy.py`, `saffron/cli.py` twice and `saffron/preflight.py`.
`saffron/repos/policy.py` exports no constant, so no caller can import one.

## Done looks like

`saffron/repos/policy.py` exports the path, and every other module imports it.

## Record

- 2026-10-24: filed from the spec loop's run 47.
