---
id: 3
title: "A test is judged by an edit chosen to break it, not by a mutation tool"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [K, L]
principles: [4, 6, 15, 17, 20, 30, 34, 45, 47, 48, 49, 52, 56, 57]
---

## Context

Appendix K found that the gates were necessary and nowhere near sufficient.
Thirty-one passing tests and five surviving mutants described one artifact.
Tests written by the code's author certify agreement, not correctness.

The decision is spread across §5.4, §5.4.1, §5.5, §5.5.1, §11 and the backlog,
and it changed five times.

- 2026-08-25. §5.4 rejected mutation testing on cost, because `mutmut` reruns
  the suite per mutant. §11 corrected that reason. `mutmut` does not rerun per
  mutant, and it ran inside the window
  (`docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`).
- 2026-09-02. §5.5 had argued that `revert` answered test quality for free.
  §5.5.1 withdrew that on measurement. `revert` asks whether the new tests test
  anything, not whether they test each thing. So lens #3 became test adequacy.
  Blast radius, which would have caught the escape Appendix L records, was
  retired.
- 2026-09-05. Nine tests passed every gate, all three lenses and a human read,
  and guarded nothing. Each was found by running a mutation. §5.4.1 added
  `witness` for that case (backlog item 69).
- 2026-09-21. The host began to run the vacuity probe each adequacy finding
  names (`SA-0109`, §5.5.1).
- 2026-09-22. The host began to apply criterion probes (`SA-0120`, backlog item
  b-2750d5). `DESIGN.md` and `CONTEXT.md` still say no gate applies one
  (backlog item b-37924b).

## Decision

Whether a test guards a behaviour is answered by running an edit chosen to
break that behaviour. No mutation-testing tool sweeps the diff. Four checks
share the question, and each asks it differently.

- `revert` reverts the diff's source files, keeps its test files, and requires
  the new tests to fail. It asks whether the tests test anything.
- `witness` applies a mutant the spec declares to the head tree, and requires
  the claim's witness to fail. It asks whether that one claim is guarded.
- A criterion probe is an edit a fresh session names to make one claim false.
  The session is never told which test is the claim's witness. The host applies
  the edit in a gate-only cell through `witness`. If the witness survives, the
  finding is an `adequacy` blocker.
- Lens #3, `adequacy`, reads the diff and names, per finding, a vacuity probe.
  That is the smallest edit that keeps the suite green while the behaviour
  breaks. The lens runs nothing. The host applies the probe in a gate-only cell
  and runs the repo's `tests` gate (`SA-0109`). `survived` makes the finding a
  `blocker`, and `killed` makes it a `note`. A probe that edits a declared test
  path is `unproven` and never applied, and `unproven` keeps the lens's
  severity.

Each run sits inside ADR 2's rule. The host invokes a gate the repo declared,
and no tool.

A spec's mutant is meant never to reach the implementer. `parse_spec` refuses a
spec whose mutant text appears in its body or claims, before a cell starts.
That refusal is a tripwire, not a boundary (backlog item 80). A probe is
different. REBUT shows a surviving probe to the implementer on purpose, so it
can answer the blocker.

A mutation tool stays out of the gate loop for two reasons that §11 measured.
`mutmut` cannot scope below a function, and cannot run over a suite that gates
its own tree. `cosmic-ray` scopes to a diff, but lacks the string-literal
operator the one real defect needed.

Coverage is not an adequacy check. `size.py` had full statement coverage, and
its one partial branch was not the defect. A line whose removal left all its
tests green was executed by every one of them (the evidence record above).

This ADR is where the decision stands. Six sentences in `DESIGN.md` and
`CONTEXT.md` still carry older forms of it, and they are named under
principle 30.

## Principles

- **4** departs. The spec file sits in the worktree the cell works in, so a
  spec's mutant is withheld from the prompt only. Item 80 decided to move
  mutants to a ref the cell never fetches, and that is not built.
- **6** upholds. Coverage stays out of adequacy, because a test that executes
  new lines without asserting on them is the cheapest way to satisfy it.
- **15** upholds. A named probe is a claim, and the host's run of a declared
  gate decides it.
- **17** upholds. `parse_spec` refuses a spec that discloses its own mutant
  before a cell starts.
- **20** departs. A mutant in the worktree copy of the spec is agent-visible.
  `SA-0064`'s implementer read one there (item 80).
- **30** departs. Six sentences keep an older decision. Item b-37924b owns two:
  `DESIGN.md` §5.4.1 and `CONTEXT.md`'s criterion probe entry say no gate
  applies a criterion probe. No item owns the other four. §5.4 says `revert`
  answers lens #3's question, and gives the withdrawn cost reason. §8 says
  `revert` replaced a whole lens. §11's table names `revert` alone against
  mutation testing.
- **34** upholds. `revert` reports `skip` when its tests fail to import, and
  `witness` names every mutant that does not apply. Neither reads as green.
- **45** upholds. Mutation now reaches every claim that names
  a witness, through a criterion probe, whether or not its spec declares a
  mutant. It misses a claim with no witness, and a probe the session did not
  name or the host could not prove.
- **47** upholds. Coverage is the proxy the adequacy question rejects.
- **48** upholds. The lens and the criterion session look for what no gate
  thought to check, and the host then turns what they name into a check.
- **49** departs. Principle 49 needs the answer hidden from the agent. A spec's
  mutant is hidden from the prompt and not from the cell, until item 80 lands.
  A surviving probe is shown at REBUT. Item 117 accepts that, because a fresh
  probe can be asked for each round. Its cost is measured: `SA-0079` killed
  the named edit and left a near neighbour surviving.
- **52** upholds. Vacuity is a property of how a test and its code respond to
  perturbation, not of the test's text. So the question is answered by running
  an edit, not by a better reading.
- **56** upholds. The 2026-08-25 measurement rejected two mutation tools for
  this gate loop, and nothing more. §11 names the constraints that would admit
  `mutmut`.
- **57** upholds. This ADR condenses §5.4, §5.4.1, §5.5, §5.5.1, §11 and two
  backlog records, and dates each change. It uses the glossary's three names,
  mutant, vacuity probe and criterion probe, rather than one general term.

## Consequences

A spec that claims a behaviour names a witness, or no probe reaches the claim.
A spec creating new code declares no mutant, because a mutant cannot pin text
the implementer has not written. Its claims still get criterion probes.

`revert` is file-level, so a file that is half test and half source reverts
whole or not at all. When the reverted tests fail to import, `revert` reports
`skip`, not green (backlog item 50).

`witness` is advisory at `standard` and blocking at `elevated`. A surviving
probe of either kind is a blocker for REBUT, whatever the tier.
