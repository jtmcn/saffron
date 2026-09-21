---
name: create-saffron-spec
description: Turns a backlog item into a Saffron spec a cell can run, through the writer and reviewer agents, and drives the review rounds to a stop. Use whenever a backlog item should become a spec, when a spec review comes back and its findings need answering, when asked to write, revise or review an `SA-NNNN` spec, and when asked to run the spec chain or the spec creation loop. Use it even when the request names only an item id or says "turn 117 into a spec", because the pre-flight it runs is what keeps the first review from finding anything.
---

# Create a Saffron spec, and leave the first review nothing to find

A spec review costs 6 to 13 minutes and a revision costs 12 to 22. A defect the
review finds is paid for twice, once by the reader and once by the writer. A
defect a cell finds is paid for in dollars and an hour.

Most of what eight review rounds found on 2026-09-20 was computable before any
reviewer read a word. This skill runs those checks first. Then it reads the
design the way a reviewer would. A first review with nothing to find has to
find no design question either.

**The target is a first review with no findings.** Read that as a measurement
rather than a slogan: every run records what the first review found, and a
finding no pre-flight check catches is the next check to build.

## The chain

Each step says what it is for. Skip one when the reason does not apply, and say
so in the record.

### 1. Choose the item and the base

The item is a `docs/backlog/` record. Read it with
`uv run python -m records show <id>`, and read every record in its `related:`.

The base is the commit a cell would cut from. Use `origin/main` unless a queued
spec this one overlaps is unmerged, in which case cut from that spec's branch
and expect a `depends_on`.

Cut a branch: `git checkout -b joel/spec-<short-slug> <base>`.

### 2. Build the brief, and verify it

A brief is a citation. Read every fact at the base before handing it over. A
writer has no reason to doubt a brief, and carries what it says into the spec.

On 2026-09-20 a brief said a file sat in `forbidden` when a review commit had
moved it to `touches` hours earlier. The spec carried the error to its review.

### 3. Pre-flight the item

Two questions decide whether one spec is the right shape, and both are cheaper
now than after a draft.

- **Size.** Estimate from real files with `wc -l`, against
  `saffron/gates/core/size.py`'s ceiling for the type. An estimate inside 100
  lines of the ceiling splits into a parent and children.
- **Overlap.** A queued spec whose `touches` intersect yours is your parent.
  `saffron queue --repo .` reads the mirror at the pinned `base_sha` and cannot
  see an unmerged spec, so drive `build_queue` over the working tree instead.

### 4. Dispatch the writer

Use the `spec-writer` agent with `item:`, `base:` and a `decisions:` block.
`references/dispatch.md` holds the shape and what belongs in each field.

Settle in `decisions:` anything the writer would otherwise hand back: which arm
of a design choice to take, whether a split is allowed, which ceilings to
match. A decision left open returns as a question and costs a round.

### 5. Commit what it wrote

The reviewer reads at a commit, so the draft is committed before the review is
dispatched. Run `make check`. Then check each new file with
`python3 hooks/prose_limit.py --file <path>`. `make check` reads the staged
index, so an unstaged file passes it and fails the commit hook.

### 6. Pre-flight the spec

This is the step that earns the skill. `references/preflight.md` holds the
checks, each with its command and the findings it removes. Run them all before
any reviewer is dispatched, and fix what they surface.

The ones that catch the most, in the order that costs least:

1. **Claim against witness, per claim.** For every set a claim quantifies
   over, name the members and say which one the witness drives. This is the
   largest class by a wide margin.
2. **Criteria against each other.** Two claims that answer one reachable input
   differently is a blocker a cell cannot resolve.
3. **Every name the spec leans on.** The spec tells the cell to read, key by
   or compare fields, keys, units and paths. Each one exists at the base and
   means what the spec assumes.
4. **The data flow.** Every source the change reads from and every place it
   writes to is reachable from `touches`. A value the change needs from a
   `forbidden` file, or a location nothing passes it, is a blocker.
5. **Citations and claims about the tree.** Resolve every `file:line`, re-run
   every count, and read every "today" sentence at the base.
6. **What the change breaks.** Any test enumerating a directory the spec adds
   a file to. Any live check the spec's own fixtures would trip.
7. **Ceilings and size.** A per-part estimate against the ceiling, and the
   ceilings against cells of the same shape.
8. **The design.** Read the spec against `DESIGN.md` and the `protected`
   documents the way a reviewer would. An argument that rests on a section
   saying something it does not say is a finding here, not a review's job.

### 7. Dispatch the first review

Use the `spec-reviewer` agent with `spec:`, `base:` and `history: run it
yourself`. Tell it what the pre-flight already settled, and ask it for what the
pre-flight missed. Its findings are the pre-flight's misses, and step 10 records
each one against the check that missed it.

### 8. Answer the review, and stop

A review with no blocker and no concern ends the chain. Otherwise revise
through the writer, commit, and run a second review, telling it what the first
one found and which class the first one missed. A reviewer told the axis to
read for finds more than one told nothing.

Two rounds is the working stop rule. A third round means the spec's subject is
unsettled, which is a question for the operator rather than another review.

Every finding is verified at the base before it is applied. A review's premise
that does not hold is answered with evidence, not applied. Roughly one finding
in twenty is false, and applying one puts the reviewer's error into the spec.

### 9. Open the pull request

`.github/pull_request_template.md` is the body's shape, and `gh pr create
--body-file` skips the template, so write the body to a file first. Say in
**Not covered** what the pre-flight could not settle and what the reviews left.

### 10. Record the run

Append to `docs/evidence/<date>-spec-chain-feedback.md`: the rounds and their
cost, every finding by class, and for each one the pre-flight check that caught
it or the check that would have. That record is what makes the next run
cheaper, and it is the only thing that tells you whether this skill works.

## What the reviews keep finding

`references/findings.md` holds the corpus from 2026-09-20: four specs, eight
review rounds, and every finding classed. The shape of it:

| Class | Share | Caught by |
|---|---|---|
| A claim's witness drives one member of a set | largest | pre-flight 1 |
| A claim about the tree that stopped being true | large | pre-flight 5 |
| A name the spec leans on that the base lacks | medium | pre-flight 3 |
| A data flow the base cannot carry | medium | pre-flight 4 |
| Two criteria disagreeing on one input | small | pre-flight 2 |
| Size or ceilings | small | pre-flight 7 |
| A design argument the documents do not support | small | pre-flight 8 |

Every class has a check, the design class included. A pre-flight that leaves
design to the reviewer leaves the reviewer something to find.

## Keeping the skill honest

The record from step 10 is the input to the next change to this skill. After a
run, ask three questions of it.

- **Did a first review find anything?** Each finding is a check that did not
  run, a check that missed, or a class with no check. The third kind becomes a
  new check in `references/preflight.md`, beside the finding that motivated it.
- **Did a check cost more than it caught?** A check that finds nothing across
  several runs is prose. Prose nobody acts on is worth deleting.
- **Can a check become a command?** A check written as a paragraph gets skipped
  and drifts. `driver.py` carries `cite`, `enumerators` and `bookkeeping` for
  three of them. `references/preflight.md` says what each cannot see.

The skill is working when the checks it names are commands, the first review
finds nothing, and the record says both with numbers.
