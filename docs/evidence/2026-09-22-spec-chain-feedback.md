# Spec chain feedback, 2026-09-22: SA-0123 and SA-0124

Two specs through `create-saffron-spec`, stacked. `SA-0123` is the writer
side of item b-fd1468. `SA-0124` is item 171, stacked on it because both
touch `saffron/ledger.py`. Item 177 was weighed the same day. The operator
chose to redefine **Run** as one task's pin, which edits protected documents,
so it gets no spec.

## Cost

| Step | Agent | Time | Tokens |
|---|---|---|---|
| SA-0123 draft, with a prototype | `spec-writer` | 34.9 min | 293k |
| SA-0123 first review | `spec-reviewer` | 8.0 min | 169k |
| SA-0123 revise, prototype rebuilt | `spec-writer` | 8.0 min | 38k |
| SA-0123 second review | `spec-reviewer` | 6.9 min | 142k |
| SA-0124 draft, with a prototype | `spec-writer` | 21.3 min | 218k |
| SA-0124 first review | `spec-reviewer` | 5.0 min | 111k |
| SA-0124 revise, one new run | `spec-writer` | 5.9 min | 18k |
| SA-0124 second review | `spec-reviewer` | 4.6 min | 102k |

Both revisions resumed the writer that drafted the spec. Each cost under a
fifth of a fresh draft, because the prototype and its context were still
held. The SA-0124 draft ran in a separate worktree while SA-0123 was
under review.

## First reviews: no blocker on either spec

| Spec | Finding | Class | Check that should have caught it |
|---|---|---|---|
| SA-0123 | Criterion 3's full ledger held no run or gate result of its own | A witness drives one member of a set | Pre-flight 1 |
| SA-0123 | The wrong implementations criteria 1 to 3 exclude were claimed, not run | An arrangement argued rather than run | Pre-flight 10 |
| SA-0123 | Size near 940 against 1000 after SA-0117's growth | Size or ceilings | Pre-flight 7 |
| SA-0123 | A dropped payload assert removed the only `error` status check in its file | A change breaking a live check or test | Pre-flight 6 |
| SA-0123 | An old-record exit code was stated and not measured | An arrangement argued rather than run | Pre-flight 10 |
| SA-0123 | One citation one line early | A claim about the tree | Pre-flight 5 |
| SA-0124 | `replay.py` was said to write no task row | A claim about the tree | Pre-flight 5 |
| SA-0124 | A `_finish` storing NULL for a measured 0 passed every witness | A witness drives one member of a set | Pre-flight 1 |
| SA-0124 | `DESIGN.md:1221` becomes false in a forbidden file | A design argument the documents do not support | Pre-flight 8 |
| SA-0124 | Test line numbers move under the parent too | A claim about the tree | Pre-flight 5 |

The measured-zero finding is the set class again. The set was the values a
stat can take, and the witness drove one of them. The run settled it in six
minutes. A mode-only patch never reaches `diff_stat`. An empty-file patch
does, and the counterfeit passed four witnesses until that run was added.

## Second reviews: one concern

| Spec | Finding | Class | Check that should have caught it |
|---|---|---|---|
| SA-0124 | The widened claim said a measured 0 on four paths, and the new run drives one | A witness drives one member of a set | Pre-flight 1, on the revision |
| SA-0123 | A counterfactual exit code named the wrong missing key | A claim about the tree | Pre-flight 5, on the revision |
| SA-0123 | §4.6 rule 1 was cited for the record, and it governs the graph | A design argument the documents do not support | Pre-flight 8 |
| SA-0124 | The empty-file run named no git version | A claim about the tree | Pre-flight 5 |

Every second-round finding came from text the revision added. The delegate
applied them by hand and did not re-review, under the two-round stop.

## What the next run should change

1. **Re-run pre-flight 1 on each revision.** A fix that widens a claim to a
   new member is itself a set claim. Both second-round set findings were
   revisions that closed one member and named more.
2. **Say where a tool behaviour was measured.** The host runs git 2.54.0 and
   the cell runs 2.39.5. A spec that quotes git output should name the host.
3. **Keep one scratch directory per writer.** The SA-0124 writer synced into
   a `proto` directory an earlier writer had left. It lost nothing that
   mattered, since SA-0123 was committed first.

# Second chain, same day: SA-0125 to SA-0128

Four specs drafted in parallel worktrees, then stacked. `SA-0127` (items 50
and 51) stands alone. `SA-0125` (b-408cf5), `SA-0126` (b-36b551) and `SA-0128`
(b-89ec93) chain, because each edits files its parent edits. Ids were assigned
up front so parallel writers could not collide, and the queue smoke test was
updated once per layer after stacking.

## Rounds

