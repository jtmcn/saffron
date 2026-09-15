---
id: 101
title: 'The rename stopped at the vocabulary: the program, its paths and its boundaries still say "saffron"'
status: open
tier: 3
specs: []
prs: [192]
commits: []
cites: [§2.1]
related: [56, 58]
---

## Problem

**Tier 3.** PR #192 moved the vocabulary to `factory:` (`CONTEXT.md` settled
naming decision 6) and deliberately stopped there. The operator's framing is that
the environment is a software factory, and that naming it after the program was a
mistake; the rest of the repository still says otherwise. Measured 2026-09-10
over tracked files:

- **Names only** — change them and nothing outside this repository notices:
  - the Python package `saffron/` (47 modules, 591 import lines), and the
    distribution name and `saffron` CLI entry point in `pyproject.toml`;
  - "Saffron" as a word — 18 in `CONTEXT.md` (its **Saffron** entry among them),
    60 in `DESIGN.md`, 5 in `CLAUDE.md`, 14 here;
  - the `SAFFRON_ALLOW_HOST_PROCESS`, `SAFFRON_GATE_ENV`, `SAFFRON_PKG` and
    `SAFFRON_ROOT` environment variables (the first is set on the host, so this
    reaches host configuration too), the `run-saffron-spec-loop` skill, and the
    `dev.saffron.batch` launchd label.
- **Boundaries** — each has state or another repository behind it, so renaming
  one is a migration, not an edit:
  - `~/.saffron/` — the ledger and the batch tree, named in 81 files. The existing
    ledger is the audit trail, and a path that cannot read it loses it.
  - `.saffron/` in every target repo — 743 references, 82 tracked files here. It
    is the onboarding contract (§2.1), so renaming it changes every onboarded
    repo, not this one.
  - The task-branch prefix `saffron/<SPEC-ID>` — 183 references. Open pull
    requests and the mirror carry it.
  - The image names `saffron/cell` (355), `saffron/cell-base` (34) and
    `saffron/proxy` (6), and the cell runtime's networks and volumes
    (`saffron-cells` 29, `saffron-egress` 9, `saffron-proxy` 6, `saffron-wt` 17,
    `saffron-st` 8). An `ORPHANED` task's volumes are preserved until
    `saffron gc` reclaims them, so a rename has to leave `gc` able to find the
    old ones.
  - The `saffron:retired-by` marker — 29 references, and it lives in target
    repos' source, where the scheduler reads it.
  - The repository itself, `jtmcn/saffron`.

## Done looks like

a plan, not one spec — the shape item **58** took, for the
reason item **56** measured: a change this wide through a cell ends `EXHAUSTED`.
It opens with the one decision nobody has made, what the program is called once
the factory is not, recorded as a settled naming decision before any rename
lands. Then the names-only half in one pass, and each boundary with its own
migration: the ledger and batch tree read from both paths for a release; the
target-repo directory and the marker accepted under both spellings until every
onboarded repo has moved; the branch prefix changed only for tasks started after
the change. Guard it the way #192 did — a test that fails on a stale spelling,
run both ways.
