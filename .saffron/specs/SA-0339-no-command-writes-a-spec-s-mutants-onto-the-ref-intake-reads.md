---
id: SA-0339
title: "No command writes a spec's mutants onto `refs/saffron/mutants`, so intake has nothing to read"
type: feature
priority: 1
depends_on: [SA-0338]
estimated_lines: 430
estimate_measured: true
touches:
  - saffron/mutants.py
  - saffron/intake.py
  - saffron/cli.py
  - tests/test_mutant_command.py
  - README.md
  - CLAUDE.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
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
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/ledger.py
  - tests/test_intake.py
  - tests/test_record_refs.py
  - tests/test_cli.py
budget_usd: 52
max_attempts: 3
max_turns: 210
risk: standard
acceptance:
  - claim: >-
      `saffron mutant <spec id> --from <file> --repo <path>` exits 0 and prints
      the mutants ref's new commit, which origin's copy of the ref then names.
      That commit's tree holds `<spec id>.yaml` at its root, byte for byte the
      file given. The reader SA-0338 adds, run over origin, returns that
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
      - The command prints the tree, or a message, rather than the commit.
      - A rewrite for one spec adds a second entry beside its old file.
  - claim: >-
      The command fetches origin's mutants ref before it builds on it. The
      witness drives two local states. A repository with no local copy of
      the ref writes on top of the commit another repository pushed. Origin's
      ref then holds both specs' files, and its new commit's parent is the
      one pushed before. A repository whose local copy is one commit behind
      origin then writes, and its commit's parent is origin's newer one.
    witness: tests/test_mutant_command.py::test_a_write_builds_on_what_another_repo_already_pushed
    wrong_versions:
      - Nothing is fetched, so the second repository writes a root commit and its push is refused.
      - The ref is fetched only when no local copy exists, so a stale copy is built on and its push is refused.
  - claim: >-
      A refused write exits 1, and neither the local ref nor origin's ref
      exists afterwards. The witness drives each of these. The
      spec id names no file `.saffron/specs/<spec id>-*.md`, or names one only
      under `done/`. The file is not YAML, or one mutant lacks `find`. A
      `find` occurs no times, twice, only in the working tree, or in a file
      that is absent at `HEAD`. A `find` occurs once at `HEAD` and also in the
      spec's body. The same holds for one in its own criterion's claim,
      another criterion's claim, or another criterion's `wrong_versions`.
    witness: tests/test_mutant_command.py::test_a_file_intake_would_refuse_is_refused_before_any_write
    wrong_versions:
      - The occurrences are counted in the working tree rather than at `HEAD`.
      - Only a `find` that occurs more than once is refused.
      - Only a `find` that occurs no times is refused.
      - The disclosure check reads one of the body, the claims and the wrong versions, and not the other two.
      - A claim discloses a mutant only when it is that mutant's own criterion's claim.
      - A spec file under `done/` counts as the spec.
      - Any spec id is accepted, whether or not a spec file names it.
      - The disclosure check runs after the ref is written.
      - A refused YAML file exits 2, because the parser's error is not caught as a refusal.
  - claim: >-
      A write that loses a race exits 1 and leaves the winner in place. The
      witness drives both races. In one, the local ref moves between the
      command's read and its `update-ref`, and the local ref keeps the other
      commit. In the other, origin's ref moves before the push, and origin
      keeps the other commit.
    witness: tests/test_mutant_command.py::test_a_write_that_loses_a_race_is_refused_and_leaves_the_winner
    wrong_versions:
      - "`update-ref` is given no old value, so the local winner is overwritten."
      - The push is forced, so origin's winner is overwritten.
      - A push origin refuses as a non-fast-forward exits 2.
      - A lost local swap exits 2.
  - claim: >-
      An origin the command cannot reach exits 2. The witness drives three
      forms. Origin's URL names no repository, and the local ref is not
      written. The repository has no `origin` remote, and the local ref is
      not written. Origin is reachable for the fetch and unreachable for the
      push, and origin holds no ref afterwards.
    witness: tests/test_mutant_command.py::test_a_broken_origin_exits_2_and_writes_no_ref
    wrong_versions:
      - Every fetch failure is read as an absent ref, so the command writes the local ref and fails later.
      - Every push failure exits 1.
  - claim: >-
      Every git process the command starts runs with `GIT_TERMINAL_PROMPT`
      set to `0` in its environment. The witness records each call, the
      fetch and the push among them.
    witness: tests/test_mutant_command.py::test_every_git_call_runs_with_no_terminal_prompt
    wrong_versions:
      - Only the fetch and the push set it.
---

## Context

Backlog item **80**, part 2 of 2. Tier 1 in `docs/backlog/PRIORITY.md`.
`SA-0338` is part 1. It moves intake onto the ref, and this spec depends on it.
Every line cited below was read at `8c024ec6`.

**What `DESIGN.md` says, as amended at base.** §5.4.1's paragraph "A mutant
lives on `refs/saffron/mutants`, never in the spec" (`DESIGN.md:1097-1105`)
gives the layout. The ref's tree holds one `<spec id>.yaml` per spec, keyed by
the id. `saffron mutant` writes that file and pushes the ref to the repo's
origin. The mirror fetches the ref by name. Intake reads each criterion's
mutant from the mirror's copy. A queued spec that still declares a `mutant:`
inline is refused.

**What `SA-0338` leaves.** It is written in parallel, so the names below are
assumed. A module `saffron/mutants.py` names the ref. It parses one spec's
YAML text into a `Mutant` per criterion, keyed by witness, and refuses a
malformed file. It reads `<spec id>.yaml` from a repository's ref. Intake
applies the disclosure refusal to the mutants it reads from the ref. Use the
names `SA-0338` landed, and the shape its parser reads.

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
(`saffron/record/refs.py:51-56`). Backlog item
b-0add4c records that gap.