| Spec | Rounds | Blockers | Writer time, first draft |
|---|---|---|---|
| SA-0127 | 2 | 0 | 18 min, after a stop on `.saffron/**` |
| SA-0125 | 2 | 0 | 22 min |
| SA-0126 | 2 | 1 (round 1) | 26 min |
| SA-0128 | 2, plus a delegate check | 3 (2 in round 1, 1 in round 2) | 36 min |

## What the first reviews found, by class

| Finding | Class | Check that should have caught it |
|---|---|---|
| SA-0127: criteria 2 and 3 answered an errored run differently | Two criteria disagreeing on one input | Pre-flight 2 |
| SA-0127: the readability guard skipped item 50's own shape | A data flow the base cannot carry | Pre-flight 4 |
| SA-0125: nothing held both callers to one predicate | A witness drives one member of a set | Pre-flight 1 |
| SA-0125: a rejected plan recorded the baseline's tier | A data flow the base cannot carry | Pre-flight 4 |
| SA-0126: two docstrings at the ten-line limit told to grow | A change breaking a live check | Pre-flight 6 |
| SA-0126: the cap keys on a column no record fact carries | A design argument the documents do not support | Pre-flight 8 |
| SA-0128: two fixtures trip `size` by line count, one in a forbidden file | A change breaking a live check | Pre-flight 6 |
| SA-0128: the token diff had no time or memory bound | An arrangement argued rather than run | Pre-flight 10 |

SA-0128's two fixture blockers were found only by running the whole suite
against the prototype with the new counting. A grep had not found them. That
sweep is the check pre-flight 6 lacks for any spec that changes a gate's unit.

## Decisions the operator made mid-chain

1. A `.saffron/**` gate change goes by hand, after the cell (SA-0127).
2. A cut with nothing committed ends `ORPHANED`, capped at one retry per
   `spec_sha` (SA-0126).
3. `size` counts whitespace tokens, not AST logical lines. An AST count would
   put Python knowledge in core, which §2.1 forbids (SA-0128). The delegate had
   recommended the AST form first, and corrected it before dispatch.
4. Past the token-diff bound a file is estimated at 4 tokens a changed line,
   not counted in full (SA-0128).

## What the next run should change

1. **Sweep the suite for a gate's unit change.** Run every test against the
   prototype and diff the failures against base, before the first review.
2. **Check a recommendation against §2.1 before offering it.** The AST option
   reached the operator and cost a round of questions.
3. **Assign spec ids and stack order before parallel drafting.** Both paid off
   here: no collision, and the bookkeeping took one pass per layer.

---

# SA-0133, from item b-864a4d

One spec, one review round. The item asks for a digest of each agent
request and of the `CLAUDE.md` a task read. It depends on `SA-0128`, the end
of the queued `SA-0125` to `SA-0128` chain.

## Cost

| Step | Agent | Time | Tokens |
|---|---|---|---|
| Draft, with a prototype | `spec-writer` | 26.4 min | 222k |
| First review | `spec-reviewer` | 9.4 min | 142k |

The operator settled the design in the dispatch: which string to hash, which
event carries each digest, and no ledger or record change. The draft
returned no question.

## First review: no blocker, three concerns, three notes

| Finding | Severity | Class | Check that should have caught it | Outcome |
|---|---|---|---|---|
| Criterion 2 claimed every session, and three kinds went undriven | concern | A claim's witness drives one member of a set | Pre-flight 1 | Applied in the notes |
| Criterion 3's three cells could share one repo once `SA-0126` lands | concern | A parent spec changes a helper the witness uses | None | Applied |
| The prototype ran at a base with none of the parent chain built | concern | A parent spec changes a helper the witness uses | None | Left, since no base carries the chain yet |
| Criterion 2 could declare criterion 1's mutant | note | A claim's witness drives one member of a set | Pre-flight 1 | Left, since intake's rule on a shared mutant is unread |
| The size note used lines after `SA-0128` moves `size` to tokens | note | Size or ceilings | Pre-flight 7 | Applied |
| The harness named `cost_usd_est` where `run_agent` reads `total_cost_usd` | note | A name the spec leans on that the base lacks | Pre-flight 3 | Applied |

## What the next run should change

1. **Read the parent specs as edits to the base.** Three of the six findings
   came from what `SA-0126` and `SA-0128` change once built. They affect a
   test helper, the `size` unit, and the prototype's base. No pre-flight check
   reads a queued parent's notes for the helpers and units this spec leans
   on. That is the next check for a spec with a `depends_on`.

# Spec chain feedback, 2026-09-22 (evening): SA-0129, SA-0130 and SA-0131

