# saffron

[![CI](https://github.com/jtmcn/saffron/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/jtmcn/saffron/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/github/license/jtmcn/saffron)](LICENSE)

A Python orchestrator that turns spec files into reviewable pull requests.

Spec files in, reviewed pull requests out, running unattended overnight on one Mac.
Saffron reads specs committed to a target repo, runs each one as an agent in an isolated
cell, drives it through a hard gate loop until the change is objectively green, subjects
the diff to an adversarial critic, and opens a draft PR. A person merges. Nothing else
merges.

A queue captured on 2026-09-08, while PR #166 was open:

```
$ uv run saffron queue --repo .
reconcile: nothing moved
queue: 0 candidate(s)
refusals: 5
  .saffron/specs/SA-0060-the-gate-holds-a-path-it-should-not.md: touches overlaps open pull request https://github.com/jtmcn/saffron/pull/166's changed files: saffron/gates/core/witness.py, saffron/gates/runner.py, tests/test_gates.py, … (4 files)
  .saffron/specs/SA-0061-a-cell-run-supplies-no-mutator.md: touches overlaps open pull request https://github.com/jtmcn/saffron/pull/166's changed files: saffron/cell/session.py, tests/test_session.py
  ... 3 more
```

## Features

- **Specs are files.** A task is a Markdown file with YAML front matter in
  `.saffron/specs/`, declaring what it may touch, what it may not, and the acceptance
  criteria each claim is witnessed by.
- **Cells are untrusted.** Each task gets its own container, git worktree, and egress
  proxy. Every control that matters lives outside the cell — never in a prompt or an
  in-agent hook.
- **Gates are the repo's, not Saffron's.** A gate is any executable emitting one JSON
  object on stdout. Saffron knows nothing about your language or test runner; onboarding
  a repo touches zero lines of `saffron/`.
- **An adversarial critic reviews the diff** before anything reaches a person, and the
  implementer gets to rebut.
- **Conflict-aware queueing.** A spec whose `touches` overlaps an open pull request is
  refused rather than run, as shown above.
- **Everything is recorded.** Transcripts, gate results, spend, and state transitions
  land in a ledger and batch tree under `~/.saffron/`.

## Contents

- [Requirements](#requirements)
- [Install](#install)
- [Usage](#usage)
- [Configuration](#configuration)
- [Development](#development)
- [Status](#status)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Requirements

Saffron runs on macOS with Apple silicon; the cell runtime is a per-cell Linux VM.

- **`apple/container`** — `brew install container`, then
  `container system kernel set --recommended`
- **Rosetta** — `softwareupdate --install-rosetta`; `container build` does not work
  without it (measured, not assumed)
- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)**
- **[prek](https://github.com/j178/prek)** — a host tool, not a project dependency:
  `brew install prek`
- **`git`** and **[`gh`](https://cli.github.com/)** — `queue`, `reconcile`, and PR
  packaging shell out to `gh`
- **`CLAUDE_CODE_OAUTH_TOKEN`** — from `claude setup-token`; needed only by `cell` and
  `batch`

Full host setup, including which macOS services must be off before a batch runs, is in
[docs/HOST-HARDENING.md](docs/HOST-HARDENING.md).

## Install

Not published to PyPI. From source:

```sh
git clone git@github.com:jtmcn/saffron.git
cd saffron
make install
```

Cell-marked tests need two images, built by hand once:

```sh
container build -t saffron/cell-base:python -f images/cell-base.python.Dockerfile .
container build -t saffron/proxy -f images/proxy.Dockerfile .
```

## Usage

See what a batch would run tonight — agent-free, no cell started:

```sh
uv run saffron queue --repo .
```

Run one spec in one cell, attended. The token is scoped to the invocation deliberately:
`.envrc` does not load it, because direnv would export it into every shell in the
directory, and from there into any agent session started in one.

```sh
CLAUDE_CODE_OAUTH_TOKEN=... uv run saffron cell .saffron/specs/SA-NNNN-<slug>.md --repo .
```

Follow a task's event log, or read a finished one:

```sh
uv run saffron watch SA-0060
uv run saffron watch SA-0060 --no-follow
```

Run a night, unattended. `--until` is a *start no new task after* bound, not a kill, so a
night ends at the deadline plus at most one task:

```sh
CLAUDE_CODE_OAUTH_TOKEN=... uv run saffron batch --repo . --budget 50 --until 06:30
```

Ask GitHub what happened to open pull requests, and replay an already-merged PR
agent-free:

```sh
uv run saffron reconcile --repo .
uv run saffron replay <repo> <pr>
```

Under launchd, `batch` needs `PYTHONUNBUFFERED=1` — without it SIGTERM discards the log,
which is the night's only human-readable record.

### Exit codes

Load-bearing, and the only thing a calling script reads:

| Code | Meaning |
|---|---|
| `0` | the task is reviewable |
| `1` | the task did not make it |
| `2` | infrastructure failed |

PACKAGE opens the PR as a draft: ratifying one means `gh pr ready <n>` before
`gh pr merge`.

## Configuration

A target repo declares itself in `.saffron/` — no Saffron release required. This repo's
own is a worked example:

- `.saffron/policy.yaml` — which gates block, which paths elevate risk, which are
  protected, which suppression tokens `integrity` scans for
- `.saffron/gates/` — the executables themselves, one JSON object on stdout each
- `.saffron/specs/` — the tasks
- `.saffron/Dockerfile` — the repo's cell image

The gate contract is the whole repo-agnostic surface: `saffron/gates/contract.py`.

## Development

```sh
make check          # lint + test — the default target
make fmt            # ruff check --fix . && ruff format .
uv run pytest       # cell-marked tests excluded by default
uv run pytest -m cell   # needs the images above
```

## Status

Pre-release and single-operator. `saffron cell` and `saffron queue` are v0.5; `saffron
batch` is v0.6; `replay` is v0 and v1 deletes it. The `ratify` and `gc` subcommands are
designed but not built. Autonomous merge is a permanent non-goal, at any version.

[docs/BACKLOG.md](docs/BACKLOG.md) is what v0.5 left undone, ordered by what would hurt
most on the first unattended night.

## Documentation

- [DESIGN.md](DESIGN.md) — authoritative for what the system does. Section numbers are
  an API; specs cite them.
- [CONTEXT.md](CONTEXT.md) — authoritative for what the words mean.
- [docs/HOST-HARDENING.md](docs/HOST-HARDENING.md) — preparing the machine.
- [docs/evidence/](docs/evidence/) — primary records from spikes and live runs.

## Contributing

Work is tracked as spec files in `.saffron/specs/`, not as issues; see
[docs/agents/issue-tracker.md](docs/agents/issue-tracker.md).

## License

[MIT](LICENSE) © Joel McNierney

Agents working in this repo: read [CLAUDE.md](CLAUDE.md).
