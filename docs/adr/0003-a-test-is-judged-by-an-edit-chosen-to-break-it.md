---
id: 3
title: "A test is judged by an edit chosen to break it, not by a mutation tool"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [A, K, L]
principles: [1, 4, 5, 6, 15, 17, 20, 28, 30, 34, 44, 45, 47, 48, 49, 52, 56, 57, 61]
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
- 2026-09-02. §5.5 argued until then that `revert` answered test quality for
  free. §5.5.1 withdrew that on measurement. `revert` asks whether the new tests
  test anything, not whether they test each thing. So lens #3 became test
  adequacy. Blast radius was retired. The escape Appendix L records fell in its
  remit.
- 2026-09-05. Nine tests passed every gate, all three lenses and a human read,
  and guarded nothing. Each was found by running a mutation. §5.4.1 added
  `witness` for that case (backlog item 69).
- 2026-09-19. The host began to run the vacuity probe each adequacy finding
  names (`SA-0109`, #375). §5.5.1 recorded it on 2026-09-21.
- 2026-09-22. The host began to apply criterion probes (`SA-0120`, #434,
  backlog item b-2750d5).
- 2026-09-23. A vacuity probe killed only by a format test read as caught
  (backlog item b-19b255). Only a test the diff adds now kills one (`SA-0138`).

## Decision

Whether a test guards a behaviour is answered by running an edit chosen to
break that behaviour. No mutation-testing tool sweeps the diff. Two gates and
two host-run probes share the question, and each asks it differently.

- `revert` reverts the diff's source files, keeps its test files, and requires
  the new tests to fail. It asks whether the tests test anything.
- `witness` applies a mutant the spec declares to the head tree, and requires
  the claim's witness to fail. It asks whether that one claim is guarded.
- A criterion probe is an edit a fresh session names to make one claim false.
  The session is never told which test is the claim's witness. The host applies
  the edit in its own gate-only cell and runs the claim's witness over it, as
  the `witness` gate does. A surviving witness files an `adequacy` blocker.
- Lens #3, `adequacy`, reads the diff and names, per finding, a vacuity probe.
  That is the smallest edit that keeps the suite green while the behaviour
  breaks. The lens runs nothing. The host applies the probe in a gate-only cell
  and runs the repo's `tests` gate (`SA-0109`). Only a failure of a test the
  diff adds kills the probe (`SA-0138`). `survived` makes the finding a
  `blocker`, and `killed` makes it a `note`.

A probe of either kind is `unproven` in three cases. No edit is named, the edit
targets a declared test path, or the cell could not apply or answer it. The
first two are refused before any edit is applied. A vacuity probe has two more.
The run cannot say which tests the diff added, or no new failure names a test
the run collected. An `unproven` vacuity
probe leaves its finding at the severity the lens filed. An `unproven`
criterion probe files no finding.

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
every `DESIGN.md` and `CONTEXT.md` sentence that carried an older form of it.

## Principles

- **1** departs. A spec's mutant needs the operator to know in advance the text
  that breaks a claim. A criterion probe upholds the principle, because a fresh
  session names that edit and the operator does not.
- **4** departs. Both withholdings live in the cell. The spec file sits in the
  worktree, so a spec's mutant is withheld from the prompt only. The criterion
  session reads files under `/work`, where the spec names every witness.
- **5** departs. A test REBUT adds for a property already true at base still
  passes once the source is reverted. No `preserves` criterion declares it, so
  `revert` fails it. One task ended `EXHAUSTED` with a correct diff that way
  (backlog item b-4a63b7).
- **6** departs. A surviving probe is a blocker, and blocking teaches the
  cheapest satisfaction. `SA-0079` killed the named edit and left a near
  neighbour surviving. Coverage stays advisory for the same reason.
- **15** departs. The first verdict on a probe is a run of a declared gate.
  After REBUT the verdict is a session reading the diff, and item 117's fresh
  probe per round is not built.
- **17** upholds. `parse_spec` refuses a spec that discloses its own mutant
  before a cell starts.
- **20** departs. A spec in the worktree is agent-visible. `SA-0064`'s
  implementer read a mutant there (item 80). No measurement shows whether a
  criterion session reads a witness there.
- **28** departs. The anchor rule was written for lens findings, and a
  criterion-probe survivor now passes through it. One that does not anchor
  stays in the record and never reaches REBUT. A `preserves` claim's probe is
  the likeliest to edit code outside the diff. The ledger's drop rate still
  counts a host-filed survivor against the lens (backlog item b-b431c1).
- **30** upholds. The pull request rewrites every sentence that still stated
  an older form, in §5.4, §5.4.1, §5.5.1, §7, §11 and `CONTEXT.md`. It deletes
  §8's claim that `revert` replaced a lens.
- **34** departs. `witness` names every mutant that does not apply. `revert`
  reports `skip` when its tests fail to import, and the PR body renders that
  skip as a gate the repo does not declare. ADR 2 records that a `skip` reads
  as passing. Backlog item 50 owns the case.
- **44** departs. No live task shows the host applying a criterion probe. Run
  13's cells ran before #434 merged.
- **45** upholds. Mutation now reaches every claim that names a witness,
  through a criterion probe, whether or not its spec declares a mutant. It
  misses a claim with no witness, a probe that ends `unproven` or `error`, and
  a survivor that does not anchor.
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
- **57** upholds. This ADR condenses five `DESIGN.md` sections, three
  appendices and seven backlog records, and dates each change. It uses the
  glossary's three names, mutant, vacuity probe and criterion probe, rather
  than one general term.
- **61** departs. The criterion probe's tests run it on fixtures only, so they
  verify the probe and not a task. Principle 44's live run is what is missing.

## Consequences

A spec that claims a behaviour names a witness, or no probe reaches the claim.
A spec creating new code declares no mutant, because a mutant cannot pin text
the implementer is yet to write. Its claims still get criterion probes.

`revert` is file-level (§5.4). When the reverted tests fail to import, `revert`
reports `skip`, and the PR body misreports the reason (backlog item 50). It
also fails a test REBUT adds for a property already true at base, which item
b-4a63b7 records as open.

`witness` as a suite gate is advisory at `standard` and blocking at `elevated`.
A surviving probe of either kind is a blocker for REBUT, whatever the tier, once
its finding anchors to the diff. A criterion-probe survivor that does not anchor
stays in the record and never reaches REBUT.
