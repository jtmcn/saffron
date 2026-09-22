---
id: 2
title: "Core invokes declared gates, never tools"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [C, F, H, I, M, N]
principles: [12, 13, 14, 29, 30, 34, 36, 39, 41, 52, 54, 57]
---

## Context

Appendix C made Saffron repo-agnostic with one structural change, the gate
contract. A gate is an executable that emits one JSON object and translates its
own tool's output. So the repair loop, the baseline subtraction and REVIEW read
`failures[]`, and never a tool's output.

The decision is spread across §2.1, §5.4, §5.4.1, §7, §11 and six appendices.
Appendix H added the `tool` field, because a green result and an absent result
were the same bytes. H also made a partial result an `error`.

Appendix F found that `revert` broke §2.1's boundary as stated. §2.1 said a
core gate that needs to execute something belongs on the repo side. F restated
the rule so the exception fits inside it: core invokes declared gates, never
tools.

Appendix M found the cheaper half. Test-set comparison looked like it needed
`revert`'s exception, and it needed one optional field in a result core already
held.

Appendix I measured the boundary. Onboarding Saffron to itself left `saffron/`
untouched. The same appendix found a leak in each direction. Core hard-coded a
Python base image, and a core probe then required a Python interpreter in
every repo's image.

## Decision

Saffron core knows diffs, git, containers, budgets and the shape of a gate
result. It knows no language, test runner, package manager or database. Those
live in the target repo's `.saffron/`. Onboarding a repo touches zero lines of
`saffron/`.

A gate is an executable in `.saffron/gates/` that emits one JSON object on
stdout. The object carries `gate`, `status`, `failures` and `summary`, and
optionally `collected`. `status` is one of `pass`, `fail`, `skip` and `error`.
A `pass` or `fail` also carries `tool`, which the gate obtains by executing its
tool. A `skip` names no tool, because nothing ran. Appendix H makes a partial
result `error`. The runner makes a non-zero exit with no failures `error`.

When a core gate needs to execute something in the repo, it runs a gate the
repo declared, through the same contract. It never runs the repo's toolchain.
Git and the cell runtime are core's own vocabulary, so running them is no
exception. `revert` and `witness` (§5.4.1) are the core gates that run a repo
gate. Each re-invokes the repo's `tests` gate with a test subset, and `witness`
first applies a mutant the spec declared.

Before a new core gate takes that exception, the cheaper question comes first.
Does a gate the repo already declares produce this data? `census` reads
`collected` and invokes nothing. `criteria` reads `collected` and the `tests`
gate's `failures[].code` as node ids, a second obligation on that gate. A core
gate that still needs to run something fits the exception's shape or moves to
the repo.

Where a gate reads as language-specific, core keeps the question and the repo
declares the tokens. `integrity` reads its suppression tokens and gate-config
paths from `policy.yaml`.

`committed` reads `git status` in the cell, which widens core's in-cell git
surface. Git is core's own vocabulary, and the gate is a pure function over
paths. The widened surface is the residual, and it is not a second exception.

Which copy of a gate the host executes is a separate decision. §5.4 takes
gates and policy from the export at `base_sha`, never from `/work` (Appendix N).

This ADR corrects two sentences that contradicted §2.1. §5.4 called `revert`
the one place core reaches into the repo's toolchain. §7's risk table said no
core gate executes repo code.

## Principles

- **12** upholds. The contract is the boundary, and no plugin layer sits behind
  it. A second implementation of anything waits for a repo that needs it.
- **13** upholds. `integrity` keeps the question in core and the tokens in
  `policy.yaml`.
- **14** departs. The two repos §1.3 names are both Python, and Appendix I
  measured an empty diff for one of them. The dissimilar third repo that C
  names as the test comes at v3. §9 gives the reason to decide first: a
  contract is cheap, and retrofitting one after core learns a language is not.
- **29** upholds. §2.1 states the exception with `revert`, and §5.4.1 places
  `witness` inside it, so the rule survives both.
- **30** upholds. F restated §2.1 and left §5.4's sentence and §7's row saying
  the opposite. This ADR corrects both in `DESIGN.md`.
- **34** upholds. The contract carries `tool`, so a gate that ran and passed
  differs from one that never ran.
- **36** upholds. A gate that breaks part-way reports `error` for the whole
  gate result, never `fail` on what it collected.
- **39** upholds. A gate that locates its tool and cannot run it names no
  `tool`, and the runner reports `error`.
- **41** upholds. Core's own gates run on artifacts core owns, and demand no
  language of a repo's image.
- **52** upholds. `census` compares collected sets and invokes nothing, which
  is the cheaper question answered.
- **54** departs. The runner requires `tool` on every `pass` and `fail`. A
  `skip` names none, so a gate that reports `skip` on its own failure reads as
  passing. One structure rule checks that `tool` came from execution. It reads
  every Python file in this repo outside `tests/`. It skips the shell `format`
  gate (backlog item 77) and every other repo's gates. Reading another repo's
  gate source needs core to know its language, which this decision refuses.
- **57** upholds. This ADR condenses §2.1, §5.4, §5.4.1, §7 and §11. Each claim
  in the Decision restates one of those sections, and nothing here widens them.

## Consequences

The orchestrator holds no parser, and each repo translates its own tools. A
repo with no analogue for a role omits the gate, and core changes nothing.

The runner holds the `tool` field on `pass` and `fail`. The
`gate-tool-must-be-executed` structure rule holds its source in this repo. The
rest is prose.

No test asserts that onboarding touches zero lines of `saffron/`. Appendix I
measured it once. §11 expects one field of the contract to be wrong for the
third repo, and it changes then.

The contract's next change is already decided, and this repo forces it. The
`tests` role will report what became of each name it was handed (backlog items
49, 50 and 51). It is not built yet.
