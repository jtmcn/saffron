---
id: SA-0394
title: "The host cannot read an edited file as the probe cell holds it, so no host-side check can judge what a wrong version's edit leaves"
type: feature
priority: 3
risk: standard
estimated_lines: 165
estimate_measured: true
touches:
  - saffron/repos/mirror.py
  - saffron/qualify.py
  - tests/test_mirror.py
removes:
  - saffron/qualify.py:_rebuild_tree
pending_symbols:
  - saffron/repos/mirror.py::files_after
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
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/probe.py
  - saffron/intake.py
  - saffron/task.py
  - saffron/cli.py
  - tests/test_qualify.py
  - tests/test_session.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 36
max_attempts: 3
max_turns: 230
acceptance:
  - claim: >-
      `saffron/repos/mirror.py` gains `files_after(mirror, tree_base, patch,
      paths)`. It builds the tree of `patch` applied to `tree_base` once,
      with `rebuild_tree`, and returns a dict with one entry per path. A
      path the patch changes or adds reads as the patch leaves it. A path
      it leaves alone reads as `tree_base` holds it. A path the built tree
      lacks reads `None`, a path the patch deletes among them. A path
      `file_at` refuses to read also reads `None`. A `tree_base` the mirror
      lacks, or a patch that does not apply, returns an empty dict. The
      witness builds a real mirror whose base holds three files, a file
      under a directory, a symlink that leaves the tree and a symlink to
      that symlink. Its patch changes one file, adds one and deletes one.
      One call over eight paths is compared with a literal dict. They are
      the changed, added, untouched, deleted and absent files, both
      symlinks and the directory. A spy on `rebuild_tree` records exactly
      one build, at that base. The witness then asserts an empty dict for a
      base of forty zeros and for a patch whose hunk no longer matches.
    witness: tests/test_mirror.py::test_files_after_reads_each_path_from_the_base_tree_with_the_patch_applied
    wrong_versions:
      - Each path read at `tree_base`, never at the tree the patch builds.
      - A tree that cannot be built returns every path as `None`, not an empty dict.
      - A `file_at` refusal raised to the caller, not read as `None`.
      - A path that reads `None` left out of the dict rather than mapped to `None`.
      - The tree built again for each path.
  - claim: >-
      `qualify` still rebuilds the tree a critic read from SA-0375's record
      once the rebuild lives in `saffron/repos/mirror.py` as `rebuild_tree`.
    witness: tests/test_qualify.py::test_an_in_cell_concern_is_dropped_when_its_line_changed_since_the_tree_its_critic_read
    preserves: true
  - claim: >-
      The moved `rebuild_tree` still names the same cause when the mirror
      lacks the tree base, and when the diff does not apply to it.
    witness: tests/test_qualify.py::test_a_layer_whose_record_cannot_be_used_keeps_the_packaged_heads_check
    preserves: true
---

## Context

Backlog item **b-7fc792**, filed from spec loop run 70 while reviewing
#1203 (`SA-0390`). It cites `DESIGN.md` §5.4.1 and §5.5. Every line number
below was read at `dffa5474`.

**The defect this half prepares for**. REVIEW turned one of `SA-0390`'s
wrong versions into an edit that kept its whole `find`. It appended an
unused function after it. The edit changed no behaviour, so the witness
passed. The host then filed the version `survived` as an adequacy blocker.
`SA-0395`, this spec's child, refuses such an edit host-side before any
cell applies it. To judge it the host must read the edited file as the
probe cell holds it. This spec gives the host that read and nothing more.

**What the probe cell holds**. `critic_cell` seeds a worktree at the
spec's tree base (`saffron/cell/session.py:1601-1604`). Then `critic_cell`
applies the exported patch with the cell's own git
(`saffron/cell/session.py:1615`).
`_apply_criterion_probes` receives that same `patch` and the `mirror`
(`saffron/cell/session.py:2072-2081`).

**Where the host already builds that tree**. `qualify._rebuild_tree`
(`saffron/qualify.py:139`) builds `tree_base` plus a raw diff as a new tree
id in the bare mirror. It works under a throwaway `GIT_INDEX_FILE`, and
each git step runs under `worktree.git_argv`'s pins
(`saffron/cell/worktree.py:232`). It returns the tree id, or `None` with a
cause: the mirror lacks the base (`saffron/qualify.py:157`), the diff does
not apply (`saffron/qualify.py:166`), or the tree did not write
(`saffron/qualify.py:174`). Its one caller is `_reviewed_tree`
(`saffron/qualify.py:203`). No other file names it.

