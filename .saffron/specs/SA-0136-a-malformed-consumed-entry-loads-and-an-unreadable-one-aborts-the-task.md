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
estimated_lines: 325
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
      A path with a `.` segment is refused at load in both forms, with a
      `SpecError` that names the entry. That holds for `pkg/./mod.py`, for
      `pkg/.`, and for a path whose first segment is `.`. A segment that starts with a dot, as in `pkg/.hidden/mod.py`, loads in both
      forms. So does a segment that ends with one, as in `pkg/v1./mod.py`.
    witness: tests/test_consumes.py::test_a_consumed_path_with_a_dot_segment_is_refused_at_load
  - claim: >-
      A path with a `..` segment is refused at load in both forms, with a
      `SpecError` that names the entry. That holds for `pkg/../mod.py`,
      for `pkg/..`, for a path whose first segment is `..`, and for a bare
      `..`. A segment that starts with two dots, as in
      `pkg/..hidden/mod.py`, loads in both forms. So does a segment that
      ends with two, as in `pkg/v1../mod.py`.
    witness: tests/test_consumes.py::test_a_consumed_path_with_a_dot_dot_segment_is_refused_at_load
  - claim: >-
      A path with an empty segment, such as `pkg//mod.py`, is refused at
      load in both forms, with a `SpecError` that names the entry.
      `pkg/mod.py` loads in both forms.
    witness: tests/test_consumes.py::test_a_consumed_path_with_an_empty_segment_is_refused_at_load
  - claim: >-
      A path ending in `/`, such as `pkg/`, is refused at load in both
      forms, with a `SpecError` that names the entry. The entry is split at
      its first colon, so `pkg/:Foo::bar` is refused too. `pkg` loads in
      both forms, and so does `a.py:Foo::bar`.
    witness: tests/test_consumes.py::test_a_consumed_path_ending_in_a_slash_is_refused_at_load
  - claim: >-
      An entry the reader cannot read for a named reason refuses the task,
      and the reason names it. The named reasons are what `file_at`'s
      three named raises refuse, and a file that is not UTF-8. They cover a
      `path:name` whose path is a submodule, a symlink that leaves the
      tree, a dangling symlink, a symlink to a directory, a symlink to
      another symlink, a file that is not UTF-8, and a symlink to such a
      file. Read alone by `unresolved_consumes`, each of the first five
      raises `UnreadablePath`. Each of the last two raises
      `UnicodeDecodeError` where the locale cannot decode the file. Given
      those seven, an entry whose path is absent and an entry that resolves,
      `run_task` returns one `Refused` and never calls `run_one_cell`. Its
      reason names the eight entries that did not resolve, in the order
      given, and not the one that did. Any other `GitError` at a commit the
      mirror holds, such as a blob missing from the mirror, raises out of
      `run_task` and is no refusal.
    witness: tests/test_consumes.py::test_an_unreadable_consumed_entry_refuses_the_task_and_names_it
  - claim: >-
      `has_commit(mirror, sha)` is true for a commit on the mirror's default
      branch and for a commit only another branch holds. It is false for
      forty zeros, and for the sha of a tree the mirror holds.
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
were split from one estimate of about 600 changed lines. At 4 tokens a
line (`saffron/gates/core/size.py:39`) that is about 2400 tokens, 80% of
the `feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`).

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

This spec stacks on `SA-0135`. The cell is cut from `saffron/SA-0135`,
and every sentence about current code was read there, at `fe1d43cf`.
That commit holds `SA-0134`'s reader and `SA-0135`'s check. `Spec` is
cited by symbol, because `SA-0129` and `SA-0135` move its lines.

**What `SA-0135` built.** `run_task` takes the tree base as `stacked_on`
or else `base.base_sha`. When `spec.consumes` is not empty, it calls
`unresolved_consumes` on it there. When any entry comes back, it prints
`f"{spec.id:<10} refused  {reason}"` and returns a `Refused` holding the
reason. Any exception from the reader propagates
(`saffron/task.py:323-332`). The witness
`test_a_tree_base_the_mirror_lacks_is_an_error_and_not_a_refusal`
(`tests/test_consumes.py:291-322`) expects `GitError` for a tree base the
mirror lacks.

