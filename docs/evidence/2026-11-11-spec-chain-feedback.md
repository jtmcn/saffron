# Spec chain feedback, 2026-11-11

## SA-0369 (b-f582ee), after spec loop run 61

One writer drafted it in 24 minutes. It asked nothing back, but it named
two runtime facts it could not settle from a read-only brief. The delegate
measured both on `apple/container` 1.6.1 before the first review. One of
them broke the draft's design.

**Before review 1: a measurement, then a revision.** While a container that
holds a volume exists, a second container cannot attach it: "The storage
device attachment is invalid." The draft read the dead cell's volume while
its container still existed. Every real rescue would have failed, and every
stubbed witness would have passed. The revision removes the cell's
container first. A forced removal kept every commit, and `git fsck` exited
0. `rm -f` of a missing name exits 1.

**Review 1: 0 blockers, 3 concerns, 4 notes.**

- The read-only mount was measured as `-v vol:/work:ro`. `Mount.to_flag`
  builds `--mount type=volume,...,readonly`. Pre-flight 10 missed it: the
  delegate ran the arrangement, but not in the spelling the code sends. The
  exact form was measured next, and it reads and refuses writes.
- The export network's name was unpinned, so it could collide with the
  cell's own networks. Pre-flight 6 missed it, since the witness calls the
  export alone and sees no live network.
- "Every read fails" had no single meaning. Base reads the subjects in
  their own `try`, then the patch. Pre-flight 1 missed it: the claim
  quantified over four reads, and base never reaches two of them.

**Review 2: 0 blockers, 2 concerns, 4 notes.** The delegate applied both
concerns by hand.

- When the volume could not answer, the revision dropped subjects the
  cell had already read. Base keeps them. Pre-flight 2 missed it, because
  round 1's fix created it.
- The spec said "the cell" for the cell's container. `CONTEXT.md` defines a
  cell as the container plus its volumes, and the volume is the part kept.
  Pre-flight 8 missed it.

Notes kept for the record: the rescue of a cell after "no PID data from
sync pipe" is still unmeasured. `DESIGN.md`'s list of subnet pool claimers
omits the export. A leftover export network is reported to nobody, as in
PACKAGE's re-verify.

## Checks to build (SA-0369)

24. A runtime fact the design rests on is measured before review, in the
    exact spelling the code will send. The writer names such facts, and the
    delegate measures them.
25. Pre-flight 1 should read each "every" over reads that base runs in
    sequence. A read base never reaches cannot fail.
26. A fix applied after a review gets pre-flight 2 again, against the
    behaviour base gives the same input.

## SA-0371 (b-7c88f8), after spec loop run 62

The item came from run 62. `SA-0369`'s gate-only cell stopped after its
26th criterion probe. Every later probe and all 37 wrong versions were
filed `unproven`, and the task still reached `READY_FOR_REVIEW`. The
delegate settled the design before the writer ran. The task is not stopped,
since `REVIEW_INCOMPLETE` opens no pull request. One fresh gate-only cell
asks the pairs left, and a pair still unasked reads `error`.

The writer drafted in 19.9 minutes and revised in 4.1. It ran every wrong
version against its prototype witnesses: 22 at the draft, 24 after the
revision. `driver.py check`, `cite` and `enumerators` passed before the
first review. `make check` passed on the draft with 5122 tests.

**Review 1: 0 blockers, 4 concerns, 3 notes.** The writer revised all of
them.

- Claim 1 entered a fresh cell on any stop. The Notes entered none when no
  pair was left. Pre-flight 2 missed it: the two disagreed on a stop at the
  last pair, and only the Notes named it.
- No wrong version ruled out marking the pairs the fresh cell answered as
  unasked. Pre-flight 1 missed it, because the prototype arranged the
  answered pair and the claim did not require it.
- The pair running at the fresh cell's stop was neither asked nor unasked
  in the claim. Base keeps the witness gate's own summary for it.
  Pre-flight 5 missed it.
- The summary said "before this edit was asked" for a survivor whose
  witness had answered. Pre-flight 8 missed it.
- The spec said "second cell" and "third cell", both on `CONTEXT.md`
  _Avoid_ lines. Pre-flight 3 does not read _Avoid_ lists.

**Review 2: 0 blockers, 2 concerns, 2 notes.** The delegate applied both
concerns and one note by hand.

- "The mutator raising as it applies a pair's edit asks that pair again"
  also covered a survivor's second ask, which the same claim skips.
  Pre-flight 2 missed it, since both sentences read the same call.
- The REVIEW tail said "never asked" for the survivor round 1's fix had
  reworded. Round 1's fix created it, as check 26 predicts.

## Checks to build (SA-0371)

27. Pre-flight 2 reads each claim against the spec's own Notes, not only
    against the other claims. Two of three cross-reading findings were
    Notes against a claim.
28. A rewording a review asks for is searched across the whole spec. Round
    1 fixed one sentence and left the same word in a verbatim line.
29. Pre-flight 3 reads each new noun phrase against `CONTEXT.md`'s _Avoid_
    lists. The `terms` gate checks only seven phrases.
