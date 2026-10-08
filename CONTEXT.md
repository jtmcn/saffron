# Saffron — terminology

The controlled vocabulary for Saffron. Every term used in a spec, a system prompt,
a PR body, a queue line, or `DESIGN.md` must appear here with one meaning.

**How this is used.** This is a host artifact. It lives in Saffron, not in any
target repo, so an agent inside a cell cannot follow a reference to it. It is
**injected into the system prompt, per phase, section by section** (`DESIGN.md`
§5.3). Each section below is tagged with the phases that receive it. Sections
tagged `—` are for the operator and the design documents only. Nothing
inside a cell can act on them.

Only three phases appear in the table. REPAIR and REBUT resume the implementer's
session and inherit its sections. PACKAGE involves no model.

It is *definitional*, not behavioural: it says what words mean, never what to do.
So it stays out of `CLAUDE.md` and is exempt from the ~200-line budget in §8.
Rules of conduct belong in `CLAUDE.md`. Rules of naming belong here.

`_Avoid_` lists are the load-bearing part. A synonym that reads as harmless in prose
is what makes two log lines, two prompts, and a ledger column disagree.
They are written for the operator and the `terms` gate. Injection strips them, since
a prohibition puts the banned word in the prompt, so a cell sees only the headword.
The conventions lens keeps them, because it judges a diff against them (SA-0195).
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

**Engine**: Saffron as a versioned artifact that an operator deploys. A target repo
carries `.saffron/` and never the engine (ADR 10).
_Avoid_: "the package", "the app".

**Control plane**: The trusted host-side half: intake, scheduler, supervisor, gate
runner, packager, ledger. It decides what runs and whether the result is acceptable,
and never executes model-authored code.
_Avoid_: "the server", "the daemon", "the backend".

**Cell**: One task's isolation unit: a container plus its worktree volume, agent
state volume, and any fixture services. The cell is untrusted.
_Avoid_: "sandbox". The word implies the isolation boundary is the control, and in
Saffron it is not (the controls are structural and live outside the cell).
_Avoid_ also: "the container" when you mean the whole cell, "worker", "runner".

**Container**: The runtime primitive specifically: the object the cell runtime
creates and destroys. Use only when that object itself is the subject.

**Cell runtime**: The program that creates cells. `apple/container` (a VM per
cell), chosen in rev 10 against a four-assertion spike (Appendix G).
Say "the cell runtime". The seam is `saffron/cell/runtime.py`. Every caller
uses it, and it names no product at all. Each runtime's own module under
`saffron/cell/runtimes/` names exactly one. No other module in `saffron/`
names any. A decision made by spike can be remade by spike. A second answer
is then a second module rather than an edit spread through the tree.
_Avoid_: **"Docker"** as a generic term for it. "Docker" was a product name standing
in for an unmade decision through seven revisions. Naming a different product
generically would repeat the mistake. _Avoid_ also "the container engine", "the
VM" (a cell now *has* one, so the phrase is ambiguous), "the hypervisor".

**Worktree**: The git working tree a task edits, on a volume mounted at `/work`.
A cell contains a worktree and is not one.
_Avoid_: "the checkout", "the clone", "the workspace", "the sandbox dir".

**Operator**: The human. Singular per deployment, by design (ADR 10).
_Avoid_: "the user", "the reviewer" (reviewing is one of several things they do).

**Deployment**: One engine, one operator, one home, and the target repos that operator
configures. The home is the `--home` directory, `~/.saffron` by default. A target repo
belongs to one deployment. It arbitrates that operator's credential, budget and review queue. Its
host is the operator's Mac or a Linux host VM (ADR 10).
_Avoid_: "the tenant", "the instance".

**Target repo**: The repository a task modifies. Saffron is generic. The target repo
holds the specs, the policy, the cell image, and the repo's own gates.
_Avoid_: "the project", "the codebase", "the client repo".

**Agent**: Any model session inside a cell, when the specific role does not matter.
The ontology's `prov:Agent` is wider. It includes the operator, their delegates,
and every gate, which is a `prov:SoftwareAgent` there because it asserts
(`ontology/factory.ttl`, `DESIGN.md` §4.6). "Model" means a model identifier.
_Avoid_: "the AI", "the bot", "the LLM".

**Delegate**: A model session the operator starts on the host, outside any cell, to
act on their behalf, under their git identity and credentials. The factory neither
starts nor constrains it. None of its work is recorded as a task's, so the ledger
cannot tell it from the operator. It is never the operator: a ratification or
approval it types is still the operator's judgement. Plural, unlike the operator. A
delegate's subagents are delegates too, and every chain of them ends at the
operator.
> PROV-O's word, and PROV-O would call the implementer one as well. The implementer too acts
> on the operator's behalf, directly or through a delegate, and both can work to a
> plan. What separates them is what holds them to it. The implementer's plan is a
> control artifact, validated outside its cell, and its work is recorded as
> attempts. A plan handed to a delegate binds only as far as the delegate follows
> it, and nothing records whether it did.

_Avoid_: "Claude Code" (a product standing for a role), "the assistant", "the
agent" (that is inside a cell), bare "session", and "surrogate". _Avoid_ also "the critic" or
"a lens" for a delegate's review.

---

## 2. Work

**Spec**: A markdown file with YAML frontmatter at `.saffron/specs/` in a target
repo. The unit of work, written by the operator.
_Avoid_: "ticket", "issue", "story", "request", "prompt".

**Task**: One spec being executed: a ledger row with a state, a branch, a budget,
and a cell. A spec is the input. A task is the execution. Its budget is a
**best-effort** bound. It is checked between attempts, and an attempt's cost is
not knowable until the attempt ends. So a task admitted under its ceiling can
finish over it by up to one whole attempt: 67% on `SA-0059` (`DESIGN.md` §3).
In a batch, the bound that is enforced is the batch's, checked between
tasks (`DESIGN.md` §4.2.1). The batch's bound is itself exceedable by at most one task's overshoot,
since it admits a task on that task's declared ceiling. A task started by
`saffron cell` belongs to no batch, and its own best-effort bound is the only one.
_Avoid_: "job", "work item", "unit".