**What the reader raises now.** `_run` decodes git's output as text and
catches only `OSError` (`saffron/repos/mirror.py:43-48`). `_git` raises
`GitError` on any non-zero exit (`saffron/repos/mirror.py:51-57`).
`file_at` raises `GitError` for a submodule, for a symlink that leaves the
tree, and for one whose target is not a regular file
(`saffron/repos/mirror.py:232-260`). `SA-0134`'s criterion 6 makes the
reader raise `GitError` for a missing sha too, and its notes list every
input it raises on. So one exception type means two things. No function in
the module says whether the mirror holds a commit
(`saffron/repos/mirror.py:60-336`). `GitError` is only "A git invocation
that did not do what was asked" (`saffron/repos/mirror.py:39-40`). A
corrupt object at a held commit raises it too. That is the host
breaking, not the spec (CLAUDE.md, `error` ≠ `fail`).

## Problem

A malformed entry reaches the reader, and an unreadable one aborts the
task as though the host had failed. Build three things.

1. **The shapes, at load.** Validate each `consumes` entry on `Spec`. Split
   it at its first colon. Refuse an empty entry, an empty path, and an
   empty name after a colon. Refuse a path that is not canonical. A
   canonical path is repo-relative, its segments are non-empty and joined
   by single slashes, and none is `.` or `..`. The message quotes the
   entry with `!r`.
2. **`has_commit(mirror, sha)` and `UnreadablePath`** in
   `saffron/repos/mirror.py`. `has_commit` says whether the mirror holds
   `sha` as a commit. `UnreadablePath` subclasses `GitError`, and
   `file_at` raises it at each of its three named raises
   (`saffron/repos/mirror.py:249`, `:253`, `:258`). Its `_git` calls still
   raise plain `GitError`.
3. **The mapping, in `run_task`.** For a spec that consumes something, ask
   `has_commit` about the tree base first. A no raises `GitError`. Then
   read each entry on its own. An entry for which the reader raises
   `UnreadablePath` or `UnicodeDecodeError` joins the unresolved ones, in
   the order given, and the reason names it. Catch nothing else. Any
   other exception raises out of `run_task` as it does at `SA-0135`.

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

**New code and edits, and no mutant.** Criteria 1 to 9 and 11 are new
code. Criterion 10 edits `file_at`'s three raises and `SA-0135`'s block
in `run_task`. It still declares no mutant, because a mutant's `find`
must match exactly once. The one edit worth reverting is the third raise
back to `GitError`. At the cell's head that raise opens with the same
text as the other two. A `find` unique to it must span the new class name
and the line after it. The spec cannot fix that layout without dictating
it. So `witness` will report `skip` for all eleven. Criterion
10's witness kills that wrong version by asserting each raise on its own.

**Where each part goes.** The shape check is a `field_validator` on
`consumes`, beside `SA-0135`'s validator that needs a `depends_on`. The
`dead` gate ignores a function under that decorator
(`.saffron/gates/dead.py:34`). `has_commit` goes beside `file_at`, and
asks `git cat-file -e` about `<sha>^{commit}` through `_run`. It returns
whether that exited 0. `UnreadablePath` goes beside `GitError`. It must
subclass it: every caller that catches `GitError` from `file_at` still
catches it, and the `file_at` tests at `tests/test_mirror.py:677-705`
expect `GitError` from all three sites. The reason keeps `SA-0135`'s
format. An unreadable entry is named in it as an unresolved one is, by the
entry alone.

**The witnesses.** All eleven go in `tests/test_consumes.py`, which
`SA-0135` created. Import `has_commit` inside its test body, never at the
top of the module. With the source reverted, a module-scope import of a
new name fails collection, and `revert` reads that as `skip`. Add no test
that passes with the source reverted. `revert` blocks such a test whether
or not a criterion declares it.

**Criteria 1 to 9** each call `parse_spec` on frontmatter with
`depends_on: [SA-0001]` and one entry. Each loading entry comes back as
written. For criteria 4 to 9 the witness drives the path alone and the
path with `:run_task` after it, refused and loading alike. For a first
segment of `.` or `..`, criteria 6 and 7 drive `./mod.py` and `../mod.py`.
The criteria describe them in words, because the scope check reads a
literal path in a claim as one outside `touches`.

