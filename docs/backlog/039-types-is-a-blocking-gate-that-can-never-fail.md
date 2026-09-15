---
id: 39
title: '`types` is a blocking gate that can never fail'
status: done
tier: null
closed: 2026-09-01
specs: []
prs: [92]
commits: []
cites: [§5.4]
related: []
by_hand: true
---

## Problem

**Status:** **done**, by hand, on `joel/ty-typechecking`. The gate executes
`ty` (pinned exactly in `pyproject.toml`), `[tool.pyright]` is gone, a prek hook
carries it into `make check` and CI, and `.saffron/Dockerfile` asserts
`ty --version`. `policy.yaml` is unchanged, as this item predicted. Two things
it did **not** predict, both measured:

**ty, not pyright, and the reason is the cell.** The `pyright` PyPI package is a
Node wrapper that downloads a runtime on first use. `cell-base.python` has no
node, and the proxy allows one host — so the download takes a 403, the same
failure the Dockerfile's `UV_NO_SYNC` note already records for `uv run`. ty is a
single binary from ruff's vendor. It is also the better surface for the agent in
the loop: 0.09s against 1.97s on this tree, 23 KB of `concise` output against
pyright's 127 KB of JSON, and no duplicates (13% of pyright's 206 diagnostics
were exact repeats). Deduped, the two agree on the same production defects.

**"neither touches `saffron/`" was wrong**, and usefully so — turning the gate on
found 11 real defects in it: five `int(cursor.lastrowid)` where sqlite types the
value `int | None`, a `list[str] | None` iterated in `criteria`, two
`list[X] = ()` defaults in `pr_body`, and `fields()` on an untyped `_KINDS`.

**The mutation this item was written about is caught by nothing, and that is not
a ty limitation.** Measured against the shipped gate:

| mutation | `types` | `test_the_enumerations_are_pinned` |
|---|---|---|
| `ceiling: Ceiling` widened to `ceiling: str` | pass | pass |
| `Terminal` dropped from the `Event` union | **fail** | pass |
| a member removed from `Ceiling` | **fail** | **fail** |
| a member added to `Ceiling` | pass | **fail** |

Widening a type cannot error in any checker unless some code exercises the wider
value, and none does; pyright behaves identically. So this item's reading of
`test_the_enumerations_are_pinned` as a "substitute" is backwards — it is the
only control over a member quietly *added* or renamed, and it stays. The row the
gate uniquely covers is the dropped union member.

Caught in review, and the sharpest finding of the branch: the first version set
`[tool.ty.environment] python = ".venv"`. A cell worktree is a fresh
`git init`/fetch/checkout and `.venv` is gitignored, so it is never present —
and a configured environment ty cannot resolve is a hard failure, exit 2 with
nothing on stdout, which this gate correctly calls `error`. `error` aborts the
attempt and is charged to nobody (§5.4), so a blocking `types` gate would have
aborted every attempt against this repo. Item 39 would have been closed by
replacing a gate that could never fail with one that could never run. Reproduced
against a clean clone before fixing; the fix is that ty resolves the environment
from its own executable, so `/opt/venv/bin/ty` finds `/opt/venv`. The test that
should have caught it now exists — none of the others paired the repo's own
config with a tree shaped like a cell's.

The parser is `concise` and reconciles against ty's own `Found N diagnostics`
trailer, so a diagnostic it cannot key (one carrying no line, a message shape
that moved) is `error` rather than a smaller repair target than the real one.
Exit codes beyond 0 and 1 are `error` for the same reason. ty's only JSON output
is its `gitlab` format, which is a schema name and not a destination; a flag
naming a forge this repo does not use would read as an integration it is not.

`# ty: ignore` joins `integrity.suppressions`. ty honours it, and before this
branch that did not matter because nothing enforced types; a blocking gate with
a suppression syntax the anti-gaming gate cannot see is the hole that gate
exists to close.

One standing cost, recorded rather than fixed: `docs/evidence/scripts/` is in
scope, so every future evidence script — a verbatim record of something already
executed — must type-check or a blocking gate goes red. Three existing ones
needed an `assert spec and spec.loader`.

Also fixed in passing: the gate's implementation was first written as
`.saffron/gates/types.py`, which sits on `sys.path[0]` and shadows the stdlib
`types` every `import json` reaches through. It crashed under one interpreter
and survived under another, writing nothing to stdout — a gate that did not run,
reported as nothing at all. Renamed `typecheck.py`, with a test asserting no
gate script shadows a stdlib module name.

`.saffron/gates/types` emits `skip` unconditionally, `policy.yaml` declares it
`blocking: true`, and `pyproject.toml` carries a configured `[tool.pyright]`
block that nothing runs — pyright is not a dependency, a hook, or installed.
`policy.yaml`'s own note on `shacl`, five lines below, states the principle this
breaks: *a control that reads as present and is not is the founding defect of
Appendix I.*

Measured while reviewing PR #91: mutations replacing `Ceiling` and
`TerminalReason` with bare `str`, and removing `Terminal` from the `Event`
union, all left the suite green. `saffron/events.py` is a module whose whole
value is type safety, and `tests/test_events.py` now hand-rolls
`test_the_enumerations_are_pinned` as a substitute.

## Done looks like

pyright as a dev dependency and `.saffron/gates/types`
executing it — the gate is already declared and already blocking, so nothing in
`policy.yaml` changes. Or, if that is not wanted, the gate stops claiming to
block. Either is a repo-side change and neither touches `saffron/`.
