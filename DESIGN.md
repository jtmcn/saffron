# Saffron — System Design

An agentic software factory: spec files in, reviewed pull requests out, running unattended overnight on one Mac.

**Status:** rev 10 — the cell runtime is `apple/container`, decided by spike rather than deferred (Appendix G). Prior: rev 2 post adversarial review (Appendix A); rev 3 factory ontology (Appendix B); rev 4 repo-agnostic (Appendix C); rev 5 prior art (Appendix D); rev 6 vocabulary corrections (Appendix E); rev 7 read-through defects (Appendix F); rev 8 cell runtime named (Appendix G); rev 9 v0 built and replayed (Appendix H)

**Companion document:** `CONTEXT.md` — the controlled vocabulary. It is authoritative for what words mean; this document is authoritative for what the system does. Where they disagree, one of them has a bug.
**Scope:** language- and stack-agnostic. Saffron develops *any* repo that can satisfy the gate contract (§5.4). First repo is Saffron itself; `thermal-edge` is the first external one.

> **Section numbers are an API.** `.saffron/specs/` cites this document by section (`SA-0001` references §4.1, §5.1, §5.6, §7.1, §8, §11, N5). Numbering is therefore held stable across revisions — new material is added as subsections, never by renumbering.
**Author of record:** Joel · Aug 2026

---

## 0. The one-paragraph version

Saffron is a Python orchestrator that reads spec files committed to a target repository, assigns each to an isolated containerized agent working in its own git worktree, drives that agent through a hard gate loop until the change is objectively green, subjects the resulting diff to an adversarial reviewer that tries to prove it wrong, and packages everything into a pull request plus a one-line verdict in a morning queue. Joel merges. Nothing else merges.

The important inversion: **the product of this factory is not code, it is a reviewable artifact.** Code is cheap now. Your attention is the scarce resource, and every decision below is ultimately about spending less of it per accepted change. That principle also disqualifies designs that quietly move work back onto you — see §5.2, where it kills the most obvious version of scope control.

---

## 1. Requirements

### 1.1 Functional

| # | Requirement |
|---|---|
| F1 | Discover spec files in a target repo, validate them against a schema, and enqueue them as tasks |
| F2 | Execute tasks unattended in batches (nightly), respecting dependencies and file-conflict sets |
| F3 | Isolate each task: own branch, own filesystem, own database, own process |
| F4 | Enforce hard verification gates; let the agent self-repair against gate output for a bounded number of attempts |
| F5 | Run an independent adversarial review of the final diff before anything reaches the human queue |
| F6 | Produce a PR per task carrying spec, plan, gate results, findings, and cost |
| F7 | Present a single morning index across the whole batch |
| F8 | Re-verify on merge, not just in isolation |
| F9 | Record every run durably: transcripts, tool calls, gate output, spend |
| F10 | Reclaim resources from killed, crashed, and orphaned tasks without operator intervention |
| F11 | Operate on any repository, in any language, via a declared contract — **onboarding a repo requires no change to Saffron's source** |
| F12 | Run a batch spanning multiple repos, sharing one concurrency pool and one budget |

### 1.2 Non-functional

| # | Requirement | Target |
|---|---|---|
| N1 | Unattended safety | Zero writes to real infrastructure, prod DB, or remote `main` — enforced structurally, not by prompt or by in-agent hook |
| N2 | Bounded spend | Per-attempt, per-task, and per-batch USD ceilings; hard stop, enforced host-side against reported spend (§4.1) |
| N3 | Bounded time | Batch completes inside the sleep window (~8h) or is killed and reclaimed cleanly |
| N4 | Throughput | 3 concurrent tasks on a 32GB M-series Mac; 6–12 accepted PRs per week |
| N5 | Auditability | Any merged change reconstructible from stored artifacts alone — expressed as a derivation-chain query, so it is checkable rather than asserted (§4.6) |
| N6 | Operability | Single operator, zero standing services beyond the cell runtime; `saffron` is one CLI |
| N7 | Recoverability | Crash mid-batch resumes without losing completed work or leaking disk |
| N8 | Onboarding cost | A new repo is productive after writing one `.saffron/` directory — target: an afternoon, not a Saffron release |

### 1.3 Constraints

- One machine (Mac; every container runtime here is a Linux VM), one operator, part-time attention.
- **Saffron's harness is Python. The repos it works on are any language.** These are unrelated facts and the design must not let them become related.
- API auth must reach a container without leaking any target repo's credentials into it.
- **The generality is aspirational until proven.** The first two repos (Saffron, `thermal-edge`) are both Python. The language seam will be *designed* long before it is *exercised* — §7's "premature generality" row exists because of this, and §9 treats the third repo as the real test.
- **Every container runtime on macOS is a VM, and the VM is one per cell (`apple/container`, settled in rev 10 by the spike in Appendix G).** Bind-mount I/O is slow, host firewall rules don't see container traffic, and no runtime can pin a container to a physical core. A per-cell VM means there is no single fixed memory allocation to divide by K, and it means the guest's visible core count is structural rather than declared. Several design decisions below fall out of these facts.

### 1.4 Explicit non-goals for v1

- Multi-tenant / multi-user. One operator.
- Autonomous merge. Never, at any version.
- Cloud runners. Local only until throughput actually binds.
- Agents writing their own specs from a roadmap. That's v3 and it's the part most likely to waste money.
- A bespoke diff viewer. GitHub already built the best one you'll ever have (§6).
- An ontology-*driven* orchestrator. The factory ontology (§4.6) **describes** the run record; it never controls execution. SHACL shapes validate the projection; they do not gate state transitions, and no scheduling decision reads a triple.
- Publishing the vocabulary at a resolvable IRI, or `owl:imports` of external ontologies at run time. Cells have no network (§5.1); external vocabularies are vendored and committed.
- **Language auto-detection, or a plugin system.** A repo declares what it is; Saffron does not sniff for a `package.json`. Declaration is one file the repo owner writes once; detection is a heuristic that fails silently on the tenth repo.
- **A gate marketplace / shared gate library.** Gates are shell programs in the repo. Copy-paste between repos beats a dependency for the first ten repos, and probably forever at this scale.

This list is a **living refusal record**, not a one-time scoping exercise. Each entry gets what it costs: the thing refused, why, and which existing seam covers it instead. The failure mode it guards against is specific and it is the default trajectory of any personal tool — *a factory accretes one knob per bad night.* A written refusal turns the fifth time you want a feature into a link rather than an argument with yourself at 7am. Adding to this list is a normal outcome of a morning review, and so is deleting from it when a refusal stops being right.

---

## 2. High-level architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ANY TARGET REPO   (saffron · thermal-edge · …)                          │
│                                                                          │
│   .saffron/                                                              │
│     specs/         XX-0001-….md                   ← unit of work         │
│     policy.yaml    gate roles, budgets, protected paths, envelopes       │
│     gates/         executables emitting the gate JSON contract (§5.4)    │
│     Dockerfile     cell image; FROM a saffron base                       │
│   CLAUDE.md        standing agent instructions (the learning surface)    │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ git (local bare mirror, no network)
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  SAFFRON CONTROL PLANE   (host process, Python, ~/Code/saffron)          │
│                                                                          │
│   intake ─▶ gc ─▶ scheduler ─▶ supervisor ─▶ gate runner ─▶ packager     │
│      │                 │            │            │             │         │
│   validate      conflict sets   run/kill    HOST-INVOKED    PR + index   │
│                 dep DAG        containers   deterministic                │
│      ▼                                                                   │
│   ledger (SQLite)  +  batch tree (~/.saffron/batches/…, plain files)     │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ exec / stdio
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
     ┌─────────────────┐  ┌──────────┐  ┌──────────┐
     │  CELL #1        │  │ CELL #2  │  │ CELL #3  │  ← one container per task
     │                 │  └────┬─────┘  └────┬─────┘
     │  /work worktree │       │             │
     │  fixture svcs   │       │             │
     │  agent proc     │       ▼             ▼
     │  no credentials │  ┌───────────────────────────┐
     │  no default rte ├─▶│  egress proxy (allowlist) │──▶ api.anthropic.com
     └─────────────────┘  └───────────────────────────┘    package mirror
