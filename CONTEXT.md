# Saffron — terminology

The controlled vocabulary for Saffron. Every term used in a spec, a system prompt,
a PR body, a queue line, or `DESIGN.md` should appear here with one meaning.

**How this is used.** This is a host artifact — it lives in Saffron, not in any
target repo, so an agent inside a cell cannot follow a reference to it. It is
**injected into the system prompt, per phase, section by section** (`DESIGN.md`
§5.3). Each section below is tagged with the phases that receive it. Sections
tagged `—` are for the operator and the design documents only; nothing inside a
cell can act on them.

Only three phases appear in the table. REPAIR and REBUT resume the implementer's
session and inherit its sections; PACKAGE involves no model.

It is *definitional*, not behavioural — it says what words mean, never what to do —
so it stays out of `CLAUDE.md` and is exempt from the ~200-line budget in §8.
Rules of conduct belong in `CLAUDE.md`; rules of naming belong here.

`_Avoid_` lists are the load-bearing part. A synonym that reads as harmless in prose
is what makes two log lines, two prompts, and a ledger column quietly disagree.
They are written for the operator and the `terms` gate, and stripped at injection:
a prohibition puts the banned word in the prompt, so a cell sees only the headword.
A definition therefore never lives on an `_Avoid_` line.

| § | Section | Injected into |
|---|---|---|
| 1 | Core | DIAGNOSE · IMPLEMENT · REVIEW |
| 2 | Work | DIAGNOSE · IMPLEMENT · REVIEW |
| 3 | Scope | DIAGNOSE · IMPLEMENT · REVIEW |
| 4 | Verification | IMPLEMENT · REVIEW |
| 5 | Review | REVIEW |
| 6 | Outcomes | — |
| 7 | Repos | — |
| 8 | Artifacts | — |
| 9 | Flywheel | — |
| 10 | Style | DIAGNOSE · IMPLEMENT · REVIEW |
| 11 | Design record | — |

---

## 1. Core

**Saffron**: The orchestrator. A Python program running on the host that turns specs
into reviewable pull requests.
_Avoid_: "the system", "the tool", "the pipeline" (the pipeline is one part of it).

**Factory**: Saffron plus its gates, cells, and target repos, considered as a whole.
Use when talking about the arrangement rather than the program.
_Avoid_: "the platform", "the framework".

**Control plane**: The trusted host-side half — intake, scheduler, supervisor, gate
runner, packager, ledger. It decides what runs and whether the result is acceptable,
and never executes model-authored code.
_Avoid_: "the server", "the daemon", "the backend".

**Cell**: One task's isolation unit — a container plus its worktree volume, agent
state volume, and any fixture services. The cell is untrusted.
_Avoid_: "sandbox" — it implies the isolation boundary is the control, and in
Saffron it is not (the controls are structural and live outside the cell).
_Avoid_ also: "the container" when you mean the whole cell, "worker", "runner".

**Container**: The runtime primitive specifically — the object the cell runtime
creates and destroys. Use only when that object itself is the subject.

**Cell runtime**: The program that creates cells. `apple/container` — a VM per
cell — chosen in rev 10 against a four-assertion spike (Appendix G).
Say "the cell runtime". The seam is `saffron/cell/runtime.py`, which every caller
uses and which names no product at all; each runtime's own module under
`saffron/cell/runtimes/` names exactly one, and nothing else in `saffron/` may
name any. A decision made by spike can be remade by spike, and a second answer
is a second module rather than an edit spread through the tree.
_Avoid_: **"Docker"** as a generic term for it — that was a product name standing
in for an unmade decision through seven revisions, and naming a different product
generically would repeat the mistake. _Avoid_ also "the container engine", "the
VM" (a cell now *has* one, so the phrase is ambiguous), "the hypervisor".

**Worktree**: The git working tree a task edits, on a volume mounted at `/work`.
A cell contains a worktree; it is not one.
_Avoid_: "the checkout", "the clone", "the workspace", "the sandbox dir".

**Operator**: The human. Singular, by design.
_Avoid_: "the user", "the reviewer" (reviewing is one of several things they do).

**Target repo**: The repository a task modifies. Saffron is generic; the target repo
holds the specs, the policy, the cell image, and the repo's own gates.
_Avoid_: "the project", "the codebase", "the client repo".

**Agent**: Any model session inside a cell, when the specific role doesn't matter.
The ontology's `prov:Agent` is wider — it includes the operator, their delegates,
and every gate, which is a `prov:SoftwareAgent` there because it asserts
(`ontology/factory.ttl`, `DESIGN.md` §4.6). "Model" means a model identifier.
_Avoid_: "the AI", "the bot", "the LLM".

**Delegate**: A model session the operator starts on the host, outside any cell, to
act on their behalf, under their git identity and credentials. The factory neither
starts nor constrains it, and none of its work is recorded as a task's — the ledger
cannot tell it from the operator. It is never the operator: a ratification or
approval it types is still the operator's judgement. Plural, unlike the operator; a
delegate's subagents are delegates too, and every chain of them ends at the
operator.
> PROV-O's word, and PROV-O would call the implementer one as well — it too acts
> on the operator's behalf, directly or through a delegate, and both can work to a
> plan. What separates them is what holds them to it: the implementer's plan is a
> control artifact, validated outside its cell, and its work is recorded as
> attempts; a plan handed to a delegate binds only as far as the delegate follows
> it, and nothing records whether it did.

