# Spec chain feedback, 2026-10-27

Run 49's loop ranked what Saffron should absorb next. This chain took the
three ranked items that have backlog records, at base `5a9ee6d7`. The
adequacy lens item, ranked third, has no record yet and was skipped.

- **b-781ea4.** `SA-0325`: a follow-up draft that does not parse goes back
  to its writer once. The send-back is one closure, `send_back(reason)`.
- **b-549012.** `SA-0326`: `saffron review` reads a task's review commits
  with the end review's per-layer lenses.
- **b-e0044f.** `SA-0327`, stacked on `SA-0325`: the finishing layer leaves
  out a follow-up whose cell ran, and a draft the finishing suite fails goes
  back through `send_back`.

The operator settled two design arms before any writer ran. A draft meets the
prose bar through the repo's own gates and one send-back, with no gate policy
change. The review commit reader is a new command, not a flag on `regate`.

| Spec | Round 1 | Round 2 | Size |
|---|---|---|---|
| `SA-0325` | 0B 5C 3N | 0B 2C 2N | 175 tokens, measured |
| `SA-0326` | 2B 5C 3N | 0B 3C 3N | 1972 tokens, estimated |
| `SA-0327` | 1B 5C 4N | 0B 3C 4N | 840 tokens, estimated |

Drafts took 19 to 30 minutes. Revisions took 8 to 11, and each review took
5 to 7. Every spec stopped at two rounds. The last round's findings were
applied in place, with no third review.

## Each finding by class

- **A witness drives one member of its set.** Both of `SA-0326`'s round-1
  blockers. A restack fixture held one commit with the packaged subject, so
  a subject-only match passed. Thirteen declines shared one assertion, so a
  dropped decline fell through to the next one and still passed.
- **A seam the child cannot reach.** `SA-0325`'s first seam took the first
  prompt and the caller's `write`, which exist only inside the loop. Its
  round 1 asked where the child would call it. The fix moved pricing, the
  log line and the charge into the closure.
- **A promise split across parent and child.** `SA-0327`'s round-1
  blocker. `SA-0325` handles a raise from the second `write` at its call
  site, not inside `send_back`. The child cited the seam as if the closure
  held the `try`.
- **A loop variable read by a closure.** `SA-0325`'s round 2. The closure
  read the loop's `session`, so a second parse failure could charge the
  first session twice. `ty` also widened the captured name. Both were
  settled by running the prototype.
- **Infrastructure repeated per group.** `SA-0327`'s judge raise pooled
  only its own group, so a broken image would buy one writer session per
  group. It now pools every later group, as a reset time does.
- **A protected sentence that goes false.** `DESIGN.md:472` and ADR 7 each
  described the old finishing layer. Both were amended by hand in
  `SA-0327`'s pull request.
- **A claim about the tree.** `SA-0325` counted a docstring at nine lines,
  and the `prose` gate counts ten. `SA-0326`'s renumbering left one stale
  criterion number.
- **A framing witness the template already satisfies.** `SA-0326`'s round
  2. Both end review templates print the range line, so the assertion was
  pinned to the spec's own slice of the prompt.

## What the pre-flight missed

The pre-flight has no check for a parent's seam as the child will call it.
Three of this chain's findings sit on that boundary: the seam's reach, its
`try`, and its loop variable. A check would read the child's call site
against the parent's text before the parent's first review.

The size reading needed one settlement. `size` leaves declared test paths
out (`saffron/gates/core/size.py:275-288`). `preflight.md` check 7 says to
count the touched files with `wc -l`, which reads tests too. Read that way,
`SA-0326` would have split for no reason.

## What the run itself got wrong

Auto mode refused the spec branches' first push, so the pull requests opened
only after the operator granted it.
