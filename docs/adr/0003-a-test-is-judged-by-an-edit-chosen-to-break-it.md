---
id: 3
title: "A test is judged by an edit chosen to break it, not by a mutation tool"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [A, K, L]
principles: [4, 5, 6, 15, 17, 20, 30, 34, 44, 45, 47, 48, 49, 52, 56, 57]
---

## Context

Appendix A made `coverage` advisory and `revert` blocking. Appendix K found that
the gates were necessary and nowhere near sufficient. Thirty-one passing tests
and five surviving mutants described one artifact. Tests written by the code's
author certify agreement, not correctness.

The decision is spread across §5.4, §5.4.1, §5.5, §5.5.1, §11 and the backlog,
and it changed five times.

- 2026-08-25. §5.4 rejected mutation testing on cost, because `mutmut` reruns
  the suite per mutant. §11 corrected that reason. `mutmut` does not rerun per
  mutant, and it ran inside the window
  (`docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`).
- 2026-09-02. §5.5 had argued that `revert` answered test quality for free.
  §5.5.1 withdrew that on measurement. `revert` asks whether the new tests test
  anything, not whether they test each thing. So lens #3 became test adequacy.
  Blast radius was retired. The escape Appendix L records fell in its remit.
- 2026-09-05. Nine tests passed every gate, all three lenses and a human read,
  and guarded nothing. Each was found by running a mutation. §5.4.1 added
  `witness` for that case (backlog item 69).
- 2026-09-19. The host began to run the vacuity probe each adequacy finding
  names (`SA-0109`, #375). §5.5.1 recorded it on 2026-09-21.
- 2026-09-22. The host began to apply criterion probes (`SA-0120`, #434,
  backlog item b-2750d5).

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
  the edit in its own gate-only cell and runs `witness_gate` over it. If the
  witness survives, the finding is an `adequacy` blocker.
- Lens #3, `adequacy`, reads the diff and names, per finding, a vacuity probe.
  That is the smallest edit that keeps the suite green while the behaviour
  breaks. The lens runs nothing. The host applies the probe in a gate-only cell
  and runs the repo's `tests` gate (`SA-0109`). `survived` makes the finding a
  `blocker`, and `killed` makes it a `note`.

A probe of either kind is `unproven` when no edit is named or the edit targets
a declared test path. An `unproven` probe is never applied, and the finding
keeps the severity it was filed at.

ADR 2 names only the spec's mutant among the edits core applies. The two probe
runs are host steps inside the same rule. The host invokes a gate the repo
declared, and no tool.

A spec's mutant is meant never to reach the implementer. `parse_spec` refuses a
spec whose mutant text appears in its body or claims, before a cell starts.
That refusal is a tripwire, not a boundary (backlog item 80). A probe is
different. REBUT shows a surviving probe to the implementer on purpose, so it
can answer the blocker. After REBUT a verdict session reads the diff, and no
probe runs again.

A mutation tool stays out of the gate loop for two reasons that §11 measured.
`mutmut` cannot scope below a function, and cannot run over a suite that gates
its own tree. `cosmic-ray` scopes to a diff, but lacks the string-literal
operator the one real defect needed.

Coverage is not an adequacy check. `size.py` had full statement coverage, and
its one partial branch was not the defect. A line whose removal left all its
tests green was executed by every one of them (the evidence record above).

This ADR is where the decision stands. The pull request that adds it rewrites
six `DESIGN.md` sentences that carried older forms of it. Two more remain, and
principle 30 names them.

## Principles

- **4** departs. Both withholdings live in the cell. The spec file sits in the
  worktree, so a spec's mutant is withheld from the prompt only. The criterion
  session reads files under `/work`, where the spec names every witness.
- **5** departs. A test REBUT adds to kill a surviving probe belongs to no
  criterion, so `revert` fails it. One task ended `EXHAUSTED` with a correct
  diff that way (backlog item b-4a63b7).
- **6** departs. A surviving probe is a blocker, and blocking teaches the
  cheapest satisfaction. `SA-0079` killed the named edit and left a near
  neighbour surviving. Coverage stays advisory for the same reason.
- **15** departs. The first verdict on a probe is a run of a declared gate.
  After REBUT the verdict is a session reading the diff, and item 117's fresh
  probe per round is not built.
- **17** upholds. `parse_spec` refuses a spec that discloses its own mutant
  before a cell starts.
- **20** departs. A spec in the worktree is agent-visible. `SA-0064`'s
  implementer read a mutant there (item 80). Whether a criterion session has
  read a witness there is not measured.
- **30** departs. Two sentences still say no gate applies a criterion probe:
  §5.4.1, and `CONTEXT.md`'s criterion probe entry. Item b-37924b owns both.
  The same pull request rewrote the other six, in §5.4, §5.5.1, §7, §8 and §11.
- **34** upholds. `revert` reports `skip` when its tests fail to import, and
  `witness` names every mutant that does not apply. Neither reads as green.
- **44** departs. No live task shows the host applying a criterion probe. The
  three cells of run 13 ran before #434 merged.
- **45** upholds. Mutation now reaches every claim that names a witness,
  through a criterion probe, whether or not its spec declares a mutant. It
  misses a claim with no witness, and a probe that is `unproven`.
- **47** upholds. Coverage is the proxy the adequacy question rejects.
- **48** upholds. The lens and the criterion session look for what no gate
  thought to check, and the host then turns what they name into a check.
- **49** departs. Principle 49 needs the answer hidden from the agent. A spec's
  mutant is hidden from the prompt and not from the cell, until item 80 lands.
  A surviving probe is shown at REBUT, and item 117 accepts that only if a
  fresh probe is asked for each round.
- **52** departs. Vacuity is a property of how a test and its code respond to
  perturbation, so the first verdict comes from running an edit. After REBUT
  the question returns to reading.
- **56** upholds. The 2026-08-25 measurement rejected two mutation tools for
  this gate loop, and nothing more. §11 names the constraints that would admit
  `mutmut`.
- **57** upholds. This ADR condenses five `DESIGN.md` sections, two appendices
  and six backlog records, and dates each change. It uses the glossary's three
  names, mutant, vacuity probe and criterion probe, rather than one general
  term.

## Consequences

A spec that claims a behaviour names a witness, or no probe reaches the claim.
A spec creating new code declares no mutant, because a mutant cannot pin text
the implementer has not written. Its claims still get criterion probes.

`revert` is file-level, so a file that is half test and half source reverts
whole or not at all. When the reverted tests fail to import, `revert` reports
`skip`, not green (backlog item 50). It also fails a test REBUT adds, which
b-4a63b7 records as open.

`witness` as a suite gate is advisory at `standard` and blocking at `elevated`.
A surviving probe of either kind is a blocker for REBUT, whatever the tier.