_Avoid_: "Claude Code" (a product standing for a role), "the assistant", "the
agent" (that is inside a cell), bare "session", "surrogate", and "the critic" or
"a lens" for a delegate's review.

---

## 2. Work

**Spec**: A markdown file with YAML frontmatter at `.saffron/specs/` in a target
repo. The unit of work, written by the operator.
_Avoid_: "ticket", "issue", "story", "request", "prompt".

**Task**: One spec being executed — a ledger row with a state, a branch, a budget,
and a cell. A spec is the input; a task is the execution. Its budget is a
**best-effort** bound: it is checked between attempts and an attempt's cost is
not knowable until the attempt ends, so a task admitted under its ceiling can
finish over it by up to one whole attempt — 67% on `SA-0059` (`DESIGN.md` §3).
In a batch, the bound that is actually enforced is the batch's, checked between
tasks (`DESIGN.md` §4.2.1) — itself exceedable by at most one task's overshoot,
since it admits a task on that task's declared ceiling. A task started by
`saffron cell` belongs to no batch, and its own best-effort bound is the only one.
_Avoid_: "job", "work item", "unit".

**Batch**: One night's execution, spanning every selected repo. One budget, one
concurrency pool, one `--until`.
_Avoid_: "session" (that means an agent session), "cycle", "sweep", "run".

**Batch stop reason**: `DRAINED`, `BUDGET`, `UNTIL`, `INFRASTRUCTURE`, or
`INCOMPLETE`. Why a night ended, written on the batch when it closes and absent
while it is still running — an absent one means in flight, not unknown. Never a
task's end state: these describe the night, and `DRAINED` says the queue emptied,
not that anything in it succeeded. `INFRASTRUCTURE` is the breaker firing, and
it is the only one of the five that says the machine rather than the work was
wrong. `INCOMPLETE` is a night that left a task in flight: that task reached no
end state, which is not the same as failing. It outranks the other ordinary
reasons, and `INFRASTRUCTURE` outranks it.
_Avoid_: "failed" for `INFRASTRUCTURE` (a task fails; a night stops), "finished",
"timeout" for `UNTIL`.

**Run**: One task's pin, owning the `base_sha` its gates and policy are read at, its
**preflight outcome** and its baseline. A batch holds one run per task. Every run of
one repo in a batch shares the `base_sha` the batch pinned for that repo. A stacked
task's tree and baseline sit on its parent's head instead, while its run keeps the
pin. `saffron cell` and `saffron replay` each mint a run that belongs to no batch.
The per-repo slice of a batch has no name and no row (backlog item 177).
> Batch and run are **not** synonyms and stopped being interchangeable when Saffron
> went multi-repo. Budget is a batch property; `base_sha` is a run property. If a
> sentence works with either word, it is imprecise.

**Preflight outcome**: What a run records when its first baseline suite ends: `PASSED`
or `FAILED`.
It lives in `runs.preflight`. A baseline that aborts in the cell writes `FAILED`, so
this is not the batch-start **Preflight** under Repos (backlog item 113). What a
NULL means is open (backlog item b-eac388).

**Phase**: A named stage in the cell pipeline — DIAGNOSE, IMPLEMENT, GATE ⇄ REPAIR,
REVIEW, REBUT, PACKAGE. Written in bare caps.
The event log alone splits GATE ⇄ REPAIR into GATE and REPAIR, because a gate
attempt and a repair turn print different lines. Everywhere else it is one phase.
_Avoid_: "stage", "step", "mode".

**Attempt**: One numbered execution of a phase. Attempts are bounded on five axes —
turns, spend, idle, completion, and wall clock. "Attempt 3" without a phase is
ambiguous — name both. A gate suite's number is the one exception: it counts the
gate suites judged in a task, so the suite re-run after REBUT continues the
repair loop's count — attempt 3, labelled REBUT, after a loop that reached 2.
_Avoid_: "iteration", "round", "pass", "retry", "try".

**Plan checkpoint**: The `plan.json` write and host-side validation that opens the
IMPLEMENT session. Deliberately *not* a phase — the planner and the implementer are
the same session.
_Avoid_: "the planning phase", "the plan step", "PLAN".

**Extraction turn**: A tool-less turn that resumes a session solely to emit a
validated `<output>` block. How every structured artifact is produced.
_Avoid_: "the JSON step", "parsing the output".

**Control artifact**: A host-consumed file an agent produces — `plan.json`,
`scope.json`. Extracted and hashed the moment it is written, never re-read from
`/work`. A control artifact left in the workspace is a claim, not a record.

**Refusal**: A task rejected before any cell starts — a duplicate open PR, an
overlapping in-flight change, a malformed or moved spec, a repo that failed
preflight. Costs nothing and reaches the queue as one line.
_Avoid_: "skip" (that is a gate status), "blocked", "reject" (that is what the
operator does to a PR).

---

## 3. Scope

**Envelope**: The loose outer bound a DIAGNOSE phase may read within. Declared by
the operator on bug specs; never enforced against a diff.

