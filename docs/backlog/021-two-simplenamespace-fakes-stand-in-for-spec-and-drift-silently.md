---
id: 21
title: Two `SimpleNamespace` fakes stand in for `Spec` and drift silently
status: done
tier: null
closed: 2026-08-28
specs: [SA-0012]
prs: [49]
commits: [f31550c]
cites: [§5.4]
related: [24]
---

## Problem

`tests/test_package.py:679` and `:783` build a `Spec` out of `SimpleNamespace`,
carrying whatever attributes `package()` happened to read when they were written.
They are not typed, so nothing checks them against the model, and they do not
fail when `Spec` gains a field — they fail later, when some renderer finally
*reads* that field, in tests that are nominally about something else entirely.

That is exactly how it went. `SA-0011` added `Spec.acceptance` and nothing
noticed for three tasks; the moment `pr_body._criteria` read it, fourteen
PACKAGE tests died on `AttributeError: 'types.SimpleNamespace' object has no
attribute 'acceptance'` — none of them about acceptance criteria, all of them
about pushes, conflicts and queue lines.

**The trap is the `touches` interaction, and it is what makes this worth an
item.** A spec's `touches` is written by reasoning about which files the change
*should* need, and nobody knows these fakes exist until the code runs. So the
cell hits a wall with no way over it: editing `tests/test_package.py` fails
`scope`, and leaving it fails `tests`. Both burn the attempt, on every attempt,
until the budget is gone — and the agent cannot widen its own `touches`, which
is the point of `touches`. `SA-0011` only got past it because a human was
watching and amended the spec. An unattended night would have spent the whole
budget on it.

The blast radius is small and was measured, not assumed: these two are the only
structural `Spec` doubles in the repo. `tests/test_session.py:86` builds a real
`CellSpec`, `tests/test_report.py` goes through `parse_spec`, and
`saffron/replay.py:51` uses a real `Spec` from `load_spec`. `CellSpec` is never
`asdict`-ed or serialised, so a pydantic model inside the dataclass costs
nothing.

Tempting and wrong: `getattr(spec, "acceptance", [])` in `pr_body`. It makes a
missing field indistinguishable from an empty one, which is §5.4's `tool` defect
in a third costume — and it puts a default in production code to accommodate a
test fake.

## Done looks like

both call sites building a real `Spec` (via `parse_spec` on
a string literal, as `tests/test_report.py` already does), so the next field
`Spec` gains is a type error at construction rather than an `AttributeError` in
an unrelated suite three tasks later. Roughly twenty lines.

## Record

**Status:** **done**, driven from `SA-0012`
(`.saffron/specs/done/SA-0012-spec-doubles.md`) in PR #49 (`f31550c`). Both call sites
now build a real `Spec` through `parse_spec`. Found by `SA-0011`. Review of that
diff found the defect had moved rather than died — value drift where this was
shape drift — which is item 24. Read what follows for why the fakes cost what
they did, not as work outstanding.

**One thing it left.** `SA-0011`'s `touches` still names `tests/test_package.py`
(`.saffron/specs/done/SA-0011-criteria-have-witnesses.md:24`), declared only because
of these fakes. `SA-0012` and `SA-0013` both put it out of scope, and
`.saffron/**` is `forbidden` in every spec — no cell can do it. It wants a
human edit.
