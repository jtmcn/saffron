---
id: SA-0339
title: "No command writes a spec's mutants onto `refs/saffron/mutants`, so intake has nothing to read"
type: feature
priority: 1
depends_on: [SA-0338]
estimated_lines: 505
estimate_measured: true
touches:
  - saffron/mutants.py
  - saffron/cli.py
  - tests/test_mutant_command.py
  - README.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
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
  - saffron/intake.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/ledger.py
  - tests/test_intake.py
  - tests/test_mutants.py
  - tests/test_record_refs.py
  - tests/test_cli.py
budget_usd: 58
max_attempts: 3
max_turns: 240
risk: standard
acceptance:
  - claim: >-
      `saffron mutant <spec id> --from <file> --repo <path>` exits 0 and prints
      the mutants ref's new commit, which origin's copy of the ref then names.
      That commit's tree holds `<spec id>.yaml` at its root, byte for byte the
      file given. `read_mutants`, run over origin at that commit, returns that
      file's mutants. A write for a second spec keeps the first spec's file
      and takes the earlier commit as its parent. A second write for the
      first spec replaces that spec's file alone, and the tree then holds
      exactly the two files.
    witness: tests/test_mutant_command.py::test_a_mutants_file_is_committed_onto_the_ref_and_pushed_to_origin
    wrong_versions:
      - The file lands under a subdirectory of the ref's tree, so the reader finds nothing.
      - Each commit's tree holds only the spec just written.
      - Each commit is a root commit with no parent.
      - The YAML is parsed and dumped again, so the blob differs from the file given.
      - The ref is updated locally and never pushed.
      - The command prints a message, or the tree, rather than the commit.
      - A rewrite for one spec adds a second entry beside its old file.
      - The fetch names the ref exactly, so the first write to an origin without it fails.
  - claim: >-
      The command fetches origin's mutants ref before it builds on it, and
      origin's copy wins over the local one. The witness drives four local
      states, and each write exits 0. With no local copy, the new commit's
      parent is the one another repository pushed. With a local copy one
      commit behind, the parent is origin's newer commit. With a local copy
      origin's ref does not contain, the parent is origin's commit and the
      local copy's file is absent. With a local copy while origin holds no
      ref, the pushed commit has no parent and holds the written file alone.
    witness: tests/test_mutant_command.py::test_a_write_builds_on_what_origin_holds_whatever_the_local_copy
    wrong_versions:
      - Nothing is fetched, so a repository with no local copy writes a root commit and its push is refused.
      - The ref is fetched only when no local copy exists, so a stale copy is built on and its push is refused.
      - The fetch refspec has no leading `+`, so a diverged local copy makes the fetch fail.
      - The fetch has no `--prune`, so a local copy origin lacks is built on and pushed.
  - claim: >-
      A refused write exits 1 and prints its cause, and neither the local ref
      nor origin's ref exists afterwards. The witness drives each cause. No
      file `.saffron/specs/<spec id>-*.md` exists, or one exists only under
      `done/`, or two exist. The spec file does not parse, or declares
      another id. The `--from` file is missing. The file is not YAML, is a
      list, has a mutant without `find`, or has a key `Mutant` lacks. A
      `find` occurs no times, twice, only in the working tree, or in a file
      absent at `HEAD`. A key names a witness no criterion declares, or one
      two criteria declare. A criterion declaring `subject:` gets no mutant.
      A `find` occurs once at `HEAD` and also in the spec's body, its own
      criterion's claim, another criterion's claim, or another criterion's
      `wrong_versions`.
    witness: tests/test_mutant_command.py::test_a_file_run_task_would_refuse_is_refused_before_any_write
    wrong_versions:
      - The occurrences are counted in the working tree rather than at `HEAD`.
      - Only a `find` that occurs more than once is refused.
      - Only a `find` that occurs no times is refused.
      - "`attach_mutants` is never called, so a witness no criterion declares is written."
      - The disclosure check runs alone, without `attach_mutants`, so a doubled witness or a bare subject is written.
      - A spec file under `done/` counts as the spec.
      - The first of two matching spec files is taken.
      - The spec's declared id is never compared with the argument.
      - A missing `--from` file exits 2.
      - A refused YAML file exits 2, because the `SpecError` is not caught as a refusal.
      - The validation runs after the ref is written.
  - claim: >-
      A write that loses a race exits 1 and leaves the winner in place. The
      witness drives four races. Before the local `update-ref`, the ref is
      created where none was, moved, or deleted, and the local ref keeps
      that state. Before the push, origin's ref moves. Origin keeps the
      other commit, and the local ref is put back to the commit it held
      before the write.
    witness: tests/test_mutant_command.py::test_a_write_that_loses_a_race_is_refused_and_leaves_the_winner
    wrong_versions:
      - "`update-ref` is given no old value, so the local winner is overwritten."
      - The push is forced, so origin's winner is overwritten.
      - A push origin refuses as a non-fast-forward exits 2.
      - A lost local swap exits 2.
      - Only `but expected` reads as a lost swap, so a created or deleted ref exits 2.
      - The local ref keeps the unpushed commit after the refused push.
  - claim: >-
      A git failure that is no race exits 2. The witness drives four. Origin's
      URL names no repository. The repository has no `origin` remote. The
      local ref's lock file is held when `update-ref` runs. Origin is
      reachable for the fetch and unreachable for the push. Afterwards
      neither the local ref nor origin's ref exists.
    witness: tests/test_mutant_command.py::test_a_broken_origin_or_ref_exits_2
    wrong_versions:
      - Every `update-ref` failure exits 1.
      - Every push failure exits 1.
      - The local ref keeps the unpushed commit after the failed push.
  - claim: >-
      Every git process the command starts runs with `GIT_TERMINAL_PROMPT`
      set to `0` in its environment. The witness records each call. The
      `HEAD` read, the fetch, the `update-ref` and the push are among them.
    witness: tests/test_mutant_command.py::test_every_git_call_runs_with_no_terminal_prompt
    wrong_versions:
      - Only the fetch and the push set it.
      - The `HEAD` read goes through a helper that passes no environment.
