# Rejections

`DESIGN.md` §8's flywheel input, for this repo as a target of itself. One line of
*why* per rejection, triaged into exactly one bucket, and what became of it.

**Reread this monthly, not weekly.** At 6–12 pull requests a week you get 2–6
rejections; week-over-week accept rate on n≈8 swings ±20 points from two tasks
and means nothing. The reading is a habit, not a report — each reread appends
its own dated section at the bottom.

**Buckets, cheapest first** (`CONTEXT.md` §9). **1** a gate, if it is mechanically
checkable. **2** a line in `CLAUDE.md`, if it is judgement the agent could apply
given context. **3** a critic lens amendment, if it is a defect class gates cannot
catch. A rule's whole life is a migration toward bucket 1.

**Every entry dated before 2026-09-09 is backfilled**, reconstructed from
`git log --grep='^review-fix(SA-'`, the eight-pull-request table in
`docs/superpowers/plans/2026-09-07-trusting-the-queue.md`, and the backlog items
each round filed. They were not written at rejection time. A record that does not
say which of its lines came after the fact has the same defect as an estimate
stored in a column named for a measurement.

**Landings are one of three words**, so a reread is a grep (§8): **Landed** — a
gate's name, or a backlog item marked done; **Open** — with the item that tracks
it, if one does; **Inert** — landed somewhere nothing reads. **No bucket** marks a
rejection that names a mechanism which does not exist: it becomes a spec, not a
rule, and *exactly one of three* is not available for it.

**Adding one:** append under today's date — one line of why, the bucket, and its
landing. An entry dated on or after 2026-09-09 was written when the rejection was.

---

## 2026-09-04 — `SA-0045`, `SA-0048` (fixes landed via #123)

- Two tests named a behaviour they did not guard, and the adequacy lens showed
  neither would have noticed the code being wrong.
  **Bucket 1** — **Landed:** `witness`, which mechanises exactly this question;
  declared by `SA-0058`, which found it built and reachable by nothing. Item 80 is
  why a spec author still cannot declare a mutant safely.
- A preflight failure that takes the whole batch down was skippable by its caller.
  **Bucket 2** — `error` ≠ `fail` is already a `CLAUDE.md` invariant, and this is
  the judgement it exists to supply. **Landed:** the line every phase reads, from
  `fix(session): the implementer never saw the repo's CLAUDE.md, so bucket 2 had
  no reader` (IMPLEMENT) and `fix(review): no lens was shown the invariants it
  judged a diff against` (the lenses).

## 2026-09-05 — `SA-0055` (#131)

- An assertion guarding the regression could not see it.
  **Bucket 1** — **Landed:** `witness`.

## 2026-09-05 — `SA-0056` (#135)

- The guard against a moved tree was dead for the default mutant.
  **Bucket 1** — **Landed:** `witness`.

## 2026-09-05 — `SA-0057` (#136)

- A `return` inside a `finally` swallowed the operator's Ctrl-C, in a core gate.
  **Bucket 1, and the gate does not exist.** ruff selects `B`, and B012 does not
  see a `return` nested inside a `try` inside a `finally`. CPython 3.14 does: this
  was the only file under `saffron/` emitting
  `SyntaxWarning: 'return' in a 'finally' block`. **Open:** item 96 — which found
  the obvious gate would pass in the cell, whose interpreter is 3.12 and has no
  such warning.
- The fix for the swallowed interrupt was itself unwitnessed — three branches
  mutated to `pass` with the file green.
  **Bucket 1** — **Landed:** `witness`.

## 2026-09-05 — `SA-0058` (#139)

- A pre-flight probe's docstring claimed it proved subset filtering when it proved
  only tolerance, so `witness` reported `pass` for a claim nothing checked.
  **Bucket 3** — a claim the code does not support is the contract lens's subject.
  **Open.**

## 2026-09-05 — `SA-0060` (#148)

- "could not restore" was said about a mutant that was never applied — the loudest
  thing that gate says, said falsely.
  **Bucket 3** — correctness. **Open.**

## 2026-09-06 — `SA-0058` (#139), after its review-fix

- `witness` is built, wired, and cannot run — the `tree` it needs does not exist
  in a cell.
  **No bucket** — a missing mechanism, not a rule. **Landed:** item 71. The plan's
  footnote credits items 71–73 to `SA-0059`; item 71 itself says it was found
  reviewing #139, and the item is the primary record.

## 2026-09-06 — `SA-0060`, second round (#148)

- The commit that corrected four comments left three wrong, one of them twenty
  lines above its own correction.
  **Bucket 1, partly built** — a citation guard exists, and shipped shadowing 347
  of the citations it claimed to check (corrected 2026-09-09). Prose that no guard
  reaches is item 87's class. **Open:** item 87.

## 2026-09-06 — `SA-0061` (#150)

- Half of §5.6's elevation rule went unguarded — the by-path half, which is the
  one an operator is most likely to hit.
  **Bucket 1** — **Landed:** `witness`.
- Four comments the `witness` wiring falsified, and no queued spec can reach them.
  **Bucket 1** — item 87's class. **Open:** item 75.
