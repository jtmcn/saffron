---
id: SA-0134
title: The host cannot tell whether a tree base holds a name a stacked child consumes
type: feature
priority: 2
depends_on: [SA-0129]
touches:
  - saffron/repos/mirror.py
  - tests/test_mirror.py
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
  - saffron/intake.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/cell/**
  - saffron/gates/**
  - tests/test_intake.py
  - tests/test_task.py
  - tests/test_batch.py
  - tests/test_cli.py
  - tests/test_scheduler.py
pending_symbols:
  - saffron/repos/mirror.py::unresolved_consumes
budget_usd: 20
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      `unresolved_consumes(mirror, sha, entries)` reads an entry with no
      colon as a path, and every path it is given is canonical and
      repo-relative. The path resolves when the tree at `sha` holds a
      regular file of mode `100644` or `100755`, a directory or a symlink
      at that path. A symlink resolves whether it points at a regular file,
      at no path in the tree, or outside the tree. A path the tree does not
      hold is unresolved, and so is a prefix
      of a directory's name. This claims nothing for any other spelling of
      a path, which `SA-0135` refuses at intake.
    witness: tests/test_mirror.py::test_a_consumed_path_resolves_when_the_tree_holds_a_file_a_directory_or_a_symlink_there
  - claim: >-
      An entry `path:name` resolves when `path` at `sha` is a regular file,
      or a symlink `file_at` reads through to one, and its text holds `name`
      as a whole word. A path the tree does not hold is unresolved. A
      directory is unresolved without raising, even when a file inside it
      holds the name. A symlink is judged by its target's text and never by
      the link's own.
    witness: tests/test_mirror.py::test_a_consumed_name_is_read_from_the_file_its_path_names
  - claim: >-
      A whole word is an occurrence with no ASCII letter, digit or underscore
      directly before or after it, and the start and end of the text count
      as boundaries. The match is case-sensitive, and `name` is literal
      text, never a pattern. The entry splits at its first colon, so a name
      may hold a colon. One whole occurrence resolves the entry, even after
      an occurrence inside a longer word.
    witness: tests/test_mirror.py::test_a_consumed_name_matches_only_as_a_whole_word
  - claim: >-
      It reads the tree at `sha`, never the mirror's `HEAD`. Of two commits,
      a path or a name that only the older holds resolves at the older and
      not at the newer. One that only the newer holds resolves at the newer
      and not at the older.
    witness: tests/test_mirror.py::test_consumed_entries_resolve_at_the_sha_given_and_not_at_head
  - claim: >-
      It returns exactly the entries that do not resolve, as written, in the
      order given, once per occurrence. When every entry resolves it returns
      an empty list.
    witness: tests/test_mirror.py::test_unresolved_consumes_returns_each_unresolved_entry_in_order
  - claim: >-
      A `sha` the mirror does not hold raises `GitError`, for a path entry
      and for a `path:name` entry alike. It never reports either entry as
      unresolved.
    witness: tests/test_mirror.py::test_unresolved_consumes_raises_on_a_sha_the_mirror_does_not_hold
---

## Context

Backlog item **b-602d00**, filed 2026-09-21. It cites `DESIGN.md` §4.2.
ADR 6 names it as the check on a composite's first join, the names a member
consumes (`docs/adr/0006-work-larger-than-one-cell-is-a-composite-spec.md`,
its last paragraph).

A stacked child's tree base is its parent's branch head (§4.2). The child's
criteria and notes name functions, fields and paths the parent adds. If the
parent built them under other names, the child's cell finds out after its
first turn is paid for. The item asks for a `consumes:` field and a refusal
before the cell starts, as gate 0 refuses in §4.2.

**This spec is the first of two.** Estimated whole, the change ran to about
500 changed lines. At 4 tokens a line (`saffron/gates/core/size.py:39`) that
is about 2000 tokens, against the `feature` ceiling of 3000 tokens
(`saffron/gates/core/size.py:26`, read at `c915d801`). Past `feature` cells
touching six files landed between 250 and 660 lines, or 1000 to 2640
tokens. The top of that range is past 2400, which is 80% of the ceiling. So
the check splits. This spec builds the
host's reader of a tree base. `SA-0135` stacks on it and adds the `consumes:` field, the refusal in
`saffron/task.py`'s `run_task`, and the batch's handling of that refusal.
The reader goes first so that no commit carries a field that parses and
changes nothing, the defect §4.2.1 names in item 18's words.

This spec stacks on `SA-0129`, which the operator chose because `SA-0135`
edits `saffron/intake.py` after it. Nothing here touches what `SA-0129`
touches. Every sentence below about current code was read at `1e543011`.

**What the mirror module reads now.** Core knows git and nothing about
languages (§2.1), and `saffron/repos/mirror.py` is where it reads the bare
mirror. `_git` raises `GitError` on any non-zero exit
(`saffron/repos/mirror.py:51-57`). `_ls_tree_mode` returns the git mode at a
path, or `None` when the tree at the sha holds no such path
(`saffron/repos/mirror.py:225-228`). `file_at` returns a regular file's text
at a sha, or `None` when the path is absent (`saffron/repos/mirror.py:231-243`).
It follows a symlink one hop to a regular file (`:244-256`). Every other mode
raises `GitError`, a directory included (`:257-259`). Its test for a sha the
mirror does not hold expects `GitError`
(`tests/test_mirror.py:655-659`). Nothing in the module answers whether a
file at a sha holds a given word.

## Problem

No host code can say whether the tree at a sha holds a path, or a name in a
file. So only a reader checks what a stacked child relies on.

Add `unresolved_consumes(mirror, sha, entries)` to `saffron/repos/mirror.py`.
`entries` is a list of strings, each a repo-relative `path` or a `path:name`.
It returns the entries that do not resolve at `sha`, and the criteria say
what resolves. It reads the bare mirror through git and parses no language.

The name is fixed, because `SA-0135` calls it and `pending_symbols` names it
for the `dead` gate until then.

## Out of scope

- **The `consumes:` field, its intake rules, and the fixture spec that uses
  it.** `SA-0135` adds them. `saffron/intake.py` is forbidden here.
- **The refusal before the cell, and the batch's handling of it.**
  `SA-0135` wires this reader into `run_task` after `_resolve_stacked_on`
  returns (`saffron/task.py:286-294`) and before `run_one_cell`
  (`saffron/task.py:319`).
- **Refusing a malformed entry.** A canonical path is repo-relative. Its
  segments are non-empty, joined by single slashes, and none is `.` or
  `..`. `SA-0135` refuses every other entry at intake, and this reader
  is not asked about them. The shapes it refuses are these.
  - an empty entry
  - an empty path, as in `:name`
  - an empty name, as in `path:`
  - an absolute path
  - a bare `.`
  - a path with a `.` segment, as in `saffron/./task.py`
  - a path with a `..` segment, as in `saffron/../CLAUDE.md`
  - a path with an empty segment, as in `saffron//task.py`
  - a path ending in `/`
  - a path holding a colon, as in `weird:name.py`, which the reader splits

  A trailing `/` makes `git ls-tree` list the directory's children, so the
  reader would read the first child's mode and then a directory listing as
  text. The Notes give what git did with each shape.
- **The vocabulary and the refusal count.** `CONTEXT.md` has no entry for a
  consumed name, and §4.2.1 counts the refusals gate 0 makes. Both change
  with `SA-0135`, by hand.

## Notes for the agent

**Every change here is new code.** So each criterion declares a witness and
no mutant, and `witness` will report `skip` for all six.

**Where it goes.** Beside `file_at` in `saffron/repos/mirror.py`, with a
docstring of ten lines or fewer. Split each entry at its first colon. Ask
`_ls_tree_mode` first, so that a directory is answered before `file_at`
could raise on it. For a `path:name`, a tree's mode `040000` is
unresolved, and every other mode goes to `file_at` for its text. Catch
no `GitError`, because a sha the mirror lacks is an error and never an
unresolved entry. Build the word test from the name escaped as literal
text, bounded by a lookbehind and a lookahead over ASCII letters, digits
and the underscore.

**The witnesses.** All six go in `tests/test_mirror.py`. Build each repo
with `_plain_repo` (`tests/test_mirror.py:457`) and read it through
`ensure_mirror`, as the `file_at` tests do. Import `unresolved_consumes`
inside each test body, never in the module's import block at the top. With
the source reverted, a module-scope import of it fails collection. `revert`
reads that as `skip`, so it checks nothing.

**Criterion 1's witness** commits `exact.py`, an executable `run.sh`, a
directory `pkg` holding `pkg/mod.py`, and three symlinks. `link.py` points
at `exact.py`, `dangling.py` at `gone.py`, which the tree does not hold, and
`escape.py` at `../outside.py`. It sets `run.sh`'s mode with `os.chmod`
before the commit, so the tree records `100755`, and makes the links with
`os.symlink`. It asserts that `exact.py`, `run.sh`, `pkg`, `link.py`,
`dangling.py` and `escape.py` each return an empty list. It asserts that `missing.py`,
`pkg/missing.py` and `pk` each return themselves. A check that the tree
lists a path starting with the entry fails it on `pk`. A check for mode
`100644` alone fails it on `run.sh`. A path entry answered through
`file_at` for every mode but `040000` raises `GitError` on `dangling.py`
and on `escape.py`, and fails it there. Measured on 2026-09-23 at
`c915d801` on host git 2.54.0. `git ls-tree` lists both links at mode
`120000`, and `file_at` raises on `dangling.py` from `:251-255` and on
`escape.py` from `:247-250`. A symlink to a directory or to another
symlink takes the same branch as `dangling.py`, and no witness drives it.

**Criterion 2's witness** uses the same tree. `exact.py` and `run.sh` each
hold `run_task` and nothing else, and `pkg/mod.py` holds `helper` and
nothing else. `exact.py:run_task`, `run.sh:run_task` and
`link.py:run_task` resolve. `missing.py:run_task`, `pkg:helper` and
`link.py:exact` do not, and `pkg:helper` raises nothing. These fail it:

- a search of every file under a directory
- a call to `file_at` on a directory that raises
- a read of the symlink's own text
- a text read for mode `100644` alone, on `run.sh:run_task`, reasoned and
  not run

**Criterion 3's witness** calls the reader once per entry, so a failure
names its case. Each file below holds its text and nothing else.

- Resolve: `run_task` with no newline, `task.run_task(`, a line reading
  `run_tasks = run_task`, `x = a.c` for the name `a.c`, and `Foo::bar()`
  for the entry `lib.rs:Foo::bar`.
- Do not resolve, for the name `run_task`: `xrun_task`, `Xrun_task`,
  `0run_task`, `_run_task`, `run_tasks`, `run_taskS`, `run_task9`,
  `run_task_`, and `Run_Task RUN_TASK`.
- Do not resolve: `abc` for the name `a.c`.

These fail it:

- a substring test
- a test that needs a character on each side
- a check of only the first occurrence
- a letter class of lowercase letters only
- a case-folded match
- the name used as a regular expression
- a split at the last colon

**Criterion 4's witness** commits `a.py` holding `first_name` and an
`old.py`. A second commit rewrites `a.py` to hold `second_name`, deletes
`old.py` and adds `new.py`. The mirror's `HEAD` is the second commit. At
the first commit, `a.py:first_name` and `old.py` resolve, and
`a.py:second_name` and `new.py` do not. At the second, the reverse holds.
A reader of `HEAD` or of the default branch fails it. So does a path check
that reads the history reaching `sha`, as `git log <sha> -- <path>` does,
because at the second commit it still finds `old.py`.

**Criterion 5's witness** passes `missing.py`, `exact.py`,
`missing.py:run_task`, `exact.py:run_task` and `missing.py` again. It
expects `missing.py`, `missing.py:run_task` and `missing.py`, in that order.
It also passes only resolving entries and expects an empty list. A sorted
result or a set fails it.

**Criterion 6's witness** passes forty zeros as the sha, once with
`exact.py` and once with `exact.py:run_task`. Each raises `GitError`. A
reader that reads a failed git call as an absent path fails it.

**What it raises, and on which inputs.** `SA-0135` maps each of these onto
a refusal or an error, so the list is whole. Only the first has a witness.

- `GitError`, for any entry at a `sha` the mirror does not hold
  (criterion 6).
- `GitError`, for a `path:name` whose path is a submodule, from `file_at`'s
  last branch (`saffron/repos/mirror.py:257-259`).
- `GitError`, for a `path:name` whose path is a symlink that leaves the tree
  (`:247-250`).
- `GitError`, for a `path:name` whose symlink is dangling, or points at a
  directory or at another symlink (`:251-255`).
- `UnicodeDecodeError`, for a `path:name` whose file, or whose symlink's
  target, does not decode in the host locale's encoding, which is UTF-8 on
  the host. `_run` decodes git's output as text and catches only `OSError`
  (`saffron/repos/mirror.py:43-48`).
- `GitError`, for an empty entry, an empty path, an absolute path or a bare
  `..`, because `git ls-tree` exits 128 on each. A `..` segment that climbs
  past the root likely does too, and was not measured.

A path entry that names a submodule resolves, since `git ls-tree` lists it.
No witness drives that either.

**What git did with each malformed shape.** Measured on 2026-09-22 in a
bare mirror built by `ensure_mirror`, on host git 2.54.0. Each shape was
passed to `git ls-tree <sha> -- <path>`.

- `./CLAUDE.md`, `saffron//task.py`, `saffron/./task.py` and
  `saffron/../CLAUDE.md` listed the canonical path's entry and exited 0.
- `.` listed the root's children, and `saffron/` listed `saffron/task.py`.
- `..` and `/CLAUDE.md` exited 128 with "outside repository".
- The empty string exited 128 with "empty string is not a valid pathspec".
- `git show <sha>:saffron/` printed `tree <sha>:saffron/` and a listing of
  `task.py`. A prototype of this reader resolved `saffron/:task` against
  that listing.
- A prototype resolved `CLAUDE.md:`, an empty name, against a file holding
  `y` and a newline.

**Left unclaimed, and why.** A whole-word match finds a name in a comment
or a docstring as readily as in code. That is a limit of the check, and
`SA-0135`'s claim states it. What a non-ASCII neighbour does, and a name
that starts or ends with punctuation, are left open, and no witness drives
them.

**Size.** About 40 changed lines of source and 165 of test. `file_at`
(`saffron/repos/mirror.py:231-259`) and its seven tests, which start at
`tests/test_mirror.py:638` through `:694`, run to about 95 lines. This
reader has more cases. A bare prototype measured 20 lines of source
and 115 of test, with no docstrings.

**Measured wrong implementations.** On 2026-09-22 a prototype of the reader
and the six witnesses ran at `16065067` on host git 2.54.0. With the
reader in place, all six passed. Each of these failed at least one:

- a substring test
- a word test that needs a character on each side
- a check of only the first occurrence
- a letter class of lowercase letters only
- a case-folded match
- the name used as a regular expression
- a split at the last colon
- a path matched as a prefix of any listed path
- no directory check before `file_at`
- a read of the symlink's own text
- a read at `HEAD`
- a sorted result, and a deduplicated one
- a caught `GitError` read as unresolved
- a search of every file in the tree

A second prototype ran at `1e543011` on the same day, against criterion
4's witness with `old.py` added. It passed, and a path check through
`git log <sha> -- <path>` failed it on `old.py` at the second commit. The
same prototype resolved `run.sh` at mode `100755`. That a check for mode
`100644` alone fails criterion 1 is reasoned, and was not run.

The control, a word test bounded by `\b`, passed all six. It is correct for
every name the witnesses drive. The operator's loop runs this list again
before the cell. Do not run it yourself.