---

## Context

Backlog item **80**, part 2 of 2. Tier 1 in `docs/backlog/PRIORITY.md`.
`SA-0338` is part 1. It moves intake onto the ref, and this spec depends on it.
Every line cited below was read at `8c024ec6`, which is `origin/main`.

**Cited lines move on the cell's base.** `SA-0338` edits `saffron/intake.py`
and `saffron/cli.py`, so their cited line numbers move on the branch
the cell starts from. Find each by the function or text named beside it.

**What `DESIGN.md` says, as amended at base.** §5.4.1's paragraph "A mutant
lives on `refs/saffron/mutants`, never in the spec" (`DESIGN.md:1097-1105`)
gives the layout. The ref's tree holds one `<spec id>.yaml` per spec, keyed by
the id. `saffron mutant` writes that file and pushes the ref to the repo's
origin. Intake reads each criterion's mutant from the mirror's copy. A queued
spec that still declares a `mutant:` inline is refused.

**What `SA-0338` leaves in `saffron/mutants.py`.** Read from its spec at the
head of `joel/spec-mutants-ref`. `MUTANTS_REF` names the ref. `MutantsError`
is a `SpecError`. `parse_mutants(text, where)` returns a dict from witness to
`Mutant`, and `where` names the file in each error. It wraps every YAML and
validation error in `MutantsError`. It refuses a YAML error and a value that is
not a mapping. It refuses an entry that is not a mapping, has no `file`, has
an empty `find`, or has an unknown key. `read_mutants(mirror, commit, spec_id)`
reads `<spec id>.yaml` at a commit and hands its text to `parse_mutants`.
`attach_mutants(spec, found)` returns the spec with each criterion's mutant
set. It refuses a witness no criterion declares, a witness two criteria
declare, and a `subject:` with no mutant. It then runs the disclosure
refusal, which raises `DisclosedMutantError`.

