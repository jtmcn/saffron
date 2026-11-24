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

## SA-0418 (b-952c34)

One writer, two reviews, and a fixture pass after the second review. The
writer took about 72 minutes for the draft and 18 and 20 for the two
revisions. Each review took about 11 minutes.

Round 1 found one blocker. The function under change already picks the
last gated attempt as the diff's generator. A rule tied to that attempt
passed every witness, because each fixture task gated its last cell
attempt. Check 67 named the set's members but not the rule beside it.
Round 1 also found a mutant the writer had called impossible. The line
`math.floor(ceilings.timestamp)` survives the change, so the spec now
carries one.

Round 2 found one blocker. The spec described base's shared-floor guard
as wider than it is. The prototype had widened it silently, and the
writer read the claim from the prototype. Check 5 resolved the citation
but not the sentence. The operator kept base's rule, and the measured
table did not move. Round 2 also named a rule in which every cell
attempt claims its span. It survived once measured, and a new fixture
member kills it. The writer ran 25 wrong versions, and all died.

## What SA-0418 adds

76. A witness for a selection rule also kills each selection the same
    function or its module already makes, run as a wrong version.
77. Each sentence that says what base does is read at base, never from
    the prototype, before the prototype's measurements are quoted.

## SA-0419 (b-7431a2)

One writer, two reviews, and a fixture pass after the second review. The
writer took about 21 minutes for the draft and 16 and 13 for the two
revisions. Each review took 5 to 7 minutes. Neither review found a
blocker.

Round 1 found that the fold's refusal never met `PASSED` or `DRAINED`.
Both are members of sets the same module already declares. The fix added
those two values. Round 2 then found `FAILED`, the other member of the
preflight set, refused nowhere. So the first fix named members and not
the set. Round 2 also found the fold's twin of a refusal placed after the
commit, which criterion 1 already drove. The writer ran 30 wrong
versions, and all died.

## What SA-0419 adds

78. When a refused set borrows from a declared set in the same module,
    every member of the declared set is a refused case.
79. A refusal a criterion drives before and after a commit is driven the
    same way on each path the claim names.

## SA-0421 (b-0f5493)

One writer, two reviews, and the delegate's fixes after the second. The
writer took about 34 minutes for the draft and 5 for the revision. The
reviews took about 11 and 9 minutes.

Round 1 found two blockers. The over-bound member was a clean event, so a
version that returned the handed event whenever it bounded passed. The
other was measured by the delegate: `append`'s new return type broke `ty`
at two test call sites outside `touches`. Round 1 also found the refused
write undriven in `run_task`'s closure, and DESIGN.md text that claimed
too much. The delegate's hand edit had missed a second DESIGN.md sentence,
which the writer had not named either.

Round 2 found no blocker. The budget cleared REBUT's history by $0.32, so
it rose to $60. Two DESIGN.md sentences named too few emitters.

## What SA-0421 adds

80. A change to a function's return type runs `ty check` on the prototype.
    Every site that passes the function as a value is in `touches`.
81. A hand edit to a protected document greps the whole document for each
    claim the change falsifies, not only the sentence the item names.

## SA-0422 (b-d9ed45)

One writer, two reviews, and a final writer round. The writer took about
33 minutes for the draft. Round 1's revision ran long, since the host was
busy with a batch. Each review took 10 to 13 minutes.

Round 1 found no blocker and eight concerns. A fixed `/tmp` lock root
trusted a directory or symlink another uid could plant. The scope cut was
stated in one direction only. No witness drove PACKAGE under the lock. The
claim said "every home on the host" over a root per uid. Round 2 found
two concerns. A mode check relied on the host's umask. No member drove an
unsafe root and a held lock at once. It also cited a line range wrongly,
and the writer showed this with the file at base. The writer ran 27 wrong
versions, and 26 died. The racy one is named in the notes.

## What SA-0422 adds

82. A witness that checks a file mode sets the umask it assumes.
83. A path a change creates outside the batch tree is checked for owner,
    type and symlink before it is used.

## SA-0423 (b-bc54d1)

One writer, two reviews, and a final writer round. The writer took about
33 minutes for the draft and 6 for each revision. Each review took about
11 minutes.

Round 1 found no blocker and four concerns. The guards' witnesses drove
three exception families, and `KeyboardInterrupt` on one path only. A
ledger check was vacuous because an earlier call had already written the
state it read. A rewritten case checked a mark no reader sees. Round 2
found three blockers in the same class. Every exception the revision
added was a `RuntimeError` subclass, so a guard naming `RuntimeError`
passed. A guard that also wrapped the ledger write passed as well. The
final round added a test-local `Exception` subclass on each path. The
writer ran 41 wrong versions, and all died.

## What SA-0423 adds

