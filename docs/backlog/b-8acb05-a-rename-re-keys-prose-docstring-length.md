---
id: b-8acb05
title: "`prose` keys a long docstring by its function's name, so a rename makes an old one new, and joining lines slips it back under"
status: open
tier: 2
filed: 2026-10-08
specs: [SA-0225]
prs: [746]
commits: []
cites: [§5.4]
related: []
---

## Problem

Measured in the spec loop's run 31, on #746.

SA-0225 renamed `pr_body._problem` to `extract_problem`. `_long_docstrings`
keys its hit on `node.name` (`.saffron/gates/prose.py:319`), so the rename
alone reports the eleven-line docstring as a new `docstring-length` hit. The
cell joined two of its lines into one of 103 characters. That put the
docstring at ten lines, and the gate passed. `E501` is ignored
(`pyproject.toml`), so no gate saw the long line.

The spec said to change nothing else in that file. Both seats raised it, and
the end review did too. A review commit shortened the docstring to eight
lines.

## Done looks like

A rename does not make an unchanged docstring a new hit, and a docstring
cannot leave the hit by joining lines. A rule-test shows both cases.

## Record

- 2026-10-08: filed from the spec loop's run 31.
