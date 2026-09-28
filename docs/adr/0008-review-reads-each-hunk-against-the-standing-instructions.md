---
id: 8
title: "REVIEW reads each hunk against the standing instructions, in a fourth lens"
status: accepted
date: 2026-09-28
supersedes: []
superseded_by: []
appendices: [A, F, K, L, R, T]
principles: [4, 6, 9, 15, 17, 18, 28, 29, 30, 34, 41, 43, 47, 50, 51, 61]
---

## Context

ADR 4 named three in-cell lenses: correctness, contract and adequacy. Every
lens is shown the repo's `CLAUDE.md` as read at `base_sha` (§5.3). None of the
three is asked to judge the diff against it.

The spec loop runs a Standards seat on each pull request. It is a subagent
outside the cell that reads the diff against the repo's conventions. Run 20
(2026-09-28) had eight pull requests. The seat found hunk defects on five,
each after all three lenses passed the diff. The sources are backlog item
b-abeb74 and `docs/evidence/2026-09-28-spec-loop-skill-feedback-run-20.md`.

- A comment or docstring that contradicts its code, on #565 and #566.
- A constant restated in place of the one the repo defines, on #559 and #560.
- A citation to a section that does not say what the text claims, on #562.

No gate sees these. `prose` and `terms` judge the form of a sentence
(Appendix R). Neither judges whether the sentence is true of the code beside
it. The first defect above came from `prose` itself. A repair turn split a
sentence to pass the gate, and the new sentence misstated its constant
(b-ad1285).

A Standards lens already exists, in a stack batch's end review (ADR 7). It
runs once per batch, after the stack is built, and its findings feed a
follow-up spec. A defect it finds is fixed a whole generation late, and an
attended cell never meets it.

The operator set a direction on 2026-09-28. A cell's own review leaves no
seat anything to find before the next cell starts.

## Decision

This ADR amends ADR 4's list of lenses from three to four, and ADR 4 names
this ADR. REVIEW runs correctness, contract, adequacy and conventions.

`conventions` is a declared lens under ADR 4 in every respect. It is a fresh,
read-only session in a critic cell. The host starts it on every reviewed diff,
at every risk tier. Its findings anchor, route to REBUT and take verdicts as
the other lenses' do.

Its remit is the hunk against the standing instructions its prompt carries,
which the host read at `base_sha`. It asks four questions of every hunk:

- Does each term carry the meaning the standing instructions give it?
- Does the hunk hold to each invariant and convention they state?
- Is a type, constant or helper the repo already defines imported, not
  restated?
- Does each comment, docstring and citation say what the code or the cited
  text says?

The last question needs no standing instructions. A repo with no `CLAUDE.md`
still gets it, and the prompt says the repo declares none.

Format, lint, types, structure and prose form stay with their gates. The lens
reports only what a gate cannot see.

A docstring that misstates a public interface's documented contract stays
with `contract`. A comment, docstring or citation that misstates its own code,
or the section it cites, is `conventions`. Each lens prompt names that edge.

The end review's Standards lens stays as ADR 7 sets it. The two share a remit
and read different things. The in-cell lens reads one task's diff before its
pull request opens. The end review reads a finished layer inside its stack.

The in-cell lens is not named `standards`, because the end review's lens
holds that key. The ledger's findings rows carry no column naming the review
that filed them. Two readers tell the two apart by `review.LENSES` alone, so
the two lens sets share no key.

## Options considered

- **Keep the Standards seat.** Every loop run pays a person's review of every
  pull request, and the run cannot finish unattended.
- **Widen the correctness lens.** Its remit is the data a change computes.
  Conventions and citations would crowd it, and a lens with two remits drops
  the one it reads for second.
- **Rely on the end review.** It runs only in a stack batch, and only after
  every cell. A defect it finds costs a follow-up spec and a second cell.
- **Gate it.** A comment that contradicts its code is a reading question. No
  pattern holds it, and `prose` shows how far a pattern gets.
- **A fourth lens (chosen).** One more session per reviewed diff, and each
  defect is found in the cell that made it, before REBUT.

## Principles

- **4** upholds. The lens runs outside the implementer's container, as ADR 4's
  lenses do.
- **18** departs. The lens emits its block in the turn that does the work,
  as ADR 4's lenses do.
- **34** upholds. A conventions lens that errors stops the task at
  `REVIEWING`, so an absent review never reads as a clean one.
- **6** upholds. A repair turn that rewrites a comment to pass `prose` now
  meets a reader that asks whether the comment is still true.
- **9** upholds. Any one blocker still routes to REBUT, and a fourth lens adds
  no vote.
- **15** upholds. A conventions finding counts only once the host anchors it.
- **17** departs. Each lens runs on the floored per-lens cap, never
  decremented between lenses, and REVIEW is not bounded on spend. A fourth
  lens raises REVIEW's worst-case overrun from three remainders to four
  (§5.5.1).
- **28** upholds. The end review and REVIEW write one findings table, and two
  readers tell them apart by lens name alone. The new key is chosen so that
  test still separates them.
- **29** upholds. The amendment is stated in the Decision, and ADR 4's own
  text names this ADR.
- **30** departs. §5.5, §5.5.1, §7's cost row and `CONTEXT.md`'s Lens entry
  now count four lenses. §5.3 still says "the three review lenses", in a
  sentence the `prose` ratchet holds as written. `CONTEXT.md` and §5.5 still
  call the lenses disjoint, which b-ac97c0 owns.
- **41** upholds. The prompt names no repo's language or tools. It reads the
  standards a repo declares at `base_sha`, and none when it declares none.
- **43** departs. The prompt carries the standing instructions read at
  `base_sha`. The lens can still Read the head's `CLAUDE.md`, which a patch can
  edit, and it reads any cited text at head. The fourth question depends on
  that head copy.
- **47** departs. The prompt's four questions were written from run 20's
  defects, and the first measured pass scores the lens on those same defects.
  A prompt tuned to its grader passes in exactly that direction.
- **61** departs. That pass shows the prompt can raise run 20's defects. It
  does not show the lens finds defects nobody wrote into it.
- **50** departs. The Standards seat is a reviewer outside the critic, and this
  ADR moves toward retiring it. The seat and the lens fail differently. Once
  the seat leaves, the operator is the one reviewer outside the critic.
- **51** departs. The conventions and contract lenses can file one finding on
  a docstring near the edge above. Appendix L measured such overlap. Two
  filings are a fact about the prompts, never corroboration.

## Consequences

Each reviewed diff costs one more lens session. The spec that builds the lens
states that cost against run 20's cells.

The change ships with a measured pass. `harness/lens_scoring.py` scores
REVIEW before and after against a fixture that declares run 20's Standards
findings. The seat stays in the loop after that pass. It leaves only once live
runs show it finding nothing in a hunk the lens missed.

Every recorded run in the corpus holds three lenses. Once `SA-0189` lands,
`calibrate` scores each run against the lenses that run carried, so a fourth
lens leaves the published passes reproducible.

Inside a stack batch, a layer's diff meets two such readings: the in-cell
`conventions` lens, then the end review's Standards lens. The end review's
prompt lists the in-cell findings as already raised, so it reads for what
the cell's own lens missed.
