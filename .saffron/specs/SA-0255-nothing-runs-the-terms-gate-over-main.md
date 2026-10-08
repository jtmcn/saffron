---
id: SA-0255
title: Nothing runs the `terms` gate over main, so a widened rule turns main red and only a cell's baseline says so
type: bug
priority: 2
depends_on: []
estimated_lines: 102
estimate_measured: true
touches:
  - .pre-commit-config.yaml
  - tests/test_terms_hook.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - Makefile
  - pyproject.toml
  - uv.lock
  - .github/**
  - .saffron/**
  - .claude/**
  - hooks/**
  - saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - tests/test_prose_gate.py
  - tests/test_prose_limit_hook.py
  - tests/test_dead_gate.py
  - tests/test_saffron_gates.py
  - tests/test_retired_vocabulary_hook.py
budget_usd: 12
max_attempts: 3
max_turns: 90
acceptance:
  - claim: >-
      A `terms` hook in `.pre-commit-config.yaml`, run by its own `entry` in a
      git tree, exits 0 on a gate `pass` and non-zero on a gate `fail`. It
      reads committed files, with nothing staged, as b-1e106d's hit was. It
      fails in both kinds of file the gate reads. The witness drives a
      Markdown file in scope, `README.md`, and a class docstring in
      in-scope Python, `saffron/m.py`. Each carries `sandbox`, a phrase the
      gate reports. A tree whose `README.md` says `cell` instead passes.
    witness: tests/test_terms_hook.py::test_the_terms_hook_fails_a_tree_carrying_an_avoided_phrase
    wrong_versions:
      - An entry that reads only the staged index, as `prose-limit` does, so a committed hit passes.
      - An entry that runs the `prose` gate in place of `terms`.
      - An entry that runs the gate and ignores its verdict, though the gate exits 0 on a `fail`.
      - An entry that greps for the `status` key alone, not for its `pass` value.
      - An entry that ends in `|| true`.
      - An entry whose literal uses compact JSON separators, which the gate never prints, so the clean tree fails.
  - claim: >-
      The hook fails on a gate `error` as well. The witness runs it in a tree
      that is no git repository, where the gate cannot list its files and
      reports `error`.
    witness: tests/test_terms_hook.py::test_the_terms_hook_fails_when_the_gate_reports_an_error
    wrong_versions:
      - An entry that fails only on a `fail` verdict, so an `error` passes.
  - claim: >-
      prek runs the hook on every file the gate reads, passes it no
      filenames, and runs it at the commit stage. The witness takes every
      path tracked at the repo root that `in_scope` in
      `.saffron/gates/prose.py` accepts, the gate's own script among them.
      It asserts the hook's `files` matches each one. It asserts
      `pass_filenames` is false, and that any `stages` the hook declares
      include `pre-commit`.
    witness: tests/test_terms_hook.py::test_prek_runs_the_terms_hook_on_every_file_the_gate_reads
    wrong_versions:
      - A `files` pattern for Markdown alone, so a docstring edit like this item's never runs the hook.
      - A `files` pattern for Python alone.
      - A `files` pattern naming the scope's directories and missing its root files, such as `README.md`.
      - A `files` pattern for the gate's own script alone, so a new hit in any other file never runs the hook.
      - "`pass_filenames: true`, which hands the gate arguments it refuses with a usage line and no verdict."
      - "`stages: [manual]`, which `prek run --all-files` skips, so CI never runs the hook."
---

## Context

Backlog item **b-1e106d**, found in the spec loop's run 30. Tier 2. It cites
`DESIGN.md` §5.4, whose rule is that only new failures count. A failure on
`base_sha` is subtracted from every cell's result.

**What happened.** By the item's account, the first cell of run 30 printed
`terms=fail` on its baseline line. The hit was the `Spec` class docstring in
`saffron/intake.py` from 2026-08-19. The gate began reading docstrings at
`9ef9e7b2`, and `main` failed `terms` from then on. Baseline subtraction
spared every cell and hid any new hit in that file. #720 reworded the line by
hand.

**Why nothing saw it.** CI runs `uvx prek run --all-files` and then
`uv run pytest -q` (`.github/workflows/ci.yml:18-19`). `make check` runs
the same `prek run --all-files` (`Makefile:8-9`). No prek hook runs `terms`.
The `prose-limit` hook (`.pre-commit-config.yaml:85-92`) runs
`hooks/prose_limit.py`. That script lists only staged files, through
`--cached` (`hooks/prose_limit.py:53-56`). It runs the `prose` rules alone
(`hooks/prose_limit.py:108`). The suite runs `terms` only over fixture trees,
such as `tests/test_prose_gate.py:536-549`. The one place the gate meets the
whole tree is a cell, where subtraction hides it.

**The model to copy.** The `dead` hook (`.pre-commit-config.yaml:22-37`)
closed the same gap for `dead`. It is a `repo: local`, `language: system`
hook with `pass_filenames: false`. Its entry runs the gate, tees the JSON to
stderr, and greps for the `pass` verdict. The gate exits 0 whatever it
found, so the hook reads `status` instead (`.pre-commit-config.yaml:24`).
`tests/test_dead_gate.py:401-447` holds that hook. `_hook_config` reads the
hook from the file prek reads, by its `id`. One test asserts that the grep
literal appears in a passing gate's output and in no failing or erroring
one. Another asserts that `pass_filenames` is false and which paths
`files` matches.

**The gate.** `.saffron/gates/terms` execs `prose.py terms`
(`.saffron/gates/terms:2`). `Policy.gate_executables` maps the declared
`terms` gate to that file (`saffron/repos/policy.py:87-90`). The script
lists the tree with `ls-files` and `--others`, so untracked files count
(`.saffron/gates/prose.py:604-613`). It keeps each path `in_scope` accepts
(`:198-203`, `:652-658`). It prints one JSON line through `_emit`, built by
`json.dumps`, and returns 0 (`:599-601`). Its status is `fail` on any hit
and `pass` on none (`:688-696`). A failed `git ls-files` is an `error`
(`:646-651`). Any argument list other than one gate name prints a usage line
to stderr and returns 2, with no JSON (`:624-626`). The phrases are
`AVOIDED` (`:151-159`), and `sandbox` is the first. Python scope is
`CODE_DIRS` (`:53-63`), which includes `.saffron/`.

**Measured at base `958db033`, on the host, 2026-10-07.** `uv run python
.saffron/gates/prose.py terms` over this tree printed `pass`, with
`0 failures in 762 files`, in about 17 seconds. A prototype of this change
ran its entry over fixture trees holding a copy of `.saffron/gates/`. A
clean `README.md` exited 0. A `README.md` or a class docstring carrying `sandbox`
exited 1, and so did a tree with no git repository. `prek run terms
--all-files` over the base tree passed. With one staged line carrying
`sandbox` in `docs/backlog/PRIORITY.md`, `prek run terms` failed and printed
the gate's `fail` line.

## Problem

`terms` runs over the whole tree only inside a cell, where subtraction hides
a failure on `main`. Add a `terms` hook that runs the gate over the whole
tree. It fails on any verdict but `pass`, as the `dead` hook does for `dead`.

- **The hook.** A `repo: local`, `language: system` hook with `id: terms`.
  Run the declared gate's own executable, `.saffron/gates/terms`, so the hook
  and a cell run one command. Its `files` covers every Markdown and Python
  path, since those are the only files the gate reads. Pass it no filenames.
- **Its comment.** Two lines at most, naming the reason: a widened rule
  reaches files no commit stages, so `main` went red unseen.
- **Where it goes.** Put it directly after the `dead` hook.
  `tests/test_saffron_gates.py:637` reads the file from `id: ast-grep` to its
  end. A hook placed after `ast-grep` then joins the text it searches.
- **Its test.** A new `tests/test_terms_hook.py`, holding the hook the way
  `tests/test_dead_gate.py` holds `dead`. Read the hook from
  `.pre-commit-config.yaml` by its `id`, as `_hook_config` does. The first
  two witnesses run the hook's whole `entry`, split with `shlex.split`, in
  fixture trees under `tmp_path`.

## Out of scope

- **`prose` over the whole tree.** It fails at base by design, and each
  message names its sentence (`.saffron/policy.yaml:22-25`). The
  `prose-limit` hook stays staged-only.
- **`.saffron/policy.yaml`.** `terms` stays `blocking: false` inside a cell.
  The hook blocks a commit and CI, and a cell runs no prek hook.
- **`Makefile` and `.github/workflows/ci.yml`.** Both run `prek run
  --all-files` already, so the new hook reaches them with no edit.
- **A suite test over this repo's own tree.** CI runs the hook over it. A
  test would make an advisory gate blocking for every cell through `tests`.
- **The gate itself.** `.saffron/**` is protected, and no edit there is
  needed.

## Notes for the agent

**This change is new, so no criterion declares a mutant.** The hook does not
exist at base. No `find` text could pin a spelling you have not written, so
the `witness` gate reports `skip` here. With `.pre-commit-config.yaml`
reverted, each witness finds no `terms` hook and fails, which `revert` needs.

**The fixture trees.** Copy `.saffron/gates/` whole into each tree with
`shutil.copytree`, then add the tree's own files. The copy carries the entry
whatever form it takes. `CODE_DIRS` puts the copied scripts in scope, and
they are free of avoided phrases, as the base measurement shows. For
criterion 1's trees, run `git init`, `git add -A` and `git commit`, so
nothing is staged when the hook runs. Give each
git call and each hook run an environment with `GIT_CONFIG_GLOBAL` set to
`os.devnull` and `GIT_CONFIG_NOSYSTEM` set to `1`, as `_git_in` in
`tests/test_dead_gate.py` does. Name a user with `-c` on each git call, as
`_git_in` does. For the `error` tree, skip `git init` and set
`GIT_CEILING_DIRECTORIES` to `tmp_path`, so no parent repository answers.
Keep every avoided phrase in the test file as a quoted string. The gate
reads a test file's comments and docstrings, not its strings.

**Criterion 1's witness.** Assert the exit code, not the output. Three trees:
`README.md` reading "The agent runs in a cell." exits 0. The same file with
`sandbox` for `cell` exits non-zero. A `saffron/m.py` whose class
docstring carries `sandbox` exits non-zero. That is the shape of
b-1e106d's hit.

**Criterion 3's witness.** Load `.saffron/gates/prose.py` by path inside the
test, as `_prose` in `tests/test_prose_gate.py` does, and register the
module in `sys.modules` before running it. List the tracked paths with
`git ls-files` at the repo root. Assert that `.saffron/gates/prose.py` is
among the paths `in_scope` accepts, then that `files` matches every one.

**How the lists were measured.** On 2026-10-07 a prototype of this change
and its three witnesses ran on a plain copy of the base. Each wrong version
above was applied to the hook in turn. Each failed the witness it sits under.
With `.pre-commit-config.yaml` reverted, all three witnesses failed.

**What the criteria leave undriven.** Criterion 1 drives one phrase,
`sandbox`. The gate's own tests in `tests/test_prose_gate.py` cover its
phrase list. It drives a docstring, not a comment. Criterion 3 covers the
paths tracked at the cell's head, not a path no commit holds yet.

**Where this was measured.** On the host, under `uv` and the host's git.
The cell runs the suite with `/opt/venv/bin` first on `PATH`
(`.saffron/Dockerfile:29`), so `python3` resolves there. The entry needs
`sh`, `python3`, `git`, `tee` and `grep`, and the prototype did not run in a
cell.

**The `prose` gate** counts every comment and docstring in the new test
file from zero. Write none with an em dash, a semicolon, a contraction, the
perfect tense or a sentence over 25 words. Run `python3 hooks/prose_limit.py
--file tests/test_terms_hook.py` before you commit.

**Size.** A prototype measured 406 tokens by `size_gate` over 110 changed
lines: 14 in `.pre-commit-config.yaml` and 96 in the test. The `bug`
ceiling is 1300 tokens (`saffron/gates/core/size.py:26`). Neither touched
path is in `elevate_on`, so `size` stays advisory.