```

Three planes, deliberately separated:

- **Control plane** (host, trusted): decides *what* runs, *when*, and *whether the result is acceptable*. Holds all state. Runs the gates. Never executes model-authored code.
- **Cells** (containers, untrusted): where agents and their code execute. Assume everything inside is adversarial.
- **Ledger + batch tree** (host, append-mostly): the audit trail.

The single most important line in this document: **a cell is untrusted, and "untrusted" means every control that matters lives outside it.** Concretely, the controls that hold regardless of agent cooperation are: no target-repo credentials in the container — the agent's own API key being the one exception, and §5.1 states it as part of the rule rather than beside it — no default route except through an allowlisting proxy, the only git remote is a local bare mirror, and the gate runner is invoked by the host and reports to the host. Prompts and in-agent hooks are *inside* the cell — they shape behavior and reduce wasted turns, but they are not the boundary and must never be counted as one (§5.3).

### 2.1 The core/repo boundary

Saffron is repo-agnostic, which is a claim that only means something if you can say precisely where the knowledge lives. The rule:

> **Saffron knows about diffs, git, containers, budgets, and the shape of a gate result. It knows nothing about languages, test runners, package managers, or databases. Everything in the second list lives in the target repo's `.saffron/` directory.**

The consequence is F11: **onboarding a repo touches zero lines of Saffron.** If adding a Rust project requires a `rust.py` in the orchestrator, the boundary has already failed.

| Concern | Owner | Why |
|---|---|---|
| Spec schema, task state machine, scheduler, budgets | **Core** | Universal; nothing language-shaped about a dependency edge |
| Worktree, bare mirror, branch/PR mechanics | **Core** | git is git |
| Cell lifecycle, network policy, resource limits | **Core** | Containers are containers; the runtime hides behind one module (Appendix G) |
| `scope`, `size`, `secrets` gates | **Core** | Operate on the diff as text and paths — no language knowledge needed |
| `integrity` gate logic | **Core**, patterns from repo | "Was a test deleted or suppressed?" is universal; *what a test file looks like* and *what a suppression comment looks like* are not |
| `revert` gate | **Core** logic, the repo's `tests` gate as runner | The sanctioned exception below: core re-invokes a declared gate, it does not run a tool |
| `format`, `lint`, `types`, `tests`, `no-network` | **Repo** | Executables satisfying the gate contract |
| Cell image, services (DB, cache, …), fixtures | **Repo** | `.saffron/Dockerfile` and a declared service list |
| Risk-elevation paths, protected paths, envelope defaults | **Repo** | `policy.yaml` |
| Standing agent instructions | **Repo** | `CLAUDE.md` |

Saffron ships thin base images (`saffron/cell-base:python`, `:node`, …) carrying the agent runtime, git, and the gate-runner shim — and nothing else. A repo's `.saffron/Dockerfile` starts `FROM` one of those and installs whatever it needs. Saffron never installs a toolchain on a repo's behalf.

**The seam to watch.** Most core gates are core precisely because they read the diff rather than run the code. That is not a coincidence and it is worth protecting: every time a proposed core gate needs to *execute* something in the repo, it belongs on the repo side of the line.

**The one sanctioned exception is `revert` (§5.4), and the shape of the exception is the real rule.** `revert` does run something — but what it runs is a gate the repo already declared, invoked through the same JSON contract as every other gate, with one extra argument. Core still knows nothing about the toolchain: it knows only that a `tests` gate exists and that the contract obliges it to accept a test subset. So the rule is not "core never executes"; it is **core invokes declared gates, never tools.** Any future core gate that wants to run something must fit that shape or move to the repo side. Stated positively because the absolute version was false the moment `revert` was added — and a rule with an unstated exception is a rule that has quietly been abandoned.

The moment core code branches on language, the boundary is gone and you have a monolith with a config file.

---

## 3. The unit of work: spec files

### 3.1 Where specs live — and why

Specs live in the **target repo**, at `.saffron/specs/`, not in Saffron.

| | Specs in target repo (chosen) | Specs in Saffron |
|---|---|---|
| Spec travels with the code it changed | ✅ git history shows asked-vs-built | ❌ split-brain |
| Multi-repo factory | ✅ Saffron stays generic | ❌ Saffron accumulates repo knowledge |
| Spec references code paths | ✅ same tree, checkable | ❌ stale references |
| Merge noise in target repo | ❌ specs churn alongside code | ✅ clean |
| Saffron can improve itself | ✅ point it at `~/Code/saffron` | ✅ |

The merge-noise cost is real but small, and it buys the thing that matters at review time: opening a PR and seeing the original ask, verbatim, in the same tree.

### 3.2 Spec format

Markdown with YAML frontmatter. Machine-checkable header, human-written body. The schema is core; everything it references (paths, gate names, risk paths) is the repo's. The example below is from one repo's `.saffron/specs/` and is illustrative — a Rust repo's spec has identical structure and different nouns.

```markdown
---
id: TE-0142
title: NWS forecast ingest has produced no rows since 2026-08-11
type: bug                       # feature | bug | refactor | test | docs | chore
priority: 2
depends_on: [TE-0139]           # satisfied at READY_FOR_REVIEW, see §4.2
envelope:                       # outer bound for DIAGNOSE; required for bugs
  - src/thermal_edge/**
  - tests/**
touches:                        # optional for bugs — agent proposes, you ratify (§5.2)
forbidden:                      # hard deny, beyond global protected paths
  - alembic/versions/**
budget_usd: 12
max_attempts: 4
risk: standard                  # standard | elevated (§5.6)
---

## Context
`forecast_raw` has received no rows from any of the three providers since
2026-08-11. The sync job logs success. Ops note: docs/ops/2026-08-11-gap.md.

## Problem
State the observable defect, not the suspected cause.

## Acceptance criteria
- [ ] A regression test exists that fails on the current `main`
- [ ] `forecast_raw` receives rows for all ERCOT zones over a 48h backfill
- [ ] The silent-success path is removed: ingest raises on zero-row responses
- [ ] No change to the `forecast_raw` schema

## Out of scope
Kalshi sync errors. Portfolio snapshot staleness. Separate specs.

## Notes for the agent
Fixtures in `tests/fixtures/nws/`. Do not hit the live NWS API; use the
recorded cassettes. Timescale hypertable — watch chunk boundaries on backfill.
```

Design notes:

- **`envelope` vs `touches` is the central fix in rev 2.** For features and refactors you know the blast radius, so you write `touches` directly and it is enforced from the start. For **bugs you do not know the blast radius — that's what a bug is.** Requiring you to declare it means you must diagnose before the agent does, which inverts the entire economics (you do the expensive part; the agent types). So for bugs you declare a loose `envelope`, the DIAGNOSE phase proposes a `touches` set inside it, and you ratify that in one click (§5.2). Hard scope enforcement survives; human pre-diagnosis does not.
- **`touches`, once fixed, is load-bearing.** It feeds the conflict-set scheduler (§4.2) and the `scope` gate (§5.4). An agent that wanders outside it fails mechanically.
- **Acceptance criteria are checkboxes** because the packager renders them into the PR body as a checklist, and the critic is handed them as its rubric.
- **"Out of scope" measurably reduces sprawl.** Agents are eager. Naming the adjacent broken things stops them from opportunistically fixing three of them in one unreviewable diff.
- **No `estimated_diff_lines`.** A self-reported number from the model being gated is not a gate. Size is enforced post-implementation where it's measurable, and at plan time via `len(files_to_change)`, which is checkable against `touches`.

### 3.3 Task state machine

```
  DRAFT ──▶ QUEUED ──┬─(bug)──▶ DIAGNOSING ──▶ SCOPE_REVIEW ──▶ (you: 1 click)
                     │                              │
                     └─(other)─────────────────────▶│
                                                    ▼
                                          IMPLEMENTING (plan checkpoint inside)
                                                    │
                                          PLAN_REJECTED ──▶ (you)
                                                    │
                                                    ▼
                                            GATING ⇄ REPAIRING ──▶ EXHAUSTED
                                                    │                  ▲
                                                REVIEWING              │  gates red
                                                    │                  │  after rebuttal
                                                REBUTTING ─────────────┘
                                                    ▼
                                          READY_FOR_REVIEW ──▶ (you)
                                                    │
                          ┌─────────────────────────┼──────────────────────┐
                          ▼                         ▼                      ▼
                      APPROVED             CHANGES_REQUESTED           REJECTED
                          │                         │                      │
                     MERGE_TRAIN               (re-queue)              LEARN (§8)
                          │
                   MERGED / MERGE_FAILED

  ORPHANED ◀── any state, on crash/kill; reclaimed by `saffron gc` (§4.5)
```

Terminal states that reach you: `SCOPE_REVIEW`, `PLAN_REJECTED`, `EXHAUSTED`, `READY_FOR_REVIEW`, `MERGE_FAILED`. Everything else is internal.

---

## 4. Control plane

### 4.1 Ledger and batch tree

**SQLite**, one file, WAL mode, at `~/.saffron/ledger.db`.

Not Postgres, not Timescale, despite that being home turf. Single writer, single machine, no ops, trivially backed up — and the real reason: the ledger must survive the cell runtime being down, your Postgres being mid-migration, or the factory having broken its own environment. A dependency-free state store is what lets Saffron recover from Saffron.

```sql
batches      (batch_id, started_at, ended_at, budget_usd, spent_usd_est,
              concurrency, until_ts, status)
repos        (repo_id, name, origin, mirror_path, policy_sha, image_tag,
              image_built_at, enabled)
runs         (run_id, batch_id, repo_id, base_sha, preflight, started_at,
              ended_at, status)
tasks        (task_id, run_id, spec_id, spec_sha, state, priority, risk, branch,
              parent_task_id, worktree, volume, budget_usd, spent_usd_est, updated_at)
attempts     (attempt_id, task_id, phase, n, session_id, model, started_at,
              ended_at, subtype, terminal_reason, num_turns, cost_usd_est)
gate_results (gate_result_id, attempt_id, run_id, gate, status, duration_ms,
              summary)
failures     (failure_id, gate_result_id, file, code, message, line)
findings     (finding_id, task_id, lens, severity, file, line, claim, anchored,
              verdict, adjudication, rebuttal)
decisions    (decision_id, task_id, actor, action, reason, created_at)
```

**A batch is not a run.** A **batch** is one night: one budget, one concurrency pool, one `--until`, spanning every selected repo. A **run** is one repo's slice of that batch, owning its own `base_sha`, its own preflight outcome, and its own baseline. Rev 4 made these genuinely different and left them sharing a table; a multi-repo night had no identity you could query. Budget lives on the batch, because that is the level it is actually enforced at.

`gate_results`, not `gate_runs` — "run" was doing three jobs (the nightly event, a repo's slice, one gate execution) and this is the one that had a better name available. It also matches what the gate contract emits (§5.4).

**`failures` is a table, not a log line, and that is load-bearing.** Three separate mechanisms key on `(gate, file, code)` — baseline subtraction, no-progress detection (§5.4), and the flywheel's "which gate was the sole failure" question (§8) — so the identity has to be queryable, not gzipped in the batch tree. A status-only `gate_results` would have made N7 re-derive the baseline by parsing files after a crash, and would have made `SA-0001`'s Q3 unanswerable *in SQL for schema reasons rather than expressiveness ones*, quietly corrupting the SQL-equivalence challenge that spec exists to run. `line` is stored because the PR body and finding anchoring display it; it is not part of the identity (§5.4).

**Exactly one of `attempt_id` and `run_id` is set**, and the null is the point: a gate result belongs to an attempt, *except* the baseline suite (§4.4), which runs against a run's `base_sha` with no agent, no session and no cost. Rev 7's schema had no column that could hold it. This is also §4.6's first criticism showing its teeth from the other side — `findings` stored `file`, `line` and `claim` in full while `gate_results` stored none of it, which is a strange asymmetry between two things the PR body already renders as one table.

`findings` carries three distinct judgements and they must not collapse into one column: **`verdict`** is the critic's own confirm-or-withdraw at REBUT; **`adjudication`** is the operator's agree/disagree, which §4.6 flagged as belonging in a typed field rather than folded into `decisions.reason`, and which is the entire basis of the critic-ROI query; **`rebuttal`** is the implementer's argument. `anchored` records whether the finding survived reconciliation against the diff (§5.5) — dropped findings are kept, not deleted, because the drop rate is the signal that a lens is badly prompted.

**`cost_usd_est`, and the suffix is not decoration.** Every dollar figure the agent runtime reports is a *client-side estimate*, computed locally from a price table bundled into the SDK at build time. It drifts when pricing changes, when the installed SDK doesn't recognize a model, and when billing rules apply that the client cannot model; the runtime's own documentation says not to make financial decisions from it. Saffron makes exactly one financial decision from it — the budget gate (§4.2) — and that is acceptable because the consequence of drift is a night that costs somewhat more or less than $50, not a wrong answer. What is *not* acceptable is `spent_usd` silently becoming the number you reason about in §7.1, so the estimate carries its suffix everywhere it is stored, and cost-per-accepted-PR is reconciled against real billing periodically rather than trusted outright. **A column named for a measurement it cannot make is how an estimate becomes a fact.**

`terminal_reason` exists for the same reason the supervisor measures doneness from git (§4.3): the agent runtime distinguishes a clean finish from an abort, and a crashed session (`subtype = error_during_execution`) **may report every cost field as zero**. An attempt that burned $4 and then crashed records $0 unless the supervisor falls back to the last good figure it saw before the crash. Unattended overnight, this is the difference between a budget that holds and one that silently stops counting.

`spec_sha` matters: edit a spec while a batch is running and the task is invalidated rather than silently building the old thing. `policy_sha` does the same one level up — change a repo's gate declarations mid-batch and its in-flight tasks are invalidated, because a task judged against a policy that no longer exists is not evidence of anything. `image_built_at` versus the `.saffron/Dockerfile` mtime is what triggers a rebuild at preflight.

**Both invalidations need a moment to fire at, and it is a mirror refetch at task scheduling.** Preflight fetches once and pins `base_sha` (§4.4), so nothing else in the batch ever re-reads the repo — which would leave these two columns recording a check that structurally cannot happen. The scheduler therefore refetches the mirror before each task starts and compares both shas then; it is a local `git fetch` against a bare repo, it costs milliseconds, and it is the only point in a batch where a mid-flight edit can be noticed at all. Note what this deliberately does *not* do: `base_sha` stays pinned for the whole run, so a refetch invalidates tasks and never moves the baseline out from under them.

Artifacts — transcripts, diffs, gate logs, coverage XML — go in a **plain directory tree**, not a content-addressed store:

```
~/.saffron/batches/<batch_id>/<repo>/<task_id>/<phase>/<n>.{log.gz,json,diff}
```

Content addressing would dedupe repeated gate output, but the volume is tens of MB a night. A plain tree is greppable with `rg`, inspectable when the ledger itself is what's broken, and navigable at 7am without a tool. Dedupe you don't need is not worth losing `ls`.

### 4.2 Scheduler

Selects the next runnable task when a cell frees:

0. **Refusal gate — decided before a cell starts, and it is the cheapest gate in the system.** A task is refused outright, with a reason, if: an open unmerged PR from **another task** already targets this spec; its `touches` overlaps an open PR's changed files; the spec is malformed or its `spec_sha` moved; or the repo failed preflight. Refusals cost nothing — no container, no tokens — and land in the morning queue as one line. The instinct is to let the agent discover these and report back; that instinct costs $8 to learn something a `gh pr list` call knew for free. **Every condition you can check without starting a cell, check without starting a cell.**
   > *Another* task, because a `CHANGES_REQUESTED` task re-queues (§3.3) while its own PR is still open — the unqualified version refuses every re-queued task in the system, which is the one case this gate is most obviously not for. Refusal is keyed on `task_id`, not on the spec.
1. **Dependency gate** — all `depends_on` tasks have reached **`READY_FOR_REVIEW`** (not `MERGED`). A dependent task branches off its parent's branch rather than `base_sha` — stacked branches.
   > Requiring `MERGED` would mean a dependency can never be satisfied inside a batch, since merging requires your morning approval. A 3-node DAG would take three nights, two cells idle each night. Stacking is the fix; the risk it introduces (parent gets rejected, child is built on sand) is exactly the risk the merge train exists to catch, and it costs one wasted task rather than three wasted nights.
2. **Conflict gate** — the task's `touches` do not overlap any in-flight task's `touches` **in the same repo**, except for a stacked child of an in-flight parent, which is serialized behind it by definition. **File conflicts are prevented by scheduling, not resolved by rebasing.** Conflict sets never span repos; two repos are trivially parallel, which is the one place multi-repo makes life easier rather than harder.
   > **Bugs are scheduled twice, and they have to be.** A bug spec has no `touches` until DIAGNOSE proposes one and you ratify it (§5.2), so at first scheduling both this gate and gate 0's overlap test have nothing to compare — the task is admitted on its `envelope`, which is explicitly never enforced against anything. So **gates 0 and 2 re-run at ratification**, against the ratified set, before IMPLEMENT opens; a bug whose real blast radius collides with an in-flight task waits there instead of being discovered by two agents editing the same file. Checking only at intake leaves the conflict machinery blind for exactly the task type whose scope is least predictable — which is the whole reason DIAGNOSE exists.
3. **Budget gate** — uncommitted batch budget ≥ task budget, where *uncommitted* is `budget_usd − spent_usd_est − Σ(budget of in-flight tasks)`. The task's budget is **reserved when it is scheduled and the unspent remainder released when it reaches a terminal state**, which is the difference between a hard stop and a soft one: comparing against `spent_usd_est` alone lets K tasks each pass the gate on the same last $12 and overshoot by up to K× a task budget, because spend is recognized as it happens and the gate runs before any of it has.
4. **Order** — priority, then dependency depth (unblock the most work), then **round-robin across repos**, then FIFO.

Round-robin matters more than it looks. Straight priority ordering lets one repo with a deep queue monopolize a night, and you wake up to twelve PRs in one codebase and none in the other two — which is worse for review than four each, because your context-switching cost is paid once per repo either way. Interleaving also spreads the risk of a bad night: a repo whose gates are misconfigured burns a third of the budget, not all of it.

**Most of this is v2, and the queue depth is why.** §7.1 sizes a night at 10–15 completed tasks; N4 wants 6–12 accepted PRs a *week*; §9 concedes that spec-writing binds before throughput does. The realistic steady state is therefore a two- or three-deep queue against three cells — and at that depth priority-then-FIFO *is* the scheduler, while conflict sets, round-robin and dependency depth arbitrate contention that never arrives. So v1 builds gate 0, the budget gate, and ordering by priority. The rest is written down here because it is the right answer once the queue is deep, and each piece gets built the first night it actually binds: round-robin when one repo demonstrably monopolizes a night, conflict sets when two tasks first collide, stacking when a DAG first stalls. This is §9's rule about second implementations applied to a scheduler rather than to a language seam — the same rule catches both, and it caught the language seam only because someone wrote it down.

**Dependencies do not cross repos.** A cross-repo `depends_on` would require coordinated merges across two review queues, and there is no version of that which is simple. If two repos must change together, that is one spec in each and a note in both — you sequence them by running one batch, merging, then the next. Stated as a limit rather than discovered as a bug.

Concurrency cap **K = 3**, and rev 10 settles what the arithmetic closes against. With a VM per cell there is no shared allocation to divide: three cells at `--memory 4g` draw 12GB against the whole Mac rather than against a fixed VM allocation, and nothing stands between batches. CPUs divide the same way — `--cpus 1` yields 2 vCPUs per cell (the calibration in §5.1), so K=3 is 6 vCPUs against a host of 11. A repo's fixture services run *inside* the cell, so 4g is the whole budget for a database, the toolchain and the test process together. This is the first number here likely to be wrong; K is the knob, and it turns down. Do not raise K: throughput is model-latency-bound most of the time, but gate runs are not, and oversubscribing makes gate timings flaky — which poisons the repair loop's only signal. **Rev 8 removed the second ceiling this paragraph used to close against.** It was the performance-core count, and no macOS runtime can pin a cell to one (Appendix G), so K is now bounded by memory and by measured gate-time variance rather than by a core enumeration that cannot be performed.

### 4.3 Supervisor

Owns one cell's lifecycle: reconcile → create worktree and volume → start container → run phases → collect artifacts → tear down → mark reclaimed.

Every phase is bounded on five axes, all enforced host-side:

| Axis | Mechanism | Catches |
|---|---|---|
| Turns | `ClaudeAgentOptions(max_turns=…)` | thrash |
| Spend | supervisor sums reported cost against task and batch ceilings; `max_budget_usd` per attempt as an in-cell backstop | expensive thrash |
| Idle | no output for N seconds | a stalled agent |
| Completion | a *short* silence window after the agent signals done | a finished agent whose child process (an MCP server, a spawned CLI) holds stdout open so EOF never arrives |
| Wall clock | `asyncio.wait_for` + container timeout | deadlock |

**Note the order of the spend row, because it inverts the obvious one.** The agent runtime offers a per-query spend ceiling, and it is tempting to treat that as *the* budget enforcement. It is not: it is evaluated by the runtime process, which runs **inside the cell**, against the runtime's own running estimate. That places it on the untrusted side of §2's boundary — the same category as the `PreToolUse` path check (§5.3), valuable for cutting off a runaway attempt a few seconds earlier, worthless as a guarantee. The ceiling that holds is the supervisor's, because the supervisor is on the host and stops the cell rather than asking it to stop itself. The in-cell ceiling is still worth setting, for the same reason the path check is: it saves turns. It is just not what N2 rests on.

Five, and the last two are the ones you only discover by running this overnight — rev 2 had three. Splitting **idle** from **completion** matters because they want opposite treatment: silence *before* the agent claims to be done is a stall, and silence *after* is almost always a lingering child process. Collapsing them means a finished agent burns the full idle timeout and then gets treated as a failure.

**A timeout must never discard committed work.** Whichever bound fires, the supervisor evaluates what is actually in the worktree — commits exist or they don't — rather than throwing the attempt away because the process didn't exit cleanly. The corollary, and it is the same rule from a different angle: **never auto-clean on failure.** A failed or aborted task keeps its worktree and volume so you can look at them; `saffron gc` (§4.5) reclaims them on the 24-hour rule, and that delay is the feature.

#### Doneness is measured, never reported

The agent's claim that it finished is an input, not a verdict. Every phase transition is decided by a host-side measurement against git or the filesystem:

| Phase | The measurement |
|---|---|
| IMPLEMENT | `git rev-list --count base..HEAD > 0` — an attempt that produced no commits failed, whatever the transcript says |
| REPAIR | the gate result, which the agent never sees itself produce (§5.4) |
| REBUT | HEAD moved, or an explicit recorded argument — not "I've addressed the findings" |
| PACKAGE | rebase succeeded and `git diff --diff-filter=U` is empty |

This is the same principle as host-invoked gates, applied to control flow rather than to quality. It is cheap, it is a handful of `git` calls, and it is what keeps a confident-sounding transcript from moving a task forward on its own authority.

#### Retry taxonomy

The repair loop retries gate failures (§5.4). Nothing else in the system retries by default, and the distinction is worth stating because "add a retry" is the reflex:

- **Retry** idempotent infrastructure races — container start, mirror fetch, worktree creation. Re-running them is free.
- **Fail fast** on hangs, on genuine errors, and above all on anything that assembles the *content the agent acts on*. A retried or degraded prompt build — a missing spec fragment silently dropped, a stale template — runs the agent against a subtly wrong instruction and burns a whole attempt producing plausible garbage. That is far more expensive to recover from unattended than a clean abort into the morning queue.

### 4.4 Batch orchestration

```
saffron batch --repos saffron,thermal-edge --budget 50 --until 06:30 --concurrency 3
saffron batch --all --budget 50 --until 06:30           # every enabled repo
```

Nightly via `launchd` (not cron — `launchd` handles wake and won't silently skip a sleeping Mac). One batch spans all selected repos: **one concurrency pool, one budget, one morning queue.** Per-repo budgets would need per-repo tuning you have no data for, and separate batches would contend for the same three cells without knowing it.

The batch:

1. **Preflight**, per repo: mirror fetch, `policy.yaml` parse and validate, cell image rebuild if `.saffron/Dockerfile` changed, cell runtime up, auth valid, disk headroom, then `saffron gc` (§4.5). **A repo that fails preflight is skipped, not fatal** — one broken `policy.yaml` must not cost the other repos their night. It appears in the morning queue as a skipped-repo line.
2. Per repo: pin `base_sha` and **run the full gate suite on it, recording that repo's baseline failure set.** Baselines are per-repo and never compared across repos.
3. **Do not skip a repo because its base is red.** Skip only on *infrastructure* failure — any gate returning `error` rather than `fail`, or >25% of tests failing — which means the baseline itself is untrustworthy. This is precisely why the contract separates `error` from `fail`: it is the signal that distinguishes "your codebase has three flaky tests" from "the toolchain is broken," and without it you would have to guess from a failure count. A single flaky timing test should never cancel a repo's night; "base was red in these 3 tests" is a line in the batch header, not a stop.
4. Scheduler loop until the queue drains, the budget is gone, or `--until` hits.
5. Emit the batch index.

Steps 2 and 3 together are what make "only new failures count" (§5.4) do real work. An abort-on-red policy would make the baseline always-empty and the subtraction dead code.

### 4.5 Garbage collection

`saffron gc` runs at every batch start and on demand:

- List runtime volumes matching `saffron-wt-*` and `git worktree list` in the mirror.
- Diff against non-terminal ledger tasks.
- Anything unreferenced, or referenced by a task that has been `ORPHANED` for more than **12h**, has its artifacts flushed to the batch tree and its volume and worktree removed.

**Twelve, not twenty-four, and the number is set by the cycle rather than by taste.** A 24h rule evaluated by a once-nightly gc can never reclaim on the cycle that produced the corpse: a cell killed at 06:30 is ~15h old at the next batch's 22:00 preflight and survives to the night after. That is a bounded leak rather than rev 7's unbounded one, but it still means carrying an extra night of volumes in steady state — the same symptom, one cause further out. **A delay rule and its evaluation interval have to be chosen together; either one alone is a guess.** Twelve hours keeps the "never auto-clean on failure" property that the delay exists for (§4.3) — a corpse from last night is still there when you sit down with coffee — while landing inside the next preflight rather than after it.

**`ORPHANED` is stamped when the cell dies, not when gc notices.** The supervisor sets it on kill, on crash, and on `--until`; gc only reclaims. Deriving the state from a stale `updated_at` instead puts reclamation a full night out of phase — a cell killed at 06:30 is twelve hours old when the next batch starts, so nothing is freed and you carry an extra night of volumes in steady state, permanently. The delay is still the feature (§4.3, never auto-clean on failure); it just runs from the death rather than from gc's first glance at the corpse.

Without this, `--until 06:30` killing three mid-flight cells leaks three multi-GB volumes a night. Two weeks and the disk is full — and preflight would detect it and abort, which is detection without reclamation. F10 exists because of this.

### 4.6 The run record as a provenance graph — derived, one-way, provisional

The ledger is a good state store and a poor analytical surface. §8's flywheel is where that bill comes due: triaging a rejection into gate / `CLAUDE.md` / lens means joining an acceptance criterion to a critic finding to a gate result to a human decision — four tables and a directory of gzipped logs. Today that join happens in your head, monthly.

`SA-0001` defines a vocabulary for the run record so those joins become expressible. Three rules keep it from becoming a liability:

**1. Derived and one-way.** SQLite remains the system of record. The graph is a projection with no write path back. If it is stale, wrong, or absent, the factory still runs — which is the property (§4.1) that lets Saffron recover from Saffron. An authoritative graph store would trade that away for query convenience, and a dual-write arrangement would trade it away for nothing at all: divergence in an audit trail is worse than either store alone.

**2. PROV-O and EARL, not a bespoke schema.** Runs, tasks, attempts, phases and gate runs are `prov:Activity`; specs, `plan.json`, `scope.json`, diffs, gate output and PRs are `prov:Entity`; the implementer session, each critic lens and the human are `prov:Agent`. `wasGeneratedBy`, `used`, `wasDerivedFrom`, `wasRevisionOf` and `wasInvalidatedBy` (which is exactly what `spec_sha` invalidation is, §4.1) carry the backbone. Gate results and critic findings are both `earl:Assertion`s over an `earl:TestSubject`. The genuinely Saffron-specific terms — the only part that justifies a new namespace — are the gate taxonomy with its blocking/advisory split, `envelope` versus ratified `touches`, lens disjointness, and the terminal-versus-internal state distinction of §3.3.

**2b. The cheap rival the RATIONALE must also beat: a glossary.** Prior art (Appendix D) reaches the same need — a shared vocabulary its agents must read before touching code — and answers it with a 200-line markdown glossary where every term carries an explicit ***Avoid:*** list of the words not to use for it, plus an instruction to *flag* a conflict with a recorded decision rather than silently override it. That is a weekend's less work than an ontology and it does the thing an ontology is usually reached for. So `RATIONALE.md` has a second bar to clear: not only "is SPARQL better than SQL here," but "**is any of this better than a disambiguating glossary the agents actually read?**" If the honest answer is that the vocabulary's value is agent-facing rather than query-facing, write `GLOSSARY.md` and stop — the queries were the justification, and without them the RDF is decoration. Worth noting that Saffron needs the glossary either way; the ontology has to earn the *delta*.

**3. Provisional by construction.** The deliverable includes `ontology/RATIONALE.md`, which challenges each of five queries against its SQL equivalent over the §4.1 schema. **"All five have easy SQL equivalents — don't build the emitter" is a successful outcome**, and is the cheapest form that answer can take. The vocabulary is a design artifact validated against hand-authored fixtures; the emitter and the store are a separate, conditional task (§9, v2.5).

Rule 3 is the important one, and it is §9's build-order discipline applied to a data model: prove the layer is worth having before building the machinery that feeds it. A vocabulary costs a weekend and can be deleted. An always-on materialization pipeline cannot.

#### What the modelling already surfaced

Two schema criticisms that stand whether or not a single triple is ever stored:

- **`gate_results` and `findings` are the same thing wearing different table names.** A type error and a critic blocker against an acceptance criterion are both *an assertion, by an agent, about a subject, with an outcome*. EARL says that in one shape. The SQL schema splits them because gates are deterministic and critics are not — which is a fact about how the assertion was *produced*, not about what it *is*. The PR body already renders them into one table, which is the tell. Worth reconciling in §4.1.
- **A rebuttal is not a string.** §5.6 records implementer/critic disagreement across `verdict`, `adjudication` and `rebuttal`. Modelled as a `prov:qualifiedAssociation` the disagreement becomes a node carrying role, plan and time — which is what makes "blockers per lens, split by whether the operator agreed" answerable at all. *(The typed `adjudication` field this originally argued for landed in rev 6; the qualified-association question remains open.)*

That is the ontology earning its keep before it ships: writing down what an *attempt* is in relation to a *gate run* produced two design corrections, not two triples.

#### The trap it must avoid

An isomorphic re-encoding of §4.1 — one class per table, one datatype property per column, one object property per foreign key. That is a mechanical transform (it is what W3C Direct Mapping does), it passes Turtle parsing and shape validation, and it is worth nothing, because anything expressible over it was already expressible in SQL. A term earns its place by delivering **alignment** (external PROV tooling works on it), **qualification** (a relationship becomes a node that carries role and time), or **an axiom the relational schema cannot state** (disjointness, set containment across rows). `rdfs:comment` prose proves none of these — prose is the part that is cheap to fake.

`SA-0001` enforces this mechanically with a dead-term test: every term in the `saffron:` namespace must be referenced by at least one committed query or one shape, or it is deleted rather than commented. That check rides the existing blocking `tests` gate; it is not a new repo gate.

---

## 5. The cell pipeline

```
 ┌──────────┐  ┌──────────────────────┐  ┌────────────────┐  ┌────────┐  ┌────────┐
 │ DIAGNOSE │─▶│      IMPLEMENT       │─▶│ GATE ⇄ REPAIR  │─▶│ REVIEW │─▶│PACKAGE │
 │ bugs only│  │ plan checkpoint then │  │ bounded loop   │  │read-only│  │  host  │
 │ read-only│  │ write, one session   │  │ host-invoked   │  │adversarial│ │no model│
 └──────────┘  └──────────────────────┘  └────────────────┘  └────────┘  └────────┘
```

REVIEW is a separate session because it must be adversarial — it cannot be allowed to see the implementer's rationalizations. DIAGNOSE is separate because it runs under a different scope envelope and its output needs your ratification. PLAN is *not* separate: it's a checkpoint inside the implement session, because a planner and an implementer are not adversaries and splitting them pays full context cost twice for the same file reads.

### 5.1 Cell construction

```
# one-time
container network create --internal --subnet 10.88.0.0/24 saffron-cells
container run -d --name saffron-proxy \
  --network saffron-cells --network saffron-egress \
  saffron/proxy            # hostname CONNECT allowlist, addressed by IP

# per task
container run --rm \
  --network saffron-cells \                       # no default route
  -e HTTPS_PROXY=http://10.88.0.2:3128 \          # by IP: internal nets have no DNS
  -e ANTHROPIC_API_KEY \
  -e CLAUDE_CONFIG_DIR=/agent-state \
  $(policy.thread_env) \                          # repo-declared, see below
  --cpus 1 --memory 4g \                          # 1 requested, 2 delivered — see below
  --cap-drop ALL \
  --mount type=volume,source=saffron-wt-TE0142,target=/work \
  --mount type=volume,source=saffron-st-TE0142,target=/agent-state \
  saffron/cell:thermal-edge                       # built from .saffron/Dockerfile
```

**The runtime is `apple/container`,** decided in rev 10 against the four-assertion spike rather than left to taste (Appendix G). `no-new-privileges` and seccomp have no equivalent and are deliberately not replaced: the per-cell VM is the boundary offered instead, and §2's whole claim is that the structural controls are the ones that hold. Every remaining flag is load-bearing:

- **No target-repo credentials — for any repo, ever, and exactly one credential of any kind.** No host `.env`, no cloud profile, no database URL, no third-party API key. Tests run against recorded fixtures. A task that genuinely needs live data is a task you run attended. This is a rule core enforces rather than one each repo is trusted to follow: the cell simply never receives them.
  **The exception is `ANTHROPIC_API_KEY`, and it is stated here because an unstated exception is an abandoned rule (Appendix F, principle 29).** The agent cannot run without it, so the cell holds one live billing credential and the blast radius of that is spend, not data — which is why it is tolerable and why §2's boundary claim is written in terms of *target-repo* credentials. But it does mean N2's ceilings are an accounting sum over numbers the cell reports, not a limit the cell is subject to: an agent that leaks or misuses the key spends outside the supervisor's view entirely. Two mitigations, neither of which needs building before v1: use a **separate key for the factory** so it can be revoked without touching your interactive work, and set a **provider-side monthly cap on that key** — the only ceiling in the whole design that holds without the cell's cooperation. Moving custody into the proxy is the principled fix and is not available: `CONNECT` tunnels are opaque, so the proxy cannot inject a header it cannot see.
- **Egress via an allowlisting proxy, not iptables.** Two reasons the obvious version doesn't work: `--cap-drop ALL` removes `CAP_NET_ADMIN`, so a cell entrypoint cannot install firewall rules (and granting it that capability would let the untrusted cell rewrite its own firewall); and `api.anthropic.com` is behind a CDN, so an IP allowlist resolved at startup starts failing mid-batch. A sibling proxy on both the internal and external networks doing hostname-based `CONNECT` filtering solves both — hostnames not IPs, zero capabilities in the cell.
- **`CLAUDE_CONFIG_DIR` on a separate volume, never under `/work`.** Session state and any OAuth credential file must not live in the tree the agent has write access to, that the `scope` gate walks, that the secret scanner scans, and that gets patch-exported. Putting them together means the agent can read its own credentials and the secret scan trips on a real token.
- **A cell must see only the CPUs it has — not a quota, plus explicit thread caps.** Docker's `--cpus` is a CFS quota, not a core mask: Polars, pyarrow, and numpy's BLAS all size their thread pools from the *visible* core count and will each spawn ~10 threads inside a 2-CPU quota. The result is heavy throttling and wildly variable test timings — the exact flaky-gate failure mode §7 warns about, self-inflicted.
  **What survives, and what rev 8 struck out.** The requirement above is durable and it is not really about `cpuset`: **a cell must see only the CPUs it actually has.** The chosen runtime satisfies it structurally — the cell's VM is configured with that many vCPUs, so `nproc` is honest with no affinity flag at all. Write the requirement, not the flag.
  **Calibrated, because the physical world needs a knob a minimal model does not see.** `apple/container` 1.2.2 allocates **one vCPU more than `--cpus` requests** — deterministically, measured at 1→2, 2→3, 4→5, 6→7 (Appendix G). That is not the failure this bullet is about: the guest count is honest about the VM it is in, which is the property thread pools need, and the VM simply gets one more vCPU than asked for. So the supervisor requests `n − 1` and asserts the result, rather than trusting either number. **An offset that is measured, deterministic and asserted is a constant; the same offset assumed is a bug that surfaces as flaky gate timings.** Re-measure it on any runtime upgrade — the spike is the thing that measures it.
  ~~**Pin performance cores only.** Enumerate the P-cores once at preflight and let K fall out of how many there are.~~ **Struck in rev 8: this is not implementable on macOS under any runtime.** `--cpuset-cpus` is interpreted by the kernel that reads it, and on macOS that kernel is always inside a VM — so the mask indexes *virtual* CPUs, and which physical core a vCPU thread lands on is macOS's decision, not one any flag exposes. A VM-per-cell runtime has no pinning flag to offer in the first place. The underlying hazard is real and unchanged — vCPU threads prefer P-cores but spill to E-cores under contention, so a cell can run its gates slower than its siblings and the difference reads as task difficulty. It is now a thing to **detect rather than prevent**: record per-gate wall clock and treat cross-cell variance at equal K as a signal about the machine, not about the task (§7).
  The runtime caps the CPUs; the repo declares *which* env vars cap its toolchain's thread pools (`policy.thread_env`), because core has no business knowing that Rayon reads `RAYON_NUM_THREADS` and the JVM doesn't.
- **Worktree on a named volume, not a bind mount.** macOS bind mounts are slow for the many-small-files pattern of pytest collection and mypy. Clone from a bare mirror into a named volume, work there, export a patch. Costs easy host-side inspection mid-run; buys gate runs 3–10× faster, compounding across a 4-attempt repair loop. Dependency directories (`.venv`, `node_modules`, `target/`) live in the volume too — never on a mount, in any language.
- **Services and fixtures are baked into the repo's image layer, not orchestrated by core.** A repo that needs a database says so in its own `.saffron/Dockerfile`: install it, run the migrations, seed it, all at *image build* time. Every cell then starts from the layer — near-instant, no per-task restore, no "template database" subsystem in Saffron, and a real service so that migration and schema gates mean something. A repo needing nothing gets a smaller image and starts faster. Core's only involvement is rebuilding the image when `.saffron/Dockerfile` changes.
  > Rejected alternative: a `services:` block in `policy.yaml` that core turns into a Compose file. It reads cleaner and it drags service lifecycle, health checks, and startup ordering into the orchestrator — which is exactly the kind of knowledge §2.1 exists to keep out. A Dockerfile is already the standard way to say this, and the repo owner already knows how to write one.
- **Git remote is a local bare mirror.** The cell physically cannot reach your GitHub remote. The host pushes, after gates pass.

### 5.2 Phase 1 — DIAGNOSE (bugs only)

Read-only tools, scoped to `envelope`. Output is `scope.json`: the proposed `touches` set, the identified root cause, and the evidence for it.

This phase exists because of a specific trap. The obvious design — human declares `touches`, agent is confined to it — is sound for features and fatal for bugs. In the TE-0142 example, "no rows from any of three providers" most plausibly originates *outside* `ingest/nws/**`: a shared HTTP retry helper, a Polars schema change producing a silently empty frame, a continuous-aggregate refresh policy, a chunk-interval/retention interaction, a migration that changed a constraint. Several of those are in `forbidden` or outside a hand-written `touches`. The agent would correctly find the cause and then be auto-rejected for looking in the right place — and the rejection would read as "your spec needs work," which is both wrong and unactionable.

So: the agent proposes scope, you ratify. `SCOPE_REVIEW` items appear at the top of the morning queue as a diff of proposed `touches` plus the one-paragraph root cause — a genuine 10-second decision, versus a rewrite-the-spec-and-lose-a-night loop. Ratified scope is recorded in the ledger, and written into the spec file **on the task's own branch, as its first commit** — so it reaches `main` through the task's normal PR and needs no exception to N1's rule that nothing unattended writes to a remote `main`. **The task's own spec path is added to the ratified `touches` when it is recorded**, or that first commit fails the `scope` gate on every bug task: the writeback changes `.saffron/specs/…`, which is not a path DIAGNOSE would ever propose. A control artifact that has to be committed has to be in scope to be committed. Two further things fall out, both load-bearing. The ledger is authoritative until that PR merges, so enforcement starts at turn one of IMPLEMENT rather than next batch. And `spec_sha` on `main` deliberately does *not* move while the task is in flight — writing the spec back to `main` directly would invalidate (§4.1) the very task that ratification just unblocked.

Cost: ~$0.30–1.00. Cheapest possible place to catch a misconceived task.

### 5.3 Phase 2 — IMPLEMENT (with a plan checkpoint)

Full write tools inside `/work`, with an explicit `allowed_tools` list and a permission mode that **cannot prompt**.

That second requirement is easy to miss and fatal to get wrong. The obvious mode auto-accepts file *edits* — which covers Edit and Write and nothing else. A shell command outside `allowed_tools` still raises a permission prompt, and at 03:00 inside a container there is nobody to answer it: the attempt burns its idle timeout (§4.3) and reads as a stall. **Unattended operation requires a mode whose behaviour on an unapproved tool is to deny, not to ask.** The runtime offers one; it also offers a mode that skips permission checks entirely, which is the wrong fix — it removes the wasted-turn savings along with the prompt, and buys nothing safety-wise since the real controls are structural anyway (§2).

The general form, because it will recur with every runtime option: **in an unattended system, "ask the operator" is not a fallback, it is a hang.** Any option whose failure mode is a prompt needs its non-interactive equivalent chosen deliberately.

#### Control artifacts never stay in the workspace

`plan.json` and `scope.json` are written into `/work`, which is the one directory the agent has full write access to. So: **the host extracts them the moment they are produced, hashes them, and never reads them from `/work` again.** Nothing downstream trusts a file the agent could have rewritten after it was validated — and a validated plan that the implementer then quietly edits is exactly the kind of failure that leaves no trace in the diff.

The general rule, which applies to anything the harness needs to be true: *if a control artifact lives where the agent can write, it is a claim, not a record.* Session state already lives outside `/work` for the same reason (§5.1). Extraction closes the same hole for everything else.

#### Spec text is data, never a template

**Vocabulary is injected per phase, not wholesale.** `CONTEXT.md` is the controlled vocabulary, and it is a host artifact — it lives in Saffron, not in any target repo, so an agent inside a cell cannot follow a reference to it. It is injected into the system prompt, and only the sections that phase needs: the critic gets findings, severities and lenses; the implementer gets gates and statuses; **both get the scope section**, because §5.5 asks the critic for "behavior change outside the stated scope" and bare "scope" is the one word `CONTEXT.md` insists is never safe unqualified — a critic that cannot tell `envelope` from ratified `touches` from the `scope` gate is being asked to judge against a term it was not given. Neither gets the flywheel or the merge train, because nothing inside a cell can act on those.

REPAIR and REBUT take no injection of their own: both resume a session that already has the implementer's sections, and re-injecting on a resumed session pays for the same terms twice. Injecting all of it into three prompts on every attempt of every task is real money for terms the agent has no use for, and a long glossary crowds out the instructions that actually change behaviour.

The document is sectioned so this is a slice, not a rewrite. Sections are declared per phase in one table in `agents/prompts/`, and adding a term to the wrong section is caught by the same review that catches everything else.

Prompts are assembled from versioned template files plus substituted values. **The spec body is a substituted value, never a template**, and the assembler does not scan it for placeholders or command syntax. A spec that happens to contain `{{`, backticks, or anything else the templating layer would otherwise act on must pass through untouched — and specs are markdown written by a human about code, so it will happen. Two failure modes avoided at once: a hard crash mid-batch on a spec that looked fine, and the quieter one where user-supplied text reaches an expansion step it shouldn't.

#### Structured output: the extraction turn

The Agent SDK has no first-class structured-output guarantee, and asking an agent to both do work and emit clean JSON in one breath produces neither reliably. So structured output is its own turn: the host **resumes the same session** with a prompt that forbids further action —

> Emit a single `<output>` block as the last thing in your response. **Do not change files. Do not run commands.** Do not include text outside the block.

— and validates the result host-side with Pydantic. This is the **extraction turn**, and it is the only way a structured artifact is ever produced. On a schema failure, feed the validation error back and re-emit; twice, then reject. The retry is bounded and it is about *shape*, never about content, which keeps it clearly distinct from the gate repair loop.

This applies uniformly to `plan.json`, `scope.json`, and critic findings. It costs one cheap turn per artifact and removes an entire class of "the agent wrote prose around the JSON" failure.

The session opens by writing `plan.json` before touching anything:

```json
{"understanding": "...", "approach": "...",
 "files_to_change": ["src/...", "tests/..."],
 "test_strategy": "...", "risks": ["..."], "blocking_questions": []}
```

Validated host-side with Pydantic. **Auto-rejected — no model call — if:** `files_to_change` ⊄ `touches`; it intersects `forbidden` or global protected paths; `blocking_questions` is non-empty; or no test file appears and `type` ∈ {feature, bug}. On rejection the session is killed before a single implementation token is spent. On schema-invalid output, one re-prompt with the validation error, then reject.

**On hooks.** `PreToolUse` hooks run *inside the agent's own process, inside the cell.* They sit on the untrusted side of the boundary and must not be counted as a control. Their two legitimate uses:

1. **Audit tap** — every `PreToolUse` / `PostToolUse` / `SubagentStop` event appended to the attempt transcript. This is what you read when a PR looks strange and you want to know why.
2. **A path check on `Edit`/`Write`** — deny writes outside `/work` or into protected paths. Its value is *fewer wasted turns*, not safety; the real protection is that there's nothing outside `/work` worth writing to.

Explicitly **not** doing: a regex denylist over Bash command strings. It's the same category error as a prompt, one level down. It fails open on `python -c`, `make`, `sh -c "$(…)"`, any Makefile target, any interpolation — and far more often it fails *closed*, because `curl` appears in fixtures, `rm -rf` on a tmpdir is legitimate, and `git push --dry-run` in a doc check is harmless. You'd spend week two loosening it until it protects nothing, and then keep counting it as protection. The controls that actually hold — no credentials, no route, mirror-only remote — hold whether the agent cooperates or not.

### 5.4 Phase 3 — GATE ⇄ REPAIR

The gate runner is **host-invoked, deterministic, and not an agent**. It executes a declared sequence in the cell and returns structured results. The agent never runs the gates and never reports its own gate status — it only ever *receives* gate output as input. This is the single most important structural property in the pipeline.

#### The gate contract

This is what makes Saffron repo-agnostic, and it is deliberately tiny. **A gate is an executable in `.saffron/gates/` that emits one JSON object on stdout.** Saffron does not know or care what it ran.

```json
{ "gate": "types",
  "status": "pass" | "fail" | "skip" | "error",
  "tool": "mypy 1.18.2",
  "failures": [ { "file": "src/ingest.py", "line": 88,
                  "code": "arg-type", "message": "…" } ],
  "summary": "4 errors in 2 files" }
```

Everything downstream is built on this and nothing else:

- **The repair loop is language-agnostic** because it feeds `failures[]` back to the agent as structured text. It never parses compiler output; that translation is the gate's job, and it belongs in the repo where someone knows the tool.
- **Baseline subtraction works** because failures are comparable by **`(gate, file, code, normalized message)`** — deliberately *not* including `line`. A task that inserts thirty lines near the top of a file moves every pre-existing failure below it, so a line-keyed baseline entry stops matching and an untouched failure reads as new. The repair loop would then spend attempts on pre-existing code, which is the exact thing baselines exist to prevent: the countermeasure defeating itself on nearly every diff that is not append-only. `line` is carried for display and for anchoring (§5.5); it is never part of the identity. **An identity that includes a coordinate the change moves is not an identity.**
- **The subtraction counts; it is not a set difference.** Normalizing the message means collapsing the digit runs that embed the coordinate — and in one file, two failures of one rule often differ *only* in those digits, so they normalize to one identity legitimately. Under set semantics a single pre-existing failure then cancels every head failure sharing that identity, and genuinely new ones vanish. Baseline subtraction is therefore a multiset operation: one baseline failure cancels one head failure. The known consequence is that where N of M colliding failures are new, the ones *reported* may name a pre-existing line — acceptable, because `line` was already display-only. Found by review after v0's replays, which happened not to contain the shape (Appendix H).
- **`skip` is a first-class status**, so a repo simply omits gates it has no analogue for. A repo with no type system declares no `types` gate; nothing in core changes.
- **`error` is distinct from `fail`** — the gate itself broke (toolchain missing, DB down). It never counts as a task failure, it aborts the attempt and surfaces as an infrastructure problem. Conflating these is how you get an agent spending four attempts "fixing" a crashed linter.
- **`tool` is what distinguishes "ran and passed" from "didn't run",** and v0 shipped without it at the cost of a silently green replay (Appendix H). `{"status":"pass","failures":[]}` is bit-for-bit identical whether the linter found nothing or the linter was not on `PATH` and a shell script swallowed the error. So the contract requires an opaque tool identifier **obtained by executing the tool** — `ruff --version`, not a string literal. A gate that cannot run its tool cannot produce the field. The host stores it per gate result and treats a `tool` that differs between a run's baseline and its head as grounds to distrust the subtraction rather than report it.

Two rules about `error` that the same replay forced, both stated because a gate author has to know them and neither is derivable from the schema:

- **A non-zero exit with an empty `failures[]` is `error`, never `pass`.** It means the tool objected to something the gate's parser did not recognize — a reworded output line after a version bump is the ordinary cause, and it produces the identical false green as a missing binary, from a different direction. The gate knows its own exit code; nothing downstream does.
- **Partial results are not results.** When a gate's execution mechanism breaks part-way — a lost test worker, a collection crash, a timeout on one shard — the gate returns `error` for the whole run rather than `fail` on whatever it managed to collect. There is deliberately no per-failure `error` vocabulary: a suite that lost a worker did not produce a trustworthy result, and the cost of that rule is one re-run charged to nobody, against the cost of an agent spending attempts "fixing" a test that a scheduler killed.

Requiring gates to translate their own tool output is the price of admission, and it is the right price: it is ~20 lines of shell per gate, written once by the person who understands that tool, and it keeps every parser out of the orchestrator.

#### Gate roles

`policy.yaml` declares which roles the repo implements and their blocking level. Core supplies three; the repo supplies the rest.

| Role | Owner | Blocking | Notes |
|---|---|---|---|
| `scope` | **core** | yes | changed files ⊆ `touches` |
| `size` | **core** | at `elevated` | diff lines ≤ type ceiling (bug 300 / feature 600 / refactor 1000) |
| `secrets` | **core** | yes | credential scan over the diff |
| `integrity` | **core**, repo patterns | yes | test-tampering check (below) |
| `revert` | core logic, repo runner | yes | new tests must fail without the source hunks (below) |
| `format` | repo | yes | |
| `lint` | repo | yes | |
| `types` | repo | yes, or `skip` | untyped language ⇒ omit |
| `tests` | repo | yes | must accept a test-subset argument, for `revert` |
| `no-network` | repo | yes | the repo knows how to intercept its own sockets |
| `coverage` | repo | **advisory, at every tier** | see below |
| *(repo-defined)* | repo | declared | conditional on touched paths |

The last row is where a repo's real leverage lives, and it is why the contract is worth having. A repo declares its own gates against its own hard-to-fake surfaces, conditioned on paths:

```yaml
# .saffron/policy.yaml — excerpt from one repo
gates:
  shacl:      { blocking: true, when: "**/*.ttl" }
  migration:  { blocking: true, when: "migrations/**" }
  perf-smoke: { blocking: false }
