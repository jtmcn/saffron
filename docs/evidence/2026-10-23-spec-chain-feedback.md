# Spec chain feedback, 2026-10-23

The top four items from run 46's ranked list went through the chain at base
`af2831e8`. The operator chose them and settled four design arms.

- **b-0bd346.** `SA-0311`: REBUT earns one repair turn when only form gates
  went red. The repo declares a form gate with `form: true` (§2.1).
- **b-1572e7.** `SA-0312`: a child stacks on its deepest open parent.
- **b-619b7d and b-066901.** Split twice at step 1, into `SA-0313` (adopt
  re-gates, then moves the task), `SA-0315` (`ready_task` takes a layer cut
  from a review commit) and `SA-0316` (a PACKAGE raise closes the batch
  `INFRASTRUCTURE`).
- **b-2da959.** Split into `SA-0314` (the core checker) and a driver half.
  The driver half lives in `.claude/`, which the queue refuses as a touch.
  It lands by hand on `SA-0314`'s cell pull request, so `SA-0317` is unused.

The six specs ship as one stack, `SA-0311`, `SA-0314`, `SA-0312`, `SA-0313`,
`SA-0315` and `SA-0316`, bottom to top.

| Spec | Round 1 | Round 2 | Size |
|---|---|---|---|
| `SA-0311` | 0B 6C 4N | 1B 4C 3N | 1624 tokens, measured |
| `SA-0312` | 0B 6C 4N | 0B 6C 4N | 1512 tokens, measured |
| `SA-0313` | 1B 4C 5N | 2B 4C 3N | 2236 tokens, priced |
| `SA-0314` | 5B 2C 3N | 0B 2C 4N | 804 tokens, measured |
| `SA-0315` | 1B 4C 6N | 0B 3C 4N | 1120 tokens, measured |
| `SA-0316` | 3B 4C 4N | 1B 5C 2N | 1580 tokens, measured |

Drafts took 22 to 46 minutes, and a split report took 5 to 7. Revisions took
9 to 25 minutes, and each review took 5 to 9. Every spec stopped at two
rounds. Round 2's fixes went in through the writer, and the delegate read
each result instead of a third review. No first review came back empty.

## Each finding by class

- **A witness drives one member of its set.** The largest class again, at
  14 findings across every spec. Examples: one list marker of three, one
  closing bracket of three, no unmarked `PackageError`, a fixture with one
  task per spec. Writers who ran each wrong version on a prototype closed it
  in revision. Writers who reasoned about them did not.
- **An infrastructure fault comes out as a refusal.** A new class, at 6
  findings. A failed `ls-remote`, a `merge-base` exit 128, an unreadable
  mirror and a caught `RateLimited` each turned `error` into `fail`. Every
  spec that added a git or network call drew one.
- **The delegate's protected edits.** 8 findings. Hand edits to
  `DESIGN.md`, `CONTEXT.md` and ADR 7 broke an antecedent twice, left the
  base out of its own chain, and claimed `reconcile` follows `MERGE_FAILED`.
- **A change's meaning reaches past `touches`.** 4 findings. Adopt
  rewriting `pushed_sha`, which the end review reads as PACKAGE's commit.
  The batch's rechecks, and `saffron finish`'s resume seed, which no spec
  owned (b-e39286).
- **Two paths answer one input differently.** 3 findings: `saffron batch
  --stack` against `saffron finish`, and the scan against `run_task` on
  which parents are open.
- **The delegate's brief was wrong.** 4 findings. "No re-run after a failed
  repair turn" broke §4.3's rule that a cut turn is still judged. A
  `.saffron/policy.yaml` key cannot land before the loader knows it. A
  `.claude/` touch is refused by the queue, twice.
- **An arrangement right only by accident.** 2 findings, both in
  `SA-0315`'s fixture: every git object was local, and one branch head was
  unpinned.
- **A change breaks a live test.** 1 finding: a new `Policy` field fails
  the setup template's field test.

## What the delegate did by hand

- **Splits.** Three writers stopped at step 1 on size. Each split cost 5 to
  7 minutes and saved a draft over the ceiling.
- **Protected edits and policy keys.** `SA-0314`'s pull request lands the
  `citations` key, its loader test, the setup template and this repo's
  declaration, so the cell builds only the checker.
- **Restacks.** A scratch loop resolved every conflict, all in the queue
  smoke test's pins and the origin items' `specs:` lines.
- **Stale bytecode.** `SA-0314`'s writer found its own runner reusing a
  stale `.pyc`, so a mutant could run the previous mutant's code. Every
  writer re-ran its wrong versions with `PYTHONDONTWRITEBYTECODE=1`. All
  163 still die on an assertion. One probe in `SA-0312` had matched nothing
  until it was fixed.

## The next checks

1. **Every new git, `gh` or network call names what an outage returns.**
   The new class. A pre-flight line per call, saying which exits raise and
   which refuse, would have caught all six.
2. **A brief's decisions are read against `DESIGN.md`'s principles before
   dispatch.** Run 47's one design blocker came from the delegate's own
   decision.
3. **Writers run wrong versions through one guarded command.** `driver.py
   probe` already clears bytecode. A `driver.py wrongs <spec> --root
   <prototype>` that applies each listed version would replace six ad hoc
   runners.
4. **Pre-flight 6 reads the queue's own refusals.** A `.claude` touch, or a
   new `Policy` key, is visible before the writer starts.
