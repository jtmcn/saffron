---
id: SA-0378
title: The finish reads an in-cell concern's line from the packaged head, not the tree its lenses read, so a line REBUT changed stays live
type: bug
priority: 2
estimated_lines: 86
estimate_measured: true
depends_on: [SA-0377, SA-0375, SA-0373]
consumes:
  - saffron/cell/session.py:reviewed-diff.json
touches:
  - saffron/qualify.py
  - saffron/cli.py
  - tests/test_qualify.py
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
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cell/**
  - saffron/events.py
  - saffron/finish.py
  - saffron/follow_up.py
  - saffron/end_review.py
  - saffron/ledger.py
  - saffron/projection.py
  - saffron/task.py
  - saffron/agents/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/repos/**
  - tests/test_session.py
  - tests/test_events.py
  - tests/test_finish.py
  - tests/test_follow_up.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 40
max_attempts: 3
max_turns: 170
acceptance:
  - claim: >-
      `qualify.qualify` takes an `out_dir`, the batch tree's root. For a
      layer with in-cell concerns it reads `out_dir / <spec id> /
      reviewed-diff.json`. The record is used when its `sha256` is the
      sha256 of `raw` encoded as UTF-8, and when it is bound to the layer's
      task. It is bound when a REVIEW phase line in that directory's
      `events.jsonl` names the `sha256`, and the next `RecordAppend` line
      after it carries the layer's task key. A used record's tree is
      rebuilt as `tree_base` with `raw` applied. A concern `_decide` would file `qualified` is then filed `unverified`
      when its cited line sits in a hunk of the diff from the graded head
      to that tree. The diff is read with `DIFF_FLAGS` on the tree's side.
      This holds whether or not the graded head is the packaged one. The
      reason reads `its cited line changed between the tree its critic read
      <tree> and the graded head <graded head> after it was cited`. The
      rebuilt tree's id and the graded head are both in full. The witness
      drives a stacked layer, graded one review commit above its packaged
      head, and an unstacked one graded at its packaged head. Both records
      are bound. A later task of the stacked layer's spec stopped before
      REVIEW. Four concerns cite the stacked layer's tree. Its REBUT rewrote
      the first in place, and the second sits three lines below it. Its
      review commit rewrote the third, and the line four lines above the
      fourth. REBUT also inserted four lines between the third and the
      fourth. The first three are `unverified`, and the fourth stays
      `qualified`. The unstacked layer's REBUT rewrote one cited line, which
      is `unverified`, and a concern six lines above it stays `qualified`.
      `finish.write_findings` writes each `unverified` one with that outcome
      and reason, and the fourth as `follow_up`.
    witness: tests/test_qualify.py::test_an_in_cell_concern_is_dropped_when_its_line_changed_since_the_tree_its_critic_read
    wrong_versions:
      - The record is ignored and the diff stays the packaged head to the graded head, so the line REBUT rewrote stays qualified.
      - The rebuilt tree is diffed against the packaged head, so the line the review commit rewrote stays qualified.
      - The diff is read on the graded head's side, so the fourth concern is dropped.
      - The diff is read without `DIFF_FLAGS`, so under a global `diff.context` of 0 the concern dropped by context alone stays qualified.
      - The tree is rebuilt on the run's `base_sha`, so the stacked layer's diff does not apply and its concerns keep the packaged head's drop.
      - The record is used only when the graded head differs from the packaged one, so the unstacked layer's concern stays qualified.
      - The hash is taken over `raw` encoded as Latin-1, so the stacked record's character outside ASCII fails it.
      - The record is bound only when its line sits after the log's last `Ceilings` line, so the later task's span unbinds it.
      - The reason names the packaged head, or the tree's first 12 characters.
      - The dropped concern is recorded `killed`, so `finish.write_findings` never writes it.
  - claim: >-
      A layer with in-cell concerns whose record cannot be used keeps the
      drop from the packaged head to the graded head as before. It calls
      `note` once, with `reviewed_diff`, `False`, and `<spec id>: <cause>,
      so its in-cell concerns are checked from the packaged head`. The
      witness drives six causes on the stacked layer, each in its own tree,
      while the unstacked layer's record stays bound. The causes are `no
      reviewed-diff.json`, and `reviewed-diff.json is unreadable` for a
      truncated file. They go on with `its sha256 does not match its diff`
      and `no REVIEW line binds it to this task`. The last two are `the
      mirror lacks its tree base <sha>` and `its diff does not apply to
      <sha>`. In each case two concerns are `unverified` with the packaged
      head's reason, two stay `qualified`, and the only note is the stacked
      layer's.
    witness: tests/test_qualify.py::test_a_layer_whose_record_cannot_be_used_keeps_the_packaged_heads_check
    wrong_versions:
      - A truncated file raises out of `qualify`.
      - The recorded `sha256` is trusted without hashing `raw`, so an edited `raw` is rebuilt.
      - The record is bound by any REVIEW line naming its hash, so a later task's record is read as this task's.
      - The record is bound when its hash line and a `RecordAppend` under the layer's key both sit anywhere in the log.
      - A `tree_base` the mirror lacks raises out of `qualify`.
      - A diff that does not apply raises out of `qualify`.
      - Every cause prints the same words.
      - A note is printed for the bound layer too.
      - A layer whose record cannot be used skips the later drop altogether, so the concern its review commit rewrote stays qualified.
  - claim: >-
      `_stack_follow_ups` hands `qualify.qualify` its own `out_dir`, the
      root that holds each task's directory. The witness builds it with an
      `out_dir` of its own and reads what `qualify.qualify` received.
    witness: tests/test_cli.py::test_a_stack_batchs_qualify_reads_task_directories_under_the_batch_tree
    wrong_versions:
      - "`qualify.qualify` is handed `out_dir / \"follow-ups\" / batch_key`, where no task directory lives."
  - claim: >-
      A layer with no record keeps SA-0320's drop, its reason naming the
      packaged and the graded heads.
    witness: tests/test_qualify.py::test_an_in_cell_concern_whose_cited_line_a_review_commit_changed_is_not_drafted
    preserves: true
    wrong_versions:
      - A layer with no record drops nothing, so the concerns SA-0320's review commits rewrote stay qualified.
---

## Context

Backlog item **b-1b05be**, the second of two specs closing its Record line
of 2026-11-11. It cites `DESIGN.md` §5.7. Every line number below was
read at `3f9ee9d9`.

**The incident.** Finish 80 graded `SA-0369`'s two in-cell concerns as
live. REBUT changed the cited line 308 of `worktree.py` before PACKAGE pushed, and
shifted every line below 959 by one.

**What `qualify` does now.** `_in_cell_concerns` rebuilds a layer's REVIEW
concerns from the `findings` table (`saffron/qualify.py:90-105`). The
layer's block anchors them over the packaged range and passes the graded
head (`saffron/qualify.py:324-349`). `_qualify_range` then diffs the graded
head against the packaged head and reads the packaged side
(`saffron/qualify.py:143-148`). A `qualified` concern whose line sits in a
hunk becomes `unverified`, with a reason naming both heads
(`saffron/qualify.py:189-197`). When the two heads are equal, nothing is
diffed. A REVIEW lens cites lines of the critic cell's tree, which is
`tree_base` plus the exported patch, applied by `_apply_and_commit_patch`
(`saffron/cell/session.py:1441-1510`).
REBUT then commits in the implementer's cell. Teardown exports that cell's
patch, which PACKAGE pushes (`saffron/cell/session.py:1074-1075`). So a
line REBUT changed never reaches that diff, and the critic's numbers are
read against the wrong tree.

**What `SA-0375` records.** REVIEW writes `reviewed-diff.json` in the task
directory as the critic cell's export returns. It holds `tree_base`, `raw`
and `sha256`, the hex sha256 of `raw` encoded as UTF-8. A REVIEW phase line
then names the full hash in `events.jsonl`. The task directory is `out_dir
/ spec_id` (`saffron/cell/session.py:2321`). A later task of the same spec
that stops before REVIEW leaves the file in place, as that spec's Out of
scope says. So this spec binds the file to its task before using it.

**Why the next `RecordAppend` binds it.** The ledger's sink writes a
line per fact into its task's directory, naming the task key (`saffron/ledger.py:675-698`, `saffron/cli.py:116-125`,
`saffron/events.py:389-398`). Every command's ledger carries that sink
(`saffron/cli.py:398-402`). Each lens session opens an attempt, and
`SA-0369`'s log shows its `attempt_opened` line right after the lens's own
REVIEW line (`~/.saffron/batches/v0/SA-0369/events.jsonl`, line 1932). A
later task of the spec writes its own key there.

**Where `out_dir` comes from.** `qualify.qualify` takes no directory now
(`saffron/qualify.py:235-249`). Its one caller is `run_qualify` inside
`_stack_follow_ups` (`saffron/cli.py:1857-1874`). Both the night and
`saffron finish` hand that function the batch tree's root
(`saffron/cli.py:2620-2626`, `saffron/cli.py:2879-2886`), which is
`<home>/batches/v0` by default (`saffron/cli.py:350-351`).

**Is a stacked `tree_base` still in the mirror?** Measured on 2026-11-11
in `~/.saffron/mirrors/saffron-f6b7e296a444.git`. Of 158 task directories
whose `patch.json` names a `tree_base` other than `base_sha`, 114 hold it in
the mirror. The other 44 are tasks last updated by 2026-10-12. For every
one of those 44, the task's newest `pushed_sha` is gone too. The packaged
diff at `saffron/qualify.py:139` then raises before any concern is read.
All 155 unstacked `tree_base` values are present. So the missing
`tree_base` fallback guards a mirror that lost objects, and no finish
measured so far reaches it.

## Problem

The finish reads an in-cell concern's line from the packaged head. Read it
from the tree the lenses read, rebuilt from `SA-0375`'s record, and diff
that tree against the graded head.

In `saffron/qualify.py`, `qualify` gains a required `out_dir: Path`. In the
layer's concerns block, read and check the record, then rebuild the tree.
Rebuild it in the mirror under a temporary `GIT_INDEX_FILE`, with
`read-tree` of `tree_base`, `apply --cached` with `raw` on stdin, and
`write-tree`. Use `worktree.git_argv` for those three calls, the pins the
critic cell's own `git apply` ran under (`saffron/cell/session.py:1471`).
Pass the tree to `_qualify_range`. There, diff the graded head against the
tree with `DIFF_FLAGS`, so `parse_diff`'s `hunk_lines` reads the tree's side
(`saffron/agents/findings.py:159-162`). A layer whose record cannot be used
calls `note` with its cause and keeps today's diff.

In `saffron/cli.py`, `run_qualify` passes `out_dir=out_dir`. In
`tests/test_qualify.py`, `_Built` gains an `out_dir` field that its `run`
passes. Write the three new tests the criteria name.

## Out of scope

- **A fix below the cited line.** `SA-0369`'s other concern cites
  line 1008 of `session.py`, and REBUT fixed its defect six lines below. The
  settled rule is that the cited line changed, so a hunk three lines away
  is the reach.
- **Anchoring.** A concern still anchors over the packaged range at the
  packaged head (`saffron/qualify.py:139-140`). A REBUT shift can move the
  line anchoring reads too. Re-anchoring on the critic's tree is another
  change.
- **End-review and join findings.** They are read at the graded head and
  never meet this drop.
- **`SA-0375`'s record.** Its writer, its file name and its keys stay as
  that spec fixes them. `saffron/cell/**` is forbidden here.
- **A ledger with no events sink.** `fold` and `next-id` build one
  (`saffron/ledger.py:681-683`), and open no cell. A task recorded under one has no `RecordAppend` lines, so
  its record is never bound.
- **Tasks that ran before `SA-0375`.** They wrote no record and keep the
  packaged head's drop, with a note.

## Notes for the agent

**Every criterion but the fourth is new code.** The reader, the binding
and the rebuilt tree are absent at base, so no spelling is forced. None declares a mutant, and `witness` reports `skip` for each. The
cause strings and the reason are fixed here, since each witness compares
them whole. The fourth criterion preserves `SA-0320`'s witness, which
passes unchanged once `_Built.run` passes `out_dir`.

**Seed each witness so its wrong version reaches its branch.** Build one
fixture for both `qualify` witnesses, in the shape of `_later_diff_fixture`
(`tests/test_qualify.py:1344-1472`).

- Set `GIT_CONFIG_GLOBAL` to a file holding `diff.context = 0`, as
  `_stack_mirror` does (`tests/test_qualify.py:103-105`). That kills a diff
  read without `DIFF_FLAGS`.
- `A` seeds `src/a.py`, 60 lines with line 46 `a46 retry_budget`, and
  `src/p.py`, 12 lines. TE-1's critic tree `T1` is `A` with lines 5 and 8
  of `p.py` rewritten. Its packaged head `P` is one commit on `A`, with
  line 8 rewritten again. TE-2's critic tree `T2` is `P` with lines 10, 30
  and 50 of `a.py` and line 5 of `p.py` rewritten. Give line 10 an `é`, so
  a Latin-1 hash differs. End line 50 with `retry_budget`, so its concern
  anchors by token.
- TE-2's packaged head `H` is one commit on `P`. It rewrites line 10
  again and inserts four lines after line 40. Its graded head `G` is a
  commit on `H` rewriting `G`'s lines 30 and 50.
- Each record's `raw` is `git diff` with `DIFF_FLAGS` from its tree base
  to its tree. Write `events.jsonl` through `events.EventLog`, with
  `Ceilings`, `PhaseStart` and `RecordAppend` values as production writes
  them. TE-2's log ends with a second `Ceilings` line and a `RecordAppend`
  under a second ledger task of spec TE-2. The expected tree is `git
  rev-parse <T>^{tree}`, read in the test.
- TE-2's concerns cite lines 10, 13, 30 and 50 of `a.py`. TE-1's cite
  lines 8 and 2 of `p.py`. Pass TE-2 a graded head of `G` through `fields`,
  as `SA-0320`'s witness does with `replace`.
- For criterion 2, the truncated file is its first 40 characters. The
  edited `raw` and the other task's `raw` each change one added line and
  still apply. The other task's log names its own hash and its own key
  after a second `Ceilings` line. The lost tree base is 40 hex characters
  naming no object. The diff that does not apply names `A` as its tree
  base.
- For criterion 3, start from
  `test_a_stack_batchs_follow_up_writer_is_seeded_at_the_top_head_the_end_review_graded`
  (`tests/test_cli.py:12942-13047`). Patch `fetch_default_branch`, so no
  fetch reaches GitHub.

**What the witnesses leave.** Criterion 2 drives a truncated file. A JSON
value that is not an object, or an object missing a key, is the same cause,
and no witness drives it. A hash line with no `RecordAppend` after it
leaves the record unbound, and no witness drives that either. A layer with
no in-cell concerns reads no record and prints no note, also undriven.

**`apply --cached` under a temporary index works in a bare mirror.**
Measured on 2026-11-11 with the host's git 2.54. The witnesses build an
ordinary repository, which the cell's git 2.39.5 reads the same way.

**At base each witness fails in its body.** `qualify` there takes no
`out_dir`, and `run_qualify` passes none. Import nothing the change adds at
module scope.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words.

**Size.** A prototype on `SA-0375`'s diff measured 345 changed tokens with
`size_gate`, against the `bug` ceiling of 1300. It held 1287 more under
the test paths. Every test in `tests/test_qualify.py` passed on it, with
the three witnesses here.