Each refused entry raises a `SpecError`, and the witness reads the
validator's own message from it, as `exc.__cause__.errors()[0]["msg"]`.
`parse_spec` raises the `SpecError` from the `ValidationError`
(`saffron/intake.py:230`), so `__cause__` is that error. The assertion is
`repr(entry) in msg`, for every refused entry. A bare `entry in msg` checks
nothing for the empty entry, since `"" in msg` always holds. Nor does it
for a bare `.`, since any message ending in a period holds one. Do not
assert on `str(exc)`. Pydantic
prints the whole input there as `input_value`, so the entry appears
whatever the validator says. Measured on this repo's pydantic on
2026-09-23: a validator raising `ValueError` gives a `msg` that starts
`Value error, ` and then the validator's text.

Quote every entry in the YAML the witness writes, as `"a.py:"` and
`":run_task"`. Unquoted, PyYAML reads `a.py:` in a flow list as a mapping,
and `:run_task` in one as a parser error, measured on 2026-09-23. Either
way the entry never reaches the validator.

These fail them:

- a check of the bare path form only
- a validator message that does not name the entry
- a generic message for the empty entry or a bare `.`, such as
  "consumes entry is empty.", which holds neither `''` nor `'.'`
- a split at the last colon, `entry.rpartition(":")`. It reads
  `pkg/:Foo::bar` as the path `pkg/:Foo:` and the name `bar`, and loads
  it. `SA-0134`'s reader splits at the first colon and reads `pkg/`, a
  directory listing. Criterion 9's witness refuses `pkg/:Foo::bar`.
- a refusal of any name holding a colon, which `a.py:Foo::bar` catches
- a test for `./` anywhere with a check of the end, which refuses
  `pkg/v1./mod.py`
- a test for `../` anywhere, which refuses `pkg/v1../mod.py`
- a test for any dot at a path's start, which refuses `.github`
- a test for `..` anywhere in the path, which refuses `..hidden`
- a test for `/./` or `/../` inside the path, which lets a first or last
  segment of `.` or `..` load
- a check through `posixpath.normpath` that lets `pkg/` through
- a check that refuses everything, which a loading entry catches

**Criterion 10's witness** commits a tree through `_plain_repo` from
`tests.test_mirror`, and reads it through `ensure_mirror`.

- `sub`, a submodule, added with `git update-index --add --cacheinfo`
  as `tests/test_mirror.py:105-112` does. Stage it after `git add -A` and
  right before the commit. Nothing exists at `sub` in the worktree, so an
  `add -A` run after it stages the gitlink's removal, and `sub` is then
  absent. Measured on host git 2.54.0 on 2026-09-24.
- `out.md`, a symlink to `../outside`.
- `gone.md`, a symlink to `missing.md`.
- `dir.md`, a symlink to a directory `docs`, which holds the file
  `docs/a.md`. Git records no empty directory, so without that file
  `dir.md` is only a dangling symlink.
- `hop.md`, a symlink to `link.md`, itself a symlink to `real.py`.
- `bytes.py`, holding the bytes `ff fe` and nothing else.
- `bytes_link.py`, a symlink to `bytes.py`.
- `real.py`, holding `run_task`.

Its spec consumes `sub:x`, `out.md:x`, `gone.md:x`, `absent.py:x`,
`dir.md:x`, `hop.md:x`, `bytes.py:x`, `bytes_link.py:x` and
`real.py:run_task`, in that order. `absent.py:x` sits among the
unreadable entries on purpose.

Before it calls `run_task`, the witness reads each unreadable entry alone,
as `unresolved_consumes(mirror, sha, [e])`. For each of `sub:x`,
`out.md:x`, `gone.md:x`, `dir.md:x` and `hop.md:x` it asserts a raise of
`UnreadablePath`, which is a `GitError`. Import `UnreadablePath` inside
the test body. For `bytes.py:x` and `bytes_link.py:x` it asserts a raise
of `UnicodeDecodeError`. It skips those two assertions where
`locale.getpreferredencoding(False)` decodes the bytes `ff fe`. It asserts
`absent.py:x` comes back unresolved and raises nothing. This kills a build
that leaves the third raise as plain `GitError`. Without it, a fixture that
lost `sub` makes `sub:x` absent, and that build passes.
Measured at `fe1d43cf` on 2026-09-24: each of the five raised `GitError`
from its named raise, and each bytes entry raised `UnicodeDecodeError`.