Three specs from the spec loop's run 14 summary. Three writers ran in
parallel, each in its own worktree. Two other items of the five landed by
hand: #463 (b-440f17, `prose` reading Python) and #464 (the writer rules).
The child `SA-0132` is drafted and waits for `SA-0129` and `SA-0131` to merge.

## Cost

| Spec | Step | Time |
|---|---|---|
| SA-0129 | draft, with a prototype | 12.4 min |
| SA-0129 | revise to wait on SA-0128 (operator decision) | about 7 min |
| SA-0129 | first review, then revise | 3.8 min, 5.2 min |
| SA-0129 | second review, then revise with measurement | 4.2 min, 6.0 min |
| SA-0130 | draft, then move the witness to `test_context.py` | 11.6 min, 5.1 min |
| SA-0130 | first review, then revise | 2.0 min, 5.0 min |
| SA-0130 | second review, fixed by the delegate | 2.8 min |
| SA-0131 | draft of parent and child, with prototypes | 29.0 min |
| SA-0131 | first review, then revise with measurement | 2.6 min, 5.3 min |
| SA-0131 | second review, then revise with measurement | 5.1 min, 5.2 min |

No round found a blocker. Round 2's concerns on `SA-0129` and `SA-0131`
were settled by running each wrong version on the writer's prototype, not
by a third review.

## Findings by class

| Spec | Round | Finding | Class | Check that should have caught it |
|---|---|---|---|---|
| SA-0129 | 1 | Every driven boundary divided exactly | Driven values share a shape the claim does not require | none |
| SA-0129 | 1 | The clear line beside a size blocker was unpinned | Two criteria disagreeing on one input | Pre-flight 2 |
| SA-0129 | 2 | Every driven ceiling had a whole-token 80% | Driven values share a shape the claim does not require | none |
| SA-0129 | 2 | No no-rows run watched the clear line | A witness drives one member of a set | Pre-flight 1 |
| SA-0130 | 1 | The dictated text said the host runs every listed wrong version | A claim about the system the dictated text makes | none |
| SA-0130 | 2 | The dictated text could override `CLAUDE.md`'s run against unfixed code | A claim about the system the dictated text makes | none |
| SA-0131 | 1 | A check against the mirror's default ref passed | A fixture makes two sources of one fact agree | none |
| SA-0131 | 1 | The parent's rows had no stated order | A fixture makes two sources of one fact agree | none |
| SA-0131 | 1 | `saffron cell` was said to apply no refusal | A claim about the tree | Pre-flight 5 |
| SA-0131 | 2 | The mirror's `HEAD` and `FETCH_HEAD` agreed with the pin | A fixture makes two sources of one fact agree | none |
| SA-0131 | 2 | A stated reason was false for `saffron batch` | A claim about the tree | Pre-flight 5 |

## What the pre-flight should learn

Three classes recurred with no check behind them.

1. **Driven values that share a shape.** Before review, list each value a
   witness drives and name one property they all share that the claim does
   not promise. Exact division, a multiple of 5 and a whole token count were
   each found one round apart on `SA-0129`.
2. **Two sources of one fact.** For each fact a check reads, list every
   place the fixture holds it: a pinned sha, a mirror ref, `HEAD`,
   `FETCH_HEAD`, a ledger state. Make at least one pass hold them apart.
3. **Text the cell is told to write.** Check each sentence a spec dictates
   against the code, and against the rest of the prompt it lands in.

Both round-2 concerns on `SA-0129` and `SA-0131` repeated their round-1
class. Naming the class in the second review's prompt found more of it.
Naming it in the writer's revision prompt did not stop it.

# SA-0134, from item b-602d00

One spec through `create-saffron-spec`. The writer split the item at about
500 lines against the `feature` ceiling of 600. `SA-0134` is the reader of
a tree base. `SA-0135` adds the `consumes:` field and the refusal, and is
not written. The operator stacked `SA-0134` on `SA-0129` so that the
child's `intake.py` edit follows `SA-0129`'s.

## Cost

| Step | Agent | Time | Tokens |
|---|---|---|---|
| Draft, with a prototype and the split | `spec-writer` | 22.5 min | 229k |
| First review | `spec-reviewer` | 3.9 min | 63k |
| Revise, with bare-mirror probes | `spec-writer` | 7.3 min | 64k |
| Second review | `spec-reviewer` | 1.9 min | 44k |

The second review's findings were applied by hand. No third review ran.

## Findings by class