**How the record writes a ref today.** `RefsRecord.append` hashes a blob and
builds a tree with `mktree`. It commits that tree with `commit-tree` onto the
old head (`saffron/record/refs.py:82-87`). It moves the ref with `update-ref`
given the old value, as a compare-and-swap (`saffron/record/refs.py:88-90`).
`_push` pushes `ref:ref` with no `--force` (`saffron/record/refs.py:148-152`).
It reads `[rejected]` in git's stderr as a stale writer and any other failure
as an error (`saffron/record/refs.py:153-162`). The identity rides on each
command, because a repository can hold none (`saffron/record/refs.py:21-23`).
`_fetch_one` sets `GIT_TERMINAL_PROMPT=0` (`saffron/record/refs.py:121`).
`_git_bytes` passes no environment unless its caller gives one
(`saffron/record/refs.py:51-56`). Backlog item b-0add4c records that gap.
`saffron/repos/mirror.py`'s `_run` passes no environment either
(`saffron/repos/mirror.py:52-55`).

**The CLI.** A command that opens no ledger is dispatched before the home
`Ledger` is built, and an exception there exits 2
(`saffron/cli.py:358-365`). The module docstring lists every command
(`saffron/cli.py:1-3`).

## Problem

After `SA-0338`, intake reads mutants from `refs/saffron/mutants` and refuses
one written inline. Nothing writes that ref. An author would have to build a
blob, a tree and a commit by hand and push the ref. Nothing would check the
file before it reached a night.

Build `saffron mutant <spec id> --from <file.yaml> [--repo <path>]`:

1. **Validate before any write.** Exactly one file
   `.saffron/specs/<spec id>-*.md` must exist in the working tree of
   `--repo`, outside `done/`. Parse it with `load_spec`, and require its id
   to equal the argument. Read the `--from` file's bytes. Parse its text
   with `parse_mutants`, `where` naming the `--from` path. Each mutant's `find` must occur exactly once in its
   `file` as committed at `HEAD`. Then call `attach_mutants` on the spec and
   the parsed mutants, so the command refuses what `run_task` refuses.
2. **Fetch, then write.** Run `git fetch --prune origin` with the refspec
   `+refs/saffron/mutants*:refs/saffron/mutants*`. Origin's copy then
   replaces the local one, and a local copy origin lacks is deleted. Read
   the local ref. Build a tree holding every root entry of the old tree,
   with `<spec id>.yaml` added or replaced by the file's own bytes. Commit
   it with `commit-tree`, with the old commit as the parent when there is
   one. Move the ref with `update-ref`, given the old value, or the empty
   string where there was none.
3. **Push.** Push `refs/saffron/mutants` to origin with no `--force`. On a
   failed push, put the local ref back to the old commit with a
   compare-and-swap `update-ref`. Where there was no old commit, delete it
   with `update-ref -d` given the new one. Print the new commit on success.
4. **Exit codes.** 0 for a write that reached origin. 1 for every refusal in
   step 1, a lost local swap, or a push origin refuses as a non-fast-forward.
   2 for any other git failure.
5. **No terminal prompt.** Every git process the command starts carries
   `GIT_TERMINAL_PROMPT=0` in its environment. That includes the `HEAD` read.
6. **Docs.** Add `mutant` to the list in `saffron/cli.py`'s module
   docstring. Add the command to `README.md` beside `next-id`.

## Out of scope

- A list or show subcommand. The command writes and pushes, nothing more.
- Moving any existing spec's inline mutants onto the ref. That is `SA-0338`'s,
  or the operator's by hand.
- `GIT_SSH_COMMAND` with `BatchMode`. Item b-0add4c names it as unverified.
- A failed rollback after a failed push. It exits 2 with git's reason, and
  no witness drives it.
- `RefsRecord`, `saffron/repos/` and the rest of `saffron/record/`. Reuse
  their approach, never their functions.
- `CLAUDE.md`. It runs past its line budget, and `README.md` carries the
  command.

## Notes for the agent

**Mutants and new code.** The command and its writer are new code, so no
criterion declares a mutant and `witness` reports `skip` for all six.

