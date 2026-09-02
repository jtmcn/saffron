# Splitting a spec that is too wide for one repair loop

**Status:** design, approved in conversation 2026-09-01. Not yet a plan.

A spec whose diff cannot fit one repair loop currently discovers this by
running out — of turns, of budget, or of attempts — and ends `EXHAUSTED` with
its work stranded. This design lets a cell **propose child specs** instead, at
two points, and lets the host render them into real spec files the operator
ratifies with a commit.

## The problem, measured

Nine specs into v0.5's first real batch, this is the most expensive recurring
failure the factory has.

| spec | what happened |
|---|---|
| `SA-0020` | split into `SA-0020` + `SA-0022`; the gate and the stacking could not ship together |
| `SA-0022`, `SA-0025` | both split mid-flight |
| `SA-0029` | plan checkpoint rejected 1100 estimated lines against `feature`'s 600, at $2.20. Split **by hand** into `SA-0029` + `SA-0040` |
| `SA-0029` (shipped) | 548 changed lines in the cell, **885** after two host-side review rounds (the 863 in the first draft does not reproduce under `size._changed_lines`) |
| `SA-0040` | **974** after review; the in-cell figure is three recorded `size` results — 306, 658, 683 — not the single 671 the first draft cited |
| `SA-0031` | plan estimated 850 against `refactor`'s 1000 — accepted. Died at 141 turns of 140, **$19.17 of an $18.00 budget**, 6 commits, gates red, no branch pushed, no pull request |

`docs/BACKLOG.md` item 25 already records the failure class, and item 40
records the review-round half of it.

## What already exists, and why it did not fire

`saffron/agents/artifacts.py:269` rejects a plan whose own `estimated_lines`
exceeds the ceiling for its type (`gates/core/size.py:25` — `bug` 300,
`feature` 600, `refactor` 1000). It works: it is what stopped `SA-0029`.

For `SA-0031` it did not fire, and the reason matters more than the first draft
of this document claimed. The estimate was **850** against a ceiling of
**1000**, so the plan was accepted.

The first draft then said the incomplete patch was "1174 lines", concluded the
estimate was 38% too low, and reasoned from there. That number is `wc -l` on a
diff — it counts context lines and hunk headers. Run through
`size._changed_lines`, the function the ceiling is actually enforced with, the
same patch is **481 lines**, and the ledger agrees: `SA-0031`'s own `size` gate
recorded *"481 changed lines within the refactor ceiling of 1000"*.

So the estimate was **77% too high**, not too low, and the run died with the
diff at less than half its ceiling. Which kills one of the two conclusions and
strengthens the other:

- ~~A plan-time check catches an honest over-estimate and misses an optimistic
  one.~~ **Withdrawn.** `SA-0031`'s estimate was pessimistic and the check still
  let it through, because the estimate was never the problem.
- **The binding constraint is not the diff.** `SA-0031` was comfortably inside
  its line ceiling and outside every other one — 141 turns of 140, $19.17 of
  $18.00. A line-based ceiling is measuring the wrong thing, and the mid-flight
  trigger is not a backstop for a bad estimate; it is the only trigger that
  watches the constraint that actually binds.

## Decisions

1. A too-wide spec produces **child specs**, not merely a better refusal.
2. A split may be proposed at **two** points: the plan checkpoint, and the
   moment a run would otherwise end `EXHAUSTED` with commits in hand.
3. On a mid-flight split the branch is **pushed with no pull request**. Red work
   is preserved without ever being called reviewable.
4. The **host renders** the child spec files; the **operator commits** them.
   Nothing queues until that commit exists.

Decision 4 is forced as much as chosen: `.saffron/**` is `protected`, so a cell
cannot write a spec file. The proposal must arrive as an extracted, hashed
artifact — the rule `plan.json` and `SA-0018`'s scope proposal already follow.

## The artifact

`split.json`, extracted and hashed the moment it is produced, never re-read
from `/work`.

```
{
  "why": "...",
  "children": [
    { "title":    "...",
      "touches":  ["..."],
      "criteria": [ {"criterion": 1,
                     "claim":     "...",
                     "witness":   "tests/test_x.py::test_y"} ],
      "context":  "...",
      "notes":    "..." }
  ],
  "dropped": [ {"criterion": 7, "why": "..."} ]
}
```

### Who decides what

| Field | Author | Why |
|---|---|---|
| `id` | host | the cell cannot see the ledger and must not choose numbering |
| `depends_on` | host | a chain from `children` order, newest parent in slot 0 |
| `forbidden` | host | the parent's, **plus every other child's `touches`** |
| `type`, `priority`, `risk` | host | inherited from the parent |
| `budget_usd`, `max_attempts`, `max_turns` | host | inherited **unchanged**, not divided |
| `touches`, `criteria`, `witness`, prose | agent | the semantic half |

