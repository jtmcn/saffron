# Spec chain feedback, 2026-10-20

Five items from run 45's ranked list went through the chain at base
`e8f5529e`. The operator settled one arm each up front, in a single
question round.

- **b-998bb7.** The fix sits in `.saffron/gates/prose.py`, which is
  protected, so it landed by hand as #924, with no spec.
- **b-08a36a.** `SA-0298`, merged as #926.
- **b-e40d09.** `SA-0299`, merged as #925.
- **b-589cf6.** `SA-0300`.
- **b-8a0c9a.** Six specs, `SA-0301` to `SA-0306`. Its first writer split it
  into five at step 1, and the fifth writer split again.

`SA-0300` to `SA-0306` ship as one pull request, with this record.

| Spec | Round 1 | Round 2 | Size |
|---|---|---|---|
| `SA-0298` | 1B 3C 5N | 1B 2C 4N | 248 tokens, measured |
| `SA-0299` | 0B 2C 6N | 0B 4C 5N | 944 tokens, measured |
| `SA-0300` | 0B 0C 5N | none | 776 tokens, measured |
| `SA-0301` | 1B 3C 4N | 0B 1C 6N | 1644 tokens, priced |
| `SA-0302` | 0B 6C 3N | 0B 3C 5N | 2128 tokens, measured |
| `SA-0303` | 1B 3C 4N | 0B 2C 4N | 1772 tokens, measured |
| `SA-0304` | 0B 5C 4N | 0B 5C 2N | 1120 tokens, measured |
| `SA-0305` | 0B 5C 7N | 0B 5C 4N | 1580 tokens, measured |
| `SA-0306` | 1B 0C 4N | 0B 2C 4N | 1500 tokens, measured |

Drafts took 16 to 30 minutes, and a split report took 4 to 8. Revisions took
1 to 14 minutes, and each review took 3 to 7. Every spec stopped at two
rounds. Round 2's fixes went in through the writer or by the delegate's hand,
with no third review. Only `SA-0300`'s first review found nothing to fix.

## Each finding by class

- **The delegate's own protected edits.** The largest class, at 11 findings.
  They hit `SA-0299` (5), `SA-0301` (1), `SA-0305` (3), `SA-0306` (1) and
  `SA-0298` (1). Each hand edit to `DESIGN.md`, `CONTEXT.md` or an ADR
  either missed a sentence the change makes false or claimed more than the
  spec did. Twice it was "spends both shares" or "runs its follow-ups",
  where the code runs them only on `DRAINED`. Pre-flight 12 names this
  class. It ran as a reading, and the reading missed each time.
- **A witness that drives one member of a set.** 9 findings, across
  `SA-0301`, `SA-0302`, `SA-0303`, `SA-0304`, `SA-0305` and `SA-0306`.
  Each writer ran a prototype and probed its wrong versions. The reviewers
  still found members no row drove: a write that raises once the directory
  exists, a guard that catches `OSError` alone, and a stack base whose branch
  is gone.
- **A child drafted while its parent moved.** 7 findings. The parents were
  drafted and reviewed in parallel with their children, so the children
  carried stale names and shapes. The cases were a field name the parent
  never fixed, `StackReview.fields` as the parent's first draft had it, and
  in-cell findings given the graded head after `SA-0303` kept them on the
  packaged one. `SA-0306`'s blocker made its declared mutant the correct
  code. The memory note from 2026-10-07 says to draft children after the
  parent's prototype exists. Parallel drafting here bought hours and cost
  these rounds.
- **A doc outside `touches` the change makes false.** 4 findings:
  `CLAUDE.md:30`, `CLAUDE.md:77` and `:82`, and a sentence in
  `create-saffron-spec`. Pre-flight 6 reads tests that enumerate a
  directory. It reads no prose that describes a command's behaviour.
- **A design gap the brief never named.** 6 findings, each settled by the
  delegate without the operator:
  - a bottom layer's range taking in a newer `main`;
  - a merged bottom layer graded as an empty diff;
  - a resume rewriting the night's row;
  - an outage using up a batch's only finish;
  - in-cell concerns moving to the graded range;
  - the follow-up gate reading a status the row rewrites.
- **The delegate's brief was wrong.** 3 findings. `SA-0302`'s "known gap"
  was a gap that did not exist. `SA-0304`'s turn ceiling was under a past
  peak. `SA-0305`'s retry over `error` rows would have paid and then raised
  on the ledger's primary key. The writers caught all three before review.
- **Ceilings.** 5 findings. The thin cases all trace to one row: `SA-0162`
  is a runaway and set the budget floor for its shape (b-206d2c).

## What the delegate did by hand

- **Protected edits.** 17 hand edits across `DESIGN.md`, `CONTEXT.md`, ADR
  3, ADR 4, ADR 7 and two skills. Reviews found errors in 11 of them.
- **Restacks.** Each restack hit the queue smoke test's pins and the
  origin item's `specs:` line. A scratch script unioned both. One `&&`
  after a piped `tail` let a failing test reach a commit, which was then
  amended.
- **Prose.** Three writers reported `make check` at exit 0 on drafts the
  commit hook refused. That is b-08a36a itself, which `SA-0298` fixes. From
  the fourth brief on, writers staged their files and ran the hook before
  reporting, and no later draft carried a hit.

## The next checks

1. **A protected edit is reviewed before the spec's first review.** The
   delegate's edits drew more findings than any other class. A
   `spec-reviewer` pass over the hand edit alone, grepped for the changed
   term across `DESIGN.md`, `CONTEXT.md` and `docs/adr`, would catch most.
   The cheaper form is a driver command that prints each sentence in those
   files naming the changed identifier.
2. **Children are drafted after the parent's second review.** Seven
   findings came from parallel drafting. Draft a child once its parent's
   contract is settled, and hand the writer the parent's final text.
3. **Pre-flight 6 reads prose that names a command.** For each command or
   file a spec changes, grep `CLAUDE.md`, `README.md`, `docs/agents` and
   `.claude/skills` for its name.
4. **The writer brief always says to stage and run the prose hook.** It
   costs one line and removed the class from every later draft.
