# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Saffron is a Python orchestrator that turns spec files into reviewable pull requests: it runs
an agent in an isolated cell, drives it through a hard gate loop, subjects the diff to an
adversarial critic, and packages the result. `DESIGN.md` is authoritative for what the system
does; `CONTEXT.md` is authoritative for what the words mean. Both are read constantly — cite
`DESIGN.md` by section number (`§5.4`), and use `CONTEXT.md`'s vocabulary exactly.

> Saffron is also a *target repo* of itself (`.saffron/`), so this file is the standing
> instruction surface for agents running in a cell here (§8). Budget: ~200 lines. If it grows
> past that, promote rules to gates rather than adding prose.

`docs/BACKLOG.md` is what v0.5 left undone, ordered by what would hurt most on the first
unattended night. Read it before picking up work; `docs/evidence/` holds the primary records.

## Commands

```
make install                 # uv sync + prek install
make check                   # lint + test — the default target
make fmt                     # ruff check --fix . && ruff format .
uv run pytest                # cell-marked tests excluded by default (pyproject addopts)
uv run pytest tests/test_session.py::test_name    # one test
uv run pytest -m cell        # needs apple/container + the images below
```

`prek` is a host tool, not a project dependency — `brew install prek` if `make install`
cannot find it.

Cell-marked tests need real images, built by hand once (and after editing them):

```
container build -t saffron/cell-base:python -f images/cell-base.python.Dockerfile .
container build -t saffron/proxy -f images/proxy.Dockerfile .
```

The repo's own cell image is built from `.saffron/Dockerfile` by `saffron.repos.image`.
Host prerequisites (Rosetta, `container system kernel set --recommended`, nothing listening
on non-loopback) are in `docs/HOST-HARDENING.md`.

Running the CLI:

```
uv run saffron replay <repo> <pr>          # v0: replay a merged PR, agent-free
uv run saffron cell .saffron/specs/SA-0002-size-gate.md --repo .    # v0.5: one attended cell
```

