---
id: 3
title: "Tests are judged by targeted mutants, not a mutation tool"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [K, L]
principles: [6, 30, 45, 47, 48, 49, 56, 57]
---

## Context

Appendix K found that the gates were necessary and nowhere near sufficient.
Thirty-one passing tests and five surviving mutants described one artifact.
Tests written by the code's author certify agreement, not correctness.

The decision is spread across §5.4, §5.4.1, §5.5, §5.5.1 and §11. It changed
twice.

Until 2026-09-02, §5.5 argued that `revert` answered test quality for free, so
no lens needed to. §5.5.1 withdrew that on measurement. `revert` asks whether
the new tests test anything. It does not ask whether they test each thing. So
lens #3 became test adequacy, and blast radius, which Appendix L argued for,
was retired.

§5.4 rejected mutation testing on cost, because `mutmut` reruns the suite per
mutant. §11 corrected that reason on 2026-08-25. `mutmut` does not rerun per
mutant, and it ran inside the window
(`docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`).

On 2026-09-05 nine tests passed every gate, all three lenses and a human read,
and guarded nothing. Each was found by running a mutation. §5.4.1 added
`witness` for that case (backlog item 69).

## Decision

Whether a test guards a behaviour is answered by running a mutant chosen for
that behaviour. No mutation-testing tool sweeps the diff. Three checks share
the question, and each asks it differently.

- `revert` reverts the diff's source files, keeps its test files, and requires
  the new tests to fail. It asks whether the tests test anything.
- `witness` applies a mutant the spec declares to the head tree, and requires
  the claim's witness to fail. It asks whether that one claim is guarded.
- Lens #3, `adequacy`, reads the diff and names, per finding, the smallest edit
  that keeps the suite green while the behaviour breaks. It runs nothing. The
  host applies that edit in a gate-only cell and runs the repo's `tests` gate
  (`SA-0109`). `survived` makes the finding a `blocker`, and `killed` makes it
  a `note`.

A mutant never comes from the implementer. The spec author declares it, and
`parse_spec` refuses a spec whose mutant text appears in its body or claims. A
lens names it from a fresh session.

A mutation tool stays out of the gate loop for two reasons that §11 measured.
`mutmut` cannot scope below a function, and cannot run over a suite that gates
its own tree. `cosmic-ray` scopes to a diff, but lacks the string-literal
operator the one real defect needed.

Coverage is not an adequacy check. `size.py` had full statement and branch
coverage, and a line whose removal left all its tests green.

## Principles

- **6** upholds. Coverage stays out of adequacy, because a test that executes
  new lines without asserting on them is the cheapest way to satisfy it.
- **30** departs. §5.4 still gives the withdrawn cost reason for rejecting
  mutation testing. §11 corrects it beside the other half, and §5.4 was not
  edited.
- **45** upholds. Mutation is how this decision tells agreement from
  correctness, but applied per claim or per finding.
- **47** upholds. Coverage is the proxy the adequacy question rejects.
- **48** upholds. The lens looks for what no gate thought to check, and the
  host then turns its finding into a check.
- **49** upholds. The implementer never sees a mutant before the check runs.
- **56** upholds. The 2026-08-25 measurement rejected two mutation tools for
  this gate loop, and nothing more. §11 names the constraints that would admit
  `mutmut`.
- **57** upholds. This ADR condenses §5.4, §5.4.1, §5.5, §5.5.1 and §11, and
  states each amendment where it happened.

## Consequences

A spec that claims a behaviour says what would falsify it, or its claim gets no
`witness` verdict. A spec creating new code declares a witness and no mutant,
because the mutant cannot pin text the implementer has not written. It accepts
a `skip`.

`revert` is file-level, so a file that is half test and half source reverts
whole or not at all. When the reverted tests fail to import, `revert` reports
`skip`, not green (backlog item 50).

`witness` is advisory at `standard` and blocking at `elevated`. A criterion
probe, the edit a fresh session names per claim (`SA-0113`), is named and not
yet applied by any gate (backlog item b-2750d5).
