# Saffron — System Design

An agentic software factory: spec files in, reviewed pull requests out, running unattended overnight on one Mac.

**Status:** rev 18 — `SA-0001` built and answered: five queries, five SQL equivalents, don't build the emitter (`ontology/RATIONALE.md`). The vocabulary is gated by `shacl` and cross-checked against `CONTEXT.md`'s closed sets; the *operational* question the RATIONALE never tested is stated in Appendix O and left to a spike, and §1.4's bullet stands until that spike runs. Prior: rev 17 the first night's scheduler decided against the queue that exists rather than the deep one §4.2 is written for (§4.2.1), and §6's ranking corrected against the real ledger after it sorted a sustained blocker last (`docs/evidence/2026-08-25-morning-queue-from-real-rows.md`). Prior: rev 16 the tree a task is cut from and the executables that judge it are both host-supplied, closing the two trust boundaries backlog items 11 and 12 left open (Appendix N). Prior: rev 15 the cell moved off the API key onto a Claude Code subscription token, and the ceiling reasoning corrected against a measured run (`docs/evidence/2026-08-21-subscription-turn-accounting.md`, Appendix M); rev 14 the critic built and measured against a known-bad diff (Appendix L); rev 13 three tasks run, one reviewed, and the review said no (Appendix K); rev 12 v0.5 run against a live model (Appendix J); rev 11 v0.5 built and reviewed (Appendix I); rev 10 the cell runtime chosen by spike (Appendix G); rev 2 post adversarial review (Appendix A); rev 3 factory ontology (Appendix B); rev 4 repo-agnostic (Appendix C); rev 5 prior art (Appendix D); rev 6 vocabulary corrections (Appendix E); rev 7 read-through defects (Appendix F); rev 8 cell runtime named (Appendix G); rev 9 v0 built and replayed (Appendix H)

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
| N2 | Bounded spend | Per-attempt, per-task, and per-batch USD ceilings; hard stop, enforced host-side against reported spend (§4.1). Under a subscription those dollars are notional, so the ceiling that actually binds is the provider's rate limit: the runtime reports `RateLimitInfo` and a `rejected` window is the terminal state `RATE_LIMITED`, never `EXHAUSTED` — a provider limit and a task that could not pass its gates are different outcomes (§3.3, §5.1) |
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
- An ontology-*driven* orchestrator. The factory ontology (§4.6) **describes** the run record; it never controls execution. SHACL shapes validate the projection; they do not gate state transitions, and no scheduling decision reads a triple. (Stands for v1. Appendix O states the operational question this bullet forecloses, and the spike that would reopen it.)
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
     └─────────────────┘  └───────────────────────────┘    (and nothing else)
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
| `integrity` gate logic | **Core**, patterns from repo | "Was a suppression added, or gate config edited?" is universal; *what a suppression comment looks like* is not |
| `census` gate | **Core** | Subtracts two lists of names the repo's `tests` gate already reported — reads a gate result, invokes nothing |
| `criteria` gate | **Core** | Judges each declared witness against the same two reported lists — reads a gate result, invokes nothing |
| `revert` gate | **Core** logic, the repo's `tests` gate as runner | The sanctioned exception below: core re-invokes a declared gate, it does not run a tool |
| `format`, `lint`, `types`, `tests`, `no-network` | **Repo** | Executables satisfying the gate contract |
| Cell image, services (DB, cache, …), fixtures | **Repo** | `.saffron/Dockerfile` and a declared service list |
| Risk-elevation paths, protected paths, envelope defaults | **Repo** | `policy.yaml` |
| Standing agent instructions | **Repo** | `CLAUDE.md` |

Saffron ships thin base images (`saffron/cell-base:python`, `:node`, …) carrying the agent runtime, git, and nothing else. **There is no gate-runner shim** — that phrase survived four revisions describing a component that was never built and turned out not to be needed: the host `exec`s the repo's gate executables directly through the runtime, so there is nothing for a shim to do (Appendix I). A repo's `.saffron/Dockerfile` starts `FROM` one of those and installs whatever it needs. Saffron never installs a toolchain on a repo's behalf.

**The seam to watch.** Most core gates are core precisely because they read the diff rather than run the code. That is not a coincidence and it is worth protecting: every time a proposed core gate needs to *execute* something in the repo, it belongs on the repo side of the line. And before reaching for `revert`'s exception, ask the cheaper question first: *does a gate the repo already declares produce this data?* `census` needed collected test names and got them by adding a field to a result that was already being returned, which is not an exception to the boundary at all.

