# Stack batch: one batch runs the spec DAG into one PR stack

Date: 2026-09-23. Decision record: ADR 7.

## Intent

The operator starts one run and returns to one linked PR stack and a summary.
The delegate works through every queued spec with little operator input. It
comes to the operator only for a major concern. Review findings become specs,
and those specs run inside the same batch. Each task hands its branch to the
next task. Nothing merges on its own (§1.4).

Success is measured by what the delegate still does by hand. Each run's
feedback file lists those steps, and the list shrinks run by run.

## What exists at `c915d801`

- `saffron batch` rescans its queue after every task (`SA-0106`). A child is
  admitted once its parent reaches `READY_FOR_REVIEW` (§4.2 gate 1).
- `task._resolve_stacked_on` cuts a child from its parent's pushed branch.
  PACKAGE opens the child's PR with `--base` set to that branch.
- A spec with no `depends_on` is cut from the default branch. So a batch
  produces siblings, and the skill's step 4 chains them by hand.
- The delegate pushes `review(SA-NNNN)` commits between cells. No gate,
  critic or record reads them (backlog items 40 and 97).
- `GOTCHAS.md` still says `run_batch` resolves its candidates once. That line
  is stale since `SA-0106`.

## Decisions taken in the design session

1. Follow-ups come from one review at the end, and land on top of the stack.
2. One generation of follow-ups, fixed. A second generation needs an ADR that
   amends ADR 7, so the exception to §1.4 keeps a stated bound (principle 29).
3. A task that misses `READY_FOR_REVIEW` is skipped. Its descendants are
   refused. The batch goes on.
4. Spec review runs inside the batch. `build` and `witness` blockers get up
   to three revise rounds. A `scope` blocker skips its spec and escalates.
   The batch never pauses.
5. The end review is the Spec and Standards seats per layer, plus one lens
   over the joins. Host code decides which findings qualify.
6. The whole flow lives in `saffron batch --stack`. It is built in an order
   that passes through a delegate-assisted stage first.

## 1. The handoff, and how the chain is recorded

**The order is planned once, at batch start.** Stack mode orders the queued
specs as `driver.py snapshot` does: parents first, then priority, then id.
Each entry pins its `spec_sha`. A child whose parent sits earlier in the same
plan counts as admissible, although the parent has no task yet. Stack mode
does not rescan the spec directory. Follow-ups are the only later additions,
and they append at the top.

**Each task is cut from the head of the task below it.** That task is its
**predecessor**. "Parent" keeps its one referent, `depends_on[0]` (principle
26). The batch resolves the predecessor's pushed branch and sha. It hands them
to `run_task` as the existing `(stacked_on, target_branch)` pair, in place of
`_resolve_stacked_on`'s derivation. PACKAGE then opens every PR against the
branch below it. A declared parent always sits below its child, so the child's
tree holds the parent's code.

**A dependency outside the plan refuses the spec.** This covers every
`depends_on` entry, not only `depends_on[0]`. A dependency at
`READY_FOR_REVIEW` in an earlier, unmerged stack never enters this plan.
Cutting the spec from a predecessor would drop that code, so stack mode refuses
it with a reason naming the dependency. It runs once that stack merges.

**A composite's members stay contiguous.** The order keeps them together. The
last member's tree still carries every layer below the composite. So the
composite review's range starts at the first member's predecessor head, and
the layers below it are its base (ADR 7 narrows ADR 6 here).

**The predecessor is the last task at `READY_FOR_REVIEW`.** A task in any
other state adds no layer. The next task starts from the same head the failed
one used. Each `depends_on` descendant of the failed task is refused with a
reason that names it.

**Gate 0's open-PR overlap check exempts the batch's own tasks.** Every lower
layer's PR is open and often touches nearby files. Without the exemption,
stack mode refuses its own second task. Backlog item 59 exempted a
declared chain, and no item covers a stack's layers yet.

**Recording.** A ledger table `stack_layers` holds `batch_id`, `position`,
`spec_id`, `task_id`, `predecessor_task_id` and `generation`. Generation 0 is
a queued spec, and generation 1 is a follow-up. Under item 170's direction, a
record fact carries the same row and the ledger folds it. The driver's `stack`
and `status` read this table in place of `.saffron-loop/order.json`.

**Unchanged.** Each cell takes its baseline on its own starting tree, the
predecessor's head (§4.4 step 2). A batch without `--stack` behaves as today.

## 2. The end review, and which findings qualify

**When.** A stage of stack mode. It starts once the last generation-0 task
settles, and before any follow-up is written. It reads the stack as it stands
and rebuilds no layer.