**The disclosure refusal.** `parse_spec` refuses a mutant whose `find` occurs
in the spec's body, in any claim, or in any criterion's `wrong_versions`
(`saffron/intake.py:366-414`). `Mutant` refuses an empty `file` or `find`
(`saffron/intake.py:103-118`). It leaves the count of matches to a tree
(`saffron/intake.py:92-94`).

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

1. **Validate before any write.** Refuse a spec id with no file
   `.saffron/specs/<spec id>-*.md` in the working tree of `--repo`. A file under `done/` does not count. Parse it
   with `load_spec`. Parse the YAML with `SA-0338`'s parser. Each mutant's
   `find` must occur exactly once in its `file` as committed at `HEAD`.
   Apply intake's disclosure refusal to the file's mutants and this spec.
   Call the one check intake runs. If `SA-0338` left it inside `parse_spec`,
   move it into a function in `saffron/intake.py` that both call.
2. **Fetch, then write.** Fetch origin's `refs/saffron/mutants` into the
   same local name, replacing the local copy. An origin that lacks the ref
   is no error. Then read the local ref. Build a tree holding every root
   entry of the old tree, with `<spec id>.yaml` added or replaced by the
   file's own bytes. Commit it with `commit-tree`, with the old commit as
   the parent when there is one. Move the ref with `update-ref` given the
   old value.
3. **Push.** Push `refs/saffron/mutants` to origin with no `--force`. Print
   the new commit.
4. **Exit codes.** 0 for a write that reached origin. 1 for a refused file,
   a lost local swap, or a push origin refuses as a non-fast-forward. 2 for
   any other git failure, a fetch or a push included.
5. **No terminal prompt.** Every git process the command starts carries
   `GIT_TERMINAL_PROMPT=0` in its environment.
6. **Docs.** Add `mutant` to the list in `saffron/cli.py`'s module
   docstring. Add the command to `README.md` beside `next-id`, and one line to
   `CLAUDE.md`'s "Running the CLI" block.

## Out of scope

- A list or show subcommand. The command writes and pushes, nothing more.
- Moving any existing spec's inline mutants onto the ref. That is `SA-0338`'s,
  or the operator's by hand.
- `GIT_SSH_COMMAND` with `BatchMode`. Item b-0add4c names it as unverified.
- Refusing a mutant keyed to a witness the spec does not declare. Intake
  decides what such a key means.
- `RefsRecord` and the rest of `saffron/record/`. Reuse its approach, not
  its class.

## Notes for the agent

**Mutants and new code.** The command and its writer are new code, so no
criterion declares a mutant and `witness` reports `skip` for all six.

**Extend `SA-0338`'s module.** Put the writer in `saffron/mutants.py`, beside
the reader. Give it two exception types, one for a refusal and one for a git
failure. `saffron/cli.py` maps the first, and intake's own `SpecError`, to
exit 1. Its dispatch maps anything else to 2, the way `next-id` does. Spell
the identity flags on each command, as `saffron/record/refs.py:23` does.

**Run git through `subprocess.run` with an argv list.** The race and prompt
witnesses replace `subprocess.run` with a wrapper. The wrapper acts on the
call whose argv holds `update-ref` or `push` as an element. Each call passes
`env=` explicitly.

**Tell a race from a broken origin by git's own words.** A non-fast-forward
push writes `[rejected]` to stderr, as `_push` reads it. A lost `update-ref`
swap exits nonzero. An absent remote
ref on fetch says `couldn't find remote ref`. Measured with git 2.54 on the
host.

**The witnesses.** One new file, `tests/test_mutant_command.py`. Drive the
command through `saffron.cli.main`, with `--home` under `tmp_path`. Import
anything `SA-0338` or this spec adds inside the test function, never at
module scope. A module-scope import of a new name makes the reverted run a
collection error. Each test sets `HOME`, `XDG_CONFIG_HOME` and
`GIT_CONFIG_NOSYSTEM=1` under `tmp_path` with `monkeypatch.setenv`, so no
`config --global` reaches the real config. Origin is a local bare
repository. The repository under test commits one source file and adds the
bare one as `origin`. It writes two spec files under `.saffron/specs/`,
uncommitted. One test spec carries two criteria, one of them with a
`wrong_versions` entry.

- Criterion 1. The `--from` file starts with a comment line, so a parsed and
  dumped copy differs from it. Compare blobs as read, not stripped.
- Criterion 2. Copy the repository after the first write, delete the copy's
  local ref, and write a second spec from the copy. Then write again from the
  first repository, whose local ref still names the first commit.
- Criterion 3. Commit the source with each disclosing phrase once, then add a
  line to the working tree alone. Each refused `find` must occur once at
  `HEAD`, except the cases about its count. Then only the check under test can
  refuse it. Pick a twice-occurring `find` that the spec text never holds.
- Criterion 4. For the local race, the wrapper moves the local ref to another
  commit, then runs the command's `update-ref`. For origin's race, it moves
  origin's ref to a child of the pushed commit, then runs the push.
- Criterion 5. Drive the two fetch failures first, then restore origin. For
  the push failure, the wrapper points `origin` at a missing path, then runs
  the push.
- Criterion 6. The wrapper records each git call's environment, or
  `os.environ` where `env` is `None`. Assert a fetch and a push are among them.

**Every new test must fail with the source reverted.** Each one does. At base
`saffron mutant` is no command, and `main` exits through argparse.

**For the hand edits in the pull request.** `.claude/` is not this cell's to
edit. The operator adds a line to `.claude/agents/spec-writer.md` and
`.claude/agents/spec-reviewer.md`. It tells an author to write mutants with
`saffron mutant` and never inline.
