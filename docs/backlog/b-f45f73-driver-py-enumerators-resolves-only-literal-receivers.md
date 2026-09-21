---
id: b-f45f73
title: The `enumerators` subcommand resolves only literal receivers, so on this repository it lists all 35 calls as unresolved
status: open
tier: 2
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: []
related: [b-b69bb6, b-2750d5]
---

## Problem

Split out of `SA-0115` by the operator in the spec loop's run 11, 2026-09-21.

Four review rounds did not converge on resolving a call's receiver through
Python names, imports, module attributes, `__file__` and scopes. Each round found
another way to build the resolver wrong. `SA-0115` now resolves a receiver only
where it is a string literal, `Path` of one, or a `/` join of those.

None of the 35 enumerating calls under `tests/` at `d5de5176` has such a
receiver. So the command lists every one as unresolved, the same for every spec.

The four rounds found these, and the follow-up starts from them.

- `TURNS_DIR` is two constants, the second built on the first
  (`saffron/agents/context.py:21-22`).
- The real import names the module second: `from saffron.agents import
  artifacts, context` (`tests/test_context.py:8`).
- Every real `<module>.__file__` comes through a `from` import, as
  `tests/test_cli.py:17` and `:196` do. No test imports a local module plainly.
- A function binding can shadow a module one, and the claim named no order.

A rough count of the 35 receivers: about 17 resolve within one file, through
`__file__` or a name assigned once. About 14 are `tmp_path`, fixtures or
parameters, which point at temporary directories no resolver can map to the
repository.

## Done looks like

A spec, written and reviewed outside a loop, resolves those receivers. It
classes the temporary-directory ones as no repository path, so the unresolved
list stops carrying them.

## Record

- 2026-09-21: filed from the spec loop's run 11 (#406).
