# CLAUDE.md

Saffron is a Python orchestrator that turns spec files into reviewable pull requests: it runs
an agent in an isolated cell, drives it through a hard gate loop, subjects the diff to an
adversarial critic, and packages the result. `DESIGN.md` is authoritative for what the system
does; `CONTEXT.md` is authoritative for what the words mean. Both are read constantly — cite
`DESIGN.md` by section number (`§5.4`), and use `CONTEXT.md`'s vocabulary exactly. For the
closed sets `tests/ontology/test_vocabulary_agrees_with_context.py` names, `ontology/factory.ttl`
is authoritative and both `CONTEXT.md` and `ontology/shapes/factory-shapes.ttl` are generated
from it: edit the vocabulary and run `uv run python -m ontology.render`. Two shape lists stay
hand-maintained because the vocabulary cannot imply them — a new core gate needs a blocking level
in `factory:CoreGateBlockingShape`, a new terminal state a place in `factory:TaskShape`'s
endedInState — and a test names the shape and the file when you forget. The `shacl` gate
validates every `.ttl` in the tree against those shapes, so a graph no test loads is still
checked. The same command also rewrites `DESIGN.md`'s principle and appendix indexes, and those
run the other way: the appendix records in `docs/appendices/` are authoritative and the indexes
are their render, so a new principle is written into its appendix record and never into a table
(Appendices P and U).

> Saffron is also a *target repo* of itself (`.saffron/`), so this file is the standing
> instruction surface for agents running in a cell here (§8). Budget: ~200 lines. If it grows
> past that, promote rules to gates rather than adding prose.

`docs/backlog/` is what v0.5 left undone, one record per item; `make backlog` lists them and `uv run python -m records show 118` prints one.
`docs/backlog/PRIORITY.md` is the order to work in. Read it before picking up work; `docs/evidence/` holds the primary records.

## Commands

```
make install                 # uv sync + prek install
make check                   # lint + test — the default target (lint = prek run --all-files)
make fmt                     # ruff check --fix . && ruff format .
uv run pytest                # cell-marked tests excluded by default (pyproject addopts)
uv run pytest tests/test_session.py::test_name    # one test
uv run ast-grep test -c .saffron/sgconfig.yml     # the structure rules' own tests
uv run ast-grep test -c .saffron/sgconfig.yml --update-all   # after adding a snippet
.saffron/gates/structure                          # what the `structure` gate runs; `prose` and `terms` rules live in .saffron/gates/prose.py
uv run pytest -m cell        # needs apple/container + the images below
```

`prek` is a host tool, not a project dependency — `brew install prek` if `make install`
cannot find it.

Cell-marked tests need real images, built by hand once (and after editing them; a host with
no registry adds `--build-arg BASE_IMAGE=…`, §5.1.2):

```
<runtime> build -t saffron/cell-base:python -f images/cell-base.python.Dockerfile .
<runtime> build -t saffron/proxy -f images/proxy.Dockerfile .
```

The repo's own cell image is built from `.saffron/Dockerfile` by `saffron.repos.image`.
Host prerequisites (Rosetta, `container system kernel set --recommended`, nothing listening
on non-loopback) are in `docs/HOST-HARDENING.md`.

Running the CLI:

```
uv run saffron replay <repo> <pr>          # v0: replay a merged PR, agent-free
uv run saffron cell .saffron/specs/SA-NNNN-<slug>.md --repo .    # v0.5: one attended cell
uv run saffron queue --repo .              # v0.5: what a batch would run; reconciles PR state first
uv run saffron reconcile --repo .          # ask GitHub what happened to open pull requests
uv run saffron watch SA-NNNN               # follow a task's event log; --no-follow for a finished one
uv run saffron batch --repo . --budget 50 --until 06:30   # v0.6: a night, unattended
```

`saffron batch` is the unattended one: `--until` is a *start no new task after* bound, not a
kill, so a night ends at the deadline plus at most one task (backlog item 67). Under launchd it
needs `PYTHONUNBUFFERED=1`, or SIGTERM discards the log — which is the night's only
human-readable record. `docs/host/dev.saffron.batch.plist` and `docs/HOST-HARDENING.md` §4a
carry the setup.

`saffron cell` and `saffron batch` need `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) in
the environment of the command itself, and nowhere else. `.envrc` deliberately does not load it: direnv would
export it into every shell in this directory, and from there into any Claude Code session
started in one. `.env` is no home for it either — `.envrc` loads that with
`dotenv_if_exists`. Scope it to the invocation instead (fish; a cloud host, which has no
`~/.secrets`, is `docs/HOST-HARDENING.md` §1a):

```
env CLAUDE_CODE_OAUTH_TOKEN=(bash -c 'source ~/.secrets; printf %s $CLAUDE_CODE_OAUTH_TOKEN') \
  uv run saffron cell <spec> --repo .
