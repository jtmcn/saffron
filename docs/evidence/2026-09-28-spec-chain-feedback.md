# Spec chain feedback, 2026-09-28: three tier-1 items from run 20 become six specs

Run 20 ranked three items for Saffron to absorb before the seats go:
b-7e69d0, b-ab4b33 and b-abeb74. Each moves one seat's work into the cell.
This run turned them into specs through the writer and reviewer chain, with
one writer per item working in parallel, each in its own scratchpad worktree.

## What the operator settled up front

- The three form one linear chain.
- Wrong versions are prose per criterion, turned into edits by a session of
  their own.
- A contradicted rebuttal reaches `READY_FOR_REVIEW`, marked, never
  `SCOPE_REVIEW`.
- A fourth lens lands with an ADR and a measured pass.

## What the chain produced

| Spec | Item | Risk | Size by `check` | Rounds |
|---|---|---|---|---|
| `SA-0187` | b-7e69d0, the field and its session | standard | 78% | 2 |
| `SA-0190` | b-7e69d0, the host runs them | elevated | 79.6% | 2 |
| `SA-0188` | b-ab4b33 | standard | 92%, measured | 2 |
| `SA-0189` | b-abeb74, the harness | elevated | 10% | 2 |
| `SA-0191` | b-abeb74, the lens | standard | 69% | 2 |
| `SA-0192` | b-abeb74, its edges | standard | 38% | 2 |

The stack is `SA-0187` ← `SA-0190` ← `SA-0188` ← `SA-0189` ← `SA-0191` ←
`SA-0192`. ADR 8 records the fourth lens and amends ADR 4.

`SA-0188`'s 92% is its writer's measured prototype, 1705 tokens, priced again
by `check`'s 1.62 overrun. That is b-b0a187's double count, and the operator
accepted it.

## Where the drafts stopped before any review

Two writers stopped on their own and handed a decision back.

- **Both b-7e69d0 and b-abeb74 split on size.** Each writer priced the whole
  item from a measured neighbour, or from a prototype, before writing. Each
  came back at 138% and 113% of the ceiling. Neither spec was written
  whole and then cut.
- **The lens name collided.** The brief named the lens `standards`. The
  end review's lens already holds that key, and two readers tell the reviews
  apart by lens name alone. The writer measured the break on a stub lens
  before writing a word.

The brief caused the second one. It named a key without checking every
reader of `review.LENSES`, which pre-flight 3 asks for. The pre-flight ran on
the item, not on the brief's own decisions.

## Findings by class

| Class | Spec | Round | Check that should have caught it |
|---|---|---|---|
| A tabled value that coincides with another computation (sorted order, entry count, last criterion, palindromic order) | 0187, 0190, 0188 | 1, 2 | pre-flight 1 |
| A pairing a loose zip gets right by accident | 0190 | 1 | pre-flight 1 |
| A witness that renames an existing test, which `census` fails | 0191, 0192 | 1 | pre-flight 6, not run on these parts |
| A pinned test the change turns vacuous, not red | 0189, 0191 | 1 | none: pre-flight 6 finds breaks, not silence |
| A preparatory edit no witness forces | 0189 | 1 | none |
| A check applied to one member of a lens set | 0188 | 1 | pre-flight 1 |
| A helper that cannot carry the value a claim names | 0187, 0191 | 1 | pre-flight 3 |
| A hand edit that overstates the mechanism | 0187, ADR 8 | 1 | pre-flight 8 |
| Stale text after a revision | 0187, 0190 | 2 | pre-flight 5, rerun after revising |
| A default patched where the build may move it (`__defaults__` against a keyword-only one) | 0189 | 2 | none |
| A parametrised id a changed row renames, which `census` fails | 0191 | 2 | pre-flight 6, not extended to ids |
| A new parametrised id `revert` cannot collect at base | 0191 | 2 | none, left for step 1b |

No round found a claim about the tree that had stopped being true.
`driver.py cite` ran clean on every draft.

## New checks this run argues for

- **A witness that renames a test.** Pre-flight 6 lists "a test the spec
  deletes". Two parts carried a rename that reads as a replacement. The
  check becomes a grep: every `replaces`, `renamed` or `under the new name`
  in a spec's notes against the tests it names at base.
- **A pinned test the change silences.** Two reviewers found
  `test_the_spread_pass_s_per_run_totals_are_re_derivable` independently.
  The fourth lens turns it from red to vacuous, so a stub-lens blast radius
  counts it as green. The check runs the stub, then diffs each test's assert
  count, not only its pass or fail.
- **The brief's own decisions.** A decision that names a key, a file or a
  state gets pre-flight 3 before any writer sees it.

## Rounds

| Step | Result |
|---|---|
| Writers, three in parallel | two stops (size, name), one draft |
| Writers, after the decisions | six specs, ADR 8 by hand |
| Review round 1, six specs and ADR 8 | 5 blockers, 29 concerns |
| Review round 2, six specs | 4 blockers, 16 concerns |
| Writers, round 2 answered | applied with no third review |

Every round-2 blocker was a witness fix a writer could apply as stated. None
reopened a spec's subject, so no spec took a third review.

## What the delegate got wrong

- **A decision that could not be built.** I told the `SA-0189` writer to
  monkeypatch `review.LENSES`. A default argument is bound when its `def`
  runs, so the patch would move nothing. The writer measured that and
  corrected it. Its replacement then failed round 2 for the same reason one
  level down. The second fix spies on the argument each call receives.
- **A masked exit code.** A background `make check; tail` reported exit 0
  over two failures, both from my own ADR 8 edits. The records check wants one
  principle per bullet. Read the log, never the notification's code.
- **A brief that named a key without its readers.** The `standards` collision
  above.

## Not settled

- The fixture for ADR 8's measured pass is hand work once `SA-0191` lands.
  Its defect table is in `SA-0191`'s notes, with severities unconfirmed.
- The issue-tracker and spec-writer rules that tell writers to use
  `wrong_versions` wait for `SA-0190` to merge.
- `SA-0188`'s optional quote fields are the first unrequired properties in an
  `output_format` schema. Its cell's REBUT is their first live run.
- Every ordering arrangement the reviews called reasoned, not run, waits for
  the loop's step 1b.