```

Core sees three more entries in a list. **The best gates are always the domain-specific ones** — a migration round-trip, a schema conformance check, an invariant only this codebase can state — because they are the ones an agent cannot satisfy by writing plausible-looking code. Onboarding a repo well means asking: *what is expensive to fake here?*

Four roles carry most of the weight.

**`integrity` — the anti-gaming gate.** The dominant failure mode of a hard-gate self-repair loop is not the agent giving up; it is the agent *making the gate pass*. Deleting a failing test, adding `@pytest.mark.skip` or `xfail`, sprinkling `# type: ignore`, loosening `==` to `is not None`, lowering a threshold in config. So: diff test files separately from source files, and fail on any deletion of an existing test, any newly added suppression, and any edit to gate configuration, unless `touches` explicitly includes it. Without this gate, hard gates actively *train the loop toward test destruction*, because that's the cheapest path to green.

The *logic* is core — "was a test removed or silenced?" is a question about a diff, and it is identical in every language. The *vocabulary* is not, so the repo declares it:

```yaml
integrity:
  test_paths:   ["tests/**", "**/*_test.go"]
  suppressions: ["@pytest.mark.skip", "xfail", "# type: ignore", "# noqa"]
  gate_config:  ["pyproject.toml", ".coveragerc", ".github/workflows/**"]
```