- An agent has no channel to record a fact it is forbidden to fix.
  **No bucket** — a missing mechanism, not a rule. Became `SA-0063` and
  `SA-0064`. **Landed:** item 74.

## 2026-09-06 — `SA-0062` (#154)

- A failed write left the worktree truncated, and a mutant unrestored: two
  critical fixes on one diff, against **0 blockers** from REVIEW.
  **Bucket 3** — and the rejection that turned the lens itself into something
  measured: item 79 built the fixture corpus and a baseline of `3/12`, which
  measures the lens without amending it. **Open:** item 79.
- `witness` mutates before `committed` runs, and the spec that built it says the
  opposite.
  **Bucket 1** — done in code; the `DESIGN.md` sentence is still owed.
  **Open:** item 78.

## 2026-09-07 — `SA-0063` (#158)

- The mutant a witness is judged by is withheld from the prompt and left in the
  worktree.
  **Bucket 1** — **Open:** item 80. #166 landed the detection (item 85); stripping
  the worktree copy waits on a decision about which copy is authoritative.
- The guard against a spec refused on its own criteria never sees 31 of 53 specs.
  **Bucket 1** — **Landed:** item 81, 2026-09-08. The diagnosis was wrong and the
  fix landed anyway.
- A mutant can pin the text a spec dictates or the text an agent writes, never
  both.
  **Bucket 1** — **Landed:** item 82, 2026-09-08 — `intake.py` refuses such a
  mutant at parse.
- A mutant that matches at the base commit kills the task before it starts.
  **Bucket 1** — **Landed:** item 83, #166. The eight-pull-request table does not
  attribute this one to a round; it is placed with its cluster.
- `revert` judges a witness whose subject the spec forbids.
  **Bucket 1** — **Landed:** item 84, #166. Arrived through the notes channel item
  74 built, in `SA-0064`'s own `notes.json` — the first rejection this repo
  collected by mechanism rather than by hand.

## 2026-09-07 — `SA-0064` (#160)

- A test's name promised one claim and it makes two, so a maintainer deleting the
  second half is pointed at the wrong phase.
  **Bucket 3** — naming a test for what it proves. **Open.**
- The host runs one copy of a spec and the cell reads another.
  **Bucket 1** — **Landed:** item 85, #166.
- The notes channel's two rendering-side safety properties are unwitnessed.
  **Bucket 1** — `witness`. **Open:** item 86.

## Round not recorded — prose cluster

- Two prose claims about the core gate set went stale where no guard reaches.
  **Bucket 1** — **Open:** item 87. No round in the record attributes it; a
  rejection whose pull request cannot be cited is itself worth noticing.

---

## First reading — 2026-09-09

*Corrected 2026-09-10.* The first version counted five entries open whose items
had landed on 2026-09-08 (81–85 — read off the backlog's tier index, which keeps
done items, rather than their Status lines), omitted item 71's entry, said nine
specs for eleven, and dated `SA-0062` a day late. The counts below are
re-derived from the file — `grep -c '^  \*\*Bucket 1'` and its siblings, and
`grep -c` on each bolded landing word. The item-96 paragraph was added the same
day.

The backfill's own output, and the first time §8's two heuristics have been read
off counts rather than impression. Twenty-four rejections across eleven specs.

| Bucket | Count | |
|---|---:|---|
| 1 — a gate | 17 | 10 landed (5 by `witness`, 5 as items 81–85), 7 open |
| 2 — `CLAUDE.md` | 1 | landed in every phase |
| 3 — a lens | 4 | all open |
| No bucket | 2 | both became work, both landed |

**"If most rejections keep landing in bucket 3, your gates are too weak" does not
fire.** Seventeen of twenty-four are mechanically checkable, and ten of those
seventeen have landed. Bucket 1 is where rejections close. The seven it leaves
open are a queue, and the backlog ranks one of them (item 80) tier 1.

**Bucket 3 is the one that has not moved.** Four entries, none landed. Item 79
made the lens measurable — a corpus and a `3/12` baseline — which is the
precondition for amending one, not an amendment.

**Bucket 2 has one entry and it is inert.** Item 7 means no rejection can be
answered by a `CLAUDE.md` line today, so the middle of the flywheel is not merely
underused — it is disconnected. One sample is not a rate, but the count cannot
grow while the bucket has no reader.

**One bucket-1 destination was named here and filed nowhere** *(added
2026-09-10)*, and filing it (item 96) found that the obvious version is a trap.
CPython 3.14 names the Ctrl-C defect at compile time. Ruff's four `finally` rules
don't, and neither do CPython 3.12 or 3.13 — and the cell runs 3.12.14. A compile
gate declared the ordinary way would pass the one defect it exists to catch.

**`witness` is the flywheel working, and it has a cost.** Five rejections about
tests that guard nothing were answered by one gate, which is §8's `revert`
precedent repeating. Wiring it produced rejections of its own: items 71, 78, 80,
82, 83 and 84 are each `witness` unable to run, mutating in the wrong order, or
judged by a mutant that cannot be declared safely. Four of the six have landed;
78's `DESIGN.md` sentence and 80's stripping are open. That is not an argument
against promotion — it is the cost of it, and it belongs in the reading rather
than in a footnote.
