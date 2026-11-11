---
id: SA-0372
title: A spec that removes a name starts its cell though a file outside its touches reads that name, so the cell ends EXHAUSTED
type: feature
priority: 2
estimated_lines: 108
estimate_measured: true
touches:
  - saffron/repos/mirror.py
  - saffron/task.py
  - tests/test_removed_name_readers.py
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
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/repos/policy.py
  - tests/conftest.py
  - tests/test_consumes.py
  - tests/test_mirror.py
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/fixtures/**
budget_usd: 45
max_attempts: 3
max_turns: 230
acceptance:
  - claim: >-
      `removed_name_readers(mirror, sha, entries)` in
      `saffron/repos/mirror.py` returns each tracked file at `sha` that
      reads one of the `removes` entries, as a `(path, entry)` pair. A
      `path:name` entry's subject is its name. A bare `path` entry's subject
      is the whole path. A reader holds the subject as a whole word, by
      `_word_pattern`. The file at the entry's own path is never its reader,
      in both forms. Pairs come in entry order, then path order. The witness
      drives both forms in both orders. It drives an import, an attribute
      read, a subject that starts a file with no trailing newline, and a
      Markdown reader. It drives `OLD_NAME_V2`, `NOOLD_NAME` and `old_name`
      as files that read nothing. It drives two near misses on a bare path
      the same way, one with its last dot made an underscore and one with a
      letter after its extension. An entry no file reads adds no pair. Where the locale cannot decode the bytes
      `\xff\xfe`, a file holding them beside the subject counts as a
      reader. A `sha` the mirror lacks raises `GitError`.
    witness: tests/test_removed_name_readers.py::test_the_readers_of_a_removed_entry_are_the_files_holding_its_subject_as_a_whole_word
    wrong_versions:
      - A substring test, so `OLD_NAME_V2` and `NOOLD_NAME` read as readers.
      - A match that ignores case, so `old_name` reads as a reader.
      - The subject used as a regular expression unescaped, in the grep and the match, so the near miss with an underscore for the dot reads as a reader.
      - The whole entry taken as a `path:name` entry's subject, so no file reads `lib.py:OLD_NAME`.
      - The file at the entry's own path kept, so `lib.py` reads its own `OLD_NAME`.
      - A file that does not decode skipped, so it reads nothing.
      - Every git grep exit past 0 read as no match, so a `sha` the mirror lacks returns no pair.
      - Pairs sorted by path across all entries, so a later entry's reader with an earlier path comes first.
  - claim: >-
      `run_task` refuses a spec that declares `removes` and a non-empty
      `touches` before its cell, when a reader at the tree base lies outside
      `touches`. Markdown, a file under `.saffron/specs/` and a path the tree
      base's `policy.yaml` lists as `protected` are never readers. Both
      `touches` and `protected` patterns match by `scope.matches`. The reason
      is the tree base's first 12 characters, then `holds readers outside
      touches:`, then each reader as `<path> reads <subject>`. Readers are
      joined by a comma and a space, in `removed_name_readers`'s order. One
      `refused` line is printed, and no `tasks` or `runs` row is written. The
      witness drives a reader that each of these leaves out. Those are an
      exact `touches` path, a `src/**` glob, Markdown at the top level and
      nested, a file under `.saffron/specs/` and a `protected` glob. It
      drives a reader one directory below a `tests/*.txt` pattern in
      `touches`, and one below a `gen/*.txt` pattern in `protected`. The
      reason names both. It drives both entry forms. The same spec with every reader in `touches`
      starts its cell.
    witness: tests/test_removed_name_readers.py::test_run_task_refuses_a_removed_name_read_outside_touches_before_the_cell
    wrong_versions:
      - A `touches` entry compared as an exact string, so a reader under `src/**` is named.
      - "`fnmatch` in place of `scope.matches` for `touches`, so `tests/*.txt` reaches a file one directory down."
      - "`fnmatch` in place of `scope.matches` for `protected`, so `gen/*.txt` reaches a file one directory down."
      - Markdown kept, so `README.md` is named.
      - The `.saffron/specs/` exclusion left out, so a text file there is named.
      - The policy left unread, so a reader under the `protected` glob is named.
      - The reason names each entry in place of its subject.
      - A refusal that writes its task row first.
  - claim: >-
      Readers and the policy are read at the task's tree base. Unstacked
      that is `base_sha`. A commit after it and a file only in the working
      copy add no reader. Stacked, it is the parent's head. A reader the
      parent deleted is not named, a reader it added is named, and the
      parent's `protected` list applies. A tree base whose `policy.yaml` is
      absent, does not parse, or cannot be read protects nothing. The
      witness drives a symlink leaving the tree for the last. Where the
      locale cannot decode the bytes `\xff\xfe`, it drives a policy holding
      them too. A tree base the mirror lacks raises `GitError` and prints no
      `refused` line.
    witness: tests/test_removed_name_readers.py::test_readers_are_read_at_the_tasks_tree_base_with_its_own_policy
    wrong_versions:
      - Readers read at `base_sha` when the task is stacked, so the parent's deleted reader is named and its new one is not.
      - The policy read at another commit or from the working copy, so the parent's `protected` glob does not apply.
      - A policy that does not parse raises, so the task aborts and is not refused.
      - Only a `PolicyError` caught, so a policy symlink leaving the tree aborts the task.
      - A policy that does not decode left uncaught, so the task aborts.
      - A tree base the mirror lacks turned into a refusal.
  - claim: >-
      A spec with no `removes`, or with an empty `touches`, never calls
      `removed_name_readers` and starts its cell. The witness first sees one
      call, through the same spy, for a spec that declares both and whose
      cell then starts.
    witness: tests/test_removed_name_readers.py::test_a_spec_with_no_removes_or_no_touches_never_looks_for_readers
    wrong_versions:
      - The check made for a spec with an empty `touches`, so every reader lies outside it and the spec is refused.
      - The reader called with an empty list for a spec with no `removes`.
      - The check never made, so the spy sees no call for a spec that declares both.
---

## Context

Backlog item **b-1c59c3**, filed 2026-10-12 from the spec loop. It cites `DESIGN.md` §4.3 and §5.4. Every line number below was
read at `c1fe691c`.

**The incident.** `SA-0269` removed `CRITIC_NETWORK` from
`saffron/cell/session.py`. `tests/test_sigterm.py` imported it and was not in
the spec's `touches`. Attempt 2 fixed the test and `scope` refused the edit.
Attempt 3 reverted it and `tests` failed. The task ended `EXHAUSTED` at
$41.03 of $36. PR #853 added the file to `touches`, and the second cell
reached `READY_FOR_REVIEW`. One `git grep` would have found the reader before any
cell started.

**A spec already names what it removes.** `Spec.removes` holds `path` or
`path:name` entries (`saffron/intake.py:250`). One validator refuses the same
malformed shapes for `consumes` and `removes`, split at the first colon
(`saffron/intake.py:303-330`). The queue scan reads `removes` only to
compare two specs (`saffron/scheduler.py:802`, `saffron/scheduler.py:836`).
Backlog item b-e773d9 owns that check. Nothing compares a spec with the tree.

**`run_task` already reads the tree base before a cell.** It builds
`cell_spec` at `saffron/task.py:851`. For a spec with `consumes` it then
checks `has_commit` on `cell_spec.tree_base`, resolves each entry, prints one
`refused` line and returns `Refused` (`saffron/task.py:873-886`). That
check catches `UnreadablePath` and `UnicodeDecodeError` per entry and counts
the entry against the task.

**The mirror reads a tree without a checkout.** `file_at` returns a file's
text at a sha, or `None` (`saffron/repos/mirror.py:265`). `_word_pattern` is
the whole-word pattern `unresolved_consumes` uses (`saffron/repos/mirror.py:308`,
`saffron/repos/mirror.py:312`). `retirement_markers` greps a tree-ish with
`-z`, maps exit 1 to no match and raises `GitError` on any other non-zero
exit (`saffron/repos/mirror.py:358-367`).

**Policy and globs.** `Policy.protected` is a list of globs
(`saffron/repos/policy.py:199`). `parse_policy` reads `policy.yaml`'s bytes
with no file or gate read (`saffron/repos/policy.py:277`). `load_policy`
also requires each declared gate's executable to exist
(`saffron/repos/policy.py:268-272`). `scope.matches` is the glob the
`scope` gate uses, where `*` stops at a slash (`saffron/gates/core/scope.py:35`).

**An empty `touches` is not a scope.** `scope` skips a diff when `touches`
is empty (`saffron/gates/core/scope.py:79-88`). The scheduler skips its
criterion path check for the same spec, a bug awaiting DIAGNOSE
(`saffron/scheduler.py:447`).

## Problem

Before its cell, `run_task` lets a spec that removes a name start, though a
file it cannot edit still reads that name. Refuse it there instead, beside
the `consumes` check.

**The mirror function.** Add `removed_name_readers(mirror, sha, entries)`
to `saffron/repos/mirror.py`, next to `unresolved_consumes`. Split each
entry at the first colon. The subject is the name of a `path:name`, or the
whole of a bare `path`. List the candidate files with one `git grep` per
entry over the tree-ish, fixed-string. List names only, with `-l` and `-z`.
A match line can hold bytes that do not decode, and `_run` decodes all of
its output as text (`saffron/repos/mirror.py:54-59`). Exit 1 means no
candidate, and any other non-zero exit raises `GitError`. Skip the file at
the entry's own path. Keep a candidate whose `file_at` text holds the
subject by `_word_pattern`. A candidate that raises `UnreadablePath` or
`UnicodeDecodeError` is kept as well. Return `(path, entry)` pairs, in entry
order, then in the path order git lists.

**The refusal.** In `run_task`, after the `consumes` block, check a spec
whose `removes` and `touches` are both non-empty. Use `cell_spec.tree_base`
and the same `has_commit` guard. Read `.saffron/policy.yaml` at the tree
base with `file_at`, and pass its text to `parse_policy` encoded as bytes.
An absent file, an `UnreadablePath` or `UnicodeDecodeError` from `file_at`,
or a `PolicyError` leaves no path protected. Drop each reader whose path ends in
`.md`, starts with `.saffron/specs/`, or matches a `touches` or `protected`
pattern by `scope.matches`. If any reader is left, print the `refused`
line and return `Refused`. The reason reads as below, with one
`<path> reads <subject>` per reader.

```
<tree base[:12]> holds readers outside touches: tests/test_sigterm.py reads CRITIC_NETWORK
```

Name the new refusal in three docstrings of `saffron/task.py`. The module
docstring lists the refusals `run_task` makes, and calls the `consumes` one
the exception (`saffron/task.py:16-26`). Add a bullet beside it. `Refused`'s
docstring lists its causes (`saffron/task.py:604-614`). Add a sentence there.
`run_task`'s docstring lists them too, and it is already ten lines
(`saffron/task.py:754-763`). Reflow it to name the new refusal within ten. Write the four tests the criteria name,
in `tests/test_removed_name_readers.py`.

## Out of scope

- **The queue scan.** It reads spec text and the ledger, never the mirror,
  and the operator kept it so.
- **A model call.** Nothing here asks an agent whether a file reads a name.
- **A reader inside `touches` that `forbidden` also matches.** `scope`
  refuses that edit too, but the decision was `touches` alone.
- **A frozen record that names a live name.** At `c1fe691c`, 33 files under
  `docs/evidence/` name `run_one_cell`, and ten of them are not Markdown.
  Such a file refuses a spec that removes the name, until its path joins
  `touches` or `protected`. The operator accepts that, and the exclusions
  stay as they are.
- **A bare path read another way**, such as `saffron.replay` for
  `saffron/replay.py`. The subject is the path string as written.
- **Declaring `removes` on any queued spec.** No queued spec declares it at
  `c1fe691c`, so this refusal refuses none, and no `retired_first` is needed.
- **Two documents amended by hand.** This spec's pull request amends
  `docs/agents/issue-tracker.md`'s `removes` paragraph and `DESIGN.md`
  §4.2's gate 0 paragraph. The cell must not edit either.

## Notes for the agent

**Every criterion is new code.** None declares a mutant, so `witness` will
report `skip` for each. The wrong versions under each criterion say what its
witness must still catch.

**At base each witness fails in its body.** The first imports
`removed_name_readers` inside its body, never at module scope. The second
and third find `run_task` ignoring `removes` and starting the cell. The
fourth patches a `removed_name_readers` attribute `saffron.task` lacks.

**Why these files are not readers.** A Markdown mention breaks no gate the
cell must pass. A spec file names what it removes by design. A protected
path cannot sit in `touches`. `protected_touch_refusal` refuses a literal
one there (`saffron/scheduler.py:458`), and `scope` fails any changed file a
`protected` pattern matches, glob or not (`saffron/gates/core/scope.py:103-107`). So a protected reader would refuse a
spec that no `touches` entry can fix, and the operator leaves such a reader
to a person.

**Why an empty `touches` is skipped.** A spec with no `touches` is a bug
awaiting DIAGNOSE, and `scope` skips its diff (see Context). Every reader
would lie outside an empty list, so the check would refuse every such spec.

**Read the policy with `parse_policy`, not `load_policy`.** `load_policy`
needs an exported `.saffron` and checks each gate's executable. A test repo
holds only `policy.yaml`, and this check needs only `protected`.

**A symlink is never a candidate.** Measured on the host's git 2.54.0, a
`git grep` over a tree lists no symlink, whatever its target string holds. A
regular file it points at is read on its own. The cell image's git 2.39.5 is
unmeasured. No witness drives a symlink as a reader.

**The fixtures.** `_plain_repo` and `git` live in `tests/test_mirror.py`.
`tests/test_consumes.py` shows a `run_task` fixture with a faked
`run_one_cell` and `push_unpackaged_work`, and a stacked tree base through a
patched `_resolve_stacked_on`. Import from those files, and do not edit them.
The undecodable case follows `tests/test_consumes.py`'s locale check, since
`file_at` decodes with the locale's encoding.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** A prototype measured 433 changed tokens with `size_gate`, against
the `feature` ceiling of 3000, with 951 more under the test paths. It held
the function, the refusal, the three docstring edits and the four witnesses. Every
test in `tests/test_consumes.py`, `tests/test_mirror.py` and
`tests/test_task.py` passed on it.
