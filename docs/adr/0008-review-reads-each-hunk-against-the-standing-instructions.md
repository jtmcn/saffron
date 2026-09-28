---
id: 8
title: "REVIEW reads each hunk against the standing instructions, in a fourth lens"
status: accepted
date: 2026-09-28
supersedes: []
superseded_by: []
appendices: [L, R]
principles: [9, 15, 17, 29, 30, 41, 43, 48, 50, 51, 59]
---

## Context

ADR 4 names three in-cell lenses: correctness, contract and adequacy. None of
them reads a hunk against the conventions a repo's `CLAUDE.md` states. A cell
reads those conventions at `base_sha` as its standing instructions (§5.5), and
nothing checks the diff against them.

The spec loop's run 20 (2026-09-28) put a Standards seat beside the cells. It
read every pull request of the run by hand. It found such a defect on every
one, after all three lenses passed the diff (backlog item b-abeb74):

- A comment or docstring that contradicts its code, on #565 and #566.
- A constant restated in place of the one the repo defines, on #559 and #560.
- A citation to a section that does not say what the text claims, on #562.

No gate sees these. `prose` and `terms` judge the form of a sentence
(Appendix R). Neither judges whether the sentence is true of the code beside
it.

A Standards lens already exists, in a stack batch's end review (ADR 7). It
judges each layer against the standing instructions the host read at the
task's base. It runs once per batch, after the stack is built, and its
findings feed a follow-up spec. A defect it finds is fixed a whole generation
late, and an attended cell never meets it.

The operator set a direction on 2026-09-28. A cell's own review leaves no
seat anything to find before the next cell starts. The Standards seat
is one of the seats to retire.

## Decision

REVIEW runs four lenses: correctness, contract, adequacy and conventions.
`conventions` is a declared lens under ADR 4 in every respect. It is a fresh,
read-only session in a critic cell. The host starts it on every reviewed diff,
at every risk tier. Its findings anchor, route to REBUT and take verdicts as
the other lenses' do.

Its remit is the hunk against the standing instructions the host read at
`base_sha`. It never reads a standard from the worktree, since the
implementer could have rewritten it. It asks four questions of every hunk:

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

- **9** upholds. Any one blocker still routes to REBUT, and a fourth lens adds
  no vote.
- **15** upholds. A conventions finding counts only once the host anchors it.
- **17** departs. Each lens runs on the floored per-lens cap, never
  decremented between lenses, and REVIEW is not bounded on spend. A fourth
  lens raises REVIEW's worst-case overrun from three remainders to four
  (§5.5.1).
- **29** upholds. ADR 4's three-lens sentence has this exception, and ADR 4
  points here.
- **30** departs. §5.5 lists three lenses, and §5.5.1 counts three
  remainders. The spec that builds the lens edits both in its own pull
  request.
- **41** upholds. The prompt names no repo's language or tools. It reads the
  standards a repo declares at `base_sha`, and none when it declares none.
- **43** upholds. The standing instructions are read at `base_sha`, never
  from the worktree the implementer wrote.
- **48** upholds. The lens covers what `prose`, `terms` and `structure`
  cannot see.
- **50** upholds. The seat stays until a measured pass shows the lens finds
  what the seat found.
- **51** departs. The conventions and contract lenses can file one finding
  on a docstring near the edge above. Appendix L measured such overlap. Two
  filings are a fact about the prompts, never corroboration.
- **59** upholds. The lens judges no sentence's form. That stays with `prose`,
  which limits growth and exempts no file.

## Consequences

Each reviewed diff costs one more lens session. The spec that builds the lens
states that cost against run 20's cells.

The change ships with a measured pass. `harness/lens_scoring.py` scores
REVIEW before and after against a fixture that declares run 20's Standards
findings. The seat leaves the loop only once that pass shows the lens
raising them.

Every recorded run in the corpus holds three lenses. `calibrate` scores each
run against the lenses that run carried, so a fourth lens leaves the
published passes reproducible.

Inside a stack batch, a layer's diff meets two such readings: the in-cell
`conventions` lens, then the end review's Standards lens. The end review's
prompt lists the in-cell findings as already raised, so it reads for what
the cell's own lens missed.