**The seats become lenses.** `review.py` runs host-invoked lenses from prompt
files (`LENSES`, `run_lens`), each a fresh session in a critic cell. The Spec
and Standards seats become two lens prompts in `saffron/agents/prompts/`.
Core owns them, and they name no repo file or tool. The Standards lens reads
the standards documents a repo declares in `.saffron/`, and none when it
declares none (principle 41). It reads them from the `base_sha` export, never
from the layer's head, which that layer's agent could have written
(principle 43).
They run once per reviewable layer, in a critic cell seeded at that layer's
head. The host fills the template fields from the ledger. A layer's `{BASE}` is
its predecessor's head. `{KNOWN}` is that layer's in-cell findings and its
`rebuttal.json`. Each field is filled once, and a filled value is never
expanded again (principle 22).

**One lens reads the joins.** It reads the top layer's tree with the whole
stack's range, under ADR 6's rubric:

- a name one layer uses and another layer produces.
- a name a layer produces and no later layer uses.
- work a layer redoes that an earlier layer already provides.

**Qualification is host code.** Each finding from the seats, the join lens,
and each layer's in-cell `concern` passes these steps in order.

1. **Anchored** (principle 15), as `CONTEXT.md` defines the word: inside a
   hunk, or citing a line that names an identifier the diff changed. For the
   join lens, the stack's combined diff counts. One rule for every producer
   (principle 28). An unanchored finding goes to the backlog pool.
2. **Probed.** A finding with a `{file, find, replace}` probe runs through
   `saffron/probe.py` against that layer's tree, as REBUT does
   (`apply_probe_verdict`), under ADR 3's kill rule. A killed probe drops the
   finding. A surviving probe qualifies it. An errored probe, or a find that
   matches other than once, sends it to the backlog pool marked unverified.
   A finding with no probe skips this step. The Standards lens, two parts of
   the join rubric and most correctness findings carry none (principle 28).
3. **Severity.** A qualified `blocker` or `concern` feeds a follow-up. A
   `note` goes to the backlog pool.
4. **Grouped.** Qualified findings group by layer and by the files they
   touch. Each group becomes one follow-up spec.

**Output.** Each finding and its outcome is a record fact. That gives the
skill's `labels.json` and the rejections evidence a machine source.

**Money.** The batch reserves the end review's budget at start. REVIEW spend
is not checked while it runs (§5.5), so the stage cannot rely on the budget
gate. When the reserve runs short, the review covers layers from the top down.
A layer it did not reach, or whose lens errored, shows as unreviewed in the
summary, never as clean (principle 34).

## 3. Writing and reviewing specs inside the batch

**Where they run.** Spec writing and spec review become host-invoked
sessions in a critic cell. The cell is seeded at the tree the spec would be cut
from. The writer never writes into `/work`. Its spec returns through the
extraction turn and is hashed on arrival, as a plan is. The spec review's
tags return through their own extraction turn too (principle 18). Both prompts are core's,
in `saffron/agents/prompts/`, and so are the tags blockers route by. A target
repo supplies none of them (ADR 2). This repo's `.claude/agents/spec-writer.md`,
`spec-reviewer.md` and the skill's `REVIEW-PROMPT.md` stay the hand path's
own. They name this repo's tools, so they differ from core's by design.

**Queued specs are reviewed before their cells.** At batch start one spec
review runs per queued spec, up to K at once. A spec's first cell waits only
for its own review. Blockers route by their tag.

- `build` or `witness`: the writer revises, and a fresh spec review reads the
  whole spec again, beside the original. Up to three rounds. Each round walks
  the earlier concerns and names the wrong implementation the edit must kill.
  A changed purpose the fresh review finds routes as `scope`, since the tag
  that allowed the revision is a claim (principle 15).
- Every revised spec passes gate 0 and `parse_spec`'s refusals again before
  its cell (principle 54).
- A revised spec's cell holds the base text at the spec's path. The implement
  prompt carries the revision, and core's gates read the host's parsed copy.
  Writing the revision into `/work` would put a protected path in the task's
  diff, so the stale file stays. A repo gate that reads `.saffron/specs/`, as
  `dead` reads `pending_symbols`, still sees the base text. So can the
  implementer and the criterion session (principle 20, item 85).
- `scope`, or no tag: the spec and its `depends_on` descendants are skipped
  and escalated.
- Still blocked after round three: the spec and its descendants are skipped
  and escalated.
- A concern that a criterion's witness cannot be measured routes as
  `witness`.
- Other concerns and notes go to the backlog pool.