**Batch**: One night's execution, spanning every selected repo. One budget, one
concurrency pool, one `--until`.
_Avoid_: "session" (that means an agent session), "cycle", "sweep", "run".

**Batch stop reason**: `DRAINED`, `BUDGET`, `UNTIL`, `INFRASTRUCTURE`, or
`INCOMPLETE`. Why a night ended, written on the batch when it closes and absent
while it is still running. An absent one means in flight, not unknown. Never a
task's end state: these describe the night, and `DRAINED` says the queue emptied,
not that anything in it succeeded. `INFRASTRUCTURE` is the breaker firing, and
it is the only one of the five that says the machine rather than the work was
wrong. `INCOMPLETE` is a night that left a task in flight: that task reached no
end state, which is not the same as failing. It outranks the other ordinary
reasons, and `INFRASTRUCTURE` outranks it.
_Avoid_: "failed" for `INFRASTRUCTURE` (a task fails, a night stops), "finished",
"timeout" for `UNTIL`.

**Stack batch**: A batch started with `saffron batch --stack` (ADR 7). It fixes its
stack order once, at batch start, and never rescans. Each task stacks on its
predecessor. One end review reads the stack once the batch stops taking tasks.
_Avoid_: "stack run" (a run is a pin), "spec loop" (the delegate's attended pass).

**Stack order**: A stack batch's fixed order over its queued specs. A spec joins it
once every `depends_on` entry is already in the order or on the default branch. Among
ready specs the lowest `priority` goes first, then the lowest id. A spec the order
never takes is refused before any cell starts.

**Predecessor**: The last task below a task in its stack order to reach
`READY_FOR_REVIEW`. The task is cut from the predecessor's head and targets its
branch. A task with no predecessor is cut from `base_sha`.
_Avoid_: "parent" (that is `depends_on[0]`, and a predecessor need not be one).

**Layer**: A task in a stack batch that reached `READY_FOR_REVIEW`. It is one
`stack_layers` row, with its position and its predecessor. A task that misses adds no
layer.

**Mint**: What a stack batch does to open a spec's run and task before its spec
review. The review's attempts and facts are recorded against that task, and its cell
runs on it. A spec offered again after a wait keeps the task it was minted.

**Spec writer session**: A host-invoked session that revises one spec after its spec
review routes it to `revise`. It runs in a critic cell at the predecessor's head, or
at `base_sha` with no predecessor. Its attempt is labelled SPEC_WRITING. Its reply
becomes a recorded spec text, which the spec review then reads. Under `saffron draft`
it also writes the first text, from the item (§3.4).

**Revision**: One spec writer session and the spec review of the text it returned. A
stack batch runs at most three per spec, then escalates the spec. `saffron draft` runs
at most one (§3.4). A stack batch's revision starts
only while the budget left, less the reserve, covers a writer, a review and the spec's
budget.

**Escalation**: A stack batch's spec review sending a spec to the operator and not to
a cell. A `blocker` tagged neither `build` nor `witness` escalates. So does any
`blocker` left after three revisions, or read with no spec writer to revise it. The
task ends `SPEC_WITHHELD`, and each spec that depends on it is refused. It counts as
no abort.
_Avoid_: "rejected", "blocked".

**Recorded spec text**: A spec's text that a task records and that is not at
`base_sha`. It is a `spec_texts` row and a `spec_text` fact, hashed when recorded.
Before the cell, `run_task` re-runs the gate 0 refusals that need no GitHub against
the latest one. A revision, a follow-up and a draft each write one.

**Spec loop**: A delegate's pass over the queued specs, each through an attended
`saffron cell`, into one stack. Each step it does by hand is one the factory does
not yet do. It hands a step over once a gate, lens or phase can do it.
_Avoid_: "batch" (unattended, with one budget over every task), "night".

**Spec chain**: A delegate's turning of a backlog item or a handed-over finding into
a spec, through the `spec-writer` and `spec-reviewer` delegates, until its review
rounds stop. It ends at a spec a cell can run and starts no cell. The spec loop
runs that spec. `saffron draft` runs it as a task (§3.4).
_Avoid_: "spec loop" (that runs specs), "spec creation loop".

**Run**: One task's pin, owning the `base_sha` its gates and policy are read at, its
**preflight outcome** and its baseline. A batch holds one run per task. Every run of
one repo in a batch shares the `base_sha` the batch pinned for that repo. A stacked
task's tree and baseline sit on its parent's head instead, while its run keeps the
pin. `saffron cell` and `saffron replay` each mint a run that belongs to no batch.
The per-repo slice of a batch has no name and no row (backlog item 177).
> Batch and run are **not** synonyms and stopped being interchangeable when Saffron
> went multi-repo. Budget is a batch property, and `base_sha` is a run property. If a
> sentence works with either word, it is imprecise.

**Preflight outcome**: What a run records when its first baseline suite ends: `PASSED`
or `FAILED`.
It lives in `runs.preflight`. A baseline that aborts in the cell writes `FAILED`, so
this is not the batch-start **Preflight** under Repos (backlog item 113). What a
NULL means is open (backlog item b-eac388).

**Phase**: A named stage in the cell pipeline: DIAGNOSE, IMPLEMENT, GATE ⇄ REPAIR,
REVIEW, REBUT, PACKAGE. Written in bare caps. A stack batch also labels attempts
SPEC_REVIEW and SPEC_WRITING. Each is a host-invoked session before the cell, and
neither is a stage of the cell pipeline.
The event log alone splits GATE ⇄ REPAIR into GATE and REPAIR, because a gate
attempt and a repair turn print different lines. Everywhere else it is one phase.
_Avoid_: "stage", "step", "mode".

**Attempt**: One numbered execution of a phase. Attempts are bounded on five axes:
turns, spend, idle, completion, and wall clock. "Attempt 3" without a phase is
ambiguous, so name both. A gate suite's number is the one exception. It counts the
gate suites judged in a task, so the suite re-run after REBUT continues the
repair loop's count. After a loop that reached 2, that re-run is attempt 3, labelled REBUT.
_Avoid_: "iteration", "round", "pass", "retry", "try".

**Plan checkpoint**: The `plan.json` write and host-side validation that opens the
IMPLEMENT session. Deliberately *not* a phase, because the planner and the implementer are
the same session.
_Avoid_: "the planning phase", "the plan step", "PLAN".

**Extraction turn**: A tool-less turn that resumes a session solely to emit one
structured artifact, which the host validates. REBUT's turns return it as a
schema-constrained value. Every other extraction turn emits an `<output>` block.
How every structured artifact is produced.
_Avoid_: "the JSON step", "parsing the output".

**Control artifact**: A host-consumed file an agent produces: `plan.json`,
`scope.json`. Extracted and hashed the moment it is written, never re-read from
`/work`. A control artifact left in the workspace is a claim, not a record.

**Refusal**: A task rejected before any cell starts. The causes include a duplicate open PR, an
overlapping in-flight change, a malformed or moved spec, and a repo that failed preflight.
The refusal itself costs nothing. A refusal the queue scan makes reaches the queue as
one line. `run_task` also refuses a task whose `consumes` entry does not resolve, or
cannot be read, at the tree base. That refusal prints one line and writes no queue
row. A stack batch also refuses a spec its stack order never takes, and every spec
whose `depends_on` reaches a missed task. It refuses a revision the budget left cannot
cover.
_Avoid_: "skip" (that is a gate status), "blocked", "reject" (that is what the
operator does to a PR).

**Consumed name**: An entry in a spec's `consumes` list, naming something its
`depends_on` parent built. It is a repo-relative path, or `path:name` for a name that
file holds as a whole word. `run_task` resolves each entry at the task's tree base
before any cell starts. An unresolved entry refuses the task. A spec that declares one
with no `depends_on` does not parse.
_Avoid_: "import", "dependency" (that is a `depends_on` entry).

---

## 3. Scope

**Envelope**: The loose outer bound on what a DIAGNOSE phase reads. Declared by
the operator on bug specs, and never enforced against a diff.

**Touches**: The set of paths a task is permitted to change. Declared directly on non-bug specs.
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
Distinct from `forbidden`: one is per-task, one is repo-wide.
_Avoid_: using either name for the other, or "the denylist" for either.

**Out of scope**: The prose section of a spec naming adjacent broken things the
agent must leave alone. Not machine-enforced. It reduces sprawl by being read.
_Avoid_: conflating with `forbidden`, which is enforced.

**Risk tier**: `standard` or `elevated`. Set on the spec, or raised automatically when
the diff touches a path in the repo's `elevate_on`. At the plan checkpoint the same
rule reads the plan's `files_to_change` instead, as a forecast. Elevated makes `size`
and `witness` blocking, the only two gates a tier moves (`DESIGN.md` §5.4.1). It
also marks the queue entry. It adds no lens, because every declared lens runs at every tier
(`DESIGN.md` §5.5.1). It does **not** make `coverage` blocking: `coverage` is
advisory at every tier (`DESIGN.md` §5.4).
_Avoid_: "priority" (a separate field), "severity" (that is a finding property),
"critical", "high-risk".

---

## 4. Verification

**Gate contract**: The interface that makes Saffron repo-agnostic. A gate is an
executable that emits one JSON object: `gate`, `status`, `tool`, `failures[]`,
`summary`. Nothing downstream sees tool output.

**`tool`**: The identifier a gate obtains *by executing* its tool (`ruff 0.14.2`).
It is the only thing separating a gate that ran and passed from one that never ran
(Appendix H, `DESIGN.md` §5.4).
_Avoid_: "the version", "the tool name". A `tool` value is neither on its own, and a string
literal in a gate script is not a `tool` value at all.

**Gate role**: A name in the contract — `format`, `lint`, `types`, `tests`,
`no-network`, `coverage`. The repo supplies the executable, and core supplies the
meaning.

**Gate**: One named verification, host-invoked and deterministic. Written lowercase
in backticks. Three kinds, and the distinction is the core/repo boundary:

- **Core gates** — `scope`, `size`, `secrets`, `integrity`, `census`, `committed`,
  `criteria`, `revert`, `witness`. Implemented in Saffron. Most read the diff.
  `committed` reads the worktree's status instead, and `census` and `criteria`
  read other gates' results. `revert` and `witness` are the two that run
  something, and §2.1's rule is shaped around them rather than broken by them:
  core invokes declared gates, never tools (`DESIGN.md` §2.1). `witness` is also
  the second gate a risk tier moves (§5.4.1). The rest sit at the level §5.4
  fixes for them.
- **Contract gates**: the gate roles above. Declared in `policy.yaml`, implemented
  in the repo's `.saffron/gates/`.
- **Repo-defined gates**: anything a repo adds against its own hard-to-fake
  surfaces, conditional on touched paths. Names vary by repo and are not vocabulary.

_Avoid_: "check", "validation", "CI" (there is no CI), "the linter" for the `lint`
gate. _Avoid_ naming any repo-defined gate here as though it were universal.

**Gate result**: One execution of one gate against one tree: an attempt's, or a
run's `base_sha` for the baseline. Exactly one of `attempt_id` and `run_id` is set
on the row, and the baseline is why (`DESIGN.md` §4.1).
_Avoid_: "gate run", or bare "run". "Run" means one task's pin.

**Gate suite**: Every gate executed as one unit against one tree: the core gates
plus the roles the repo declares. It has no identity of its own, so name what it ran
against ("the baseline suite", "attempt 3's suite"). Two suites are what the
baseline subtracts and what `suite_drift` compares.
> Bare "suite" means the **gate suite**. A repo's own tests are always "the test
> suite", never bare, because the gate suite *contains* them. §7.1 times both two
> lines apart, and a bare "the suite is minutes" names the wrong cost.

_Avoid_: "gate run", as for a gate result.

**Suite comparison**: What judging a head gate suite against its baseline yields.
It is one of three things, checked in this order. First, a gate `error`ed, and whatever ran
the suite aborts, whether an attempt or a package. Second, the suites **drifted** (a gate
stopped running, or its `tool` changed), so no subtraction is to be trusted. Third,
the blocking new failures that remain.
_Avoid_: "verdict", which is the critic's confirm-or-withdraw of a finding.
_Avoid_ also "the subtraction" for the whole: the subtraction produces only the
third outcome, and it is not even attempted when either of the first two holds.

**Status**: A gate result is `pass`, `fail`, `skip`, or `error`.
- `skip`: the repo declares no such gate. Not a failure. Nothing is wrong.
- `fail`: the repo's code is wrong.
- **`error`: the gate itself broke.** Toolchain missing, service down, collection
  crashed. It aborts the attempt, is never charged to the task, and is what
  distinguishes "three flaky tests" from "the toolchain is broken" at preflight.

> `error` and `fail` are the single most important distinction in this section.
> Reserve the bare word "failed" for `fail`. Say "errored" for `error`.

**Blocking / advisory**: A gate is one or the other. Blocking gates stop the task.
Advisory gates are reported in the PR body and stop nothing. State which when it
matters. `coverage` being advisory is a design decision, not an oversight.
_Avoid_: "soft fail", "warning", "non-fatal".

**Baseline**: The gate results recorded against a run's `base_sha` at batch start.
Per repo, and never compared across repos.

**New failure**: A gate failure not present in the baseline, compared on
`(gate, file, code, normalized message)`, never on line number, which the diff
moves. The comparison **counts**: identities collide legitimately, so one baseline
failure cancels one head failure, not all of them. Only new failures are a task's
problem. A `witness` survivor is the one exception. The baseline never cancels a
`witness` failure coded `survived-mutant`, so a survivor at base is still new at
head. The spec declared that mutant, so killing it is the task's work.
_Avoid_: "regression" *as a noun for a new failure*. ("Regression test" remains the
ordinary term for a test and is fine.) _Avoid_ also "real failure".

**Pre-existing failure**: A baseline failure. Reported in the batch header, charged
to nobody. A `witness` survivor at base is not subtracted, so it is also a new
failure at head (see **New failure**).

**Repair**: The bounded loop in which the agent receives gate output and responds.
The agent never runs the gates and never reports gate status.
_Avoid_: "fix", "retry", "self-heal", "auto-fix".

**No-progress**: An identical new-failure set across two consecutive attempts, on
the same identity as a new failure and counted the same way. The signal to stop
paying.
_Avoid_: "byte-identical". Line numbers shift every attempt, so a byte comparison
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
_Avoid_: "mutation testing" for the gate as a whole. The gate runs one declared edit
against one named witness, not a generated suite. _Avoid_ "mutant" for the tree
the edit is applied to. That is the worktree, mutated. _Avoid_ "mutant" for the
edit a lens names in a review finding. That is a vacuity probe.

**Vacuity probe**: A find-and-replace edit a *lens* names to show that the tests would not
notice the behaviour it describes breaking. After REVIEW the host applies each anchored adequacy
finding's probe in a gate-only cell. It refuses a probe that edits a declared test path, and
every probe when the repo declares no `test_paths`. An end review's
anchored findings that carry a probe are applied the same way. The corpus harness applies one inside a
fixture's cell. No gate applies one. Its outcome is inverted from a mutant's: a
vacuity probe that *survives* the suite is the finding confirmed, where a mutant that
survives its witness is the finding.
During a task only a failure of a test the diff adds kills a probe. A new failure of any
other test is recorded beside the verdict and does not kill it. The corpus harness still
counts every test it collected. During a task the verdict decides the finding. `survived` makes it a `blocker`, `killed`
makes it a `note`, and `unproven` leaves the severity the lens filed.
_Avoid_: "mutant" for one. A mutant is declared by a criterion, is withheld from the
implementer, and must be killed. _Avoid_ "mutation testing" for the corpus number: one probe
per finding, chosen by the lens to make its own case, is not a sample of the mutation space.

**Criterion probe**: A find-and-replace edit a fresh session names to make one acceptance
claim false. During REVIEW the host starts one session per criterion in the critic cell.
Each session sees one claim and the diff, and is never told which test is its witness.
Its edits are recorded in `criterion-probes.json`. A criterion probe that survives its own
criterion's witness is the finding: nothing guards the claim. The host applies each one in
a gate-only cell, and a survivor that anchors to the diff is a blocker for REBUT (`SA-0120`).
_Avoid_: "mutant" for one. A mutant is declared in a criterion, and a criterion probe is
named by a session that wrote neither the code nor the witness. _Avoid_ "vacuity probe" for
one. A lens names a vacuity probe against the tests, and a criterion probe targets a claim.

**Wrong version**: A plausible wrong implementation a spec's author lists in prose under one
criterion's `wrong_versions`. The implementer reads the list under that criterion's witness.
During REVIEW one fresh session per such criterion turns each into a find-and-replace edit.
It sees the claim, the list and the diff, and is never told which test is its witness. A
version it cannot express as an edit is recorded as such. The host applies each edit in the
gate-only cell criterion probes use and runs that criterion's witness. Every outcome is
recorded in `wrong-versions.json`. A survivor that anchors to the diff is a blocker for REBUT
(`SA-0187`, `SA-0190`).
_Avoid_ "mutant" for one. A mutant is exact text withheld from the implementer, and a wrong
version is prose the implementer reads. _Avoid_ "criterion probe" for its edit. A criterion
probe's session is shown no list.

---

## 5. Review

**Critic**: The adversarial reviewer. A fresh, read-only session that never sees the
implementer's transcript.
_Avoid_: "the reviewer" (that is the operator), "QA", "the checker".

**Critic cell**: The cell a critic runs in. It is a new container from the repo's
cell image. Its worktree is the task's base with the exported patch applied by
that cell's own git. It sits on a critic network the task's proxy joins and the
implementer does not. It is never the implementer's
cell. A fresh session in the container the implementer had root in re-execs a
runner that container could have rewritten. That session also reads the tree through a `.git`
the implementer wrote (Appendix Q, `DESIGN.md` §5.5). REVIEW's lenses and
REBUT's verdict sessions both run in one (`SA-0087`, `SA-0088`). The end review
and a stack batch's spec sessions use one with no implementer behind it. It is
seeded at a head, or at `base_sha`, with no patch applied (ADR 7).
_Avoid_: "review cell", "clean cell", "second cell", "the critic's container"
when you mean the whole cell.

**Gate-only cell**: The cell the gate table a critic is shown is computed in.
It holds the same rebuilt tree as the critic cell, but sits on a network of its own.
It carries `policy.thread_env` and nothing else: no proxy, no agent, no
credential, because it runs gates rather than a session. It is not the critic
cell, and the distinction is the point. A gate runs model-authored code.
Running that code in the container the lenses then re-exec their runner from would
hand it root over the critic (`SA-0089`, `DESIGN.md` §5.5). PACKAGE's
re-verification uses one too.
_Avoid_: "the gate cell", "the suite cell", "the third cell".

**Implementer**: The session that holds write tools during IMPLEMENT and REBUT. It
acts on the operator's behalf, directly or through the delegate that started the
task. Every diff it writes is written to the plan validated at the plan
checkpoint. An attempt that ends in a scope proposal writes neither.
_Avoid_: "the coder", "the writer", "the worker".

**Lens**: One critic perspective with a bounded remit: correctness & data
semantics, contract & schema, test adequacy, conventions. Their remits are meant to
be disjoint, and Appendix L measured two lenses filing one finding. Two lenses agreeing
is a fact about the prompts, not corroboration. So any single blocker routes to REBUT,
and there is no vote (principles 9 and 51). The end
review's Spec, Standards and join lenses are not among them (ADR 7).
_Avoid_: "reviewer", "pass", "check", "critic #2".

**End review**: The one read of a stack batch's stack, once the batch stops taking
tasks (ADR 7). The join lens reads first. The end-review lenses then read each layer
from the top down. It spends only the end-review reserve, and it runs after an `UNTIL`
stop too.

**End-review lens**: The Spec or the Standards session that reads one layer in the end
review. Each runs in a fresh critic cell at the layer's pushed head, with no patch
applied. Neither is one of ADR 4's declared lenses.

**Join lens**: The session that reads a whole stack's diff once, from the bottom
layer's base to the top layer's head (ADR 6). It reads the seams between layers. A
stack of fewer than two layers gets none. Its outcome is filed under the top layer's
task.

**End-review reserve**: A quarter of a stack batch's `--budget`, held back from every
task's budget check for the end review. A layer starts only while what remains covers
both of its lenses' ceilings.

**End-review status**: One lens's outcome against one layer: `reviewed`, `error` or
`not_reached`. `not_reached` is a layer the reserve did not cover, and no cell opens
for it. `error` is the lens breaking, never a verdict on the layer. Unlike a gate
`error`, its cost is still charged to the reserve.

**Finding**: Anything a critic reports, pointing at one file and line. Whether
that line is one the change reaches is **anchored** below, a separate property
on the row: an unanchored finding is still a finding.
_Avoid_: "issue", "comment", "bug", "problem".

**Anchored**: A finding that either falls inside a diff hunk, or cites a line
naming an identifier the diff changed. The second target is what keeps a lens
usable when its findings point at code the diff did not touch. The second target was written for
blast radius (retired, `DESIGN.md` §5.5.1). It is now load-bearing for test
adequacy, whose finding is often about a test that already existed.
Unanchored findings are recorded and excluded, never deleted, because the drop rate per
lens is the signal that a lens is badly prompted.

**Severity**: `blocker`, `concern`, or `note`.
- **`blocker`**: routes the task to REBUT.
- **`concern`**: reaches the operator's judgement. The count in a queue line is
  concerns, and only concerns.
- **`note`**: true but trivial. Appears in the PR body, counted nowhere. It exists
  so that filing everything as a concern is visibly wrong.

_Avoid_: "nit", "minor", "suggestion". _Avoid_ using "finding" where you mean one
specific severity.

**Spec review**: A delegate's read of one spec at the base a cell would be cut
from, before any cell runs it, on six checks
(`docs/superpowers/specs/2026-09-14-spec-reviewer-design.md`). It uses the
severities. Outside a stack batch, no task exists yet for a `blocker` to route to
REBUT, so it becomes a question to the operator. There it is the delegate's, and
advisory. In a stack batch the host starts one session per spec in a critic cell
at the predecessor's head, or at `base_sha` with no predecessor. Its route runs
the spec, revises it, or withholds it (`SPEC_WITHHELD`). A provider limit routes
it to `wait`, and an unreadable read to `error`. Each round it records keeps its
findings one by one, as `spec_finding` facts (§3.4).
`spec-reviewer` is the file and id of the agent definition that performs it, not
a role.
_Avoid_: "the reviewer" (that is the operator), "the critic" or "a lens" (both
read a diff, and are sessions the host starts).

**Verdict**: The critic's own answer on a finding at REBUT: `confirmed`, `withdrawn` or
`contradicted`. `contradicted` means the rebuttal and the finding each rest on a line of the
spec, and the two lines disagree. The host reads one as `confirmed` when a quote is missing, is not in that spec,
or equals the other. It also reads a `withdrawn` answer on its own survivor of a
`preserves` criterion as `confirmed`, unless the first answer was `fixed` and HEAD moved.

**Adjudication**: The operator's agree-or-disagree with a finding. Distinct from
the critic's verdict, and the basis of the critic-ROI question.
> Three judgements, three words: the critic **verdicts**, the operator
> **adjudicates**, the implementer **rebuts**. Never call any of them "the verdict"
> without saying whose.

**Rebuttal**: The implementer's single response to confirmed blockers: either a fix
or an argument that the finding is wrong. Both outcomes are recorded. A documented
disagreement is more informative than agreement.
_Avoid_: "response", "appeal", "pushback".

---

## 6. Outcomes

**Task state**: A value `tasks.state` holds, which is an in-flight state or an end
state. `TaskState` in `saffron/ledger.py` names every task state, and a test holds
it to the vocabulary.

**End state**: A state the task waits in, on the operator, GitHub, the merge train or
the garbage collector: `SCOPE_REVIEW`, `PLAN_REJECTED`, `EXHAUSTED`,
`READY_FOR_REVIEW`, `MERGE_FAILED`, `PREFLIGHT_FAILED`, `NOT_IMPLEMENTED`,
`GATE_ERROR`, `RATE_LIMITED`, `SPEC_WITHHELD`, `PROVIDER_UNREACHABLE`,
`SPEC_DRAFTED`, `APPROVED`, `CHANGES_REQUESTED`, `REJECTED`, `MERGED`, `ORPHANED`,
`MERGE_TRAIN`.
A re-queue resumes the same row from six end states, so an end state need not be
final. Every terminal state is an end state.

**In-flight state**: A state in which Saffron advances the task, tonight or now: `DRAFT`,
`QUEUED`, `DIAGNOSING`, `IMPLEMENTING`, `GATING`, `REPAIRING`, `REVIEWING`,
`REBUTTING`.
A batch scan stamps a task it finds in one `ORPHANED` (§4.2.1).

**Terminal state**: A state that reaches the operator — `SCOPE_REVIEW`,
`PLAN_REJECTED`, `EXHAUSTED`, `READY_FOR_REVIEW`, `MERGE_FAILED`,
`PREFLIGHT_FAILED`, `NOT_IMPLEMENTED`, `GATE_ERROR`, `RATE_LIMITED`,
`SPEC_WITHHELD`, `PROVIDER_UNREACHABLE`, `SPEC_DRAFTED`.
Everything else is internal.
> A state a task *ends in* is a wider set than the states that *reach you*.
> `MERGED` ends a task and reaches nobody, and `ORPHANED` waits for `saffron gc`
> rather than the operator. One column holds both.

`TerminalEvent`, the kind `events.Terminal` writes, is not a terminal state. It records why
IMPLEMENT committed nothing, a plan rejected before any turn included. Each of its five
reasons ends the task in `PLAN_REJECTED` or `NOT_IMPLEMENTED`, except the two cut-off
reasons. A bound can cut an IMPLEMENT turn with nothing committed. The bound is the turn
ceiling, the wall clock or the turn's own budget cap. A turn so cut, with nothing recovered by salvage or
checkpoint, ends `ORPHANED` the first time at a `spec_sha`. The second such cut ends `NOT_IMPLEMENTED`. The two names are deliberately distinct.

**`EXHAUSTED`**: A task that could not pass its own gates within `max_attempts`. An
informative outcome about the spec or the codebase. Five more ways in share the state.
The spend ceiling stops the task before its next turn. Its gates go red after the
rebuttal. A REBUT is cut short by its $10.00 cap. Its exported patch
does not apply or commit in a Gate-only or critic cell, or its commits net to no change.

**`RATE_LIMITED`**: The provider refused the turn. The ceiling it hit is the provider's, not the task's.
Says nothing about the spec, and the only thing it asks for is a retry after the
window reopens.
_Avoid_: "exhausted", "out of budget".
_Avoid_: "failed", "gave up", "errored". Reserve "failed" for gates and
infrastructure, and "errored" for gate status `error`.

**`PROVIDER_UNREACHABLE`**: A task whose plan turn ended `api_error` with no token
served. No turn of the task completed, so nothing was learned about the spec. It is
infrastructure, exits 2 and re-queues. A rejected window stays `RATE_LIMITED`. A turn
that fails after an earlier turn completed never ends here.
_Avoid_: "offline", "network failure".

**`SPEC_WITHHELD`**: A task whose spec review in a stack batch escalated, so no cell
ran its spec. It escalates a `blocker` it could not revise, or a spec still unclean
after three revisions. The review is a fact on the task. The spec is not queued again
until it is edited. Under `saffron draft`, a writer reply that declares an id other
than the task's is withheld too, with no further review (§3.4).
_Avoid_: "rejected" (the operator's word for a pull request), "blocked".

**`ORPHANED`**: A task whose cell was killed or crashed, awaiting reclamation by
`saffron gc`. Its worktree and volume are deliberately preserved until then.
A bound can cut an IMPLEMENT turn with nothing committed: the turn ceiling, the wall
clock or the turn's own budget cap. A turn so cut, with nothing recovered by salvage or checkpoint, also
ends here. It does so the first time at a `spec_sha`, so the spec re-queues once. Its cell is torn down as
usual, so `saffron gc` has nothing to reclaim. The second such cut ends `NOT_IMPLEMENTED`.

**Ratify**: What the operator does to a proposed `touches` set at `SCOPE_REVIEW`.
_Avoid_: "approve" (reserved for PRs), "confirm", "sign off".

**Approve**: What the operator does to a pull request in GitHub by marking PACKAGE's
draft ready. Reconcile records it as `APPROVED`. Approval admits a task to the merge
train and does not merge it. No train exists yet, so today the operator merges by hand.
_Avoid_: "accept", "merge" (merging is what the train does, later, if green), and
"approve" for GitHub's review approval, which an author cannot give.

**Trailing accept rate**: The share of the last twenty settled tasks that are
`MERGED`. The number that says whether this is working.
> Always "trailing". A batch's own accept rate is unknowable when the batch ends,
> because nothing in it is merged by then. Merging is the next morning's work.

**Settled task**: A task whose outcome can no longer change. Its state is
`MERGED`, `REJECTED`, `MERGE_FAILED`, `EXHAUSTED`, `NOT_IMPLEMENTED`,
`PLAN_REJECTED` or `SPEC_WITHHELD`. A task the scheduler re-queues has not settled,
and neither has one whose outcome still waits on the operator.

**Merge train**: The serial post-approval process: rebase onto current `main`,
re-run the full gate suite on the merged result, merge only if green.
_Avoid_: "merge queue" (GitHub's feature, which this is not).

**Stacked branch**: A dependent task's branch, cut from its parent's branch rather
than `base_sha`, because dependencies are satisfied at `READY_FOR_REVIEW`. In a stack
batch a task is cut from its predecessor's head instead, which need not be its parent.
A dependency there is met by a layer below it in the same stack, or by the default
branch.

**Retired spec**: A spec the operator moved to `.saffron/specs/done/`, asserting
that its work is in the default branch. Not offered to the scan. It admits a
dependent the same way a `MERGED` task does. Retiring it makes the assertion the ledger cannot
make, because only a cell writes a task.

**Tree base**: The commit a task's worktree is built on and its patch is exported
against. It is `base_sha` for an ordinary task, and the parent's branch head for a stacked
one. Recorded in `patch.json` beside `base_sha`, which stays the run's pin: gates
and policy are exported from the pin either way.
_Avoid_: using it and `base_sha` interchangeably. They differ for exactly one kind
of task, and that is the kind every consumer of either has to be right about.

---

## 7. Repos

**Policy**: `.saffron/policy.yaml` in a target repo: gate roles and blocking
levels, `elevate_on`, protected paths, envelope defaults, `integrity` patterns,
thread env. Everything repo-shaped that is not an executable.
_Avoid_: "config", "settings", "the manifest".

**Cell image**: Built from the repo's `.saffron/Dockerfile`, `FROM` a Saffron base
image. Carries the toolchain, services, migrations, and seed data.
_Avoid_: "the container image" when the distinction from a base image matters.

**Base image**: `saffron/cell-base:<runtime>`. Agent runtime and git. Nothing
else, ever. In particular, it carries no gate shim. The host `exec`s the repo's own gate
executables through the runtime, so a shim would have nothing to do (§2.1).

**Fixture services**: Whatever a repo bakes into its cell image to make its tests
meaningful: a database, a cache, nothing at all. Never anything the operator runs
for real, which no cell can reach.
_Avoid_: "the test DB", "the local DB", naming a specific engine as though every
repo has one.

**Onboarding**: Writing a repo's `.saffron/` directory. It touches zero lines of
Saffron. If it does not, the core/repo boundary failed.

**Preflight**: Per-repo readiness at batch start: mirror fetch, policy parse, image
rebuild, baseline. A repo that fails preflight is skipped, not fatal.
A task has a preflight of its own. Each `PreflightEvent` is one step of it, written by
`events.Preflight`. The steps include the proxy, the image build, the port probe and the
worktree coming online.
A baseline that aborts inside the task's cell ends the task in
`PREFLIGHT_FAILED`. That is fatal to the task, where the per-repo sense skips a repo.

---

## 8. Artifacts

**Ledger**: The SQLite database at `~/.saffron/ledger.db`. Authoritative for state.
Item 170 makes it an index that `saffron fold` rebuilds from the record on
`refs/saffron/*`. It stays authoritative until a caller constructs it with a record.
_Avoid_: "the DB" (ambiguous with fixture services inside a cell), "the store".

**Batch tree**: The plain directory tree of artifacts under
`~/.saffron/batches/`: transcripts, diffs, gate logs. Greppable on purpose.
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
`run_finished`, `run_preflight`, `batch_created`, `batch_closed`, `repo_upserted`,
`stack_layer`, `end_review`, `qualification`, `spec_review`, `spec_finding`,
`spec_text`, `stack_finish`.
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
_Avoid_: "origin" (that is the real remote, reachable only from the host).

**Index**: The static page listing one line per task across a batch. An index, not a
viewer, because the diffs live in GitHub.
_Avoid_: "dashboard", "the queue UI", "the report", "dossier".

**Queue line**: One task's entry in the index. While the task runs, it is a live row
holding the phase state. Once the task ends, it is the outcome summary. It is never a
"verdict", which belongs to findings.

---

## 9. Flywheel

**Rejection**: An operator decision to reject or request changes, plus the one-line
reason appended to `.saffron/rejections.md`.

**Bucket**: One of the three destinations a rejection is triaged into: a gate
(bucket 1), a `CLAUDE.md` line (bucket 2), a lens amendment (bucket 3). Cheapest
first.
_Avoid_: "category", "type", "tier".

**Promote**: To move a rule toward bucket 1: lens to `CLAUDE.md`, or `CLAUDE.md`
to a gate. The direction a rule must always travel.
> Name the destination, never the direction. The buckets print 1, 2, 3 but are
> ordered cheapest-first. So "up" and "down" point opposite ways depending on
> whether you mean the page or the cost. Say "promote to bucket 1".

_Avoid_: "automate", "harden", "codify", "promote up", "promote down".

**Scoring run**: One execution of every declared lens over one fixture, in the
harness (`harness/lens_scoring.py`). The qualifier is not optional: bare **run**
is one task's pin (§2), and the harness measures REVIEW rather than
running a night.
_Avoid_: bare "run" for one, "attempt" (that is a phase execution inside a task),
"sample", "trial".

**Scoring pass**: A set of scoring runs over one fixture, scored together and
recorded under `docs/evidence/passes/`. Its n is part of its result. A k/n
without its n is the shape item 69 charged the mutation-vs-lens record with.
_Avoid_: bare "pass". That is a gate status, and `_Avoid_` under **Attempt**
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
  sample output, states appear bare, because backticks are prose markup, not part of the
  name.
- Phases in bare caps: DIAGNOSE, IMPLEMENT, REVIEW.
- Gate names lowercase in backticks: the `revert` gate, not the Revert gate.
- Gate statuses lowercase in backticks: `pass`, `fail`, `skip`, `error`.
- Severities lowercase in backticks: `blocker`, `concern`, `note`.
- Spec IDs with the repo prefix: `TE-0142`, `SA-0001`.
- Refer to a document section by number when precision matters: "§5.4", not "the
  gates section". Section numbers in `DESIGN.md` are stable and are cited by specs.
- "The agent" is singular and generic. Name the role when the role matters.

---

## 11. Design record

Where a decision Saffron made is written down. Every genre here is addressed by a
citation rather than a path: "principle 34", "Appendix G", "ADR 1", "§5.4". The reason is that specs,
prompts and evidence records all cite them, and a record addressed by path moves
when the path does. Distinct from the **run record** (`DESIGN.md` §4.6), which is
what the factory produced. The design record says why the factory has the shape it has.

**Principle**: A numbered lesson in one global sequence, stating what generalizes
past the case that found it. Contributed by the revision appendix that found it,
never renumbered, cited as "principle 34".
_Avoid_: "lesson", "learning", "takeaway", and "rule". **rule** already carries
three senses here, so it cannot also carry this one. The three are a rule of
conduct in `CLAUDE.md`, a numbered rule inside a `DESIGN.md` section such as
§4.6.2b, and the rules a gate runs.

**Revision appendix**: A record under `docs/appendices/` recording what a revision found:
the live run, the spike, or the read-through, and what it cost. It carries the
narrative a principle compresses. Cited by letter: "Appendix G". Usually one per
revision, and not reliably so: a revision that *closes* an earlier revision's
question lands in that question's appendix rather than opening its own. Appendix G
carries rev 8 and rev 10, Appendix O rev 18 and rev 19.
_Avoid_: "the changelog" (an appendix records what was *learned*, not what
changed), "release notes", "the postmortem".

**Evidence record**: A dated document under `docs/evidence/` holding what one run
or one spike produced. The primary record: a measured fact beats a
reasoned one, and this is where the measurement lives.
_Avoid_: "the writeup", "the report" (`saffron/report/` renders the index, so the
word would name either),
"the log" (that is a batch tree artifact).

**Spike verdict**: A bounded document answering the one question a spike was run to
answer, carrying the clause that would reopen it (`ontology/RATIONALE.md`). A
negative verdict is still the deliverable (principle 10).
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

1. **run vs. batch**: *not* synonyms. A **batch** is one night across repos and
   owns the budget. A **run** is one task's pin and owns `base_sha` and the
   baseline. They diverged when Saffron went multi-repo and kept sharing a table,
   which left a multi-repo night with no identity to query. The ledger now has a
   `batches` table. The third sense, one gate execution, is retired: it is a
   **gate result**.

2. **verdict**: three judgements, not two, defined under Review above. The
   operator's judgement was previously folded into `decisions.reason`, which made
   the critic-ROI question unanswerable.

3. **Docker vs. the cell runtime**: "Docker" was never a decision, only a
   proper noun that read as one. It survived seven revisions and an
   adversarial review on that basis. The runtime is chosen at v0.5 against a
   four-assertion spike. Until then the word is **cell runtime**. Same shape as
   the two above: a word hiding a design defect rather than a word choice
   (Appendix G, principle 32).

4. **ADR vs. the design record**: Saffron keeps no ADRs, and never did. `CLAUDE.md`
   and `docs/agents/domain.md` promised `docs/adr/` from the day the engineering
   skills were given a repo config to read (`26ce379`). The directory was the
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

5. **Claude Code vs. the delegate**: a model session on the host had no name, so
   it was called by its product. The product name hid the fact that shapes
   the design. A delegate acts on the operator's behalf, under their identity, and none
   of its work is recorded as a task's. So the ledger cannot tell it from the
   operator. The word is PROV-O's (`prov:actedOnBehalfOf`), chosen for the
   alignment. "Surrogate" was considered and dropped, and so was "works to no
   plan". Both rested on a delegate never being handed a plan, and a delegate can be
   handed one. PROV-O puts `prov:hadPlan` on an association, and a plan binds no one who is
   not checked against it. Same shape as 3: a proper noun standing where a role
   was never named (principle 32).

6. **`saffron:` vs. `factory:`**: the vocabulary's namespace carried the
   program's name. The vocabulary describes the arrangement: gates, cells,
   target repos, the operator and their delegates. That arrangement is the **factory**. The prefix
   is `factory:` and the IRI `urn:software-factory:ns#`, a URN so that it cannot
   resolve (`DESIGN.md` §1.4). Every use was rewritten, dated records included.
   `saffron:retired-by` was not: it is a marker in source that the scheduler
   reads, not a vocabulary term, and shares only the spelling.

7. **the spec reviewer vs. a spec review**: a delegate reading a spec before its
   first cell was named "the spec reviewer". "The reviewer" was already the
   operator and a lens's avoided name. The seat had an occupant, and the name hid
   what separates this one: its `blocker` cannot route to REBUT, because no task
   exists yet, so it reaches the operator. It is named as an activity a delegate
   performs. `spec-reviewer` stays as the agent definition's file and id, which
   the loop invokes and the backtest's frozen reports cite.

8. **approve vs. mark ready**: GitHub refuses an author's own approval, and PACKAGE
   opens every pull request as the operator. So `APPROVED` had no writer, and the
   step that admits a task to the merge train had no signal. The operator's act is
   marking PACKAGE's draft ready, and reconcile records it as `APPROVED` (backlog
   item 52). **Approve** keeps its name for the act, and the state keeps
   `APPROVED`, since `DESIGN.md` §3.3 and §6.1 use both. "Mark ready" names the
   mechanism only. Avoid "approve" for GitHub's review approval, which PACKAGE's
   author cannot give. Until a train exists, the act admits a task to nothing.

## Open naming decisions

Add here rather than resolving in prose elsewhere. An ambiguity that gets settled
in a commit message is an ambiguity that comes back.

1. **A word for what a gate result and a finding both are.** `DESIGN.md` §4.6 treats
   a `mypy` failure and a critic blocker as one shape. That shape is *an assertion, by an
   agent, about a subject, with an outcome*. The same section calls the two-table split "worth
   reconciling in §4.1". §4 and §5 here reproduce that split with no shared term. So
   the sentence the ontology exists to make cannot be written in Saffron's own
   vocabulary. Left open deliberately: coining a supertype before §4.1 reconciles
   would put a word here that nothing says. Resolve when the schema does, or record
   that it never will.