This split is the boundary of §2.1 in miniature, and it is the pattern to reach for whenever a check feels language-specific: usually the *question* is universal and only the *tokens* are local. Pushing the tokens into `policy.yaml` keeps the check in core where it gets maintained.

**`revert` — the anti-theater gate, and the best cost/value ratio in the system.** Stash the source hunks of the diff, keep the test hunks, run only the new and changed tests, and require them to **fail**. One extra test run. This is the one place core reaches into the repo's toolchain, and it is why the contract requires the `tests` gate to accept a **test-subset argument** — the single most constraining line in the whole contract, and worth the constraint: every serious test runner supports it, and without it this gate degrades to a full-suite run per attempt. It mechanically answers the question critic lens #3 would otherwise be asked to reason about: does this test actually detect the thing it claims to? It catches deleted assertions, `assert result is not None`, and tests that pass identically on `main`.

This replaces mutation testing, which was the obvious choice and doesn't fit: `mutmut` reruns the suite per mutant, a Timescale-backed suite takes minutes per run, and 15 mutants is an hour inside a 2-core cell competing with two siblings inside an 8-hour window that also has to fit 10–15 tasks. It would break N3 outright.

**`coverage` is advisory, deliberately — and at every risk tier.** Blocking on changed-line coverage generates exactly the behavior `integrity` exists to prevent: the cheapest way to satisfy it is a test that *executes* new lines without asserting on them. It also misfires structurally here — `except` branches for provider timeouts, `if TYPE_CHECKING`, defensive gap handling, and pure refactors where every changed line is a moved line. Report it in the PR body; block on `tests` and `revert`.

> Through rev 6, §5.6 made `coverage` blocking at `risk: elevated`, contradicting the paragraph above. Resolved in favour of the paragraph, and the reasoning generalizes: **an argument against a gate does not weaken as risk rises, it inverts.** Elevated risk is where a gamed gate does the most damage, so it is the last place to switch on the one gate whose cheapest satisfaction is theater. This is the same defect Appendix B caught in `size`, living in the same sentence, and it survived one revision longer because only half of the sentence was fixed.

**`revert` generalizes past code, which is a useful test of a spec.** `SA-0001` produces a vocabulary, not a program, and the gate still bites: stashing "the source hunks" means removing `saffron.ttl` and the shapes, after which the shape and query tests must fail. Tests that pass against an empty graph get caught. Any artifact with an executable claim about it — a schema, a config, an ontology — is checkable this way. The corollary is a cheap smell test when writing a spec: *if you cannot say what reverting it should break, your acceptance criteria are prose.*

**The repair loop:**

```
for n in 1..max_attempts:
    results = run_gates(cell)
    new_failures = results.failures - baseline.failures     # §4.4
    if not new_failures: break
    if new_failures == prev_failures: escalate_or_abandon() # no progress
    agent.repair(new_failures)                              # resumed session
```

- **Only new failures count.** Failures on `base_sha` are pre-existing and not this task's problem. Otherwise every task inherits your flaky tests and burns its budget on them.
- **No-progress detection.** The same new-failure set two attempts running — same identity as above, and counted the same way, for the same reason — means the agent is stuck; stop paying. Comparing raw bytes instead would make this dead code, because every repair shifts line numbers, so a permanently stuck agent would look like it were making progress forever. Counted rather than set-compared because fixing three of four colliding failures is progress and a set cannot see it. Optionally escalate once to a fresh session rather than a resumed one — sometimes the accumulated context *is* the problem.
- **`EXHAUSTED` is a respectable outcome.** A task that can't pass its own gates in four tries is telling you the spec was underspecified or the codebase is hostile at that point. Both worth knowing.

### 5.5 Phase 4 — REVIEW (adversarial)

Fresh session, read-only tools, different system prompt, ideally a different model or effort level. It never sees the implementer's transcript. It sees the spec, the diff, the gate results, and the acceptance criteria.

Its instruction is not "review this code":

> Find the reason this change should not be merged. Assume it is subtly wrong. The gates passed, so the defect is not something the gates check — look for what gates cannot see: an acceptance criterion technically satisfied but not actually met; a test that passes for the wrong reason; a fix that treats a symptom; behavior change outside the stated scope; an assumption about the data that holds in fixtures but not in production. Report only findings you can point at a specific line for. **If you cannot find a real defect, say so — do not manufacture one.**

That last clause is not politeness. A critic prompted to find problems will always find problems, and you'll spend your mornings adjudicating invented ones.

**Findings are reconciled against the diff before they count.** The critic emits `file` and `line` per finding; the host drops any finding it cannot anchor, and logs the drop. An unanchorable finding is either a hallucination or a complaint about pre-existing code, and neither belongs in a queue that is supposed to be about *this change*. Same move as measuring doneness from git (§4.3): treat agent output as claims, reconcile against a host-computed fact set. Perhaps twenty lines of code, and it is the difference between a critic you read and a critic you learn to skim.

**Anchoring admits two targets, not one, and the second exists for lens #3.** The blast-radius lens is asked *what else calls this* — so its best findings point at lines the diff never touched: an unupdated caller, a missing migration, a serializer left behind. A hunk-only rule discards most of what that lens is for, and the drop-rate diagnostic below would then read as a prompting defect when the reconciler is what is wrong. So a finding anchors if its file and line fall **inside a diff hunk**, *or* if that line **mentions an identifier the diff added, removed or renamed**. The second test is deliberately crude — tokenize the changed lines on word boundaries, intersect with the tokens on the cited line, no language knowledge anywhere — and crude is enough, because anchoring only ever had to establish that a finding points at real code with a real connection to this change. Everything else is still dropped and still counted.

> The general lesson, because it will recur: **a reconciler tuned to one producer silently disables another.** The hunk rule was written with lenses #1 and #2 in mind and would have zeroed out #3 without a single error message — the only symptom being a lens that looked badly prompted.

Dropped findings are recorded with `anchored = false`, not deleted — a lens that keeps producing unanchorable findings is badly prompted, and the drop rate is how it tells you.

**Severity is two levels that count and one that doesn't.** `blocker` routes to REBUT. `concern` reaches the operator's judgement and is the number in a queue line. `note` appears in the PR body and is excluded from every count — because without a third level, every true-but-trivial observation inflates the concern count that drives queue sort order, and you learn to ignore the number. The critic is told the distinction explicitly; a lens that files everything as `concern` is as much a prompting defect as one that hallucinates.

Two lenses in v1, a third at elevated risk — **different lenses, not repeated ones**:

1. **Correctness & data semantics** — timezones, chunk boundaries, null/gap propagation, unit errors, market-hours assumptions.
2. **Contract & schema** — public API compatibility, migration reversibility, serialization and schema conformance, anything downstream consumers depend on.
3. *(elevated)* **Blast radius** — what else calls this, what breaks downstream, what the diff changes that the spec never asked for.