`committed` (§5.4) is the nearest thing to a counter-example so far: reading `git status` inside the cell widens core's in-cell git surface past the `git diff` it already ran. The boundary holds only because the gate itself stays a pure function over a list of paths — the host runs a git command it already knows how to run, and nothing in the check knows or asks what any of those paths contain.

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
forbidden:                      # denied at the plan checkpoint, not against the diff — below
  - alembic/versions/**
budget_usd: 12
max_attempts: 4
max_turns: 60                   # per-turn ceiling; the flags override all three
risk: standard                  # standard | elevated (§5.6)
---

**`forbidden` and `protected` bind the plan, not the diff, and the wording here said otherwise until `SA-0011` leaned on it.** Both are read in exactly two places: `agents/artifacts.py` rejects a plan whose *declared* `files_to_change` matches one, and `agents/context.py` prints them into the prompt. No gate reads either against a diff. The only diff-time path control is `scope` — changed files ⊆ `touches` (§5.4) — and it is what actually stops a task editing a denied path, because a denied path is normally outside `touches` anyway.

The gap that leaves is narrow and real: a `touches` broad enough to contain a `forbidden` path (`touches: ["saffron/**"]`, `forbidden: ["saffron/cell/**"]`) passes `scope`, and nothing else looks. A plan that declares the edit is caught; a plan that does not declare it is not. Stated rather than fixed, because narrowing it is a design change and `integrity`'s exemption paragraph (§5.4) reasons about the same shape: **a check that fires on a declaration is not a check that fires on a diff.**

**A spec cannot introduce the frontmatter it is written in.** `Spec` sets `extra="forbid"`, so a spec declaring a key its own task adds is refused at intake as malformed — the first spec to use a field can never be the one that builds it. The standing answer is a fixture in the same change, asserted by one acceptance criterion. Found by `SA-0011`, whose first draft declared the key it was proposing and would have been refused by the factory it was written for.

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

  PREFLIGHT_FAILED ◀── the baseline suite errored: the toolchain is broken, not
                       the code, and no model call has happened yet (§5.4)
  NOT_IMPLEMENTED  ◀── IMPLEMENT produced no commit. Measured, never reported —
                       a dead seam here would have returned an earned state
  GATE_ERROR       ◀── a gate errored, or the two suites drifted: infrastructure,
                       and never charged to the task (§5.4)
  EXHAUSTED        ◀── also from IMPLEMENTING: the host-side spend ceiling stops
                       a task before its next turn, and the budget stop and
                       "four attempts, still red" share the state (§4.3)
  RATE_LIMITED     ◀── any turn, on a `rejected` window: the provider's ceiling,
                       not the task's. Deliberately not EXHAUSTED — nothing was
                       learned about the spec, and the retry is free (N2, §5.1)
```

Terminal states that reach you: `SCOPE_REVIEW`, `PLAN_REJECTED`, `EXHAUSTED`, `READY_FOR_REVIEW`, `MERGE_FAILED`, `PREFLIGHT_FAILED`, `NOT_IMPLEMENTED`, `GATE_ERROR`, `RATE_LIMITED`. Everything else is internal. The last three are named rather than folded into a neighbour because the alternative is an abort, or an attempt that produced nothing, reading as an ordinary task outcome — principle 34 wearing a state name.

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

`repos.origin` is the **real remote** — the URL a PR is opened against.
`repos.mirror_path` is the local bare mirror, which is the only remote a cell
ever reads (§5.1). v0 and v0.5 stored the mirror's *source* in both, so nothing
downstream knew where the real remote was; PACKAGE is the first component that
needs the distinction and the first that enforces it.

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
3. **Budget gate** — uncommitted batch budget ≥ task budget, where *uncommitted* is `budget_usd − spent_usd_est − Σ(budget of in-flight tasks)`. The task's budget is **reserved when it is scheduled and the unspent remainder released when it reaches a terminal state**, which is the difference between a hard stop and a soft one: comparing against `spent_usd_est` alone lets K tasks each pass the gate on the same last $12 and overshoot by up to K× a task budget, because spend is recognized as it happens and the gate is evaluated before any of it has.
4. **Order** — priority, then dependency depth (unblock the most work), then **round-robin across repos**, then FIFO.

Round-robin matters more than it looks. Straight priority ordering lets one repo with a deep queue monopolize a night, and you wake up to twelve PRs in one codebase and none in the other two — which is worse for review than four each, because your context-switching cost is paid once per repo either way. Interleaving also spreads the risk of a bad night: a repo whose gates are misconfigured burns a third of the budget, not all of it.

**Most of this is v2, and the queue depth is why.** §7.1 sizes a night at 10–15 completed tasks; N4 wants 6–12 accepted PRs a *week*; §9 concedes that spec-writing binds before throughput does. The realistic steady state is therefore a two- or three-deep queue against three cells — and at that depth priority-then-FIFO *is* the scheduler, while conflict sets, round-robin and dependency depth arbitrate contention that never arrives. So v1 builds gate 0, the budget gate, and ordering by priority. The rest is written down here because it is the right answer once the queue is deep, and each piece gets built the first night it actually binds: round-robin when one repo demonstrably monopolizes a night, conflict sets when two tasks first collide, stacking when a DAG first stalls. This is §9's rule about second implementations applied to a scheduler rather than to a language seam — the same rule catches both, and it caught the language seam only because someone wrote it down.

**Dependencies do not cross repos.** A cross-repo `depends_on` would require coordinated merges across two review queues, and there is no version of that which is simple. If two repos must change together, that is one spec in each and a note in both — you sequence them by running one batch, merging, then the next. Stated as a limit rather than discovered as a bug.

Concurrency cap **K = 3**, and rev 10 settles what the arithmetic closes against. With a VM per cell there is no shared allocation to divide: three cells at `--memory 4g` draw 12GB against the whole Mac rather than against a fixed VM allocation, and nothing stands between batches. CPUs divide the same way — `--cpus 1` yields 2 vCPUs per cell (the calibration in §5.1), so K=3 is 6 vCPUs against a host of 11. A repo's fixture services run *inside* the cell, so 4g is the whole budget for a database, the toolchain and the test process together. This is the first number here likely to be wrong; K is the knob, and it turns down. Do not raise K: throughput is model-latency-bound most of the time, but gate suites are not, and oversubscribing makes gate timings flaky — which poisons the repair loop's only signal. **Rev 8 removed the second ceiling this paragraph used to close against.** It was the performance-core count, and no macOS runtime can pin a cell to one (Appendix G), so K is now bounded by memory and by measured gate-time variance rather than by a core enumeration that cannot be performed.

### 4.2.1 The first night's scheduler

Everything above is the scheduler once the queue is deep. This is what v1 builds, decided against the queue that actually exists: two or three specs, ~45–60 min a task, an eight-hour window (§7.1). **Every piece cut below arbitrates contention, and at this depth there is none to arbitrate** — §4.2's own rule about second implementations, turned on the scheduler itself rather than on one of its gates. Each cut names the night it comes back.

**Input — the specs at `base_sha`, filtered by what the ledger already knows.** A batch scans `.saffron/specs/*.md` from the export `export_saffron_dir` already takes at the run's pinned `base_sha`; `specs/` arrives free because that export was deliberately made the whole directory rather than `gates/` alone (§5.4). Not the working copy, and this is a new member of the family item 13 assembled — gates at `base_sha`, the policy declaring them at `base_sha`, PACKAGE's policy at `fetch_head`, the cell image from the working copy (§5.1). A spec joins the first group, and the friction is the point: **a spec on a branch is a draft, and the factory owing you work on an unlanded draft is the wrong default when nobody is awake.** It also closes the loop where a task could rewrite the queue that schedules it.

**The scan resolves to a task, not to a spec, and that is load-bearing rather than pedantic.** A spec with a task at this `spec_sha` in a re-queueing state **resumes that task row**; a spec with no such task gets a new one. Minting a fresh task per queued spec looks equivalent and is not: gate 0 refuses a task when an open unmerged PR *from another task* already targets the spec, and §4.2's footnote is explicit that this survives a `CHANGES_REQUESTED` re-queue only because **refusal is keyed on `task_id`, not on the spec**. A new task row at the same `spec_sha` is "another task" by its own id, so a spec-keyed scan admits the re-queue and gate 0 refuses it on the PR it was sent back to fix. The same root would discard a ratified `SCOPE_REVIEW` `touches`, which lives on the task, and send the bug back through DIAGNOSE.

**The filter is stated negatively and keyed on `spec_sha`.** A spec is queued unless it has a task **at this `spec_sha`** in a state that is *done with it*: `READY_FOR_REVIEW`, `APPROVED`, `MERGE_TRAIN`, `MERGED`, `MERGE_FAILED`, `REJECTED`, `EXHAUSTED`, `NOT_IMPLEMENTED`, `PLAN_REJECTED`, `SCOPE_REVIEW`. It re-queues on `CHANGES_REQUESTED`, `RATE_LIMITED`, `GATE_ERROR`, `PREFLIGHT_FAILED` and `ORPHANED`. The rule underneath is one line — **re-queue when nothing was learned about the spec** — and it is what makes the list derivable rather than memorized. The positive form, "has a task at this `spec_sha`", is the one to reject: §3.3 sends `CHANGES_REQUESTED` back to the queue against an unchanged spec, so it refuses the one case the re-queue arrow exists for. **Dropping the key instead of the form is the other wrong fix**, and it costs the edit case: unscoped, a `REJECTED` spec you then rewrite is never queued again. `EXHAUSTED` stays out for the reason from the third side — something *was* learned, and running it again learns it twice. `MERGE_FAILED` likewise: it reaches you (§3.3) with a branch and an open PR, and a fresh task tonight would duplicate work and trip gate 0.

> **The in-flight states are not on either list, and the scan must not treat that as "queue it".** `DRAFT`, `QUEUED`, `DIAGNOSING`, `IMPLEMENTING`, `GATING`, `REPAIRING`, `REVIEWING` and `REBUTTING` at scan time mean a corpse: one batch runs at a time, so nothing is legitimately in flight when a scan happens. `ORPHANED` covers only the deaths the supervisor stamped (§4.5) — a host power cut leaves the task in `IMPLEMENTING`. **The scan stamps any in-flight task `ORPHANED` before filtering**, which is §4.3's reconcile step doing the job it is already named for, and the task then re-queues by the ordinary rule.

**`depends_on` is refused, at gate 0 rather than at intake.** `Spec` parses it, nothing schedules it, and `SA-0007` declared it and was sequenced by hand — an instance of the pattern item 18 named, where a field that parses and validates and changes nothing is indistinguishable from one that works. The tempting middle path is to honour it as ordering only, topologically sorting inside the batch without stacking branches. **That is not a smaller version of the feature; it is a version that lies.** Without stacking the child branches off `base_sha`, so the parent's changes are not in its tree, and it builds against code that does not exist yet and fails its own gates. But the refusal belongs in the refusal gate, not in `parse_spec`: `SA-0006` and `SA-0007` both carry the field today, so raising at parse regresses `saffron cell` on two specs in this repo, and an exception mid-scan has no defined handling while a refusal has one — a reason, and one line in the morning queue (§6). Stacking arrives in v2 (§9); until then hand-sequencing stays the documented workaround.

> Item 18 counts five instances and declines to number a sixth. This is the sixth, and #27 called it the fifth — the miscount is worth correcting precisely because the pattern's value is in the count.

**The refusal gate refuses six things, and the fifth is the only one with a corpse behind it.** §4.2's four stand as written, `depends_on` is the sixth, and the fifth is: **a spec whose acceptance criteria name a path that no `touches` pattern matches.** Item 18 measured that such a spec is unsatisfiable by construction — `SA-0005` burned $5.34 and died at turn 61 because its criteria reached `cli.py` and `package.py` while its `touches` did not, so the implementer could not have satisfied them without failing `scope`, and one finding was dropped as unanchorable for the same reason. The adjudication was that **the fault was the spec's, not the implementer's**, and nothing in intake checked for it.

Two things that condition has to get right, and the obvious statement of it gets both wrong:

- **It matches globs, not strings.** `touches` is glob-matched everywhere it is enforced — `scope.matches`, and `integrity` and `size` both reuse that function so that "declared" means one thing in every gate. A criterion naming `saffron/gates/core/size.py` against `touches: ["saffron/gates/core/**"]` string-compares to no match, and a false refusal at gate 0 costs a whole spec overnight with no cell started and nothing to notice until morning.
- **It is skipped when `touches` is empty.** That is the documented shape for a bug awaiting DIAGNOSE (§5.2), and every criterion names a path outside an empty list — so the unguarded form refuses the entire bug class before the phase that would populate `touches` can run. §4.2 already carves bugs out of gate 0's overlap test for exactly this reason, and like gates 0 and 2, this one **re-runs at ratification** against the ratified set.

**Preflight is what a task already does, hoisted, plus two.** `_run_cell` today does the mirror fetch, the origin refusal and the default-branch pin per task; a batch does them once per run. Added: `load_policy` validation, and an auth check. **The auth check is not hygiene — it guards a measured landmine.** Appendix J found that a cell whose agent cannot authenticate returns `subtype: "success"`, `is_error: true`, `total_cost_usd: 0.0`; unattended, an expired token at 22:00 produces a night of clean-looking nothing against a budget that never counts down. Deferred: `saffron gc` (§4.5), because K=1 means `--until` kills at most one cell and the leak is one volume a night rather than three. **The disk-headroom check is not deferred with it, and the pairing is the whole point.** §4.5's endgame is *"two weeks and the disk is full — and preflight would detect it and abort, which is detection without reclamation."* K divides the leak rate; with gc deferred the accumulation is still unbounded, so dropping the detection as well turns a warned failure into a silent one.

**K = 1, and the scheduler is a `for` loop over a sorted list.** §4.2's arithmetic sets K=3 against memory, and that arithmetic is not wrong — it is just answering a question a three-deep queue does not ask. Three tasks at 45–60 minutes is three hours of an eight-hour night, so concurrency buys idle time rather than throughput. What it costs is the whole of gate 3's reserved-budget machinery, which exists **only** to stop K tasks passing the budget gate on the same last $12; at K=1 that race cannot occur and the gate is one comparison before each task. Ordering is priority then FIFO, sorted once in memory.

> K becomes real the first night the *wall clock* ends the batch rather than the queue. That night is also the first evidence about which of §7.1's three disagreeing numbers was right, so it is worth waiting for rather than guessing past.

**A batch ends four ways, and says which.** The queue drains, the budget is gone, `--until` hits, or the breaker fires. No task-count ceiling: it is a proxy for spend, and spend is measured directly.

**The breaker counts two consecutive aborts, and what counts as an abort is enumerated rather than implied.** A task exiting `2` is infrastructure, charged to nobody (§5.4), so it is recorded and stepped over — but two in a row stops the batch, because two in a row is a broken host and the remaining tasks will each burn a preflight and a baseline suite to learn the same thing. The states that count: `GATE_ERROR`, `PREFLIGHT_FAILED`, and **`RATE_LIMITED`**. The last is not exit `2` and is not infrastructure, but it fails the same way — a provider ceiling hit at 22:05 lets every remaining task start a cell and run a baseline suite (minutes, §7.1) before dying of the same global condition. N2 says the retry is free, so the queue re-queues intact tomorrow (§5.1). **The counter resets on any state a task *earned*** — anything else in §3.3, up to and including `EXHAUSTED`. Saying "any terminal state" would be a bug rather than a shorthand: §3.3 lists `GATE_ERROR` and `PREFLIGHT_FAILED` among the terminal states that reach you, so the counter would reset on the very aborts it counts and never reach two.

**Schema: `batches` gets built, `tasks.priority` does not.** §4.1 declares both and neither exists. They are not the same call. The batch's window and its stop reason have to survive for §6's morning queue to render the night, so `batches` lands as `(batch_id, started_at, ended_at, budget_usd, spent_usd_est, until_ts, status)` with `runs.batch_id` beside it; `status` carries `DRAINED`, `BUDGET`, `UNTIL` or `INFRASTRUCTURE`, one per stop condition above. `concurrency` waits for K to have a second position. Priority is different: it is read exactly once, at scan, to sort a list already in memory. **A column written at scan and read by nobody would be item 18's pattern wearing a schema instead of a dataclass** — the repo has produced six of those and one of them cost a task. It gets added the first night something reads it back.

**The command, and what is missing from it deliberately:**

```
saffron batch --repo . --budget 50 --until 06:30
```

No `--repos`, because multi-repo is v2 (§9). No `--concurrency`, because **a flag for a knob with one position is the same defect in a CLI that item 18 found in a spec.** `--repo` defaults to the working directory, matching `saffron cell`. `--until` takes `HH:MM` and resolves to the next occurrence. `--budget` defaults to 50, which is §7.1's own recommendation and is sized against the queue rather than against capacity.

**Exit codes, and why `1` is reserved rather than reused.** A batch is not a task, so `cell`'s codes do not carry over: `0` for `DRAINED`, `BUDGET` and `UNTIL`, `2` for `INFRASTRUCTURE` and for a preflight failure that takes the whole batch. Never `1`. **A batch that drains with three failed tasks did its job** — individual outcomes are the morning queue's business, and letting `1` mean anything here would quietly merge two vocabularies that answer different questions.

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

**2. PROV-O and EARL, not a bespoke schema.** Batches, runs, tasks, attempts, phases and gate suites are `prov:Activity` — one activity per suite and not one per gate, because a gate's own execution is already fully described by the assertion it produces: `gate_results` carries its status and its `duration_ms`, and a separate activity node would restate them; specs, `plan.json`, `scope.json`, diffs, gate output and PRs are `prov:Entity`; the implementer session, each critic lens and the human are `prov:Agent`. `wasGeneratedBy`, `used`, `wasDerivedFrom`, `wasRevisionOf` and `wasInvalidatedBy` (which is exactly what `spec_sha` invalidation is, §4.1) carry the backbone. Gate results and critic findings are both `earl:Assertion`s over an `earl:TestSubject`. The genuinely Saffron-specific terms — the only part that justifies a new namespace — are the gate taxonomy with its blocking/advisory split, `envelope` versus ratified `touches`, lens disjointness, and the terminal-versus-internal state distinction of §3.3.

**2b. The cheap rival the RATIONALE must also beat: a glossary.** Prior art (Appendix D) reaches the same need — a shared vocabulary its agents must read before touching code — and answers it with a 200-line markdown glossary where every term carries an explicit ***Avoid:*** list of the words not to use for it, plus an instruction to *flag* a conflict with a recorded decision rather than silently override it. That is a weekend's less work than an ontology and it does the thing an ontology is usually reached for. So `RATIONALE.md` has a second bar to clear: not only "is SPARQL better than SQL here," but "**is any of this better than a disambiguating glossary the agents actually read?**" If the honest answer is that the vocabulary's value is agent-facing rather than query-facing, write `GLOSSARY.md` and stop — the queries were the justification, and without them the RDF is decoration. Worth noting that Saffron needs the glossary either way; the ontology has to earn the *delta*.

**3. Provisional by construction.** The deliverable includes `ontology/RATIONALE.md`, which challenges each of five queries against its SQL equivalent over the §4.1 schema. **"All five have easy SQL equivalents — don't build the emitter" is a successful outcome**, and is the cheapest form that answer can take. The vocabulary is a design artifact validated against hand-authored fixtures; the emitter and the store are a separate, conditional task (§9, v2.5).

Rule 3 is the important one, and it is §9's build-order discipline applied to a data model: prove the layer is worth having before building the machinery that feeds it. A vocabulary costs a weekend and can be deleted. An always-on materialization pipeline cannot.

#### What the modelling already surfaced

Two schema criticisms that stand whether or not a single triple is ever stored:

- **`gate_results` and `findings` are the same thing wearing different table names.** A type error and a critic blocker against an acceptance criterion are both *an assertion, by an agent, about a subject, with an outcome*. EARL says that in one shape. The SQL schema splits them because gates are deterministic and critics are not — which is a fact about how the assertion was *produced*, not about what it *is*. The PR body already renders them into one table, which is the tell. Worth reconciling in §4.1.
- **A rebuttal is not a string.** §5.6 records implementer/critic disagreement across `verdict`, `adjudication` and `rebuttal`. Modelled as a `prov:qualifiedAssociation` the disagreement becomes a node carrying role, plan and time — which is what makes "blockers per lens, split by whether the operator agreed" answerable at all. *(The typed `adjudication` field this originally argued for landed in rev 6; the qualified-association question remains open.)*

That is the ontology earning its keep before it ships: writing down what an *attempt* is in relation to a *gate result* produced two design corrections, not two triples.

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
  -e CLAUDE_CODE_OAUTH_TOKEN \
  -e CLAUDE_CONFIG_DIR=/agent-state \
  $(policy.thread_env) \                          # repo-declared, see below
  --cpus 1 --memory 4g \                          # 1 requested, 2 delivered — see below
  --cap-drop ALL \
  --mount type=volume,source=saffron-wt-TE0142,target=/work \
  --mount type=volume,source=saffron-st-TE0142,target=/agent-state \
  --mount type=bind,source=<task-dir>/gates,target=/gates,readonly \   # gates at base_sha
  saffron/cell:thermal-edge                       # built from the checkout — see below
```

**Every flag in the per-task block is a requirement, and the wiring is the control.** v0.5 shipped a cell created without `--network` and without the proxy environment: the isolated network was created, the host-binding probe ran against it, the proxy started on it and printed its address, and none of it was passed to the container holding the agent. Every mechanism ran, every mechanism reported success, and all of it applied to a different container. So `network` and `env` are **required** arguments where a cell is created — omission is an error, not a default — and the test that proves isolation must start a cell *the way production starts one* and probe **from inside that container**, not from an ephemeral sibling (Appendix I). **That rule is about a *container's* egress.** A preflight probe establishing a property of the *network* — N1's host-binding probe — necessarily runs in an ephemeral sibling on that same network, because it gates whether a cell is started at all and so cannot run inside one that does not exist yet.

**Two of the arguments above are read before the cell exists, and neither comes from the invoking checkout.**

- **`base_sha` is the head of the remote's default branch,** fetched into the mirror at task start (§5.7). `ensure_mirror` clones from the *local working copy*, so the remote's head is not an object the mirror holds until that fetch lands — which is why the fetch is part of cell construction rather than the PACKAGE-time step it used to be. The rule that the mirror is the only remote anything downstream reads is unchanged: the mirror is where the fetch lands.
- **`/gates` is `.saffron/` as it stood at `base_sha`,** exported out of the mirror onto the host and mounted **read-only**. The runner execs the gates from there and never from `/work`, so an in-cell edit to a gate — committed or not — cannot reach the thing that judges the task (§5.4). The whole directory rather than `gates/` alone, because the `policy.yaml` *declaring* those gates is read back out of the same export (§5.4). It is the one bind mount in the block, and the bullet below arguing against bind mounts does not reach it: a handful of small files read once per gate is not pytest collection.

**The cell image is built from the invoking checkout, and it is the one input that is.** The tree, the gates and the policy all come from `base_sha`; the image comes from where the operator is standing — `.saffron/Dockerfile` read out of the working copy, with that working copy as the build context. Deliberate, because the image is the *toolchain* and not the judgment: what a gate measures is the base tree's code either way. Named rather than left implicit, because the drift is real and this repo's own Dockerfile shows the shape of it — `COPY pyproject.toml uv.lock /seed/` bakes the checkout's dependency lock into an image that then runs `base_sha`'s code. **The scheduler reopens this.** Unattended (§4.2) there is no checkout for the phrase to mean anything, and the honest answer there is a build context exported from `base_sha` like everything else.

**The consequence, stated because it changes who can run.** A repo with no reachable `origin` can no longer start a cell. Previously the supervisor caught that and ran anyway, on the reasoning that such a repo simply could not be *packaged* — which spent a whole attempt before saying so. Network at task start was already required (`ensure_mirror`, the proxy), so this moves *when* an unreachable remote fails, not whether, and failing before the cell starts is the better end. The same call site reads `github_slug` for its refusal, so the narrowing is wider than "unreachable": a repo whose `origin` is not a GitHub remote cannot start a cell either, attended or not. That is the same trade one step further — the slug reaches `gh` at the end of PACKAGE, and discovering there that no pull request can be opened spends the whole budget to learn something knowable at task start. The checkout's `policy.yaml` is read at neither call site, nor anywhere else on this path: the cell's policy comes from `base_sha` and PACKAGE's from the default-branch head it verifies against (§5.4, §5.7). Editing it changes the next task rather than this one, the same way editing a gate does.

**Two measured prerequisites, neither obvious and both expensive to rediscover.** `container build` does not work on macOS without Rosetta installed (`softwareupdate --install-rosetta`). And `container volume create` pre-formats a volume with a `lost+found` directory, so `git clone` refuses the destination as non-empty — a worktree is seeded with `git init` + `remote add` + `fetch` + `checkout` + `remote remove`, chained under `sh -euc` so the remote removal cannot be skipped on a successful seed.

**The runtime is `apple/container`,** decided in rev 10 against the four-assertion spike rather than left to taste (Appendix G). `no-new-privileges` and seccomp have no equivalent and are deliberately not replaced: the per-cell VM is the boundary offered instead, and §2's whole claim is that the structural controls are the ones that hold. Every remaining flag is load-bearing:

- **No target-repo credentials — for any repo, ever, and exactly one credential of any kind.** No host `.env`, no cloud profile, no database URL, no third-party API key. Tests run against recorded fixtures. A task that genuinely needs live data is a task you run attended. This is a rule core enforces rather than one each repo is trusted to follow: the cell simply never receives them.
  **The exception is `CLAUDE_CODE_OAUTH_TOKEN`, and it is stated here because an unstated exception is an abandoned rule (Appendix F, principle 29).** The agent cannot run without a credential, so the cell holds exactly one, and its blast radius is the subscription's rate limit rather than data — which is why it is tolerable and why §2's boundary claim is written in terms of *target-repo* credentials. Rev 15 struck the API key in its favour. The token comes from `claude setup-token`, which is minted for exactly this and is revocable on its own, so the "separate credential for the factory" mitigation is kept rather than lost: revoking it does not touch interactive work. **Two things measured on the first subscription run change what this section may claim** (`docs/evidence/2026-08-21-subscription-turn-accounting.md`). The runtime still reports `total_cost_usd` — $3.88 across 65 turns for `SA-0004` — so N2's host-side sum continues to hold against a real quantity and the in-cell `max_budget_usd` still fires. But those dollars are **notional**: an API-rate valuation of tokens nobody is billed for, so no provider-side cap stands behind them and this section can no longer reach for one, as earlier revisions did. What does stand behind them is the rate limit, which the runtime reports as `RateLimitInfo` on the same stream — the first ceiling in this design the cell is *subject to* rather than merely *reporting*, and the one this section has wanted since rev 1. What is genuinely given up is isolation of *contention*: a runaway cell burns the same rate-limit pool the operator is working in, so the failure mode moves from an unexpected bill to a tool that stops responding. That is a worse day and a cheaper one. A host `ANTHROPIC_API_KEY` is deliberately **not** forwarded even when present, and a test asserts it, because that is the regression that would restore the old design in silence. Moving custody into the proxy remains the principled fix and remains unavailable: `CONNECT` tunnels are opaque, so the proxy cannot inject a header it cannot see.
- **The proxy is dual-homed, and it drops privilege by starting without it.** An `--internal` network has **no route out at all**, not merely no DNS — so the proxy sits on both the internal network and an egress network, egress-first, because the runtime's default route follows the first `--network`. And squid cannot start under `--cap-drop ALL` as root, because dropping privilege needs `SETUID`/`SETGID`; rather than granting a capability, the proxy runs as `--user squid:squid` from launch so squid never calls `setuid()`. **No capability is granted to anything.** Both facts were measured, not reasoned (Appendix I).
- **Egress via an allowlisting proxy, not iptables.** Two reasons the obvious version doesn't work: `--cap-drop ALL` removes `CAP_NET_ADMIN`, so a cell entrypoint cannot install firewall rules (and granting it that capability would let the untrusted cell rewrite its own firewall); and `api.anthropic.com` is behind a CDN, so an IP allowlist resolved at startup starts failing mid-batch. A sibling proxy on both the internal and external networks doing hostname-based `CONNECT` filtering solves both — hostnames not IPs, zero capabilities in the cell.
- **`CLAUDE_CONFIG_DIR` on a separate volume, never under `/work`.** Session state and any OAuth credential file must not live in the tree the agent has write access to, that the `scope` gate walks, that the secret scanner scans, and that gets patch-exported. Putting them together means the agent can read its own credentials and the secret scan trips on a real token.
- **A cell must see only the CPUs it has — not a quota, plus explicit thread caps.** Docker's `--cpus` is a CFS quota, not a core mask: Polars, pyarrow, and numpy's BLAS all size their thread pools from the *visible* core count and will each spawn ~10 threads inside a 2-CPU quota. The result is heavy throttling and wildly variable test timings — the exact flaky-gate failure mode §7 warns about, self-inflicted.
  **What survives, and what rev 8 struck out.** The requirement above is durable and it is not really about `cpuset`: **a cell must see only the CPUs it actually has.** The chosen runtime satisfies it structurally — the cell's VM is configured with that many vCPUs, so `nproc` is honest with no affinity flag at all. Write the requirement, not the flag.
  **Calibrated, because the physical world needs a knob a minimal model does not see.** `apple/container` 1.2.2 allocates **one vCPU more than `--cpus` requests** — deterministically, measured at 1→2, 2→3, 4→5, 6→7 (Appendix G). That is not the failure this bullet is about: the guest count is honest about the VM it is in, which is the property thread pools need, and the VM simply gets one more vCPU than asked for. So the supervisor requests `n − 1` and asserts the result, rather than trusting either number. **An offset that is measured, deterministic and asserted is a constant; the same offset assumed is a bug that surfaces as flaky gate timings.** Re-measure it on any runtime upgrade — the spike is the thing that measures it.
  ~~**Pin performance cores only.** Enumerate the P-cores once at preflight and let K fall out of how many there are.~~ **Struck in rev 8: this is not implementable on macOS under any runtime.** `--cpuset-cpus` is interpreted by the kernel that reads it, and on macOS that kernel is always inside a VM — so the mask indexes *virtual* CPUs, and which physical core a vCPU thread lands on is macOS's decision, not one any flag exposes. A VM-per-cell runtime has no pinning flag to offer in the first place. The underlying hazard is real and unchanged — vCPU threads prefer P-cores but spill to E-cores under contention, so a cell can run its gates slower than its siblings and the difference reads as task difficulty. It is now a thing to **detect rather than prevent**: record per-gate wall clock and treat cross-cell variance at equal K as a signal about the machine, not about the task (§7).
  The runtime caps the CPUs; the repo declares *which* env vars cap its toolchain's thread pools (`policy.thread_env`), because core has no business knowing that Rayon reads `RAYON_NUM_THREADS` and the JVM doesn't.
- **Worktree on a named volume, not a bind mount.** macOS bind mounts are slow for the many-small-files pattern of pytest collection and mypy. Clone from a bare mirror into a named volume, work there, export a patch. Costs easy host-side inspection mid-run; buys gate suites 3–10× faster, compounding across a 4-attempt repair loop. Dependency directories (`.venv`, `node_modules`, `target/`) live in the volume too — never on a mount, in any language.
- **Services and fixtures are baked into the repo's image layer, not orchestrated by core.** A repo that needs a database says so in its own `.saffron/Dockerfile`: install it, run the migrations, seed it, all at *image build* time. Every cell then starts from the layer — near-instant, no per-task restore, no "template database" subsystem in Saffron, and a real service so that migration and schema gates mean something. A repo needing nothing gets a smaller image and starts faster. Core's only involvement is rebuilding the image when `.saffron/Dockerfile` changes.
  > Rejected alternative: a `services:` block in `policy.yaml` that core turns into a Compose file. It reads cleaner and it drags service lifecycle, health checks, and startup ordering into the orchestrator — which is exactly the kind of knowledge §2.1 exists to keep out. A Dockerfile is already the standard way to say this, and the repo owner already knows how to write one.
- **The image runs the toolchain offline, because the proxy allows one host.** A package manager that re-resolves the project on every invocation — `uv run`, `npm exec`, `bundle exec` — reaches the network at every turn the agent uses it and at every gate, and takes a 403 from the proxy. Measured on `SA-0002`: `uv run pytest` was refused four times and the agent spent three implement turns arriving at `python3 -m pytest`, which is a working task paying for a toolchain defect. So a repo's `.saffron/Dockerfile` bakes the environment **and** pins the runner to it rather than only installing it — this repo sets `UV_NO_SYNC=1` beside `UV_PROJECT_ENVIRONMENT=/opt/venv`. The failure is quiet in the wrong direction: the agent works around it and the run still goes green, so it shows up as cost rather than as an error.

- **Git remote is a local bare mirror.** The cell physically cannot reach your GitHub remote. The host pushes, after gates pass.

### 5.1.1 The proxy's route out is asserted, never assumed

**The proxy starting is not the proxy working.** A first install ran a whole
attempt against a proxy that had come up, taken an address, and had no route
out: `container` 1.3.0 leaves a dual-homed container's egress leg dead if
anything joined the internal network before it, and the symptom reaches the
operator as ten `api_retry` events and then an API error
(`docs/evidence/2026-08-28-attach-order-takes-the-proxys-route.md`).

Every layer reported success and none of them was the path. The network was
created, the proxy was started, its address was printed, the image was built,
the cell came up and its whole baseline suite passed. The first thing to use the
network for what it is for was the agent, and by then the run was being paid
for — the attempt ended `NOT_IMPLEMENTED`, having established nothing about the
task.

So the supervisor asserts the **path** rather than the parts: from an ephemeral
sibling on the cells network, through the proxy, to the one host the allowlist
names — the agent's own first request, made before the agent exists. Any HTTP
status is a pass, **401 included**: what is being established is reachability,
and no credential is being tested. It runs immediately after the proxy starts and
before the repo's image is built, so the cost of the answer is one container
start rather than an image build and an attempt. The status it got goes on the
operator's line — what answered, not merely that something did.

A failure here is `error`, never `fail` — the repo's code is not what is wrong.
It raises before a cell exists, aborts the run, and is charged to nobody (§4.3).

**This deliberately does not check the runtime's version, or the attach order
that caused this one.** That ordering fix is a workaround for a defect in
`container` 1.3.0 and will age with it; a proxy that cannot reach the upstream
is wrong on every runtime, for every cause, including the ones this design has
not met yet. It is §7's "money spent to learn something free" one layer down.

### 5.2 Phase 1 — DIAGNOSE (bugs only)

Read-only tools, scoped to `envelope`. Output is `scope.json`: the proposed `touches` set, the identified root cause, and the evidence for it.

This phase exists because of a specific trap. The obvious design — human declares `touches`, agent is confined to it — is sound for features and fatal for bugs. In the TE-0142 example, "no rows from any of three providers" most plausibly originates *outside* `ingest/nws/**`: a shared HTTP retry helper, a Polars schema change producing a silently empty frame, a continuous-aggregate refresh policy, a chunk-interval/retention interaction, a migration that changed a constraint. Several of those are in `forbidden` or outside a hand-written `touches`. The agent would correctly find the cause and then be auto-rejected for looking in the right place — and the rejection would read as "your spec needs work," which is both wrong and unactionable.

So: the agent proposes scope, you ratify. `SCOPE_REVIEW` items appear at the top of the morning queue as a diff of proposed `touches` plus the one-paragraph root cause — a genuine 10-second decision, versus a rewrite-the-spec-and-lose-a-night loop. Ratified scope is recorded in the ledger, and written into the spec file **on the task's own branch, as its first commit** — so it reaches `main` through the task's normal PR and needs no exception to N1's rule that nothing unattended writes to a remote `main`. **The task's own spec path is added to the ratified `touches` when it is recorded**, or that first commit fails the `scope` gate on every bug task: the writeback changes `.saffron/specs/…`, which is not a path DIAGNOSE would ever propose. A control artifact that has to be committed has to be in scope to be committed. Two further things fall out, both load-bearing. The ledger is authoritative until that PR merges, so enforcement starts at turn one of IMPLEMENT rather than next batch. And `spec_sha` on `main` deliberately does *not* move while the task is in flight — writing the spec back to `main` directly would invalidate (§4.1) the very task that ratification just unblocked.

Cost: ~$0.30–1.00. Cheapest possible place to catch a misconceived task.

### 5.3 Phase 2 — IMPLEMENT (with a plan checkpoint)

Full write tools inside `/work`, with an explicit list of the tools that **exist**, an explicit list of those callable without a prompt, and a permission mode that **cannot prompt**.

**Those first two are different options and only one of them withholds anything.** `allowed_tools` governs auto-approval, not availability: measured live, a session that named six tools there was offered all twenty-one built-ins the runtime had — `Task`, `WebFetch`, `WebSearch`, `SendMessage`, `Workflow`, `Cron*`, `ScheduleWakeup`. `dontAsk` denied the ones outside the list, so the boundary held, but the model spent context seeing them and turns attempting them, which is the entire saving the list was written to produce. `tools` is the option that decides what exists, and it is a positive allowlist: a name the runtime does not recognise is dropped rather than granted, so the list can only fail closed. Restated generally, because it is the same shape as the hooks warning below: **a control that denies an action and a control that removes it are not interchangeable, and only the second one saves the turn.**

That second requirement is easy to miss and fatal to get wrong. The obvious mode auto-accepts file *edits* — which covers Edit and Write and nothing else. A shell command outside `allowed_tools` still raises a permission prompt, and at 03:00 inside a container there is nobody to answer it: the attempt burns its idle timeout (§4.3) and reads as a stall. **Unattended operation requires a mode whose behaviour on an unapproved tool is to deny, not to ask.** The runtime offers one; it also offers a mode that skips permission checks entirely, which is the wrong fix — it removes the wasted-turn savings along with the prompt, and buys nothing safety-wise since the real controls are structural anyway (§2).

The general form, because it will recur with every runtime option: **in an unattended system, "ask the operator" is not a fallback, it is a hang.** Any option whose failure mode is a prompt needs its non-interactive equivalent chosen deliberately.

**Configuration is loaded from nowhere.** `setting_sources` is pinned to `[]`. Its default loads project settings from the working directory, and the working directory is `/work` — the target repo's checkout, a tree the task itself can edit. Measured with a planted `.claude/`: an agent definition and a skill in `/work` both reached the agent Saffron was running *on that repo*, which for self-hosting means Saffron's own `.claude/` configures its own factory. Every instruction the agent gets is composed host-side and injected (§5.3); nothing is read from the tree under work. The cost of the pin is that the repo's `CLAUDE.md` no longer loads either — that is the right trade and the right fix is the same one `CONTEXT.md` already uses: inject it host-side, read from the mirror at the base commit, never from the tree the agent can rewrite.

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

**`collected` is optional, and only `census` and `criteria` read it.** A gate may report the identifiers it enumerated — for a test runner, its node ids. Core treats them as opaque strings: it never splits one, never assumes a separator, never infers a path from one. Absence is not a failure; it means the runner does not enumerate, and both gates report `skip`. Unlike `tool`, this field is not a trust signal — it is data core gates compare, and it is transient: `gate_results` has no column for it, so the comparison happens in memory within a run.

Two rules about `error` that the same replay forced, both stated because a gate author has to know them and neither is derivable from the schema:

- **A non-zero exit with an empty `failures[]` is `error`, never `pass`.** It means the tool objected to something the gate's parser did not recognize — a reworded output line after a version bump is the ordinary cause, and it produces the identical false green as a missing binary, from a different direction. The gate knows its own exit code; nothing downstream does.
- **Partial results are not results.** When a gate's execution mechanism breaks part-way — a lost test worker, a collection crash, a timeout on one shard — the gate returns `error` for the whole run rather than `fail` on whatever it managed to collect. There is deliberately no per-failure `error` vocabulary: a test suite that lost a worker did not produce a trustworthy result, and the cost of that rule is one re-run charged to nobody, against the cost of an agent spending attempts "fixing" a test that a scheduler killed.

Requiring gates to translate their own tool output is the price of admission, and it is the right price: it is ~20 lines of shell per gate, written once by the person who understands that tool, and it keeps every parser out of the orchestrator.

#### Where the gates come from, and what they measure

**One invariant, which both halves of the gate boundary serve:**

> **Anything that changes what the suite measures must appear in the patch a human reads.**

Not *the cell cannot lie*. It can, and a design that assumes otherwise is how v0.5 shipped a cell where every control reported green and none was connected (Appendix I). The achievable property is weaker and worth more: a lie has to be **visible in the diff**, where the operator and `integrity` both already look.

**Gates are executed from a host-supplied copy, never from `/work`.** `.saffron/` is exported out of the mirror at `base_sha` and mounted read-only at `/gates` (§5.1), and the runner execs the gates from there. An in-cell edit to a gate — committed or not — no longer reaches the runner. `reverify` (§5.7) does the same at `new_base_sha`, because it subtracts two suites of its own and they have to come from one set of executables.

**It also closes a drift nothing had recorded, and that is the stronger of the two reasons for doing it.** The baseline suite runs in the same cell and the same worktree as head, before the agent starts. Read from `/work`, the baseline ran the base tree's gates and head ran whatever gates were in `/work` by then — so a task that edits its repo's `tests` gate changes what the two subtracted sides *mean*. That is suite drift by construction. Pinning makes both sides provably the same executable, which is the question `tool` (above) was already asking between a run's baseline and its head and could only answer after the fact.

**The policy is read from that same export, not from the operator's working copy.** Both halves of a declaration have to come from one commit: reading `policy.yaml` from the checkout while the executables it names come from `base_sha` diverges them on any branch that touches `.saffron/` — which is the ordinary way a gate gets written. The ledger's `policy_sha` then names a file no gate was ever resolved against, and a branch adding a gate role fails preflight reporting a broken toolchain rather than a policy the export does not carry.

**A task whose job is to change a gate is judged by the pre-change gate**, and the new gate takes effect for the next task — its *declaration* included, so a branch that adds a gate role runs under the roles `base_sha` declares. Written down because it reads as a bug the first time someone's new gate does not fire on its own patch. The edit still lands in the patch, and `integrity`'s `gate_config` check still routes it to a person.

#### Gate roles

`policy.yaml` declares which roles the repo implements and their blocking level. Core supplies six; the repo supplies the rest.

| Role | Owner | Blocking | Notes |
|---|---|---|---|
| `scope` | **core** | yes | changed files ⊆ `touches` |
| `size` | **core** | at `elevated` | diff lines ≤ type ceiling (bug 300 / feature 600 / refactor 1000); `error` where it blocks and a file inside `touches` is hidden as binary — a `-diff` attribute otherwise counts 0 and passes any ceiling |
| `secrets` | **core** | yes | credential scan over the diff |
| `integrity` | **core**, repo patterns | yes | test-tampering check (below) |
| `census` | **core** | yes | collected test names at `base_sha` vs head (below) |
| `committed` | **core** | yes | the worktree is clean at gate time (below) |
| `criteria` | **core** | yes | each declared witness ran and turned green at head, and was not already green at `base_sha` (below) |
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

`when` is **declared and not yet read**: `repos/policy.py` parses it and `run_suite` runs every declared gate regardless, so a conditional gate today runs unconditionally. Saffron's own `shacl` gate is declared without it for that reason (`docs/BACKLOG.md`).

Core sees three more entries in a list. **The best gates are always the domain-specific ones** — a migration round-trip, a schema conformance check, an invariant only this codebase can state — because they are the ones an agent cannot satisfy by writing plausible-looking code. Onboarding a repo well means asking: *what is expensive to fake here?*

Five roles carry most of the weight.

**`integrity` — the anti-gaming gate.** The dominant failure mode of a hard-gate self-repair loop is not the agent giving up; it is the agent *making the gate pass*. Deleting a failing test, adding `@pytest.mark.skip` or `xfail`, sprinkling `# type: ignore`, loosening `==` to `is not None`, lowering a threshold in config. Two of those are visible in the diff and one is not, so the work is split across two gates: `integrity` fails on any newly added suppression, and on any edit to gate configuration **unless `touches` explicitly includes the file**; `census` (below) answers deletion, which a diff cannot. Without the pair, hard gates actively *train the loop toward test destruction*, because that's the cheapest path to green.

**The exemption binds `gate_config` alone, and the reason is a rule worth carrying.** `touches` is a **file-level** authorization, and `scope` already requires every changed file to be inside it — so in any diff that can reach green, a per-file exemption fires on *every* file. A file-level key cannot exempt a **line-level** check without nullifying it. "Was gate configuration edited?" is file-level and the exemption fits it. "Was a suppression added on this line?" is not, and exempting it produced a measured green run on the move this paragraph names first: `touches: ["tests/test_a.py"]`, a failing test, and `@pytest.mark.skip` added to it — `scope`, `integrity`, `census` and `tests` all passing.

**What the exempted check is left covering, measured.** Exempt, `gate_config` fires only where `scope` has already failed — with one exception, and it is not the one it is tempting to name. A `touches` *broader* than the gate-config pattern does **not** leave a gap: `touches: [".saffron/**"]` against an edit to `.saffron/policy.yaml` matches, so `declared` is true and the check is exempt. The only live case is an **empty `touches`**, where `scope` skips outright and `integrity` still fires — the check's whole remaining value. That is thin, and it is stated rather than fixed: narrowing the exemption is a design change, and a check that fires in one case is not a check that fires in none.

The cost of not exempting suppressions is prose: a docstring quoting a token fails, and this repository's own merge of PR #5 does. That is accepted, because the failure is a `fail` and not an `error` — it reaches the agent with the file, the line and the token named, and the repair is to reword a docstring. A gate that never fires cannot be repaired, because nothing reports it.

Deletion is exempt from nothing. `touches: tests/test_session.py` authorizes *editing* that file; it does not authorize deleting three unrelated tests inside it to reach green. Exempting deletion would silence `census` on nearly every real task, since almost every spec names a test file.

The *logic* is core — "was a test removed or silenced?" is a question about a diff, and it is identical in every language. The *vocabulary* is not, so the repo declares it:

```yaml
integrity:
  test_paths:   ["tests/**", "**/*_test.go"]
  suppressions: ["@pytest.mark.skip", "xfail", "# type: ignore", "# noqa"]
  gate_config:  ["pyproject.toml", ".coveragerc", ".github/workflows/**"]
