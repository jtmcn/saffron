---
id: b-6a9707
title: The spec loop's driver calls a gate result and a probe outcome a verdict
status: open
tier: 3
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: []
related: [b-281f0a]
---

## Problem

Found by the spec loop's Standards seat reviewing #382, 2026-09-19, and
verified by the delegate.

`CONTEXT.md:285` is an explicit `_Avoid_` line. "verdict" is the critic's
confirm-or-withdraw of a finding. `CONTEXT.md:430-432` says it again:
"Three judgements, three words: the critic **verdicts**, the operator
**adjudicates**, the implementer **rebuts**. Never call any of them 'the
verdict' without saying whose." `saffron/agents/findings.py:50-51` enforces it
by name in the code that matters.

`.claude/skills/run-saffron-spec-loop/driver.py` uses the word for the `size`
gate's result and for a probe's outcome, at `:592`, `:1123` and `:1166-1174`.
All predate #382, which is why that review held it to a note.

Nothing catches it. `.saffron/gates/prose.py` returns no `terms` findings for a
`.py` path, so the gate checks only comment and docstring length there.
`tests/records/check.py`'s `LIVE_SURFACES` does not scan `.claude/` at all.
`CLAUDE.md` says vocabulary is enforced including the `_Avoid_` lists. For this
file nothing enforces it.

## Done looks like

The three uses are renamed. Then the `terms` gate reaches `.py` under
`.claude/`, or the file joins a surface `tests/records/check.py` scans. The
next one is caught rather than reviewed.

## Record

- 2026-09-19: filed from the spec loop's run 10 (#382). #382's own new use of
  the word was fixed in that pull request's review commit. These three are the
  ones it inherited.
