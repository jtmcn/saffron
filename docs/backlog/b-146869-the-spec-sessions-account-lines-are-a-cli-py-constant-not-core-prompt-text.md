---
id: b-146869
title: The spec session's account lines are a `cli.py` constant, not core prompt text in `saffron/agents/prompts/`
status: open
tier: 3
filed: 2026-09-27
closed:
specs: []
prs: []
commits: []
cites: []
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 19, 2026-09-27, by the Standards seat on #553.

`SA-0156` put the lines that tell a spec session about its account in
`_SPEC_SESSION_ACCOUNT_LINES` (`saffron/cli.py:668`). ADR 7 puts core's prompt
text in `saffron/agents/prompts/`
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:63-64`).
`SA-0176` builds the spec writer session and will copy the constant.

## Done looks like

The lines live in a prompt file under `saffron/agents/prompts/`, and both
spec sessions load it.

## Record

- 2026-09-27: filed from the spec loop's run 19.
