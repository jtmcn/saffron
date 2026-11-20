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

## SA-0416 (b-32b3db)

One writer, two reviews, and a fixture pass after the second review. The
chain began on 2026-11-18 and ended on 2026-11-20, after a weekly usage
limit cut the second review off mid-read. The writer measured the gap on
this repo's tree: an edit to line 200 of `SCHEMA` derived nothing. Its
first prototype killed 15 wrong versions, and the reviews brought the
count to 20.

Round 1 found one blocker and one concern.

- The refusal witness refused every call, so `ls-tree` raised first. The
  blob read's own refusal branch never ran. A blob read that returns
  `None`, as `read_at_head` does, passed.
- The notes gave the string pattern in YAML escaping for a Python dict,
  and no fixture used a single quote.

Round 2 found one blocker.

- No witness diff held two non-test files whose added lines differ. So a
  line set built once, outside the per-file loop, passed.

The writer measured every fix, and no third review ran. Budget rose from
58 to 62 after round 1, since the old ceiling cleared the worst review
plus rebut by $0.32.

## What this chain adds

Both blockers sit after the decisive step: a second call, and a second
file. Check 67's class reached both. Neither brief named a second call or
a second file.

72. A witness for a function that makes two calls in sequence refuses the
    second call alone, with the first call passing through.
73. A witness for a per-file loop holds two files in which the second
    file's line numbers would read differently under the first file's set.

## SA-0417 (b-3a3081)

One writer, two reviews, and a fixture pass after the second review. No
review found a blocker. Each found concerns that named wrong versions the
writer had not run, and each such version survived once measured.

Round 1 named four. A findings walk that redacted only each claim
survived. So did a redaction skipped when the token is `None`, a plan
parsed and dumped again, and a default log that read the environment's
token. Every placed credential sat in a claim, and every drive handed a
token.

Round 2 named two more. A plan dumped again with `indent=2` wrote the
same bytes as the block, since the block was itself that dump. A fallback
to the environment survived in `run_task` and in both PACKAGE logs,
because no `None` call set the environment.

The writer measured each fix, and no third review ran. The spec carries
no mutant: `saffron mutant` refused the writer's, because its `find` is
new at base. The writer ran 30 wrong versions, and all died.

## What this chain adds

Both rounds found the same shape. The witness held every input the
change handles in one form, so a wrong version that handles only that
form passed. Check 67 names a set's members. It does not ask which form
each member takes.

74. A witness for a function that takes an optional value drives the
    absent case as well, with every fallback source set to a value it
    can see.
75. A witness that compares bytes uses an input that no default
    serializer reproduces, so a parse and a re-dump changes them.
