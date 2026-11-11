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
