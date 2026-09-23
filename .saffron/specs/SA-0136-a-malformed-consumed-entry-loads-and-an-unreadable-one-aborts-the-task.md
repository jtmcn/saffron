---
id: SA-0136
title: A malformed consumed entry loads, and an unreadable one aborts the task instead of refusing it
type: feature
priority: 2
depends_on: [SA-0135]
touches:
  - saffron/intake.py
  - saffron/task.py
  - saffron/repos/mirror.py
  - tests/test_consumes.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - saffron/batch.py
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - tests/test_mirror.py
  - tests/test_task.py
  - tests/test_batch.py
  - tests/test_cli.py
  - tests/test_intake.py
  - tests/test_scheduler.py
  - tests/fixtures/**
  - pkg/**
budget_usd: 36
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      An empty `consumes` entry is refused at load with a `SpecError` that
      names it, and the entry `a` loads.
    witness: tests/test_consumes.py::test_an_empty_consumed_entry_is_refused_at_load
  - claim: >-
      An entry with an empty path, such as `:run_task`, is refused at load
      with a `SpecError` that names it, and `a.py:run_task` loads.
    witness: tests/test_consumes.py::test_a_consumed_entry_with_an_empty_path_is_refused_at_load
  - claim: >-
      An entry with an empty name, such as `a.py:`, is refused at load with
      a `SpecError` that names it, and `a.py:x` loads.
    witness: tests/test_consumes.py::test_a_consumed_entry_with_an_empty_name_is_refused_at_load
  - claim: >-
      An absolute path, one that starts with a slash, is refused at load as
      a path entry and as the path of a `path:name`, with a `SpecError` that
      names the entry. The same path without its leading slash loads in both
      forms.
    witness: tests/test_consumes.py::test_an_absolute_consumed_path_is_refused_at_load
  - claim: >-
      A bare `.` is refused at load as a path entry and as the path of a
      `path:name`, with a `SpecError` that names the entry. A path whose
      first segment starts with a dot, such as `.github`, loads in both
      forms.
    witness: tests/test_consumes.py::test_a_bare_dot_consumed_path_is_refused_at_load
  - claim: >-
      A path with a `.` segment, such as `pkg/./mod.py`, is refused at
      load in both forms, with a `SpecError` that names the entry. A segment
      that starts with a dot, as in `pkg/.hidden/mod.py`, loads in both
      forms.
    witness: tests/test_consumes.py::test_a_consumed_path_with_a_dot_segment_is_refused_at_load
  - claim: >-
      A path with a `..` segment is refused at load in both forms, with a
      `SpecError` that names the entry. That holds for `pkg/../mod.py`
      and for a bare `..`. A segment that starts with two dots, as in
      `pkg/..hidden/mod.py`, loads in both forms.
    witness: tests/test_consumes.py::test_a_consumed_path_with_a_dot_dot_segment_is_refused_at_load
  - claim: >-
      A path with an empty segment, such as `pkg//mod.py`, is refused at
      load in both forms, with a `SpecError` that names the entry.
      `pkg/mod.py` loads in both forms.
    witness: tests/test_consumes.py::test_a_consumed_path_with_an_empty_segment_is_refused_at_load
  - claim: >-
      A path ending in `/`, such as `pkg/`, is refused at load in both
      forms, with a `SpecError` that names the entry. `pkg` loads in both
      forms.
    witness: tests/test_consumes.py::test_a_consumed_path_ending_in_a_slash_is_refused_at_load
  - claim: >-
      An entry the reader cannot read refuses the task, and the reason names
      it. That covers a `path:name` whose path is a submodule, a symlink
      that leaves the tree, a dangling symlink, a symlink to a directory, a
      symlink to another symlink, a file that is not UTF-8, and a symlink to
      such a file. Given with one unresolved entry and one resolving entry,
      `run_task` returns one `Refused` and never calls `run_one_cell`. Its
      reason names the eight entries that did not resolve, in the order
      given, and not the one that did.
    witness: tests/test_consumes.py::test_an_unreadable_consumed_entry_refuses_the_task_and_names_it
  - claim: >-
      `has_commit(mirror, sha)` is true for a commit on the mirror's default
      branch and for a commit only another branch holds. It is false for
      forty zeros.
    witness: tests/test_consumes.py::test_has_commit_answers_whether_the_mirror_holds_a_commit
---

## Context

Backlog item **b-602d00**, filed 2026-09-21. It cites `DESIGN.md` §4.2.

**This spec is the third of three.** `SA-0134` built the reader,
`unresolved_consumes(mirror, sha, entries)` in `saffron/repos/mirror.py`.
`SA-0135` added the `consumes:` field and the refusal in `run_task`, and
kept every exception the reader raises as an error. This spec closes the
gap `SA-0135` left. It refuses nine malformed shapes at load, and it turns
an entry the reader cannot read into a refusal that names it. The two
were split from one estimate of about 600 changed lines against the
`feature` ceiling of 600 (`saffron/gates/core/size.py:25`).

**What the gap cost until now.** `SA-0134`'s notes give what git does with
each malformed shape, measured on host git 2.54.0.

- An empty entry, an empty path, an absolute path and a bare `..` make
  `git ls-tree` exit 128. The reader raises `GitError`, and `run_task`
  raises. `saffron cell` exits 2, and a batch counts the task as an abort.
- A `path:name` whose path ends in `/` resolves against the directory's
  listing, and an empty name resolves against any file. Each is a false
  pass, and the cell runs.
- An unreadable entry raises from the reader, `GitError` or
  `UnicodeDecodeError`, and `run_task` raises too. That charges the spec's
  own mistake to the host.

This spec stacks on `SA-0135`, whose code does not exist at `02af122a`.
Sentences about its code cite that spec. `Spec` is cited by symbol,
because `SA-0129` and `SA-0135` move its lines. Every other sentence about
current code was read at `02af122a`.

**What `SA-0135` builds.** `run_task` takes the tree base as `stacked_on`
or else `base.base_sha`. When `spec.consumes` is not empty, it calls
`unresolved_consumes` on it there. When any entry comes back, it prints
`f"{spec.id:<10} refused  {reason}"` and returns a `Refused` holding the
reason. Any exception from the reader propagates
(`.saffron/specs/SA-0135-a-stacked-child-starts-its-cell-without-its-parents-names.md`,
its Problem, item 3). Its criterion 5's witness,
`test_a_tree_base_the_mirror_lacks_is_an_error_and_not_a_refusal`, expects
`GitError` for a tree base the mirror lacks.

**What the reader raises now.** `_run` decodes git's output as text and
catches only `OSError` (`saffron/repos/mirror.py:43-48`). `_git` raises
`GitError` on any non-zero exit (`saffron/repos/mirror.py:51-57`).
`file_at` raises `GitError` for a submodule, for a symlink that leaves the
tree, and for one whose target is not a regular file
(`saffron/repos/mirror.py:244-259`). `SA-0134`'s criterion 6 makes the
reader raise `GitError` for a missing sha too, and its notes list every
input it raises on. So one exception type means two things. No function in
the module says whether the mirror holds a commit
(`saffron/repos/mirror.py:60-262`).

## Problem

A malformed entry reaches the reader, and an unreadable one aborts the
task as though the host had failed. Build three things.

1. **The shapes, at load.** Validate each `consumes` entry on `Spec`. Split
   it at its first colon. Refuse an empty entry, an empty path, and an
   empty name after a colon. Refuse a path that is not canonical. A
   canonical path is repo-relative, its segments are non-empty and joined
   by single slashes, and none is `.` or `..`. The message names the entry.
2. **`has_commit(mirror, sha)`** in `saffron/repos/mirror.py`. It says
   whether the mirror holds `sha` as a commit.
3. **The mapping, in `run_task`.** For a spec that consumes something, ask
   `has_commit` about the tree base first. A no raises `GitError` naming
   the tree base. Then read each entry on its own. An entry for
   which the reader raises `GitError` or `UnicodeDecodeError` joins the
   unresolved ones, in the order given, and the reason names it.

## Out of scope

- **A path holding a colon.** It cannot be written as an entry. The first
  colon splits it, so `weird:name.py` reads as the path `weird` and the
  name `name.py`. It loads, and at run time it comes back as that
  unresolved entry, which `SA-0135`'s criterion 3 drives. A spec that
  needs such a file consumes its directory instead.
- **A path entry that names a submodule.** `git ls-tree` lists it, so it
  resolves, as `SA-0134` notes. No witness drives it here.
- **The refusal's shape, the batch and `saffron cell`.** `SA-0135` owns
  them, and `saffron/batch.py` and `saffron/cli.py` are forbidden.
- **The vocabulary.** Backlog item b-343c21 holds the glossary entry for a
  consumed name, done by hand.

## Notes for the agent

**Every change here is new code.** So each criterion declares a witness
and no mutant, and `witness` will report `skip` for all eleven.

**Where each part goes.** The shape check is a `field_validator` on
`consumes`, beside `SA-0135`'s validator that needs a `depends_on`. The
`dead` gate ignores a function under that decorator
(`.saffron/gates/dead.py:34`). `has_commit` goes beside `file_at`, and
asks `git cat-file -e` about `<sha>^{commit}` through `_run`. It returns
whether that exited 0. Name an unreadable entry in the reason with the
first line of what was raised, in parentheses after it.

**The witnesses.** All eleven go in `tests/test_consumes.py`, which
`SA-0135` created. Import `has_commit` inside its test body, never at the
top of the module. With the source reverted, a module-scope import of a
new name fails collection, and `revert` reads that as `skip`. Add no test
that passes with the source reverted. `revert` blocks such a test whether
or not a criterion declares it.

**Criteria 1 to 9** each call `parse_spec` on frontmatter with
`depends_on: [SA-0001]` and one entry. Each refused entry raises a
`SpecError` whose message holds the entry. Each loading entry comes back
as written. For criteria 4 to 9 the witness drives the path alone and the
path with `:run_task` after it, refused and loading alike. These fail
them:

- a check of the bare path form only
- a message that does not name the entry
- a test for any dot at a path's start, which refuses `.github`
- a test for `..` anywhere in the path, which refuses `..hidden`
- a check through `posixpath.normpath` that lets `saffron/` through
- a check that refuses everything, which a loading entry catches

**Criterion 10's witness** commits a tree through `_plain_repo` from
`tests.test_mirror`, and reads it through `ensure_mirror`.

- `sub`, a submodule, added with `git update-index --add --cacheinfo`
  as `tests/test_mirror.py:101-109` does.
- `out.md`, a symlink to `../outside`.
- `gone.md`, a symlink to `missing.md`.
- `dir.md`, a symlink to a directory `docs`.
- `hop.md`, a symlink to `link.md`, itself a symlink to `real.py`.
- `bytes.py`, holding the bytes `ff fe` and nothing else.
- `bytes_link.py`, a symlink to `bytes.py`.
- `real.py`, holding `run_task`.

Its spec consumes `sub:x`, `out.md:x`, `gone.md:x`, `dir.md:x`,
`hop.md:x`, `bytes.py:x`, `bytes_link.py:x`, `real.py:run_task` and
`absent.py:x`, in that order. It asserts a `Refused` and no call to the
`run_one_cell` double. The reason holds the eight entries other than
`real.py:run_task`, in order, and not that one. These fail it:

- a read of the whole list that stops at the first exception
- a catch of `GitError` alone, which lets the decode error out
- a reason that names an entry by index, or drops the exception's entry

A host whose locale decodes the bytes reads them as text holding no
`x`. The entry is then unresolved, and the witness still holds.

**Criterion 11's witness** builds a repo with a commit on `main` and a
commit only a second branch holds. It reads both through `ensure_mirror`,
which fetches every ref. It asserts true for both and false for forty
zeros. `git rev-parse --verify` accepts forty zeros without looking them
up, so a check through it fails the witness.

**What stays guarded without a new test.** `SA-0135`'s criterion 5 witness
passes a tree base the mirror lacks and expects `GitError`. A mapping that
turned every `GitError` into a refusal fails it. It exists once `SA-0135`
merges, so it runs in the `tests` gate here. `SA-0135`'s criterion 8,
`test_a_task_that_never_packaged_still_reaches_the_index`, passes a mirror
that does not exist. So a `has_commit` call for a spec with no `consumes`
fails it.

**Size.** About 60 changed lines of source and 190 of test. The nine shape
witnesses are short and alike.

**Measured.** Nothing here was prototyped. `SA-0134`'s reader and
`SA-0135`'s check do not exist at `02af122a`. The operator's loop runs the
wrong versions above before the cell. Do not run them yourself.
