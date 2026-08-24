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
cell — chosen in rev 10 against a four-assertion spike (`DESIGN.md` Appendix G).
Say "the cell runtime"; the seam is `saffron/cell/runtime.py` and it stays the only
module that names the product, because a decision made by spike can be remade by
spike.
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
_Avoid_: "the AI", "the bot", "the LLM". "Model" means a model identifier.

---

## 2. Work

**Spec**: A markdown file with YAML frontmatter at `.saffron/specs/` in a target
repo. The unit of work, written by the operator.
_Avoid_: "ticket", "issue", "story", "request", "prompt".

**Task**: One spec being executed — a ledger row with a state, a branch, a budget,
and a cell. A spec is the input; a task is the execution.
_Avoid_: "job", "work item", "unit".

**Batch**: One night's execution, spanning every selected repo. One budget, one
concurrency pool, one `--until`.
_Avoid_: "session" (that means an agent session), "cycle", "sweep", "run".

**Run**: One repo's slice of a batch, owning its own `base_sha`, preflight outcome,
and baseline. A batch contains one run per repo.
> Batch and run are **not** synonyms and stopped being interchangeable when Saffron
> went multi-repo. Budget is a batch property; `base_sha` is a run property. If a
> sentence works with either word, it is imprecise.

_Avoid_: "run" for a single gate execution — that is a **gate result**.

**Phase**: A named stage in the cell pipeline — DIAGNOSE, IMPLEMENT, GATE ⇄ REPAIR,
REVIEW, REBUT, PACKAGE. Written in bare caps.
_Avoid_: "stage", "step", "mode".

**Attempt**: One numbered execution of a phase. Attempts are bounded on five axes —
turns, spend, idle, completion, and wall clock. "Attempt 3" without a phase is
ambiguous — name both.
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

**Touches**: The set of paths a task may change. Declared directly on non-bug specs;
proposed by DIAGNOSE and ratified by the operator on bug specs. Once fixed it feeds
the conflict set and the `scope` gate.

**`scope` gate**: The check that changed files are a subset of `touches`.

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
when the diff touches a path in the repo's `elevate_on`. Elevated adds the third
lens and makes `size` blocking. It does **not** make `coverage` blocking —
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
(`DESIGN.md` §5.4, Appendix H).
_Avoid_: "the version", "the tool name" — it is neither on its own, and a string
literal in a gate script is not a `tool` value at all.

**Gate role**: A name in the contract — `format`, `lint`, `types`, `tests`,
`no-network`, `coverage`. The repo supplies the executable; core supplies the
meaning.

**Gate**: One named verification, host-invoked and deterministic. Written lowercase
in backticks. Three kinds, and the distinction is the core/repo boundary:

- **Core gates** — `scope`, `size`, `secrets`, `integrity`, `census`, `committed`.
  Implemented in Saffron. They never execute repo code, which is why they can be
  core; most read the diff, but `committed` reads the worktree's status instead
  (`DESIGN.md` §2.1).
- **Contract gates** — the gate roles above. Declared in `policy.yaml`, implemented
  in the repo's `.saffron/gates/`.
- **Repo-defined gates** — anything a repo adds against its own hard-to-fake
  surfaces, conditional on touched paths. Names vary by repo and are not vocabulary.

_Avoid_: "check", "validation", "CI" (there is no CI), "the linter" for the `lint`
gate. _Avoid_ naming any repo-defined gate here as though it were universal.

**Gate result**: One execution of one gate against one attempt.
_Avoid_: "gate run" — "run" means a repo's slice of a batch.

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

---

## 5. Review

**Critic**: The adversarial reviewer. A fresh, read-only session that never sees the
implementer's transcript.
_Avoid_: "the reviewer" (that's the operator), "QA", "the checker".

**Implementer**: The session that holds write tools during IMPLEMENT and REBUT.
_Avoid_: "the coder", "the writer", "the worker".

**Lens**: One critic perspective with a bounded remit — correctness & data
semantics, contract & schema, blast radius. Lenses are disjoint by construction,
which is why any single blocker routes to REBUT and why there is no vote.
_Avoid_: "reviewer", "pass", "check", "critic #2".

**Finding**: Anything a critic reports, pointing at a specific changed line.
_Avoid_: "issue", "comment", "bug", "problem".

**Anchored**: A finding that either falls inside a diff hunk, or cites a line
naming an identifier the diff changed. The second target is what keeps the
blast-radius lens usable, since its findings point at code the diff did not touch.
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
`PLAN_REJECTED`, `EXHAUSTED`, `READY_FOR_REVIEW`, `MERGE_FAILED`, `RATE_LIMITED`.
Everything else is internal.

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

---

## 8. Artifacts

**Ledger**: The SQLite database at `~/.saffron/ledger.db`. Authoritative for state.
_Avoid_: "the DB" (ambiguous with fixture services inside a cell), "the store".

**Batch tree**: The plain directory tree of artifacts under
`~/.saffron/batches/` — transcripts, diffs, gate logs. Greppable on purpose.
_Avoid_: "artifact store", "the logs", "the run tree".

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

## Settled naming decisions

Recorded because both were live ambiguities and both turned out to be design
defects rather than word choices (`DESIGN.md` Appendix E).

1. **run vs. batch** — *not* synonyms. A **batch** is one night across repos and
   owns the budget; a **run** is one repo's slice and owns `base_sha` and the
   baseline. They diverged when Saffron went multi-repo and kept sharing a table,
   which left a multi-repo night with no identity to query. The ledger now has a
   `batches` table. The third sense — one gate execution — is retired: it is a
   **gate result**.

2. **verdict** — three judgements, not two. The critic **verdicts** a finding, the
   operator **adjudicates** it, the implementer **rebuts** it, and the morning
   index shows a **queue line**. The operator's judgement was previously folded
   into `decisions.reason`, which made the critic-ROI question unanswerable.

3. **Docker vs. the cell runtime** — "Docker" was never a decision, only a
   proper noun that read as one, and it survived seven revisions and an
   adversarial review on that basis. The runtime is chosen at v0.5 against a
   four-assertion spike; until then the word is **cell runtime**. Same shape as
   the two above: a word hiding a design defect rather than a word choice
   (`DESIGN.md` Appendix G, principle 32).

## Open naming decisions

None. Add here rather than resolving in prose elsewhere — an ambiguity that gets
settled in a commit message is an ambiguity that comes back.
