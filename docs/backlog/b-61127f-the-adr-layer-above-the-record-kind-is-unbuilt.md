---
id: b-61127f
title: The ADR layer above the record kind is unbuilt, so nothing loads, indexes or judges a real decision
status: open
tier: null
filed: 2026-09-19
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [b-9ff0fd, b-27b9db, b-98dc4d]
---

## Problem

`SA-0110` (#377) built the record kind: the `Adr` model, the loader's
required-headings rule, `records list adr`, and three checks. It deliberately
stopped there, and `b-9ff0fd` closed with it. What is left has no owner.

- **`docs/adr/` and ADR 1.** The directory does not exist, so `records list
  adr` exits 2 against the live root. The kind is already offered in `--help`.
- **Wiring the three checks into `check_all`.** They sit behind
  `ADR_CHECKS_NOT_YET_WIRED` in `tests/records/test_records_check.py`, an
  exemption whose comment says the by-hand layer removes it with ADR 1.
- **`check_adr_principles`** and the reviewer half of the design's "Validation
  against the principles" (`.claude/agents/adr-reviewer.md`). The fixtures
  carry `## Principles` sections and a bullet form that nothing reads yet, so
  this also edits them.
- **`records show --kind`.** Cut when the first cell was refused for size.
- **`CONTEXT.md` §11**, which still says an ADR is prior art's record and that
  Saffron keeps no `docs/adr/`. With it goes `tests/test_citations.py`'s
  `test_saffron_keeps_no_adrs`, which passes only until the directory exists.
- **The ontology entry and `DESIGN.md`'s ADR index.**

Each is by hand or a later spec: `CONTEXT.md`, `DESIGN.md` and
`.saffron/policy.yaml` are `protected`, and the design orders ADR 1 after them.

## Done looks like

A real decision lives in `docs/adr/0001-*.md`, `check_all` runs the ADR checks
against it, and the glossary says what an ADR is here.

## Record

- 2026-09-19: filed when `b-9ff0fd` closed with #377, so the deferred half has
  a record of its own.
