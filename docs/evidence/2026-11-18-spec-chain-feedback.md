# Spec chain feedback, 2026-11-18

Continues `docs/evidence/2026-11-17-spec-chain-feedback.md`. Check numbers
carry on from its 69. The chain took b-c12d39 after spec loop run 79
merged, from `f1068af4`.

## SA-0415 (b-c12d39)

One writer, two reviews, and a fixture pass after the second review. The
writer killed 37 wrong versions on its first prototype. The two reviews
added 26 more, and the prototype killed every one.

The writer measured the negation word list over the done corpus. It
matched 1233 of 1580 claims, and 19 of 25 sampled hits were real negative
clauses. The operator chose to print those lines as concerns in
`driver.py check` and to block only on an undriven member.

Round 1 found two blockers and five concerns.

- No witness pinned the negation line's text, though the driver splits on
  its ending.
- No witness saw lines from two criteria in one call. So a hard-coded
  `criterion 1`, or a walk that stopped at the first flagged criterion,
  passed.
- The concerns: a `positive_case` that skipped member lines, driven wrong
  versions at the edges of their list, members in sorted order, a blank
  check by emptiness, and a hand edit the spec described wrongly.

Round 2 found two blockers and two concerns, all one class.

- The last criterion never yielded a line, so a walk that skipped it
  passed. The first and last members of each set were driven, so a walk
  that dropped either passed.
- The twins with and without a `positive_case` sat in no fixed order, so a
  flag carried across criteria passed.

The writer applied round 2's fixes on its prototype, and the caller ran no
third review. The writer placed the quiet claim third from last rather
than second to last. It measured that a flag lagging one criterion passes
when a quiet claim sits between the twins.

Size crossed the 2400 split line after each round: 2380, then 2460, then
2608 tokens. Every added token is a test fixture. The cell's size gate
counts 461 tokens against 3000, so the spec stays whole.

## What the reviews keep finding

Both rounds found check 65's class, after a writer whose brief named it.
Round 1 found the first member at an edge. Round 2 found the last one.
Neither round's fix reached the other edge until a reviewer read for it.

## Checks to build

70. Every fixture puts a deciding member at both edges in turn, first and
    last, and a third case between them. A walk that drops either edge
    then fails.
71. A loop over criteria, sets or members carries no flag across
    iterations unless a witness puts the reader of that flag after its
    writer.