**Each lens is a separate host-invoked session, not a subagent.** The runtime has a subagent facility that fits a lens almost perfectly — per-agent model, effort level, and a read-only tool list — and it is the wrong mechanism here for one reason: *the model decides when to spawn a subagent.* A REVIEW phase that asks one session to delegate to two or three lens subagents produces a lens set that varies by task, silently, with no error when a lens is skipped. Saffron needs all declared lenses to run on every reviewed diff, so the host invokes each one and collects its findings. The subagent *shape* is still the right configuration — it is where per-lens model and effort live — it just gets driven from the host rather than requested in a prompt.

This is §4.3's doneness rule again, one level out: **anything that must happen every time is measured and driven by the host; anything the model decides is a claim.** A lens that runs only when the model thinks it is relevant is not a lens, it is a suggestion.

One property the subagent facility does confirm: a fresh session receives no parent conversation at all — only what its invoker puts in the prompt. That is exactly the isolation this phase requires, and it means the diff, the spec, the gate results and the acceptance criteria must all be passed explicitly. There is no context to inherit, by design.

**Any single blocker routes to REBUT.** No voting. A majority rule sounds rigorous and is decoration here: the lenses are disjoint by construction, so the schema critic will never independently corroborate the correctness critic's timezone finding, and "majority" with two disjoint lenses means "never." False positives are handled by the rebuttal plus queue ordering (§6), which is the better mechanism anyway.

Note that lens #3 in a naive design would be "test quality" — but the `revert` gate now answers that mechanically and for free. Per §8's own triage rule, that's a bucket-1 solution displacing a bucket-3 one, which is exactly the direction things should move.

### 5.6 Phase 4b — REBUT

The implementer session resumes and gets the confirmed blockers. **One** attempt to either fix them or argue the finding is wrong. Both outcomes recorded. Gates re-run.

**If that re-run is red, the task is `EXHAUSTED` — REBUT does not re-enter the repair loop.** The rebuttal diff and the failing gate are both kept for you to read. Reopening repair here would let a task ping-pong between two phases on one budget, and it would be paying to paper over the most informative failure in the pipeline: a fix for a confirmed blocker that breaks something else is the clearest possible signal that the change and the finding both want your attention rather than another attempt.

Why allow rebuttal rather than mandate a fix: sometimes the critic is wrong, and a recorded disagreement between two agents is a strong signal about *which part of the diff you should read carefully*. Unanimity is far less informative than a documented argument.

**Risk tiering.** `risk: elevated` — set explicitly in the spec, or auto-elevated when the diff touches any path in the repo's `policy.elevate_on` (a repo with migrations and an ontology might list `migrations/**`, `**/*.ttl`, `trading/**`; Saffron's own lists `saffron/gates/**` and `saffron/cell/**`) — adds the third lens, makes `size` blocking, and marks the queue entry so you read it cold rather than skim. **`coverage` does not become blocking** — not at `elevated`, not ever; see §5.4.

Getting `elevate_on` right is most of what "onboarding a repo" actually means. It is the repo owner answering one question — *where in here does a plausible-looking wrong change hurt most?* — and it is worth more than any amount of gate configuration.

### 5.7 Phase 5 — PACKAGE (no model involved)

Host-side, deterministic:

1. Rebase onto current `main` (or onto the parent branch, if stacked). Conflicts → `MERGE_FAILED`. Never ask an agent to resolve conflicts unattended; a plausible-looking wrong answer there is very expensive. (Prior art suggests a middle path — see §11, "what I'd revisit".)
2. Push `saffron/TE-0142-forecast-gap` to the real remote **with `--force-with-lease` pinned to the SHA the packager checked out.** If the branch moved underneath — a re-queued task, a second run, you pushing a fixup by hand — the push fails loudly instead of silently clobbering. Turning a race into an error costs one flag.
   Branch mutation is also serialized: one writer per branch, ever, held across package and merge-train operations. A `CHANGES_REQUESTED` task that gets re-queued must not race the merge train rebasing the same branch.
3. Open the PR. Body generated from the ledger: spec, root cause (if diagnosed), acceptance-criteria checklist with the critic's assessment of each, gate table, findings with rebuttals, attempt count, cost, transcript path.
4. Append the verdict line to the batch index.

---

## 6. The morning queue

**The queue is an index, not a viewer.** §5.7 already pushed a real branch and opened a real PR with the full body — so GitHub's review UI, with line comments, syntax highlighting, blame, and phone access, is already yours for free. Building a second diff viewer duplicates the best-engineered component in the stack for no gain.

So the deliverable is one small static page, ~50 lines of Jinja: a sorted list of verdict lines, each linking to its PR.

```
thermal-edge  TE-0139  READY   2 att $6.40  1 concern  +180/−22  → PR #211
thermal-edge  TE-0144  SCOPE   diagnosed: shared retry helper    → ratify?
saffron       SA-0001  READY   1 att $8.20  0 concerns +410/−0   → PR #14
thermal-edge  TE-0142  MERGE_FAILED  conflicts with #209         → PR #213
saffron       SA-0003  EXHAUSTED  3 att $9.10  types: 4 new      → log
toolbox       —        SKIPPED  policy.yaml: unknown gate role "typecheck"
```

Sort order, designed so you can dismiss in 10 seconds and accept in two minutes:

0. Skipped repos — an entire repo produced nothing, which is the most expensive thing on the page
1. `SCOPE_REVIEW` — one-click, and it unblocks the next night
2. `MERGE_FAILED`, `PLAN_REJECTED` — fast to triage, unblocks the queue
3. `risk: elevated`
4. Everything else by concern count descending — concerns, not findings (`CONTEXT.md` §5): `note` is excluded by construction and `blocker` never reaches this page unrebutted

**Sort by state, not by repo.** The temptation with multiple repos is to group them, and it is worth resisting: the most urgent item across all repos should be the top line, and grouping buries a skipped repo under another repo's routine PRs. Repo is a column you scan, not a heading you navigate.

Batch header: counts by terminal state, total spend, wall clock, per-repo preflight and base-suite status, and the one number that says whether this is working — **trailing accept rate**.

*Trailing*, and the qualifier is not pedantry. This batch's accept rate is unknowable when the batch ends: nothing has been merged yet, because merging is what you do next. The header can only show the rate over prior batches — a rolling window of about the last twenty completed tasks, which is also roughly the smallest n at which the number means anything (§8). A header field that claimed to score the night it was printed would be reporting on work that hadn't happened.

Inside the PR body, the ordering that matters is: **disagreements first.** Anywhere the critic and implementer diverged goes above the gate table, because that's where your judgment is worth the most.

### 6.1 Merge train

You approve in GitHub; nothing merges on your click. Approved tasks enter a serial train that rebases onto current `main`, re-runs the **full** gate suite on the merged result, and merges only if green.

Green-in-isolation is not green-after-merge. The conflict-set scheduler prevents *file* collisions but not *semantic* ones — two tasks can each pass while jointly breaking an invariant — and stacked branches (§4.2) make this more likely, not less. The train catches it at machine cost rather than at yours.

---

## 7. Failure modes and countermeasures

| Failure | Why it happens | Countermeasure |
|---|---|---|
| **Gate gaming** — tests deleted/skipped, `type: ignore`, thresholds lowered | Hard gates make "green" the objective; destroying the test is cheapest | `integrity` gate; test-file diff shown separately in the PR |
| **Coverage theater** — tests that execute but don't assert | A blocking coverage gate rewards it | `coverage` advisory only; `revert` gate blocks |
| **Plausible-but-wrong** — passes everything, subtly incorrect | Gates only check what you thought to check | Adversarial critic, disjoint lenses; disagreements surfaced first |
| **Human does the diagnosis** | Hand-written `touches` on a bug spec | DIAGNOSE phase + `SCOPE_REVIEW` ratification (§5.2) |
| **Dependencies never unblock** | `MERGED` unreachable within a batch | Dependency satisfied at `READY_FOR_REVIEW`; stacked branches |
| **Runaway spend** | Repair loops are unbounded by nature | Per-attempt / task / batch ceilings, no-progress detection, wall clock |
| **Chasing pre-existing failures** | Base was already red | Baseline gate run; only new failures count |
| **Batch cancelled by one flaky test** | Abort-on-red policy | Abort only on infrastructure failure; red base is a header line |
| **Parallel PRs that conflict** | Two agents edit the same files | Conflict-set scheduling + `scope` gate; merge train for semantic overlap |
| **Scope creep** | Agents helpfully fix adjacent things | `touches` + `forbidden` + `scope` + `size` + "Out of scope" |
| **Credential exposure** | Agent reads `.env` or its own OAuth file | No real credentials in the cell; `CLAUDE_CONFIG_DIR` off `/work` |
| **Egress to something live** | Agent curls your broker | `--internal` network, no default route, hostname-allowlisting proxy |
| **Destroying your repo** | `git push --force` | Local bare mirror is the cell's only remote; host does real pushes |
| **Flaky gates poisoning the loop** | Thread oversubscription under concurrency | The cell sees only the CPUs it has — `cpuset` under a shared VM, vCPU count under a per-cell VM — plus `policy.thread_env` caps; K=3; baseline comparison (§5.1) |
| **Disk exhaustion** | Killed cells leak volumes and worktrees | `ORPHANED` state + `saffron gc` at every batch start |
| **Saffron breaks Saffron** | Self-hosting | Dependency-free SQLite ledger; self-tasks are `risk: elevated`, put `saffron/` in `forbidden`, and never auto-enter the train |
| **Premature generality** | Two Python repos look like proof of language independence and are not | Keep the contract (it's cheap and it's a boundary, not an abstraction layer); refuse new abstraction until a genuinely different repo forces it (§9) |
| **Language knowledge leaks into core** | One `if lang == …` is always easier than a contract change | The four core gates read diffs and never execute repo code; any core gate that wants to *run* something belongs on the repo side (§2.1) |
| **One repo starves the others** | Priority ordering across a shared pool | Round-robin across repos in the scheduler; per-repo lines in the batch header |
| **A broken `policy.yaml` costs the whole night** | Preflight treated as fatal | Per-repo preflight; a failing repo is skipped and surfaces at the top of the queue |
| **Gate `error` mistaken for `fail`** | Crashed toolchain looks like a red test | `error` is a distinct contract status; aborts the attempt, never counts against the task |
| **Timeout discards committed work** | Process didn't exit ⇒ attempt treated as failed | Doneness measured from git after any bound fires; never auto-clean on failure (§4.3) |
| **Agent rewrites a validated control artifact** | `plan.json` lives in the writable worktree | Host extracts and hashes it at validation; never re-read from `/work` (§5.3) |
| **Hallucinated critic findings** | Nothing checks the finding points at a real changed line | Findings reconciled against diff hunks; unanchorable ones dropped and counted (§5.5) |
| **Spec text breaks or hijacks prompt assembly** | Markdown containing template syntax | Spec body is a substituted value, never scanned as a template (§5.3) |
| **Silent branch clobber** | Two writers on one branch | `--force-with-lease` pinned to the checked-out SHA; one writer per branch (§5.7) |
| **Money spent to learn something free** | Refusable conditions discovered inside the cell | Refusal gate before any container starts (§4.2) |
| **Ontology is a re-encoding of the schema** | Direct mapping passes every syntactic check and delivers nothing | Dead-term test; terms must earn alignment, qualification, or an unstatable axiom (§4.6) |
| **Derived graph drifts from the ledger** | Two stores, one truth | Projection is one-way and disposable — rebuild it from the ledger, never reconcile into it |
| **False new failures from line drift** | Baseline keyed on a coordinate the diff moves | Failure identity is `(gate, file, code)`; `line` is display-only (§5.4) |
| **No-progress detection never fires** | Byte comparison over a line-shifting failure set | Same identity as baseline subtraction, so the comparison is stable (§5.4) |
| **Blast-radius findings all dropped** | Anchoring admits only lines inside a hunk | Second anchor: a line naming an identifier the diff changed (§5.5) |
| **REBUT reds a gate and hangs** | No edge out of REBUTTING except success | A red re-run is `EXHAUSTED`, with the rebuttal kept to read (§5.6) |
| **Volumes reclaimed a night late** | `ORPHANED` inferred from a 24h-stale timestamp | Supervisor stamps `ORPHANED` at death; gc's 12h delay runs from then and lands inside the next preflight (§4.5) |
| **Cells with unequal cores** | vCPU threads prefer P-cores but spill to E-cores under contention | **Not preventable on macOS** — no runtime pins physical cores. Record per-gate wall clock; treat cross-cell variance at equal K as a machine signal, not task difficulty (§5.1, Appendix G) |
| **Silent batch no-op** | Cell runtime down, Mac asleep, auth expired | `launchd` + preflight that fails loudly into the queue |
| **Batch overshoots its budget by up to K×** | Budget gate compares against spend, which lags scheduling | Reserve the task budget at schedule, release the remainder at terminal state (§4.2) |
| **Every re-queued task is refused** | Gate 0 sees the task's own open PR | Refusal keyed on another task's PR, not on the spec (§4.2) |
| **Ratified bug tasks fail `scope` on their first commit** | The writeback edits a spec path DIAGNOSE never proposed | The spec's own path joins the ratified `touches` (§5.2) |
| **Two bug tasks collide inside one file** | `touches` is empty when a bug is first scheduled | Gates 0 and 2 re-run at ratification against the ratified set (§4.2) |
| **Baseline subtraction has nothing to subtract from** | `gate_results` stored status, not `failures[]` | `failures` table keyed `(gate, file, code)`; baseline rows hang off `run_id` (§4.1) |
| **`spec_sha` invalidation never fires** | Nothing re-reads the repo after preflight pins `base_sha` | Mirror refetch and sha comparison at each task's scheduling (§4.1) |
| **Spend outside the supervisor's accounting** | The cell holds a live API key by necessity | Separate factory key, provider-side monthly cap — the one ceiling not dependent on the cell (§5.1) |
| **Unattended agent hangs on a permission prompt** | Auto-accepting edits doesn't cover shell commands | A permission mode that denies rather than asks; prompts are a hang, not a fallback (§5.3) |
| **A crashed attempt records $0** | The runtime zeroes cost fields on session crash | `terminal_reason` stored; supervisor falls back to the last good figure before the crash (§4.1) |
| **Repair loop pays full input price every attempt** | 5-minute cache TTL is shorter than a gate run | One-hour cache TTL set on the cell (§7.1) |
| **A critic lens silently doesn't run** | Lenses spawned as subagents are invoked at the model's discretion | Each lens is a separate host-invoked session (§5.5) |
| **An estimate hardens into a billing fact** | Runtime-reported cost is a local approximation | `_est` suffix on every stored figure; reconcile against real billing (§4.1) |
| **Host services reachable from an isolated cell** | An `--internal` network still routes to the host gateway — **confirmed by spike**, at the gateway *and* at the LAN address | Bind host services to `127.0.0.1`, never `0.0.0.0`; verified by a preflight probe, because N1 rests on it (Appendix G) |
| **A cell gets more CPU than it was allocated** | The runtime allocates `--cpus + 1` vCPUs | Request `n − 1` and assert the result; re-measure the offset on every runtime upgrade (§5.1, Appendix G) |
| **The cell cannot resolve its own proxy** | Internal networks have no DNS | Pin the network subnet and address the proxy by IP (Appendix G) |
| **A runtime flag silently means something else** | Container flags are interpreted inside a VM on macOS | State the requirement, not the flag; verify each control on the runtime actually chosen (Appendix G) |
| **A gate that never ran reports `pass`** | An absent tool and a clean repo emit identical JSON | `tool`, obtained by executing the tool; non-zero exit with empty `failures[]` is `error` (§5.4, Appendix H) |
| **A tool-output parser silently stops matching** | Gates regex an unversioned CLI string that a version bump rewords | Same two guards — the exit code disagrees with the empty parse, and `tool` records the bump (§5.4) |
| **A crashed test worker reads as a code failure** | A lost worker's `code` field looks like an assertion failure's | Partial results are not results: the gate returns `error` for the whole run, charged to nobody (§5.4) |
| **New failures cancelled by a pre-existing one** | Normalization collapses the digits that tell colliding failures apart | Baseline subtraction is a multiset operation — one baseline failure cancels one head failure (§5.4) |
| **A replayed PR drags `main` into its own diff** | `M^1` is `main` at merge time, not the branch point | Base is the merge base of the two parents; a squash's sole parent already is one (Appendix H) |

### 7.1 Cost model

| Phase | Typical |
|---|---|
| Diagnose (bugs) | $0.30–1.00 |
| Implement (incl. plan) | $2–6 |
| Repair × 2 | $1–4 |
| Review × 2 lenses | $1–2 |
| Rebut | $0.50–1.50 |
| **Total** | **$5–14** |

**Extend the prompt-cache TTL, or the repair loop pays full price every attempt.** The default cache lifetime is five minutes. The repair loop resumes the same session *across a gate run*, and a gate run against real fixture services is minutes — so on most attempts the cache has expired and the entire accumulated context is re-billed as fresh input. The repair row above is the row this lands on, and it is the row that runs up to four times. The runtime exposes a one-hour TTL through an environment variable; set it on the cell. It trades a higher cache-write rate for reads that actually survive a gate run, and it is the single cheapest cost lever in the system — one env var against the most-repeated phase.