84. A claim that a guard catches `Exception` is driven with a test-local
    `Exception` subclass on each path, since named kinds share bases.
85. A guard's upper edge is driven too: the statement before the guarded
    one raises, and the witness expects it to escape.

## SA-0424 (b-9eceda)

One writer, two reviews, and a final writer round. The writer took about
56 minutes for the draft and 18 for the first revision. Each review took
about 13 minutes.

Round 1 found one blocker. The spec let a cell split `append`'s one
`except` clause, so the mutant's `find` could match twice or never. A
warning printed one event late passed every emitter witness, because a
second event always followed each fault. The writer measured that it
survived. Round 1 also found that step 6 was built on the prototype's
`SA-0421` rather than the open pull request. Round 2 found one blocker.
The only two-fault log met its faults in one order, so a version that
swapped which flag triggers each warning passed. It also found that the
spec paraphrased the mutant. The writer ran 55 wrong versions, and 54
died. The survivor behaves like correct code.

## What SA-0424 adds

86. A claim over two faults drives both orders, and a fault as the log's
    last event.
87. A spec whose mutant pins a construct tells the cell to keep that
    construct, and never says that a mutant pins it.
88. A child's prototype builds on its parent's open pull request when one
    exists, not on the parent's prototype.

## SA-0425 (b-f582ee, b-b8f0d9)

One writer, two reviews, and a final writer round. The delegate first
reproduced the defect on main with a stub that raised deaths into
`_RebutCap`. The draft took about 52 minutes. Each review took 8 to 9
minutes.

Round 1 found one blocker. In the verdict stage, a death followed by a
second lens met the refusal branch, which set the cut. Every witness row
had one lens. Round 1 also found that an older test drove its cut with a
turn ceiling. It stayed green under the new rule and stopped guarding
`SA-0407`'s reset. Round 2 found no blocker. Two concerns named members
reached only through a sequence of sessions in one stage. A third named
the bare words "stage" and "pool" a cell would copy. The writer ran 22
wrong versions, and 20 died. The two survivors behave like correct code.

## What SA-0425 adds

89. A rule keyed on spend drives each sequence of sessions that can share
    one pool, not only one session per stage.
90. A change that narrows when a predicate fires reads every existing test
    that drove the old predicate, whether or not it still passes.

## SA-0426 (b-18fa39)

One writer, two reviews, and the delegate's own last edit. The delegate
first rebuilt finish 103's draft from the mirror and measured pytest's
80-column cut. The draft took about 28 minutes and the revision about 20.
Each review took 7 to 8 minutes.

Round 1 found one blocker. A test outside `touches` requires `GATES.md` to
name every failure field, and `GATES.md` is forbidden. The prototype ran
its witnesses and not the suite. Round 1 also found two readers the new
field reached: `migrate`'s top-up and the PR body's table. Round 2 found
no blocker. One concern named a witness whose detail held a pipe alone,
where the claim says the detail is escaped as the message is.

## What SA-0426 adds

91. A spec that adds a contract field runs the whole suite on its
    prototype, since a test may enumerate the fields.
92. A witness for an escape drives every character class the escape
    handles, not only the first one.

## SA-0427 (b-708b05)

One writer, two reviews, and a final writer round. The draft took about 37
minutes, the revision about 23 and the final round about 20. Each review
took 6 to 8 minutes.

Round 1 found no blocker and four concerns, all on one ordering criterion.
Its witness was red against its mutant and never measured against base,
where nothing truncates on release. It drove one of two locks and one
ending, and its seam was measured on a newer Python than the cell runs.
Round 2 found no blocker. One concern named two claims that the release
window contradicted. Another named a docstring already at its line limit.
The last three named wrong versions no command had run. The final round
killed all ten.

## What SA-0427 adds

93. A witness for an ordering runs against base as well as its mutant,
    since base may already satisfy the order by doing nothing.
94. A spec that adds a sentence to a docstring counts that docstring's
    lines at base against the gate's limit.

## SA-0429 (b-619b7d)

One writer, two reviews, and a final writer round. The draft took about 29
minutes. The delegate then sent it back before any review, because the
writer had measured a red adopt that admitted the child and left it out of
scope. That revision took about 27 minutes, and the next two about 2 and 4.
Each review took 11 to 12 minutes.

Round 1 found no blocker and three concerns. The size estimate sat 16 lines
under the prototype, and the measured figure prices past 80% of the
ceiling. No witness adopted one pull request red twice. A window between
two ledger writes stays open until adopt is retried. Round 2 found no
blocker. Its two concerns were members no witness drove: a repeat on the
same head, and a row with no push. The final round killed all three
wrong versions it added.

## What SA-0429 adds

95. A claim about a retried command drives the retry on the same input,
    not only on a fresh one.
96. A spec's size estimate is read from the prototype's numstat, never
    fitted to the 80% line.
