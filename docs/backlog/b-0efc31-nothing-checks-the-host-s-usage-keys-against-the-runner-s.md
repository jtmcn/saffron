---
id: b-0efc31
title: "Nothing checks the host's copies of the runner's usage keys, so a renamed key makes the cost floor price nothing"
status: open
tier: 3
filed: 2026-10-05
specs: []
prs: []
commits: []
cites: [§4.1]
related: []
---

## Problem

Found in stage 2 of the delegate-loop plan, on `SA-0206`.

`images/agent_runner.py` defines `_RESULT_USAGE_KEYS` and `_STEP_USAGE_KEYS`
(`images/agent_runner.py:31`, `:37`). `saffron/phases/implement.py` restates
them as `_TOKEN_USAGE_KEYS` and `_STEP_USAGE_KEYS`
(`saffron/phases/implement.py:119`, `:128`). The host never imports the
runner, which imports the Agent SDK and executes only in the cell. No test compares
the two.

A key renamed in the runner leaves the host reading a key no event carries.
The cost floor then prices nothing, and no error says so.

## Done looks like

A test reads both modules' tuples and fails when they differ.

## Record

- 2026-10-05: filed from stage 2 of the delegate-loop plan (the first live stack batches, batches 13 and 14).