Worth stating as a general shape, because it is invisible until you look for it: **a cache TTL has to outlive the slowest thing between two uses of the cache.** Here that thing is not a model call, it is a test suite — which is why the default was never going to fit.

Gate wall-clock is a real budget line, not just a token one: a full suite against a repo's fixture services is minutes, and the repair loop runs it up to 4× per task. Assume ~45–60 min per task at K=3, so ~25 task-slots in an 8-hour window, realistically 10–15 completed.

**Set the nightly budget before you set the queue depth.** A hard stop is the difference between a useful factory and a surprising invoice.

But size it against the queue you actually have, and note that three numbers in this document disagree about that: N4 wants 6–12 accepted PRs a *week*, the paragraph above sizes a night's *capacity* at 10–15 completed tasks, and §4.2 concedes the realistic queue is two or three deep because spec-writing binds first (§9). **Capacity is not throughput, and the budget should be set from the queue.** Three tasks at $5–14 is a $45 night with headroom; `--budget 120` buys a queue depth you will not have for months, which makes it a ceiling that never fires — and a ceiling that never fires is not a ceiling, it is a comment. Start at **$50**, raise it the first night the batch stops on budget rather than on an empty queue. That night is also the first real evidence about which of the three numbers was right.

Track cost per *accepted* PR, not per task — that's the number that tells you whether the critic layer pays for itself.

---

## 8. The flywheel

A factory producing the same quality in month six as month one is an expensive script runner. The loop:

**Every rejection becomes a rule.** When you reject or request changes, write one line of *why* — appended to `.saffron/rejections.md` in the target repo, by hand. Then triage it into exactly one of three destinations:

1. **A new gate** — if it's mechanically checkable. "Don't use naive datetimes" is a lint rule, not a prompt. Best destination: strictly increasing quality, zero token cost, applies forever.
2. **A line in the repo's `CLAUDE.md`** — if it's judgment the agent could apply given context. Second best.
3. **A critic lens amendment** — if it's a defect class gates can't catch. Most expensive; use last.

Reread the file monthly, not weekly. At 6–12 PRs a week you get 2–6 rejections; week-over-week accept rate on n≈8 swings ±20 points from two tasks and means nothing. This is a markdown file and a monthly habit, not a module with a taxonomy and a dashboard.

**Promote toward bucket 1.** A rule's whole life should be a migration from lens (3) to `CLAUDE.md` (2) to gate (1) — each step cheaper, more reliable, and more permanent than the last. Say "promote to bucket 1", never "up" or "down": the buckets are printed 1, 2, 3 but ordered cheapest-first, so directional words point opposite ways depending on whether you mean the page or the cost.

Two heuristics that need no code:

- If most rejections keep landing in bucket 3, your gates are too weak.
- If `CLAUDE.md` exceeds ~200 lines, you're using prompts where you should be using gates. Audit it and promote what's mechanizable. (The vocabulary in `CONTEXT.md` is exempt and does not count against this — it is definitional, not behavioural. Rules of conduct belong in `CLAUDE.md`; rules of naming belong in `CONTEXT.md`.)

**On mechanizing the triage.** Three of `SA-0001`'s five queries are precisely the questions this section asks you to answer by hand: which acceptance criteria failed on rejected tasks and whether any gate or lens asserted on them; blockers per critic lens split by whether you agreed; and which gates were ever the sole failure — or never fired at all. That is not a licence to build a dashboard. At 6–12 PRs a week the statistics are still noise, and rev 2 cut `learn.py` for exactly that reason; **the cut stands.** The queries are worth having as evidence you can pull up *while* rereading the markdown file, not as a replacement for reading it. And if the RATIONALE concludes they are answerable in SQL, answer them in SQL. Either way: keep the monthly habit and the hand-written line.

The `revert` gate (§5.4) is what this loop looks like when it works: a whole critic lens replaced by one deterministic check.

---

## 9. Build order

Three rules govern this section. **"Unattended" is the last property you turn on, not the first.** And: **build for the repo in front of you, but put the seam where it will be needed.**

And a third, which rev 7 earned the hard way: **the document is not the cheapest defect-finder available.** Appendix E's principle — that a derived artifact written with enough precision finds defects in what it derives from — is true, and it is why this document is as good as it is. But v0 costs one evening and $0, and the two most expensive defects rev 7 fixed (line-keyed baseline subtraction, §5.4; hunk-only finding anchoring, §5.5) are both things a single replayed PR surfaces in an hour and no amount of rereading surfaces at all. Six revisions is enough. **The next artifact written against this document should be v0.**

The second needs stating carefully, because repo-agnostic is exactly the kind of goal that produces a beautiful abstraction serving one caller. The resolution: the *contract* (§5.4) is written now, because a contract is cheap, it is a boundary rather than a layer, and retrofitting one after core has grown language knowledge is genuinely painful. But **no second implementation of anything gets built until a repo needs it.** Saffron ships one base image until a repo needs a second. No plugin registry, no capability negotiation, no adapter interface with a single implementer.

The honest state of the claim: repos one and two are both Python, so the language seam will be designed long before it is exercised. **Repo three is the test** — and it should be chosen for being *unlike* the others rather than for being useful. A small TypeScript or Rust project, onboarded in an afternoon, tells you whether §2.1 holds. If it touches Saffron's source, the boundary failed, and you found out for the price of a weekend rather than after building a plugin system on top of the mistake.

### v0 — the harness, agent-free (one evening, $0 in tokens)

No agent at all. Take three already-merged PRs from a real repo, write specs for them retroactively, and build: spec parse → **gate contract runner** → PR body → index page. The gate runner is written against the JSON contract from the first line — it is the one piece where doing it generically costs nothing extra, because "shell out and parse JSON" is simpler than "shell out and parse ruff."

Why this and not "one agent fixes one bug": that version proves an agent can edit a repo and run pytest, which you already know from using Claude Code interactively. It defers everything unproven — whether the gate runner's structured-result contract survives real tool output, whether the gate set catches what you care about, whether the artifact actually saves you review time — and it runs unattended with your `.env`, your real Postgres, your real `origin`, and open network, which is the highest-risk configuration in the whole design.

Success criterion: replay a merged PR, and the gate table plus PR body tell you something you'd have had to read the diff to learn.

**Shipped 2026-08-19, against `thermal-edge` PRs #172, #169 and #165. Criterion met; four contract defects returned. Appendix H.**

### v0.5 — one cell, attended (a weekend)

Containerized cell with proxy egress, fixture-service image layer, volume worktree, no credentials. One implement session, plan checkpoint, gate loop, no critic. You watch it run.

**The cell runtime is already chosen** — the spike ran ahead of v0.5 and returned `apple/container` on all four assertions (Appendix G, `spikes/cell-runtime.sh`). It cost half an hour and settled a question eight revisions left open, which is the argument for running it early rather than at the start of the weekend it belongs to.

Success criterion: an agent fixes one real bug inside the cell, and the cell demonstrably cannot reach your DB, your keys, or your remote.

### v1 — the factory (2–3 weekends)

- DIAGNOSE + `SCOPE_REVIEW`.
- Full gate set including `scope`, `integrity`, `revert`, `secrets`, `no-network`, `size`.
- Repair loop with baseline comparison and no-progress detection.
- Adversarial review, 2 lenses; rebuttal.
- Scheduler: refusal gate, budget gate, ordering by priority then FIFO. **Not** conflict sets, round-robin or stacking (§4.2) — with one repo and a shallow queue all three are dead code, and `depends_on` waits with them.
- Real PRs + index page.
- **One repo: Saffron itself.** No `--repos` flag yet, no round-robin, but the `repos` table and the `.saffron/` layout exist from the start so that adding the second is data rather than code.

Self-hosting from day one is not the bold choice it sounds like, provided the first tasks put `saffron/` in `forbidden`. **`SA-0001` (the factory ontology) is close to an ideal first task**: `forbidden` covers `saffron/`, `pyproject.toml` and `DESIGN.md`, so the factory structurally cannot modify its own orchestrator or its own design while building it; validation is fixture-based and fully offline, so it runs in a no-route cell; and a wrong answer costs a weekend of Turtle rather than a broken pipeline. Run it *through* the pipeline rather than by hand.

Success criterion: a full night runs while you sleep, and you merge at least half of what it produces before the coffee's cold.

### v2 — the second repo, and sharpening

- **`thermal-edge` onboarded**, and the onboarding is the point: write `.saffron/policy.yaml`, `.saffron/gates/*`, `.saffron/Dockerfile`, and `elevate_on`. **Time it.** If it takes more than an afternoon, N8 is not being met and the contract is wrong somewhere — that measurement is worth more than the repo.
- Multi-repo batching: `--repos`, `--all`, round-robin, per-repo preflight and baselines, repo column in the queue.
- Conflict sets, `depends_on` and stacked branches — two repos and a deeper queue are the condition §4.2 defers them to, and by v2 it has arrived.
- Repo-declared conditional gates against domain surfaces — this is where a repo's real leverage shows up (§5.4).
- Third lens and risk tiering.
- Merge train with re-verification.
- Rejection log habit (§8).

Success criterion: a batch spans two repos, and the diff to Saffron's source required to onboard the second one is **empty**.

### v2.5 — the emitter, conditional

Only if `ontology/RATIONALE.md` says the queries are worth reading: ledger → RDF projection, pyoxigraph store, materialization at batch end, SHACL validation of the projection.

If it says otherwise, move `ontology/queries/` into `docs/` as worked examples and keep the vocabulary as documentation. **That is a completed project, not an abandoned one** — you will have bought a precise answer to "is the relational model costing me anything?" for the price of a weekend, which is the cheapest that answer is ever available.

### v3 — the generality test, then only if v2 is earning its keep

- **A deliberately dissimilar third repo** — TypeScript, Rust, Go; small, chosen for being unlike the first two. This is the only real evidence that §2.1's boundary holds. Budget an afternoon; if it takes a weekend, spend the rest of that weekend fixing the contract rather than the repo.
- Decomposition agent: coarse goal → spec DAG (you approve specs, not code).
- Remote runners, if throughput actually binds — it probably won't before spec-writing does.

**Do not build v3 first.** The gravitational pull of this project is toward the planner, because it's the interesting part. It also has the worst cost-to-value ratio until the verification layer beneath it is trustworthy. A factory that reliably executes good specs is worth a great deal; a factory that generates mediocre specs and executes them unreliably is worth *less than nothing*, because it consumes review attention.

---

## 10. Repository layout

```
~/Code/saffron/
  pyproject.toml
  DESIGN.md              # what the system does
  CONTEXT.md             # what the words mean — injected per phase (§5.3)
  saffron/
    cli.py                 # batch, run, queue, ratify, gc
    ledger.py              # SQLite schema + DAO
    intake.py              # spec discovery, parse, validate (Pydantic)
    scheduler.py           # dep DAG, stacking, conflict sets, budget
    supervisor.py          # per-task lifecycle
    gc.py                  # orphan reconciliation
    cell/
      runtime.py  worktree.py  database.py  proxy.py   # runtime.py is the only file that knows which runtime (Appendix G)
    phases/
      diagnose.py  implement.py  repair.py  review.py  package.py
    agents/
      prompts/             # system prompts, versioned — treat as source
      definitions.py       # per-lens model, effort, tools — host-invoked (§5.5)
      hooks.py             # audit tap + path check (NOT a security control)
    gates/
      runner.py            # host-invoked; shells out, parses the JSON contract
      contract.py          # the gate result schema — the whole repo-agnostic surface
      core/                # scope, size, secrets, integrity — diff-only, no repo code run
    repos/
      registry.py          # repo table, mirrors, enable/disable
      policy.py            # .saffron/policy.yaml parse + validate
      image.py             # build .saffron/Dockerfile FROM a base, cache by sha
    report/
      index.py  pr_body.py  templates/
  images/                  # not docker/ — the runtime is not the format (principle 32)
    cell-base.python.Dockerfile    # agent runtime + git + gate shim. Nothing else.
    cell-base.node.Dockerfile      # added only when a repo needs it
    proxy.Dockerfile
  spikes/
    cell-runtime.sh        # Appendix G's four assertions; delete once cell/runtime.py lands
  ontology/                # SA-0001 — provisional, standalone, not imported by saffron/ (§4.6)
    saffron.ttl            # the vocabulary
    shapes/                # SHACL; every shape has a negative fixture it rejects
    queries/               # Q1–Q5, each with expected results + its SQL challenge
    vendor/                # prov-o.ttl, earl.ttl — committed by hand, never fetched
    RATIONALE.md           # ≤40 lines; the verdict on whether to build the emitter
  tests/
  .saffron/                # Saffron is itself a target repo — same shape as any other
    specs/  policy.yaml  gates/  Dockerfile
```

**Note what is absent: no `languages/`, no `adapters/`, no `plugins/`.** If a directory like that ever appears, §2.1 has been abandoned. The only language-shaped artifacts in the whole tree are the base Dockerfiles, which install a runtime and nothing else.

And the other half of the layout — the part that lives in every target repo, and the entirety of what onboarding means:

```
<any-repo>/
  .saffron/
    policy.yaml            # gate roles + blocking levels, elevate_on, protected,
                           #   envelope defaults, integrity patterns, thread_env
    gates/
      lint  types  tests  no-network  coverage   # executables → gate JSON (§5.4)
      shacl  migration                            # repo-defined, conditional
    Dockerfile             # FROM saffron/cell-base:<runtime>; toolchain, services,
                           #   migrations and seed data baked at build time
    specs/                 # the queue
  CLAUDE.md                # standing agent instructions — the learning surface (§8)
```

`agents/prompts/` is a directory of versioned files, not string literals in Python. Prompts are the most-edited artifact in a system like this; you will want to diff them, blame them, and correlate a quality regression with a prompt change. Treat them as source.

---

## 11. Trade-offs, stated explicitly

| Decision | Chosen | Rejected | Cost of the choice |
|---|---|---|---|
| Repo knowledge | Entirely in the repo's `.saffron/` | Adapters/plugins in Saffron | Every repo writes ~20 lines of shell per gate; core never learns a toolchain |
| Gate interface | Executable → one JSON object | Core parses tool output | Repos do their own translation; the orchestrator has zero parsers |
| Services (DB, cache) | Baked into the repo's `.saffron/Dockerfile` | `services:` in policy, core runs Compose | Repo owner writes a Dockerfile; core stays out of service lifecycle |
| Batch scope | One pool, one budget, all repos | Per-repo batches | Repos contend for the same 3 cells — but visibly, with round-robin, rather than by accident |
| Cross-repo deps | Not supported | Coordinated merge trains | Two specs and a manual sequence; no version of the alternative is simple |
| Runtime | Local Mac, containerized | Cloud CI | K=3 ceiling; Mac must be awake; you own the container plumbing |
| Cell runtime | **`apple/container`** — VM per cell, decided by spike (Appendix G) | Shared VM (Docker Desktop/Colima); or deciding by taste | No `no-new-privileges` or seccomp, a young runtime, and a measured `--cpus` offset to carry; buys a private kernel per cell and no shared memory allocation |
| Orchestration | Agent SDK + custom Python | Claude Code headless + shell | Weeks of harness code you own forever — bought back in host-side gate enforcement and structured state |
| Task queue | Spec files in target repo | GitHub issues | You write markdown instead of clicking; no notifications |
| Review UI | GitHub PRs + a thin index | Custom dossier viewer | Index is dumb; you're in a browser tab, not a local page |
| Scope control | Agent proposes, human ratifies (bugs) | Human declares upfront | One extra round trip per bug spec; avoids inverting who does the diagnosis |
| Dependencies | Satisfied at `READY_FOR_REVIEW`, stacked | At `MERGED` | A rejected parent wastes its children; avoids one-task-per-night |
| Test quality | `revert` gate | Mutation testing | Coarser signal; fits the window, costs one test run |
| Coverage | Advisory | Blocking | Weaker guarantee; avoids rewarding assertion-free tests |
| Egress | Allowlisting proxy | iptables in cell | Extra container; works with `--cap-drop ALL` and CDN endpoints |
| Isolation | Container + volume + repo fixture services | Worktree only | Real build/teardown complexity; the only thing that makes "unattended" defensible |
| State | SQLite + plain batch tree | Postgres + content-addressed store | No dedupe; recovers when everything else is broken |
| Factory analytics | Derived one-way RDF projection, provisional (§4.6) | Authoritative graph store; or nothing at all | A vocabulary to maintain and a sync step — and it may conclude it isn't worth emitting, which counts as a result |
| Conflicts | Prevent by scheduling | Resolve by rebase | Lower parallelism; no "two green PRs that break each other" |
| Merge | Human, always | Auto-merge on green | You remain the throughput ceiling — correctly, at this scale |

**What I'd revisit as it grows:**