`forbidden` gaining the siblings' `touches` is what stops child 1 wandering
into child 2's files and re-creating the diff the split existed to cut.

Ceilings are inherited rather than halved because the ceiling is a per-spec
bound, not a pot being divided. `SA-0031` needed more than $18 and 140 turns;
two children at $9 and 70 turns would reproduce the failure exactly.

### Criteria are conserved

Every acceptance criterion in the parent is claimed by **at least** one child,
or appears in `dropped` with a reason.

*At least*, not exactly one — corrected by the dry run below. Some criteria are
invariants rather than work: "the terminal output does not change" and
"`run_one_cell` stays callable with no `emit`" must hold for **every** child,
and assigning them to one would let the other break them. `intake.Criterion`
already models this and the first draft of this design did not: `preserves:
true` marks a criterion whose witness is checked **green at both sides** rather
than red-at-base and green-at-head. So the partition is over the criteria that
are *work*, and `preserves` criteria are copied to every child. Without this, "split this spec" becomes a
way to shed the criteria that were hard — which is the failure to expect from a
turn that has just spent 141 turns failing them.

`dropped` is not a quiet exit. `ratify` prints every dropped criterion and its
reason before it writes anything, because a criterion the factory decided not
to meet is the single thing in a split an operator most needs to see. It is not
an error: a criterion can be genuinely obsolete. It is a thing said out loud.

### Every criterion names a witness

`saffron/gates/core/criteria.py` states its contract in one line: *a test by
this name ran at head and passed, and if it existed at base it was not green
there.* That is red-to-green, enforced as a gate, fed by an `acceptance:` block
in frontmatter (`intake.py:45`). It shipped in `SA-0011`.

The first draft said "nothing uses it", which is false. `SA-0011`, `SA-0012`
and `SA-0013` all declare `acceptance:`, and the ledger holds a passing
`criteria` result — attempt 7, `SA-0013`, *"3 criteria witnessed at head"*.
`SA-0013` is a working model, and its two `preserves` witnesses name tests that
actually exist.

What is true is narrower: **no spec written in this batch declares one**, so
every one of `SA-0029`, `SA-0040`, `SA-0030` and `SA-0031` ran with the gate
inert. And the observation that "every baseline reads `criteria=skip`" is true
but proves nothing — at baseline the prior side is empty, so the gate always
skips. It was evidence of nothing.

It is aimed at exactly what went wrong. Twice in one evening a criterion was
satisfied only by a comment or an inert test: `SA-0040`'s `FAMILIES` table
asserted itself (deleting three rows passed 67 tests), and `SA-0030`'s AC8 test
passed with the phase seam severed at all six call sites (218 tests green).
Both were caught by an independent review that could as easily have missed
them.

So a proposed child's criteria each carry a `witness`. The children arrive with
the `criteria` gate **live** rather than skipping. This also acts as a forcing
function on the proposing turn: it must name the test it intends to write.

### The four host checks

Run before anything is rendered, all reusing code that exists:

0. **a claim may be rewritten, and check 2 runs against the rewrite.** The dry
   run proved this is not optional: running `_unmatched_criterion_path` over
   the parent's criteria *verbatim* against each child's `touches` refuses four
   of them, and one — the parent's sweep over all seven test files — is
   unreachable from *either* child, so no assignment of it survives. A split
   that may only inherit claims is a split that cannot be made
1. each child's `touches` ⊆ the parent's — no scope growth through splitting
2. each child's criteria are reachable from its own `touches`
   (`scheduler._unmatched_criterion_path`, the gate-0 function)
3. the criteria partition is total — every parent criterion claimed or dropped
4. every claimed criterion names a witness — and the witness's file is **not**
   required to be in that child's `touches`. A `preserves` criterion names a
   test that already exists and must stay green; the child never edits it. Only
   the paths a criterion's *prose* cites are checked against `touches`, which is
   what check 2 already does

A proposal failing any check ends the run `SPLIT_REFUSED`. There is no second
attempt, for the reason a rejected plan gets none: re-asking is negotiating.

## The two triggers

### Plan time

The plan turn today ends two ways — a plan, or a scope proposal
(`ScopeProposed`, `artifacts.py:47`, from `SA-0018`). It gains a third,
`SplitProposed`, reusing the same extraction-and-hash path.

The existing ceiling rejection becomes a split. Today `estimated_lines >
ceiling` raises `PlanRejected` and the run dies having paid for the checkpoint
with nothing to show — which is precisely what `SA-0029` cost at $2.20 before
being split by hand. Under this design that condition asks for a split instead.
`PlanRejected` survives as the last resort for a turn that returns an
over-ceiling plan anyway.

