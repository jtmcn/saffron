---
id: 177
title: attempts.model is writable and no attempt supplies it
status: open
filed: 2026-09-17
specs: []
prs: []
commits: []
cites: [§4.1]
related: []
---

## Problem

`SCHEMA` declared `attempts.model` in v0.5. Nothing wrote it.

Task 6 of the prompt-change-measurement plan gave `close_attempt` a `model`
parameter. Its own call site in `saffron/cell/session.py` still passes `None`,
because no model value reaches that call site today.

`images/agent_runner.py:131` checks `hasattr(message, "model")` only to tell
an assistant message from a result message. It does not read the model
string out or put it in an event. `AttemptResult` in
`saffron/phases/implement.py` has no `model` field to carry that value even
if the event carried it.

A prompt comparison reads `tasks.prompt_sha` beside `attempts.model` to ask
whether a result came from the prompt tree it names or from a different
model. With `model` always `None`, that question stays unanswered. The
comparison cannot rule out that the model moved underneath the prompt.

## Done looks like

`images/agent_runner.py` emits the model string on its own result event, and
`implement.py`'s `AttemptResult` field carries it to the call site.
`saffron/cell/session.py` passes that value to `close_attempt` instead of
`None`.

An attempt row then names the model that produced it. A prompt comparison
can tell whether the model moved underneath the prompt.

## Record

**Filed 2026-09-17**, from Task 6 of the prompt-change-measurement plan. That
task added the `model` parameter to `close_attempt` and the column write
path. It left the call site's real value as a gap.

Closing it touches `images/agent_runner.py`, the file gated as the sole
importer of the Agent SDK. It also touches `saffron/phases/implement.py`.
Both sit outside that task's file scope.