- **K = 3 and the single machine.** The first real ceiling, and multi-repo brings it closer — three repos with healthy queues will saturate three cells long before one repo would. Revisit when a batch consistently fails to drain, not when it merely feels slow.
- **The gate contract's shape.** It survives contact with two Python repos trivially. The interesting questions arrive with repo three: does `failures[]` with `file`/`line`/`code` fit a compiler that reports spans rather than lines, or a test runner that reports suites rather than files? Expect one field to be wrong. Change it then, with a real second opinion in hand, rather than speculatively widening it now.
- **Refusing agent conflict resolution.** §5.7 sends every rebase conflict to `MERGE_FAILED`. Prior art (Appendix D) runs a better-shaped version: the host attempts `git merge` itself and only invokes an agent on genuine conflict, then verifies the result deterministically (`git diff --diff-filter=U` empty, HEAD actually moved) before allowing a push — with the agent explicitly told *"do not invent new behaviour; reconciliation is not feature work; if a sensible resolution requires logic that was on neither side, flag uncertainty rather than be creative."* Their version is weakly verified because they have no gates. **Saffron's would be gate-verified**, which is a materially different risk profile — a resolved conflict runs the full suite before it reaches you. Revisit once `MERGE_FAILED` volume is annoying enough to measure; the deterministic-first / LLM-as-fallback shape is the right one, and it should stay off until the gates have earned trust.
- **`scope` having one severity for every kind of escape.** v0 put a new file the spec's own acceptance criteria required, three docs files, an adjacent source file and a dbt test into one `out-of-scope` bucket at identical weight (Appendix H). Not fixed, because the case that produced it — `touches` hand-written before anyone saw the diff — is the case §5.2 removes for bugs: in the real pipeline DIAGNOSE proposes and you ratify. If ratified `touches` still produces mixed-weight escapes once bugs run for real, that is the evidence to act on.
- **Per-repo budgets.** Deliberately not built — you have no data to tune them with. Once you have three months of cost-per-accepted-PR *by repo*, a repo that reliably costs triple is an argument for its own ceiling.
- **`revert` vs. mutation testing.** If gate wall-clock stops being the constraint (faster fixtures, more cores), mutation sampling on `risk: elevated` diffs becomes affordable and is strictly stronger.
- **Conflict-set scheduling.** Limiting once you have many small tasks in one hot module. The principled upgrade is function-level conflict sets, which is a lot of work; the cheap alternative is batching hot-module specs into one task.
- **`SCOPE_REVIEW` as a human step.** If ratification becomes rubber-stamping — you approve 95% of proposed scopes without edits — auto-ratify when the proposal stays inside `envelope` and only surface the exceptions.
- **Human-in-the-loop merge.** Keep it. But the *shape* of your review should shrink as gates absorb your rejection reasons. If in six months you're still reading full diffs line by line, the flywheel isn't turning — and that's the thing to fix, not the merge click.
- **The `gate_results` / `findings` split.** EARL models both as one assertion shape (§4.6). If the RATIONALE confirms that isn't an accident of vocabulary, unify them in SQL too — the PR body already renders them as one table.
- **The critic layer's ROI.** Track how many blockers it raises that you agree with. If that trends toward zero, gates have absorbed its job and you can cut a lens and its cost. That would be a success, not a regression. (This is `SA-0001`'s Q2, and it is the query most likely to justify the whole projection — it is a three-way join across findings, decisions and lens identity that is genuinely unpleasant in SQL.)

---

## Appendix A — What changed in rev 2, and why

Rev 1 was reviewed adversarially. Nine findings survived scrutiny; all are incorporated above. The ones worth remembering as *principles*, because they'll recur:

1. **A gate that requires the human to already know the answer isn't a gate, it's a tax.** (Hand-written `touches` on bug specs → DIAGNOSE.)
2. **A dependency edge that can only be satisfied by a human action outside the batch will never be satisfied inside it.** (`MERGED` → `READY_FOR_REVIEW`.)
3. **A walking skeleton must contain the hard part.** Rev 1's v0 deferred the gate contract, the artifact, and all isolation — and turned unattended execution on first.
4. **Controls inside the untrusted zone are not controls.** (In-agent hooks and Bash regex denylists demoted to ergonomics.)
5. **Two safety mechanisms that make each other dead code mean you picked one without noticing.** (Abort-on-red vs. baseline subtraction.)
6. **A blocking metric gate teaches the cheapest way to satisfy it.** (Coverage → advisory; `revert` → blocking.)
7. **Resource limits that the runtime doesn't actually enforce produce flakiness you'll misattribute to the model.** (`--cpus` vs. `--cpuset-cpus` + thread env vars.)
8. **Detection without reclamation is not a countermeasure.** (Disk preflight → `saffron gc`.)
9. **A voting rule over disjoint voters never votes.** (Majority-of-lenses → any blocker.)

Rev 1 sections that survived unchanged: specs-in-target-repo, SQLite-for-recoverability, three-axis bounding, host-invoked gates, the critic's "say so if there's nothing" clause, never letting an agent resolve conflicts, and the warning against building the planner first.

---

## Appendix B — rev 3: the factory ontology

`SA-0001` defines a PROV-O/EARL vocabulary for Saffron's own run record (§4.6). Two principles it contributes, both generalizable beyond ontologies:

10. **A design artifact can succeed by concluding "don't build it."** The spec's deliverable includes a rationale that challenges every one of its queries against a SQL equivalent, and a verdict of "SQL is fine" is a pass. This is the cheapest possible form of that answer. The expensive form is an emitter you maintain for a year before noticing nobody reads it.
11. **Modelling pays before it ships.** Writing down what an *attempt* is in relation to a *gate run* produced two schema criticisms (§4.6) that hold whether or not a triple is ever stored. The output of a modelling exercise is not only the model.

**And one correction the spec forced on the design.** §5.4 listed `size` as always-blocking; §5.6 described it as *becoming* blocking at `risk: elevated`. Both couldn't be true. `SA-0001`, written against the document and reasoning about its own 600-line ceiling, tripped on the contradiction. Resolved in favour of §5.6: `size` is advisory at standard risk, blocking at `elevated`.

That is worth noting for its own sake. The first real spec written against this design found a defect in it — which is the same mechanism as §5.2's plan gate, operating one level up. Specs are a test suite for the design document, and they should be read that way: a spec that is awkward to write is evidence about the design, not about the spec author.

---

## Appendix C — rev 4: repo-agnostic

Saffron develops any repo, in any language. `thermal-edge` is demoted from *the* target to *an* example — the second repo, after Saffron itself.

**What actually changed, structurally.** Only one thing, and everything else follows from it: **the gate contract** (§5.4). A gate is an executable emitting one JSON object. That single decision is what lets the repair loop, baseline subtraction, and the whole review pipeline stay language-blind, because nothing downstream ever sees tool output — it sees `failures[]`. The corollary that makes it work is that gates translate their own output, which pushes ~20 lines of shell into each repo and keeps every parser out of the orchestrator.

The rest is bookkeeping: a `repos` table, per-repo preflight and baselines, round-robin scheduling, a repo column in the queue.

Three principles this revision contributes:

12. **A boundary is cheap; an abstraction layer is not.** The contract gets written now because retrofitting one into a core that has grown language knowledge is painful. The *second implementation* of anything waits for a repo that needs it. There is no plugin registry with one plugin.
13. **When a check feels language-specific, separate the question from the vocabulary.** "Was a test deleted or silenced?" is universal; `@pytest.mark.skip` is not. Put the question in core and the tokens in `policy.yaml` (§5.4, `integrity`). This is the single most reusable move in the whole design.
14. **Generality is a claim, and claims need tests.** Two Python repos prove nothing about language independence. Repo three exists to falsify §2.1, should be chosen for dissimilarity rather than usefulness, and has a pass condition stated in advance: the diff to Saffron's source is empty.

**What did not change, and shouldn't:** every safety property in §5.1 is about containers and git, not about languages, so repo-agnostic costs nothing there. The critic lenses (§5.5) are stated in terms of correctness, contracts and blast radius rather than any stack — that was accidental in rev 2 and is load-bearing now. And §8's flywheel becomes *more* valuable with multiple repos, because a rejection reason promoted from `CLAUDE.md` to a gate in one repo is a gate you can copy into the next.

---

## Appendix D — rev 5: lessons from prior art

Reviewed `mattpocock/sandcastle` — a TypeScript library for orchestrating coding agents in sandboxes, plus the author's own factory built on it (a label-driven GitHub Actions pipeline, and two earlier abandoned generations: a local daemon and a parallel planner).

**The headline finding is a negative one, and it is the most useful thing here.** Their pipeline has essentially no verification. `ci.yml` is `on: push: branches: [main]` — **no `pull_request` trigger**, so agent PRs receive zero automated checks before a human merges them. Every "run the tests" instruction is prose inside a prompt, executed and self-assessed by the agent. Their own library documents the host-side gate pattern explicitly — *"`sandbox.exec()` … handy for gating an implement step on a quick verification"* — and their factory never uses it. Their reviewer is framed as a refactoring agent told to *"preserve exact functionality"*, posts `event: "COMMENT"` (never `REQUEST_CHANGES`), and then calls `gh pr ready` — it advances the PR and structurally cannot block it. There is nothing anywhere on anti-gaming, baselines, or repair loops; their iteration terminates when the agent prints `<promise>COMPLETE</promise>`, a string the agent controls.

This is a serious, well-engineered project by a capable author, and it converged on: **good process hygiene, near-zero verification.** Read that as evidence about where the gravity pulls. Process is visible, satisfying, and produces a working pipeline quickly; gates are invisible until the day one catches something. Saffron's entire bet is the other way round, and this is the strongest argument yet for not letting that bet erode when the harness work gets tedious.

**What they do better, adopted here.** All operational, all things you learn by running something overnight rather than by designing it:

15. **Treat agent output as claims; reconcile against a host-computed fact set.** They validate the reviewer's inline comments against parsed diff hunks and drop the ones that don't land. Generalized in rev 5 to critic findings (§5.5) and to phase transitions (§4.3, doneness measured from git — `commitsAhead`, HEAD-moved, `--diff-filter=U`). This is the same principle as host-invoked gates, extended from quality to control flow.
16. **Bound liveness on more axes than you think, and never let a bound destroy work.** Their ADR-0019 documents an agent finishing, a spawned child holding stdout open, EOF never arriving, the full idle timeout burning, and *then the committed work being discarded*. Hence rev 5's split of idle from completion, and the rule that any bound firing still evaluates the worktree (§4.3).
17. **Refuse before you spend.** Their workflows check issue shape and existing PRs before starting an agent. Rev 5 makes this scheduler gate 0 (§4.2).
18. **Structured output is a separate, tool-less turn** — do the work, then resume the session with a prompt that forbids acting and asks only for the block (§5.3). Bounded schema retries, never content retries.
19. **Retry idempotent infrastructure races; fail fast on everything that builds what the agent acts on.** Their ADR-0020, on a prompt-expansion timeout under parallel load: degradation is worse than abort, because a silently-wrong prompt burns an attempt producing plausible garbage (§4.3).
20. **Control files in the workspace are agent-visible and agent-writable.** Their worktree lock deliberately lives outside the worktree — *"visible to the agent, which could delete or commit it."* Saffron had `plan.json` inside `/work` after validation; fixed (§5.3).
21. **`--force-with-lease` pinned to the checked-out SHA, and one writer per branch** (§5.7). Turns a silent clobber into a loud failure for the price of a flag.
22. **Source determines processing** — their ADR-0008: inline prompts skip templating entirely, because callers pipe issue bodies containing `{{...}}` into them. Spec text is data (§5.3).
23. **A living refusal record.** Their `.out-of-scope/` gives each refused feature a doc: what, why, which seam covers it, and the prior requests. Adopted for §1.4.
24. **A glossary with explicit *Avoid:* lists**, read by agents before they touch code. Cheap, and it competes directly with the ontology — so it is now a second bar `RATIONALE.md` has to clear (§4.6, rule 2b).

**Deliberately not adopted.** GitHub labels as the task queue and state machine — it's a good fit for a public repo with contributors and a poor one here, where specs-in-repo buy version-controlled acceptance criteria and offline batches. Their `<promise>COMPLETE</promise>` completion signal, for the obvious reason. And their reviewer framing, which is the thing Saffron most specifically rejects.

---

**One thing to actually go read, independent of this design:** `docs/research/permissions-systemic-fix.md` and ADRs 0005/0014 — a full taxonomy of container UID/permission failures, including that macOS assigns GID 20 to `staff` while `node:22-bookworm` already uses it for `dialout`, so `groupmod -g 20` fails and the image build dies without `-o`. Also that a single-file bind mount whose parent doesn't exist in the image causes Docker to create the parent as `root:root` and silently break auth. Those will cost a day each to rediscover, and §5.1's cell will hit both.

---

## Appendix E — rev 6: what the vocabulary found

`CONTEXT.md` (Appendix D, item 24) was written against this document. Like `SA-0001` before it, the artifact found defects in the design it was derived from — three, all of which had survived four revisions and an adversarial review:

- **Accept rate could not appear in the batch header.** §6 claimed it; the definition — merged over completed — made the impossibility plain. Nothing is merged when a batch ends, because merging is the next morning's work. Now a *trailing* rate over prior batches (§6).
- **`runs` had no batch identity.** Rev 4 quietly turned a run into *one repo's slice* of a night and left it in the table that used to mean the night itself. A multi-repo batch was unqueryable. Now `batches` exists, budget lives on it, and `gate_runs` became `gate_results` to retire the third sense of the word (§4.1).
- **The finding severity scale was defined nowhere in this document.** It had a `severity` column, a rule about blockers, and a queue line printing "1 concern" — and never stated the levels. Writing them down surfaced that two levels were not enough: with only `blocker` and `concern`, every true-but-trivial observation inflates the number that drives queue sort order. `note` added (§5.5).

Two principles from this, and the first is the one worth keeping:

25. **A vocabulary is a test suite for a design, in the same way a spec is.** Both `SA-0001` and `CONTEXT.md` found real defects purely by being written *against* the document with enough precision to force a contradiction. This is now twice in a row, which stops being luck. **Any derived artifact that has to be exact — a glossary, a spec, a schema, a prompt template — is worth writing partly for the defects it will surface.**
26. **Directional words need a fixed referent.** "Promote down the bucket list" is ambiguous the moment the list is printed 1, 2, 3 but ordered cheapest-first. Name the destination, not the direction (§8).

Also settled here: the vocabulary is injected per phase rather than wholesale (§5.3), and it is exempt from the `CLAUDE.md` line budget because it is definitional rather than behavioural (§8).

---

## Appendix F — rev 7: what a read-through found

`SA-0001` and `CONTEXT.md` each found defects by being *written against* this document (Appendix E, principle 25). Rev 7 is the cheap version of the same move: reading the document end to end against the vocabulary, writing nothing. It found nine things, and the two most expensive of them had survived an adversarial review and five revisions.

**Three contradictions the document was already carrying.**

- **`coverage` was blocking and advisory at the same time.** §5.4 argued at length that a blocking coverage gate rewards assertion-free tests; §5.6 then made it blocking at `risk: elevated`. Resolved in favour of §5.4, at every tier. This is the identical defect Appendix B caught in `size` — in the same sentence — and it survived because only half the sentence was fixed.
- **"Bounded on three axes", followed by five rows and the words "Five, not three."** `CONTEXT.md` said five. A residue of rev 5, and the kind of thing the companion document exists to catch.
- **`revert` broke §2.1's boundary as stated.** §2.1 said any core gate needing to *execute* something belongs on the repo side; §5.4 said `revert` is "the one place core reaches into the repo's toolchain." The rule is now stated so the exception fits inside it: **core invokes declared gates, never tools.**

**Six defects that would have shipped.**

- **Baseline subtraction was keyed on `line`.** The worst of them. Any diff that is not append-only shifts pre-existing failures, so untouched failures would have read as new and the repair loop would have spent attempts on code the task never wrote — the §7 countermeasure defeating the exact failure it was built for. Identity is now `(gate, file, code)`. The same fix rescues no-progress detection, which was comparing bytes across a set whose line numbers move every attempt, and would therefore never have fired.
- **Finding anchoring would have zeroed out lens #3.** Blast radius is *what else calls this*, so its findings point at unchanged lines; a hunk-only reconciler drops them all, silently, and the drop-rate diagnostic would have blamed the prompt. A second anchor admits a line that names an identifier the diff changed.
- **REBUT had no edge out of failure.** One attempt, gates re-run, and nothing in §3.3 said what happens when the re-run is red. It is `EXHAUSTED`.
- **`saffron gc` ran a night behind itself.** `ORPHANED` was inferred from a 24h-stale `updated_at`, but a cell killed at 06:30 is twelve hours old at the next batch start — so nothing was ever freed on the cycle that killed it. The supervisor now stamps `ORPHANED` at death and the delay runs from there.
- **`--cpuset-cpus` pins into a hybrid core list.** A cell landing on efficiency cores runs its gates several times slower than its siblings, reintroducing per-cell timing variance — the flaky-gate mode that bullet was written to remove. P-cores only, enumerated at preflight.
- **`SCOPE_REVIEW` writeback had no home.** "Written back into the spec file" meant either an unattended write to a remote `main` (forbidden by N1) or a `spec_sha` move that invalidates the task ratification just unblocked (§4.1). It now rides the task's own branch as its first commit, which needs neither exception.

