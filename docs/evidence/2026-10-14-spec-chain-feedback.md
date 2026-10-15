# Spec chain feedback, 2026-10-14

One item went through the chain at base `841a62e1`: b-4901d2, filed the same
day from the spec loop's run 39. It became `SA-0293`. The delegate settled a
verdict reserve on top of REBUT's $10 cap, never carved from it, because the
fixes on `SA-0272` spent $9.49.

| Spec | Item | Round 1 | Round 2 | Measured tokens |
|---|---|---|---|---|
| `SA-0293` | b-4901d2 | 0B 3C 5N | 0B 3C 2N | 576 |

The draft took 25 minutes, and the revision took 11. Round 1 took 7 minutes
and round 2 took 3. Round 2's findings were one sentence each, so the
delegate applied them by hand and checked that the spec still loads.

## Each finding by class

- **Two criteria disagreeing on one input.** Three findings across both
  rounds. A verdict cut after a refused extraction carried the extraction's
  error. Two cut sessions left "the cut verdict" ambiguous. Criterion 3 said
  without condition that a failed verdict ends unjudged, while criterion 2
  cut a later lens. The pre-flight's check 2 read pairs of claims, but not
  the cases a revision added.
- **A wrong version argued rather than run.** Round 1 asked for every wrong
  version of criteria 2 and 3 to be run. The writer's prototype killed each
  one, so the class cost a revision and found nothing.
- **A quoted figure that did not add up.** $6.41 and $3.08 leave $0.51 of $10,
  not the $0.56 the draft said. The verdict started with $0.51 and spent
  $0.56. Check 5 resolves citations, not arithmetic over measured figures.
- **A refusal's text naming the wrong pool.** Round 2 found that the verdict
  pool's refusal would name the $10.00 cap. No check reads error text against
  the line it lands in.

## What the delegate did by hand

- Edited `CONTEXT.md`'s `EXHAUSTED` entry, which the writer flagged as partly
  false once the verdict has its own reserve.
- Applied round 2's three one-sentence fixes to the spec and DESIGN §5.6.
- Confirmed the SA-0272 figures from the batch log before the revision.

## The next checks

1. **Re-read every claim pair after a revision adds cases.** Check 2 runs
   once, on the draft. Each new case is a new input both claims must answer.
2. **Re-add every sum a spec quotes.** A figure built from two measured ones
   should be recomputed in the pre-flight, as a count is.
3. **Name which session's error a line carries when two sessions fail.** A
   spec that rewrites a line built from several sessions should say which
   one wins.
