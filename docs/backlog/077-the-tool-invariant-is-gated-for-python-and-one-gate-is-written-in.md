---
id: 77
title: The `tool` invariant is gated for Python, and one gate is written in shell
status: open
tier: 3
specs: []
prs: [145]
commits: []
cites: [§5.4]
related: []
---

## Problem

Found reviewing PR #145. `.saffron/rules/gate-tool-must-be-executed.yml` is
`language: python`, and `.saffron/gates/format` builds its whole contract in `sh`.
Measured: rewriting its `tool="ruff $(ruff --version | awk …)"` to
`tool="ruff 0.16.3"` — the literal §5.4 exists to forbid — leaves `structure`
reporting `pass`. Five of the six gates here are `sh` wrappers that `exec python3`
and so are covered; `format` is the one authored in shell, and a target repo
onboarding these rules may have more.

The Python side of this is now closed as far as a structural rule reaches,
including the contract serialized by hand as a single string — which is exactly
the shape `format` uses, so it is what a new Python gate copies.

## Done looks like

a `language: bash` rule in `.saffron/rules/` with its own
`invalid` snippet for `tool="<literal>"`, and `ruleDirs` already loads it. Cheap;
it is here rather than in #145 because the rule needs its own false-positive
measurement against the five wrappers and `format`'s own `case` arms.