### Mid-flight

**One** trigger point: the moment a run would end `EXHAUSTED` with commits in
hand. That single boundary covers budget exhaustion, attempt exhaustion and
no-progress, and it is where `SA-0031` died. The turn is the salvage turn
`SA-0028` already added, with its trigger widened and `split.json` added to
what it may emit.

Deliberately **not** a trigger: the turn ceiling firing mid-run. `SA-0031`'s
fired and the run correctly carried on to the gate loop. Only the terminal
boundary knows the spec was genuinely too wide.

### The split turn is exempt from the spend ceiling

At the mid-flight boundary the budget is gone by definition — `SA-0031` was at
$19.17 of $18.00. A split turn gated on remaining spend would fire never. It is
therefore exempt, capped separately, and its overspend recorded as its own
line rather than hidden. The cap is a single figure the plan must pick and
justify from measurement. `SA-0029`'s rejected plan turn cost **$2.2030**,
exactly; `SA-0030`'s cost **$2.347**. `SA-0031` has no separate plan row at all
— its two attempts are $5.99 and $13.18 — so the honest starting point is
roughly one plan turn, around $2.50, not a fraction of a budget.

This is not a new principle. `cell/session.py:45` already states that REVIEW is
"deliberately not gated on the spend ceiling — a green diff nobody reviewed is
not a product." The argument holds harder here: the split proposal is the only
thing that makes the money already spent recoverable.

## States, and the branch

Two new states, both `DONE` — re-running the parent learns nothing, because it
has been superseded:

- **`SPLIT_PROPOSED`** — a valid proposal passed all four checks
- **`SPLIT_REFUSED`** — a proposal failed one. The branch is pushed here too:
  the work is no worse for the proposal being malformed, and stranding it
  would re-create the defect this design exists to remove

On `SPLIT_PROPOSED` the branch is **pushed with no pull request**: `pushed_sha`
set on the task row, `pr_url` left `None`. `SA-0031`'s row carries
`pushed_sha: None` today, which is why $19.17 of work exists only as a
`patch.diff` nobody will open.

### Child 1 absorbs; it does not stack

The obvious wiring breaks. `_resolve_stacked_on` makes PACKAGE open a child's
pull request **against the parent's branch**, and a `SPLIT_PROPOSED` parent has
red gates and no pull request of its own — so nothing in that stack could ever
merge.

So child 1's worktree is cut from the parent's branch while its pull request
targets the **default branch**. The parent's commits become part of child 1's
diff and are reviewed as one unit; the parent branch is then deleted. Child 2
stacks on child 1 in the ordinary way.

**This is a new concept and it reverses a shipped invariant. The first draft
said the opposite and was wrong.** `SA-0022`'s `tree_base` is not "the diff
base" as against `base_sha`: *every* diff in the system is measured from
`tree_base`, and `base_sha` is only the pin for exporting `.saffron`, protected
paths and retirement markers. The pull request's target is neither — it is
`target_branch`, which `cli._resolve_stacked_on` returns **paired** with
`stacked_on` and hands to `package(parent_branch=...)`.

That pairing is the invariant. `package`'s own docstring says a worktree
stacked on a sha whose pull request targets the default branch "is exactly the
defect this spec exists to close (`SA-0026`)" — and absorbing is precisely that
combination. It is still the right call here, because a `SPLIT_PROPOSED` parent
has no pull request for a child to target, so `SA-0026`'s defect (a child's
diff re-applying its parent's hunks against a base that will merge separately)
cannot arise. But it must be built as a deliberate, named exception with its
own test, not slipped in as "one new combination".

### Exit code

`SPLIT_PROPOSED` exits **1**. Exit codes are load-bearing and this design adds
no fourth: `0` means there is a pull request to review, and after a split there
is none until ratification. The state carries the distinction, as
`RATE_LIMITED` and `EXHAUSTED` already do behind the same exit.

## Ratification

```
$ uv run saffron ratify SA-0031 --repo .
re-validated against main @ 5c8f30e
  wrote .saffron/specs/SA-0041-the-agent-stream-becomes-events.md
  wrote .saffron/specs/SA-0042-package-events-and-the-fan-out.md
         depends_on: [SA-0041]
  marked SA-0031 retired-by SA-0041

review the diff, then commit. Nothing queues until you do.
```

`ratify` reads `split.json`, **re-runs all four checks against the current
tree**, renders the spec files, retires the parent, and stops.