Then it calls `run_task`. It asserts a `Refused` and no call to the
`run_one_cell` double. The reason holds the eight entries other than
`real.py:run_task`, in order, and not that one.

Then the witness breaks `real.py` at a commit the mirror holds. It reads
the blob's sha with `git rev-parse <sha>:real.py`, asserts that the loose
object `<mirror>/objects/<first 2>/<other 38>` exists, and deletes it. No
other file in the tree holds `real.py`'s text, so no other entry shares
that blob. A spec consuming `real.py:run_task` alone must make `run_task`
raise `GitError`, and the `run_one_cell` double must not be called.
Measured on 2026-09-23 on host git 2.54.0, in a mirror from
`git clone --mirror` of a local repo: the objects were loose, not packed.
With the blob deleted, `cat-file -e <sha>^{commit}` exited 0,
`ls-tree <sha> -- real.py` exited 0 with mode `100644`, and
`show <sha>:real.py` exited 128 with "bad object". A later
`fetch --prune origin` did not restore the blob. So `has_commit` says yes,
and `file_at`'s own `_git` call raises a plain `GitError`.

These fail it:

- a read of the whole list that stops at the first exception
- a catch of `UnreadablePath` alone, which lets the decode error out
- a catch of every `GitError`, which refuses the broken blob
- `except Exception`, which refuses the broken blob too
- `file_at` left raising plain `GitError` at its named sites, which
  either refuses the broken blob or raises on the first unreadable entry
- the first two named raises made `UnreadablePath` and the third left
  plain `GitError`, which the per-entry assertion on `sub:x` catches
- a reason that names an entry by index, or drops the exception's entry
- the entries that raised first, then the unresolved ones
- the unresolved entries first, then the ones that raised

A host whose locale decodes the bytes reads them as text holding no
`x`. The entry is then unresolved, and the call to `run_task` still
holds.

**Criterion 11's witness** builds a repo with a commit on `main` and a
commit only a second branch holds. It reads both through `ensure_mirror`,
which fetches every ref. It asserts true for both. It asserts false for
forty zeros and for the first commit's tree, from
`git rev-parse <sha>^{tree}`.

Measured on 2026-09-23 in a bare mirror built by `ensure_mirror` under
pytest's `tmp_path`, on host git 2.54.0.

- `git cat-file -e <sha>^{commit}` exited 0 for both commits. For forty
  zeros it exited 128 with "Not a valid object name". For a tree and for
  a blob it exited 128 with "expected commit type".
- `git cat-file -e <sha>`, with no `^{commit}`, exited 0 for the tree and
  the blob. A check through it fails the witness on the tree.
- `git rev-parse --verify` exited 0 for forty zeros, so a check through
  it fails the witness. With `^{commit}` it exited 128 for zeros, the
  tree and the blob, as `cat-file -e` did.
- `file_at` on the bytes `ff fe` raised `UnicodeDecodeError` from the
  `utf-8` codec.

None of this was run with the cell image's git.

**What stays guarded without a new test.** `SA-0135`'s criterion 5 witness
passes a tree base the mirror lacks and expects `GitError`. A mapping that
turned every `GitError` into a refusal fails it. It exists at the cell's
base, so it runs in the `tests` gate here. `SA-0135`'s criterion 8,
`test_a_task_that_never_packaged_still_reaches_the_index`, passes a mirror
that does not exist. So a `has_commit` call for a spec with no `consumes`
fails it.

**Size.** About 75 changed lines of source and 250 of test, declared as
`estimated_lines`. At 4 tokens a line that is about 1300 tokens, under 80% of the `feature` ceiling of 3000
(`saffron/gates/core/size.py:26`). The nine shape witnesses are short and
alike.

**Measured.** The change was not prototyped. The per-entry raises were
run against `fe1d43cf`'s reader. The git and pydantic behaviour above was
measured. The operator's loop runs the
wrong versions above before the cell. Do not run them yourself.
