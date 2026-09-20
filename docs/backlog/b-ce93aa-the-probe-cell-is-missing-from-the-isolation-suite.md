---
id: b-ce93aa
title: The probe cell's `env` is pinned by no test the operator runs by default
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§2, §5.5]
related: [b-a70ec1]
---

## Problem

Found by the spec loop's Spec seat reviewing #375, 2026-09-19.

`_probe_adequacy` creates its Gate-only cell with `env=dict(thread_env)`, the
repo's declared gate env and nothing more. Replacing that with
`env=dict(os.environ)` survives the whole default suite. The code that keeps a
host `ANTHROPIC_API_KEY` out of the probe cell is guarded by nothing the
operator runs by default.

`CLAUDE.md` says isolation tests must start a cell the way production does and
probe from inside it, and those live behind `-m cell`. The probe cell is a new
cell that never joined them.

## Done looks like

The cell-marked isolation suite starts a probe cell the way `_probe_adequacy`
does and probes its environment from inside.

## Record

- 2026-09-19: filed from the spec loop's run 9 (#375).