**Why it moves**. The qualify module imports the session module at
module scope (`saffron/qualify.py:40`). So the session module cannot import
the qualify module, and the child's caller there cannot reach the rebuild
where it lives. `saffron/repos/mirror.py` already imports from
`saffron.cell.worktree` (`saffron/repos/mirror.py:17`). The qualify module
already imports its `file_at` from there (`saffron/qualify.py:46`).

**How a path is read from a tree**. `file_at(mirror, sha, path)`
(`saffron/repos/mirror.py:265`) returns `None` for a path the tree lacks. It
raises `UnreadablePath`, a `GitError` (`saffron/repos/mirror.py:45`). The
body of `file_at` raises it for a directory or a submodule. So it does for
a symlink that leaves the tree, or one whose target is no regular file
(`saffron/repos/mirror.py:278-293`). It reads through `git ls-tree` and
`git show`. The prototype measured on the host's git that both take a tree
id as readily as a commit.

## Problem

Move `qualify._rebuild_tree` to `saffron/repos/mirror.py` as
`rebuild_tree`, with its body and docstring unchanged. Have
`qualify._reviewed_tree` call it there, and drop the imports `qualify` then
no longer uses.

Add `files_after(mirror, tree_base, patch, paths) -> dict[str, str | None]`
to the same module. It calls `rebuild_tree` once. When that returns no
tree, it returns an empty dict. Otherwise it reads each path with
`file_at` at the tree id it built, and maps a `GitError` to `None`. The
rule is criterion 1's claim.

Nothing in `saffron/` calls `files_after` yet, and `SA-0395` adds its
caller. So this spec lists it under `pending_symbols`.

## Out of scope

- **The refusal itself**. `inert_edit` in `saffron/probe.py` and its call
  in `_apply_criterion_probes` are `SA-0395`'s, which depends on this spec.
- **Any change to what `rebuild_tree` does**. Its three causes keep their
  words, and `qualify` keeps reading them as before.
- **A `retired_first`**. This spec adds no refusal.
- **A submodule path**. `file_at` refuses one as it refuses a directory,
  and the witness drives the directory alone.

## Notes for the agent

**`files_after` is new code**, so criterion 1 declares a witness and
no mutant, and `witness` will report `skip`. Criteria 2 and 3 are
`preserves`, and both tests exist at base in `tests/test_qualify.py`.
Criterion 2's test compares a reason that quotes the rebuilt tree id.
Criterion 3's test compares the two causes word for word. A prototype
checked both against a `rebuild_tree` that returns no tree. Each failed.
Only criterion 3's test failed when one cause was reworded.

**At base the new witness fails in its body**. `files_after` does not exist
there. Import it inside the witness, never at module scope, as the comment
at `tests/test_mirror.py:19` says for `unresolved_consumes`.

**The witness** uses `_plain_repo` (`tests/test_mirror.py:587`) and
`ensure_mirror`. Commit the base with an `os.symlink` to `../outside`, as
`test_file_at_raises_on_a_symlink_escaping_the_tree` does. Add a second
symlink that points at the first. Stage the change and take the patch from
`git diff --cached` before the mirror is cloned, so the mirror holds the
base alone. Make the stale patch by rewriting the removed line's text, and
assert the rewrite changed the patch. Spy on `rebuild_tree` with
`monkeypatch.setattr` on the `saffron.repos.mirror` module, wrapping the
real function, so the spy sees the build that produced the dict.

**The `dead` gate** reads `pending_symbols` from this spec while it is
open, so `files_after` with no caller passes it. `rebuild_tree` has
`qualify` as its caller.

**The `prose` gate** reads the moved docstring as new text in
`saffron/repos/mirror.py`. Keep it as it stands, since it carries no
em dash, semicolon or contraction. Give `files_after` a short docstring
held to the same rules.

**Size**. A prototype measured 442 counted tokens outside `tests/` and 216
under it, about 165 changed lines. The move is about half of the counted
tokens.
