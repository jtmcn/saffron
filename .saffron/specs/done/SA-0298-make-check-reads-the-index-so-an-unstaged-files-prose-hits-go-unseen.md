---
id: SA-0298
title: The prose hook reads the index, so `make check` passes a new file that was never staged and fails a staged one already fixed
type: bug
priority: 2
depends_on: []
estimated_lines: 62
estimate_measured: true
touches:
  - hooks/prose_limit.py
  - tests/test_prose_limit_hook.py
  - .pre-commit-config.yaml
  - Makefile
  - docs/agents/issue-tracker.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .github/**
  - .saffron/**
  - .claude/**
  - saffron/**
  - ontology/**
  - images/**
  - harness/**
  - records/**
  - hooks/retired_vocabulary.py
  - docs/backlog/**
  - docs/evidence/**
  - docs/adr/**
  - docs/appendices/**
  - docs/superpowers/**
  - docs/host/**
  - docs/HOST-HARDENING.md
  - tests/test_prose_gate.py
  - tests/test_terms_hook.py
  - tests/test_dead_gate.py
  - tests/test_scheduler.py
budget_usd: 24
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      `python3 hooks/prose_limit.py --tree` reads a file git does not track,
      at its working-tree content, against zero, and exits 1 on a new
      `prose` hit. The witness drives both shapes of an unstaged new file. One
      is untracked, `docs/backlog/1-new.md`. One is intent-to-add after
      `git add -N`, `.saffron/specs/SA-0001-x.md`, whose working copy changed
      after the add. Each carries one long sentence, and stdout names each
      file and line.
    witness: tests/test_prose_limit_hook.py::test_tree_mode_reads_an_untracked_file_against_zero
    wrong_versions:
      - A tree mode that lists only `git diff HEAD`, so the untracked file is never read.
      - A tree mode that lists only untracked files, so the intent-to-add file is never read.
      - A tree mode that reads each file's staged blob, which an untracked file lacks and an intent-to-add entry holds empty.
  - claim: >-
      `--tree` reads an unstaged edit to a tracked file at its working-tree
      content against `HEAD`, in both kinds of file the gate reads. The witness
      edits a committed `README.md` and a committed `saffron/m.py` with nothing
      staged. The Markdown file gains a long sentence and the Python file a
      three-line comment block. `--tree` exits 1 and prints in the commit
      mode's format. Its stdout holds the lines `README.md: 1 new
      sentence-length hit` and `saffron/m.py: 1 new comment-block hit`, and a
      line opening with two spaces and `README.md:3: sentence-length: `. The
      no-argument commit mode still exits 0 on the same repo, since nothing
      is staged.
    witness: tests/test_prose_limit_hook.py::test_tree_mode_reads_an_unstaged_edit_against_head
    wrong_versions:
      - A tree mode that lists only `git diff --cached`, so an unstaged edit is never read.
      - A tree mode that reads Markdown alone, so the comment block passes.
      - A tree mode that prints `--file`'s format, one `N new hits against HEAD` line per file and unindented hit lines.
      - A no-argument mode rewired to read the working tree, so the commit hook refuses a commit over an edit it does not carry.
  - claim: >-
      `--tree` reads the working copy of a staged file, not the staged copy,
      and the commit mode keeps reading the staged copy. The witness stages a
      `README.md` carrying a long sentence, then rewrites the working copy
      without it. `--tree` exits 0 with empty stdout. The no-argument mode
      exits 1 on the same repo.
    witness: tests/test_prose_limit_hook.py::test_tree_mode_reads_a_fixed_working_copy_not_the_staged_one
    wrong_versions:
      - A tree mode that reads `git show :<path>`, so it reports the hit the working copy no longer has.
      - A shared helper that makes the commit mode read the working tree too, so the commit mode exits 0.
      - A no-argument mode that runs the tree mode, so the commit mode exits 0.
  - claim: >-
      `--tree` counts only new `prose` hits against each file's baseline. It
      reads only files in the gate's scope that git does not ignore. The
      witness exits 0 with empty stdout on one repo carrying six shapes at
      once. A committed `README.md` with a long sentence gains an unrelated
      line above it. A committed `docs/backlog/1-a.md` with a long sentence
      is renamed by `git mv`. A committed `docs/backlog/3-c.md` gains a
      sentence naming a sandbox, a `terms` hit and no `prose` hit. A
      committed `docs/evidence/x.md`, out of scope, gains a long sentence
      unstaged. An untracked `docs/evidence/run.md`, out of scope, carries a
      long sentence. An untracked in-scope `docs/backlog/9-ignored.md`,
      listed in `.gitignore`, carries one too.
    witness: tests/test_prose_limit_hook.py::test_tree_mode_counts_only_what_head_lacks
    wrong_versions:
      - A tree mode that reads every file against zero, so the old hit in `README.md` fails it.
      - A tree mode that drops the rename's old path, so the renamed file reads against zero.
      - A tree mode that lists untracked files without `--exclude-standard`, so the ignored file fails it.
      - A tree mode that skips the `in_scope` check, so the evidence files fail it.
      - A tree mode that applies `in_scope` to the untracked list alone, so the tracked `docs/evidence/x.md` fails it.
      - A tree mode that reuses `_new_lines`, which runs both gates in `GATES`, so the `terms` hit in `docs/backlog/3-c.md` fails it.
  - claim: >-
      `make check` runs the tree mode and skips the index mode, and a commit
      runs only the index mode. The witness reads `.pre-commit-config.yaml`
      and `Makefile`. One hook runs the tree mode with `stages: [manual]`,
      `pass_filenames: false` and `always_run: true`. The `prose-limit` hook
      declares no `stages`, so it still runs on commit.
    witness: tests/test_prose_limit_hook.py::test_make_check_runs_the_tree_hook_and_a_commit_does_not
    wrong_versions:
      - A tree hook with no `stages`, which runs on commit and refuses a commit over an untracked file it does not carry.
      - "A `stages: [manual]` added to `prose-limit`, so a commit runs no prose limit at all."
  - claim: >-
      `make lint` calls prek twice, in order, whichever way the first call
      ends. The first is `prek run --all-files --skip prose-limit`. The second
      is `prek run --all-files --stage manual prose-limit-tree`. The recipe
      exits non-zero when either call fails, and 0 when both pass. The
      witness runs the `lint` recipe from `Makefile` as make would, against a
      stub `prek` on `PATH` that logs its arguments. It drives three cases.
      Both calls pass, the first fails, and the second fails. Each case logs
      both calls, and only the first case exits 0.
    witness: tests/test_prose_limit_hook.py::test_lint_runs_the_tree_hook_after_a_failure_and_still_fails
    wrong_versions:
      - A `lint` recipe left as `prek run --all-files`, which skips every manual hook.
      - A recipe of two plain lines, which make stops after the first failure, so the tree hook never runs.
      - A recipe joining the two calls with `;` alone, which exits 0 when only the first call fails.
      - A recipe ending the first call in `|| true`, which exits 0 when only the first call fails.
      - "A recipe writing `status=$?` and `exit $status` with a single `$`, which make expands to `exit tatus`, so a clean tree fails `make lint`."
      - A recipe whose first call carries a leading `-`, so make ignores its failure and the recipe exits 0 when only the first call fails.
      - A first call that does not skip `prose-limit`, so a staged copy the working tree has fixed still fails `make check`.
      - A second call of `prek run --all-files --stage manual` with no hook id, which reruns every hook, `prose-limit` included.
---

## Context

Backlog item **b-08a36a**, tier 2, filed 2026-09-19 from PR #378. It recurred
in the spec loop's runs 39 and 45. Line numbers below were read at
`e8f5529e`.

**The hook reads the index.** `.pre-commit-config.yaml:100-107` declares the
`prose-limit` hook with `entry: uv run hooks/prose_limit.py` and
`pass_filenames: false`. With no arguments, `main` runs `commit_time`
(`hooks/prose_limit.py:215`). `commit_time` takes its file list from `staged`
(`:103`). `staged` lists `git diff --cached --name-status -M -z
--diff-filter=AMR` (`:53-58`). `commit_time` reads each file's staged blob
with `git show :<path>` (`:100-107`).

**`make check` runs that hook.** `Makefile:8-9` makes `lint` the single
command `prek run --all-files`, and `check` is `lint test` (`Makefile:18`).
Two consequences follow, and the item measured both.

- **An unstaged file is invisible.** An untracked file never reaches
  `staged`. The item measured a file after `git add -N` passing too, since
  that entry stages no content.
- **A staged file is read at its staged content.** After a refused commit,
  a copy fixed in the working tree still fails. The hits name lines it no
  longer has.

**prek cannot hand the hook the working tree.** `prek run --help` (prek
0.5.3) says `--all-files` runs hooks "on all tracked files". Measured
2026-10-20 in a scratch repo with a hook that echoes its arguments. It got
the tracked file and the intent-to-add file, and no untracked file. So the
hook lists its own files, and `pass_filenames` stays false.

**prek skips a manual-stage hook unless asked.** Measured 2026-10-20 in a
scratch repo with prek 0.5.3 and a hook declaring `stages: [manual]`. Plain
`prek run --all-files` did not run it. `git commit` with the pre-commit hook
installed did not run it either, with an untracked file present. Then
`prek run --all-files --stage manual <id>` ran that hook alone.
`prek run --all-files --stage manual` with no id ran every hook, since a hook
with no `stages` runs at every stage. `prek run --all-files --skip <id>`
reported that hook `Skipped`.

**A file mode exists and reads one file.** `--file <path>` reads the working
copy against `HEAD` (`hooks/prose_limit.py:144-169`), for both gates in
`GATES` (`:138`). It takes one path, and nothing in `make check` calls it.

**Who reads `make check`.** `docs/agents/issue-tracker.md:85-86` tells a spec
author to run `make check` before pushing a spec. CI runs
`uvx prek run --all-files` on a clean checkout (`.github/workflows/ci.yml:18`),
where nothing is staged or unstaged. `CLAUDE.md:228-230` says the
no-argument mode reads the staged index. That stays true here.

## Problem

Add a third mode, `python3 hooks/prose_limit.py --tree`. It asks the
commit mode's question of the working tree instead of the index. It reads every
in-scope file the working tree adds, modifies or renames against `HEAD`,
staged or not. It also reads every untracked file git does not ignore. Each is
read at its working-tree content. Its baseline is the `HEAD` copy, or the old
path's `HEAD` copy for a rename git detects, or zero for a new file. It runs
the `prose` gate alone, as the commit mode does
(`hooks/prose_limit.py:108`). It prints in the commit mode's format and
exits 1 on any new hit, else 0.

Wire it into `make check`. Add a local hook to `.pre-commit-config.yaml` that
runs the tree mode at the manual stage only, with `always_run: true`. Change
the `lint` recipe in `Makefile` to call prek twice. The first call runs
`prek run --all-files` skipping `prose-limit`. The second runs the manual
stage with the new hook's id alone. The second call runs even when the first
fails, so a ruff failure cannot hide a prose hit. The recipe still exits
non-zero when either fails. Keeping the first call's status in a shell
variable does this in one recipe line, written as `$$` for make.

Leave the commit mode as it is. `prose-limit`'s config entry stays unchanged,
and the no-argument mode keeps reading the index. The per-commit limit
belongs there.

Add two sentences to `docs/agents/issue-tracker.md` after the `make check`
sentence at `:85-86`. The first says `make check` reads each changed file's
working-tree copy, staged or not, while the commit hook reads the index. The
second says a file moved with plain `mv` reads against zero there until
`git add -A` stages the rename.

## Out of scope

- **The `terms` rules in tree mode.** The commit mode runs `prose` alone,
  and the `terms` hook already scans the tree (`.pre-commit-config.yaml:41-52`).
- **A rename git cannot see.** A file moved with plain `mv` and never staged
  shows as a deletion and an untracked file. Tree mode reads the new path
  against zero, so its old hits fail `make check`. No witness drives it, and
  the claim names only `git mv`. The `issue-tracker.md` sentence names the
  fix, `git add -A`.
- **CI.** `.github/workflows/ci.yml:18` keeps `prek run --all-files`. A clean
  checkout has no working-tree change for the tree mode to read.
- **Two sentences this change makes false.** `CLAUDE.md:30` says
  `lint = prek run --all-files`. `.claude/skills/create-saffron-spec/SKILL.md:73-75`
  says the lint pass reads tracked files only, so an untracked spec passes
  it. Both go false only when this change lands, and both files are
  forbidden here. The delegate edits them in a review commit on this cell's
  pull request. The new wording says only the `prose-limit-tree` hook reads
  the working tree. The `--all-files` hooks still read tracked files only.
- **`.claude/agents/spec-writer.md`.** It stays true as written, and it is
  forbidden here.
- **A file staged as added, then deleted from the working tree.** Neither
  listing names it. Measured with git 2.54.0 and 2.47.3, for a file added
  with `git add`, one added with `git add -N`, and a `git mv` target, each
  then removed. So tree mode never reads it, and no witness drives it.

## Notes for the agent

**Each criterion is new code**, so each declares a witness and no mutant,
and `witness` reports `skip`. Write all six tests in
`tests/test_prose_limit_hook.py`, beside the `--file` tests, with its
`_repo`, `_stage`, `_hook` and `_git` helpers.

**Each witness fails at base.** There `main` refuses `--tree` as an
unexpected argument and exits 2 (`hooks/prose_limit.py:203-214`). The fifth
finds no tree hook in the config. The sixth logs one call,
`run --all-files`. Measured on a prototype: all six failed with
`hooks/prose_limit.py`, `.pre-commit-config.yaml` and `Makefile` reverted.
Each wrong version under every criterion failed its witness.

**Run the recipe without make.** The cell image has no `make` (measured
2026-10-20 in `saffron/cell:saffron`). So the sixth witness reads the `lint`
recipe from `Makefile` and runs it the way make does. Each logical line,
after joining a backslash continuation, goes to its own `sh -c`. It strips a
leading `@`, `-` or `+`, and a `-` makes it ignore that line's status. It
reads `$$` as `$`. It expands any other `$` reference to nothing, as make
does: `$x`, `$(...)` and `${...}` alike. It stops at the first line that
exits non-zero. The stub reads
an environment variable naming which call fails. Measured on a prototype:
the real `make lint` with a ruff failure ran both calls and exited 2. Real
make with a stub `prek` agreed with that emulation on the single-`$` recipe.
That recipe exited 2 with both calls passing, since `$status` became `tatus`.

**Name the hook `prose-limit-tree`.** The fifth witness and the `lint`
recipe both select it by id. Measured with `--dry-run`, `--skip` matches by
exact id, so skipping `prose-limit` leaves it alone.

**Write `.pre-commit-config.yaml` through Bash.** The Write tool refuses that
path whatever `allowed_tools` grants (`saffron/agents/context.py:143-154`). Run
a short python3 script through Bash to append the hook.

**The listing.** Measured with git 2.54.0 on the host and git 2.47.3 in
`saffron/cell-base:python`. `git diff HEAD --name-status -M -z
--diff-filter=AMR` listed a staged `git mv` as `R100` with both paths, and an
intent-to-add file as `A`. It did not list an untracked file. `git ls-files
--others --exclude-standard -z` listed that file alone. The commit mode's
parse (`hooks/prose_limit.py:59-70`) reads the first command's output as
written.

**Size.** Measured at 238 changed tokens by `size_gate` on the prototype, with
495 more under `tests/**` uncounted. That is under the `bug` ceiling of 1300.

**The `prose` gate** reads `hooks/` and `tests/`. A new comment or
docstring takes no em dash, semicolon, contraction or perfect tense. It takes
no sentence over 25 words, and a docstring stays within ten lines. Check each
file with `python3 hooks/prose_limit.py --file <path>`.
