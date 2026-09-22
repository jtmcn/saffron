---
id: 2
title: "Core invokes declared gates, never tools"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [C, F, H, I, M]
principles: [12, 13, 14, 29, 34, 36, 39, 41, 44, 52, 54, 57]
---

## Context

Appendix C made Saffron repo-agnostic with one structural change, the gate
contract. A gate is an executable that emits one JSON object and translates its
own tool's output. So the repair loop, the baseline subtraction and review read
`failures[]`, and never a tool's output.

The decision is spread across §2.1, §5.4, §5.4.1, §11 and five appendices.
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
stdout. The object carries `gate`, `status`, `tool`, `failures` and `summary`,
and optionally `collected`. `status` is one of `pass`, `fail`, `skip` and
`error`. The gate obtains `tool` by executing its tool. A partial result is
`error`, and so is a non-zero exit with no failures.

When core needs to run anything, it runs a gate the repo declared, through the
same contract. It never runs a tool. `revert` and `witness` (§5.4.1) are the
core gates that do this. Each re-invokes the repo's `tests` gate with a test
subset, and `witness` first applies a mutant the spec declared.

Before a new core gate takes that exception, the cheaper question comes first.
Does a gate the repo already declares produce this data? `census` and
`criteria` read `collected` and invoke nothing. A core gate that still needs to
run something fits the exception's shape or moves to the repo.

Where a check reads as language-specific, core keeps the question and the repo
declares the tokens. `integrity` reads its suppression tokens and gate-config
paths from `policy.yaml`.

`committed` reads `git status` in the cell, which widens core's in-cell git
surface. It stays inside the rule, because the check is a pure function over
paths. It is a stated residual, not a second exception.

Which copy of a gate the host executes is a separate decision. §5.4 takes
gates and policy from the export at `base_sha`, never from `/work` (Appendix N).

## Principles

- **12** upholds. The contract is the boundary, and no plugin layer sits behind
  it. A second implementation of anything waits for a repo that needs it.
- **13** upholds. `integrity` keeps the question in core and the tokens in
  `policy.yaml`.
- **14** departs. The two repos §1.3 names are both Python, and Appendix I
  measured an empty diff for one of them. §9 orders the tests. v2's empty diff
  for a second repo comes first, and the dissimilar third repo comes at v3.
  "Do not build v3 first" is why the decision stands before that test runs.
- **29** upholds. §2.1 and §5.4.1 state both uses of the exception, `revert`
  and `witness`, so the rule survives them.
- **34** upholds. The contract carries `tool`, so a gate that ran and passed
  differs from one that never ran.
- **36** upholds. A gate that breaks part-way reports `error` for the whole
  run, never `fail` on what it collected.
- **39** upholds. The contract requires `tool` to come from running the tool,
  not from locating it.
- **41** upholds. Core's own checks run on artifacts core owns, and demand no
  language of a repo's image.
- **44** upholds. The cost of a gate is stated below as measured on this tree,
  not as C's estimate.
- **52** upholds. `census` compares collected sets and invokes nothing, which
  is the cheaper question answered.
- **54** departs. A structure rule holds the `tool` invariant for Python gates
  only. `.saffron/gates/format` is shell, and no rule reads it (backlog item
  77).
- **57** upholds. This ADR condenses §2.1, §5.4, §5.4.1 and §11. Each claim in
  the Decision is one of those sections restated, and nothing here widens them.

## Consequences

The orchestrator holds no parser, and each repo translates its own tools.
Appendix C estimated a gate at about 20 lines of shell. On this tree
`.saffron/gates/format` is 25 lines of shell. `lint.py` is 56 lines of Python,
`typecheck.py` 113 and `tests.py` 123. A repo with no analogue for a role omits
the gate, and core changes nothing.

No test asserts that onboarding touches zero lines of `saffron/`. Appendix I
measured it once. §11 expects one field of the contract to be wrong for the
third repo, and it changes then.
