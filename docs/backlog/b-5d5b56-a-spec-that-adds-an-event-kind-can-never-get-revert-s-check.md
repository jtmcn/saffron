---
id: b-5d5b56
title: A spec that adds an event kind can never get `revert`'s check, because the reverted suite fails to collect
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§5.4]
related: [49, 50, 51]
---

## Problem

Found in the spec loop's run 8, 2026-09-18, at `SA-0101`'s spec review. The
cell confirmed it.

`tests/test_events.py` builds its parametrize lists at module scope:
`_ONE_OF_EACH` (`:74`, used at `:117` and `:561`) and `_JOINED` (used at
`:1967`). A spec that adds a kind puts an instance of it in those lists. With
the source reverted, the name does not import, so the whole module fails to
collect.

`revert` then has no verdict to read. `SA-0101`'s ledger row for `revert` is
`skip`: "the reverted run returned error and no readable verdict — no new test
was seen to pass without its source". Every new test in #351 went without the
check.

Item 51 is a cell buying a skip on purpose. This one is structural: no spec
that adds a kind can avoid it.

## Done looks like

`revert` runs each new test's node on its own, or collects around a module
that fails to import. One error then no longer costs every new test its verdict.
Or `tests/test_events.py` builds its kind lists inside a fixture, and a test
holds that no module-scope list names a kind. A spec that adds a kind then gets
`pass` or `fail` from `revert`.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353).