Retirement is **not** the `saffron:retired-by` marker, though the first draft
said it was. `repos/mirror.py:32` excludes `.saffron/specs` from the marker
grep — *"a spec file is where a marker is discussed; it is never where one
lives"* — so a marker written into the parent's spec file is invisible, and one
written anywhere else names a path the child's `touches` must reach or
`scheduler.retirement_refusal` refuses the child. The dry run found the working
shape by accident: a prose `## Status: superseded` block and a move to
`.saffron/specs/done/`. That is what `ratify` should do. It does not commit,
push, or queue.

The re-validation is not ceremony. Every measured figure in the first batch
went stale within hours: `SA-0031`'s eleven `watch=watch` keyword sites became
eight while a cell was running, and the operator-visibility plan's ledger
figures moved three times in one evening. A proposal made at $19 and ratified
the next morning is measuring a tree that has moved.

Numbering is the highest `SA-` id across `.saffron/specs/` **and** `done/`,
plus one.

## Testing

The parts where this would rot:

- each host check gets a test with a proposal violating exactly one — above all
  the criteria partition, since a proposal that quietly drops the hard criteria
  is the expected failure
- a child cut from a `SPLIT_PROPOSED` parent opens its pull request against the
  **default branch** while its worktree carries the parent's commits.
  `SA-0022`'s bug had this shape and it has already recurred once
- the split turn runs when the budget is already over, which is the only
  condition it fires under
- no new test carries the `cell` marker; `addopts` excludes those, and a
  skipped assertion has twice been mistaken for a passing one

## Out of scope

**Making the estimate accurate.** The plan-time estimate will stay optimistic;
this design routes around that rather than fixing it. If it were reliable, the
mid-flight trigger would be unnecessary — and it is the mid-flight trigger that
recovers the money.

**Automatic ratification.** A cell's proposal deciding what the factory builds
next is the boundary `CLAUDE.md` says never moves inside.

**Splitting an already-merged spec.** Retrospective decomposition is a
different problem with no cell in it.

**Two ceiling defects `SA-0031` surfaced**, which want their own backlog items
rather than this design:

- a single turn can overshoot the budget ceiling, because `_over_budget` is
  checked *before* a turn and `SA-0031`'s final turn cost $13.18 on its own
- an `EXHAUSTED` run that made commits pushes no branch, so its work survives
  only as `patch.diff`. `SA-0028` fixed the zero-commit door; this is the one
  beside it

## The dry run

`SA-0031` was split by hand on 2026-09-01, deliberately following this design's
shape before any of it was built. Three findings, all folded in above.

**The cut came from a coupling argument, not a file grouping — which is the
evidence for the agent proposing it.** `saffron/phases/package.py` looks like it
belongs with its three sibling phase modules, and it does not: `package()` is
called from `saffron/cli.py`, outside `run_one_cell`, so its events cannot reach
the log until `cli.py` builds the fan-out. The two must ship together. Meanwhile
both `_phase_watch` constructions exist *only* for the other three phases, so
the adapter dies with them. Approach C — the host grouping files by directory —
would have made exactly the wrong cut, and cheaply.

**The children are the first specs in this repo to declare `acceptance:`.** That
is the point, and it is also a warning: it forces the spec to name the test node
ids the implementation will create, before it exists. Prescriptive, and the
forcing function is the value — but a proposing turn will find this the hardest
field to fill honestly, and a plan should expect the first proposals to name
witnesses that drift from the tests eventually written. The gate catches that as
a failure, which is the right outcome and an expensive one.

**Counts do not conserve.** `SA-0031`'s 12 criteria became 9 + 5 = 14, because
invariants repeat across both children and criteria spanning two subsystems
split. A host check asserting `sum(len(child.criteria)) == len(parent.criteria)`
would refuse every honest split.

**And the first cut of the split silently dropped one.** The parent required
that no `watch=` remain anywhere under `tests/`; neither child claimed it, and
the arithmetic in this section concealed it — "two invariants and one split"
predicts 15, not 14, and nobody noticed the missing one until review. That is
the exact failure host check 3 exists to prevent, committed by hand while
writing the check. It is the strongest argument in this document for automating
the conservation check rather than trusting a careful author.

**An obligation with no possible witness belongs in `## Notes`, not in
`acceptance:`.** Two of the children's criteria named witnesses inside
`cell`-marked files, which `addopts` excludes from the `criteria` gate's
collection — so they could never be collected at head and would have blocked
every attempt. The `criteria` gate can only witness what the default suite
collects; everything else is a note.

## Open question

Whether `refactor`'s 1000-line ceiling is right at all. It is the widest in the
table and the only one a spec has passed on its way to `EXHAUSTED`. Worth
re-deriving from the measured spread once a few more specs have run, rather
than adjusting it on one data point.
