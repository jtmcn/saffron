---
id: SA-0284
title: "Commits pushed after PACKAGE reach no gate, and no command re-runs a task's gates over its pull request's head"
type: feature
priority: 2
depends_on: [SA-0275, SA-0271, SA-0268, SA-0265]
consumes:
  - saffron/ledger.py:record_regate
estimated_lines: 478
estimate_measured: true
touches:
  - saffron/regate.py
  - saffron/cli.py
  - tests/test_regate.py
  - CLAUDE.md
  - README.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/preflight.py
  - saffron/record/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/view/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/repos/**
  - tests/test_cli.py
  - tests/test_ledger.py
  - tests/test_reconcile.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 42
max_attempts: 3
max_turns: 170
risk: standard
acceptance:
  - claim: >-
      `saffron regate <task id> --repo <path>` judges an open pull request's
      current head with the task's own gates. It asks
      `gh pr view <pr url> --json state,baseRefName`. It fetches the branch
      that answer names as the base, and the task's branch, into the mirror
      at the path `_mirror_path` gives. The head is the task branch's
      fetched head, and the baseline is the merge base of the two fetched
      heads. It exports `.saffron/` from the task's run's `base_sha` and
      reads the policy and the spec file from that export. It builds the
      repo's cell image. It then runs N1's host probe on a network it
      claims from the pool, after removing a leftover of that name, and
      removes the network before `reverify` starts. It prints the ports line
      `run_one_cell` prints, `tolerating` part included. It calls
      `package_phase.reverify` once, with the mirror, that head, that merge
      base, the policy, the export, the built image and the spec. It then
      calls `record_regate` with the task id, `head_sha` the head,
      `baseline_sha` the merge base and `new_failures` 0, prints `green`, and
      exits 0. It reads no token and reaches no agent. The witness drives a
      base of the default branch and a base of a parent's branch, each
      moved after the task's branch forked from it, with `--repo` relative
      to the working directory.
    witness: tests/test_regate.py::test_regate_runs_the_tasks_gates_over_the_pull_requests_head_and_records_green
    wrong_versions:
      - The export taken at the default branch's fetched head, as PACKAGE takes it.
      - The policy or the spec read from the checkout's working tree.
      - The base fetched as the default branch whatever branch the pull request names.
      - The baseline taken as the base branch's head rather than the merge base.
      - The baseline taken as the task's run's `base_sha`.
      - The merge base taken against the task row's `pushed_sha` rather than the fetched head.
      - The spec loaded at a commit other than the run's `base_sha`.
      - "`gh pr view` asked for the task's branch rather than its `pr_url`."
      - The head taken from the task row's `pushed_sha` rather than the fetched branch.
      - A mirror at a path other than `_mirror_path`'s.
      - "`cell_tag(repo)` passed as the image with no build."
      - No probe, or the probe run after `reverify` returns.
      - The probe at a fixed subnet's gateway rather than the claimed one's.
      - No removal of a leftover network before the claim.
      - A ports line with no `tolerating` part.
      - No `record_regate` call, or one whose `baseline_sha` is the base branch's head.
      - "`--repo` used unresolved."
      - A refusal to run when `CLAUDE_CODE_OAUTH_TOKEN` is unset.
  - claim: >-
      When `reverify` returns new failures, the command prints one line per
      new failure, naming its gate, its code and its file. It records
      `new_failures` as their count, prints that count, and exits 1. The
      witness returns two new failures in two gates.
    witness: tests/test_regate.py::test_regate_prints_each_new_failure_records_the_count_and_exits_one
    wrong_versions:
      - An exit of 0 whatever `reverify` returned.
      - "`new_failures` recorded as 0, or not recorded on a red result."
      - Only the first new failure printed.
  - claim: >-
      The command refuses each of these eight tasks. They are an id with no
      task row, a task with no pull request, a task of another repo than
      `--repo`'s, a pull request GitHub reports `MERGED`, one it reports
      `CLOSED`, a run `base_sha` holding no `.saffron/specs/<spec id>-*.md`,
      a spec file there whose sha is not the task's `spec_sha`, and a task
      holding a recorded spec text. Each refusal prints `regate:` and its
      reason, and exits 1. None builds an image, claims a network, runs the
      probe, calls `reverify` or calls `record_regate`. The witness drives
      all eight in one test.
    witness: tests/test_regate.py::test_regate_refuses_each_task_it_cannot_judge_before_any_cell_and_exits_one
    wrong_versions:
      - Any one of the eight refusals dropped.
      - A state check that refuses `CLOSED` and lets `MERGED` through.
      - A spec check that compares the file's sha and never asks for a recorded text.
      - The image built before the refusals are decided.
  - claim: >-
      Each of these three exits 2 and records nothing. They are a
      `gh pr view` that exits non-zero, a `PreflightFailed` from
      `assert_host_is_unreachable`, and a `PackageError` from `reverify`. On
      the probe's refusal the probe's network is removed and `reverify` is
      never called. The witness drives all three.
    witness: tests/test_regate.py::test_regate_exits_two_on_infrastructure_and_records_nothing
    wrong_versions:
      - A probe refusal read as a refused task, exit 1.
      - The probe's network left behind when the probe refuses.
      - A failed `gh pr view` read as a refused task, exit 1.
      - A raise from `reverify` caught and turned into exit 1.
  - claim: >-
      A SIGTERM while `reverify` runs exits 143 through `_guarding_sigterm`,
      as `saffron cell` and `saffron batch` do, and records nothing. The
      witness installs its own SIGTERM handler first, which must not be the
      one that runs.
    witness: tests/test_regate.py::test_regate_stopped_by_sigterm_exits_143
    wrong_versions:
      - The dispatch calling the command with no `_guarding_sigterm` around it.
---

## Context

Backlog item **97**, with the re-gate half of item **40**. It cites
`DESIGN.md` §5.4, §5.7 and §6.1. Every line number below was read at
`bc879e2c`. `SA-0275`, the parent, adds `Ledger.record_regate` and the
reader `reconcile` prints from. This spec adds the command that writes it.

**Review commits reach no gate.** 34 of 38 packaged pull requests merged
at a head other than the one PACKAGE pushed
(`docs/evidence/2026-09-10-review-fixes-past-package.md:1`). Item 40
records three. `SA-0029`'s cell left 548 changed lines, and two host-side
review rounds took it to 863 against a 600 ceiling. `SA-0086`'s review
round edited a file its spec forbade. `reconcile` already names a head
that moved past `pushed_sha` (`saffron/reconcile.py:177-179`).
`tasks.merged_head_sha` keeps the head a merge landed at
(`saffron/ledger.py:146-148`). No gate judges either head.

**Re-verification is the suite to reuse.** `package_phase.reverify`
(`saffron/phases/package.py:482-591`) runs the whole gate suite twice. It
runs a baseline at `new_base_sha` and the head at `packaged_sha`, each in
its own gate-only cell. It reads its gates from the caller's `gates_dir`
and raises `PackageError` on an errored gate or on drift. It returns a
`SuiteComparison` whose `new_failures` are `NewFailure(gate, failure)`
pairs (`saffron/gates/suite.py:112-125`, `saffron/gates/baseline.py:20-22`).
`_finish_verify` calls it outside PACKAGE already (`saffron/cli.py:768-795`).

**PACKAGE takes its gates from the default branch's head.** It exports
`.saffron/` at `fetch_head` and loads the policy from that export
(`saffron/phases/package.py:733-737`). The cell took its gates from its
run's `base_sha` (`DESIGN.md` §5.4).

**N1's probe admits a cell.** `run_one_cell` lists the host's ports with
`preflight.host_probe_ports`. It prints the count, the addresses and
`tolerating` with the tolerated names or `nothing`. It then calls
`preflight.assert_host_is_unreachable` per network
(`saffron/cell/session.py:1095-1111`). A command that calls `reverify`
alone has had no probe in its invocation.

**What the ledger holds.** A task row carries `spec_id`, `spec_sha`,
`branch`, `pushed_sha` and `pr_url`, and its run carries `base_sha` and
`repo_id` (`saffron/ledger.py:117-146`). `create_task` writes `spec_sha`
once (`saffron/ledger.py:730`), and nothing rewrites it. A stack batch can
run a task on a recorded text in place of its file
(`saffron/task.py:464-471`). That text lives in `spec_texts`, and
`Ledger.spec_text` returns the newest or `None`
(`saffron/ledger.py:1828-1839`). So such a task's `spec_sha` still matches
its file at `base_sha`. Modules outside `ledger.py` read a task row through
`ledger._db` already (`saffron/chain_walk.py:64`,
`saffron/end_review.py:111`). A stack batch creates its task with the
candidate's `spec_sha`, the file's at `base_sha` (`saffron/cli.py:1123-1127`).

**Helpers at base.** `fetch_parent_branch(mirror, url, branch)` fetches any
named branch into the mirror, checks its objects, and returns its head
(`saffron/phases/package.py:173-205`). `git_mirror.export_saffron_dir`
writes `.saffron/` under its `dest` (`saffron/repos/mirror.py:182-227`).
`load_spec` returns a spec and the sha256 of its file's bytes
(`saffron/intake.py:348-359`). `_mirror_path` is the mirror path
`saffron cell` uses (`saffron/cli.py:1651-1657`). `_guarding_sigterm`
turns a SIGTERM into exit 143 after the stack unwinds
(`saffron/cli.py:451-474`). The dispatch's `except Exception` turns any
other raise into exit 2 (`saffron/cli.py:300-307`).

## Problem

Add `saffron regate <task id> --repo <path>`, `--repo` defaulting to the
working directory. It runs the task's gate suite over its pull request's
current head and records the result. No agent runs, and the command needs
no token. The task's state is left alone.

**`saffron/regate.py` takes every step.** `saffron/cli.py` adds the parser
and resolves `--repo`. It dispatches inside `_guarding_sigterm`. It passes
the ledger, the shared `out_dir`, `_mirror_path`'s path and `run_gh`. The
steps run in this order.

1. Read the task row and its run. Refuse an unknown id and a task with no
   `pr_url`. Refuse a task holding a recorded spec text. Refuse a task
   whose run's `repo_id` is not the one `resolve_repo_id` gives for
   `real_remote(repo)`.
2. Ask `gh pr view <pr url> --json state,baseRefName`. A non-zero exit
   raises. Refuse any state but `OPEN`.
3. `ensure_mirror` at `_mirror_path`'s path. Fetch `baseRefName` and the
   task's `branch` with `fetch_parent_branch`. The baseline is
   `git merge-base` of the two heads.
4. Export `.saffron/` at the run's `base_sha`. Find
   `.saffron/specs/<spec id>-*.md` in it, refuse when there is none, and
   load it with `load_spec`. Refuse when its sha is not the task's
   `spec_sha`. Load the policy from the export.
5. Build the repo's cell image with `build_cell_image`.
6. Run N1's probe, as below.
7. Call `package_phase.reverify` with the mirror, `packaged_sha` the head,
   `new_base_sha` the merge base, the policy, the export, the image and
   the spec.
8. Call `ledger.record_regate(task_id, head_sha=..., baseline_sha=...,
   new_failures=...)`. `baseline_sha` is the commit the baseline suite ran
   at, the merge base, and `new_failures` is the count.
   Print each new failure's gate, code and file, then one line with the
   head, the merge base and `green` or the count. Exit 0 green and 1 red.

A refusal prints `regate:` and its reason, and exits 1. Any raise
propagates to `main`, which exits 2.

**Why the task's `base_sha` and not the default branch's head.** Item 97
asks for "the task's gates, from the same `base_sha` export". The question
is whether the head still passes what the cell's diff passed. So it is
judged by the gates and policy the cell was judged by. A later change to
the default branch's gates then never judges an older task. Neither the
head nor the base it merges onto supplies the gates, so a review commit
cannot weaken them. PACKAGE reads the default branch's head instead
because it applies the patch onto that head and opens the pull request
there. Its gates must name the roles that tree carries.

**Why the merge base.** GitHub shows a pull request as the diff from the
merge base. A baseline at the base branch's newer head would read every
commit the branch lacks as this task's diff. `scope` and `census` would
then fail on files the task never touched.

**N1's probe.** Name its network `saffron-regate-probe-<task id>`, a prefix
no other network uses. Remove a leftover of that name first. Inside a
`try`, claim it with `runtime.allocate_network`, and take the gateway with
`runtime.gateway` of the claimed subnet. List the ports with
`preflight.host_probe_ports()`. Print the line `run_one_cell` builds, with
the gateway first and then `preflight.probe_addresses(gateway)`, each once.
Call `preflight.assert_host_is_unreachable(repo_image.BASE_TAG, name,
gateway=..., ports=..., sockets=...)`. The `finally` removes the network,
so it is gone before `reverify` starts.

**The documentation, as cell work.**

- `CLAUDE.md`'s command list: one line for the command after `reconcile`
  (`CLAUDE.md:62`).
- `README.md`'s usage: a short paragraph and block after `reconcile`'s
  (`README.md:131-137`). Say that no agent runs and no token is needed,
  and give the three exit codes.
- `saffron/cli.py`'s module docstring lists every subcommand
  (`saffron/cli.py:1-2`). Add `regate`.

## Out of scope

- **The record and the reader.** `SA-0275` owns the `task_regate` fact,
  `record_regate`, `regate`, and what `reconcile` prints.
- **The state.** A red result does not move the task. Nothing refuses
  `gh pr ready` on it.
- **The merge train** (`DESIGN.md` §6.1). This judges the branch as GitHub
  shows it, not the merged result.
- **A task that ran a recorded text** is refused, not judged with that
  text.
- **A shared probe helper.** The probe repeats about 20 lines that
  `SA-0268` writes inline in `saffron/task.py`. One helper for both is a
  later change, and `saffron/task.py` is forbidden here.
- **`DESIGN.md` §6.1** names the command in a paragraph the operator adds
  by hand on this spec's branch.

## Notes for the agent

**Every criterion is new code.** Neither the module nor the subcommand
exists at base. So each criterion declares a witness and no mutant, and
`witness` reports `skip` for each. With the source reverted, `regate` is
not a subcommand, so `main` raises `SystemExit` from argparse and every
witness fails. Import nothing at the witness module's top that this change
adds. Every name the module imports exists at the tree base.

**Writing against `SA-0270` and `SA-0271`.** Once `SA-0271` lands,
`runtime.allocate_network(name)` claims a /24 of the pool and returns its
subnet. `runtime.GATEWAY` and `create_network`'s default subnet are then
gone. `assert_host_is_unreachable` and `probe_addresses` then take the
gateway as a required parameter, ahead of `ports`. So pass
`gateway`, `ports` and `sockets` to `assert_host_is_unreachable` by
keyword. Then the call is right under either order. Read `runtime` and
`preflight` at the tree base before you write the probe.

**Writing against `SA-0275`.** Call `ledger.record_regate` with exactly
the keywords `head_sha`, `baseline_sha` and `new_failures`, the last an `int`.
The `types` gate checks the call against the parent's signature.

**The seams.** Call each host step through its module, so a monkeypatch
reaches it. They are `saffron.cli.run_gh`, read when the dispatch runs,
and `repo_image.build_cell_image`, `runtime.remove_network`,
`runtime.allocate_network`, `preflight.host_probe_ports`,
`preflight.probe_addresses`, `preflight.assert_host_is_unreachable` and
`package_phase.reverify`. The witnesses replace each of these, and
`Ledger.record_regate` with a function that records its arguments. They
also replace `saffron.task.run_one_cell` and
`saffron.phases.implement.run_agent` with functions that raise, and unset
`CLAUDE_CODE_OAUTH_TOKEN`.

**A scan reads every file under `saffron/`.**
`test_only_the_scan_constructs_a_refusal` fails any file but
`scheduler.py` whose text holds `Refusal(`
(`tests/test_refusal_count.py:78-85`). So give the refusal another name.
Annotate the runner parameter with the `GhRunner` alias at
`saffron/phases/package.py:401`, rather than a third alias.

**What each fake returns by default, and what that default hides.**

- `gh` answers `OPEN` and a `baseRefName` the test sets. Left at `main`,
  a build that always fetches the default branch passes. So criterion 1
  also sets a parent's branch. The fake records its argv, and criterion 1
  asserts it holds the task's `pr_url` and `state,baseRefName`.
- `build_cell_image` returns a tag that is not `cell_tag(repo)`. Criterion
  1 asserts that `reverify` received that tag.
- `allocate_network` returns one pool /24 that is not the pool's first.
  A build that computes the gateway from a fixed subnet then fails.
- `reverify` returns a green comparison with no results. It records its
  keyword arguments, and criterion 1 asserts each.
- The `record_regate` fake accepts any keywords. So the witnesses assert
  the exact keyword set, and a `base_sha` spelling fails.
- `probe_addresses` returns the gateway and one LAN address.

**The origin is real git.** Build a checkout with a bare origin added as
`origin`. Then `real_remote` reads a local path, and `fetch_parent_branch`
fetches from it. On `main`, commit a policy with no spec, then the spec,
then the task's `base_sha` with policy A. Then commit policy B with an
edited spec text, and fork a parent branch there. Fork the task's branch
from the parent's first commit, with a packaged commit. Move the parent
and `main`. Then make the review commit merge moved `main` into the task's
branch, as GitHub's "update branch" does. Push all three branches. Make each
policy's `protected` list differ, so the witness can name which export it
read. Then rewrite the working copy's policy and spec, so a read of the
checkout shows. Seed the repo row with the origin's path and a run at
`base_sha`. Seed a task with the spec's sha. Call `set_task_package` with
the packaged commit and a pull request URL. The merge base is then moved
`main` for `main`, where `pushed_sha` would give the policy B commit. For
the parent's branch it is the parent's first commit. Every commit but
`base_sha` holds a spec text whose sha is not the task's. Criterion 1 also asserts that `reverify` was handed the mirror at
`_mirror_path`'s path.

**Criterion 3's cases.** Seed a run at the commit with no spec for the
missing file. Seed a `spec_sha` of zeros for the mismatched text. Call
`record_spec_text` with origin `revision` for the recorded text. Seed the
task under a second repo row for another repo.

**Criterion 5** sets its own SIGTERM handler before `main`, and restores
the earlier one in a `finally`. Its `reverify` fake sends the process
SIGTERM. With the guard, `main` returns 143 and the test's handler never
runs. Without it, the test's handler runs and `main` returns 0.

**Five residuals, one line each.**

- The probe adds one ephemeral container on the base image, as
  `run_one_cell`'s does.
- A baseline gate that errors raises out of `reverify`, and the command
  exits 2. Gates read from an old `base_sha` can name a role a newer tree
  lacks.
- A head pushed while the suite runs is not the head recorded. The record
  names the head it judged.
- The cell image is built from the checkout, as `saffron cell` builds it.
- An old `base_sha` whose policy or spec today's parser refuses raises,
  and the command exits 2.

**Wrong versions.** Each criterion lists the ones its witness must kill.
A prototype's witnesses killed all 38 on 2026-10-12 and passed with the
change. Do not run them yourself.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** No path in `touches` is in `elevate_on`, so the task is
`standard` and `size` is advisory. A prototype measured 1910 tokens with
`size_gate`'s counter against the `feature` ceiling of 3000. It held the
module, the dispatch and docstring edit, the five witnesses, the
`CLAUDE.md` line and the `README.md` paragraph. `record_regate` and
`allocate_network` were stand-ins outside the count. The witnesses were 1234 tokens of it.
`estimated_lines` is that count over four.
