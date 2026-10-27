# Spec chain feedback, 2026-10-26

Run 48's loop ranked three items for Saffron to absorb next. All three went
through the chain at base `068862d9`. Three writers drafted in parallel, one
worktree each.

- **b-1b05be.** `SA-0320` (#973): the finish drops an in-cell concern whose
  cited line changed between the packaged head and the graded head.
- **b-009d51.** `SA-0321` (#974): a stack batch rewrites a citation whose
  construct moved to one place, rather than refuse the spec.
- **b-b9365d.** `SA-0322`: a host-filed survivor stays a blocker, and its
  claim names the tests the whole `tests` gate failed under its edit.

| Spec | Round 1 | Round 2 | Round 3 | Size |
|---|---|---|---|---|
| `SA-0320` | 0B 3C 3N | 0B 1C 5N | none | 128 tokens, measured |
| `SA-0321` | 1B 3C 4N | 1B 3C 3N | none | 1280 tokens, estimated |
| `SA-0322` | 2B 2C 3N | 2B 4C 6N | 1B 7C 2N | 289 tokens, measured |

Drafts took 19 to 32 minutes. Revisions took 9 to 22, and each review took
3 to 8. `SA-0320` stopped at two rounds. Its round-2 notes were applied by
hand. `SA-0321`'s round-2 blocker was settled by the writer running every
wrong version on its prototype, in place of a third review. `SA-0322` was
redesigned after round 2, so its round 3 read a new design.

## Each finding by class

- **A witness drives one member of its set.** The largest class again, with
  4 blockers and 6 concerns or notes. `SA-0321`'s held set had no member for
  a file the later commit adds, which is run 48's own case. Its added
  tie-break had one fixture, whose clause order also fit the wrong rule.
  `SA-0322` named one killing test where its claim said each.
- **The design fails its own motivating case.** A new class, found once and
  caught once. `SA-0322`'s first design downgraded a survivor that the whole
  suite killed, and voided the kill on a new failure in any other gate. I
  applied `SA-0313`'s false-blocker edit at `a0ec477e`, and `ruff format
  --check` failed on it. So the design kept its own example a blocker. The
  operator then chose evidence over a downgrade. `SA-0321`'s writer ran the
  same check before review. Two of ten one-place rewrites would have moved a
  use-site citation onto a definition, so the scope narrowed before round 1.
- **`error` collapsed into a pass.** 1 blocker. `subtract_baseline` reads
  failures only, so an errored gate read as clean in `SA-0322`'s round 2.
- **A rule added in a revision, with no witness of its own.** 2 findings.
  `SA-0321`'s shorter-construct rule and `SA-0322`'s other-gates step each
  arrived in a revision, and each drew a blocker in the next round.
- **A wrong version that dies on the stub, not an assertion.** 2 concerns,
  both on `SA-0322`. The fix was a stub that answers `pass` after its
  script ends.
- **A protected sentence that says more than the build.** 3 concerns,
  across `SA-0321`'s ADR 7 amendment and `SA-0322`'s `DESIGN.md` and
  `CONTEXT.md` sentences.
- **A data flow the spec did not pin.** 2 findings. `SA-0321`'s `revise`
  route could receive the unrewritten text. `SA-0320`'s later diff had to
  be read before the first qualification row was recorded.
- **Stale prose in a forbidden file.** 4 notes, each named in Out of scope.
- **An arrangement argued rather than run.** 3 concerns. Each was settled
  by the writer rerunning its prototype, never by another review.

## What the run itself got wrong

- **My brief overclaimed.** I told `SA-0321`'s writer that run 48's defects
  each moved to exactly one place. The writer measured it and found that
  untrue for `SA-0315`.
- **I first chose a downgrade without testing it on its own case.** The
  measurement that killed it took one command, and it came after two
  review rounds.
- **The first push was blocked.** Opening a spec PR is not covered by a
  loop's push grant, and the operator granted it for this chain.

## What should change

1. **Run the item's own evidence through the prototype before review.** A
   new pre-flight check. It caught two wrong rewrites in `SA-0321` before
   any review, and its absence cost `SA-0322` two rounds.
2. **A rule a revision adds gets the claim-against-witness check again.**
   Pre-flight 1 runs on the draft today, and not on what a revision adds.
3. **Every wrong version is run on a prototype, and the spec says which
   assertion kills each.** Three reviews asked for this as a concern.
