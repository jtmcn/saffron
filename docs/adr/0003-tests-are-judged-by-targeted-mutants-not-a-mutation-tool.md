---
id: 3
title: "Tests are judged by targeted mutants, not a mutation tool"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [K, L]
principles: [4, 6, 15, 20, 30, 34, 45, 47, 48, 49, 52, 56, 57]
---

## Context

Appendix K found that the gates were necessary and nowhere near sufficient.
Thirty-one passing tests and five surviving mutants described one artifact.
Tests written by the code's author certify agreement, not correctness.

The decision is spread across §5.4, §5.4.1, §5.5, §5.5.1 and §11, and it
changed three times.

§5.4 rejected mutation testing on cost, because `mutmut` reruns the suite per
mutant. §11 corrected that reason on 2026-08-25. `mutmut` does not rerun per
mutant, and it ran inside the window
(`docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`).

Until 2026-09-02, §5.5 argued that `revert` answered test quality for free, so
no lens needed to. §5.5.1 withdrew that on measurement. `revert` asks whether
the new tests test anything. It does not ask whether they test each thing. So
lens #3 became test adequacy. Blast radius, which would have caught the escape
Appendix L records, was retired.

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
  a `note`. An edit to a declared test path is `unproven` and never applied,
  and `unproven` keeps the severity the lens filed.

The probe run sits inside ADR 2's rule. The host invokes a gate the repo
declared, and no tool.

A mutant is meant never to reach the implementer. The spec author declares it,
and a lens names it from a fresh session. `parse_spec` refuses a spec whose
mutant text appears in its body or claims. That refusal is a tripwire, not a
boundary (backlog item 80).

A mutation tool stays out of the gate loop for two reasons that §11 measured.
`mutmut` cannot scope below a function, and cannot run over a suite that gates
its own tree. `cosmic-ray` scopes to a diff, but lacks the string-literal
operator the one real defect needed.

Coverage is not an adequacy check. `size.py` had full statement and branch
coverage, and a line whose removal left all its tests green.

This ADR is where the decision stands. §5.4 and §11 keep three sentences it
replaces, and they are named under principle 30.

## Principles

- **4** departs. The spec file sits in the worktree the cell works in, so the
  mutant is withheld from the prompt only. Item 80 decided to move mutants to
  a ref the cell never fetches, and that is not built.
- **6** upholds. Coverage stays out of adequacy, because a test that executes
  new lines without asserting on them is the cheapest way to satisfy it.
- **15** upholds. The lens's named edit is a claim, and the host's run of the
  `tests` gate decides it.
- **20** departs. A mutant in the worktree copy of the spec is agent-visible.
  `SA-0064`'s implementer read one there (item 80).
- **30** departs. Three sentences keep the older decision. §5.4 says `revert`
  answers lens #3's question, and gives the withdrawn cost reason. §11's table
  still names `revert` alone against mutation testing. They stay unedited
  because `DESIGN.md` is `protected`, and this ADR is the record where the
  decision stands.
- **34** upholds. `revert` reports `skip` when its tests fail to import, and
  `witness` names every mutant that does not apply. Neither reads as green.
- **45** departs. Mutation is how this decision tells agreement from
  correctness, but only where a mutant exists. A spec that declares none gets
  `skip` from `witness`, and seven of eight specs in stack #251 declared none.
- **47** upholds. Coverage is the proxy the adequacy question rejects.
- **48** upholds. The lens looks for what no gate thought to check, and the
  host then turns its finding into a check.
- **49** departs. Principle 49 needs the answer hidden from the agent. The
  spec's mutant is hidden from the prompt and not from the cell, until item 80
  lands.
- **52** upholds. Vacuity is a property of how a test and its code respond to
  perturbation, not of the test's text. So the question is answered by running
  a mutant, not by a better reading.
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