**Extend `SA-0338`'s module.** Put the writer in `saffron/mutants.py`, beside
the reader. Give it two exception types, one for a refusal and one for a git
failure. `saffron/cli.py` maps the first, and any `SpecError`, to exit 1.
`MutantsError` and `DisclosedMutantError` are both `SpecError`s. Its
dispatch maps anything else to 2, the way `next-id` does. Spell the
identity flags on each command, as `saffron/record/refs.py:23` does.

**Run your own git.** Do not call `file_at`, `ref_commit` or anything else
in `saffron/repos/` for the command's git work. They pass no environment.
Run git through `subprocess.run` with an argv list, and pass `env=` on each
call. The race and prompt witnesses replace `subprocess.run` with a wrapper.
The wrapper acts on the call whose argv holds `update-ref` or `push` as an
element.

**Tell a race from a broken repository by git's own words.** Measured with
git 2.54.0 on the host and git 2.47.3 in `saffron/cell-base:python`, which
agreed. A lost `update-ref` swap exits 128 with one of three phrases:

- `but expected`, where the ref holds another commit.
- `reference already exists`, where the empty old value meets a ref.
- `unable to resolve reference`, where the old value meets no ref.

A held lock file exits 128 with `Unable to create` and `File exists`. A
missing object exits 128 with `nonexistent object`. Read those and any other
`update-ref` failure as exit 2. A non-fast-forward push writes `[rejected]`
and exits 1. A fetch of the glob with `--prune` exits 0 when origin lacks the
ref, and deletes a local copy. Without the `+`, a diverged local copy fails
that fetch with `[rejected]`. An unreachable or missing origin fails the
fetch with exit 128.

**The witnesses.** One new file, `tests/test_mutant_command.py`. Drive the
command through `saffron.cli.main`, with `--home` under `tmp_path`. Import
anything `SA-0338` or this spec adds inside the test function, never at
module scope. A module-scope import of a new name makes the reverted run a
collection error. Each test sets `HOME`, `XDG_CONFIG_HOME` and
`GIT_CONFIG_NOSYSTEM=1` under `tmp_path` with `monkeypatch.setenv`, so no
`config --global` reaches the real config. Origin is a local bare
repository. The repository under test commits one source file and adds the
bare one as `origin`. It writes its spec files under `.saffron/specs/`,
uncommitted. One test spec carries two criteria, one of them with a
`wrong_versions` entry.

- Criterion 1. The `--from` file starts with a comment line, so a parsed and
  dumped copy differs from it. Compare blobs as read, not stripped.
- Criterion 2. Copy the repository after the first write, delete the copy's
  local ref, and write a second spec from the copy. Write again from the
  first repository, whose local ref still names the first commit. Then
  point its local ref at a commit built by hand that holds another file, and
  write again. Last, point `origin` at a new empty bare repository and write.
- Criterion 3. Commit the source with each disclosing phrase once, then add a
  line to the working tree alone. Each refused `find` must occur once at
  `HEAD`, except the cases about its count. Then only the check under test can
  refuse it. Pick a twice-occurring `find` that the spec text never holds.
  Give the doubled-witness, bare-subject, two-file, other-id and unparsable
  cases their own spec files.
- Criterion 4. The wrapper changes the local ref, then runs the command's
  first `update-ref`. Drive the created case before the first successful
  write. For origin's race, it moves origin's ref to a child of the pushed
  commit, then runs the push.
- Criterion 5. Drive the two fetch failures first, then restore origin. The
  lock case writes the lock file beside the ref under `.git`, then runs the
  `update-ref`, and removes it afterwards. For the push failure, the
  wrapper points `origin` at a missing path, then runs the push.
- Criterion 6. The wrapper records each git call's environment, or
  `os.environ` where `env` is `None`.

**Every new test must fail with the source reverted.** Each one does. At base
`saffron mutant` is no command, and `main` exits through argparse.

**For the hand edits in the pull request.** `.claude/` is not this cell's to
edit. The operator adds a line to `.claude/agents/spec-writer.md` and
`.claude/agents/spec-reviewer.md`. It tells an author to write mutants with
`saffron mutant` and never inline.
