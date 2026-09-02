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
| `SA-0029` (shipped) | 548 changed lines in the cell, **863** after two host-side review rounds |
| `SA-0040` | 671 in the cell, **974** after review |
| `SA-0031` | plan estimated 850 against `refactor`'s 1000 — accepted. Died at 141 turns of 140, **$19.17 of an $18.00 budget**, 6 commits, gates red, no branch pushed, no pull request |

`docs/BACKLOG.md` item 25 already records the failure class, and item 40
records the review-round half of it.

## What already exists, and why it did not fire

`saffron/agents/artifacts.py:269` rejects a plan whose own `estimated_lines`
exceeds the ceiling for its type (`gates/core/size.py:25` — `bug` 300,
`feature` 600, `refactor` 1000). It works: it is what stopped `SA-0029`.

For `SA-0031` it did not fire, and the reason matters for the design. The
estimate was **850** against a ceiling of **1000**, so the plan was accepted.
The exported patch is **1174 lines and incomplete** — the estimate was wrong by
at least 38%, and the run died on **turns and budget**, not on lines.

Two conclusions:

- A plan-time check against a self-reported estimate is necessary and
  insufficient. It catches an honest over-estimate and misses an optimistic one.
- The binding constraint is not always the diff. `SA-0031` was inside its line
  ceiling and outside every other one.

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
      "criteria": [ {"criterion": 1, "witness": "tests/test_x.py::test_y"} ],
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

Every acceptance criterion in the parent is claimed by exactly one child, or
appears in `dropped` with a reason. Without this, "split this spec" becomes a
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

Nothing uses it. Every baseline in the first batch reads
`criteria=skip` — the spec declares no witnesses — including all four specs of
part 1.

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

1. each child's `touches` ⊆ the parent's — no scope growth through splitting
2. each child's criteria are reachable from its own `touches`
   (`scheduler._unmatched_criterion_path`, the gate-0 function)
3. the criteria partition is total — every parent criterion claimed or dropped
4. every claimed criterion names a witness

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
justify from measurement — `SA-0031`'s plan turn cost $2.35 and `SA-0029`'s
rejected one $2.20, so the honest starting point is roughly one plan turn, not
a fraction of a budget.

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

This is the `tree_base` / `base_sha` distinction `SA-0022` already shipped
(`cell/session.py:199`) — the worktree is cut from one, the diff measured from
the other. No new concept, one new combination.

### Exit code

`SPLIT_PROPOSED` exits **1**. Exit codes are load-bearing and this design adds
no fourth: `0` means there is a pull request to review, and after a split there
is none until ratification. The state carries the distinction, as
`RATE_LIMITED` and `EXHAUSTED` already do behind the same exit.

## Ratification

```
$ uv run saffron ratify SA-0031 --repo .
re-validated against main @ 5c8f30e
  wrote .saffron/specs/SA-0041-the-four-phase-modules.md
  wrote .saffron/specs/SA-0042-the-fan-out-and-the-adapters.md
         depends_on: [SA-0041]
  marked SA-0031 retired-by SA-0041

review the diff, then commit. Nothing queues until you do.
```

`ratify` reads `split.json`, **re-runs all four checks against the current
tree**, renders the spec files, retires the parent with the
`saffron:retired-by` marker `SA-0027` built, and stops. It does not commit,
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

## Open question

Whether `refactor`'s 1000-line ceiling is right at all. It is the widest in the
table and the only one a spec has passed on its way to `EXHAUSTED`. Worth
re-deriving from the measured spread once a few more specs have run, rather
than adjusting it on one data point.
