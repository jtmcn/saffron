# Saffron — System Design

An agentic software factory: spec files in, reviewed pull requests out, running unattended overnight on one Mac.

**Status:** rev 25: **a refusal reaches only as far as its reason**. The appendices moved into `docs/appendices/` as records with their letters intact. This document keeps §0 to §11 and two indexes rendered from them (Appendix U, principle 62). Prior: rev 24: **a check that runs only on fixtures verifies the check, not the subject**. N5's derivation-chain query ran only against hand-authored graphs, so no merged change was ever its subject. The emitter is reopened on `ontology/RATIONALE.md`'s own revisit clause, under a decision rule stated before the run (Appendix T, principle 61). §1.4 is untouched: no scheduling decision reads a triple. Prior: rev 23 — **a threshold that names one cause is read as naming the only cause**. `CLAUDE.md`'s ~200-line budget named one remedy, promote to a gate. The overflow it kept firing on was reference the tree already states (Appendix S, principle 60). §8 orders the cut. Prior: rev 22, **a style rule limits growth, and never exempts a whole file**. Saffron's own prose now has a blocking `prose` gate and an advisory `terms` gate (Appendix R, principle 59). No file can gain hits of any rule, and existing prose stays as written. Prior: rev 21, **the verdict of record leaves the implementer's container.** The final gate suite and every critic lens ran in the container the implementer had spent the repair loop in as root. PACKAGE's re-verification, the one check outside it, was skipped on an unmoved base as "provably redundant". It now re-verifies every packaged commit, and the lenses move to a critic cell rebuilt from the exported patch (§5.4 to §5.7, Appendix Q, principle 58). `SA-0086` to `SA-0089` build it. Prior: rev 20 — the vocabulary covers the design record as well as the run record. `CONTEXT.md` §11 named the genres a decision here is written in and nothing carried them; `factory:Principle` and `factory:RevisionAppendix` now do, with shapes as their readers and `DESIGN.md`'s generated principle index as the surface that renders from them (Appendix P). What §9's v2.5 closed is **the emitter** — the ledger→RDF projection — and it is deferred rather than finished: `ontology/RATIONALE.md` carries its own revisit clause and it will be asked again. "`ontology/` is a completed project" was shorthand for that verdict plus Appendix O's, and it read as a third and wider decision neither of them made — principle 57. §1.4 is untouched: no shape controls execution, and the design record projects from no §4.1 table. Prior: rev 19 — the vocabulary is authoritative for the run record's closed sets and generates them: `CONTEXT.md`'s enumerations and the shapes' `sh:in` lists render from `ontology/factory.ttl`, so a set declared in one place reaches all three (§4.6). Two shape lists stay hand-maintained because the vocabulary cannot imply them — `CoreGateBlockingShape`'s blocking levels and `TaskShape`'s `endedInState` superset — and a test names the file when one is forgotten. **And Appendix O's spike ran and closed §1.4.** The refusal predicate built as shapes against the Python answered *no* on questions 1 and 4, so §1.4's bullet stands and no scheduling decision reads a triple. (Rev 20 narrows what that sentence originally claimed: it said `ontology/` was a completed project, which is not what either verdict decided.) Two corrections landed with it — the appendix's premise that the predicate is "pure set containment" is wrong, four of its eight refusals being glob matching; and the spike's own first claim that glob matching is inexpressible in SHACL was false and is retracted (Appendix O *The result*, `docs/evidence/2026-09-04-refusal-predicate-two-arms.md`). A fourth defect the modelling found: `MERGE_TRAIN` is a state §3.3 shows a task entering and `scheduler.py` reads twice, and it is in neither `CONTEXT.md` nor the vocabulary. Prior: rev 18 `SA-0001` built and answered: five queries, five SQL equivalents, don't build the emitter (`ontology/RATIONALE.md`). The vocabulary is gated by `shacl` and cross-checked against `CONTEXT.md`'s closed sets; the *operational* question the RATIONALE never tested is stated in Appendix O and left to a spike, and §1.4's bullet stands until that spike runs. Prior: rev 17 the first night's scheduler decided against the queue that exists rather than the deep one §4.2 is written for (§4.2.1), and §6's ranking corrected against the real ledger after it sorted a sustained blocker last (`docs/evidence/2026-08-25-morning-queue-from-real-rows.md`). Prior: rev 16 the tree a task is cut from and the executables that judge it are both host-supplied, closing the two trust boundaries backlog items 11 and 12 left open (Appendix N). Prior: rev 15 the cell moved off the API key onto a Claude Code subscription token, and the ceiling reasoning corrected against a measured run (`docs/evidence/2026-08-21-subscription-turn-accounting.md`, Appendix M); rev 14 the critic built and measured against a known-bad diff (Appendix L); rev 13 three tasks run, one reviewed, and the review said no (Appendix K); rev 12 v0.5 run against a live model (Appendix J); rev 11 v0.5 built and reviewed (Appendix I); rev 10 the cell runtime chosen by spike (Appendix G); rev 2 post adversarial review (Appendix A); rev 3 factory ontology (Appendix B); rev 4 repo-agnostic (Appendix C); rev 5 prior art (Appendix D); rev 6 vocabulary corrections (Appendix E); rev 7 read-through defects (Appendix F); rev 8 cell runtime named (Appendix G); rev 9 v0 built and replayed (Appendix H)

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
- An ontology-*driven* orchestrator. The factory ontology (§4.6) **describes** the run record; it never controls execution. SHACL shapes validate the projection; they do not gate state transitions, and no scheduling decision reads a triple. (Stands for v1, and the spike that would have reopened it has now run and did not: Appendix O's rule closed the question on 2026-09-04, `docs/evidence/2026-09-04-refusal-predicate-two-arms.md`.)
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
forbidden:                      # denied at the plan checkpoint and by `scope` — below
  - alembic/versions/**
budget_usd: 12                  # best-effort; the enforceable ceiling is the batch's (§4.2.1)
max_attempts: 4
max_turns: 60                   # per-turn ceiling; the flags override all three
risk: standard                  # standard | elevated (§5.6)
---

**`budget_usd` is a best-effort bound, and saying so here is backlog item 44's decision rather than an apology.** The supervisor gates each attempt on what has been spent *so far*, and an attempt's cost is not knowable until it ends — nothing caps it but `max_turns` times the per-turn cap — so a task admitted under its ceiling can finish over it by up to one whole attempt. Measured at 67% on `SA-0059`: $26.75 against a $16 ceiling, the last attempt admitted at $12.64 and costing $14.11 by itself (`docs/evidence/2026-09-06-an-attempt-is-the-overshoot-bound.md`). The 6.5% this paragraph used to cite, on `SA-0031`, was one turn's overshoot — a true measurement of the wrong unit (backlog item 73). Charging a worst-case estimate instead would mean *guessing* the bound, which is the defect item 56 argues against for size predicates and is worse here: a guess that refuses a legitimate attempt costs more than the overshoot it prevents. **The enforceable ceiling is the batch's, checked between tasks** (§4.2.1), because between tasks nothing is mid-flight — which is exactly why a bound holds there and cannot inside a turn. Strictly the batch's bound is best-effort too, since it admits a task on that task's *declared* ceiling: a night can end at most one task's overshoot above its budget. Bounded by one overshoot rather than unbounded is the whole distinction. Unattended, one task running $10.75 over is not the exposure; a night spending unboundedly is.

**`forbidden` and `protected` bind both the plan and the diff, and this paragraph has been wrong in each direction once.** It said they bound the diff until `SA-0011` leaned on it; it said they bound only the plan until `SA-0024` closed that. Three places read them now: `agents/artifacts.py` rejects a plan whose *declared* `files_to_change` matches one, `agents/context.py` prints them into the prompt, and the `scope` gate (§5.4) fails any changed file matching either — independently of `touches`, under its own `forbidden` and `protected` failure codes.

The gap this used to leave was narrow and real: a `touches` broad enough to contain a `forbidden` path (`touches: ["saffron/**"]`, `forbidden: ["saffron/cell/**"]`) passed `scope`, and nothing else looked — a plan that declared the edit was caught, a plan that did not was not. `SA-0024` closed it, for the reason `integrity`'s exemption paragraph (§5.4) reasons about the same shape: **a check that fires on a declaration is not a check that fires on a diff.**

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
  GATE_ERROR       ◀── a gate errored, the two suites drifted, or the critic cell
                       met a binary stub the export cannot carry: infrastructure,
                       and never charged to the task (§5.4, §5.5)
  SCOPE_REVIEW     ◀── also from IMPLEMENTING: an implementer whose declared
                       `touches` cannot satisfy the criteria proposes a set
                       instead of writing a plan, and the proposal ends the
                       attempt (§5.3.1)
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
tasks        (task_id, run_id, spec_id, spec_sha, state, risk, branch, policy_sha,
              prompt_sha, parent_task_id, worktree, volume, budget_usd,
              spent_usd_est, updated_at)
attempts     (attempt_id, task_id, phase, n, session_id, model, started_at,
              ended_at, subtype, terminal_reason, num_turns, cost_usd_est)
gate_results (gate_result_id, attempt_id, run_id, gate, status, tool,
              duration_ms, summary)
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

`prompt_sha` is a digest of `saffron/agents/prompts/**` as authored, the third input beside `spec_sha` and `policy_sha`. `attempts.model` is writable through `close_attempt`. No call site supplies a value yet.

Artifacts — transcripts, diffs, gate logs, coverage XML — go in a **plain directory tree**, not a content-addressed store:

```
~/.saffron/batches/<batch_id>/<repo>/<task_id>/<phase>/<n>.{log.gz,json,diff}
```

Content addressing would dedupe repeated gate output, but the volume is tens of MB a night. A plain tree is greppable with `rg`, inspectable when the ledger itself is what's broken, and navigable at 7am without a tool. Dedupe you don't need is not worth losing `ls`.

### 4.2 Scheduler

Selects the next runnable task when a cell frees:

0. **Refusal gate — decided before a cell starts, and it is the cheapest gate in the system.** A task is refused outright, with a reason, if: an open unmerged PR from **another task** already targets this spec; its `touches` overlaps an open PR's changed files; the spec is malformed or its `spec_sha` moved; or the repo failed preflight. Refusals cost nothing — no container, no tokens — and land in the morning queue as one line. The instinct is to let the agent discover these and report back; that instinct costs $8 to learn something a `gh pr list` call knew for free. **Every condition you can check without starting a cell, check without starting a cell.**
   > *Another* task, because a `CHANGES_REQUESTED` task re-queues (§3.3) while its own PR is still open — the unqualified version refuses every re-queued task in the system, which is the one case this gate is most obviously not for. Refusal is keyed on `task_id`, not on the spec.
1. **Dependency gate** — all `depends_on` tasks have reached **`READY_FOR_REVIEW`** (not `MERGED`). A dependent task branches off its parent's branch rather than `base_sha` — stacked branches. Built by `SA-0022` (the cell's second base), `SA-0025` (PACKAGE's parent branch) and `SA-0026` (the resolver and the widened gate); K=1, so only the first `depends_on` entry is a stacking candidate.
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

**Built, 2026-09-04.** Everything this section specifies now exists: `batches` and `runs.batch_id` in `ledger.py` with their writers (`create_batch`, `close_batch`, `attach_run_to_batch`, `batch_spend`, `batch_runs`), `tasks.policy_sha`, `check_readiness` in `preflight.py`, the loop in `batch.py`, the shared scan in `cli._resolve_queue`, and the command in `cli._batch`. The paragraphs below are written as design and now read as description; they are left in that voice deliberately, because each one argues for a decision the code makes and the argument is what a reader needs. Where a sentence says something "does not exist", read it as the state this section was written against. **What is still deferred is named as deferred and remains so:** `saffron gc` (§4.5), `tasks.priority`, K > 1, and every piece of gate 3's reserved-budget machinery.

Everything above is the scheduler once the queue is deep. This is what v1 builds, decided against the queue that actually exists: two or three specs, ~45–60 min a task, an eight-hour window (§7.1). **Every piece cut below arbitrates contention, and at this depth there is none to arbitrate** — §4.2's own rule about second implementations, turned on the scheduler itself rather than on one of its gates. Each cut names the night it comes back.

**Input — the specs at `base_sha`, filtered by what the ledger already knows.** A batch scans `.saffron/specs/*.md` from the export `export_saffron_dir` already takes at the run's pinned `base_sha`; `specs/` arrives free because that export was deliberately made the whole directory rather than `gates/` alone (§5.4). Not the working copy, and this is a new member of the family item 13 assembled — gates at `base_sha`, the policy declaring them at `base_sha`, PACKAGE's policy at `fetch_head`, the cell image from the working copy (§5.1). A spec joins the first group, and the friction is the point: **a spec on a branch is a draft, and the factory owing you work on an unlanded draft is the wrong default when nobody is awake.** It also closes the loop where a task could rewrite the queue that schedules it.

**The scan resolves to a task, not to a spec, and that is load-bearing rather than pedantic.** A spec with a task at this `spec_sha` in a re-queueing state **resumes that task row**; a spec with no such task gets a new one. Minting a fresh task per queued spec looks equivalent and is not: gate 0 refuses a task when an open unmerged PR *from another task* already targets the spec, and §4.2's footnote is explicit that this survives a `CHANGES_REQUESTED` re-queue only because **refusal is keyed on `task_id`, not on the spec**. A new task row at the same `spec_sha` is "another task" by its own id, so a spec-keyed scan admits the re-queue and gate 0 refuses it on the PR it was sent back to fix. The same root would discard a ratified `SCOPE_REVIEW` `touches`, which lives on the task, and send the bug back through DIAGNOSE.

**The filter is stated negatively and keyed on `spec_sha`.** A spec is queued unless it has a task **at this `spec_sha`** in a state that is *done with it*: `READY_FOR_REVIEW`, `APPROVED`, `MERGE_TRAIN`, `MERGED`, `MERGE_FAILED`, `REJECTED`, `EXHAUSTED`, `NOT_IMPLEMENTED`, `PLAN_REJECTED`, `SCOPE_REVIEW`. It re-queues on `CHANGES_REQUESTED`, `RATE_LIMITED`, `GATE_ERROR`, `PREFLIGHT_FAILED` and `ORPHANED`. The rule underneath is one line — **re-queue when nothing was learned about the spec** — and it is what makes the list derivable rather than memorized. The positive form, "has a task at this `spec_sha`", is the one to reject: §3.3 sends `CHANGES_REQUESTED` back to the queue against an unchanged spec, so it refuses the one case the re-queue arrow exists for. **Dropping the key instead of the form is the other wrong fix**, and it costs the edit case: unscoped, a `REJECTED` spec you then rewrite is never queued again. `EXHAUSTED` stays out for the reason from the third side — something *was* learned, and running it again learns it twice. `MERGE_FAILED` likewise: it reaches you (§3.3) with a branch and an open PR, and a fresh task tonight would duplicate work and trip gate 0.

> **The in-flight states are not on either list, and the scan must not treat that as "queue it".** `DRAFT`, `QUEUED`, `DIAGNOSING`, `IMPLEMENTING`, `GATING`, `REPAIRING`, `REVIEWING` and `REBUTTING` at scan time mean a corpse: one batch runs at a time, so nothing is legitimately in flight when a scan happens. `ORPHANED` covers only the deaths the supervisor stamped (§4.5) — a host power cut leaves the task in `IMPLEMENTING`. **The scan stamps any in-flight task `ORPHANED` before filtering**, which is §4.3's reconcile step doing the job it is already named for, and the task then re-queues by the ordinary rule.

**`depends_on` is refused unless the parent has already shipped, and at gate 0 rather than at intake.** `Spec` parsed it, nothing scheduled it, and `SA-0007` declared it and was sequenced by hand — an instance of the pattern item 18 named, where a field that parses and validates and changes nothing is indistinguishable from one that works. The tempting middle path is to honour it as ordering only, topologically sorting inside the batch without stacking branches. **That is not a smaller version of the feature; it is a version that lies.** Without stacking the child branches off `base_sha`, so the parent's changes are not in its tree, and it builds against code that does not exist yet and fails its own gates. But the refusal belongs in the refusal gate, not in `parse_spec`: `SA-0006` and `SA-0007` both carry the field today, so raising at parse regresses `saffron cell` on two specs in this repo, and an exception mid-scan has no defined handling while a refusal has one — a reason, and one line in the morning queue (§6). `SA-0020` then narrowed the refusal to what needs no stacking. A parent whose work is already in the default branch admits its dependent, because a child cut from `base_sha` does have that parent's commits: a task recorded `MERGED`, or a spec the operator retired to `.saffron/specs/done/` as shipped. The second exists because **only a cell writes a task**, so work done by hand leaves no row the ledger could be asked about, and in a repo where humans and cells both commit "has the parent shipped" and "did a cell run it" are different questions. `SA-0022`, `SA-0025` and `SA-0026` then built the stacking those two admissions were standing in for, and the narrowing is gone: a parent at `READY_FOR_REVIEW`, `APPROVED` or `MERGE_TRAIN` admits its dependent too, and the dependent is cut from that parent's branch rather than `base_sha`. What is still refused is a parent that will not merge as it stands (`DEPENDENCY_DEAD_STATES`) or has no task at its current `spec_sha` at all, and the reason names the state it actually read — including `done/` itself: a retired spec that no longer parses declares no id, credits nothing, and gets its own line in the morning queue, because a child refused for a parent sitting in `done/` is the one refusal an operator cannot act on.

> Item 18 counts five instances and declines to number a sixth. This is the sixth, and #27 called it the fifth — the miscount is worth correcting precisely because the pattern's value is in the count.

**The refusal gate refuses eight things, and the fifth is the only one with a corpse behind it.** §4.2's four stand as written, `depends_on` is the sixth, `SA-0023`'s is the seventh — a spec whose own `touches` are protected paths, refused before the cell rather than after the plan checkpoint has spent its budget — and `SA-0027`'s is the eighth, which belongs beside the fifth rather than at the end: both refuse *a path named that no `touches` pattern reaches*, read from two different sources — an acceptance criterion in the one case, a `saffron:retired-by` marker in the repository in the other. This count has now been wrong by one twice, each time within a release of being corrected; backlog item 48 is the standing item for the reader that would notice a ninth. The fifth is: **a spec whose acceptance criteria name a path that no `touches` pattern matches.** Item 18 measured that such a spec is unsatisfiable by construction — `SA-0005` burned $5.34 and died at turn 61 because its criteria reached `cli.py` and `package.py` while its `touches` did not, so the implementer could not have satisfied them without failing `scope`, and one finding was dropped as unanchorable for the same reason. The adjudication was that **the fault was the spec's, not the implementer's**, and nothing in intake checked for it.

Two things that condition has to get right, and the obvious statement of it gets both wrong:

- **It matches globs, not strings.** `touches` is glob-matched everywhere it is enforced — `scope.matches`, and `integrity` and `size` both reuse that function so that "declared" means one thing in every gate. A criterion naming `saffron/gates/core/size.py` against `touches: ["saffron/gates/core/**"]` string-compares to no match, and a false refusal at gate 0 costs a whole spec overnight with no cell started and nothing to notice until morning.
- **It is skipped when `touches` is empty.** That is the documented shape for a bug awaiting DIAGNOSE (§5.2), and every criterion names a path outside an empty list — so the unguarded form refuses the entire bug class before the phase that would populate `touches` can run. §4.2 already carves bugs out of gate 0's overlap test for exactly this reason, and like gates 0 and 2, this one **re-runs at ratification** against the ratified set.

**Preflight is what a task already does, hoisted, plus two.** `_run_cell` today does the mirror fetch, the origin refusal and the default-branch pin per task; a batch does them once per run. Added: `load_policy` validation, and an auth check. **The auth check is not hygiene — it guards a measured landmine.** Appendix J found that a cell whose agent cannot authenticate returns `subtype: "success"`, `is_error: true`, `total_cost_usd: 0.0`; unattended, an expired token at 22:00 produces a night of clean-looking nothing against a budget that never counts down. Deferred: `saffron gc` (§4.5), because K=1 means `--until` kills at most one cell and the leak is one volume a night rather than three. **The disk-headroom check is not deferred with it, and the pairing is the whole point.** §4.5's endgame is *"two weeks and the disk is full — and preflight would detect it and abort, which is detection without reclamation."* K divides the leak rate; with gc deferred the accumulation is still unbounded, so dropping the detection as well turns a warned failure into a silent one.

**K = 1, and the scheduler is a `for` loop over a sorted list.** §4.2's arithmetic sets K=3 against memory, and that arithmetic is not wrong — it is just answering a question a three-deep queue does not ask. Three tasks at 45–60 minutes is three hours of an eight-hour night, so concurrency buys idle time rather than throughput. What it costs is the whole of gate 3's reserved-budget machinery, which exists **only** to stop K tasks passing the budget gate on the same last $12; at K=1 that race cannot occur and the gate is one comparison before each task. Ordering is priority then FIFO, sorted once in memory.

> K becomes real the first night the *wall clock* ends the batch rather than the queue. That night is also the first evidence about which of §7.1's three disagreeing numbers was right, so it is worth waiting for rather than guessing past.

**A batch ends four ways, and says which.** The queue drains, the budget is gone, `--until` hits, or the breaker fires. No task-count ceiling: it is a proxy for spend, and spend is measured directly. **A fifth reason, `INCOMPLETE`, says the night left a task in flight**: a task came back mid-phase, having reached no end state. This was measured on `SA-0057`, where a provider error during REBUT drained the night at exit `0` (backlog item 70). It outranks `DRAINED`, `BUDGET` and `UNTIL`, because which ordinary limit came first matters less than a task nobody can account for, and `INFRASTRUCTURE` outranks it. The breaker does not count it: the next scan stamps the task `ORPHANED` and requeues it, and two provider blips must not end a night that would have recovered.

**The breaker counts two consecutive aborts, and what counts as an abort is enumerated rather than implied.** A task exiting `2` is infrastructure, charged to nobody (§5.4), so it is recorded and stepped over — but two in a row stops the batch, because two in a row is a broken host and the remaining tasks will each burn a preflight and a baseline suite to learn the same thing. The states that count: `GATE_ERROR`, `PREFLIGHT_FAILED`, and **`RATE_LIMITED`**. The last is not exit `2` and is not infrastructure, but it fails the same way — a provider ceiling hit at 22:05 lets every remaining task start a cell and run a baseline suite (minutes, §7.1) before dying of the same global condition. N2 says the retry is free, so the queue re-queues intact tomorrow (§5.1). **The counter resets on any state a task *earned*** — anything else in §3.3, up to and including `EXHAUSTED`. Saying "any terminal state" would be a bug rather than a shorthand: §3.3 lists `GATE_ERROR` and `PREFLIGHT_FAILED` among the terminal states that reach you, so the counter would reset on the very aborts it counts and never reach two.

**Schema: `batches` gets built, `tasks.priority` does not.** §4.1 declares both and neither exists. They are not the same call. The batch's window and its stop reason have to survive for §6's morning queue to render the night, so `batches` lands as `(batch_id, started_at, ended_at, budget_usd, spent_usd_est, until_ts, status)` with `runs.batch_id` beside it; `status` carries `DRAINED`, `BUDGET`, `UNTIL`, `INFRASTRUCTURE` or `INCOMPLETE`, one per stop condition above. `concurrency` waits for K to have a second position. Priority is different: it is read exactly once, at scan, to sort a list already in memory. **A column written at scan and read by nobody would be item 18's pattern wearing a schema instead of a dataclass** — the repo has produced six of those and one of them cost a task. It gets added the first night something reads it back.

**The command, and what is missing from it deliberately:**

```
saffron batch --repo . --budget 50 --until 06:30
```

No `--repos`, because multi-repo is v2 (§9). No `--concurrency`, because **a flag for a knob with one position is the same defect in a CLI that item 18 found in a spec.** `--repo` defaults to the working directory, matching `saffron cell`. `--until` takes `HH:MM` and resolves to the next occurrence. `--budget` defaults to 50, which is §7.1's own recommendation and is sized against the queue rather than against capacity.

**Exit codes, and why `1` is reserved rather than reused.** A batch is not a task, so `cell`'s codes do not carry over: `0` for `DRAINED`, `BUDGET` and `UNTIL`, `2` for `INFRASTRUCTURE`, for `INCOMPLETE`, and for a preflight failure that takes the whole batch. Never `1`. **A batch that drains with three failed tasks did its job** — individual outcomes are the morning queue's business, and letting `1` mean anything here would quietly merge two vocabularies that answer different questions. `INCOMPLETE` is not the exception it looks like: a task left in flight has no outcome for the morning queue to read, so the night is the only place that can say it happened.

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

**2. PROV-O and EARL, not a bespoke schema.** Batches, runs, tasks, attempts, phases, gate suites and a contested finding's rebuttal are `prov:Activity` — one activity per suite and not one per gate, because a gate's own execution is already fully described by the assertion it produces: `gate_results` carries its status and its `duration_ms`, and a separate activity node would restate them; specs, `plan.json`, `scope.json`, diffs, gate output and PRs are `prov:Entity`; the implementer session, each critic lens, every gate, the human and the human's delegates (`CONTEXT.md` §1) are `prov:Agent` — a gate is one because an assertion needs an assertor. `wasGeneratedBy`, `used`, `wasDerivedFrom`, `wasRevisionOf` and `wasInvalidatedBy` (which is exactly what `spec_sha` invalidation is, §4.1) carry the backbone. Gate results and critic findings are both `earl:Assertion`s over an `earl:TestSubject`. The genuinely Saffron-specific terms — the only part that justifies a new namespace — are the gate taxonomy with its blocking/advisory split, `envelope` versus ratified `touches`, lens disjointness, and the terminal-versus-internal state distinction of §3.3.

**2b. The cheap rival the RATIONALE must also beat: a glossary.** Prior art (Appendix D) reaches the same need — a shared vocabulary its agents must read before touching code — and answers it with a 200-line markdown glossary where every term carries an explicit ***Avoid:*** list of the words not to use for it, plus an instruction to *flag* a conflict with a recorded decision rather than silently override it. That is a weekend's less work than an ontology and it does the thing an ontology is usually reached for. So `RATIONALE.md` has a second bar to clear: not only "is SPARQL better than SQL here," but "**is any of this better than a disambiguating glossary the agents actually read?**" If the honest answer is that the vocabulary's value is agent-facing rather than query-facing, write `GLOSSARY.md` and stop — the queries were the justification, and without them the RDF is decoration. Worth noting that Saffron needs the glossary either way; the ontology has to earn the *delta*.

**3. Provisional by construction.** The deliverable includes `ontology/RATIONALE.md`, which challenges each of five queries against its SQL equivalent over the §4.1 schema. **"All five have easy SQL equivalents — don't build the emitter" is a successful outcome**, and is the cheapest form that answer can take. The vocabulary is a design artifact validated against hand-authored fixtures; the emitter and the store are a separate, conditional task (§9, v2.5).

Rule 3 is the important one, and it is §9's build-order discipline applied to a data model: prove the layer is worth having before building the machinery that feeds it. A vocabulary costs a weekend and can be deleted. An always-on materialization pipeline cannot.

#### What the modelling already surfaced

Two schema criticisms that stand whether or not a single triple is ever stored:

- **`gate_results` and `findings` are the same thing wearing different table names.** A type error and a critic blocker against an acceptance criterion are both *an assertion, by an agent, about a subject, with an outcome*. EARL says that in one shape. The SQL schema splits them because gates are deterministic and critics are not — which is a fact about how the assertion was *produced*, not about what it *is*. The PR body already renders them into one table, which is the tell. Worth reconciling in §4.1.
- **A rebuttal is not a string.** §5.6 records implementer/critic disagreement across `verdict`, `adjudication` and `rebuttal`. Modelled as a `prov:qualifiedAssociation` the disagreement becomes a node carrying role, plan and time — which is what makes "blockers per lens, split by whether the operator agreed" answerable at all. *(Both landed with the vocabulary: the typed `adjudication` field in rev 6, and `factory:Rebuttal` as the activity carrying the three judgements as `prov:Association`s, which is what `Q2-blockers-per-lens.rq` reads.)*

That is the ontology earning its keep before it ships: writing down what an *attempt* is in relation to a *gate result* produced two design corrections, not two triples.

#### The trap it must avoid

An isomorphic re-encoding of §4.1 — one class per table, one datatype property per column, one object property per foreign key. That is a mechanical transform (it is what W3C Direct Mapping does), it passes Turtle parsing and shape validation, and it is worth nothing, because anything expressible over it was already expressible in SQL. A term earns its place by delivering **alignment** (external PROV tooling works on it), **qualification** (a relationship becomes a node that carries role and time), or **an axiom the relational schema cannot state** (disjointness, set containment across rows). `rdfs:comment` prose proves none of these — prose is the part that is cheap to fake.

`SA-0001` enforces this mechanically with a dead-term test: every term in the `factory:` namespace must be referenced by at least one committed query or one shape, or it is deleted rather than commented. That check rides the existing blocking `tests` gate; it is not a new repo gate.

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

**A second runtime exists, and it is a second safety argument rather than a port.** `podman` runs where `apple/container` cannot and where Appendix G's Architecture A is not on offer either — a container-hosted Linux runner has no daemon and no way to start one, and podman needs none. It keeps three of the four grounds the spike decided on: an honest CPU count, an internal network, `--cap-drop ALL`. **What it gives up is the per-cell VM, which Appendix G called the single largest point in `apple/container`'s favour.** So the paragraph above stops applying to it, in both directions: with no private kernel to offer instead, `no-new-privileges` comes back on and seccomp's default filter is relied on rather than waived. The trade is stated here rather than absorbed, because a runtime swapped in silently swaps the boundary with it.

**Rootful podman is refused outright, and a night does not run on podman at all yet.** No image sets a `USER`, so a cell runs as root; with no user namespace that is root on the host kernel, and the three flags above are all that stand between the untrusted cell and a host holding the `gh` credential PACKAGE pushes with. Rootless podman maps it to an unprivileged user, so the supervisor asks the binary itself (`podman info`) before its first network or container and refuses anything else. And until a cell has started on podman end to end — the one measured host refused `DEFAULT_SUBNET` — `saffron batch` refuses it; attended `saffron cell` does not.

**Which runtime runs is declared and never detected,** for the reason Appendix G's principle 32 gives about proper nouns: a supervisor that picks its boundary from what is on `PATH` has made the safety argument a property of the machine, and the two runtimes do not offer the same boundary. `SAFFRON_CELL_RUNTIME` names it; an unknown name is an error, never a fallback, because a fallback reports one runtime's calibration for another and `CPU_OFFSET` wrong by one surfaces as flaky gate timings rather than as a failure.

**The CPU requirement is met less completely there, and `policy.thread_env` is what closes the gap.** A per-cell VM *has* N CPUs, so every API agrees. A shared kernel can only narrow the affinity mask: measured, `--cpuset-cpus 0-1` leaves `nproc` reporting 2 while `os.cpu_count()` and `/proc/cpuinfo` both still report the host's 4 (`docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md`). A BLAS sizing itself from `sysconf` therefore oversubscribes exactly as this section warns — so under a VM-per-cell runtime the repo-declared `thread_env` is belt and braces, and under a shared-kernel one it is *the* control. A repo onboarded onto such a host that declares none has an uncapped thread pool, and that is a difference in what a gate result means, not merely in how fast it is.

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

### 5.1.2 The image is the toolchain, so where it came from is part of the record

The cell image carries the toolchain every gate executes against (§5.1), which
makes it the one input a gate result is not meaningful without. Two hosts whose images differ are two
hosts whose `tests` results are not comparable, and nothing in a gate result
says so.

**`FROM` is therefore an argument, and the default is the measurement.**
`images/cell-base.python.Dockerfile` is `FROM python:3.12-slim-bookworm` and
that is what this project is built and measured against; `BASE_IMAGE` changes
nothing for a host that can pull it. (The default path does change, on purpose:
three variables point pip, requests and uv at the system CA store and
`update-ca-certificates` runs, which a host behind a TLS-terminating proxy
needs; the provenance file below is written; the build refuses a base whose
Python is not 3.12; and `.saffron/Dockerfile` takes uv from pypi at a pinned
version rather than from a registry at `latest`.) What the argument buys is a host that
cannot: an egress policy that refuses every container registry still permits an
apt mirror and pypi, which between them supply every layer above the base —
measured, including the SDK wheel's bundled Claude Code binary, which is the
whole reason that image is glibc rather than musl. `images/bootstrap-base.sh`
builds such a base from `debootstrap` alone.

**A base built that way is not the same toolchain, and the image says so
itself.** Both images write a provenance file — distribution, interpreter, git,
SDK, and the agent binary's own version string — and every line of it is
obtained by *running* the tool rather than by restating the argument the build
was given (principle 39, and the same rule as a gate's `tool` field in §5.4). A
bootstrapped base records `ubuntu 24.04` where the default records `debian 12`,
so the difference is legible instead of silent. **Read it before trusting one
host's gate result against another's** — that is the whole reason it exists.

**What this deliberately does not do is make the two equal.** A base resolved
from an apt mirror at the moment it runs is reproducible only to the day it was
built. The durable answer is one image built once and carried between hosts as
an OCI archive — `save` on the host that can pull, `load` on the host that
cannot — and the provenance file is what verifies it arrived intact. That is
worth doing before a second host's results are compared to the first's, and it
is not what a `BASE_IMAGE` argument achieves on its own.

### 5.2 Phase 1 — DIAGNOSE (bug specs only; the scope proposal is not)

Read-only tools, scoped to `envelope`. Output is `scope.json`: the proposed `touches` set, the identified root cause, and the evidence for it.

This phase exists because of a specific trap. The obvious design — human declares `touches`, agent is confined to it — is sound for features and fatal for bugs. In the TE-0142 example, "no rows from any of three providers" most plausibly originates *outside* `ingest/nws/**`: a shared HTTP retry helper, a Polars schema change producing a silently empty frame, a continuous-aggregate refresh policy, a chunk-interval/retention interaction, a migration that changed a constraint. Several of those are in `forbidden` or outside a hand-written `touches`. The agent would correctly find the cause and then be auto-rejected for looking in the right place — and the rejection would read as "your spec needs work," which is both wrong and unactionable.

So: the agent proposes scope, you ratify. **Everything from `SCOPE_REVIEW` onward is the phase-independent half of this contract** — §5.3.1 gives IMPLEMENT the same door on any spec type, and the ratification, the writeback and the rules below are identical whichever phase proposed. `SCOPE_REVIEW` items appear at the top of the morning queue as a diff of proposed `touches` plus the one-paragraph root cause — a genuine 10-second decision, versus a rewrite-the-spec-and-lose-a-night loop. Ratified scope is recorded in the ledger, and written into the spec file **on the task's own branch, as its first commit** — so it reaches `main` through the task's normal PR and needs no exception to N1's rule that nothing unattended writes to a remote `main`. **The task's own spec path is added to the ratified `touches` when it is recorded**, or that first commit fails the `scope` gate on every ratified task: the writeback changes `.saffron/specs/…`, which is not a path DIAGNOSE would ever propose. Since `SA-0024` that is necessary and no longer sufficient — the deny lists do not consult `touches`, so a repo whose spec directory is `protected` (this one is) needs the recorded spec path exempted from them too, and nothing does that yet. A control artifact that has to be committed has to be in scope to be committed. Two further things fall out, both load-bearing. The ledger is authoritative until that PR merges, so enforcement starts at turn one of IMPLEMENT rather than next batch. And `spec_sha` on `main` deliberately does *not* move while the task is in flight — writing the spec back to `main` directly would invalidate (§4.1) the very task that ratification just unblocked.

Cost: ~$0.30–1.00. Cheapest possible place to catch a misconceived task.

### 5.3 Phase 2 — IMPLEMENT (with a plan checkpoint)

Full write tools inside `/work`, with an explicit list of the tools that **exist**, an explicit list of those callable without a prompt, and a permission mode that **cannot prompt**.

**Those first two are different options and only one of them withholds anything.** `allowed_tools` governs auto-approval, not availability: measured live, a session that named six tools there was offered all twenty-one built-ins the runtime had — `Task`, `WebFetch`, `WebSearch`, `SendMessage`, `Workflow`, `Cron*`, `ScheduleWakeup`. `dontAsk` denied the ones outside the list, so the boundary held, but the model spent context seeing them and turns attempting them, which is the entire saving the list was written to produce. `tools` is the option that decides what exists, and it is a positive allowlist: a name the runtime does not recognise is dropped rather than granted, so the list can only fail closed. Restated generally, because it is the same shape as the hooks warning below: **a control that denies an action and a control that removes it are not interchangeable, and only the second one saves the turn.**

That second requirement is easy to miss and fatal to get wrong. The obvious mode auto-accepts file *edits* — which covers Edit and Write and nothing else. A shell command outside `allowed_tools` still raises a permission prompt, and at 03:00 inside a container there is nobody to answer it: the attempt burns its idle timeout (§4.3) and reads as a stall. **Unattended operation requires a mode whose behaviour on an unapproved tool is to deny, not to ask.** The runtime offers one; it also offers a mode that skips permission checks entirely, which is the wrong fix — it removes the wasted-turn savings along with the prompt, and buys nothing safety-wise since the real controls are structural anyway (§2).

The general form, because it will recur with every runtime option: **in an unattended system, "ask the operator" is not a fallback, it is a hang.** Any option whose failure mode is a prompt needs its non-interactive equivalent chosen deliberately.

**Configuration is loaded from nowhere.** `setting_sources` is pinned to `[]`. Its default loads project settings from the working directory, and the working directory is `/work` — the target repo's checkout, a tree the task itself can edit. Measured with a planted `.claude/`: an agent definition and a skill in `/work` both reached the agent Saffron was running *on that repo*, which for self-hosting means Saffron's own `.claude/` configures its own factory. Every instruction the agent gets is composed host-side and injected (§5.3); nothing is read from the tree under work. The pin also stops the repo's `CLAUDE.md` loading, so the host injects it instead: read from the mirror at `base_sha`, never from the tree the agent can rewrite, and substituted as a value like the spec body. IMPLEMENT receives it, and the sessions that resume IMPLEMENT inherit it; every fresh session — the three review lenses and the verdict lenses — receives it too, because a critic judging a diff against invariants it was never shown is judging against nothing.

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

### 5.3.1 The scope proposal — IMPLEMENT's door out of an impossible spec

A non-bug spec's `touches` is declared by hand, and a hand-written set can be wrong in a way no amount of implementation effort repairs: a criterion asks for behaviour that lives in a file the set does not cover. The plan checkpoint above rejects that plan correctly and cheaply — but rejection is *all* it does. The task ends there, at `PLAN_REJECTED`, which reaches you reading "your spec needs work" about a spec that is as good as it can be, and §4.2.1 does not re-queue it. The alternative the implementer has without this door is worse: keep the plan inside `touches`, and grind every repair attempt to a ceiling having learned nothing the spec did not already say. The exact case §5.2 was built for on bugs, arriving one phase later on everything else. So the implementer gets the same door: **before writing a plan, it may reply with a scope proposal instead**, naming the paths the criteria actually need and the root cause that makes the declared set insufficient.

Three rules keep it a door rather than an escape hatch:

- **The proposal ends the attempt.** No plan, no diff, no commit — the task goes to `SCOPE_REVIEW` and waits for you. A proposal that left the session running would be a negotiation, and an agent that can negotiate its own scope mid-attempt will open one whenever the work turns hard.
- **It must name a path outside the declared `touches`.** A proposal naming only paths already declared is refused rather than recorded: that is a restatement of the spec, not a finding about it. The implementer gets one further turn — exactly one — to submit either a real plan or a proposal that genuinely reaches outside; refusing twice ends the attempt as a rejected plan. An empty `touches` always escapes this check, since there is nothing yet to be outside of.
- **The task's own spec path is added host-side**, exactly as in §5.2, and the ratified set is a **superset** of the declared `touches` rather than a replacement. The prompt asks for paths "inside or outside" the declared set, and a prompt is not the boundary — so the union is taken host-side where it is one.

What follows the proposal is §5.2's contract unchanged: the same state, the same one-click ratification, the same writeback on the task's own branch. Only the producer differs, which is why the rules live there and only the door lives here.

**The door is at the plan checkpoint and nowhere else**, and a `ponytail:` in `cell/session.py` names that ceiling: a `touches` insufficiency the implementer discovers mid-diff, after the plan was accepted, still has no exit and still burns to a ceiling. This subsection describes an opening at the start of the phase, not a standing right to renegotiate scope during it.

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
| `scope` | **core** | yes | changed files ⊆ `touches`, and matching neither `forbidden` nor `protected` |
| `size` | **core** | at `elevated` | diff lines ≤ type ceiling (bug 300 / feature 600 / refactor 1000); `error` where it blocks and a file inside `touches` is hidden as binary — a `-diff` attribute otherwise counts 0 and passes any ceiling |
| `secrets` | **core** | yes | credential scan over the diff |
| `integrity` | **core**, repo patterns | yes | test-tampering check (below) |
| `census` | **core** | yes | collected test names at `base_sha` vs head (below) |
| `committed` | **core** | yes | the worktree is clean at gate time (below) |
| `criteria` | **core** | yes | each declared witness ran and turned green at head, and was not already green at `base_sha` (below) |
| `revert` | core logic, repo runner | yes | new tests must fail without the source files (below) |
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

`when` is **declared and not yet read**: `repos/policy.py` parses it and `run_suite` runs every declared gate regardless, so a conditional gate today runs unconditionally. Saffron's own `shacl` gate is declared without it for that reason (backlog item 19).

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

**A skipped test is still a collected test.** Measured: `pytest -q --collect-only` lists a `@pytest.mark.skip` or `xfail` test and the run exits `0`, so `census` does not see marker-based silencing and is not the gate that covers it — `integrity` is. Only `-m` deselection removes a name, and that is an edit to gate configuration rather than a marker. What `census` catches is removal and rename-out-of-collection; a test still collected but silenced belongs to `integrity`, and a test still collected but gutted belongs to `revert`, built by `SA-0044`.

**`committed` — the tree the gates measure is the tree the patch contains.** `git status --porcelain` inside the cell, read **after** the declared suite on the baseline call and the head call alike — an artifact a gate itself writes (`.coverage`, a build dir) then appears on both sides, where the baseline subtraction can cancel it. Reading before the suite saw a clean baseline and only head's leftovers, and burned the repair turn on paths the agent never touched. The cancellation is by identity, so it reaches only artifacts whose paths match on both sides; a repo whose `.gitignore` does not cover its build output still owes `committed` a failure it cannot repair. The gates exec against `/work` while `export_patch` diffs `base_sha..HEAD`, so **any** uncommitted change is absent from `scope`, from `integrity` and from the packaged patch while being fully live for every gate result. An uncommitted edit to the gate itself is only the sharpest instance; an uncommitted edit to any source file changes what the suite measures while the patch a human reads does not contain it. Non-empty status is `fail`, one failure per path — never `error`: a dirty tree is the attempt's problem, not infrastructure's, and an `error` would abort the attempt and be charged to nobody.

**It needed no new control flow, which is the argument for it being a gate rather than a check.** A `fail` gets the repair turn the loop already gives every failing gate — commit your work — and a second identical look is the no-progress rule (below) ending the attempt. One turn is worth its cost because this is an honest mistake a capable agent will make at least once before the prompt is tuned, and burning an attempt on it teaches nothing. Low disruption otherwise: §4.3 already measures doneness from commits, so an uncommitted tree at gate time was already a mistake.

**What none of this buys, stated so it is not discovered.** A **committed** `conftest.py` whose `pytest_collection_modifyitems` drops a test only when `config.option.collectonly` is false still defeats `census`: enumeration reports a name the run never executes, `census` passes because the name is collected, `tests` passes because the test never ran. Core cannot catch it — collection happens inside the repo's own Python, and "what is a collection hook" is language knowledge §2.1 keeps out. The narrowing is repo-shaped and costs one line of YAML: `**/conftest.py` in `gate_config` makes `integrity` fail any diff touching that file unless `touches` declares it. It does not stop the lie; it routes the lie to a person, which is all a diff-shaped layer was ever going to do.

Three more routes reach the same place, each measured against real git with the exact flags `worktree._git` passes. **`.git/info/exclude`**: an agent appends `conftest.py` to it, and `git status --porcelain -z -uall` and `git diff base..HEAD` both come back empty — the file is invisible to `dirty_paths` and to the patch while fully live for pytest. `DIFF_FLAGS` pins `git config` values (as `diff.srcPrefix`); this one is not a config value, so no `-c` override closes it. **`git update-index --assume-unchanged <file>`**, then rewrite the file: `git status --porcelain -z -uall` stays empty while the modified test runs live; `git ls-files -v` reports the file with a lowercase `h`, which is the cheap detection if it is ever wanted. **The in-cell toolchain is writable**: `images/cell-base.python.Dockerfile` sets no `USER` and `worktree.py` passes no `user=`, so the cell runs as root and `/opt/venv` — pytest itself — can be patched.

**`census` buys exactness against an honest suite; the gate source and `committed` buy visibility against a dishonest one. Neither buys integrity, and no diff-shaped check will.**

**So the verdict of record is not the cell's.** Every gate above executes from the read-only `/gates` mount. Every one of them still calls its toolchain from the cell's writable rootfs, and reads the tree through the cell's own `git`: the executable is pinned, and what it runs on is not. Backlog items 2, 89, 102 and 103 each closed one route one flag at a time, and the next route is the next item. The class closes where §5.7 re-verifies: in a gate-only cell the implementer never ran in, on a commit host git built from the exported patch (Appendix Q). The suites the repair loop runs stay in the implementer's cell. Their results are feedback the agent needs, and a claim the host does not publish.

**`criteria` — every acceptance criterion is prose, and an unchecked one is indistinguishable from a met one.** A spec's criteria were rendered into the PR body as `- [ ]`, unticked, always, for every criterion, with no host-side component anywhere that asked whether one was met. That is §5.4's founding `tool` defect one layer up, in the layer that decides whether a pull request is merged: the artifact an operator reads to decide looks identical whether the work was verified or nobody looked.

A criterion may therefore declare a **witness** — a test node id, in an optional `acceptance:` frontmatter block alongside the `claim` the PR body renders. What a ticked box then means, exactly: *a test by this name ran at head and passed, and if it existed at base it was not green there.* It does not mean the criterion was met; the witness's body is out of reach, which is `revert`'s question and not this one.

**It reads two gate results and invokes nothing** — `census`'s route, and the cheaper question §2.1's seam asks before reaching for `revert`'s exception. Both suites already ran: *did witness W pass on this side?* is `W ∈ collected` and `W ∉ {f.code}`, two lists the host is already holding. The cost is one contract obligation parallel to `collected` itself — a `tests` gate must key its failures on node ids — and where it does not, `criteria` reports `skip`.

**How core knows the field carries node ids, without parsing one.** A name is opaque, so a gate that recognises `::` has learned a language. The whole test is set membership: **a side is readable iff its failures list is empty, or some `failures[].code` appears in that side's `collected`.** Failures present and disjoint from the enumeration mean the runner keys failures on something else, and that side is `skip`. This is measured, not hypothetical: this repo's own `tests` gate reaches node ids only through a fallback that runs when a regex over the whole output matched nothing, and one printed `path:N: word: message` line inside a failing test satisfies that regex — every node id vanishes from the field for that run. Without the membership guard the naive rule reads *W was collected and W ∉ {"error"}* and reports `pass` for a witness that failed. A ticked box over a red test is this gate's own defect, reintroduced by the gate that closes it.

**The direction is the load-bearing part.** A criterion claiming the change *did* something must name a witness that did **not** pass at `base_sha` and passes at head — one already green proves nothing about this change. `preserves: true` claims the opposite and is checked the opposite way, green at both sides. A witness absent from `collected(base)` because the diff adds it is the ordinary new-criterion shape and produces no `error` anywhere, so the baseline suite (§4.4) is unaffected.

**`skip` is not a failure and is the common case**, and the PR body says which kind of unticked a box is: where no gate result stands behind the checklist it renders as *not mechanically checked*, because an unticked box meaning *nobody looked* must not render identically to one meaning *the witness failed*. Reaching for a default witness would be worse than skipping — a criterion checked against an invented test is the defect this gate exists to close, wearing the fix's clothes.

**What it cannot see.** A **vacuous** witness: a new test is absent from `collected(base)`, so "did not pass at base" is free, and `def test_w(): assert True` satisfies everything expressible here. `revert` closes that case; nothing here does. A **flaky** witness that happened to fail at base makes a no-op criterion read as met — the rule has no repetition or quarantine, unlike baseline subtraction, which tolerates flakes by cancelling them. A **refactor** spec has no behaviour change, so every criterion is `preserves` and the rule yields no signal for that spec type. And a witness that exists at base and is modified by the diff is judged on its name, not its body.

**`revert` — the anti-theater gate, and the best cost/value ratio in the system.** Revert the source files of the diff, keep the test files, run only the new tests, and require them to **fail**. `SA-0044` shipped it file-level rather than hunk-level, which its own `ponytail:` names: a file that is half test and half source is reverted whole or not at all. One extra test run. This is the one place core reaches into the repo's toolchain, and it is why the contract requires the `tests` gate to accept a **test-subset argument** — the single most constraining line in the whole contract, and worth the constraint: every serious test runner supports it, and without it this gate degrades to a full-suite run per attempt. It mechanically answers the question critic lens #3 would otherwise be asked to reason about: does this test actually detect the thing it claims to? It catches deleted assertions, `assert result is not None`, and tests that pass identically on `main`.

This replaces mutation testing, which was the obvious choice and doesn't fit: `mutmut` reruns the test suite per mutant, a Timescale-backed suite takes minutes per run, and 15 mutants is an hour inside a 2-core cell competing with two siblings inside an 8-hour window that also has to fit 10–15 tasks. It would break N3 outright.

**`coverage` is advisory, deliberately — and at every risk tier.** Blocking on changed-line coverage generates exactly the behavior `integrity` exists to prevent: the cheapest way to satisfy it is a test that *executes* new lines without asserting on them. It also misfires structurally here — `except` branches for provider timeouts, `if TYPE_CHECKING`, defensive gap handling, and pure refactors where every changed line is a moved line. Report it in the PR body; block on `tests` and `revert`.

> Through rev 6, §5.6 made `coverage` blocking at `risk: elevated`, contradicting the paragraph above. Resolved in favour of the paragraph, and the reasoning generalizes: **an argument against a gate does not weaken as risk rises, it inverts.** Elevated risk is where a gamed gate does the most damage, so it is the last place to switch on the one gate whose cheapest satisfaction is theater. This is the same defect Appendix B caught in `size`, living in the same sentence, and it survived one revision longer because only half of the sentence was fixed.

**`revert` generalizes past code, which is a useful test of a spec.** `SA-0001` produces a vocabulary, not a program, and the gate still bites: reverting "the source files" means removing `factory.ttl` and the shapes, after which the shape and query tests must fail. Tests that pass against an empty graph get caught. Any artifact with an executable claim about it — a schema, a config, an ontology — is checkable this way. The corollary is a cheap smell test when writing a spec: *if you cannot say what reverting it should break, your acceptance criteria are prose.*

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

#### 5.4.1 The `witness` gate — an acceptance claim that nothing guards

**Added 2026-09-05, on measurement** (backlog item 69). Nine tests
shipped in one session naming a behaviour they did not guard. Each passed every
gate, all three lenses including `adequacy`, and a human read; each was found by
running a mutation. Two were written by review agents and one by the operator's
own session while fixing the others.

**The premise.** A vacuous test and a sound one are textually identical — nobody
writes a test intending it not to guard, so intent, naming and structure all
read correct. Vacuity is not a property of the test's text; it is a property of
how the *pair* responds to perturbation. Reading examines one object while the
defect lives in the relation between two, which is why §5.5.1's lens cannot
answer this and says so in its own prompt.

**The spec may not disclose its own mutant.** A mutant is only evidence if the
implementer has not read it. The spec body *is* prompt text — `build_system_prompt`
substitutes it as `{spec}` — and so is every claim, which `witnesses_block` hands
the implementer and `criteria_section` hands the critic. So `parse_spec` refuses a
mutant whose `find` text appears in the body or in any claim, before a cell starts
(backlog item 82; measured on `SA-0063`, which dictated the heading its
own mutant pinned and produced this repo's first `witness` verdict — sound
evidence the mechanism works and none that the tests were honest). The refusal is
a policy one: the spec parsed, so it keeps its id and a retirement to `done/`
still credits its dependents. It follows that a mutant pins text the existing code
already determines, and a spec creating new code declares a witness and no mutant,
accepting a `skip` — a real limit on the answer this gate gives, not a rule of
thumb. This is a tripwire and not a boundary: paraphrase evades it, and item 80
notes the cell can read the spec file itself.

**What the gate does.** A spec's `acceptance:` already pairs a claim with the
witness that guards it. Each entry may additionally declare a **mutant**: the
smallest edit that breaks the claim while leaving the code syntactically whole.
For each such entry the gate applies the mutant to the head tree, invokes the
repo's declared `tests` gate over **exactly that one witness**, and requires the
result to be `fail`. A mutant the witness survives is the finding: the claim is
asserted by nothing.

**It is `revert`'s exception, not a new one** (§2.1). The gate executes no tool:
it applies a text edit the *spec* supplied and then invokes a gate the repo
already declared, through the same JSON contract, with the subset argument
`revert` established. Core still knows nothing about the toolchain — only that a
`tests` gate exists and that the contract obliges it to accept a subset. Any
future core gate wanting to run something must fit that shape or move to the
repo side.

**Why the spec declares the mutant rather than an agent generating it.** A cell
is untrusted, and a mutant it authored is a mutant chosen to be killed. The
operator writes the spec, and the claim and the edit that breaks it are one
thought — §5.5.1 already asks the lens to name that edit in prose, so the
naming exists and nothing runs it. The cost is real and lands where it belongs:
writing a claim now means saying what would falsify it.

**Reversion is at hunk granularity and cannot reach this.** `revert` (§5.4)
stashes whole files and asks whether the new tests test *anything*. Scaling it
down to hunks does not help: a diff that adds a function has one hunk, and
reverting it kills every test trivially while the token-level property inside it
goes unmeasured. All nine of the above live below hunk granularity. **`revert`
asks whether the tests test anything; `adequacy` asks whether they test each
thing and cannot run; this asks the same question and can.**

**A mutant that does not apply is named, never silently skipped.** The gate
reports `skip` for a criterion whose `find` text is absent or matches more than
once, and the result *names* every such criterion. A check that quietly buys
nothing is the defect one level up, and it is the failure mode Appendix I is
about.

**A gate that mutates the tree guards itself against a dirty one.** `witness`
runs inside the declared suite and `committed` runs after it
(`saffron/gates/suite.py`) — deliberately, because `committed` must see what the
gates leave behind (§5.4). So the file a mutant targets may carry uncommitted
work, and `source_mutated` refuses one that is not at `HEAD`, landing on `skip`
the way `revert` does; a failed write restores from `HEAD` before it re-raises.
Any future gate that edits the tree owes the same guard, since `committed` will
not have run yet. `SA-0062` specified the opposite order and passed review
(backlog item 78).

**Blocking level.** Advisory at `standard`, blocking at `elevated` — the level
`size` already carries, and for the same reason: an elevated diff is one where a
plausible-looking wrong change hurts most, and a claim guarded by nothing is
exactly that. A spec declaring no mutants reports `skip`, so this cannot fail a
task retroactively.

### 5.5 Phase 4 — REVIEW (adversarial)

Fresh session, read-only tools, different system prompt, ideally a different model or effort level. It never sees the implementer's transcript. It sees the spec, the diff, the gate results, the acceptance criteria, and the repo's
`CLAUDE.md` at `base_sha` (§5.3).

Its instruction is not "review this code":

> Find the reason this change should not be merged. Assume it is subtly wrong. The gates passed, so the defect is not something the gates check — look for what gates cannot see: an acceptance criterion technically satisfied but not actually met; a fix that treats a symptom; behavior change outside the stated scope; an assumption about the data that holds in fixtures but not in production. Report only findings you can point at a specific line for. **If you cannot find a real defect, say so — do not manufacture one.**

That last clause is not politeness. A critic prompted to find problems will always find problems, and you'll spend your mornings adjudicating invented ones.

**Findings are reconciled against the diff before they count.** The critic emits `file` and `line` per finding; the host drops any finding it cannot anchor, and logs the drop. An unanchorable finding is either a hallucination or a complaint about pre-existing code, and neither belongs in a queue that is supposed to be about *this change*. Same move as measuring doneness from git (§4.3): treat agent output as claims, reconcile against a host-computed fact set. Perhaps twenty lines of code, and it is the difference between a critic you read and a critic you learn to skim.

**Anchoring admits two targets, not one, and the second exists for lens #3.** The rule was written for blast radius, §5.5.1's retired #3, which is asked *what else calls this* — so its best findings point at lines the diff never touched: an unupdated caller, a missing migration, a serializer left behind. **The rule outlived the lens rather than lapsing with it:** test adequacy also cites code the diff did not touch, because the test that should have caught the change is often one that already existed. A hunk-only rule discards most of what that lens is for, and the drop-rate diagnostic below would then read as a prompting defect when the reconciler is what is wrong. So a finding anchors if its file and line fall **inside a diff hunk**, *or* if that line **mentions an identifier the diff added, removed or renamed**. The second test is deliberately crude — tokenize the changed lines on word boundaries, intersect with the tokens on the cited line, no language knowledge anywhere — and crude is enough, because anchoring only ever had to establish that a finding points at real code with a real connection to this change. Everything else is still dropped and still counted.

> The general lesson, because it will recur: **a reconciler tuned to one producer silently disables another.** The hunk rule was written with lenses #1 and #2 in mind and would have zeroed out #3 without a single error message — the only symptom being a lens that looked badly prompted.

Dropped findings are recorded with `anchored = false`, not deleted — a lens that keeps producing unanchorable findings is badly prompted, and the drop rate is how it tells you.

**Severity is two levels that count and one that doesn't.** `blocker` routes to REBUT. `concern` reaches the operator's judgement and is the number in a queue line. `note` appears in the PR body and is excluded from every count — because without a third level, every true-but-trivial observation inflates the concern count that drives queue sort order, and you learn to ignore the number. The critic is told the distinction explicitly; a lens that files everything as `concern` is as much a prompting defect as one that hallucinates.

Three lenses — **different lenses, not repeated ones**:

1. **Correctness & data semantics** — timezones, chunk boundaries, null/gap propagation, unit errors, market-hours assumptions.
2. **Contract & schema** — public API compatibility, migration reversibility, serialization and schema conformance, anything downstream consumers depend on.
3. **Test adequacy** — whether the tests in the diff would notice the code being wrong: an assertion on a value the exercised path never reads, a test that constructs the value it then asserts, a structural check over source text a rename defeats, a witness whose setup is the only input the change is correct for.

#3 was **blast radius** until 2026-09-02 and is not any more; §5.5.1 records the amendment and the evidence behind it. Only the *content* of #3 changed — the numbering is an API and this section is cited by it.

**Each lens is a separate host-invoked session, not a subagent.** The runtime has a subagent facility that fits a lens almost perfectly — per-agent model, effort level, and a read-only tool list — and it is the wrong mechanism here for one reason: *the model decides when to spawn a subagent.* A REVIEW phase that asks one session to delegate to two or three lens subagents produces a lens set that varies by task, silently, with no error when a lens is skipped. Saffron needs all declared lenses to run on every reviewed diff, so the host invokes each one and collects its findings. The subagent *shape* is still the right configuration — it is where per-lens model and effort live — it just gets driven from the host rather than requested in a prompt.

This is §4.3's doneness rule again, one level out: **anything that must happen every time is measured and driven by the host; anything the model decides is a claim.** A lens that runs only when the model thinks it is relevant is not a lens, it is a suggestion.

One property the subagent facility does confirm: a fresh session receives no parent conversation at all — only what its invoker puts in the prompt. That is exactly the isolation this phase requires, and it means the diff, the spec, the gate results and the acceptance criteria must all be passed explicitly. There is no context to inherit, by design.

**A fresh session is not a fresh container.** Until rev 21 every lens ran in the implementer's own cell. Each was a new conversation, but it re-executed the agent runner and the SDK from a rootfs the implementer had root over. It also read `/work`, and every file a finding anchors against, through the implementer's `.git`. Each lens now runs in a **critic cell**: a new container from the repo's cell image, on the task's network and proxy, whose worktree is `tree_base` with the exported patch applied and committed by that cell's own git. What the critic reads is then the patch that ships. A forged export can hide the agent's work from the pull request, but not from the critic. A patch that will not apply to its own base ends the task `EXHAUSTED`. The agent can cause that failure, and one charged to nobody would be a free way past the critic. The one exception is a binary change: the export carries it as a `Binary files … differ` stub that no base can apply, and that ends `GATE_ERROR`, as PACKAGE already treats it. An agent can reach the stub on purpose and go uncharged, but nothing ships from it, so it is no way past the critic. It is the ceiling `size` and `integrity` already carry for a hidden binary (backlog item 118). The gate table each lens is shown moves out too: into a gate-only cell on the same rebuilt tree, never into the critic cell, where a gate would run model-authored code as root in the container the lenses then re-exec their runner from. `SA-0087` built the critic cell for REVIEW, `SA-0088` for REBUT's verdicts, and `SA-0089` the gate-only cell the table is computed in; `SA-0091` gives the verdict session the diff its blockers were filed against, so a line number is read against the tree it was filed on (backlog item 118).

**Any single blocker routes to REBUT.** No voting. A majority rule sounds rigorous and is decoration here: the lenses are disjoint by construction, so the schema critic will never independently corroborate the correctness critic's timezone finding, and "majority" over disjoint lenses means "never" at any count. False positives are handled by the rebuttal plus queue ordering (§6), which is the better mechanism anyway.

This section argued until 2026-09-02 that lens #3 in a naive design would be "test quality", displaced by `revert` answering it mechanically and for free — a bucket-1 solution displacing a bucket-3 one, per §8's triage rule. **That argument is withdrawn, and §5.5.1 says why.** The direction is still right; the displacement was not measured, and when it was, it did not hold.

#### 5.5.1 Lens #3 is test adequacy, not blast radius

**Amended 2026-09-02, on measurement rather than reasoning** (`docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`, backlog item 6). Two claims this section made are false:

- **`revert` does not displace a test-quality remit.** It reverts the source files, keeps the test files, and requires the new tests to fail — which for a spec that lands source and tests together they do, for the trivial reason, without anything having asked whether a particular line is tested. **`revert` asks whether the new tests test *anything*; this remit asks whether they test *each thing*.** The two do not overlap, and the second is the one nothing else covers. `SA-0044` built it, file-level, which is the ceiling its own `ponytail:` names: a file that is half test and half source is reverted whole or not at all. Measured once it shipped, that trivial-reason case is weaker still than this bullet assumed: the reverted tests fail to *import*, and a collection error prints no line this repo's `tests` gate can key on, so it reports `error` and `revert` reports `skip` rather than green. Free, honest, and no answer at all — backlog item 50.
- **A test can be fully covered and still prove nothing.** `saffron/gates/core/size.py` reports 100% statement and 100% branch coverage, and a line whose removal left all sixteen of its tests green was executed by every one of them. An *executed line whose effect nothing observes* is the class coverage cannot report by construction, which is why a coverage gate was priced against this remit and lost.

**What the lens is.** A prompted critic (`saffron/agents/prompts/review-adequacy.md`) holding no tool that can run anything: no test runner, no interpreter, no mutation harness — all three priced against this remit and rejected in the evidence above. It cannot mutate a line and watch a test fail, so every finding instead names the smallest edit that would keep the suite green while the behaviour breaks. That is what makes a finding checkable in one command by someone who *can* run one, rather than a claim about coverage the lens has no way to have confirmed.

**Blast radius is retired, not deferred.** It is the lens that would have caught the `git config diff.srcPrefix` escape (Appendix L), and that argument stands — but it was never built, because it was gated on a risk tier nothing wires, and the gap measured on two live diffs was test adequacy instead. Reviving it is a new decision with its own evidence, not the resumption of this one. What the retirement does **not** touch is the second anchoring target above: the reconciler rule blast radius motivated is load-bearing for #3 as it now stands. One consequence is deliberate and worth stating rather than discovering: all three prompts still route callers-and-downstream findings away to "the blast-radius lens", so that class is now owned by nobody and is suppressed at three seats rather than merely uncovered at one. Left as-is on purpose — a `Not yours` list edited to release the remit would scatter it across three lenses, which is the overlap §5.5 spends its no-voting rule on.

**Ungated, and that half is open.** The lens runs at every risk tier, not at `elevated` only — measured against this repo's own specs, 28 of 34 declare `elevated`, so gating would exclude six tasks to save one lens session ($0.76–$0.91 on the two it was priced against). REVIEW is not gated on the spend ceiling (§5.5), so the third session cannot fail a task for money; it does raise the worst-case REVIEW overrun from two remainders to three, because the per-lens cap is not decremented between lenses. Whether `adequacy` is what a tier should gate, once a tier exists, is backlog item 6's remaining half.

### 5.6 Phase 4b — REBUT

The implementer session resumes and gets the confirmed blockers. **One** attempt to either fix them or argue the finding is wrong. Both outcomes recorded. Gates re-run.

**If that re-run is red, the task is `EXHAUSTED` — REBUT does not re-enter the repair loop.** The rebuttal diff and the failing gate are both kept for you to read. Reopening repair here would let a task ping-pong between two phases on one budget, and it would be paying to paper over the most informative failure in the pipeline: a fix for a confirmed blocker that breaks something else is the clearest possible signal that the change and the finding both want your attention rather than another attempt.

Why allow rebuttal rather than mandate a fix: sometimes the critic is wrong, and a recorded disagreement between two agents is a strong signal about *which part of the diff you should read carefully*. Unanimity is far less informative than a documented argument.

**The order, settled.** "Confirmed blockers" here means *anchored* (§5.5) — the host has already established the finding points at real changed code, and that is the only confirmation available before a rebuttal exists. The critic's `verdict` (§4.1) comes **after** the argument: anchored blockers → the implementer rebuts → each lens that raised one confirms or withdraws it, in a fresh read-only session that sees the argument and never the transcript behind it. That session runs in a critic cell rebuilt from the post-rebuttal patch (§5.5). A critic verdicting first would be restating its finding rather than disagreeing with an answer, which is the one thing this phase exists to record. Three outcomes reach `READY_FOR_REVIEW` — every blocker withdrawn, a fix that commits and stays green, and a confirmed blocker the implementer argued against — because none of them is the machine's to settle: adjudication is yours, in the PR. A rebuttal that neither moved HEAD nor recorded an argument earns nothing and halts at `REBUTTING`; §3.3 has no state for it, and `NOT_IMPLEMENTED` would name the wrong phase.

**Risk tiering.** `risk: elevated` — set explicitly in the spec, or auto-elevated when the diff touches any path in the repo's `policy.elevate_on` (a repo with migrations and an ontology might list `migrations/**`, `**/*.ttl`, `trading/**`; Saffron's own lists `saffron/gates/**` and `saffron/cell/**`) — makes `size` blocking and marks the queue entry so you read it cold rather than skim. **It does not add a lens:** every lens `review.LENSES` declares runs on every reviewed diff at every tier (§5.5.1). Tier-gating one is still an open question and, until it is settled, the tier buys a gate and an ordering, not a critic. **`coverage` does not become blocking** — not at `elevated`, not ever; see §5.4.

Getting `elevate_on` right is most of what "onboarding a repo" actually means. It is the repo owner answering one question — *where in here does a plausible-looking wrong change hurt most?* — and it is worth more than any amount of gate configuration.

### 5.7 Phase 5 — PACKAGE (no model involved)

Host-side, deterministic:

1. Rebase onto current `main` (or onto the parent branch, if stacked). Conflicts → `MERGE_FAILED`. Never ask an agent to resolve conflicts unattended; a plausible-looking wrong answer there is very expensive. (Prior art suggests a middle path — see §11, "what I'd revisit".) **"Rebase" is the intent — the change lands on today's default branch — and `git apply --3way` of one squashed patch (below) is the mechanism.** Both are true; the document never said so, and a reader meeting them in order takes one for a contradiction.
2. Push `saffron/TE-0142-forecast-gap` to the real remote **with `--force-with-lease` pinned to the SHA the packager checked out.** If the branch moved underneath — a re-queued task, a second run, you pushing a fixup by hand — the push fails loudly instead of silently clobbering. Turning a race into an error costs one flag.
   Branch mutation is also serialized: one writer per branch, ever, held across package and merge-train operations. A `CHANGES_REQUESTED` task that gets re-queued must not race the merge train rebasing the same branch.
3. Open the PR. Body generated from the ledger, under the three headings a person's own pull request is asked for (`.github/pull_request_template.md`): **What** — spec, risk tier, diff size, attempt count and cost, the spec's own statement of the problem, root cause (if diagnosed), acceptance-criteria checklist with the critic's assessment of each; **Verification** — what the suite was measured on, new failures, disagreements, the test files the diff touched, gate table, findings with rebuttals, transcript path; **Not covered** — the checks that did not judge this code (a gate the repo declares none of, a gate that errored, a failure held advisory), a checklist no `criteria` result stands behind, findings that never anchored and so reached neither the implementer nor §6's concern count, a rebuttal turn that recorded nothing and so left every blocker unanswered (§4.3's distinction from a turn that argued nothing, and its error string is no likelier to be quoted here than in the table), and the implementer's own unadjudicated notes. **The two bodies share a spine and cannot share a file.** A person's template is guidance they edit freely; this one's section order is load-bearing — the notes render strictly last so cell-authored prose cannot read as having moved a table above it, and the test-file diff is sized last because it is the only unbounded section. A test holds the two heading lists equal; nothing else couples them. Gates that ran at `base_sha` and were not re-run are deliberately **not** in **Not covered**: the case below makes that provably redundant, and calling it a gap would be false.
4. Append the verdict line to the batch index.

**The base a task is cut from is the head of the remote's default branch as of task start**, not the invoking checkout's `HEAD`. It is fetched into the mirror before the cell is built (§5.1), so both ends of the comparison below read one source rather than two. Two consequences, both intended. Uncommitted and unpushed local work leaves a task's base — running from a dirty feature branch used to include it silently, and this is the change most likely to surprise an operator standing at a terminal. And re-verification below measures against a base the ledger already names, not one reconstructed from wherever the operator was standing. (Until rev 21 this consequence was that re-verification's skip became reachable by construction. §5.7 no longer skips.) The rejected alternative — keep `HEAD` and have PACKAGE compare against it too — is symmetric and needs no network; it loses because it makes a task's base unreproducible from the ledger, and §4.2 cannot start tasks unattended if two of them queued the same night are cut from different trees for no recorded reason.

**A stacked task has two bases, and they answer different questions.** `base_sha` stays the run's pin — gates, policy and the `.saffron/` export are read from it whether the task is stacked or not, so two tasks queued the same night are still measured against one declaration. `tree_base` is what the worktree is built on and the patch is exported against: `base_sha` for an ordinary task, and the parent's branch head for a stacked one. `patch.json` records both, because PACKAGE has to apply the patch against the tree it is relative to while reading its policy from the pin. Collapsing them was the defect the three specs building stacking each had to avoid in turn (`SA-0022`, `SA-0025`, `SA-0026`).

**The parent's head is fetched, never remembered.** A task row's `pushed_sha` is written once, by PACKAGE, and a branch moves afterwards — every review fix an operator commits by hand puts it ahead. The ledger is asked *which branch*; the branch is asked which commit, freshly, at both ends: once when the cell is built and again at PACKAGE, where a parent that has since merged falls back to the default branch and one that has vanished is `MERGE_FAILED` rather than a pull request opened against a branch that is not there. Nothing else puts the parent's objects in the mirror — `ensure_mirror` fetches from the *local working copy* and prunes, so a parent branch the operator does not happen to have checked out is deleted from the mirror between one task and the next.

#### v1: one squashed commit, a draft PR, and re-verification of every packaged commit

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

**Re-verification runs on every packaged commit.** Until rev 21 it ran only
when the base moved, on the argument that an unmoved base makes the merged tree
byte-identical to the one the suite already ran on, so a re-run is provably
redundant. That argument proves the *tree* is the same and says nothing about
the *verdict*. The suite that ran on that tree ran inside the implementer's
cell, on a toolchain and a `.git` the agent had root over (§5.4). Re-running it
elsewhere is the first time the answer is computed outside the untrusted zone
at all (Appendix Q, principle 58). It is also where the diff half of the class
closes. The packaged commit is built by host git from `patch.diff`, so every
gate in the fresh cell, `scope` and `integrity` included, measures the tree
that is pushed and the diff a reviewer reads, whatever the implementer's `.git`
said. `SA-0086` builds it; until it lands the skip still stands, and backlog
item 118 carries it. The suite re-runs **inside a cell, never host-side**,
because the applied tree carries `.saffron/gates/*` exactly
as the patch left them, and exec'ing those on the host is the control plane
executing model-authored code (§2). Both of its runs read their gates from a
host-supplied export at the new default-branch head (§5.4), so the patch's own
`.saffron/gates/*` are never executed anywhere and the two suites it subtracts
come from one set of executables. **PACKAGE reads its whole policy out of that
export**, unconditionally and whether or not the suite re-runs: the commit a
package is verified against declares the gates it is verified with, exactly as
`base_sha` does for the cell, and the pull request body then describes the
change under the declaration it was actually measured with. The gate-only cell runs the suite twice
and subtracts as always: at the default-branch head for a fresh baseline, which
a moved base would have invalidated anyway, and at the packaged commit.
It is the whole gate suite, core gates included, assembled by the one module the
cell's attempts were judged by, so the two cannot differ in shape (principle 54).
Every diff-reading gate measures from the new head, because that is the diff a
reviewer reads; the tier is computed afresh from it (§5.6), and the pull request
reports that tier. Drift between the two suites is infrastructure, exactly as an
errored gate is. New failures are `MERGE_FAILED`. After a moved base, that means the
change did not survive contact with today's main. On an unmoved base, it means
the cell's own verdict did not reproduce outside the cell. The two share a state
for now, with a note saying which. Whether the second needs its own state is
backlog item 118's vocabulary question, and principle 55 is why no test may
assert on the state alone.

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
| **Ratified tasks fail `scope` on their first commit** | The writeback edits a spec path the proposer never named | The spec's own path joins the ratified `touches` (§5.2) |
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
| Review × 3 lenses | $1.50–3 |
| Rebut | $0.50–1.50 |
| **Total** | **$5–15** |

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

**An entry is four things**: the one line of *why*, the bucket, where it landed, and the date and pull request it came from. A landing is one of three words, so a reread can count them: **Landed** — a gate's name, or a backlog item marked done; **Open** — with the item that tracks it, if one does; **Inert** — landed somewhere nothing reads. The landing is not decoration: a bucket with no outcome cannot tell a rejection closed by a gate from one still waiting, which is the whole of the promote-toward-1 claim. A rejection that names a mechanism which does not exist becomes a spec rather than a rule, and carries **No bucket**; *exactly one of three* is the rule, and the exceptions are marked rather than forced into a bucket that does not fit.

**A line written after the fact says so.** An entry reconstructed from history rather than written at rejection time is marked as such — on the entry, or under one dated header covering every entry before that date. A record that does not say which of its lines were written at the time has the same defect as an estimate stored in a column named for a measurement (§4.1). Each monthly reread appends its dated reading at the foot of the file, and a reading corrected later says when.

Reread the file monthly, not weekly. At 6–12 PRs a week you get 2–6 rejections; week-over-week accept rate on n≈8 swings ±20 points from two tasks and means nothing. This is a markdown file and a monthly habit, not a module with a taxonomy and a dashboard.

**Promote toward bucket 1.** A rule's whole life should be a migration from lens (3) to `CLAUDE.md` (2) to gate (1) — each step cheaper, more reliable, and more permanent than the last. Say "promote to bucket 1", never "up" or "down": the buckets are printed 1, 2, 3 but ordered cheapest-first, so directional words point opposite ways depending on whether you mean the page or the cost.

Two heuristics that need no code:

- If most rejections keep landing in bucket 3, your gates are too weak.
- If `CLAUDE.md` exceeds ~200 lines, audit it. The number is a measurement and not a diagnosis. Claude Code's memory docs give the same figure for a different reason, context cost and adherence. This file is also pasted whole into five prompt templates a task (Appendix S, principle 60). Cut in this order: what the tree already states, then what a gate could hold, then what one phase alone needs. What is left is the pitfalls and the rationale, which is the whole purpose of the file. (The vocabulary in `CONTEXT.md` is exempt and does not count against this. It is definitional rather than behavioural, and §5.3 filters it per phase where this file is sent whole. Rules of conduct belong in `CLAUDE.md`, rules of naming in `CONTEXT.md`.)

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
- Adversarial review, 3 lenses (§5.5.1); rebuttal.
- Scheduler: refusal gate, budget gate, ordering by priority then FIFO. **Not** conflict sets, round-robin or stacking (§4.2) — with one repo and a shallow queue all three are dead code, and `depends_on` waits with them.
- Real PRs + index page.
- **One repo: Saffron itself.** No `--repos` flag yet, no round-robin, but the `repos` table and the `.saffron/` layout exist from the start so that adding the second is data rather than code.

Self-hosting from day one is not the bold choice it sounds like, provided the first tasks put `saffron/` in `forbidden`. **`SA-0001` (the factory ontology) is close to an ideal first task**: `forbidden` covers `saffron/`, `pyproject.toml` and `DESIGN.md`, so the factory structurally cannot modify its own orchestrator or its own design while building it; validation is fixture-based and fully offline, so it runs in a no-route cell; and a wrong answer costs a weekend of Turtle rather than a broken pipeline. Run it *through* the pipeline rather than by hand.

Success criterion: a full night runs while you sleep, and you merge at least half of what it produces before the coffee's cold.

### v2 — the second repo, and sharpening

- **`thermal-edge` onboarded**, and the onboarding is the point: write `.saffron/policy.yaml`, `.saffron/gates/*`, `.saffron/Dockerfile`, and `elevate_on`. **Time it.** If it takes more than an afternoon, N8 is not being met and the contract is wrong somewhere — that measurement is worth more than the repo.
- Multi-repo batching: `--repos`, `--all`, round-robin, per-repo preflight and baselines, repo column in the queue.
- Conflict sets — two repos and a deeper queue are the condition §4.2 defers them to, and by v2 it has arrived. `depends_on` and stacked branches came early instead, in v0.5: the dependency gate refused the states stacking exists for, and a refusal whose text names machinery that does not exist is worse than either the feature or its absence.
- Repo-declared conditional gates against domain surfaces — this is where a repo's real leverage shows up (§5.4).
- Risk tiering — the third lens shipped ahead of it and ungated (§5.5.1).
- Merge train with re-verification.
- Rejection log habit (§8).

Success criterion: a batch spans two repos, and the diff to Saffron's source required to onboard the second one is **empty**.

### v2.5 — the emitter, conditional

Only if `ontology/RATIONALE.md` says the queries are worth reading: ledger → RDF projection, pyoxigraph store, materialization at batch end, SHACL validation of the projection.

It says otherwise (rev 18). `ontology/queries/` therefore stays where it is, as worked examples that `tests/ontology/` runs — moving them under `docs/` would cost the only thing keeping them honest. The vocabulary stays as documentation with two readers the queries are not: the `shacl` gate and the `CONTEXT.md` cross-check. Appendix O's spike is one of two things that reopen an emitter. The other is the RATIONALE's own clause, and rev 24 is where it fires: N5's query runs over the merged history rather than over fixtures, and Appendix T carries the decision rule. **The analytical question is a completed project, not an abandoned one** — you will have bought a precise answer to "is the relational model costing me anything?" for the price of a weekend, which is the cheapest that answer is ever available.

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
      runtime.py  worktree.py  database.py  proxy.py   # runtime.py names no runtime; runtimes/<product>.py each name one (Appendix G)
      runtimes/
        __init__.py  apple.py  podman.py                # the Dialect contract, and one module per runtime
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
    factory.ttl            # the vocabulary
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

## Appendices — an index

The appendices are ordered by *when* a thing was learned, which is the wrong order
for finding one. This is the other index. It is navigation, not authority: where it
disagrees with an appendix, the appendix is right.

| App. | Rev | The question it settles | Principles |
|---|---|---|---|
| **A** | 2 | Nine adversarial-review findings on rev 1 — DIAGNOSE proposes `touches`, `coverage` goes advisory, no vote over disjoint lenses | 1–9 |
| **B** | 3 | Is a factory ontology worth building? (`SA-0001`, §4.6) | 10–11 |
| **C** | 4 | What makes Saffron language-blind: the gate contract, and the core/repo boundary it draws (§2.1, §5.4) | 12–14 |
| **D** | 5 | What prior art does better — and the negative finding, that good process hygiene converges on near-zero verification | 15–24 |
| **E** | 6 | Three defects `CONTEXT.md` found in this document by being written against it | 25–26 |
| **F** | 7 | Nine more from an end-to-end read-through, including `coverage` blocking and advisory in the same document | 27–30 |
| **G** | 8, 10 | The cell runtime. "Docker" was never a decision — rev 8 names the candidates, rev 10 chooses by spike | 31–33 |
| **H** | 9 | What v0 found, being the first revision that ran: three merged pull requests replayed agent-free | 34–37 |
| **I** | 11 | What building v0.5 found — including a cell whose every mechanism reported success against a different container | 38–41 |
| **J** | 12 | What the first live runs found — four agent sessions in real cells, $2.47 | 42–44 |
| **K** | 13 | The factory produced plausible, verified, broken code: three tasks green, one reviewed, verdict *do not merge* | 45–49 |
| **L** | 14 | The critic built, and measured against a known-bad diff rather than argued for | 50–51 |
| **M** | 15 | What *running* the rejected gate found, beyond what reading it found — three corrections in twenty minutes | 52 |
| **N** | 16 | What tree a task is about, and who may write the thing that judges it (backlog items 11 and 12) | 53–55 |
| **O** | 18, 19 | Is there an *operational* case for the ontology, beyond the analytical one `RATIONALE.md` closed? Rev 19 ran the spike and closed it — *The result* | 56 |
| **P** | 20 | Should the appendices have been ADRs? No — and the phrase that kept the question alive was a summary of two verdicts that nobody decided | 57 |
| **Q** | 21 | Where the verdict of record is computed: outside the container the implementer had root in, on the tree the exported patch describes | 58 |
| **R** | 22 | How a style rule holds prose that already breaks it: it limits growth, and it skips no file | 59 |
| **S** | 23 | A budget that names one remedy: over ~200 lines the cut is ordered, and the file a cell reads whole is the one it binds | 60 |
| **T** | 24 | The emitter reopened on the RATIONALE's own clause: N5's query ran only against fixtures, so no merged change was ever its subject | 61 |
| **U** | 25 | Can the appendices leave `DESIGN.md`? Yes, because a refusal reaches only as far as its reason, and the reason against ADRs was a parallel tree | 62 |

**Two revisions have no appendix, and neither needs one.** Rev 1 is the document.
Rev 17 is in §4.2.1 and §6 with
`docs/evidence/2026-08-25-morning-queue-from-real-rows.md`. Two more only look
missing: rev 10 is inside Appendix G and rev 19 inside Appendix O, under *The
result*. That is why those two rows carry two revisions each, and why "one appendix
per revision" is the wrong reading — a revision that closes an earlier revision's
question lands in that question's appendix rather than opening its own.

The principles are one sequence across every appendix, allocated as a block when the
appendix is written. That is why an appendix is coarse and chronological rather than
one decision per file: per-decision documents written in parallel would each have to
claim numbers from the same sequence.

---

## Principles — an index

Every principle in one place, which the appendices cannot give you: each is stated
where it was found, and finding one means knowing which revision found it.

**This table is generated.** `uv run python -m ontology.render` rewrites it from the
appendices below, so a principle cannot be added to one and missed by the other, and
a hand edit here is discarded rather than kept. `ontology/design_record.py` parses
it into `factory:Principle` and `factory:RevisionAppendix`; the shapes hold what
Markdown cannot say about itself, and `tests/ontology/test_design_record.py` holds
contiguity, which SHACL has no form for.

The claim is the lead sentence. It is an index, not a substitute: a principle
compresses an appendix, and the appendix is where the case that found it lives.

| # | The claim | From |
|---|---|---|
| 1 | A gate that requires the human to already know the answer isn't a gate, it's a tax | A |
| 2 | A dependency edge that can only be satisfied by a human action outside the batch will never be satisfied inside it | A |
| 3 | A walking skeleton must contain the hard part | A |
| 4 | Controls inside the untrusted zone are not controls | A |
| 5 | Two safety mechanisms that make each other dead code mean you picked one without noticing | A |
| 6 | A blocking metric gate teaches the cheapest way to satisfy it | A |
| 7 | Resource limits that the runtime doesn't actually enforce produce flakiness you'll misattribute to the model | A |
| 8 | Detection without reclamation is not a countermeasure | A |
| 9 | A voting rule over disjoint voters never votes | A |
| 10 | A design artifact can succeed by concluding "don't build it." | B |
| 11 | Modelling pays before it ships | B |
| 12 | A boundary is cheap; an abstraction layer is not | C |
| 13 | When a check feels language-specific, separate the question from the vocabulary | C |
| 14 | Generality is a claim, and claims need tests | C |
| 15 | Treat agent output as claims; reconcile against a host-computed fact set | D |
| 16 | Bound liveness on more axes than you think, and never let a bound destroy work | D |
| 17 | Refuse before you spend | D |
| 18 | Structured output is a separate, tool-less turn | D |
| 19 | Retry idempotent infrastructure races; fail fast on everything that builds what the agent acts on | D |
| 20 | Control files in the workspace are agent-visible and agent-writable | D |
| 21 | `--force-with-lease` pinned to the checked-out SHA, and one writer per branch | D |
| 22 | Source determines processing | D |
| 23 | A living refusal record | D |
| 24 | A glossary with explicit *Avoid:* lists | D |
| 25 | A vocabulary is a test suite for a design, in the same way a spec is | E |
| 26 | Directional words need a fixed referent | E |
| 27 | An identity that includes a coordinate the change moves is not an identity | F |
| 28 | A reconciler tuned to one producer silently disables another | F |
| 29 | A rule with an unstated exception has been abandoned, not weakened | F |
| 30 | Fixing half a contradiction leaves a contradiction | F |
| 31 | A resource control means whatever the kernel reading it can see | G |
| 32 | A product name in a design is an unmade decision wearing a decision's clothes | G |
| 33 | A countermeasure written against an environment you have not run on is a hypothesis | G |
| 34 | A green result and an absent result are the same bytes | H |
| 35 | When identities can legitimately collide, subtraction has to count | H |
| 36 | Partial results are not results | H |
| 37 | Every harness that reports on something else needs the check it imposes | H |
| 38 | A control and its subject are wired somewhere, and the wiring is the control | I |
| 39 | Locating a tool proves a file exists; only running it proves a tool works | I |
| 40 | A reviewer scoped to one task cannot see the seam between two | I |
| 41 | A boundary leaks in both directions, and the second is harder to see | I |
| 42 | A pipeline that verifies work and then discards it has not finished; it has failed expensively | J |
| 43 | A configuration surface is an input, and every input from the workspace is a claim | J |
| 44 | The path that has never run is the one your estimate is about | J |
| 45 | A test written by the author of the code certifies agreement, not correctness | K |
| 46 | Over-built for the rare case, under-built for the common one | K |
| 47 | A proxy measure is gameable in exactly the direction the adversary wants | K |
| 48 | Gates verify what you thought to check; the critic exists for what you did not | K |
| 49 | A verification an agent can run itself is a verification it will have already passed | K |
| 50 | A critic and a reviewer fail differently, and that is the argument for having both | L |
| 51 | Two lenses reaching the same finding is a fact about the prompts, not about the finding | L |
| 52 | When a check keeps needing a better heuristic, the question is in the wrong coordinate system | M |
| 53 | A refusal that is loosened to make tests pass is a refusal that no longer exists | N |
| 54 | A control applied at one call site is not applied; it is applied at one call site | N |
| 55 | Where two outcomes deliberately share a state, that state cannot be the assertion | N |
| 56 | A negative result answers the question it tested, and no other | O |
| 57 | A summary of two decisions is a third decision, and nobody made it | P |
| 58 | A check that is redundant only if its subject was honest is not redundant | Q |
| 59 | A style rule limits growth, and never exempts a whole file | R |
| 60 | A threshold that names one cause is read as naming the only cause | S |
| 61 | A check that runs only on fixtures verifies the check, not the subject | T |
| 62 | A refusal reaches only as far as its reason | U |
