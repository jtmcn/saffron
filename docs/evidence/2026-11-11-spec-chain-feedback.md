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

## SA-0372 (b-1c59c3), after spec loop run 62

`SA-0290` added `removes` to catch two specs that clash on a name. This
spec checks one spec against its tree base. Before the cell, `run_task`
refuses the task when a file outside `touches` still reads a removed name.
The delegate settled the reader set before the writer ran. Markdown,
`.saffron/specs/` and protected paths are not readers.

The writer drafted in 18.1 minutes and revised in 3.6. It killed 20 wrong
versions at the draft and 31 after the revision. `make check` passed on
the draft with 5129 tests. The writer landed no protected edit. The
delegate landed its two edits, to `DESIGN.md` §4.2 and
`docs/agents/issue-tracker.md`, in the draft commit.

**Review 1: 1 blocker, 2 concerns, 7 notes.** The writer revised them.

- Criterion 2 said `touches` and `protected` both match by
  `scope.matches`. Only `touches` was driven one directory below a `*`.
  Pre-flight 1 missed it: the claim named two sets and the prototype drove
  one.
- `task.py`'s module and `Refused` docstrings list every pre-cell refusal,
  and the spec named neither. Pre-flight 6 missed it, since a docstring
  that turns false breaks no test.
- Frozen `docs/evidence` records read live names, so a spec removing one is
  refused. The operator accepted it, and the spec names it.

**Review 2: 1 blocker, 1 concern, 4 notes.** The delegate applied the
blocker, the concern and one note by hand.

- Criterion 3's policy failures were absent, unparseable or unreadable.
  Round 1's fix drove two of the three. Pre-flight 1 missed it again, on a
  set round 1's fix created.
- The own-path skip was claimed for both entry forms, and only one had a
  wrong version.

## Checks to build (SA-0372)

30. Pre-flight 1 lists each set a claim names in a table, member by
    member, against the witness sentence that drives it. Both rounds here
    found one undriven member, and the second came from round 1's fix.
31. A spec that adds a refusal greps the touched modules' docstrings for a
    list of refusals. `task.py` keeps three such lists.
