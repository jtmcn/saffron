---
id: SA-0300
title: Hand numbering reads no ledger, so an id a refused follow-up took is handed out twice
type: feature
priority: 3
estimated_lines: 194
estimate_measured: true
touches:
  - saffron/cli.py
  - saffron/follow_up.py
  - tests/test_next_id.py
  - docs/agents/issue-tracker.md
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
  - docs/adr/**
  - docs/appendices/**
  - docs/backlog/**
  - docs/evidence/**
  - docs/superpowers/**
  - docs/host/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/draft.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/phases/**
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/cell/**
  - tests/test_cli.py
  - tests/test_follow_up.py
  - tests/test_draft.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 22
max_attempts: 3
max_turns: 130
risk: standard
acceptance:
  - claim: >-
      `saffron next-id` prints one line, the spec id one past the highest
      number of the working tree's spec prefix. It reads the files in
      `.saffron/specs/`, the files in `.saffron/specs/done/`, and the tasks
      the home ledger holds for the repo whose `origin` is `--repo`'s. A
      ledger task whose spec file exists in neither directory counts, and a
      task of another repo does not. It exits 0 and adds no row to the
      ledger. The witness makes each of the three places hold the highest
      number in turn. It drives `--repo` omitted, with the working
      directory the checkout, and `--repo` given as a relative path.
    witness: tests/test_next_id.py::test_next_id_prints_one_past_a_task_whose_spec_file_exists_in_neither_directory
    wrong_versions:
      - The ledger left unread, so the files' highest number plus one is printed.
      - Only `.saffron/specs/` read, or only its `done/`.
      - Every task in the ledger read, whatever repo it belongs to.
      - The prefix hard-coded as `SA` rather than read from the spec files.
      - The id printed with a label or other text on its line.
      - The number taken from the files of a commit rather than the working tree.
  - claim: >-
      When the ledger holds nothing for the repo, `saffron next-id` prints one
      past the spec files' highest number and exits 0. The witness drives the
      three ways that happens. There is no ledger file under `--home`, and the
      command creates none. There is a ledger with no repo row for the
      checkout's `origin`, and the command adds none. There is a checkout with
      no `origin` remote, and the command neither raises nor adds a row.
    witness: tests/test_next_id.py::test_next_id_prints_one_past_the_files_when_the_ledger_holds_nothing_for_the_repo
    wrong_versions:
      - The home ledger constructed whether or not its file exists, which creates it.
      - "`upsert_repo` called for the checkout's origin rather than `resolve_repo_id`."
      - A checkout with no `origin` left to raise, so the command exits 2.
  - claim: >-
      When the spec files carry no id prefix, or more than one, `saffron
      next-id` exits 2 and prints no line that is a spec id. The witness
      drives a tree whose only files are not spec ids, and a tree holding
      two prefixes.
    witness: tests/test_next_id.py::test_next_id_prints_no_id_when_the_specs_hold_no_prefix_or_two
    wrong_versions:
      - A tree with no prefix falling back to `SA` and printing an id.
      - A tree with two prefixes printing an id under one of them.
      - The refusal exiting 1, or 0.
---

## Context

Backlog item **b-589cf6**. It cites `DESIGN.md` §4.2. Every line number
below was read at `e8f5529e`.

**A follow-up's id can live only in the ledger.** A stack batch names a
follow-up spec with `follow_up.next_spec_id`
(`saffron/follow_up.py:314`). A follow-up that gate 0 refuses, or that ran
and missed, is never committed (item b-589cf6, citing `SA-0151`). On
2026-10-20 batch 39 took `SA-0297` for a refused follow-up. Its text is in
the ledger alone. The home ledger holds a `QUEUED` task `SA-0297` under
this repo's row. No file named `SA-0297` exists in `.saffron/specs/` or
its `done/` at `e8f5529e` (read 2026-10-20).

**Hand numbering reads only the files.** `docs/agents/issue-tracker.md:10-11`
numbers a new spec "from the highest existing `SA-` id + 1". A hand-written
spec can then reuse a ledger-only id and share its task rows.

**The reader already exists.** `follow_up.next_spec_id(origin_id,
specs_dir, ledger, repo_id)` returns one more than the highest number
sharing `origin_id`'s prefix. It reads the live spec files, their `done/`
retirees and `ledger.tasks_by_repo(repo_id)`, and keeps `origin_id`'s
digit width (`saffron/follow_up.py:50-78`). Its ledger read is
unconditional (`saffron/follow_up.py:73`). `draft.seed_spec_id(specs_dir)`
returns the id of the highest-numbered file in those two directories. It
raises `ValueError` when the files carry no prefix or more than one
(`saffron/draft.py:55-84`). `_draft` composes the two over the working tree, so an
uncommitted spec still holds its id (`saffron/cli.py:1369-1411`). A
`ValueError` there reaches the dispatch's `except Exception`, which prints
and returns 2 (`saffron/cli.py:347-354`). `tests/test_cli.py:10257` asserts
that exit for both prefix cases.

**Opening the ledger creates it.** `Ledger.__init__` makes the parent
directory and connects, which creates the file
(`saffron/ledger.py:402-409`). So `fold`, `migrate` and `serve` dispatch
before `main` builds the home ledger (`saffron/cli.py:278-299`). `fold` and
`migrate` each wrap their call in their own `except Exception`, which
prints and returns 2 (`saffron/cli.py:278-294`). `serve` refuses a missing
ledger file (`saffron/cli.py:2304-2307`).

**Naming the repo in the ledger.** `package_phase.real_remote(repo)`
returns `origin`'s URL and raises `PackageError` when there is none
(`saffron/phases/package.py:97-104`). `ledger.resolve_repo_id(url)`
returns the repo's id, or `None` for an origin with no row, and writes
nothing (`saffron/ledger.py:1099-1107`). `upsert_repo` always leaves a row
(`saffron/ledger.py:1077-1097`).

## Problem

Add `saffron next-id [--repo <path>]`, `--repo` defaulting to the working
directory. It prints the next free spec id for that checkout on one line
and exits 0, so `$(uv run saffron next-id)` names a new spec file.

**The steps.**

1. Resolve `--repo`. Take `specs_dir` as its working tree's
   `.saffron/specs`, never an export, as `_draft` does.
2. Take the origin id from `draft.seed_spec_id(specs_dir)`. The prefix and
   digit width come from the repo's own spec files, never a literal.
3. If `<home>/ledger.db` is not a file, the ledger contributes nothing.
   Construct no `Ledger`, since its constructor would create the file.
4. Otherwise read `real_remote(repo)`. A `PackageError` means no `origin`,
   and the ledger contributes nothing. With a URL, open the home ledger and
   take `resolve_repo_id(url)`. `None` contributes nothing. Never call
   `upsert_repo`.
5. Print `follow_up.next_spec_id` over the origin id, `specs_dir`, the
   ledger and the repo id.

**No second scanner.** Widen `next_spec_id` to accept `None` for `ledger`
and for `repo_id`, and skip the ledger read when either is `None`. Its two
callers pass both today and keep doing so (`saffron/cli.py:1411`,
`saffron/follow_up.py:314`). Add one sentence to its docstring for the
`None` case.

**The dispatch.** Dispatch `next-id` beside `fold`, `migrate` and `serve`,
before the home ledger's `Ledger(` call (`saffron/cli.py:303`). Wrap it
as `fold` is wrapped, so any raise prints `saffron: <type>: <message>`
and returns 2. A tree with no prefix or two is such a raise, as it is under
`saffron draft`. Close a ledger the command opened before it returns.

**The documentation, as cell work.**

- `docs/agents/issue-tracker.md:10-11`: number a new spec with
  `uv run saffron next-id --repo .` rather than "the highest existing
  `SA-` id + 1". Say in one sentence that it reads the ledger too, because
  a refused follow-up's id lives only there.
- `CLAUDE.md`'s command list: one line after `draft`'s (`CLAUDE.md:72`).
- `README.md`'s usage: a short paragraph and block beside `regate`'s
  (`README.md:140-147`). Say that it adds no ledger row and creates no
  ledger.
- `saffron/cli.py`'s module docstring lists every subcommand
  (`saffron/cli.py:1-3`). Add `next-id`.

## Out of scope

- **Recording a refused follow-up in the files.** The item's other arm
  writes the id where the convention looks. The operator chose this arm.
- **`DESIGN.md`.** No section lists the CLI's commands, so none changes.
- **`.claude/`.** No agent or skill file there states the file-only rule
  (`git grep -n "highest existing" e8f5529e -- .claude` finds nothing).
  The queue refuses a `.claude` touch in any case
  (`saffron/scheduler.py:437`).
- **A repo with no spec file at all.** A fresh repo chooses its own first
  id. The command refuses it with exit 2.
- **An `origin` spelled differently from the ledger's row.** The ledger
  keys a repo by the exact URL (`saffron/ledger.py:1099-1107`). A checkout
  whose `origin` is the `https` spelling of a repo recorded under its `ssh`
  spelling finds no row, as `saffron queue` finds none.

## Notes for the agent

**Every criterion is new code.** The subcommand does not exist at base.
So each criterion declares a witness and no mutant, and `witness` reports
`skip` for each. With the source reverted, `next-id` is not a subcommand.
`main` then raises `SystemExit` from argparse and each witness fails. From
Saffron, the witness module imports only `saffron.cli.main` and
`saffron.ledger.Ledger`, which exist at base.

**The witnesses' shared fixture.** Put the three witnesses in a new
`tests/test_next_id.py`. Build each checkout with `git init` and, unless
the case is the one with no `origin`, `git remote add origin <url>`. The
checkout has no commit, so a read of a commit fails. Write spec files as one-line stubs. Use the prefix `TE` with four
digits, so a hard-coded `SA` fails. Seed the ledger at `<home>/ledger.db`
with `upsert_repo`, `create_run` and `create_task`, and close it before
calling `main(["--home", str(home), "next-id", ...])`. Read stdout with
`capsys` and compare it to the id and one newline exactly.

- Criterion 1: live `TE-0005-a.md`, retired `TE-0007-b.md`, a task
  `TE-0009` under the checkout's origin, and a task `TE-0050` under a
  second origin. Both `--repo` forms print `TE-0010`. Then add a live
  `TE-0012-c.md`, which prints `TE-0013`, and a retired `TE-0015-d.md`,
  which prints `TE-0016`. Count the rows of `repos`, `runs` and `tasks`
  before and after.
- Criterion 2: the same two files each time, so each case prints
  `TE-0008`. The first case's home holds no ledger, and the witness
  asserts none exists afterwards. The other two share a ledger holding
  only the second origin's `TE-0050`, so reading every repo's tasks shows.
  Count its rows before and after.
- Criterion 3: one tree holding only `README.md` and `notes.md`, and one
  holding `TE-0001-a.md` and `SY-0002-b.md`. Assert exit 2, at least one
  printed line, and no line matching a whole spec id.

**Wrong versions.** Each criterion lists the ones its witness must kill.
A prototype's witnesses killed all thirteen on 2026-10-20 and passed with
the change. Do not run them yourself.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** No path in `touches` is in `elevate_on`, so the task is
`standard` and `size` is advisory. A prototype of the whole change
measured 775 tokens with `size_gate`'s counter: 318 outside the test
paths, 457 in the witness module. The `feature` ceiling is 3000.
`estimated_lines` is that total over four.