**Follow-ups take the same chain.** For each qualified group, the writer
receives the findings with their anchors and probe results. It also receives
the layer's spec and diff, a `touches` list from the anchored files, and the
origin spec's budget as a ceiling. It writes a `bug` or `feature` spec with no
`depends_on`. It never declares the named probe as its own mutant, since
`parse_spec` refuses a mutant whose text appears in the body (ADR 3). Each
follow-up then passes the same review and routing, and runs as generation 1.
Its own critic's criterion probe, named by a fresh session, is the check on a
cell that kills only the named edit (ADR 3, principle 6).

**Edited and new specs live in the record until the finish.** The batch never
writes the operator's working tree. A revised queued spec or a new follow-up is
a record fact with its text and `spec_sha`, and the cell runs that text. The
finishing layer commits the files. A follow-up takes the next free `SA-` id
across both spec directories and the ledger.

**The host enforces a follow-up's fields.** The writer's `touches`, budget and
risk tier are claims. The host refuses a follow-up whose `touches` reaches past
its anchored files and their tests, or whose budget exceeds its origin spec's.

**Money.** Spec work draws on the same start-of-batch reserve. Writing costs
about six times a review, measured on the writer and reviewer chain. So the
writer has its own sub-cap. Once it is spent, the remaining groups go to the
backlog pool.

## 4. Finishing the stack, escalations, and the delegate

**The finishing layer.** After the follow-ups settle, the batch adds one layer
on top with no model involved.

- It commits the revised and new spec files.
- It moves each spec with a reviewable layer to `specs/done/`
  (`RETIRED_DIRNAME`). The move sits in the top layer, so the scan sees it
  only once the operator merges the stack.
- It writes the backlog pool to `findings.json` in the batch tree.

`.saffron/specs/` is protected. The host writes these files, never a cell, and
ADR 7 names that exception. The repo's gate suite runs on the finishing tree in
a cell before any push. A red suite escalates in place of a push, so no host
commit reaches a PR unread (items 40 and 97).

The finish runs from its own reserve, so it runs after `--until` passes too.
Otherwise specs that ran in cells would never be committed (principle 16).

**Backlog filing stays with the delegate for now.** Backlog records,
`rejections.md` lines and origin-item status are this repo's conventions, not
core's. A program core runs that is not a gate would break ADR 2. So the
delegate files them from `findings.json`, in a PR on top of the stack. A
declared program that does it is a later decision, once the delegate's time on
it is measured.

**Linking.** Each PR already targets the branch below it. The finish compares
each layer's recorded predecessor head with that branch's current head. A hand
push to a lower layer mid-batch shows as a mismatch and escalates (principle
21). It then reads every base back and runs `gh stack link`. With `--ready` it marks each layer
ready. A wrong base leaves every PR a draft. Nothing merges.

**Escalations never pause the batch.** Each is a record fact and a line near
the top of the queue page. These escalate:

- a `scope` blocker, or a spec still blocked after three rounds.
- a halt: a cell that stopped at a ceiling with nothing decided.
- a gate other than `prose` that fails at base.
- a red suite on the finishing layer.
- a base that reads back wrong at link time.

**A rate limit waits.** In stack mode `RATE_LIMITED` does not count toward the
breaker. The batch sleeps until the cell's `resets_at` or `--until`, whichever
comes first. It then runs the same task again on the same predecessor. The
limit is the account's, so the next spec would meet it too.

**The summary.** The morning queue page gains a stack view with a section per
layer. Each section shows spec review rounds, the terminal state, spend against
budget, turns against ceiling, and the PR. It adds the findings with their
outcomes, and `size`. A batch section shows the order, total spend against
budget, outcomes, escalations and detours. The delegate's HTML summary asks
for each of these, and here each is a fact. The delegate publishes the page as
its Artifact.

**What the delegate still does.**

1. Start `saffron batch --repo . --stack --budget N --ready` with the token
   scoped to the command.
2. Follow it with `saffron watch`, and send a push notification per
   escalation.
3. File the backlog from `findings.json`, in a PR on top of the stack.
4. Publish the summary.
5. Write the run's feedback file, whose items are the steps that still needed
   a hand.

The skill shrinks to about a page. Each `driver.py` command retires once its
job moves into core.

## Testing

Stack mode is tested as `run_batch` is, with a fake runner and a real ledger.
Each rule gets a witness that fails at base. The rules are the handoff, the
skip past a failed layer, the overlap exemption, qualification, the rate-limit
wait, and the finish refusing a wrong base. A first live batch runs two or
three small specs before any full run.

## Build order

One spec per step. Each step ships usable on its own.

1. Handoff and `stack_layers`.
2. The overlap exemption.
3. The seat lenses and the join lens.
4. Qualification.
5. The rate-limit wait.
6. Spec review in the batch.
7. Spec writing and follow-ups.
8. The finishing layer.
9. The stack view on the queue page.

Steps 1 to 5 run through today's loop. From step 6 on, each step shortens the
loop that builds the next one.
