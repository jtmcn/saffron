---
id: b-2750d5
title: No cell mutates the line that satisfies each criterion, so a witness hole ships unless a person probes it
status: partial
tier: 1
filed: 2026-09-19
specs: [SA-0113]
prs: [403]
commits: []
cites: [§5.4, §5.5.1]
related: [117, 80, 79, b-f2a9d1, 97, b-0c1d69]
---

## Problem

Found in the spec loop's run 8, 2026-09-19. The loop's delegate makes this
check by hand after every cell, and it found a hole in all five pull requests.

`witness` judges only the mutants a spec declares. The adequacy lens names a
probe when it thinks of one, and `SA-0109` (#358) makes the host run those.
Nothing mutates the line that satisfies each acceptance criterion and runs that
criterion's witness. The Spec seat in the loop's review does exactly that, and
each probe below survived every test in the cell's diff:

- #351 (`SA-0101`): the logged spend was never compared with the returned one,
  and a reported `resets_at` of `0` had no render test. The lenses raised the
  `bool` and `None` cases as a concern and a note.
- #353 (`SA-0106`): a start line emitted after the runner call passed, and so
  did a rescan whose result was dropped. Three lenses were clean with no
  findings.
- #355 (`SA-0107`): plan-only and diff-only tampering were not separated, and a
  missing plan had no witness.
- #360 (`SA-0102`): the attempt witness passed a rebuttal set borrowing attempt
  2's gates, a skip carrying a count, and a passing gate without its zero.
- #366 (`SA-0108`): the pull request came from the caller, not the ledger, and
  the break line's task id had no witness.

Each hole was fixed in a review commit: `13f3dfa`, `9a8e7c4`, `5bce64a`,
`1be044a` and `5b838d4`.

## Done looks like

After GATE is green, a host-side step runs in a Gate-only cell. For each
criterion it mutates the lines the implementation rests on, then runs that
criterion's witness. A mutant that survives is a blocker finding for REBUT,
like an adequacy probe that survives under `SA-0109`. Which line to mutate
comes from a fresh session asked per criterion, never from the implementer.
The spec loop's Spec seat then checks this step's output in place of probing
by hand.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353). Ranked first in
  `docs/evidence/2026-09-19-spec-loop-skill-feedback-run-8.md`.
- 2026-09-19: `SA-0109` shipped its half by #375. The host now runs the
  adequacy lens's own probe and lets the verdict decide the finding. The item
  stays open for the other half: nothing yet mutates the line behind each
  criterion. Run 9 showed why both are needed. On #375 the lens's own probe
  survived, and its concern was a real hole. On #377 the lens named a probe the
  host could not apply, which is item b-98dc4d. The Spec seat's per-criterion
  probing found four more witness holes across the two pull requests.
- 2026-09-20: split in two, because the whole of "Done looks like" estimates
  past the blocking `size` ceiling for one cell. `SA-0113` is the parent and
  authors the edit: one fresh session per acceptance claim, in the critic
  cell, with the witness withheld from it, recorded in
  `criterion-probes.json`. The child applies each edit in a Gate-only cell,
  runs that criterion's witness over it, and turns a surviving edit into a
  blocker for REBUT. `b-0c1d69` holds the glossary entry and the `DESIGN.md`
  §5.4.1 paragraph that the parent's term needs.
- 2026-09-21: `SA-0113` ran in the spec loop's run 11 and reached
  `READY_FOR_REVIEW` at $12.70 (#403). Review fixed four witness holes and one
  prompt that told its session it could not see what its diff shows it.
- 2026-09-21: #403 merged, and `SA-0113` retires to `done/`. `partial`, because
  the spec loop's run 12 Spec seat still found five witness holes in #418 after
  the in-cell criterion probes ran.