**Touches**: The set of paths a task may change. Declared directly on non-bug specs.
Proposed, then ratified by the operator, where the declaration cannot stand: by
DIAGNOSE on a bug spec, which has none, and by IMPLEMENT on any spec whose declared
set cannot satisfy its acceptance criteria. Once fixed it feeds the conflict set
and the `scope` gate.

**`scope` gate**: The check that changed files are a subset of `touches`, and
match neither the spec's `forbidden` list nor the repo's `protected` list.

> Never write bare "scope" as a noun. It reads as any of the three above and they
> are enforced at different times by different things. Say "envelope", "touches",
> or "the `scope` gate".

**Conflict set**: The in-flight `touches` sets a candidate task is checked against
before it is scheduled. Overlap within a repo means the task waits. File conflicts
are prevented by scheduling, not resolved by rebasing.
_Avoid_: "lock", "collision detection", "the overlap check".

**Forbidden**: Per-spec deny paths, declared in frontmatter.

**Protected paths**: Global deny paths, declared in the target repo's `policy.yaml`.
Distinct from `forbidden` — one is per-task, one is repo-wide.
_Avoid_: using either name for the other, or "the denylist" for either.

**Out of scope**: The prose section of a spec naming adjacent broken things the
agent must leave alone. Not machine-enforced; it reduces sprawl by being read.
_Avoid_: conflating with `forbidden`, which is enforced.

**Risk tier**: `standard` or `elevated`. Set on the spec, or raised automatically
when the diff touches a path in the repo's `elevate_on`. Elevated makes `size`
and `witness` blocking — the only two gates a tier moves (`DESIGN.md` §5.4.1) —
and marks the queue entry; it adds no lens, because every declared lens runs at
every tier (`DESIGN.md` §5.5.1). It does **not** make `coverage` blocking —
`coverage` is advisory at every tier (`DESIGN.md` §5.4).
_Avoid_: "priority" (a separate field), "severity" (that is a finding property),
"critical", "high-risk".

---

## 4. Verification

**Gate contract**: The interface that makes Saffron repo-agnostic. A gate is an
executable that emits one JSON object: `gate`, `status`, `tool`, `failures[]`,
`summary`. Nothing downstream sees tool output.

**`tool`**: The identifier a gate obtains *by executing* its tool (`ruff 0.14.2`),
and the only thing separating a gate that ran and passed from one that never ran
(Appendix H, `DESIGN.md` §5.4).
_Avoid_: "the version", "the tool name" — it is neither on its own, and a string
literal in a gate script is not a `tool` value at all.

**Gate role**: A name in the contract — `format`, `lint`, `types`, `tests`,
`no-network`, `coverage`. The repo supplies the executable; core supplies the
meaning.

**Gate**: One named verification, host-invoked and deterministic. Written lowercase
in backticks. Three kinds, and the distinction is the core/repo boundary:

- **Core gates** — `scope`, `size`, `secrets`, `integrity`, `census`, `committed`,
  `criteria`, `revert`, `witness`. Implemented in Saffron. Most read the diff;
  `committed` reads the worktree's status instead, and `census` and `criteria`
  read other gates' results. `revert` and `witness` are the two that run
  something, and §2.1's rule is shaped around them rather than broken by them:
  core invokes declared gates, never tools (`DESIGN.md` §2.1). `witness` is also
  the second gate a risk tier moves (§5.4.1); the rest sit at the level §5.4
  fixes for them.
- **Contract gates** — the gate roles above. Declared in `policy.yaml`, implemented
  in the repo's `.saffron/gates/`.
- **Repo-defined gates** — anything a repo adds against its own hard-to-fake
  surfaces, conditional on touched paths. Names vary by repo and are not vocabulary.

_Avoid_: "check", "validation", "CI" (there is no CI), "the linter" for the `lint`
gate. _Avoid_ naming any repo-defined gate here as though it were universal.

**Gate result**: One execution of one gate against one tree — an attempt's, or a
run's `base_sha` for the baseline. Exactly one of `attempt_id` and `run_id` is set
on the row, and the baseline is why (`DESIGN.md` §4.1).
_Avoid_: "gate run", or bare "run" — "run" means one task's pin.

**Gate suite**: Every gate executed as one unit against one tree — the core gates
plus the roles the repo declares. It has no identity of its own; name what it ran
against ("the baseline suite", "attempt 3's suite"). Two suites are what the
baseline subtracts and what `suite_drift` compares.
> Bare "suite" means the **gate suite**. A repo's own tests are always "the test
> suite", never bare, because the gate suite *contains* them — §7.1 times both two
> lines apart, and a bare "the suite is minutes" names the wrong cost.

_Avoid_: "gate run", as for a gate result.

**Suite comparison**: What judging a head gate suite against its baseline yields —
one of three things, checked in this order: a gate `error`ed, and whatever ran
the suite aborts — an attempt, or a package; the suites **drifted** (a gate
stopped running, or its `tool` changed), so no subtraction is to be trusted; or
the blocking new failures that remain.
_Avoid_: "verdict" — that is the critic's confirm-or-withdraw of a finding.
_Avoid_ also "the subtraction" for the whole: the subtraction produces only the
third outcome, and it is not even attempted when either of the first two holds.

