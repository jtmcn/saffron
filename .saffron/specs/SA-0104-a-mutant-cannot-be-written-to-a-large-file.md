---
id: SA-0104
title: a mutant's file crosses into the cell as one argument, so no mutant can be written to a file over 96 KiB and session.py is past it
type: bug
priority: 1
depends_on: []
touches:
  - saffron/cell/worktree.py
  - tests/test_worktree.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/session.py
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/mutation.py
  - saffron/intake.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/phases/**
  - saffron/task.py
  - saffron/cli.py
budget_usd: 14
max_turns: 80
acceptance:
  - claim: >-
      A mutant on a tracked file whose base64 is longer than one argument can
      carry is applied inside the cell with every byte it did not name intact,
      and undone with the tree clean afterwards, when no argument the write
      passes to the cell exceeds 131,000 bytes, the largest measured to run. Today the whole
      file crosses as one argument, so the write fails and the mutant is
      `error`.
    witness: tests/test_worktree.py::test_a_mutant_on_a_file_larger_than_one_argument_is_applied_and_undone
    mutant:
      file: saffron/cell/worktree.py
      find: content.replace(find, mutant.replace.encode(), 1)
      replace: content
  - claim: >-
      A write that fails still restores the file from `HEAD` and raises, as it
      does today.
    witness: tests/test_worktree.py::test_a_write_that_fails_does_not_leave_the_file_truncated
    preserves: true
  - claim: >-
      A mutant on a small file is still applied and undone inside the cell, as
      it is today.
    witness: tests/test_worktree.py::test_a_mutant_is_applied_and_undone_inside_the_cell
    preserves: true
---

## Context

Backlog item **154**, found by `SA-0093`'s first cell on 2026-09-16 (spec loop
run 5).

`source_mutated` (`saffron/cell/worktree.py:481`) is the cell-side half of
`witness`'s mutation run (§5.4.1). It reads the file with `_read_file`
(`:421`), applies the edit on the host, and sends the whole result back with
`_write_file` (`:447`, called at `:567`). `_write_file` base64-encodes the
content and runs one `sh -euc` script whose only argument holds the whole
payload (`:464-466`). `runtime.exec_` carries no stdin, so an argument is the
only channel it has (`:449-454`).

Its own `ponytail:` names the ceiling (`:457-462`). Linux caps a single
argument at `MAX_ARG_STRLEN`. Measured against `saffron/cell-base:python`:
131,000 bytes of argument run, and 131,071 and above fail. Base64 grows a file
by a third, so any file over about 96 KiB cannot carry a mutant.

`saffron/cell/session.py` is 106,783 bytes at `65b1886`, and still growing.
Every mutant against it is now `error`, which aborts the attempt and is charged
to nobody. `SA-0093`'s mutant aborted its first cell (`GATE_ERROR`, $4.42) and
was dropped by #293. `SA-0099`, `SA-0101` and `SA-0102` all edit `session.py`,
so each declares no mutant and has its witnesses as its only check.

On apple/container the failure was not clean either. The `ponytail:` says "the
exec never starts". Measured on this host, the exec failed with
`Stream unexpectedly closed` and left the container wedged: listed `running`,
refusing exec as "not running", and impossible for teardown to remove. No
later cell could start until it was removed by hand.

## Problem

A mutant on any file over about 96 KiB is `error`, never a verdict. The largest
file in the tree, the one most specs edit, is already over it.

## Out of scope

**An intake refusal for a mutant whose file is over the ceiling.** Item 154
asks for one only until the write carries any size. This spec removes the
ceiling instead. `saffron/intake.py` is forbidden.

**Recovering a wedged apple/container cell.** That belongs to the cell
runtime. This spec stops the write that wedged it.

**`saffron/cell/runtime.py`.** Do not add a stdin channel to `exec_`. It is
every caller's view of the cell runtime (Appendix G), and it is forbidden.

## Notes for the agent

**Split the payload across several `runtime.exec_` calls, each under the cap.**
Item 154 allows "several arguments under the cap, appended in order, or another
channel". This spec picks the first, because the host-side tests fake
`runtime.exec_` and nothing else (`_host_git`, `tests/test_worktree.py:764`).
`exec_stream` carries stdin, and `session.py:1021-1027` writes a patch through
it. But a write through it would get past the witness's fake without being
checked. The largest argument measured to run is 131,000 bytes, so keep each
whole argument under that, script text included. Name the cap once, as a
module constant, with the measurement it comes from.

**Where the pieces go.** A base64 string decodes piecewise only at multiples of
four characters. Appending each encoded piece to a scratch file and decoding
once at the end avoids that question entirely. Put any scratch file **outside
`/work`** (the cell's `/tmp` will do) and remove it. `source_mutated`'s undo is
`git checkout HEAD -- <file>`, which never removes an untracked file. A scratch
file left in the worktree would dirty the tree that `committed` judges next.
Make each write start from an empty scratch file: create it with `mktemp`, or
truncate it with `>` on the first piece. Remove it on failure as well as on
success. Otherwise a failed write leaves pieces behind, and the next mutant in
the same cell decodes them along with its own. The witness cannot see `/tmp`,
so this rests on you.

**A failure part-way must still restore.** Today one failed exec leaves the
file truncated, and the code restores it from `HEAD` before raising
(`:467-477`). Keep that for a failure at any step, the first piece or the
last. The preserves witness fakes a failure on the call whose script contains
`base64 -d`. So keep that text in the step that writes the target file, or
that witness stops reaching your restore path. Do not add a separate test for
a later step failing: it passes with the source reverted, because today's
single write fails and restores too, and `revert` blocks any new test that
does.

**The witness.** Build it on `_repo_with_a_file` (`tests/test_worktree.py:1041`)
and `_host_git`. Wrap `worktree.runtime.exec_` with a fake that refuses any
argument longer than 131,000 bytes, the largest measured to run. It returns a
non-zero `runtime.Completed` rather than running the command. Make the file
over 300,000 bytes, so its base64 needs at least three pieces. Give it a byte
that is not valid UTF-8 and a CRLF, as
`test_a_mutant_applied_in_a_real_cell_keeps_the_bytes_it_did_not_name`
(`:1312`) does. The helper writes with `write_text` (`:1048`), so write those
bytes yourself and commit again. Inside the block, assert the file's exact bytes are the
mutated ones. After it, assert the exact original bytes and that `_porcelain`
is empty. Each check catches a plausible wrong implementation. The fake
catches pieces still over the cap. The byte comparisons catch pieces decoded at
the wrong boundary, out of order, or only the first sent. `_porcelain` catches
a scratch file left in `/work`.

**What the mutant proves, and what it does not.** The split is new code, so
nothing in it can be pinned. The mutant sits on the existing call in
`source_mutated`: it makes the write send the unmutated content, so a witness
that never looks at the bytes inside the block survives it. The split itself is
held by the witness's byte comparisons alone. Keep `_write_file`'s name and
signature, and leave its call in `source_mutated` as it is. A reflowed call
stops the mutant from applying, and `witness` then gives no verdict.

**The cell-marked test.** `test_a_mutant_applied_in_a_real_cell_keeps_the_bytes_it_did_not_name`
is the only test that runs the write in a real cell. It cannot run inside
yours. Leave it passing as written. Do not widen it.

**Update the `ponytail:`.** It describes a ceiling this change removes. Replace
it with what now bounds the write, in two lines at most.