`saffron cell` needs `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) in the environment;
this repo keeps it in a gitignored `.env` (`source .env`, or `set -x` it in fish).
Exit codes are load-bearing: `0` reviewable, `1` the task did not make it, `2` infrastructure
failed (`saffron/cli.py`).

## Architecture

Three planes (§2). **Control plane** — the host, trusted, decides what runs and whether the
result is acceptable, and never executes model-authored code. **Cells** — containers, untrusted.
**Ledger + batch tree** — `~/.saffron/ledger.db` and `~/.saffron/batches/`, the audit trail.

The one line that governs everything: *a cell is untrusted, and every control that matters
lives outside it.* Prompts and in-agent hooks shape behaviour; they are never the boundary.

### The core/repo boundary (§2.1)

Saffron knows diffs, git, containers, budgets, and the shape of a gate result. It knows
nothing about languages, test runners, package managers, or databases — those live in a target
repo's `.saffron/`. Onboarding a repo must touch zero lines of `saffron/`. The one sanctioned
exception has a shape worth memorising: **core invokes declared gates, never tools.**

### Layout

- `saffron/cell/` — `runtime.py` is the **only** module that names `apple/container`
  (Appendix G); `session.py` drives one cell start to finish (v0.5's supervisor);
  `worktree.py`, `proxy.py`.
- `saffron/gates/` — `contract.py` is the gate JSON schema and the whole repo-agnostic
  surface; `runner.py` execs gates host-side (`LocalExecutor` / `CellExecutor`);
  `baseline.py` subtracts pre-existing failures; `core/` holds the host-side gates
  (`scope`, `integrity` read the diff; `census` reads other gates' results).
- `saffron/phases/` — `implement.py` (plan checkpoint + repair turns), `review.py` (lenses),
  `rebut.py`.
- `saffron/agents/` — `context.py` injects `CONTEXT.md` sections per phase; `artifacts.py`
  the extraction turn and plan validation; `findings.py` anchors critic findings to the diff.
- `images/agent_runner.py` — the **only** file permitted to touch Agent SDK types. It runs
  inside the cell and emits Saffron's own event schema on stdout, one JSON line per event.
  The host never sees an SDK type.
- `saffron/replay.py` — v0 only; v1 deletes it.

### Invariants worth knowing before editing

- **The `tool` field** separates a gate that ran and passed from one that never ran. It must be
  obtained *by executing* the tool, never a string literal (§5.4, Appendix H).
- **`error` ≠ `fail`.** `fail` means the repo's code is wrong; `error` means the gate broke,
  aborts the attempt, and is charged to nobody. Never collapse them.
- **Baseline subtraction counts.** Identities collide legitimately — one baseline failure
  cancels one head failure, not all of them. Never compare on line number.
- **`census` compares sets; the baseline subtraction counts.** They sit beside each
  other and the rule is opposite, for a reason: failure identities collide
  legitimately, so one baseline failure cancels one head failure — but a test name
  is unique in a suite, so removal is a set difference. Do not make them match.
- **Control artifacts are extracted and hashed the moment they are produced**, never re-read
  from `/work`. A file left in the workspace is a claim, not a record.
- **Lenses are host-invoked fresh sessions, never subagents.** A lens that runs only when the
  model thinks it is relevant is not a lens.
- **Cell creation takes `network` and `env` as required arguments.** v0.5 shipped a cell with
  neither: every mechanism reported success and applied to a different container (Appendix I).
  Isolation tests must start a cell the way production does and probe from inside it.
- **No target-repo credentials in a cell, ever.** The single exception is
  `CLAUDE_CODE_OAUTH_TOKEN`. A host `ANTHROPIC_API_KEY` is deliberately not forwarded, and a
  test asserts it.
- **`RATE_LIMITED` is not `EXHAUSTED`.** A provider ceiling and a task that could not pass its
  gates are different outcomes and say different things.

## Conventions

- `DESIGN.md` section numbers are an API — specs cite them. Add subsections; never renumber.
- Vocabulary is enforced, including the `_Avoid_` lists in `CONTEXT.md`. "Cell" not "sandbox",
  "cell runtime" not "Docker", "batch" ≠ "run", "gate result" not "gate run".
- States in backticked caps in prose (`` `READY_FOR_REVIEW` ``), phases in bare caps
  (IMPLEMENT), gate names and statuses lowercase in backticks.
- A measured fact beats a reasoned one, and the comment says which. Several of the strangest
  lines here exist because a spike or a live run found something (`docs/evidence/`,
  Appendices G–L). Do not "simplify" one without reading its appendix.
- **Run the tool, don't merely locate it.** Image builds assert versions rather than paths,
  because a present-and-unrunnable binary reads identically to a working one.
- `ponytail:` comments mark deliberate simplifications and name their ceiling; leave them.
- Commit subjects are lowercase `type(scope): what changed`, written as a sentence about the
  defect rather than the file — see `git log`.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **saffron**. Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze --embeddings` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939). `--embeddings` because a plain `analyze` preserves existing embeddings but does not generate them for new nodes, and `query`'s ranking is BM25-only without them. PDG is pinned in `.gitnexusrc`, which `explain` needs.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- **A zero from `impact` is not evidence of safety here.** Measured on this repo: it resolves bare-name calls (`from x import f; f()`) and misses module-attribute calls (`worktree.prepare_worktree(...)`), which is this codebase's idiom for cross-module calls — 79 such sites in `saffron/`. `prepare_worktree` has 12 callers and reports `impactedCount: 0, risk: LOW`. Re-indexing does not fix it. Confirm every non-trivial blast radius with `grep -rn 'name(' --include='*.py'` before trusting a low number.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/saffron/context` | Codebase overview, check index freshness |
| `gitnexus://repo/saffron/clusters` | All functional areas |
| `gitnexus://repo/saffron/processes` | All execution flows |
| `gitnexus://repo/saffron/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Skill |
|------|-------|
| Understand architecture / "How does X work?" | `gitnexus-exploring` |
| Blast radius / "What breaks if I change X?" | `gitnexus-impact-analysis` |
| Trace bugs / "Why is X failing?" | `gitnexus-debugging` |
| Rename / extract / split / refactor | `gitnexus-refactoring` |
| Tools, resources, schema reference | `gitnexus-guide` |
| Index, status, clean, wiki CLI commands | `gitnexus-cli` |

<!-- gitnexus:end -->