**Status**: A gate result is `pass`, `fail`, `skip`, or `error`.
- `skip` — the repo declares no such gate. Not a failure; nothing is wrong.
- `fail` — the repo's code is wrong.
- **`error` — the gate itself broke.** Toolchain missing, service down, collection
  crashed. It aborts the attempt, is never charged to the task, and is what
  distinguishes "three flaky tests" from "the toolchain is broken" at preflight.

> `error` and `fail` are the single most important distinction in this section.
> Reserve the bare word "failed" for `fail`; say "errored" for `error`.

**Blocking / advisory**: A gate is one or the other. Blocking gates stop the task;
advisory gates are reported in the PR body and stop nothing. State which when it
matters — `coverage` being advisory is a design decision, not an oversight.
_Avoid_: "soft fail", "warning", "non-fatal".

**Baseline**: The gate results recorded against a run's `base_sha` at batch start.
Per repo; never compared across repos.

**New failure**: A gate failure not present in the baseline, compared on
`(gate, file, code, normalized message)` — never on line number, which the diff
moves. The comparison **counts**: identities collide legitimately, so one baseline
failure cancels one head failure, not all of them. Only new failures are a task's
problem.
_Avoid_: "regression" *as a noun for a new failure*. ("Regression test" remains the
ordinary term for a test and is fine.) _Avoid_ also "real failure".

**Pre-existing failure**: A baseline failure. Reported in the batch header, charged
to nobody.

**Repair**: The bounded loop in which the agent receives gate output and responds.
The agent never runs the gates and never reports gate status.
_Avoid_: "fix", "retry", "self-heal", "auto-fix".

**No-progress**: An identical new-failure set across two consecutive attempts, on
the same identity as a new failure and counted the same way. The signal to stop
paying.
_Avoid_: "byte-identical" — line numbers shift every attempt, so a byte comparison
never fires.

**Witness**: The test a spec's `acceptance:` entry names as the guard for its
claim. One per criterion, declared by the spec author, never chosen by the agent.
The `criteria` gate checks that it ran and turned green, and the `witness` gate
that it fails on its criterion's mutant. An ordinary test that happens to cover
the claim is not one.
_Avoid_: "the test for it".

**Mutant**: A find-and-replace edit a criterion declares against its own subject,
which its witness must fail on (`DESIGN.md` §5.4.1). Applied by the `witness` gate
to ask whether the tests would notice the claim being broken. Withheld from the
implementer's prompt on purpose: a mutant a cell chooses is a mutant chosen to be
killed.
_Avoid_: "mutation testing" for the gate as a whole — it runs one declared edit
against one named witness, not a generated suite. _Avoid_ "mutant" for the tree
the edit is applied to; that is the worktree, mutated. _Avoid_ "mutant" for the
edit a lens names in a review finding; that is a vacuity probe.

**Vacuity probe**: A find-and-replace edit a *lens* names to show that the tests would not
notice the behaviour it describes breaking. After REVIEW the host applies each anchored adequacy
finding's probe in a gate-only cell, unless the probe edits a declared test path. The corpus harness applies one inside a
fixture's cell. No gate applies one. Its outcome is inverted from a mutant's: a
vacuity probe that *survives* the suite is the finding confirmed, where a mutant that
survives its witness is the finding.
During a task the verdict decides the finding. `survived` makes it a `blocker`, `killed`
makes it a `note`, and `unproven` leaves the severity the lens filed.
_Avoid_: "mutant" for one — a mutant is declared by a criterion, is withheld from the
implementer, and must be killed. _Avoid_ "mutation testing" for the corpus number: one probe
per finding, chosen by the lens to make its own case, is not a sample of the mutation space.

**Criterion probe**: A find-and-replace edit a fresh session names to make one acceptance
claim false. During REVIEW the host starts one session per criterion in the critic cell.
Each session sees one claim and the diff, and is never told which test is its witness.
Its edits are recorded in `criterion-probes.json`. A criterion probe that survives its own
criterion's witness is the finding: nothing guards the claim. No gate applies one yet
(backlog item b-2750d5).
_Avoid_: "mutant" for one. A mutant is declared in a criterion, and a criterion probe is
named by a session that wrote neither the code nor the witness. _Avoid_ "vacuity probe" for
one. A lens names a vacuity probe against the tests, and a criterion probe targets a claim.

---

## 5. Review