**Two scope corrections**, both applications of rules the document already states to places it had not applied them: the scheduler's conflict sets, round-robin and stacking are deferred to v2 (§4.2, §9), because at a two-deep queue they arbitrate contention that never arrives; and §9 gains a third rule.

Four principles, and the first two are the ones that generalize past this system:

27. **An identity that includes a coordinate the change moves is not an identity.** Line numbers, byte offsets, array indices, row numbers — anything the diff renumbers is a display field. Key on what survives the edit.
28. **A reconciler tuned to one producer silently disables another.** Filters fail closed and leave no error, so the symptom shows up attributed to whatever they filtered. Every drop rule needs to be checked against every producer that feeds it, not just the one it was written for.
29. **A rule with an unstated exception has been abandoned, not weakened.** §2.1's boundary was false from the moment `revert` was added, and stayed useful only because nobody tested it. Write the exception into the rule and the rule keeps working.
30. **Fixing half a contradiction leaves a contradiction.** `size` and `coverage` were wrong in one sentence; rev 3 fixed one word of it and the appendix recorded a win.

And the method note, promoted into §9 as its third rule: **this pass cost an hour and found more than rev 6 did.** But the two defects at the top of the list — line-keyed identity, hunk-only anchoring — are things a single replayed PR surfaces immediately and no reading surfaces reliably. Rev 8 should not be a document.

---

## Appendix G — rev 8: the cell runtime

Every previous revision wrote **Docker** as though it were a decision. It was never made. §5.1's cell is described entirely in Docker's flag vocabulary, §4.2's concurrency arithmetic closes against a Docker Desktop VM allocation, and §7 has a row whose countermeasure is a Docker flag — while the actual intent was Colima, a different program that was never named anywhere. So the runtime was a proper noun standing in for a contract, which is the one mistake §2.1 exists to catch, committed in the section §2.1 does not cover.

Rev 8 names the candidates, finds the defect that naming them surfaced, and then **declines to choose**, because the choice binds at v0.5 and not before.

### Two architectures, three products

The first draft of this appendix listed three candidates and dismissed Docker Desktop on a licence and a menu bar. Both objections are wrong at this scale — Docker Desktop is free under Docker Personal for an individual, and `docker desktop start|stop|status` has been a CLI since 4.37, so it drives from `launchd` like anything else. Withdrawn. What matters is that **the choice is binary, and it is not a choice between three products:**

**A. Shared VM, Docker API — Docker Desktop *or* Colima.** One Linux VM on Apple's Virtualization.framework, one kernel, dockerd inside it, all cells sharing it, a Docker socket on the host. These two are *the same architecture*, and every line of §5.1 behaves identically on either — including the `cpuset` finding below, which is a property of the shared VM and not of the product managing it. They differ only in operator ergonomics: Colima idles at ~400MB against Docker Desktop's 2GB+ and is MIT-licensed with no account at all; Docker Desktop is the far more heavily exercised path, which is the argument that actually counts for an unattended eight-hour run, and Colima's occasional need for a restart is exactly the failure a 03:00 batch cannot absorb. Docker Desktop is also the only option anywhere on this page offering **user-namespace hardening** — Enhanced Container Isolation, container root mapped to an unprivileged host UID via Sysbox, holding even against `--privileged`. That is squarely aimed at §2's untrusted cell, and it is **Business-tier only** (~$24/user/month), which makes it a real option to price rather than a feature to assume.

**B. VM per cell — `apple/container`.** Apple's own runtime, **1.0.0 as of June 2026**, CLI and XPC API frozen across 1.0.x. A separate lightweight VM per container. No Docker socket: the supervisor shells out to a CLI that emits structured JSON.

**Nothing in this document distinguishes A-with-Docker-Desktop from A-with-Colima.** That is the useful result: pick between them on ops taste at v0.5, switch later for the price of a `DOCKER_HOST`, and record neither in the design. The decision that has design consequences is A versus B.

### What naming them found

**§5.1's rev-7 P-core fix does not work, on any of them.** Rev 7 caught that `--cpuset-cpus 4,5` indexes a hybrid core list and told preflight to enumerate the performance cores and pin to those. That is correct on Linux and meaningless on macOS: `cpuset` is interpreted by the kernel that reads it, and on macOS that kernel is always inside a VM, so the mask indexes **virtual** CPUs. Which physical core a vCPU thread lands on is macOS's scheduling decision and no flag reaches it. Under `apple/container` there is no pinning flag at all. So rev 7 fixed a real hazard with a control that does not exist on the machine Saffron runs on — and it read as fixed for one revision because nothing had been run.

The hazard is unchanged and now belongs to detection: vCPU threads are scheduled onto P-cores first and spill to E-cores under contention, so a cell can run its gates measurably slower than its siblings, and §7's countermeasure is now per-gate wall clock plus cross-cell variance rather than a flag.

**What survives is the requirement underneath it.** The reason §5.1 rejected `--cpus` was never affinity — it was that a CFS quota leaves the *visible* core count untouched, so thread pools size themselves from the host's core count and oversubscribe. Both candidates satisfy the real requirement, by different mechanisms: `cpuset` restricts the affinity mask the guest reports, and a per-cell VM configured with N vCPUs simply *has* N CPUs, so `nproc` is honest with no flag at all. The second is the stronger form — it is structural rather than declared — and it is the single largest point in `apple/container`'s favour.

### The comparison that actually matters

| | **A.** Shared VM (Docker Desktop *or* Colima) | **B.** VM per cell (`apple/container`) |
|---|---|---|
| Isolation | Shared kernel, one VM | **VM per cell** — a stronger structural boundary for §2's untrusted cell |
| Cell sees only its CPUs | Yes, via `cpuset` | Yes, structurally — the VM has that many vCPUs |
| Pin physical P-cores | **No** (indexes vCPUs) | **No** (no such flag) |
| Memory ceiling | One shared VM allocation to divide by K | No shared allocation; cells draw against the machine |
| Fast worktree storage | virtiofs mounts, or a volume | Named volumes: sparse ext4 over virtioblk, documented as faster than bind mounts |
| Isolated network | Docker `--internal` | `container network create --internal` |
| `--cap-drop ALL` | Yes | Yes (default set is already restricted) |
| `no-new-privileges`, seccomp, userns | Yes | **Not exposed** — the VM is offered as the boundary instead |
| Host integration | Docker socket; ordinary Python client | CLI shell-out, structured JSON `inspect`/`ls`; `exec` exists |
| Maturity | Years of use; Docker Desktop the most-exercised path on macOS | 1.0.0 in June 2026, API frozen for 1.0.x |
| User-namespace hardening | Docker Desktop only, **Business tier** (ECI/Sysbox) | No — the VM is offered instead |
| Idle overhead | ~400MB (Colima) to 2GB+ (Docker Desktop) | Per-cell VMs; nothing standing between batches |

Two operational facts that apply to **both**, and neither is in §5.1 today:

- **An `--internal` network still routes to the host gateway.** A host service bound to `0.0.0.0` — your Postgres — is reachable from inside a cell without ever traversing the proxy. N1 is the requirement this threatens, and the countermeasure is on the host: bind services to `127.0.0.1`, and prove it with a preflight probe rather than assume it. The `--internal` flag is not the whole boundary it reads as.
- **Isolated networks have no DNS.** `HTTPS_PROXY=http://saffron-proxy:3128` does not resolve. Pin the subnet at network creation and address the proxy by IP.

Missing `no-new-privileges` and seccomp is a real deviation, but it is the deviation §2 already argues for: a private kernel per cell is a *better* structural boundary than a shared one plus in-guest hardening, and §2's whole claim is that the controls that hold are the structural ones.

### The decision, and when it gets made

*(Superseded by "The decision, made" below. Kept because the spike it specifies is
the artifact that settled this, and because a prediction is only worth something
if it stays legible next to its result.)*

Deferred to **v0.5**, which is the first version where a cell exists at all — v0 is agent-free and touches no container. This is §9's rule about second implementations applied to a runtime: the *seam* gets written now because it is cheap, and it is one file. `saffron/cell/runtime.py` is the only module that knows which runtime, and the surface it hides is small enough to write down here: create a volume, run a container with a network, env, and CPU/memory limits, exec into it, collect artifacts, destroy it. Nothing above that file changes if the answer changes.

The spike that decides it is half an hour, and it is four assertions against a real cell on an internal network:

1. `nproc` inside the cell equals the CPUs it was allocated.
2. Egress to an unlisted host fails.
3. The proxy is reachable, by IP.
4. A Postgres on the host is **not** reachable.

Run it against `apple/container` first. If all four hold, take it — the isolation is better, the memory ceiling is better, and §5.1 gets shorter. Architecture A is the fallback and it is a good one: the Docker socket makes the supervisor duller to write, and dull is worth something at 03:00. If it wins, start on Docker Desktop rather than Colima — an unattended nightly batch weights *fewest surprises* over 1.6GB of idle RAM, and that ordering can be revisited the first night the idle footprint actually costs a cell.

Three principles, and the first is the one that generalizes:

31. **A resource control means whatever the kernel reading it can see.** `cpuset` pins host cores on Linux and virtual cores in a VM — same flag, same syntax, silently different guarantee. Every limit, mask, and quota needs verifying against the layer that actually enforces it, not the layer whose documentation you read.
32. **A product name in a design is an unmade decision wearing a decision's clothes.** "Docker" appeared in six sections and was never chosen; it survived four revisions and an adversarial review because a proper noun reads as settled. §2.1 catches this for languages and toolchains and did not catch it one layer down, for the runtime the whole cell is built on.
33. **A countermeasure written against an environment you have not run on is a hypothesis.** Rev 7's P-core enumeration was reasoned correctly from a false premise about where `cpuset` applies, and recorded as a fix. This is the third time an appendix has argued that the next artifact should be executable (§9); it is now also the reason.

---

## Appendix H — rev 9: what v0 found

Every previous revision was a document reading a document. Appendices F and G each
ended by arguing the next artifact should be executable; §9 made it a rule. v0 is
the first revision that ran — three merged `thermal-edge` pull requests replayed
through the agent-free harness (#172, #169, #165, as `TE-9001`–`TE-9003`) — and it
is worth recording what that bought and what it did not.

**The criterion was met, and by the intended mechanism.** `TE-9001`'s rendered PR
body states that the settled-high defect understated 7 of 108 stored days, that two
of the seven are invisible to the obvious METAR proxy check, and why — none of
which is derivable from reading the diff, because it came from an audit against
external settlement data. That is the artifact doing the job §0 claims for it.

**The mechanism v0 existed to test held.** `(gate, file, code, normalized message)`
with `line` excluded survived three real diffs, one of them +1905/−49. Two files
already carrying `format` debt at base, still failing at head, correctly stayed off
the new-failure table. That is §5.4's rev-7 fix confirmed against real tool output
rather than reasoned about.

### The headline finding: a green gate suite that never ran

The first replay of `TE-9001` reported `format` and `lint` as `pass` in 0.3s each,
with `types` clean — against a repository carrying 402 files needing reformatting
and 57 type errors. Saffron's own process environment had leaked into the gates it
shells out to, so every gate resolved a different Python environment than the one it
was written for, and the shell scripts swallowed the resulting failures into an
empty `failures[]`.

The defect worth recording is not the leak. It is that **nothing in the gate
contract could express the difference.** `{"status":"pass","failures":[]}` is
bit-for-bit identical whether the tool ran and found nothing or never ran at all,
and `duration_ms` is no help — genuine `ruff` against that whole repository also
finishes in 0.3s. It was caught only because someone remembered a baseline figure
from a week earlier and noticed 0 was not 396. An incidental catch, unattended, at
03:00, is not a catch.

Hence §5.4's `tool` field, obtained by executing the tool, and the two `error` rules
beside it. Three of the four defects below collapse into one shape once stated that
way, which is the argument for fixing it at the contract rather than in four gates.

### The other three

- **`tests` cannot say a worker crashed.** A lost `pytest-xdist` worker puts the
  test's own name in `code`, exactly like a real assertion failure. A repair loop
  consuming that JSON cannot tell "your change broke this" from "the runner lost a
  process, re-run it" without pattern-matching free text. Resolved by rule rather
  than by schema: partial results are not results, and the gate returns `error`
  (§5.4).
- **`format`'s parser is coupled to an unversioned CLI string.** A `ruff` release
  rewording one line makes every match vanish and the gate reports a false `pass` —
  the same failure shape as the environment leak, from a different cause. Covered by
  the same two guards.
- **`scope` has one severity for every kind of escape.** A new file the acceptance
  criteria required and three unrelated docs files rendered identically. Recorded as
  a thing to watch rather than fixed; §11 says why.

### And two the replays did not find

Both were found by review afterwards, and both are the more interesting half of this
appendix, because they are the shapes three green runs happened not to contain:

- **Baseline subtraction was a set difference.** `normalize_message` collapses digit
  runs — correctly, since messages embed the coordinate the identity exists to
  exclude — which means two failures of one rule in one file differing only in their
  numbers share an identity legitimately. Under set semantics one pre-existing
  failure then cancelled *every* head failure sharing it. The subtraction is now a
  multiset operation (§5.4), and so is no-progress detection, for the same reason.
- **`M^1` is not the branch point.** Resolving a merge commit's base as its first
  parent takes `main` as of the merge, so where `main` advanced while the pull
  request was open, commits the task never touched entered both the diff and the
  baseline. The base is the merge base of the two parents.

Three principles, and the first is the general one:

34. **A green result and an absent result are the same bytes.** Any contract that
    reports outcomes must carry evidence that the thing which produces outcomes ran.
    Absence renders as success in every schema that does not ask, and the failure is
    silent by construction — which makes it exactly the kind that survives an
    unattended night.
35. **When identities can legitimately collide, subtraction has to count.** A
    normalization that erases a distinguishing field is usually right and always
    turns set difference into cancellation. If two rows can be the same key on
    purpose, the operation over them is arithmetic, not membership.
36. **Partial results are not results.** A mechanism that broke half way through
    produces output shaped exactly like output. Give the producer the vocabulary to
    disown its own run, and prefer one re-run charged to nobody over a consumer
    reasoning about a truncated set.

**The method note, since three appendices in a row now predict it.** Rev 7 found
nine defects by reading and said the next artifact should be executable. Rev 8 found
that rev 7's central fix was not implementable on this machine and said it again,
this time as principle 33. Rev 9 is the first one that ran, and the defect it found
first — a whole gate suite reporting green while doing nothing — is not visible to
any amount of rereading, because the document was never wrong about it. It simply
never asked. **The next artifact should be v0.5**, and the four-assertion runtime
spike is what it starts with.

### The decision, made

Run ahead of v0.5, as `spikes/cell-runtime.sh`, on 2026-08-19 against
`apple/container` **1.2.2** (not the 1.0.0 this appendix was written against; the
frozen-API-across-1.0.x claim no longer covers what installs today). All four
assertions hold:

```
1. the cell sees only the CPUs it has     nproc = 3 for --cpus 2, host has 11
2. egress to an unlisted host fails       example.com unreachable
3. the proxy is reachable, by IP          10.88.0.3:3128 reachable
4. host services are not reachable        127.0.0.1-bound unreachable, gateway and LAN
```

**Take it.** Every flag §5.1 needs exists — `--internal`, `--subnet`, `--cpus`,
`--memory`, `--cap-drop`, `--network`, `--mount`, `--rm` — and the two that do not
(`no-new-privileges`, seccomp) are the deviation this appendix already argued for.
§5.1 is rewritten in the runtime's own vocabulary and is shorter for it.

Three things the run found that reading could not:

- **`--cpus n` allocates n+1 vCPUs, deterministically** — 1→2, 2→3, 4→5, 6→7. The
  count is honest about the VM the cell is in, which is the property that matters;
  the VM just gets one more than requested. A calibration constant, not a defect,
  and §5.1 now carries it as one.
- **Both no-DNS predictions were right.** The proxy answers on its IP and its name
  does not resolve on an internal network. `HTTPS_PROXY` by hostname would have
  failed at v0.5 with a DNS error nobody would have connected to this page.
- **The `0.0.0.0` hazard is real on two paths, not one.** A host service bound to
  the wildcard address is reachable from inside a cell at the gateway *and* at the
  machine's LAN address, never touching the proxy. The `127.0.0.1`-bound one is
  unreachable from both. N1 rests on a binding choice, and the preflight probe that
  checks it is not optional.

### What the spike did to itself

Its first run reported `3 passed, 2 failed` against a runtime with **no kernel
configured**, so no container ever started. "Egress blocked" and "host unreachable"
both passed — by absence. That is principle 34, committed inside the spike written
to test the runtime, hours after the principle was written down in Appendix H.

The fix is the one §5.4 already specifies for gates, applied to the spike: a
liveness gate before any assertion, a probe that reports the *probe's* exit code
rather than the runtime's, and a third outcome — `error` — that refuses to print a
verdict at all. Which is the useful part of the story:

37. **Every harness that reports on something else needs the check it imposes.**
    The gate contract grew `tool` because a gate could report green without running;
    the spike grew a liveness gate for exactly the same reason, and did not inherit
    it automatically from having been written by someone who had just fixed it
    elsewhere. A rule about verification is not self-applying. Ask, of any reporting
    harness: *what does this print when it does nothing at all?*
