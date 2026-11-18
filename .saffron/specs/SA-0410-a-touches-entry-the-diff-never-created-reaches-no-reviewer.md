---
id: SA-0410
title: A `touches` entry the diff never created reaches no reviewer
type: feature
priority: 2
estimated_lines: 182
estimate_measured: true
touches:
  - saffron/gates/core/scope.py
  - saffron/gates/suite.py
  - saffron/cell/worktree.py
  - tests/test_worktree.py
  - tests/test_suite.py
  - tests/test_constant_mutants.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cell/session.py
  - saffron/phases/**
  - saffron/report/**
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/replay.py
  - tests/test_session.py
  - tests/test_package.py
  - tests/test_review.py
budget_usd: 56
max_attempts: 3
max_turns: 245
risk: standard
acceptance:
  - claim: >-
      At head, a passing `scope` result names each literal `touches` entry
      that is absent at the cell's base and that the diff did not create. A
      literal entry holds no `*` and no `?`. Its summary is the pass count,
      then `; touches entries absent at base and never created: `, then those
      entries in `touches` order, joined by `, `. Two such entries in the
      middle of an eleven-entry `touches` are both named. Never named are a
      glob in each of its forms (`**`, `*` and `?`), a path present at base
      (a directory, and a file whose name holds `[`), a file the diff
      creates, a file the diff deletes, and a directory whose only file the
      diff deletes. The status stays `pass` with no
      failure. The baseline summary for the same spec names nothing. The
      lenses' gate text carries the whole summary on the `scope` line.
    witness: tests/test_worktree.py::test_a_passing_scope_names_each_touches_entry_the_diff_never_created
    wrong_versions:
      - Every entry not in the changed files is a candidate, a glob included, so `lib/**` is named.
      - Only `*` marks a glob, so `README?.md` is named.
      - Every literal entry outside the changed files is named with no read of the base, so `src/x[1].py` and `docs` are named.
      - The changed files are not taken out first, so `src/made.py`, which the diff creates, is named.
      - Presence is read at HEAD and the changed files are not taken out, so `old.py`, which the diff deletes, is named.
      - Presence is read at HEAD with the changed files taken out, so `lib/old`, whose only file the diff deletes, is named.
      - The base read lists files alone (`ls-tree -r`), so the directory entry `docs` is named.
      - The base read matches each entry as a shell pattern over the base listing, so `src/x[1].py` is named.
      - The entries are sorted, so `new_top.py` comes before `src/gone/deep.py`.
      - Only the first entry found is named.
      - The line is a new failure, so `scope` reads `fail`.
      - The baseline call asks too, so its summary names `src/gone/deep.py`, `src/made.py` and `new_top.py`.
  - claim: >-
      When no literal entry is left to ask the base about, the head call
      sends the cell exactly the commands its baseline call sent, in order.
      Two kinds of `touches` leave none: a glob in each of its forms, and a
      literal path the diff created or deleted. A spec with an entry left to
      ask about sends more at head than at its baseline.
    witness: tests/test_worktree.py::test_a_scope_with_no_literal_entry_left_to_ask_reads_nothing_more
    wrong_versions:
      - The base is read whenever the gate is handed the read, with an empty list when nothing is left, so the head call sends one more command.
      - The baseline call reads the base too, so the head call sends one command fewer than its baseline.
  - claim: >-
      `worktree.absent_at(target, base_sha, paths)` returns each of `paths`
      with no entry in `base_sha`'s tree, in the order given. Two absent
      paths around a present one come back as those two, in order. The read
      names `base_sha` itself. When git exits nonzero it raises `runtime.CellRuntimeError` carrying git's stderr, so
      a failed read is never taken as an empty tree.
    witness: tests/test_worktree.py::test_a_failed_read_of_the_base_raises_rather_than_naming_every_path
    wrong_versions:
      - The exit code is not read, so a refused read returns every path as absent.
      - A refused read returns an empty list, so nothing is named and nothing raises.
      - The absent paths come back in reverse order.
      - The absent paths come back sorted, as a set difference.
      - The read ignores `base_sha` and reads HEAD.
  - claim: >-
      A spec whose `touches` are all globs keeps its baseline summary and its
      head summary as they read at base.
    witness: tests/test_session.py::test_the_baseline_scope_neither_invents_nor_cancels_an_escape
    preserves: true
  - claim: >-
      A head suite over a real git tree whose literal `touches` are present
      at base still reports one new failure, from `witness`, and no drift.
    witness: tests/test_constant_mutants.py::test_a_find_repeated_at_head_is_one_new_failure_and_no_drift
    preserves: true
---

## Context

Backlog item **b-71e2df**, tier 2, cites `DESIGN.md` §3.2 and §5.4. It was
found by the Spec seat on #908. `SA-0280` listed
`saffron/gates/core/constant_mutants.py` in `touches`, the cell put the code
in `witness.py`, and the listed file was never created. No review saw it, and
no gate reports it. The item's related record is **b-281f0a**. Every line
below was read at `26754f35`.

**What `scope` says on a pass.** `scope_gate` returns `pass` with the summary
`"{n} changed files within touches"` (`saffron/gates/core/scope.py:109-114`).
It treats `**/`, `**`, `*` and `?` as glob tokens and nothing else
(`saffron/gates/core/scope.py:21`). It is handed the changed files, the
`touches`, the diff and the two deny lists (`saffron/gates/core/scope.py:43-50`),
and nothing that reads the base tree.

**Where it is called.** `GateSuite._run` calls it first among the core gates
(`saffron/gates/suite.py:214-221`). `baseline` reaches `_run`
(`saffron/gates/suite.py:147-152`), and so does `against`
(`saffron/gates/suite.py:154-159`). The suite reads its tree only
through the `Tree` protocol (`saffron/gates/suite.py:59-74`). `CellTree` is
the production adapter, and each of its reads is one `worktree` function over
the container (`saffron/gates/suite.py:77-103`). Two test adapters implement
the same protocol: `_Tree` (`tests/test_suite.py:21-67`) and `_GitTree`
(`tests/test_constant_mutants.py:54-90`). One test declares
the literal `touches` `guard.py`, `pytest.ini` and `tests/test_guard.py`
(`tests/test_constant_mutants.py:516`). It then judges its head commit through
that adapter (`tests/test_constant_mutants.py:536`). PACKAGE's own `scope_gate` call
passes no suite (`saffron/phases/package.py:1309`), and neither does replay's
(`saffron/replay.py:165`).

**How the summary reaches a lens.** REVIEW's lenses are shown
`review.gate_summary` over the Gate-only cell's comparison
(`saffron/cell/session.py:3469-3473`). That comparison is
`suite.against(CellTree(container, cwd=repo), baseline)`
(`saffron/cell/session.py:1878`). `gate_summary` writes one line per result,
ending `— {summary}` when there is one (`saffron/phases/review.py:170-188`).
The pull request's gate table renders the same summary in its last column
(`saffron/report/pr_body.py:569-578`). Two more head calls reach `against`
and so carry the line too. GATE ⇄ REPAIR judges each attempt there
(`saffron/cell/session.py:3092`). PACKAGE's re-verification judges the
packaged head in a cell of its own (`saffron/phases/package.py:623-624`).

**What the changed files hold.** `worktree.changed_files` lists
`base..HEAD` under the diff flags (`saffron/cell/worktree.py:887-896`).
`DIFF_FLAGS` carries `--no-renames` (`saffron/cell/worktree.py:195-229`). So a
deleted or renamed-away path is a changed file.

## Problem

A `touches` entry is a promise about the diff. A literal one that names a new
file the diff never made reaches the reviewer as nothing at all. Say so in
the one place every lens already reads.

1. **The line.** A passing `scope` result at head names some `touches`
   entries after its count. Each is literal, absent at the base and outside
   the changed files. The exact text is in criterion 1. Entries keep their
   `touches` order.
2. **Literal means no glob token.** An entry holding `*` or `?` is never
   named, matched or not. A `[` is literal, as `matches` reads it.
3. **The base decides.** A path present at the base is never named, a
   directory included. The changed files are taken out before the base is
   asked, so a created file and a deleted one are never named. A
   directory the diff empties is still present at base.
4. **Head only.** The baseline call names nothing and reads nothing more.
5. **Nothing left, nothing read.** A `touches` of globs and changed
   files leaves the base nothing to answer. Its head call sends the cell
   only the commands its baseline call sent.
6. **Reported, never refused.** The status stays `pass`, no failure is
   added, and no gate status is new. A spec can list a path the work turned
   out not to need.

## Out of scope

- **A `fail` result.** It already names each path it judges. This spec asks
  for the line on a `pass` alone.
- **Refusing a new module under `saffron/gates/core/` that is not a gate.**
  That is the item's first arm. It is this repo's own rule, read by
  `tests/ontology/test_vocabulary_agrees_with_code.py`, so core cannot hold
  it (`DESIGN.md` §2.1). b-71e2df stays partial on it.
- **The two direct `scope_gate` calls.** PACKAGE's own scope check and
  replay hand it no base read, so their summaries do not change.
- **A literal directory entry whose files the diff creates.** Say
  `touches` lists `pkg` beside `pkg/**`, and the diff adds `pkg/a.py`. Then
  `pkg` is absent at base and is not itself a changed file, so it is named.
  The claim covers a created file alone. Leaving a directory out would cost
  a prefix check and a fixture of its own, for a `touches` shape no spec here
  uses.
- **A glob that matches nothing.** This spec never names it, and leaves
  reporting it to a later item.
- **`DESIGN.md`.** §5.4's gate roles row for `scope` is protected. One
  sentence naming this line is added by hand in this spec's own pull request.

## Notes for the agent

**Edit or new.** The line, the base read and the new `Tree` member are new
code. So criteria 1 to 3 declare a witness and no mutant, and `witness` will
report `skip` for them. Two spellings are fixed: the line's text in
criterion 1, and `worktree.absent_at`'s name and arguments in criterion 3.
The rest is yours. Criteria 4 and 5 name tests
that exist at your base and must stay green.

**A shape that fits.** Give `scope_gate` one keyword argument, defaulting to
`None`, that takes the literal candidates and returns those the base lacks.
`GateSuite._run` passes it on the `against` call alone, as a call to a new
`Tree` member, `absent_at(base, paths)`, at `self.diff_base`. Keep `_run`'s
other callers unchanged. `tests/test_constant_mutants.py` calls `_run`
directly. `CellTree.absent_at` calls `worktree.absent_at`, the function
criterion 3 names. One `git --literal-pathspecs ls-tree -z --name-only
--full-tree <base> -- <paths>` through `_git` answers every path at once. It
prints a directory entry by its own name, and a path under a missing
directory prints nothing. A bad tree-ish exits 128. Measured on host git
2.54.0 and the cell image's git 2.47.3 (2026-11-17). Add
`absent_at` to `_Tree` (an empty list) and to `_GitTree` (its own `ls-tree`),
or the protocol and criterion 5's test break. Add no module under
`saffron/gates/core/`, which is the trap the item records.

**The witnesses.** Add all three to `tests/test_worktree.py`, which has a
real host git seam. `_exec_in` runs `runtime.exec_` on the host
(`tests/test_worktree.py:1323-1336`), and `_commit` commits all of a tree
(`tests/test_worktree.py:1197-1210`).
`test_the_suite_judges_cited_ids_against_the_spec_files_at_head` builds a
`CellSpec`, a `GateSuite` and a `CellTree` over that seam
(`tests/test_worktree.py:1213-1267`). Share one helper between criteria 1 and
2. It sets `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` to `os.devnull` and
inits a repo. It writes `src/a.py`, `src/x[1].py`, `docs/guide.md`,
`old.py` and `lib/old/only.py`. It installs a spy over `_exec_in` that records each command, then
commits the base. It takes `suite.baseline`. At head it edits `src/a.py`,
adds `src/made.py`, and deletes `old.py` and `lib/old/only.py`. Then it commits and calls
`suite.against`. It returns both suites and the commands each call sent. Use
`Policy(gates={}, ...)`, so no declared gate is invoked.

For criterion 1, declare these eleven entries in this order: `src/a.py`,
`src/gone/deep.py`, `src/x[1].py`, `lib/**`, `lib/old`, `docs`, `src/made.py`,
`new_top.py`, `old.py`, `lib/*.py`, `README?.md`. Assert the head result's
status, failures and summary together, as one tuple, with the summary
compared whole. Assert the `scope` line of `gate_summary` over the head
results is the whole line, and the baseline summary is
`0 changed files within touches`. The head summary is the positive case for
that baseline read.

For criterion 2, drive the same helper twice under one `tmp_path`, each in
its own subdirectory. First with criterion 1's entries, and assert the head
call sent more commands than the baseline call. That is the spy's positive
case. Then with `src/**`, `old.py`, `src/made.py`, `lib/**`, `lib/*.py` and
`README?.md`, and assert the two command lists are equal.

For criterion 3, stub `worktree.runtime.exec_` to record each command and
answer twice: first exit 0 with `docs` and a NUL, then exit 128 with a
stderr. Call `absent_at` with `z.py`, `docs` and `a.py` each time. The first
returns `["z.py", "a.py"]`, which is the positive case, and its command holds
the base sha. The second raises, matching the stderr.

Import nothing new at module scope in a witness file. A name the change adds
would make the reverted witness a collection error, which `revert` reads as
`skip`.

**Measured on a prototype, 2026-11-17.** The change above and the three
witnesses were built at `26754f35`. Each witness failed with `saffron/`
reverted. Each of the 19 wrong versions above was applied, one at a time, and
each failed its criterion's witness. `ruff check`, `ruff format --check` and `ty check`
passed on the six Python files. `python3 hooks/prose_limit.py --file` read
no new hit on each, once two first drafts were cut. `scope_gate`'s docstring
is already over ten lines, so a sentence added to it is a `prose` hit, and
"may" reads as a hedge. By `size_gate` the diff counted 727 changed tokens,
508 of them under `tests/**`.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. Keep each docstring within ten lines.

**Size.** The `feature` ceiling is 3000 changed tokens. `saffron/gates/**`
and `saffron/cell/**` are both `elevate_on` entries, so `size` blocks here.