| Round | Finding | Class | Check that should have caught it |
|---|---|---|---|
| 1 | Criterion 4 drove no path only the older commit held | A witness drives one member of a set | Pre-flight 1 |
| 1 | "Exactly that path" was false, since `git ls-tree` normalises `./`, `//` and `.` | A claim about a tool, not run | Pre-flight 10 |
| 1 | The child was handed three of the malformed shapes | A split's hand-off to the child | none |
| 1 | The reader's exceptions were unnamed, one of them not `GitError` | A split's hand-off to the child | none |
| 1 | No witness committed a `100755` file | A witness drives one member of a set | Pre-flight 1 |
| 1 | A submodule was in neither set | A witness drives one member of a set | Pre-flight 1 |
| 1 | A whole word also matches a comment | A design argument the documents do not support | Pre-flight 8 |
| 1 | `file_at` has seven tests, not six | A claim about the tree | Pre-flight 5 |
| 2 | Criterion 2 read no `100755` file's text | A witness drives one member of a set | Pre-flight 1 |
| 2 | A path holding a colon could not be written | A split's hand-off to the child | none |
| 2 | A `..` segment past the root was not measured | A claim about a tool, not run | Pre-flight 10 |
| 2 | The decode depends on the host locale | A claim about the tree | Pre-flight 5 |
| 2 | The text of `exact.py` was left open | A fixture's text left open | none |

## What the pre-flight should learn

1. **A split's hand-off is a class of its own.** Three findings were about
   what the unwritten child inherits. Before review, list every input the
   parent's function does not answer and every exception it raises. Hand
   the list to the child's spec.
2. **Probe a tool in the shape the code runs it.** The first reviewer probed
   git in a worktree. The writer then probed a bare mirror through
   `ensure_mirror` in a scratch test, and `saffron/../CLAUDE.md` resolved
   there too. The operator's session could not run git outside its worktree.
3. **A revision that adds a set member adds it to every criterion.** Round
   1 added `100755` to criterion 1, and round 2 found criterion 2 without it.

# SA-0135 and SA-0136, the rest of b-602d00

The writer that drafted `SA-0134` was resumed for both. Its first estimate
of the whole second half was about 610 lines against 600, so it split
again. `SA-0135` adds the field and a refusal from `run_task`. `SA-0136`
refuses nine malformed shapes at load and maps an unreadable entry to a
refusal. The operator chose no new task state: `Refused(reason)` writes no
ledger row, as `CONTEXT.md`'s Refusal already says.

## Cost

| Step | Agent | Time | Tokens |
|---|---|---|---|
| Size estimate and split proposal | `spec-writer`, resumed | 3.2 min | 260k |
| Draft both, with a ty prototype | `spec-writer`, resumed | 15.6 min | 339k |
| SA-0135 first review | `spec-reviewer` | 9.5 min | 151k |
| SA-0136 first review | `spec-reviewer` | 5.4 min | 88k |
| Revise both, with the batch run measured | `spec-writer`, resumed | 12.1 min | 394k |
| SA-0135 second review | `spec-reviewer` | 7.1 min | 134k |
| SA-0136 second review | `spec-reviewer` | 3.9 min | 77k |

The second reviews' findings were applied by hand. No third review ran.

## Findings by class

| Spec | Round | Finding | Class | Check that should have caught it |
|---|---|---|---|---|
| SA-0135 | 1 | "Prints one line" while `Ceilings` and `stacked on` print first | Output other code emits around the change | none |
| SA-0135 | 1 | A refusal leaves a lone `Ceilings` event for `saffron watch` | Output other code emits around the change | none |
| SA-0135 | 1 | The batch sequences were argued, not run | An arrangement argued rather than run | Pre-flight 10 |
| SA-0135 | 2 | The run-time refusal is missing from the plan's `refusals:` and from `saffron queue` | Output other code emits around the change | none |
| SA-0136 | 1 | The only unresolved entry came last, so a two-list join passed | A witness drives one member of a set | Pre-flight 1 |
| SA-0136 | 1 | The error text holds the entry whatever the validator says | A claim about a tool, not run | Pre-flight 10 |
| SA-0136 | 1 | No segment ending in a dot was driven | A witness drives one member of a set | Pre-flight 1 |
| SA-0136 | 1 | SA-0135's fixture was not required canonical | A split's hand-off to the child | none |
| SA-0136 | 2 | A `.` or `..` segment was driven only inside a path | A witness drives one member of a set | Pre-flight 1 |

## What the pre-flight should learn

1. **Output around the change is a class of its own.** Three findings on
   `SA-0135` were lines other code already prints or records beside the
   new one: the ceilings line, the events log, the batch plan and the
   queue. Before review, list every place the path the change runs through
   prints or records, and say what each shows for the new outcome.
2. **A position is a member of a set.** Both `SA-0136` rounds found a set
   the witness drove only in one position. That was the unresolved entry
   last, then a dot segment only inside a path. Pre-flight 1 should ask
   where each member sits, as well as which members are driven.
3. **The hand-off class recurred across a split.** The parent's fixture
   had to meet rules the child adds, and the child could not edit it.
