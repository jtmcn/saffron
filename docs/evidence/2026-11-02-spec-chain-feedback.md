# Spec chain feedback, 2026-11-02

Run 52's plan checkpoint refused `SA-0330` at $7.50, before any code. It
priced 480 whole-diff lines, and `size` would have counted 120. The operator
moved **b-15db6e** to tier 1 and asked for its spec. This chain wrote
`SA-0333` from it, at base `b0bbf178`.

- **b-15db6e.** `SA-0333`: the plan carries `estimated_test_lines` apart from
  `estimated_lines`. The checkpoint leaves those lines out where the repo
  declares `test_paths`, and prices the whole estimate where it declares none.

The operator settled the arm before the writer ran. The plan carries its test
lines apart, and the prompt names the declared test paths.

| Spec | Round 1 | Round 2 | Size |
|---|---|---|---|
| `SA-0333` | 0B 3C 4N | not run | 60 lines, measured |

The draft took 21 minutes, with a prototype measured by `size_gate`. The
review took 4. The delegate applied round 1's ceiling concern and two notes in
place, and ran no second review. No blocker was found, and the edits changed
two numbers and added a member to one set.

## Each finding by class

- **An arrangement argued rather than run.** Two concerns, on criteria 2 and
  3. The writer ran criterion 4's whole-cell arrangement against its
  prototype, and argued the other two. The reviewer found no hole by reading.
  Left for the cell's own witness and REVIEW, and named in the PR.
- **Size or ceilings.** The third concern. `max_turns` sat 29 turns above
  `SA-0327`'s 171, which was a floor, since that cell hit its ceiling. Raised
  to 240, and `budget_usd` to 44 for the REVIEW and REBUT headroom note.
- **A witness drives one member of its set.** One note. Criterion 1 drove
  omission, -1, 2.5 and one over, but not `null`. Added, with a wrong
  version.
- **A claim about the tree that stopped being true.** One note. A prompt
  sentence said test lines are taken off first, which is false where a repo
  declares no test paths. Qualified.
- **A self-reported discount.** One note, recorded only. The operator chose
  the arm, and `size` still judges the diff.

## What the pre-flight missed

Check 7 compared `max_turns` with a peak the history line itself calls a
floor. A pre-flight line for check 7: a ceiling above a floor by less than a
fifth is a concern, since the floor is the least that cell needed.

Check 10 asks for each arrangement to be run. The writer ran one of three.
Running the other two needs the witness written against the prototype, which
is most of the cell's test work.

## What the run itself changed

`SA-0330` now names `SA-0333` as its parent, at the operator's call. Without
it, a batch scans `SA-0330` first, since both are priority 1, and it would end
`PLAN_REJECTED` again.

The same edit replaced `SA-0330`'s bare citation `saffron/cell/session.py:3774`
with the call it names. `SA-0333` changes that file above the line. No
construct opens there, so the batch could not move the citation, and the bare
line would drift unchecked (b-b664d1).