```

Exit codes are load-bearing: `0` reviewable, `1` the task did not make it, `2` infrastructure
failed (`saffron/cli.py`).
PACKAGE opens the PR as a draft (§5.7): mark it ready with `gh pr ready <n>` before `gh pr merge`.

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

- `saffron/cell/` — `runtime.py` is every caller's view of the cell runtime and names **no**
  product; only `runtimes/apple.py` and `runtimes/podman.py` may spell their own binary, one
  gated rule each (Appendix G). `runtimes/__init__.py` is the `Dialect` — only what the two
  were *measured* to spell differently. `SAFFRON_CELL_RUNTIME` picks one and an unknown name
  raises: **declared, never detected**. `session.py`, `worktree.py`, `proxy.py`.
- `saffron/gates/` — `contract.py` is the gate JSON schema and the whole repo-agnostic
  surface; `runner.py` execs gates host-side (`LocalExecutor` / `CellExecutor`);
  `baseline.py` subtracts pre-existing failures; `core/` holds the host-side gates.
- `saffron/phases/` — `implement.py` (plan checkpoint + repair turns), `review.py` (lenses),
  `rebut.py`, `package.py`.
- `saffron/task.py` — `run_task` drives one task end to end, a cell *and* PACKAGE.
  `saffron cell` and `saffron batch` adapt over it.
- `saffron/agents/` — `context.py` injects `CONTEXT.md` sections per phase and loads turn prompts.
  `artifacts.py` holds the extraction turn and plan validation; `findings.py` anchors findings to the diff.
- `images/agent_runner.py` — the **only** file permitted to import the Agent SDK (gated). It runs
  inside the cell and emits Saffron's own event schema on stdout, one JSON line per event.
  The host never sees an SDK type.
- `harness/` — measures Saffron rather than shipping in it: `lens_scoring.py`
  scores REVIEW against a fixture whose defects are declared
  (`docs/evidence/fixtures/`). Not imported by `saffron/`, and the drivers that
  spend money live in `docs/evidence/scripts/` so the part that can be wrong in
  silence is the part with tests.
- `saffron/replay.py` — v0 only; v1 deletes it.

### Invariants worth knowing before editing

The five marked **(gated)** are enforced by `.saffron/rules/`, run by the `structure` gate and
a prek hook; the rest are still prose. Promote one when you find it broken — `ast-grep test`
means a rule ships with the mutant that proves it fires. Read `.saffron/sgconfig.yml` before
writing one.

- **The `tool` field** separates a gate that ran and passed from one that never ran. It must be
  obtained *by executing* the tool, never a string literal (§5.4, Appendix H). **(gated over
  Python; `.saffron/gates/format` builds its contract in `sh`, which no rule reads — item 77)**
- **A skip is spelled in full where it is used.** `integrity` reads `.saffron/policy.yaml`'s
  suppression tokens as *text*. One bound to a name, imported, or named by string spells none of
  them, so every later use passes (item 112). **(gated over all Python, not only `tests/`)**
- **One module drives a task.** `saffron/task.py` is the only caller of `run_one_cell`; both
  commands go through it. Two copies is what let the unattended path stop recording the
  ceilings that bound each task. **(gated over `saffron/`)**
- **`error` ≠ `fail`.** `fail` means the repo's code is wrong; `error` means the gate broke,
  aborts the attempt, and is charged to nobody. Never collapse them.
- **`census` compares sets; the baseline subtraction counts.** They sit beside each
  other and the rule is opposite, for a reason: failure identities collide
  legitimately, so one baseline failure cancels one head failure, not all of them, and
  never on line number — but a test name is unique in a suite, so removal is a set
  difference. Do not make them match.
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
- A comment is one or two lines naming the non-obvious why. The rationale behind it goes in
  the commit message or the PR body, and a spec's notes are that rationale, not comment text.
  A function, class or test docstring stays within ten lines. **(gated: `prose` counts both,
  per file)**
- A new test is not trusted until it has been run against the unfixed code — or, for one
  guarding a property already true, against a mutant that breaks it.
- Commit subjects are lowercase `type(scope): what changed`, written as a sentence about the
  defect rather than the file — see `git log`.
- A pull request body you write follows `.github/pull_request_template.md`: `gh pr create --body`
  skips the template, so read it first.

## Agent skills

`docs/agents/` holds how skills read this repo: spec files as the issue tracker, the five
triage labels, and the domain docs (no ADRs, `CONTEXT.md` §11).
