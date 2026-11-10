---
id: SA-0363
title: Regate, package and review load a spec with no mutant from the ref, so they judge a witness the cell set aside
type: bug
priority: 2
estimated_lines: 50
estimate_measured: true
touches:
  - saffron/mutants.py
  - saffron/regate.py
  - saffron/commit_review.py
  - saffron/task.py
  - tests/test_regate.py
  - tests/test_commit_review.py
  - tests/test_task.py
  - tests/test_cli.py
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
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/end_review.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/cell/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 64
max_attempts: 3
max_turns: 290
risk: standard
acceptance:
  - claim: >-
      `saffron regate` judges a task's pull request with the mutants its row
      pins. A task whose row pins a mutants commit, where the witness's mutant
      lies outside the diff, regates green. It exits 0 and records no new
      failure, though the ref has since moved to a commit whose mutant names
      the diff's own file. The spec `reverify` receives carries the pinned
      commit's mutant. A task whose row pins no commit attaches no mutant,
      though the ref holds one. Its witness is judged, so it records one new
      failure and exits 1.
    witness: tests/test_regate.py::test_regate_judges_a_witness_its_cells_revert_set_aside_and_finds_no_new_failure
    wrong_versions:
      - Regate reads the mutants at the ref's current head rather than at the commit the task's row pins.
      - A task whose row pins no commit reads the ref's current head instead of attaching nothing.
      - Regate attaches the mutants to a copy and still hands `reverify` the spec it loaded from the base export.
  - claim: >-
      `saffron regate` declines a task whose pinned mutants commit it cannot
      read, before the image or any cell. A commit the mirror lacks, and a
      commit whose `<spec id>.yaml` does not parse, each print one `regate:`
      line naming the commit's first 12 characters or the file. Each exits 1,
      builds no image, never reaches `reverify` and records no regate row. A
      readable pinned commit regated first in the same witness builds the
      image, reaches `reverify` and records a row.
    witness: tests/test_regate.py::test_regate_declines_a_mutants_commit_it_cannot_read_before_any_cell
    wrong_versions:
      - A commit the mirror lacks reaches `read_mutants`, whose git failure exits 2.
      - Only the missing commit is declined, so a mutants file that does not parse escapes and exits 2.
      - The mutants are attached after the image is built, so a declined task still builds it.
  - claim: >-
      `saffron adopt` moves an `EXHAUSTED` task to `READY_FOR_REVIEW` when its
      row pins a mutants commit whose mutant sets the witness aside. Its own
      regate, through `regate.run_regate` with no fake, records no new failure
      on the adopted head.
    witness: tests/test_regate.py::test_adopt_moves_a_task_whose_witness_its_cell_set_aside_to_ready_for_review
    wrong_versions:
      - The mutants are attached in `cli._regate` rather than in `run_regate`, so adopt's regate attaches none and keeps the task `EXHAUSTED`.
  - claim: >-
      `saffron package` hands `package()` the spec with the mutants the task's
      row pins. A row pinning a commit packages that commit's mutant, though
      the ref has moved on, and builds the image. A row pinning none packages
      no mutant, though the ref holds one.
    witness: tests/test_task.py::test_package_hands_package_the_mutants_the_tasks_row_pins
    wrong_versions:
      - "`package_ready_task` attaches the mutants and still passes `ready.spec` to `package()`."
      - The package path reads the ref's current head rather than the row's commit.
      - A row pinning no commit reads the ref's current head.
  - claim: >-
      `package_ready_task` returns `Refused` for a pinned mutants commit it
      cannot read. A commit the mirror lacks, and one whose `<spec id>.yaml`
      does not parse, each give a one-line reason naming the commit's first 12
      characters or the file. Neither builds the image or calls `package()`.
      The same harness builds the image and calls `package()` for a readable
      commit, under the criterion above.
    witness: tests/test_task.py::test_package_refuses_a_mutants_commit_it_cannot_read_before_the_image
    wrong_versions:
      - The refusal comes after `build_cell_image`.
      - A mutants file that does not parse raises out of `package_ready_task` rather than returning `Refused`.
      - The reason keeps the parser's newlines.
  - claim: >-
      `saffron review` hands its lenses the spec with the mutants the task's
      row pins. A row pinning a commit reviews with that commit's mutant,
      though the ref has moved on. A row pinning none attaches no mutant,
      though the ref holds one. Both read a recorded spec text.
    witness: tests/test_commit_review.py::test_review_hands_its_lenses_the_spec_with_the_mutants_the_tasks_row_pins
    wrong_versions:
      - Review reads the mutants at the ref's current head.
      - Review attaches the mutants only to a spec loaded from the base export, so a recorded spec text reaches the lenses with none.
  - claim: >-
      `saffron review` declines a task whose pinned mutants commit it cannot
      read, before any cell. A commit the mirror lacks, and one whose
      `<spec id>.yaml` does not parse, each print one `review:` line naming
      the commit's first 12 characters or the file, and exit 2. Neither
      reaches the layer review. A readable pinned commit reviewed first in the
      same witness reaches it.
    witness: tests/test_commit_review.py::test_review_declines_a_mutants_commit_it_cannot_read_before_any_cell
    wrong_versions:
      - A mutants file that does not parse escapes the decline and exits 2 through `main`'s catch-all with no `review:` line.
      - Review declines with exit 1, as regate does, rather than its own 2.
  - claim: >-
      `run_task` still attaches the mutants at the commit a given task's row
      pins, and at the ref's head for a fresh task. A given task whose row
      pins none still attaches no mutant.
    witness: tests/test_task.py::test_run_task_hands_its_cell_the_mutants_the_ref_holds_at_the_tasks_commit
    preserves: true
  - claim: >-
      `run_task` still refuses an inline mutant, an unreadable mutants file,
      a disclosed mutant and a pinned commit the mirror lacks, each before
      any cell, with one printed line and the same reason.
    witness: tests/test_task.py::test_run_task_refuses_an_inline_mutant_or_an_unreadable_mutants_file_before_its_cell
    preserves: true
