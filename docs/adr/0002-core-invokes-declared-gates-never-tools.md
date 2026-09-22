---
id: 2
title: "Core invokes declared gates, never tools"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [C, H, I]
principles: [12, 13, 14, 29, 34, 36, 39, 41]
---

## Context

Appendix C made Saffron repo-agnostic with one structural change, the gate
contract. A gate is an executable that emits one JSON object and translates its
own tool's output. So the repair loop, the baseline subtraction and review read
`failures[]`, and never a tool's output.

The decision is spread across §2.1, §5.4, §11 and three appendices. Appendix H
added the `tool` field, because a green result and an absent result were the
same bytes. H also made a partial result an `error`.

Appendix I measured the boundary. Onboarding Saffron to itself left `saffron/`
untouched. I also found a leak in each direction. Core hard-coded a Python base
image, and a core probe then required a Python interpreter in every repo's image.

`revert` runs something. The rule read "core never executes" before `revert`,
and it was false once `revert` existed. §2.1 restates it in the shape the
exception fits.

## Decision

Saffron core knows diffs, git, containers, budgets and the shape of a gate
result. It knows no language, test runner, package manager or database. Those
live in the target repo's `.saffron/`. Onboarding a repo touches zero lines of
`saffron/`.

A gate is an executable in `.saffron/gates/` that emits one JSON object on
stdout. The object carries `gate`, `status`, `tool`, `failures` and `summary`,
and optionally `collected`. `status` is one of `pass`, `fail`, `skip` and
`error`. The gate obtains `tool` by executing its tool. A partial result is
`error`, and so is a non-zero exit with no failures.

When core needs to run anything, it runs a gate the repo declared, through the
same contract. It never runs a tool. `revert` is the one core gate that does
this. It re-invokes the repo's `tests` gate with a test subset. A future core
gate that needs to run something fits that shape or moves to the repo.

Where a check reads as language-specific, core keeps the question and the repo
declares the tokens. `integrity` reads its suppression tokens and gate-config
paths from `policy.yaml`.

`committed` reads `git status` in the cell, which widens core's in-cell git
surface. It stays inside the rule, because the check is a pure function over
paths. It is a stated residual, not a second exception.

## Principles

- **12** upholds. The contract is the boundary, and no plugin layer sits behind
  it. A second implementation of anything waits for a repo that needs it.
- **13** upholds. `integrity` keeps the question in core and the tokens in
  `policy.yaml`.
- **14** departs. Every onboarded repo is Python. Appendix I measured an empty
  diff to `saffron/` for one repo. The third repo §9 names is the test, and no
  such repo is onboarded yet.
- **29** upholds. §2.1 states `revert` as the exception, so the rule survives
  it.
- **34** upholds. The contract carries `tool`, so a gate that ran and passed
  differs from one that never ran.
- **36** upholds. A gate that breaks part-way reports `error` for the whole
  run, never `fail` on what it collected.
- **39** upholds. `tool` comes from running the tool, not from locating it.
- **41** upholds. Core's own checks run on artifacts core owns, and demand no
  language of a repo's image.

## Consequences

Each gate costs its repo about 20 lines of shell, and the orchestrator holds no
parser. A repo with no analogue for a role omits the gate, and core changes
nothing.

The `structure` gate rejects a Python gate whose `tool` is a string literal.
`.saffron/gates/format` builds its contract in `sh`, which no rule reads
(backlog item 77).

No test asserts that onboarding touches zero lines of `saffron/`. Appendix I
measured it once. §11 expects one field of the contract to be wrong for the
third repo, and it changes then.