```

This split is the boundary of §2.1 in miniature, and it is the pattern to reach for whenever a check feels language-specific: usually the *question* is universal and only the *tokens* are local. Pushing the tokens into `policy.yaml` keeps the check in core where it gets maintained.

**`census` — which tests existed, and which exist now.** The set of test names collected at `base_sha`, minus the set collected at head. A name that was there and is not is a removed test, one failure each.

This is the same question `integrity` used to ask of the diff, asked where the answer actually lives. Three diff-shaped versions of it were written and all three were wrong, in three different ways: net line count is defeated by a comment longer than the test, run adjacency by *any* adjacent added line, and neither sees a test renamed out of collection — where nothing is removed, nothing is suppressed, the body survives intact, and the test never runs again. A set comparison has no false positive on a `parametrize` consolidation, because consolidation keeps the names.

**It executes nothing, and needs no exception to §2.1.** The repo's `tests` gate already runs at `base_sha` to build the baseline and again at head on every attempt. The names do not have to be fetched, only *reported*: the contract gains an optional `collected` field, the `tests` gate fills it, and core subtracts two lists it is already holding. Unlike `revert`, core invokes nothing here — it reads a field of a gate result, which is §2.1's original sentence rather than the exception to it. A repo whose runner cannot enumerate omits the field and `census` reports `skip`.

The two sides are not symmetric. No names at base is `skip` — nothing to compare. Names at base and none at head is `error`: a test suite that enumerated before the task and stopped after it is grounds to distrust the comparison, not to report every test as deleted. A head `tests` that errored has already aborted the attempt before `census` is consulted, so a truncated collection can never be read as a mass deletion.

**A skipped test is still a collected test.** Measured: `pytest -q --collect-only` lists a `@pytest.mark.skip` or `xfail` test and the run exits `0`, so `census` does not see marker-based silencing and is not the gate that covers it — `integrity` is. Only `-m` deselection removes a name, and that is an edit to gate configuration rather than a marker. What `census` catches is removal and rename-out-of-collection; a test still collected but silenced belongs to `integrity`, and a test still collected but gutted belongs to `revert`, which is not built yet.

**`committed` — the tree the gates measure is the tree the patch contains.** `git status --porcelain` inside the cell, read **after** the declared suite on the baseline call and the head call alike — an artifact a gate itself writes (`.coverage`, a build dir) then appears on both sides, where the baseline subtraction can cancel it. Reading before the suite saw a clean baseline and only head's leftovers, and burned the repair turn on paths the agent never touched. The cancellation is by identity, so it reaches only artifacts whose paths match on both sides; a repo whose `.gitignore` does not cover its build output still owes `committed` a failure it cannot repair. The gates exec against `/work` while `export_patch` diffs `base_sha..HEAD`, so **any** uncommitted change is absent from `scope`, from `integrity` and from the packaged patch while being fully live for every gate result. An uncommitted edit to the gate itself is only the sharpest instance; an uncommitted edit to any source file changes what the suite measures while the patch a human reads does not contain it. Non-empty status is `fail`, one failure per path — never `error`: a dirty tree is the attempt's problem, not infrastructure's, and an `error` would abort the attempt and be charged to nobody.

**It needed no new control flow, which is the argument for it being a gate rather than a check.** A `fail` gets the repair turn the loop already gives every failing gate — commit your work — and a second identical look is the no-progress rule (below) ending the attempt. One turn is worth its cost because this is an honest mistake a capable agent will make at least once before the prompt is tuned, and burning an attempt on it teaches nothing. Low disruption otherwise: §4.3 already measures doneness from commits, so an uncommitted tree at gate time was already a mistake.

**What none of this buys, stated so it is not discovered.** A **committed** `conftest.py` whose `pytest_collection_modifyitems` drops a test only when `config.option.collectonly` is false still defeats `census`: enumeration reports a name the run never executes, `census` passes because the name is collected, `tests` passes because the test never ran. Core cannot catch it — collection happens inside the repo's own Python, and "what is a collection hook" is language knowledge §2.1 keeps out. The narrowing is repo-shaped and costs one line of YAML: `**/conftest.py` in `gate_config` makes `integrity` fail any diff touching that file unless `touches` declares it. It does not stop the lie; it routes the lie to a person, which is all a diff-shaped layer was ever going to do.

Three more routes reach the same place, each measured against real git with the exact flags `worktree._git` passes. **`.git/info/exclude`**: an agent appends `conftest.py` to it, and `git status --porcelain -z -uall` and `git diff base..HEAD` both come back empty — the file is invisible to `dirty_paths` and to the patch while fully live for pytest. `DIFF_FLAGS` pins `git config` values (as `diff.srcPrefix`); this one is not a config value, so no `-c` override closes it. **`git update-index --assume-unchanged <file>`**, then rewrite the file: `git status --porcelain -z -uall` stays empty while the modified test runs live; `git ls-files -v` reports the file with a lowercase `h`, which is the cheap detection if it is ever wanted. **The in-cell toolchain is writable**: `images/cell-base.python.Dockerfile` sets no `USER` and `worktree.py` passes no `user=`, so the cell runs as root and `/opt/venv` — pytest itself — can be patched.

**`census` buys exactness against an honest suite; the gate source and `committed` buy visibility against a dishonest one. Neither buys integrity, and no diff-shaped check will.**

**`criteria` — every acceptance criterion is prose, and an unchecked one is indistinguishable from a met one.** A spec's criteria were rendered into the PR body as `- [ ]`, unticked, always, for every criterion, with no host-side component anywhere that asked whether one was met. That is §5.4's founding `tool` defect one layer up, in the layer that decides whether a pull request is merged: the artifact an operator reads to decide looks identical whether the work was verified or nobody looked.

A criterion may therefore declare a **witness** — a test node id, in an optional `acceptance:` frontmatter block alongside the `claim` the PR body renders. What a ticked box then means, exactly: *a test by this name ran at head and passed, and if it existed at base it was not green there.* It does not mean the criterion was met; the witness's body is out of reach, which is `revert`'s question and not this one.

**It reads two gate results and invokes nothing** — `census`'s route, and the cheaper question §2.1's seam asks before reaching for `revert`'s exception. Both suites already ran: *did witness W pass on this side?* is `W ∈ collected` and `W ∉ {f.code}`, two lists the host is already holding. The cost is one contract obligation parallel to `collected` itself — a `tests` gate must key its failures on node ids — and where it does not, `criteria` reports `skip`.

**How core knows the field carries node ids, without parsing one.** A name is opaque, so a gate that recognises `::` has learned a language. The whole test is set membership: **a side is readable iff its failures list is empty, or some `failures[].code` appears in that side's `collected`.** Failures present and disjoint from the enumeration mean the runner keys failures on something else, and that side is `skip`. This is measured, not hypothetical: this repo's own `tests` gate reaches node ids only through a fallback that runs when a regex over the whole output matched nothing, and one printed `path:N: word: message` line inside a failing test satisfies that regex — every node id vanishes from the field for that run. Without the membership guard the naive rule reads *W was collected and W ∉ {"error"}* and reports `pass` for a witness that failed. A ticked box over a red test is this gate's own defect, reintroduced by the gate that closes it.

**The direction is the load-bearing part.** A criterion claiming the change *did* something must name a witness that did **not** pass at `base_sha` and passes at head — one already green proves nothing about this change. `preserves: true` claims the opposite and is checked the opposite way, green at both sides. A witness absent from `collected(base)` because the diff adds it is the ordinary new-criterion shape and produces no `error` anywhere, so the baseline suite (§4.4) is unaffected.

**`skip` is not a failure and is the common case**, and the PR body says which kind of unticked a box is: where no gate result stands behind the checklist it renders as *not mechanically checked*, because an unticked box meaning *nobody looked* must not render identically to one meaning *the witness failed*. Reaching for a default witness would be worse than skipping — a criterion checked against an invented test is the defect this gate exists to close, wearing the fix's clothes.

**What it cannot see.** A **vacuous** witness: a new test is absent from `collected(base)`, so "did not pass at base" is free, and `def test_w(): assert True` satisfies everything expressible here. `revert` closes that case; nothing here does. A **flaky** witness that happened to fail at base makes a no-op criterion read as met — the rule has no repetition or quarantine, unlike baseline subtraction, which tolerates flakes by cancelling them. A **refactor** spec has no behaviour change, so every criterion is `preserves` and the rule yields no signal for that spec type. And a witness that exists at base and is modified by the diff is judged on its name, not its body.

**`revert` — the anti-theater gate, and the best cost/value ratio in the system.** Stash the source hunks of the diff, keep the test hunks, run only the new and changed tests, and require them to **fail**. One extra test run. This is the one place core reaches into the repo's toolchain, and it is why the contract requires the `tests` gate to accept a **test-subset argument** — the single most constraining line in the whole contract, and worth the constraint: every serious test runner supports it, and without it this gate degrades to a full-suite run per attempt. It mechanically answers the question critic lens #3 would otherwise be asked to reason about: does this test actually detect the thing it claims to? It catches deleted assertions, `assert result is not None`, and tests that pass identically on `main`.

This replaces mutation testing, which was the obvious choice and doesn't fit: `mutmut` reruns the test suite per mutant, a Timescale-backed suite takes minutes per run, and 15 mutants is an hour inside a 2-core cell competing with two siblings inside an 8-hour window that also has to fit 10–15 tasks. It would break N3 outright.

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
- **The budget stop shares it, deliberately.** A task the spend ceiling stops before its next turn is `EXHAUSTED` too, and in the ledger and the morning queue that is indistinguishable from four failed attempts — the distinction lives only on the watch line. Accepted for v0.5, which is attended: the operator is reading that line as it happens, and the `tasks` row carries the budget and the spend. It stops being acceptable when the queue is read the next morning instead of watched, so v1 splits it — the two have opposite remedies, raise the budget versus rewrite the spec.

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

**The order, settled.** "Confirmed blockers" here means *anchored* (§5.5) — the host has already established the finding points at real changed code, and that is the only confirmation available before a rebuttal exists. The critic's `verdict` (§4.1) comes **after** the argument: anchored blockers → the implementer rebuts → each lens that raised one confirms or withdraws it, in a fresh read-only session that sees the argument and never the transcript behind it. A critic verdicting first would be restating its finding rather than disagreeing with an answer, which is the one thing this phase exists to record. Three outcomes reach `READY_FOR_REVIEW` — every blocker withdrawn, a fix that commits and stays green, and a confirmed blocker the implementer argued against — because none of them is the machine's to settle: adjudication is yours, in the PR. A rebuttal that neither moved HEAD nor recorded an argument earns nothing and halts at `REBUTTING`; §3.3 has no state for it, and `NOT_IMPLEMENTED` would name the wrong phase.

**Risk tiering.** `risk: elevated` — set explicitly in the spec, or auto-elevated when the diff touches any path in the repo's `policy.elevate_on` (a repo with migrations and an ontology might list `migrations/**`, `**/*.ttl`, `trading/**`; Saffron's own lists `saffron/gates/**` and `saffron/cell/**`) — adds the third lens, makes `size` blocking, and marks the queue entry so you read it cold rather than skim. **`coverage` does not become blocking** — not at `elevated`, not ever; see §5.4.

Getting `elevate_on` right is most of what "onboarding a repo" actually means. It is the repo owner answering one question — *where in here does a plausible-looking wrong change hurt most?* — and it is worth more than any amount of gate configuration.

### 5.7 Phase 5 — PACKAGE (no model involved)

Host-side, deterministic:

1. Rebase onto current `main` (or onto the parent branch, if stacked). Conflicts → `MERGE_FAILED`. Never ask an agent to resolve conflicts unattended; a plausible-looking wrong answer there is very expensive. (Prior art suggests a middle path — see §11, "what I'd revisit".) **"Rebase" is the intent — the change lands on today's default branch — and `git apply --3way` of one squashed patch (below) is the mechanism.** Both are true; the document never said so, and a reader meeting them in order takes one for a contradiction.
2. Push `saffron/TE-0142-forecast-gap` to the real remote **with `--force-with-lease` pinned to the SHA the packager checked out.** If the branch moved underneath — a re-queued task, a second run, you pushing a fixup by hand — the push fails loudly instead of silently clobbering. Turning a race into an error costs one flag.
   Branch mutation is also serialized: one writer per branch, ever, held across package and merge-train operations. A `CHANGES_REQUESTED` task that gets re-queued must not race the merge train rebasing the same branch.
3. Open the PR. Body generated from the ledger: spec, root cause (if diagnosed), acceptance-criteria checklist with the critic's assessment of each, gate table, findings with rebuttals, attempt count, cost, transcript path.
4. Append the verdict line to the batch index.

**The base a task is cut from is the head of the remote's default branch as of task start**, not the invoking checkout's `HEAD`. It is fetched into the mirror before the cell is built (§5.1), so both ends of the comparison below read one source rather than two. Two consequences, both intended. Uncommitted and unpushed local work leaves a task's base — running from a dirty feature branch used to include it silently, and this is the change most likely to surprise an operator standing at a terminal. And the re-verification skip below becomes reachable by construction rather than by accident, because in the common case nothing has moved. The rejected alternative — keep `HEAD` and have PACKAGE compare against it too — is symmetric and needs no network; it loses because it makes a task's base unreproducible from the ledger, and §4.2 cannot start tasks unattended if two of them queued the same night are cut from different trees for no recorded reason.

#### v1: one squashed commit, a draft PR, and re-verification only when the base moved

v1 packages **one squashed commit**, not the agent's own. The cell's commits
live on the worktree volume and die with it, so `patch.diff` — a squashed
`git diff` — is the only thing that survives teardown (§5.1). The consequence
is a provenance seam and the body states both halves: **the pushed sha is not
the cell's head sha**, and the cell's head names an object no longer reachable
anywhere. The agent's own commit subjects are captured before teardown and
carried in the commit body, which is the record they would otherwise only have
in a transcript.

The PR opens as a **draft**. Real enough to exercise the path nightly, without
pinging reviewers while v1 settles.

**Re-verification runs when, and only when, the base moved.** If the default
branch head still equals `base_sha`, the merged tree is byte-identical to the
one the suite already ran on and re-running it is provably redundant; the body
says it was skipped and why. Otherwise the suite re-runs — **inside a cell,
never host-side**, because the applied tree carries `.saffron/gates/*` exactly
as the patch left them, and exec'ing those on the host is the control plane
executing model-authored code (§2). Both of its runs read their gates from a
host-supplied export at the new default-branch head (§5.4), so the patch's own
`.saffron/gates/*` are never executed anywhere and the two suites it subtracts
come from one set of executables. **PACKAGE reads its whole policy out of that
export**, unconditionally and whether or not the suite re-runs: the commit a
package is verified against declares the gates it is verified with, exactly as
`base_sha` does for the cell, and the pull request body then describes the
change under the declaration it was actually measured with. The base having moved also invalidates the
baseline, so the gate-only cell runs the suite twice — at the new default-branch
head for a fresh baseline, and at the packaged commit — and subtracts as always.
New failures are `MERGE_FAILED`: the change did not survive contact with today's
main.

**Two measured `git apply --3way` hazards** (git 2.50.1), both of which break
the obvious implementation:

- A **conflicting** apply exits 1 **and still writes the file**, with `<<<<<<<`
  markers and a staged `U` entry. "The apply failed" and "nothing happened" are
  not the same state.
- A **degraded** apply exits **0**. With the preimage blob absent and the hunk's
  context matching, git prints `error: repository lacks the necessary blob to
  perform 3-way merge. / Falling back to direct application...` to stderr and
  succeeds. Conflict detection silently becomes a context match.

So the exit code alone decides nothing: a non-zero exit is `MERGE_FAILED`, and a
zero exit whose stderr names the missing blob is an `error`.

**PACKAGE refuses to push a patch carrying the cell's credential.** It is the
first component that moves cell-authored bytes off the host, and the cell holds
`CLAUDE_CODE_OAUTH_TOKEN` (§5.1). A token pushed to a real remote is effectively
undeletable. This is a refusal, not the `secrets` gate — that gate is still v1's
to build, and until it exists **the residual risk is every credential shape the
refusal does not know**, stated here rather than left to be discovered.

Model-authored text is neutralized before it enters a commit body or a PR body:
GitHub acts on `Fixes #12` and `@name` in both, so a cell can close an issue or
notify a person without executing anything.

Two deviations from the list above, each waiting on a named sub-project: the
acceptance-criteria checklist ships **unchecked** only where no witness is
declared — `criteria` judges a witness's name and outcome, never the claim
itself, so no *lens* produces a per-criterion assessment; and there is no
root-cause section, because DIAGNOSE does not exist.

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
2. **Every state that needs you and is not a reviewable diff**: `MERGE_FAILED`, `PLAN_REJECTED`, `PREFLIGHT_FAILED`, `GATE_ERROR`, `NOT_IMPLEMENTED`, `EXHAUSTED`, `ORPHANED`, `RATE_LIMITED`. Rev 17 widened this from the first two, against `_STATE_RANK` in `report/index.py`, which had already grown the other six with a reason recorded at each: absent them, a task that could not pass its own gates or whose cell died sorts *below* a green PR. `_STATE_RANK` also ranks `REVIEWING` and `REBUTTING` alongside elevated risk — a task the night left mid-phase — which this list leaves at that level deliberately rather than by omission.
3. **Sustained blockers, descending** — a blocker the critic verdicted `confirmed` **and** the implementer answered with an argument rather than a fix (§5.6's `action`). Both halves are load-bearing: `confirmed` alone also covers a blocker the implementer *fixed and committed*, and ranking on that would rank a task by work already done — the mirror of the defect this level exists to fix. See below. `sort_key` implements this as `_SUSTAINED`, ranking above `risk: elevated` but never above the states in level 2, which already need you more; its ranks 3 and 4 moved to 4 and 5 (`SA-0008`).
4. `risk: elevated`
5. Everything else by concern count descending — concerns, not findings (`CONTEXT.md` §5): `note` is excluded by construction

**Level 3 is the one a live ledger added, and it is the page's job rather than a refinement of it.** §6 used to rank on concern count alone, guarded by the claim that *"`blocker` never reaches this page unrebutted"*. That claim is true and it is not the property the page needed. A blocker that reaches REBUT and is verdicted `confirmed` **has** been rebutted — the rebuttal failed — and `anchored_concerns` sums `severity == "concern"`, so it contributes nothing to the number the page was ranking on. Measured on this repo's own ledger: `SA-0005` (PR #21) is the most expensive task Saffron has produced. It drew three blockers, two of them anchored and therefore routed to REBUT (§5.5), and the critic confirmed both — one against an argument, which is the sustained disagreement `rebut.py` itself hands you as *"recorded disagreement, yours to adjudicate"*, and one against a fix the implementer had already committed. It renders as `0 concerns` on the bottom line of ten, wearing the same caption as four scaffolding rows. A page that exists so you can dismiss in ten seconds put the one row you must not accept last. `docs/evidence/2026-08-25-morning-queue-from-real-rows.md`.

**A confirmed blocker answered with a fix nobody committed ranks *with* a sustained one and is not counted *as* one.** `rebut_state` already measures it — `claimed and not moved` — and says so in the `why` it hands the ledger, where no page has ever read it. It is a different failure from a sustained disagreement: the implementer did not argue and lose, it promised and did not deliver, and on a page read in ten seconds those want different words rather than one number meaning both. Conflating them is the move level 3 exists to undo, one layer further in. So it enters level 3's rank and keeps its own count. The measurement is task-level and therefore a floor: `moved` is one bit for the whole rebuttal, so a task whose HEAD did move reports none of these even when only one of two claimed fixes landed. Naming that ceiling is cheaper than a per-blocker attribution the phase cannot make.

> Three judgements, three words (`CONTEXT.md` §5): the critic **verdicts**, the implementer **rebuts**, the operator **adjudicates**. This level ranks on the first two. Nothing writes an adjudication yet — `findings.adjudication` is `NULL` on every row in the ledger — which is the same missing record the trailing accept rate needs.

**The queue reads `queue.json`, not the ledger, and that is currently undecided rather than chosen.** PACKAGE appends a `QueueLine` per task to a store in the batch tree, and the page renders from it. The ledger cannot reproduce that store: `tasks.risk` was never written for tasks that ran before `SA-0007` closed item 18's fifth instance, and the diff stat this section's own mock shows (`+180/−22`) is stored in no column at all. So there are two records of a night and the authoritative one is the file, not the database. Either the ledger gains what it is missing, or this section stops implying the ledger is the source.

**Sort by state, not by repo.** The temptation with multiple repos is to group them, and it is worth resisting: the most urgent item across all repos should be the top line, and grouping buries a skipped repo under another repo's routine PRs. Repo is a column you scan, not a heading you navigate.

Batch header: counts by terminal state, total spend, wall clock, per-repo preflight and base-suite status, and the one number that says whether this is working — **trailing accept rate**.

**Three of those six have no source yet, and the gap is not evenly distributed.** Measured against the real ledger (same record): wall clock arrives with the `batches` table §4.2.1 decides; `runs.preflight` is a column that exists and is never written; and nothing anywhere records whether a task was merged, which is the trailing accept rate's whole input. Terminal-state counts and base-suite status both render today — the baseline suite is recorded with `run_id` set (`cell/session.py`), 64 rows across ten runs, and joins per repo through `runs.repo_id`. Total spend renders but reads `0.0` on the five tasks that predate cost reconciliation, which is a truthful zero rather than a gap. **A header field with no source is not a smaller header — it is a field that renders a confident em-dash**, and the batch header is the part of this page an operator reads first.

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
| **Chasing pre-existing failures** | Base was already red | Baseline gate suite; only new failures count |
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
| **Language knowledge leaks into core** | One `if lang == …` is always easier than a contract change | The seven core gates never execute repo code — most read the diff, but `census` and `criteria` read other gates' results instead; any core gate that wants to *run* something belongs on the repo side (§2.1) |
| **One repo starves the others** | Priority ordering across a shared pool | Round-robin across repos in the scheduler; per-repo lines in the batch header |
| **A broken `policy.yaml` costs the whole night** | Preflight treated as fatal | Per-repo preflight; a failing repo is skipped and surfaces at the top of the queue |
| **Gate `error` mistaken for `fail`** | Crashed toolchain looks like a red test | `error` is a distinct contract status; aborts the attempt, never counts against the task |
| **Timeout discards committed work** | Process didn't exit ⇒ attempt treated as failed | Doneness measured from git after any bound fires; never auto-clean on failure (§4.3) |
| **Agent rewrites a validated control artifact** | `plan.json` lives in the writable worktree | Host extracts and hashes it at validation; never re-read from `/work` (§5.3) |
| **Hallucinated critic findings** | Nothing checks the finding points at a real changed line | Findings reconciled against diff hunks; unanchorable ones dropped and counted (§5.5) |
| **Spec text breaks or hijacks prompt assembly** | Markdown containing template syntax | Spec body is a substituted value, never scanned as a template (§5.3) |
| **Silent branch clobber** | Two writers on one branch | `--force-with-lease` pinned to the checked-out SHA; one writer per branch (§5.7) |
| **Money spent to learn something free** | Refusable conditions discovered inside the cell | Refusal gate before any container starts (§4.2) |
| **A proxy that started but reaches nothing** | Every layer reports success; the first real use of the network is the agent's, inside a paid attempt | Egress asserted through the proxy, before the cell is built (§5.1.1) |
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
| **Repair loop pays full input price every attempt** | 5-minute cache TTL is shorter than a gate suite | One-hour cache TTL set on the cell (§7.1) |
| **A critic lens silently doesn't run** | Lenses spawned as subagents are invoked at the model's discretion | Each lens is a separate host-invoked session (§5.5) |
| **An estimate hardens into a billing fact** | Runtime-reported cost is a local approximation | `_est` suffix on every stored figure; reconcile against real billing (§4.1) |
| **Host services reachable from an isolated cell** | An `--internal` network still routes to the host gateway — **confirmed by spike**, at the gateway *and* at the LAN address | Bind host services to `127.0.0.1`, never `0.0.0.0`; verified by a preflight probe over the host's *enumerated* non-loopback listeners, because N1 rests on it. A named process can be tolerated per invocation — empty by default, matched by name not port, and reported on every run, because an exception that goes quiet is this row's hazard again (Appendix G) |
| **A cell gets more CPU than it was allocated** | The runtime allocates `--cpus + 1` vCPUs | Request `n − 1` and assert the result; re-measure the offset on every runtime upgrade (§5.1, Appendix G) |
| **The cell cannot resolve its own proxy** | Internal networks have no DNS | Pin the network subnet and address the proxy by IP (Appendix G) |
| **A runtime flag silently means something else** | Container flags are interpreted inside a VM on macOS | State the requirement, not the flag; verify each control on the runtime actually chosen (Appendix G) |
| **A gate that never ran reports `pass`** | An absent tool and a clean repo emit identical JSON | `tool`, obtained by executing the tool; non-zero exit with empty `failures[]` is `error` (§5.4, Appendix H) |
| **Every control reports green and none is connected** | The controls and the cell are wired in different modules; no test crosses the seam | `network`/`env` required where a cell is created; the isolation test starts a cell the production way and probes from inside it (§5.1, Appendix I) |
| **An image contains a tool it cannot run** | `which` prints a path for a console script whose shebang is stale | The image build asserts by *running* the toolchain, never by locating it (Appendix I) |
| **Core demands a language of every target repo** | A core probe or check executes something only one ecosystem has | Core probes run in the base image core owns, never in a repo's cell image (§2.1, Appendix I) |
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

**Extend the prompt-cache TTL, or the repair loop pays full price every attempt.** The default cache lifetime is five minutes. The repair loop resumes the same session *across a gate suite*, and a suite against real fixture services is minutes — so on most attempts the cache has expired and the entire accumulated context is re-billed as fresh input. The repair row above is the row this lands on, and it is the row that runs up to four times. The runtime exposes a one-hour TTL through an environment variable; set it on the cell. It trades a higher cache-write rate for reads that actually survive a suite, and it is the single cheapest cost lever in the system — one env var against the most-repeated phase.

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

**Built 2026-08-20, second half outstanding.** The harness is complete and reviewed: cell runtime seam, base and cell images, proxy, host-binding probe, volume worktree, the `tool` field and `error` rules, the executor seam, Saffron's own `.saffron/` onboarding, per-phase vocabulary injection, the plan checkpoint, and the session options. The **cell half of the criterion is met and measured** — a cell reaches `api.anthropic.com` through the proxy and nothing else, including by raw TCP to a bare IP, which is what proves the containment is the network rather than an environment variable an agent could unset. The **agent half is not**: `run_one_cell` stops at a marked seam and returns `NOT_IMPLEMENTED`, because the shape of that loop depends on what the message stream actually yields and writing it blind produces a step that reads as complete and is fiction. Appendix I is what building it found.

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

It says otherwise (rev 18). `ontology/queries/` therefore stays where it is, as worked examples that `tests/ontology/` runs — moving them under `docs/` would cost the only thing keeping them honest. The vocabulary stays as documentation with two readers the queries are not: the `shacl` gate and the `CONTEXT.md` cross-check. Appendix O's spike is the only thing that reopens an emitter. **That is a completed project, not an abandoned one** — you will have bought a precise answer to "is the relational model costing me anything?" for the price of a weekend, which is the cheapest that answer is ever available.

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
    cell-base.python.Dockerfile    # agent runtime + git. Nothing else, ever.
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
- **`revert` vs. mutation testing.** If gate wall-clock stops being the constraint (faster fixtures, more cores), mutation sampling on `risk: elevated` diffs becomes affordable and is strictly stronger. **Measured 2026-08-25 (#33): wall-clock is no longer what binds.** `mutmut` 3 does not rerun the test suite per mutant — 74s on the file, 274s on the module, both inside §7.1's window — so the cost clause above holds for `cosmic-ray` and not for `mutmut`. What binds now is that `mutmut` cannot scope below a function and cannot run over a test suite that gates its own tree, while `cosmic-ray` scopes to a diff and lacks the string-literal operator the one real defect needed. Reach for `mutmut` if either constraint lifts, not `cosmic-ray`. This is not a recommendation to adopt it — #33 chose a prompted lens — only a correction to the stated reason. `docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`.
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
11. **Modelling pays before it ships.** Writing down what an *attempt* is in relation to a *gate result* produced two schema criticisms (§4.6) that hold whether or not a triple is ever stored. The output of a modelling exercise is not only the model.

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
- **What that probe covers is enumerated, not remembered** (added 2026-08-20). It
  first shipped against seven ports somebody thought of, so its clean result meant
  "no host service answered on seven ports" while the docstring and this page both
  said "no host service is reachable" — and the v0.5 run that caught a service on
  8000 had four more on 8001+ that no such list would have named. `lsof -nP -iTCP
  -sTCP:LISTEN` now supplies the ports, every listener not bound to loopback, and
  enumeration that cannot run raises rather than quietly narrowing the probe to
  nothing — the `_lan_address` defect, one function over. An empty result is still
  a real pass; it now means what it says. Measured on the machine v0.5 ran on: four
  macOS services (ARD 3283, Control Centre 5000 and 7000, rapportd 49152) are
  wildcard-bound and answer from inside a cell, and none is in the old seven.

### One tolerated listener, and what it costs (2026-08-21)

**This is an accepted risk, not a fix.** The operator turned Handoff off, which
closed two of `rapportd`'s three sockets; `*:49152` stays up regardless, and
AirDrop going back on will reopen the others. So the probe correctly refuses to
start a cell, permanently, for a daemon the operator has decided to keep.

**Tolerated:** the process `rapportd`, by the COMMAND `lsof` reports —
`SAFFRON_ALLOW_HOST_PROCESS=rapportd saffron cell …`.

**Why it is judged acceptable:** it is Apple's own Continuity daemon doing
link-local discovery for Handoff, Universal Clipboard, Sidecar and AirDrop. It
is not a general-purpose service surface, it holds no repo data, and it is not
something a cell can be given credentials to.

**What it costs, plainly:** an agent inside a cell can open a TCP connection to
that socket, at the gateway and at the LAN address, without traversing the
proxy. N1 is *not* satisfied on this machine; it is satisfied except for one
named process, which is a weaker claim and should keep reading as one. A
`rapportd` remote-reachable bug is a hole Saffron has chosen to live with, and
revisiting it means turning Continuity off, not editing this paragraph.

Three properties the mechanism has, and each is load-bearing:

- **Nothing is tolerated unless it is named.** The default is empty and an
  unnamed listener fails exactly as before — measured with a second wildcard
  listener up: `rapportd` tolerated, the stranger still fails the probe.
- **It is matched by process name, never by port.** `rapportd`'s ports are
  dynamic — 49152, 60215 and 60216 have all been seen — so a port allowlist
  would be wrong the next time it restarts. A port drops out of the probe only
  when *every* listener on it is a tolerated process, so a second process
  sharing the port is not tolerated by association.
- **It is reported on every run, not the first.** §7's hazard row exists
  because a host service reachable from a cell is invisible, and an exception
  that goes quiet recreates that invisibility. The preflight line always ends
  `; tolerating rapportd:49152` — or `; tolerating nothing`, so the absence of
  a tolerance is stated rather than inferred.

An environment variable rather than a CLI flag: the probe has two entrypoints —
`saffron cell` and the `-m cell` suite — and one relaxation should not need two
knobs. It does **not** belong in `policy.yaml`, which is the repo's; this is a
property of the host. The cost of the env var over a flag is that it can be
exported into a shell profile and forgotten, which is exactly what the
every-run report is there to catch. Enumeration that cannot run still raises
with a tolerance named: tolerating a *listener* must never become tolerating a
probe that covered nothing.

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

---

## Appendix I — rev 11: what building v0.5 found

Appendix H ended by arguing the next artifact should be v0.5 rather than another
document. It was. Eleven tasks, twenty-three commits, every task reviewed against
its own brief and the whole branch reviewed at the end. What follows is what only
building it could produce.

### The headline: every control reported green and none was connected

`prepare_worktree` created the long-lived cell with no `--network` and no proxy
environment, so it joined the runtime's default network with full internet
egress. Meanwhile the driver created the isolated network, ran the host-binding
probe against it, started the proxy on it, printed `preflight: proxy at
10.88.0.3` — and passed none of it to the container holding the agent. Measured
before the fix, from a cell built exactly the way production built one:

```
$ container run --rm --cap-drop ALL saffron/cell-base:python \
    python -c "...urlopen('https://example.com')..."
REACHED 200
```

`proxy_env()` had been written, was never called, and had no test.

This is §2's claim — *a cell is untrusted, and untrusted means every control that
matters lives outside it* — satisfied in every part and false as a whole. The
proxy was correct. The probe was correct. The network was correct. Nothing joined
them, and the thing that would have caught it is the one test nobody wrote: start
a cell **the way production starts one** and probe **from inside that container**.
Every isolation test on the branch used an ephemeral sibling instead, which is a
different container answering a different question. The distinction is what is
being asserted, not what runs the assertion: a claim about *this container's*
egress must be probed from inside the production-shaped cell, while a claim
about the *network* — N1's host-binding probe, which runs before any cell
exists — is properly made by a sibling on that same network.

38. **A control and its subject are wired somewhere, and the wiring is the
    control.** Verifying each mechanism in isolation verifies nothing about the
    system, because a mechanism that reports on a thing it was never attached to
    reports on nothing at all. Test the join, from the subject's side.

The fix makes `network` and `env` **required** arguments where a cell is created,
so omission is a `TypeError` rather than a silent unisolated cell — the guarantee
moved from a call site's memory into the signature.

### The same defect, five times, in five disguises

Appendix H named principle 34: *a green result and an absent result are the same
bytes.* v0.5 produced four more instances, and the fourth is the one worth
keeping.

- **A tool-output parser silently stopped matching.** The `format` gate was
  written against ruff's `Would reformat: <path>`; installed ruff emits
  `--> path:line:col`. It matched nothing. The gate reported `error` rather than
  a false `pass` — not by luck, but because its `pass` branch is gated solely on
  the exit code and is independent of the parse. Rule 2 working on first contact
  with a real tool upgrade.
- **A section slicer over-captured.** Vocabulary injection treated only `## N.`
  headings as boundaries, so §10 — which every phase receives — ran to
  end-of-file and swallowed `CONTEXT.md`'s two trailing unnumbered sections.
  Roughly 700 characters of naming-decision history went into every prompt of
  every attempt: precisely the cost §5.3 designed per-phase injection to avoid.
  Nine tests passed because all nine ran against a synthetic fixture that happens
  to end on a numbered section.
- **A dead seam nearly returned an earned state.** The driver was written to
  return `READY_FOR_REVIEW` at the point where the agent session would be driven.
  It is a real terminal state elsewhere, so a task that ran nothing would have
  reported as assessed. The implementer refused and invented `NOT_IMPLEMENTED`
  instead — applying this document's founding principle to a state string,
  unprompted, without having been told the v0 story.
- **`which` is not a check.** The fix wave verified the cell image's toolchain
  with `which uv pytest python git`. That prints a path. `pytest --version` exited
  127, because the image built the venv at `/seed/.venv` and moved it to
  `/opt/venv`, and a console script bakes its interpreter into its shebang.

39. **Locating a tool proves a file exists; only running it proves a tool works.**
    Every check of the form "is X present" is a check that reads identically when
    X is present and broken. The image build now asserts by executing
    (`RUN ruff --version && pytest --version`), the same shape as the base image's
    bundled-binary assertion.

### Seams between correct components

Two independently-correct pieces disagreeing at their boundary was the branch's
most common defect after the wiring one, and neither instance was reachable by
any test that existed.

- **Two glob matchers.** `saffron/gates/core/scope.py` already carried a
  hand-rolled translator whose docstring states it exists *because* "fnmatch lets
  `*` cross a `/`". The plan checkpoint then reached for `fnmatch` for the same
  job on the same patterns. Nothing triggered it, because every declared pattern
  uses `**`; the first bare `*` would have produced a plan that passes validation
  and then fails the `scope` gate mechanically, reading as the agent wandering out
  of scope. `scope.py` is now the single authority, imported by both — it is the
  authority by construction, because it is what enforces the diff.
- **`spec_sha` received `policy_sha`.** Same type, wrong value, right slot. The
  `cell` path silently lacked the mid-run spec-edit invalidation that `replay`
  has. Found by review; no test could have seen it.
- **`CONTEXT.md` read from the target repo.** It is a *host* artifact — that is
  the entire reason §5.3 injects it rather than referencing it. Reading it from
  the repo under work happens to succeed when the repo is Saffron and fails for
  every other repo.

40. **A reviewer scoped to one task cannot see the seam between two.** Every
    defect *inside* a task was caught by that task's own review. Both Criticals
    lived in the wiring between tasks and were found only by the whole-branch
    pass. Scope at least one review to the joins.

### The boundary held, and that is the best news here

§2.1 claims onboarding a repository touches zero lines of the orchestrator.
Saffron was onboarded to itself and the claim was **measured, not asserted**:
`git diff --stat -- saffron/` empty, the policy parser accepting the repo's
`policy.yaml` unmodified, the whole toolchain in `.saffron/`. The one leak found
— core hardcoding a Python base image as *the* cell image — was real and is
fixed, and its inverse appeared immediately afterwards when a core probe started
requiring a Python interpreter inside every repo's image. Both are the same
mistake in opposite directions.

41. **A boundary leaks in both directions, and the second is harder to see.**
    Core learning a language is the obvious failure. Core *demanding* one of every
    repo is the same failure wearing the opposite clothes, and it looks like
    thoroughness — "probe what actually runs" is a better argument than the one it
    replaced. Core's own checks run on artifacts core owns.

### Method

Rev 7 read the document and found nine defects. Rev 8 found that rev 7's central
fix was not implementable on this machine. Rev 9 replayed real pull requests and
found the contract could not tell a tool that ran from one that didn't. Rev 10
ran a spike and measured a `--cpus` offset no document would have predicted. Rev
11 built the thing, and found that the security architecture six revisions had
argued for was, in the shipped code, applied to the wrong container.

The trend is not that documents are useless — every one of those revisions was
written against the previous document and could not have been written without it.
It is that **the defects a document can find are a different class from the
defects execution finds, and the second class is where the expensive ones live.**
Nothing left in this document is worth another read-through. The next artifact is
the agent session at §9's v0.5 seam, and after it, v1.

---

## Appendix J — rev 12: what the first live runs found

Appendix I recorded what building v0.5 found. This records what *running* it
found — four live agent sessions inside real cells, $2.47 total. The pattern from
rev 9 onward holds and sharpens: each artifact finds a class of defect the
previous one structurally could not.

### It works

`SA-0002` — implement the `size` core gate — run end to end, twice. The agent,
inside a cell with no target-repo credentials and no route but the proxy,
produced a plan that passed `validate_plan` on the first attempt, wrote
`saffron/gates/core/size.py` and `tests/test_size.py`, ran its own tests, watched
them fail, fixed them, ran the formatter, and committed. `commits_ahead` measured
the commit; the gate suite returned zero new failures against the baseline;
the run ended `READY_FOR_REVIEW`.

The code it wrote cites §2.1 and §5.4 for why `size` can be core, draws §5.6's
advisory/blocking line in the right place, and — for the spec types §5.4 gives no
ceiling for — defaults rather than returning `error`, reasoning that "`error`
means the gate itself broke." That is this document's most load-bearing
distinction, applied correctly by an agent that met it only through §5.3's
per-phase vocabulary injection. The injection works.

### The first run destroyed its own output

Teardown removed the worktree volume, and the commit ceased to exist — the mirror
had never heard of it, and the batch tree held only `plan.json` and
`baseline.json`. `worktree.export_patch()` was already written, and had no caller.

§0 says the product of this factory is **not code, it is a reviewable artifact**.
The run satisfied §9's success criterion and produced nothing anybody could read.

42. **A pipeline that verifies work and then discards it has not finished; it has
    failed expensively.** The last step of any producing stage is the one that
    makes the product outlive the machinery — and it is the step most easily
    mistaken for cleanup. §4.3 already said a bound firing must never discard
    committed work; teardown does the same thing on the *success* path, which is
    where nobody thinks to look.

The export now runs as the first statement of the `finally`, from every path that
produced commits — green, `EXHAUSTED`, budget-stopped, or raised. A task that
could not go green with commits in it is the most informative artifact the system
makes; exporting only the green ones would discard exactly the runs worth reading.

### Three things `allowed_tools` and its neighbours do not do

- **`allowed_tools` governs auto-approval, not availability.** With it set to
  `[]`, the live session offered the model all twenty-one built-in tools —
  `Task`, `CronCreate`, `ScheduleWakeup`, `SendMessage`, `WebFetch` among them.
  `dontAsk` denies the call, so the boundary holds, but §5.3's claim that omitting
  a tool "saves the turns spent discovering that" was false. The fix is a positive
  `tools` allowlist rather than a denylist: a denylist needs every name and stops
  protecting the moment the runtime grows one more, while an unrecognised name in
  an allowlist is dropped rather than granted. Twenty-one tools became six.
- **A target repo configured the agent working on it.** A planted
  `.claude/agents/` and `.claude/skills/` under `/work` both loaded into the
  session. `/work` is the tree the task edits, so a repo — or a previous
  attempt — could supply subagent definitions and skills to the agent reviewing
  it. `setting_sources: []` closes it.
- **The cost of that fix is §8's bucket 2.** Pinning `setting_sources` also stops
  the repo's `CLAUDE.md` loading, and `CLAUDE.md` is the flywheel's middle bucket
  and §2.1's named learning surface. It is inert until v1 injects it host-side
  from the mirror, the way `CONTEXT.md` already is — which is the right shape
  anyway, since a file under `/work` is rewritable mid-attempt.

43. **A configuration surface is an input, and every input from the workspace is a
    claim.** §5.3 established this for control artifacts the agent writes. The
    runtime's own configuration search path is the same hole one level lower: it
    is read before any of the harness's checks run, by machinery the harness does
    not own.

### A no-credential session reports `subtype: "success"`

Measured on the no-key path, before any real run: a cell whose agent cannot
authenticate returns `{"subtype": "success", "is_error": true,
"total_cost_usd": 0.0}`. Code keying on `subtype` — which the cost reconciliation
did, and which a review had approved — records a session that did nothing as a
clean $0 run. Unattended, that is a budget that stops counting. Both now key on
`is_error`.

This is principle 34's seventh disguise, and the cheapest one to have found: it
cost nothing, because it lives on the path you exercise when you have no money.

### The proxy allowlist and the diagram disagree

§2's diagram shows the egress proxy allowing `api.anthropic.com` **and a package
mirror**. The implementation allows one host, so `uv run`, `pip install` and
`npm install` all fail inside a cell. The implementation is the better answer —
§5.1 already requires services, fixtures and dependencies to bake in at *image
build* time, so a cell that needs a package index at run time is a repo that has
not finished onboarding. The diagram's package mirror is vestigial, exactly as
§2.1's "gate-runner shim" was: a component drawn in a design, never built, and
unnecessary once the surrounding decisions were made. Struck.

### The cost model was high

| | §7.1 estimate | Measured |
|---|---|---|
| Plan turn | *(inside Implement)* | ~$0.44 |
| Implement | $2–6 | $0.85 |
| Plan + Implement, total | $2–6 | **$1.01–1.29** |

Two runs of the same spec, one commit each, no repair attempts. Not enough data to
rewrite §7.1 — a task needing four repair attempts is the row that matters and has
not been run — but the first real numbers land under the estimate rather than over
it, which is the direction that lets `--budget 50` buy more nights than it was
sized for.

### What is still unproven

**The repair loop has never run.** Both live runs went green on attempt one, so
GATE ⇄ REPAIR — resuming a session with structured failures — remains untested
against a real model. So does no-progress detection, and so does the question of
whether `total_cost_usd` on a resumed session reports that turn's cost or the
whole session's, which decides whether the spend accounting over-counts. That is
the next thing worth paying for.

44. **The path that has never run is the one your estimate is about.** Two green
    runs measured the cheap half of a loop whose expensive half is the reason the
    loop exists. A cost model validated only on the happy path is a cost model of
    something else.

---

## Appendix K — rev 13: the factory produced plausible, verified, broken code

Three specs were run through v0.5 against a live model. All three went green on
the first attempt, produced a patch, and ended `READY_FOR_REVIEW`. One was then
applied and reviewed adversarially. The verdict was **do not merge**, on three
Critical defects.

This appendix is about that gap, because it is the whole argument of §0 and §5.5
arriving as evidence rather than as a claim.

### What passed

`SA-0004` — the `integrity` gate, 371 lines plus 579 lines of its own tests. It
passed `format`, `lint`, `types` and `tests`; its 31 new tests passed; the diff
stayed inside `touches`; the formatter was clean. Applied to the repository it
brought the test suite from 281 to 312 green.

The code was not slop. §2.1's split was clean — not one language token in a code
path, `test_paths` consulted for every classification, the Go-vocabulary tests
honest in both directions. `error` and `fail` were not blurred, and the test that
proves it is the right test to have written. Hunk consumption was count-driven
rather than marker-scanning, which is the non-obvious correct choice, with a
fixture containing diff-shaped content inside a test file to prove it. The
reviewer's own words: *"the code was close enough to correct that only actual git
output separates it."*

### What review found in under an hour

- **A diff containing `\ No newline at end of file` aborts the task.** The author
  knew about the marker — there is a branch for it — and put it in the one
  position git does not use, then wrote no test. Every task whose diff touches a
  file without a trailing newline dies as `GATE_ERROR`, unrepairable, with the
  agent never told why.
- **"An existing test was removed" was inferred from net line count.** Delete the
  failing test, write a comment longer than the test, and the gate is green —
  precisely the move §5.4 says this gate exists to stop, performed by the most
  natural thing an agent does when removing a test.
- **The same comparison fails a legitimate refactor.** Consolidating two tests
  into one `parametrize` shrinks the file and trips the gate. Blocking, with no
  override, so the loop's only repair is to pad the file — the gate teaching the
  gaming it was built to prevent.
- **The gate fails its own pull request**: sixteen violations on its own diff,
  because §5.4's "unless `touches` explicitly includes it" exemption was omitted.
- **The agent can disable the gate from inside the cell.** `export_patch` runs
  bare `git diff`, inheriting worktree config the agent can write. One
  `git config diff.srcPrefix x/` and a diff deleting the entire test suite reads
  as `pass`.

And of eleven mutants applied to the agent's own tests, **five survived**.

### Why the gates could not have caught any of it

Every one of those defects is invisible to `format`, `lint`, `types` and `tests`,
because the tests were written by the same author, against the same model of the
problem, carrying the same blind spots. The test suite is not evidence about the
behaviour anybody wanted; it is evidence that the code and its tests agree.

45. **A test written by the author of the code certifies agreement, not
    correctness.** Thirty-one passing tests and five surviving mutants are the
    same artifact described two ways. Mutation is the cheapest thing that tells
    them apart, and on agent-authored work it is not optional.

46. **Over-built for the rare case, under-built for the common one.** The parser
    handled quoted paths with spaces, binary bodies, octal escapes and mode
    changes — and mishandled the line git appends to almost every hunk. Exotica
    is visible and reads as rigour; the ordinary case is invisible because it is
    assumed. Ask of any parser: what does the *usual* input look like, and is
    there a test containing it?

47. **A proxy measure is gameable in exactly the direction the adversary wants.**
    Net lines removed stood in for "a test was removed". The adversary's move
    defeats it and a legitimate refactor trips it — wrong in both directions on
    one comparison, which is not a check but a biased coin. When a gate cannot
    measure the thing, the honest output is that it cannot, not a heuristic that
    resembles it.

### What this settles

§0 claims the product of this factory is not code but a reviewable artifact.
Three green runs and one review is the smallest experiment that could test that,
and the answer is unambiguous: **the gates were necessary and nowhere near
sufficient.** A hard-gate loop with a capable model produces work that is
plausible, internally consistent, self-tested, and wrong in ways only an
adversary looking for the wrongness will find.

§5.5's critic is therefore not a refinement to add once the loop is trustworthy.
It is the component that makes the loop's output mean anything, and v0.5's
success criterion — an agent fixing one real bug inside a cell — is met while the
factory's actual purpose is not.

48. **Gates verify what you thought to check; the critic exists for what you did
    not.** They are not two grades of one mechanism. Everything on the first list
    can be automated, and everything on the second is why the first is not enough.

### The repair loop did not fire, three times out of three

Across a new file, a schema change to code with existing tests, and a 371-line
parser, GATE ⇄ REPAIR never ran. The reason is structural rather than accidental:
**a capable agent with `Bash` runs every gate it can reach before committing.**
It ran the tests, watched them fail, fixed them, ran the formatter, and only then
committed — so the host's suite arrived after the agent had already done the
host's job.

The repair loop's real domain is therefore only the gates an agent *cannot*
self-check: the core ones, which read the host's view of the diff. That makes the
core gates the only gates that can ever fire, and it makes their absence from the
v0.5 suite — `scope` ran in no cell at all until this revision, `integrity` still
runs in none — the more serious gap of the two.

49. **A verification an agent can run itself is a verification it will have
    already passed.** Its value is not zero, but it is not caught-at-the-gate
    value; it is turns-saved value. Anything you need to *catch* has to be
    something the agent cannot see the answer to.

### Two smaller findings

**Patches perish.** `SA-0003`'s patch no longer applies: three hours of
subsequent commits moved `session.py` underneath it. A verified-green change has
a shelf life measured against the branch it was cut from, which is what §5.7's
rebase-and-re-verify and §6.1's merge train exist for, and v0.5 has neither.

**The measured cost model, three tasks in.** $1.29, $3.08 and $2.49 for plan plus
implement — against §7.1's $2–6 for implement alone. All three without a repair
attempt, so the row that matters remains unmeasured, and principle 44 still
stands.

---

## Appendix L — rev 14: the critic, measured against a known-bad diff

Appendix K argued from a single review that §5.5's critic is what makes the
loop's output mean anything. Rev 14 builds it and measures it, and the test was
available for free: `SA-0004`'s patch is a real agent-written change that passed
every gate and its own thirty-one tests, and that adversarial review rejected on
three Criticals — all written down before the critic existed.

So the critic's first live run had a ground truth. Nothing was tuned after seeing
its output.

### What it found

- **The net-line-count proxy, as a `blocker`** — the defect that defeats the
  gate's entire purpose, and the most important of K's three.
- **Two things K does not contain**, both true: the failure message hands the
  agent the evasion recipe, and no fixture covers the mixed case. K found the
  defect; the critic found why it stays exploitable.
- **§5.4's omitted `touches` exemption, as a `concern`** — reached from §5.2's
  ratified-spec commit rather than K's "the gate fails its own PR". Same defect,
  independent route.
- **Two more not in K at all**, correctly filed as `note`: an empty-file test
  deletion passing the gate, and an assertion no implementation could fail.
- **Missed**: the `\ No newline at end of file` abort, and the
  `git config diff.srcPrefix` escape — the latter squarely blast-radius, the
  third lens, deliberately not built because no risk tier is wired.

**Drop rate: 0% on both lenses.** Every finding anchored to a real changed line.
No hallucinations on the first honest run — which is the number §5.5's
reconciliation exists to protect, and the one most likely to be bad.

### What that settles, and what it does not

§5.5's design works. A critic given a bounded remit, a fresh session, read-only
tools and an instruction to find the reason a change should not merge produced
findings a careful adversarial review had missed, and produced no invented ones.

50. **A critic and a reviewer fail differently, and that is the argument for
    having both.** The machine critic caught what the human-equivalent review
    missed and missed what it caught. That is not redundancy with a weaker copy;
    it is two different failure surfaces over one diff. §5.5's disjoint lenses
    are the same idea one level down, and the same reasoning says a critic does
    not replace the operator — §11's "human, always" stands.

Two caveats, both volunteered by the implementation rather than found later:

**The lenses are not disjoint enough.** Both filed the `touches` finding, which
means their remits overlap on "code contradicts a written spec". §5.5's
no-voting rule rests on disjointness by construction — *"the schema critic will
never independently corroborate the correctness critic's timezone finding"* — so
an overlap is not a duplicate to deduplicate, it is a prompt defect.

51. **Two lenses reaching the same finding is a fact about the prompts, not about
    the finding.** It reads as corroboration, which is exactly what makes it
    dangerous: a system that treats agreement as evidence will be most confident
    where its lenses are least independent.

**The second lens ran on a smaller model** because $0.83 of budget remained. That
is a confound in every comparison above and it is stated rather than smoothed.

### Where a blocker goes

To REBUT, which §5.6 now describes in the order that ambiguity is settled in:
"confirmed" means anchored, and the critic's `verdict` answers the rebuttal
rather than preceding it. The phase is built and tested against fakes, and
**it has never run against a live model** — no rebuttal, no verdict, and no
gate re-run after a rebuttal has been measured. Appendix J's rule applies to it
exactly as it applied to the repair loop: the path that has never run is the one
your estimate is about.

---

## Appendix M — rev 15: what running the rejected gate found

Backlog item 1 said to read `SA-0004`'s rejected patch and its review before writing anything. Executing it as well took twenty minutes and returned three corrections, one of which nothing had recorded. Full record in `docs/evidence/2026-08-22-integrity-rejected-gate-measured.md`.

**The batch tree holds a later patch than the one Appendix K reviewed.** `rebuttal.json` records `head_moved: true`: the implementer changed the removal check during REBUT and the lens withdrew its blocker. Appendix K describes the code as applied and reviewed; the export is one fix past it. Both are honest about different artifacts, which is the shelf-life problem of Appendix K's own "patches perish" note arriving in a second form.

- **The `\ No newline at end of file` defect is already fixed.** All four positions git emits the marker parse cleanly. The backlog line claiming a branch sits in the wrong place is struck.
- **The removal check is run adjacency, not net line count.** So the `parametrize` false positive is gone — and the evasion is *cheaper* than Appendix K says, not harder. Not a comment longer than the test: one adjacent added line of any content, because the gate never asks what the added line says.
- **The suppression scan fails this repository's own merges.** Substring matching over every added line in every file means prose containing a token fails. `d1141d0`, the merge of PR #5, returns `fail` on two docstrings that quote `@pytest.mark.skip` while explaining that a critic's claim routinely quotes it. This is also what the "sixteen violations on its own pull request" were.

52. **When a check keeps needing a better heuristic, the question is in the wrong coordinate system.** Three rewrites of "was a test removed?" against diff text produced three different wrong answers, because the diff does not contain the answer — it contains a shadow of it. The set of collected tests contains it exactly, and comparing two sets needs no heuristic at all. The tell is not that a heuristic is imperfect; it is that each repair moves the failure somewhere else rather than shrinking it.

The corollary is the cheaper half: **the data a core gate needs may already be in a result it is holding.** Item 1 assumed test-set comparison required `revert`'s §2.1 exception — core invoking the repo's `tests` gate twice more. It did not. The baseline and head suites already run `tests`; the names needed reporting, not fetching, and the whole exception dissolved into one optional field.

---

## Appendix N — rev 16: what pinning the base and the gate runner found

Backlog items 11 and 12 are the same question asked twice — what tree is a task
about, and who is allowed to have written the thing that judges it. Twelve tasks
closed both. Most of what follows is in neither item, and the three sharpest
findings were reached by reading rather than by running.

### `github_slug` was wrong in more ways than item 11 says, twice over

Item 11 describes a two-segment-GitHub-URL problem. Measured before any code was
written, three of five real inputs returned a wrong answer rather than refusing:

| Input | Old result |
|---|---|
| `/Users/joel/Code/saffron` | `Code/saffron` |
| `git@gitlab.com:group/owner/repo.git` | `owner/repo` — leading segment dropped |
| `https://example.com/repo` | `example.com/repo` — the **host** as the owner |

The last shape is not in the backlog at all. With one path segment the pattern
takes the host as the owner, so a remote that is not a forge still yields a
plausible `owner/repo` and `gh` is handed a repository that cannot exist.

**Then the first fix was still wrong, and review caught it.** The tightened
pattern matched `github.com` preceded by any of `^ @ / .`, which does not
distinguish a URL scheme from a filesystem path separator. Measured:
`slug('/Users/joel/go/src/github.com/owner/repo')` returned `owner/repo` — a
GOPATH-style checkout walking straight through the refusal the change existed to
add. Worse, twelve fixtures had by then been relocated to
`tmp_path/github.com/o/r.git` to satisfy that same pattern, so the test suite had come
to depend on the loophole. The shipped pattern anchors on a real remote URL — a
scheme, or the SCP-like `user@host:` form — and is measured against 19 cases:
nine accept, ten refuse, including `https://github.com.evil.com/a/b`, which
nobody had considered.

**A port is accepted, but only in the scheme form.** `ssh://git@github.com:22/o/r.git`
is a real remote and the `:22` is a port; in `git@github.com:1234/repo.git` the
colon introduces the path and `1234` is an owner. One pattern cannot read the
colon both ways, so the branch it sits in decides.

**The narrowing is real, and it is wider than "unreachable".** Measured against
the old pattern, two shapes returned a *correct* slug before this change and are
refused now: a GitHub Enterprise host (`git@github.example.com:owner/repo.git` →
`owner/repo`), and an SSH `Host` alias standing in for github.com
(`git@github-work:owner/repo.git` → `owner/repo`). Because `cli._run_cell` reads
the slug for its refusal (§5.7), such a repo can no longer start a cell at all.
Accepted rather than fixed: the slug is handed to `gh pr create --repo owner/repo`,
which resolves against `gh`'s own default host, so accepting any host is worse than
refusing — `git@gitlab.com:owner/repo.git` would open a pull request on the wrong
forge. GHE is the one shape where the old behaviour was right, and carrying it
properly means plumbing the host through to `GH_HOST`, which nothing here does.
A repo on either shape must point `origin` at github.com to run.

53. **A refusal that is loosened to make tests pass is a refusal that no longer
    exists.** The tell is not that the pattern is imperfect — it is that the
    repair reshapes a *fixture* rather than a caller. Twelve fixtures moved to a
    path shape no real checkout has, and after that the test suite was evidence for
    the loophole rather than against it.

### The baseline and head suites could run different gate executables

The baseline suite runs in the same cell and the same worktree as head, before
the agent starts. So the baseline ran the base tree's gates and head ran whatever
gates were in `/work` by then, and a task editing its own `tests` gate changed
what the two subtracted sides mean. That is suite drift by construction — the
identical shape item 11 flags for `reverify`'s missing `thread_env` — and pinning
gates to `base_sha` closes it as a side effect. **This is the stronger of the two
reasons for pinning, and it is not why item 12 was written.** Nothing had
recorded it; §5.4's `tool` field would have reported it after the fact, on a task
that had already spent its attempts.

### `reverify` was a second copy of the whole seam

It has its own cell, its own `prepare_worktree` call, and its own
`gate_executables(WORKTREE_MOUNT)`. Updating only the supervisor would have left
the two suites `reverify` subtracts coming from different executables —
reintroducing the finding above in the one place §5.7 already flags for drift —
and a required `gates_dir` argument would have broken PACKAGE at runtime.
Invisible to `make check`, because the tests covering that path are cell-marked
and excluded by default. Found by reading, not by running.

54. **A control applied at one call site is not applied; it is applied at one
    call site.** The question a boundary change has to answer is not "does the
    new path use it" but "how many paths are there" — and where the second path
    is exercised only by tests the default run excludes, green is not evidence.

### Item 11 overstated the ledger defect by half

`branch` was already written at insert time by `create_task`, fed from
`spec.branch`. Only `pushed_sha` was missing, written solely by
`set_task_package` after `open_draft_pr`. One column, not two — and the fix is
correspondingly smaller than the item's account of it.

### Three smaller ones

- **A path-lifetime hazard the plan walked into.** The first draft put
  `reverify`'s exported gates under the package scratch directory — which
  `add_worktree` hands to `shutil.rmtree` and which the `finally` hands to
  `remove_worktree`. Gates written there have the worktree's lifetime. The
  shipped path is a sibling, and `Spec.id`'s `^[A-Za-z0-9]+-[0-9]+$` pattern is
  what makes `<id>-gates` unable to collide with another spec's scratch dir.
- **`git status --porcelain -z` emits `RM`, not `R `, for a staged rename that
  was also modified**, so the rename skip tests `"R" in entry[:2]` rather than
  `entry[:1] == "R"`. Mutation-checked: removing the skip leaks `"xt"` — the tail
  of `a.txt`, sliced by `entry[3:]` — into the dirty-path list, which would then
  be reported to the agent as a path to commit.
- **`cell_env` would have put a credential in a gate-only cell.** The obvious way
  to give `reverify` its `thread_env` is the call the session cell uses, and that
  call injects `CLAUDE_CODE_OAUTH_TOKEN`. `reverify` has no proxy and an
  `--internal` network with no egress; it takes `dict(policy.thread_env)`
  instead. §5.1's one-credential exception is narrow enough that a convenience
  helper can widen it without anybody deciding to.

### The dirty-tree rule needed no new control flow, and the terminal state does not prove it

`committed` is a gate, so a dirty tree gets the repair turn the loop already
gives every `fail`, and a second identical look is the no-progress rule. Verified
by mutation: dropping the no-progress branch yields three repair turns and four
attempts instead of one and two — but `state` is `EXHAUSTED` either way, because
§3.3 deliberately maps no-progress and exhausted to one state. Only the call
count and the attempt count discriminate.

55. **Where two outcomes deliberately share a state, that state cannot be the
    assertion.** A test asserting the terminal state alone passes against the
    regression it was written to catch, and reads as coverage while providing
    none. The collapse is usually correct — the operator does not need the
    distinction — which is exactly why the test has to look somewhere else.

### Deferred, for the record

`out_dir/package/<id>-gates` and `task_dir/gates` are new batch-tree artifacts
with no manifest entry and no cleanup; nothing enumerates those directories
today, and `saffron gc` (§4.5) is v1 work. The `real_remote` → `github_slug`
composition inside `package()` is no longer covered end to end — both fixture
sites monkeypatch the slug — against a regex that is far better covered in
isolation. And the empty-head guard in the default-branch fetch is untested:
constructing a successful fetch with an empty `FETCH_HEAD` against real git is
harder than the guard is worth.

---

## Appendix O — rev 18: the operational question

`SA-0001` shipped and answered the question it was asked. Five queries, five SQL wins, don't build the emitter (`ontology/RATIONALE.md`). That verdict stands, and Appendix B principle 10 is what it is an instance of.

It also raised a different question, which the RATIONALE did not test and cannot settle: **the queries were the analytical case for the ontology. Is there an operational one?**

### What makes it worth asking now

Three things, none of which existed when §1.4 was written.

- **The vocabulary found three defects in this document.** `size` blocking at the wrong tier (Appendix B), `gate_results` and `findings` being one assertion shape (§4.6), and — building it — that `CONTEXT.md` §6 and §3.3 closed the terminal-state set two different ways while `session.py` wrote a tenth state neither called terminal, `tasks.state` closes nothing at all, and `attempts.phase` holds states rather than phases. A modelling exercise that keeps finding real defects is producing something, whatever the queries say.
- **`ontology/` is now a gated surface.** The `shacl` gate makes the shapes operational *as a gate*, which is the weakest useful sense of the word and is already built. Nothing in §1.4 forbids it: the shapes validate an artifact, not a state transition.
- **Prior art.** Zhang et al., *Toward Effective and Reliable LLM Agents via Dynamic Ontology* (arXiv 2608.22974), whose framework is called OaK — ontology-as-a-kernel — builds a task ontology as an executable kernel and reports gains on three agent benchmarks. Its load-bearing sentence is architecturally ours: *"Once frozen, the kernel is the only channel through which the agent reaches the data. It cannot name a concept or invoke a computation the kernel does not declare."* That is §2's line, reached from the effectiveness side rather than the isolation side.

### The two positions

**For.** The control plane's rules are currently Python that runs and prose that does not. A declarative form makes them inspectable, checkable against each other, and testable without executing a scheduler. The conflict set, `elevate_on`, the terminal-state distinction and the refusal predicate (§4.2.1) are all set containment, and set containment is what shapes are for.

**Against, and it is the stronger half.** Saffron already has an enforceable contract between the model and what it may do, and it is not made of triples: the gate contract, `allowed_tools`, the proxy allowlist, `touches` and the `scope` gate. OaK's kernel is a *reimplementation* of that boundary for agents that lack one. Re-expressing controls that already work, in a language with no runtime here, buys inspectability and costs a second source of truth — and §4.6's first rule exists because divergence in an audit trail is worse than either store alone.

There is also a cost that has to be stated rather than discovered: **an ontology that controls execution needs the emitter the RATIONALE said not to build.** That is not incoherent — it would be built for a reason the RATIONALE never tested — but the reason must be the new one, argued on its own evidence, and not the analytics case arriving through a side door.

### What full SDLC coverage would take, measured

Extending the vocabulary to the whole of `CONTEXT.md` means roughly thirty terms — cell, container, cell runtime, worktree, mirror, batch tree, index, queue line, conflict set, extraction turn, plan checkpoint, refusal, no-progress, anchored, merge train, preflight, bucket, promote — that no query or shape reads, and that no §4.1 table projects from. Under the dead-term test they are deleted; without it the ontology is the isomorphic re-encoding §4.6 exists to forbid, one level up, re-encoding a glossary rather than a schema. **Coverage is downstream of this decision, not independent of it.** Decided one way the terms acquire readers; decided the other they are decoration, and the dead-term test is right to say so.

### The decision, and when it gets made

Not by argument. §1.4's bullet **stands for v1**, and this appendix is what reopens it — the same shape as Appendix G, which named a product only after a spike returned four assertions.

The cheap experiment is available and does not exist yet: §4.2.1's scheduler is decided in full and unbuilt, and its refusal predicate is pure set containment. Build it twice — once as the Python `intake` already needs, once as shapes over a hand-authored graph of in-flight tasks — and compare:

1. Does the shape form state a refusal the Python form leaves implicit?
2. Does either catch a case the other misses, on the same fixtures?
3. What does the graph cost to keep current, per scheduled task?
4. Can the shape form be read by someone who has not read the Python?

A yes on 1 and 4 with an acceptable 3 reopens §1.4. Anything else closes it, and `ontology/` stays what §9's v2.5 already says it is: a completed project.

56. **A negative result answers the question it tested, and no other.** `SA-0001` proved the queries were not worth an emitter. It proved nothing about whether the vocabulary is worth executing, because it never asked — and the honest response to "then let's make it operational" is a different experiment, not a re-reading of the first one.