---

## Context

Backlog item **b-c5da95**, filed reviewing `SA-0338`. It cites `DESIGN.md`
§5.4.1. Every line below was read at `f681ad39`.

**What `run_task` does.** A given task reads the commit its row pins,
through `ledger.task_mutants_commit(task_id)`. A fresh one reads
`mutants.ref_commit(base.mirror)` (`saffron/task.py:775-779`). A commit the
mirror lacks is refused by `has_commit` (`saffron/task.py:780-783`). It then
calls `refuse_inline_mutants`, `mutants.read_mutants` and
`mutants.attach_mutants`, and turns any `SpecError` into one printed
`refused` line and a `Refused` (`saffron/task.py:784-791`). `read_mutants`
returns no mutants for a `None` commit (`saffron/mutants.py:79-92`).
`attach_mutants` raises `MutantsError` for a witness no criterion declares
(`saffron/mutants.py:95-124`). `MutantsError` is a `SpecError`
(`saffron/mutants.py:31`).

**Three more loads, none of which attaches a mutant.**

- `run_regate` loads the spec from the base export with `_spec_at_base`
  (`saffron/regate.py:86-96`, called at `:154`). It hands that spec to
  `package_phase.reverify` (`saffron/regate.py:167-176`). Its `try` turns a
  `_Declined` into one `regate:` line and exit 1 (`saffron/regate.py:157-159`).
  The mirror is `git_mirror.ensure_mirror(repo, mirror_path)`
  (`saffron/regate.py:146`).
- `saffron adopt` regates through `regate.run_regate`
  (`saffron/cli.py:3195-3202`). It moves the task to `READY_FOR_REVIEW` only
  when that regate exits 0 and records no new failure on the adopted head
  (`saffron/cli.py:3203-3214`). So a fix in `run_regate` covers adopt.
- `package_ready_task` takes its spec from `ready_task`, which reads it with
  `task._spec_for_task` (`saffron/task.py:1331`). It prepares the mirror
  (`saffron/task.py:1459`), builds the image (`:1460`) and passes
  `spec=ready.spec` to `package_phase.package` (`:1493-1503`). `cli._package`
  prints `package:` and the reason for a `Refused` and exits 1
  (`saffron/cli.py:3260-3262`).
- `run_commit_review` loads the spec with `commit_review._spec_for_task`,
  a recorded text or the file at the base export
  (`saffron/commit_review.py:123-143`, called at `:230-232`). Its `try`
  turns a `_Declined` into one `review:` line and exit 2
  (`saffron/commit_review.py:235-237`). Its mirror comes from
  `ensure_mirror` too (`saffron/commit_review.py:222`).

**Why it matters.** `revert` sets a witness aside when its mutant's file lies
outside the diff's source and the test paths
(`saffron/gates/core/revert.py:348-367`). It reads that only through
`c.mutant`. A spec with no mutant attached keeps every witness judged. A regate
can then count a new failure on a witness the cell's `revert` set aside.
`adopt` then keeps the task where it was. `package()`'s own
re-verification reads the spec it is handed the same way.

**The mirror holds a pinned commit.** `ensure_mirror` fetches
`refs/saffron/mutants*` in a second fetch (`saffron/repos/mirror.py:84-92`).
`saffron mutant` builds each commit on top of the previous one
(`saffron/mutants.py:1-8`), so the ref reaches every commit a task pinned.

## Problem

1. **One helper.** Add a function to `saffron/mutants.py`, beside
   `attach_mutants`. It takes the mirror, a mutants commit or `None`, and
   the spec. It raises `MutantsError` for a commit the mirror lacks, with
   `run_task`'s reason text. It then runs `refuse_inline_mutants`,
   `read_mutants` and `attach_mutants`, in `run_task`'s order, and returns
   the attached copy. `has_commit` comes from `saffron/repos/mirror.py`.
2. **`run_task` calls it.** Replace `saffron/task.py:780-787` with one call
   inside the existing `try`. The printed line and the `Refused` stay as
   they are. Drop the imports nothing else uses.
3. **`run_regate` calls it** after `_spec_at_base`, inside the `try`, with
   `ledger.task_mutants_commit(task_id)`. A `SpecError` becomes a
   `_Declined` whose reason is the error's text on one line. It declines
   before the image is built, and the attached spec reaches `reverify`.
