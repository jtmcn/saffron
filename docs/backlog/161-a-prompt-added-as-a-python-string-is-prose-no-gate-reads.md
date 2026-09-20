---
id: 161
title: A prompt added as a Python string is prose no gate reads, and the rule putting prompts in Markdown is convention
status: open
tier: 3
filed: 2026-09-17
by_hand: false
specs: []
prs: [312, 313, 317]
commits: []
cites: [§5.3, §5.4]
related: []
---

## Problem

Found filing PR #312, which moved nine turn prompts into
`saffron/agents/prompts/turns/*.md`. PR #313 put that directory in the `prose`
gate's scope.

The gate reads Markdown listed by `git ls-files` and nothing else. A prompt
written as a string literal in Python is invisible to it. That was the state of
every turn prompt before #312: 12 hits of the house style, in prose a cell
reads on every task, in files the gate never opened. The count is the nine
constants as PR #310 left them, passed to the gate's own `check`. The moved
files measured the same 12, and PR #317 takes them to zero.

Nothing stops the next prompt from being written the same way. The convention
lives in a docstring and in the shape of a directory. The `tool` field and
`run_one_cell` were conventions too, until a rule was written for each
(Appendix H, `.saffron/rules/`).

Three properties that make this checkable are already true.
`context.turn_prompt` is the one loader, `TURNS_DIR` is the one directory, and
a test asserts that every file there is loaded by a named constant. The missing
direction is the other one: a prompt-shaped string literal in `saffron/` that
came from no file.

## Done looks like

An `ast-grep` rule under `.saffron/rules/` fails a string literal assigned to a
name ending in `_PROMPT` anywhere in `saffron/`. Its sanctioned sources are
`turn_prompt` and `build_system_prompt`. The rule ships with the mutant that
proves it fires, as every rule there does, and `uv run ast-grep test -c
.saffron/sgconfig.yml` covers it.

Two edges the rule settles rather than ignores. `repair_prompt` in
`saffron/phases/implement.py` builds its text from gate failures at runtime and
is no template. The prompt strings in `harness/` and `docs/evidence/scripts/`
are measurement code, outside what a cell reads.

## Record

**Filed 2026-09-17** while stacking PRs #312 and #313.
