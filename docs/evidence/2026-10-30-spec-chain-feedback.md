# Spec chain feedback, 2026-10-30

The operator asked why the loop still needs its review seats, and the answer
was that the item ranked third in runs 49 and 50 had no record. This chain
filed it as **b-78a590** and wrote `SA-0328` from it, at base `7c1fdbd5`.

- **b-78a590.** `SA-0328`: the criterion probe session names one edit per
  sentence of its claim, up to sixteen, and the host applies every one. The
  record carries the measurement: over 22 `SA-03xx` tasks, 122 criterion
  probes and 518 wrong versions ran, and `SA-0327`'s five seat survivors were
  each a sentence of a claim the cell had probed at another sentence.

The operator settled the design arm before the writer ran. The witness stays
withheld from the session, and the shape mirrors wrong versions. A session
shown the witness is the record's next arm.

| Spec | Round 1 | Round 2 | Size |
|---|---|---|---|
| `SA-0328` | 1B 4C 3N | 0B 2C 3N | 290 lines, estimated |

The draft took 36 minutes. The revision took 11, and the reviews took 7 and
9. The spec stopped at two rounds. The second round's findings were applied
in place by the delegate, with no third review.

## Each finding by class

- **A witness drives one member of its set.** Round 1's blocker. Every
  applied edit in criterion 4's witness sat under the first criterion, so a
  loop that paired every probe with `spec.acceptance[0]` passed, and the
  spec's own wrong version named that loop. Three of the four concerns were
  the same class on criterion 1: the `preserves` member, the one-sentence
  claim that excludes no host split, and sentences already in sorted order.
- **A claim about the tree that stopped being true.** The fourth concern.
  The delegate amended the two protected sentences after the draft and
  before the review, and the notes still quoted the old text.
- **A witness the constant it tests cannot move.** Round 2's first
  concern. The prompt witness read `16` and no slot, so a literal `16` in
  the prompt passed. The witness now patches the constant.
- **An arrangement argued rather than run.** Round 2's second concern. The
  reviewer re-derived the seven gate results and the `subsets` list from
  the base and found them right, and said the run that settles them is the
  cell's own witness.
- **A citation off by a line.** Two notes in each round, and one word,
  `ceiling`, used for the answer cap and the session budget alike.

## What the pre-flight missed

Check 1 was run by the writer over the sets it saw, and it missed the set a
whole-cell witness quantifies over by its fixture: which criterion each
applied edit belongs to. The check as written asks for the members of a
set the claim names. This set is named by the wrong version, not the claim.
A pre-flight line for check 1: read each `wrong_versions:` entry as a set
too, and name the fixture member that excludes it.

Check 12 caused the fourth concern. The delegate landed the protected edits
between the draft and the first review, as the check says, and the draft's
notes went stale under them. Land them before the writer runs, or tell the
writer they will land and to describe them as amended.

## What the run itself got wrong

The writer ran about 36 minutes, against the 19 to 30 the last chain
measured, and most of the extra was its own `make check` and `history`
runs. The delegate dispatched one writer and one reviewer per round, with
no spike, since no live API changes.