**Critic**: The adversarial reviewer. A fresh, read-only session that never sees the
implementer's transcript.
_Avoid_: "the reviewer" (that's the operator), "QA", "the checker".

**Critic cell**: The cell a critic runs in: a new container from the repo's cell
image, on the task's network and proxy, whose worktree is the task's base with
the exported patch applied by that cell's own git. It is never the implementer's
cell. A fresh session in the container the implementer had root in re-execs a
runner that container could have rewritten, and reads the tree through a `.git`
the implementer wrote (Appendix Q, `DESIGN.md` §5.5). REVIEW's lenses and
REBUT's verdict sessions both run in one (`SA-0087`, `SA-0088`).
_Avoid_: "review cell", "clean cell", "second cell", "the critic's container"
when you mean the whole cell.

**Gate-only cell**: The cell the gate table a critic is shown is computed in:
the same rebuilt tree as the critic cell, but on a network of its own and
carrying `policy.thread_env` and nothing else — no proxy, no agent, no
credential, because it runs gates rather than a session. It is not the critic
cell, and the distinction is the point: a gate runs model-authored code, and
running it in the container the lenses then re-exec their runner from would
hand that code root over the critic (`SA-0089`; `DESIGN.md` §5.5). PACKAGE's
re-verification uses one too.
_Avoid_: "the gate cell", "the suite cell", "the third cell".

**Implementer**: The session that holds write tools during IMPLEMENT and REBUT. It
acts on the operator's behalf, directly or through the delegate that started the
task, and every diff it writes is written to the plan validated at the plan
checkpoint. An attempt that ends in a scope proposal writes neither.
_Avoid_: "the coder", "the writer", "the worker".

**Lens**: One critic perspective with a bounded remit — correctness & data
semantics, contract & schema, test adequacy. Lenses are disjoint by construction,
which is why any single blocker routes to REBUT and why there is no vote.
_Avoid_: "reviewer", "pass", "check", "critic #2".

**Finding**: Anything a critic reports, pointing at one file and line. Whether
that line is one the change reaches is **anchored** below, a separate property
on the row: an unanchored finding is still a finding.
_Avoid_: "issue", "comment", "bug", "problem".

**Anchored**: A finding that either falls inside a diff hunk, or cites a line
naming an identifier the diff changed. The second target is what keeps a lens
usable when its findings point at code the diff did not touch — written for
blast radius (retired, `DESIGN.md` §5.5.1) and now load-bearing for test
adequacy, whose finding is often about a test that already existed.
Unanchored findings are recorded and excluded, never deleted — the drop rate per
lens is the signal that a lens is badly prompted.

**Severity**: `blocker`, `concern`, or `note`.
- **`blocker`** — routes the task to REBUT.
- **`concern`** — reaches the operator's judgement. The count in a queue line is
  concerns, and only concerns.
- **`note`** — true but trivial. Appears in the PR body, counted nowhere. It exists
  so that filing everything as a concern is visibly wrong.

_Avoid_: "nit", "minor", "suggestion". _Avoid_ using "finding" where you mean one
specific severity.

**Spec review**: A delegate's read of one spec at the base a cell would be cut
from, before any cell runs it, on six checks
(`docs/superpowers/specs/2026-09-14-spec-reviewer-design.md`). It uses the
severities, but no task exists yet for a `blocker` to route to REBUT, so it
becomes a question to the operator. Advisory: nothing in code enforces it.
`spec-reviewer` is the file and id of the agent definition that performs it, not
a role.
_Avoid_: "the reviewer" (that's the operator), "the critic" or "a lens" (both
read a diff, and are sessions the host starts).

**Verdict**: The critic's own confirm-or-withdraw of a finding at REBUT.

**Adjudication**: The operator's agree-or-disagree with a finding. Distinct from
the critic's verdict, and the basis of the critic-ROI question.
> Three judgements, three words: the critic **verdicts**, the operator
> **adjudicates**, the implementer **rebuts**. Never call any of them "the verdict"
> without saying whose.

**Rebuttal**: The implementer's single response to confirmed blockers — either a fix
or an argument that the finding is wrong. Both outcomes are recorded; a documented
disagreement is more informative than agreement.
_Avoid_: "response", "appeal", "pushback".

---

## 6. Outcomes

**Terminal state**: A state that reaches the operator — `SCOPE_REVIEW`,
`PLAN_REJECTED`, `EXHAUSTED`, `READY_FOR_REVIEW`, `MERGE_FAILED`,
`PREFLIGHT_FAILED`, `NOT_IMPLEMENTED`, `GATE_ERROR`, `RATE_LIMITED`.
Everything else is internal.
> A state a task *ends in* is a wider set than the states that *reach you* —
> `MERGED` ends a task and reaches nobody, and `ORPHANED` waits for `saffron gc`
> rather than the operator — and one column holds both.

`TerminalEvent`, the kind `events.Terminal` writes, is not a terminal state. It records why
IMPLEMENT committed nothing, a plan rejected before any turn included. Each of its five
reasons ends the task in `PLAN_REJECTED` or `NOT_IMPLEMENTED`. The two names are
deliberately distinct.

**`EXHAUSTED`**: A task that could not pass its own gates within `max_attempts`. An
informative outcome about the spec or the codebase.

**`RATE_LIMITED`**: The provider refused the turn — its ceiling, not the task's.
Says nothing about the spec, and the only thing it asks for is a retry after the
window reopens.
_Avoid_: "exhausted", "out of budget".
_Avoid_: "failed", "gave up", "errored". Reserve "failed" for gates and
infrastructure, and "errored" for gate status `error`.

**`ORPHANED`**: A task whose cell was killed or crashed, awaiting reclamation by
`saffron gc`. Its worktree and volume are deliberately preserved until then.

**Ratify**: What the operator does to a proposed `touches` set at `SCOPE_REVIEW`.
_Avoid_: "approve" (reserved for PRs), "confirm", "sign off".

**Approve**: What the operator does to a pull request in GitHub. Approval enters the
merge train; it does not merge.
_Avoid_: "accept", "merge" (merging is what the train does, later, if green).

**Trailing accept rate**: Merged over completed tasks across a rolling window of
recent batches. The number that says whether this is working.
> Always "trailing". A batch's own accept rate is unknowable when the batch ends,
> because nothing has been merged yet — that is the next morning's work.

**Merge train**: The serial post-approval process — rebase onto current `main`,
re-run the full gate suite on the merged result, merge only if green.
_Avoid_: "merge queue" (GitHub's feature, which this is not).

**Stacked branch**: A dependent task's branch, cut from its parent's branch rather
than `base_sha`, because dependencies are satisfied at `READY_FOR_REVIEW`.

**Retired spec**: A spec the operator has moved to `.saffron/specs/done/`, asserting
that its work is in the default branch. Not offered to the scan, and admits a
dependent the same way a `MERGED` task does — the assertion the ledger cannot
make, because only a cell writes a task.

**Tree base**: The commit a task's worktree is built on and its patch is exported
against — `base_sha` for an ordinary task, the parent's branch head for a stacked
one. Recorded in `patch.json` beside `base_sha`, which stays the run's pin: gates
and policy are exported from the pin either way.
_Avoid_: using it and `base_sha` interchangeably. They differ for exactly one kind
of task, and that is the kind every consumer of either has to be right about.

---

## 7. Repos

**Policy**: `.saffron/policy.yaml` in a target repo — gate roles and blocking
levels, `elevate_on`, protected paths, envelope defaults, `integrity` patterns,
thread env. Everything repo-shaped that is not an executable.
_Avoid_: "config", "settings", "the manifest".

**Cell image**: Built from the repo's `.saffron/Dockerfile`, `FROM` a Saffron base
image. Carries the toolchain, services, migrations, and seed data.
_Avoid_: "the container image" when the distinction from a base image matters.

**Base image**: `saffron/cell-base:<runtime>`. Agent runtime and git. Nothing
else, ever — in particular no gate shim: the host `exec`s the repo's own gate
executables through the runtime, so there is nothing for one to do (§2.1).

**Fixture services**: Whatever a repo bakes into its cell image to make its tests
meaningful — a database, a cache, nothing at all. Never anything the operator runs
for real, which no cell can reach.
_Avoid_: "the test DB", "the local DB", naming a specific engine as though every
repo has one.

**Onboarding**: Writing a repo's `.saffron/` directory. It touches zero lines of
Saffron. If it doesn't, the core/repo boundary has failed.

**Preflight**: Per-repo readiness at batch start — mirror fetch, policy parse, image
rebuild, baseline. A repo that fails preflight is skipped, not fatal.
A task has a preflight of its own. Each `PreflightEvent` is one step of it, written by
`events.Preflight`. The steps include the proxy, the image build, the port probe and the
worktree coming online.
A baseline that aborts inside the task's cell ends the task in
`PREFLIGHT_FAILED`. That is fatal to the task, where the per-repo sense skips a repo.

---

## 8. Artifacts

**Ledger**: The SQLite database at `~/.saffron/ledger.db`. Authoritative for state.
_Avoid_: "the DB" (ambiguous with fixture services inside a cell), "the store".

**Batch tree**: The plain directory tree of artifacts under
`~/.saffron/batches/` — transcripts, diffs, gate logs. Greppable on purpose.
_Avoid_: "artifact store", "the logs", "the run tree".

**Event kind**: What tags one line of a task's event log: `PreflightEvent`,
`CeilingsEvent`, `BaselineEvent`, `PhaseStartEvent`, `AttemptEvent`,
`GateResultEvent`, `BudgetEvent`, `AgentEvent`, `TerminalEvent`,
`TaskOutcomeEvent`, `TeardownEvent`.
Each name is the `kind` written to `events.jsonl` with `Event` appended, because
`Attempt` and `GateResult` already name other terms here.

**Fact kind**: What a record entry says it is: `task_created`, `task_state`,
`task_package`, `task_push`, `task_merged_head`, `task_policy`, `attempt_opened`,
`attempt_closed`, `gate_result`, `finding`, `rebuttal`, `decision`, `run_created`,
`run_finished`, `run_preflight`, `batch_created`, `batch_closed`, `repo_upserted`.
The set is the record's whole alphabet, so it holds kinds nothing appends yet.
> A fact is an entry in the record on `refs/saffron/*`. An event is a line of
> `events.jsonl`. The two words do not merge.

**Projection**: The RDF graph of a run record, read from the ledger and the batch tree.
It is built for the derivation-chain query (`DESIGN.md` Appendix T). It is
derived and one-way, with no write path back to the ledger (`DESIGN.md` §4.6).
_Avoid_: "projection" for the ledger `saffron fold` rebuilds from the record. That is the
ledger.

**Emitter**: The code that materializes the projection, `materialize` in
`saffron/projection.py`. To materialize is to write the projection to one Turtle file.
`saffron chains` does it once over the whole ledger, and nothing does it at batch end.

**Checked walk**: The judgement of one merged task's derivation chain from the ledger's rows
and the batch tree's stored files alone (`saffron/chain_walk.py`). It never reads the
projection, so comparing the two is not the projection agreeing with itself. A task the
walk finds whole and the derivation-chain query drops is a break.

**Mirror**: The local bare git repository that is a cell's only remote.
_Avoid_: "origin" (that's the real remote, reachable only from the host).

**Index**: The static page listing one line per task across a batch. An index, not a
viewer — the diffs live in GitHub.
_Avoid_: "dashboard", "the queue UI", "the report", "dossier".

**Queue line**: One task's entry in the index. Its outcome summary — never a
"verdict", which belongs to findings.

---

## 9. Flywheel

**Rejection**: An operator decision to reject or request changes, plus the one-line
reason appended to `.saffron/rejections.md`.

**Bucket**: One of the three destinations a rejection is triaged into — a gate
(bucket 1), a `CLAUDE.md` line (bucket 2), a lens amendment (bucket 3). Cheapest
first.
_Avoid_: "category", "type", "tier".

**Promote**: To move a rule toward bucket 1 — lens to `CLAUDE.md`, or `CLAUDE.md`
to a gate. The direction that should always be travelled.
> Name the destination, never the direction. The buckets print 1, 2, 3 but are
> ordered cheapest-first, so "up" and "down" point opposite ways depending on
> whether you mean the page or the cost. Say "promote to bucket 1".

_Avoid_: "automate", "harden", "codify", "promote up", "promote down".

**Scoring run**: One execution of all three lenses over one fixture, in the
harness (`harness/lens_scoring.py`). The qualifier is not optional: bare **run**
is one task's pin (§2), and the harness measures REVIEW rather than
running a night.
_Avoid_: bare "run" for one, "attempt" (that is a phase execution inside a task),
"sample", "trial".

**Scoring pass**: A set of scoring runs over one fixture, scored together and
recorded under `docs/evidence/passes/`. Its n is part of its result — a k/n
without its n is the shape item 69 charged the mutation-vs-lens record with.
_Avoid_: bare "pass" — that is a gate status, and `_Avoid_` under **Attempt**
already reserves it. Also "round", "sweep", "iteration".

**Review round**: One review of one spec or pull request at one commit, in
the spec loop's review cycle. A spec review in step 1b is one review round.
Both seats of a step 2c pull request review count as one review round
together. A cell's REVIEW counts as the cell's single review round. A spec
loop review round happens outside any task, so it is never an attempt. It is
numbered from 1, and Jev scores each one (`driver.py jev`).
_Avoid_: bare "round", "iteration", and "pass".

> These three are the only place Saffron reuses **run**, **pass**, and
> **round**, and they are qualified everywhere in prose for that reason.
> Scoring run and scoring pass name measurement of the product, never the
> product: nothing under `saffron/` imports the harness. Review round names a
> step in the spec loop, qualified the same way, because bare round already
> names an attempt count.

---

## 10. Style

- Task states in caps **in backticks, in prose**: `` `READY_FOR_REVIEW` ``, not
  "ready for review" and not bare caps. Bare caps are reserved for phases, so the
  two are distinguishable at a glance. Inside code blocks, YAML, state diagrams and
  sample output, states appear bare — backticks are prose markup, not part of the
  name.
- Phases in bare caps: DIAGNOSE, IMPLEMENT, REVIEW.
- Gate names lowercase in backticks: the `revert` gate, not the Revert gate.
- Gate statuses lowercase in backticks: `pass`, `fail`, `skip`, `error`.
- Severities lowercase in backticks: `blocker`, `concern`, `note`.
- Spec IDs with the repo prefix: `TE-0142`, `SA-0001`.
- Refer to a document section by number when precision matters: "§5.4", not "the
  gates section". Section numbers in `DESIGN.md` are stable and are cited by specs.
- "The agent" is singular and generic; name the role when the role matters.

---

## 11. Design record

Where a decision Saffron made is written down. Every genre here is addressed by a
citation rather than a path — "principle 34", "Appendix G", "ADR 1", "§5.4" — because specs,
prompts and evidence records all cite them, and a record addressed by path moves
when the path does. Distinct from the **run record** (`DESIGN.md` §4.6), which is
what the factory produced; this is why the factory has the shape it has.

**Principle**: A numbered lesson in one global sequence, stating what generalizes
past the case that found it. Contributed by the revision appendix that found it,
never renumbered, cited as "principle 34".
_Avoid_: "lesson", "learning", "takeaway", and "rule" — **rule** already carries
three senses here (a rule of conduct in `CLAUDE.md`, a numbered rule inside a
`DESIGN.md` section such as §4.6.2b, and the rules a gate runs), so it cannot
also carry this one.

**Revision appendix**: A record under `docs/appendices/` recording what a revision found —
the live run, the spike, or the read-through, and what it cost. It carries the
narrative a principle compresses. Cited by letter: "Appendix G". Usually one per
revision, and not reliably so: a revision that *closes* an earlier revision's
question lands in that question's appendix rather than opening its own. Appendix G
carries rev 8 and rev 10, Appendix O rev 18 and rev 19.
_Avoid_: "the changelog" (an appendix records what was *learned*, not what
changed), "release notes", "the postmortem".

**Evidence record**: A dated document under `docs/evidence/` holding what one run
or one spike actually produced. The primary record — a measured fact beats a
reasoned one, and this is where the measurement lives.
_Avoid_: "the writeup", "the report" (`saffron/report/` renders the index, so the
word would name either),
"the log" (that is a batch tree artifact).

**Spike verdict**: A bounded document answering the one question a spike was run to
answer, carrying the clause that would reopen it (`ontology/RATIONALE.md`). A
verdict may be negative and still be the deliverable (principle 10).
_Avoid_: "ADR", "the analysis", "the recommendation".

**ADR**: A record under `docs/adr/` holding one decision Saffron made, as it
stands today. Cited by number: "ADR 1". It names the revision appendices that
argued it, the principles it upholds or departs from, and the ADRs it
supersedes. A revision appendix records what a revision found, and an ADR
records where one decision stands now (ADR 1). Prior art's decision records
keep their dashed form, as in `ADR-0019`, and appear where Appendix D cites
them.

---

## Settled naming decisions

Recorded because each was a live ambiguity and each turned out to be a design
defect rather than a word choice (Appendix E).

1. **run vs. batch** — *not* synonyms. A **batch** is one night across repos and
   owns the budget; a **run** is one task's pin and owns `base_sha` and the
   baseline. They diverged when Saffron went multi-repo and kept sharing a table,
   which left a multi-repo night with no identity to query. The ledger now has a
   `batches` table. The third sense — one gate execution — is retired: it is a
   **gate result**.

2. **verdict** — three judgements, not two, defined under Review above. The
   operator's judgement was previously folded into `decisions.reason`, which made
   the critic-ROI question unanswerable.

3. **Docker vs. the cell runtime** — "Docker" was never a decision, only a
   proper noun that read as one, and it survived seven revisions and an
   adversarial review on that basis. The runtime is chosen at v0.5 against a
   four-assertion spike; until then the word is **cell runtime**. Same shape as
   the two above: a word hiding a design defect rather than a word choice
   (Appendix G, principle 32).

4. **ADR vs. the design record** — Saffron keeps no ADRs, and never did. `CLAUDE.md`
   and `docs/agents/domain.md` promised `docs/adr/` from the day the engineering
   skills were given a repo config to read (`26ce379`); the directory was the
   skill's own example structure, pasted, and no decision here ever went in one.
   Meanwhile every `ADR-NNNN` in the design record cites *prior art's* records, so the
   word already meant something else. Same shape as 3: a name that read as a
   decision nobody had made, surviving because nothing greps for a promise
   (principle 32). The genres are now named in §11.
   Narrowed in rev 25: the refusal was argued against a parallel tree, and the
   appendices became records under `docs/appendices/` with their letters intact
   (Appendix U, principle 62).
   Reversed in ADR 1: Saffron keeps its own ADRs under `docs/adr/`, cited
   without the dash.

5. **Claude Code vs. the delegate** — a model session on the host had no name, so
   it was called by its product, and the product name hid the fact that shapes
   the design: it acts on the operator's behalf, under their identity, and none
   of its work is recorded as a task's, so the ledger cannot tell it from the
   operator. The word is PROV-O's (`prov:actedOnBehalfOf`), chosen for the
   alignment. "Surrogate" was considered and dropped, and so was "works to no
   plan": both rested on a delegate never being handed a plan, and it can be —
   PROV-O puts `prov:hadPlan` on an association, and a plan binds no one who is
   not checked against it. Same shape as 3: a proper noun standing where a role
   was never named (principle 32).

6. **`saffron:` vs. `factory:`** — the vocabulary's namespace carried the
   program's name, and the vocabulary describes the arrangement: gates, cells,
   target repos, the operator and their delegates — the **factory**. The prefix
   is `factory:` and the IRI `urn:software-factory:ns#`, a URN so that it cannot
   resolve (`DESIGN.md` §1.4). Every use was rewritten, dated records included.
   `saffron:retired-by` was not: it is a marker in source that the scheduler
   reads, not a vocabulary term, and shares only the spelling.

7. **the spec reviewer vs. a spec review** — a delegate reading a spec before its
   first cell was named "the spec reviewer", and "the reviewer" was already the
   operator and a lens's avoided name. The seat had an occupant, and the name hid
   what separates this one: its `blocker` cannot route to REBUT, because no task
   exists yet, so it reaches the operator. It is named as an activity a delegate
   performs. `spec-reviewer` stays as the agent definition's file and id, which
   the loop invokes and the backtest's frozen reports cite.

## Open naming decisions

Add here rather than resolving in prose elsewhere — an ambiguity that gets settled
in a commit message is an ambiguity that comes back.

1. **A word for what a gate result and a finding both are.** `DESIGN.md` §4.6 holds
   that a `mypy` failure and a critic blocker are one shape — *an assertion, by an
   agent, about a subject, with an outcome* — and calls the two-table split "worth
   reconciling in §4.1". §4 and §5 here reproduce that split with no shared term, so
   the sentence the ontology exists to make cannot be written in Saffron's own
   vocabulary. Left open deliberately: coining a supertype before §4.1 reconciles
   would put a word here that nothing says. Resolve when the schema does — or record
   that it never will.

2. **Approve names an act GitHub refuses the operator.** PACKAGE opens every pull
   request as the operator. GitHub does not let an author approve their own pull
   request. Nothing else writes `APPROVED` either: reconcile reads `reviewDecision`
   only for `CHANGES_REQUESTED`. So the step that admits a task to the merge train
   (`DESIGN.md` §6.1) has no signal, and the operator's acceptance today is the
   merge itself. The likely signal is marking
   PACKAGE's draft ready, which is the operator's own act and readable from GitHub.
   Until a train exists that act carries no judgement, and it is called "mark
   ready". Resolve with backlog item 52, which holds the train's other state.
