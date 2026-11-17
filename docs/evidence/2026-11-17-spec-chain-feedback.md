# Spec chain feedback, 2026-11-17

Continues `docs/evidence/2026-11-16-spec-chain-feedback.md`. Check numbers
carry on from its 63. The chain took b-f7a591 after spec loop run 76
merged, from `a5c1f2e9`.

## b-7f6ce2, parked before a writer

The chain began at b-7f6ce2 and stopped before dispatch. A backtest on
`SA-0381` showed that the siblings it names live only in a claim's prose.
No declared wrong version holds them, so the host cannot name them. The
item's record says so, and the chain moved to b-f7a591.

## The split (b-f7a591)

The first writer built a prototype and measured it at 511 lines. Priced at
the measured overrun, that is 3600 tokens, past the 2400 line. It split in
two. `SA-0406` adds the review helpers and `run_rebut`'s `unreviewed`
keyword. `SA-0407` wires them into `_drive_cell`. The split report named
five design calls. The caller took the writer's advice on one: REBUT's own
`EXHAUSTED` stands, since a dependent stacks on a `REVIEW_INCOMPLETE`
branch.

## SA-0406 (helpers)

Two rounds, no blocker. Round 1 found two concerns. The Context said
`review.LENSES` names three lenses where it names four. "The lens" in a
clause could mean the holding `LensReview` or the finding's own field, and
`survivor_finding` sets that field to `adequacy`. Both are pre-flight 5
misses. Round 2 found four concerns. Item 3 asked for a shared helper that
item 5 forbade, the class check 64 names. Two claims named a set no wrong
version emptied, and the caller's probes killed all three new wrong
versions. A docstring edit dropped a sentence still true at the spec's
head.

## SA-0407 (wiring)

Two rounds, with a blocker in each. Round 1's blocker: criterion 2 named
every one of REBUT's own stops, and the witness drove only those
`_rebut_gates` returns. A concern found the "each lens" set driven with one
member, and another found `DESIGN.md` §3.3's legend left false. Round 2's
reviewer named a wrong version and asked for a run. The caller ran it, and
it survived: the two-lens cell put the only blocker-holding lens last. A
third lens with an error placed it in the middle. Every round-2 fix came
back measured, and all 22 wrong versions fail their witness.

The writer asked for seven hand edits where the brief named two. Each
covered a sentence the change makes false, and the caller landed all seven
plus §3.3. `driver.py check` blocks on size at 2676 tokens. The estimate
counts test tokens, and the cell's own size gate counts 144.

## SA-0408 (b-e9dd4c)

One writer, no split. It priced the change at 171 tokens against the bug
ceiling. Round 1 filed no blocker. Its first concern named a wrong version
the reviewer did not run: any stale waiting row refuses. The caller ran it
on both witnesses, and it survived both, so it became a blocker. Each
witness put the decisive row last. An older stale row under a newer pushed
row now separates the readings, and the caller re-ran both probes. Round 2
found four notes and no blocker. The caller read the live ledger to settle
the empty `retired_first`, which the reviewer could not reach.

## What the reviews keep finding

Every blocker and three concerns were one class. A claim names a set, and
its witness drives one member, or puts the member that matters at an edge
where a first-only or last-only reading also passes. Check 65 names it. `SA-0408`'s blocker was the same class.

## Checks to build

64. Every instruction in a spec's Problem section is read against every
    other, for one that forbids what another asks.
65. A set the claim names is driven with at least three members where
    order matters, and the member that decides the outcome sits between
    two others.
66. `driver.py check` prices a spec's size from its non-test tokens, as the
    size gate counts them.
