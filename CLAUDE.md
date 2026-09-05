# CLAUDE.md

Saffron is a Python orchestrator that turns spec files into reviewable pull requests: it runs
an agent in an isolated cell, drives it through a hard gate loop, subjects the diff to an
adversarial critic, and packages the result. `DESIGN.md` is authoritative for what the system
does; `CONTEXT.md` is authoritative for what the words mean. Both are read constantly — cite
`DESIGN.md` by section number (`§5.4`), and use `CONTEXT.md`'s vocabulary exactly. For the
five closed sets `tests/ontology/test_vocabulary_agrees_with_context.py` names,
`ontology/saffron.ttl` is authoritative and both `CONTEXT.md` and
`ontology/shapes/saffron-shapes.ttl` are generated from it: edit the vocabulary and run
`uv run python -m ontology.render`. Two shape lists stay hand-maintained because the
vocabulary cannot imply them — a new core gate needs a blocking level in
`saffron:CoreGateBlockingShape`, a new terminal state a place in `saffron:TaskShape`'s
endedInState — and a test names the shape and the file when you forget.

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
uv run saffron queue --repo .              # v0.5: what a batch would run; reconciles PR state first
uv run saffron reconcile --repo .          # ask GitHub what happened to open pull requests
uv run saffron watch SA-0002               # follow a task's event log; --no-follow for a finished one
```

`saffron cell` needs `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) in the environment
of the command itself, and nowhere else. `.envrc` deliberately does not load it: direnv would
export it into every shell in this directory, and from there into any Claude Code session
started in one. `.env` is no home for it either — `.envrc` loads that with
`dotenv_if_exists`. Scope it to the invocation instead (fish):

```
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
  uv run saffron cell <spec> --repo .
```

Exit codes are load-bearing: `0` reviewable, `1` the task did not make it, `2` infrastructure
failed (`saffron/cli.py`).
PACKAGE opens the PR as a draft (§5.7): ratifying one means `gh pr ready <n>` before `gh pr merge`.

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
- A new test is not trusted until it has been run against the unfixed code — or, for one
  guarding a property already true, against a mutant that breaks it.
- Commit subjects are lowercase `type(scope): what changed`, written as a sentence about the
  defect rather than the file — see `git log`.

## Agent skills

### Issue tracker

Work is tracked as spec files in `.saffron/specs/SA-NNNN-*.md`, driven by `saffron cell`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles, each label string equal to its name. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` at the root, ADRs under `docs/adr/`. See `docs/agents/domain.md`.