4. **`package_ready_task` calls it** after `prepare_mirror` and before
   `build_cell_image`, with the commit `ready.outcome.task_id`'s row pins.
   A `SpecError` returns `Refused` with the error's text on one line. The
   attached spec reaches `package()`. Update its docstring's step list.
5. **`run_commit_review` calls it** after `_spec_for_task`, inside the
   `try`. A `SpecError` becomes a `_Declined`, so it prints `review:` and
   exits 2 like every other decline there.

Each refusal matches its command's existing kind: regate's `_Declined` and
exit 1, package's `Refused` and exit 1, review's `_Declined` and exit 2.

## Out of scope

- `_task_and_run` declining a task that ran a recorded spec text
  (`saffron/regate.py:55-58`). Reading the recorded text instead of the
  file at base is b-619b7d's 2026-11-09 Record line, not this spec.
- `ready_task` itself. It reads no mirror for the spec, and `saffron
  package` is its one caller through `package_ready_task`.
- `cli.py`. PR #1130 wraps `package` and `finish` there, and no edit here
  needs it.
- Keeping an inline mutant for an older task. The helper refuses one as
  `run_task` does, so the three commands decline such a task. That is
  only a spec at its base that predates `SA-0338`.

## Notes for the agent

**Edit or new.** The helper and each call are new lines whose spelling is
the cell's. No criterion declares a mutant, so `witness` reports an honest
`skip` on each.

**The witnesses.** Plain `def`s. Import any name this spec adds inside the
test body.

- `tests/test_regate.py`. Give `_spec_text`, `_write_spec` and
  `_build_fixture` an optional witness, so the spec at base declares one
  criterion under `acceptance:`. With none, every existing test reads the
  same text. Give `_seed_task` an optional `mutants_commit`, passed to
  `create_task`. Write the mutants commits in the fixture's checkout with
  `hash-object`, `mktree` and `commit-tree`, each on top of the last with
  `-p`, then `update-ref refs/saffron/mutants`. A root commit the ref does
  not reach is not cloned into the mirror (measured). One commit puts the
  witness's mutant in `src/elsewhere.py`, outside the diff. The next names
  `work.txt`, the packaged commit's own file. Its `find` must appear in
  neither the spec's body nor its claim.
- The regate fake for `package_phase.reverify` runs the real
  `saffron.gates.core.revert.revert_gate` over `kwargs["spec"].acceptance`.
  Use `changed_files=["work.txt"]`, `test_paths=["tests/**"]` and a
  `reverted` that is `contextlib.nullcontext()`. Give it a `run_tests` that
  reports every name in the subset collected and passing. Each `revert`
  failure becomes a `NewFailure("revert", failure)` in the comparison. On
  the prototype, an unpinned task printed
  `regate: revert passed-without-source <witness>` and `1 new failure`.
- The adopt witness seeds the task with no pull request and sets it
  `EXHAUSTED`. Its `gh` fake answers `pr view 9 --repo` with the url, the
  review head and the branch, and the url form with `OPEN` and `main`.
  Monkeypatch `package_phase.github_slug`, since the fixture's origin is a
  local path. Create the mirror with `ensure_mirror` before `cli.main`:
  adopt writes its facts before the regate clones it, and the prototype
  failed with `RecordError` without that.
- `tests/test_task.py`. Fake `task.ready_task` to return a `ReadyTask`
  whose outcome names a task created by `_recorded_ledger`'s ledger with a
  `mutants_commit`. Fake `preflight.prepare_mirror` to return that mirror,
  and fake the image, the network and the probe as
  `test_package_probes_the_host_then_runs_package_on_the_rebuilt_task`
  does in `tests/test_cli.py`. Spy on `package_phase.package`. Reuse
  `_mutants_commit` and `_set_mutants_ref`. Each case needs its own
  `tmp_path` subdirectory, since `_recorded_ledger` builds a mirror there.
- `tests/test_commit_review.py`. Record a spec text that declares one
  criterion, since the fixture's file at base declares none. Monkeypatch
  `end_review._review_one_layer` with a spy that returns `[]`.
- Each decline witness first runs one task with a readable pinned commit
  through the same fakes. It sees the image, `reverify` or the layer review
  reached. Only then does it run the two unreadable ones.

**Every new test fails with the source reverted.** On the prototype, all
seven failed with `saffron/` at `f681ad39`.

**An existing test this changes.**
`tests/test_cli.py::test_package_probes_the_host_then_runs_package_on_the_rebuilt_task`
asserts `package_kwargs["spec"] is spec` (`tests/test_cli.py:5132`). The
helper returns a copy, so assert equality there instead. It was the only
existing failure in `tests/test_task.py`, `tests/test_cli.py`,
`tests/test_regate.py`, `tests/test_commit_review.py`,
`tests/test_mutants.py`, `tests/test_batch.py` and `tests/test_package.py`
on the prototype.

**Size.** The prototype measured 196 changed tokens by `size_gate`
against the `bug` ceiling of 1300. It measured 1722 more under the test
paths.
