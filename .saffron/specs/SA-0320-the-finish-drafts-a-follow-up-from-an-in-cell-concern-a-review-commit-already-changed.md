---
id: SA-0320
title: "The finish drafts a follow-up from an in-cell concern whose cited line a review commit already changed"
type: bug
priority: 2
estimated_lines: 30
estimate_measured: true
touches:
  - saffron/qualify.py
  - tests/test_qualify.py
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
  - saffron/finish.py
  - saffron/follow_up.py
  - saffron/end_review.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/agents/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_finish.py
  - tests/test_follow_up.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 26
max_attempts: 3
max_turns: 140
risk: standard
acceptance:
  - claim: >-
      In `qualify`, a layer's in-cell REVIEW concern is still anchored over
      the packaged range. One that would be `qualified` there becomes
      `unverified` when its cited line, read at the packaged head, lies in a
      hunk of the diff from the packaged head to the head `graded_fields`
      gives that layer. That diff is read with `DIFF_FLAGS`, so a hunk
      carries three lines of context. The reason names that graded head's
      full sha. The concern joins `pool` and no group. The witness drives
      one layer graded two review commits above its packaged head. The
      first commit edits one cited line in place and deletes another. The
      second inserts two lines below a third cited line and deletes the
      file a fourth cites. All four are `unverified` in `pool`, and
      `finish.write_findings` writes each with that outcome and reason. In
      that layer three findings stay `qualified` and become `follow_up`
      entries. One is a concern four lines past the insertion, one is a
      concern in a file neither commit touched, and one is an end-review
      finding citing the line edited in place. A concern unanchored over
      the packaged range, whose line the first commit edits, stays
      `unanchored` with an empty reason. A layer below, whose graded head
      is its packaged head, keeps its concern `qualified`. That concern
      cites a line the upper layer's own packaged change rewrites.
    witness: tests/test_qualify.py::test_an_in_cell_concern_whose_cited_line_a_review_commit_changed_is_not_drafted
    wrong_versions:
      - The check diffs with zero lines of context, so the concern one line above the insertion stays qualified.
      - The check diffs only the graded head against its own parent, so the first review commit's two changes stay qualified.
      - The check reads the graded side of the diff, so the concern past the insertion is dropped once the deletion shifts the lines.
      - The check diffs from the packaged head's parent, so every concern the packaged change anchored is dropped.
      - The check matches a concern by file alone, so the concern past the insertion is dropped.
      - The reason names the packaged head rather than the graded head.
      - The reason names only the graded head's first twelve characters.
      - The check overrides every outcome, so the unanchored concern becomes unverified.
      - The dropped concern is recorded `killed`, so it never reaches the findings file.
      - Every layer is checked against the top layer's graded head, so the lower layer's concern is dropped.
      - The end-review findings are checked against the packaged head too, so the end-review finding on the edited line is dropped.
  - claim: >-
      A layer's in-cell concern whose cited line no hunk of that later diff
      covers is still `qualified` and joins its layer's group. So is a
      concern in a layer `fields` does not name, which reads its packaged
      head through `graded_fields` and so has no later diff.
    witness: tests/test_qualify.py::test_findings_are_anchored_and_probed_over_the_range_the_end_review_graded
    preserves: true
    wrong_versions:
      - The check reads the graded head as `fields[task_key]`, so a layer `fields` does not name raises KeyError.
---

## Context

Backlog item **b-1b05be**, under `DESIGN.md` §5.7 and ADR 7's amendment
for a deferred finish. Every line below was read at `068862d9`.

**The run that found it.** This is the spec loop's run 48. `saffron finish
53`, `54` and `55` each wrote a `findings.json`. Its in-cell critic rows named
the PACKAGE heads `3df11823`, `9a39daa9` and `ce276ec7`. The end review read
the reviewed heads `a0ec477e`, `78f1453b` and `872215b4`. Five of those
in-cell rows went to the writer as follow-up drafts. Four cited lines the
review commits changed. The files are
`~/.saffron/batches/v0/finish/{53,54,55}/findings.json`.

**Measured on those five.** Each pair was diffed in the home mirror with
three lines of context. The diff was reversed, so its new side is the
PACKAGE head. The
four rows the item calls fixed each fall in a hunk. Read at each PACKAGE
head, not at base, these are
`saffron/cli.py:2896`, `tests/test_cli.py:2666`, `saffron/task.py:1124` and
`saffron/batch.py:243`. The fifth, `saffron/task.py:1144`, falls in none,
and the item says the spec answered it. With zero lines of context,
`saffron/cli.py:2896` falls in no hunk, since its review commit inserts
lines after line 2897.

**Where `qualify` reads each range.** `qualify` walks each layer top down
(`saffron/qualify.py:268-317`). End-review findings read the range
`graded_fields` gives the layer (`:272-294`). In-cell concerns read the
packaged range from `end_review.layer_fields` instead (`:295-317`). Its
docstring says why: "their line numbers were recorded against it"
(`:227-230`). `layer_fields` sets `head` to the task's `pushed_sha`
(`saffron/end_review.py:140-148`). `graded_fields` returns the end review's
own entry for the layer, else `layer_fields` (`saffron/qualify.py:193-203`).
`branch_heads` gives an entry whose `head` is the branch's fetched head
(`saffron/end_review.py:260-302`).

**What the finish reads.** `_stack_follow_ups` hands `qualify` the end
review's own `stack.fields` (`saffron/cli.py:1633-1646`).
`_keeping_graded_heads` copies each entry's `head` into the heads the
finish reads (`saffron/cli.py:940-945`). So the head `graded_fields` gives a
layer is the head the finish reads for it.

**How a decision is recorded.** `_qualify_range` anchors over
`base..head`, decides each finding with `_decide`, and records each through
`ledger.record_qualification` (`saffron/qualify.py:124-173`). An in-cell
concern carries no probe (`:81-96`). So `_decide` gives it `unanchored`,
`qualified`, or `unverified` for the adequacy lens (`:176-190`). `_fold`
puts a `qualified` finding in a group and any outcome but `killed` in
`pool` (`:234-239`).

**How the findings file reads it.** `finish._layer_findings` walks a
layer's qualification rows. It skips `killed`, maps `qualified` to
`pooled` or `follow_up`, and passes any other outcome through with the
row's own reason (`saffron/finish.py:270-296`). An in-cell row's `head`
stays `pushed_sha` (`:279-283`). A layer of generation 1 then lists its
critic's findings again as `left_by_critic` (`:297-300`).

**Hunk lines.** `parse_diff` returns each new-side path's lines a hunk
covers, context included (`saffron/agents/findings.py:124-164`). A deleted
file contributes no new-side lines (`:157-160`). `DIFF_FLAGS` pins
`--unified=3` (`saffron/cell/worktree.py:211`).

**The tests.** `_graded_fixture` builds a two-layer stack graded above its
packaged heads (`tests/test_qualify.py:997-1150`).
`test_findings_are_anchored_and_probed_over_the_range_the_end_review_graded`
drives it (`:1170-1300`). Its concern `ic-packaged` cites line 2 of
`src/b.py`, which no later commit touches. It stays in its group
(`tests/test_qualify.py:1211`). A run whose `fields` lacks the top layer
keeps it there too (`tests/test_qualify.py:1266-1269`).

## Problem

An in-cell concern is anchored at the head PACKAGE pushed. A review commit
can change its cited line before the end review runs. The finish still
drafts a follow-up from it, so the writer drafts a fix for code that is
already gone.

1. **The later range.** For each layer with in-cell concerns, read the head
   `graded_fields` gives it. When that head differs from the packaged head,
   diff the two with `DIFF_FLAGS`. Collect each path's packaged-side lines
   a hunk covers.
2. **The drop.** Take a concern `_decide` would make `qualified`, whose
   line is in that set for its file. It becomes `unverified` instead. The reason
   names the graded head's full sha. Any other outcome is left as it is.
3. **What stays.** Anchoring still reads the packaged range. End-review and
   join findings are not checked. A layer whose graded head is its
   packaged head is not checked.
4. **Docstrings.** The module docstring and `qualify`'s say a concern whose
   cited line a later commit changed is `unverified`. Each stays within ten
   lines, the prose gate's cap.

## Out of scope

- The `head` field of an in-cell row in `findings.json`. It stays
  `pushed_sha`, the head the line was cited at (`saffron/finish.py:279-283`).
- Re-anchoring an in-cell concern at the graded head.
- The join's findings, and an adequacy concern `_decide` already makes
  `unverified`.
- The writer's prompt, which still names a kept concern's packaged head
  (`saffron/follow_up.py:149-152`).
- A follow-up draft that fails to parse (b-781ea4), or one a queued spec
  owns (b-cc87b1).
- Any new qualification outcome. `unverified` already means the host could
  not confirm the finding, and its reason says why.

## Notes for the agent

The drop is new code, so criterion 1 declares a witness and no mutant, and
`witness` will report `skip` for it. Criterion 2 is a `preserves` witness
that exists at base and must pass unchanged.

**Read the reversed diff.** `git diff <graded>..<packaged>` puts the
packaged head on the new side, so `parse_diff`'s `hunk_lines` are already
packaged-side lines. A file the graded head deleted is a whole added file
there, so every line it had is covered. The prototype behind this spec read
the diff this way.

**The fixture for criterion 1.** Build it beside `_graded_fixture` with
`_git`, `_write`, `_finding`, `_key` and `_Built`. Add no global git
config. `DIFF_FLAGS` sets the context itself.
- Make one batch with `ledger.create_batch`, and give both runs its id, so
  `finish.write_findings` finds the layers.
- Record both layers with generation 0. Generation 1 lists every critic
  finding a second time as `left_by_critic`.
- The base commit holds `src/a.py` of 60 lines, `src/b.py`, `src/gone.py`
  and `src/u.py`.
- TE-1 pushes `H1`, which rewrites line 10 of `a.py`. TE-2 pushes `H2` on
  `H1`. It rewrites lines 10, 20, 39 and 44 of `a.py`, line 6 of `b.py`
  and line 2 of `gone.py`.
- `R1` edits line 10 of `a.py`, deletes its line 20 and edits line 3 of
  `u.py`. `R2` inserts two lines after what was line 40 of `a.py`, and
  deletes `gone.py`.
- TE-2's concerns cite lines 10, 20, 39 and 44 of `a.py`, line 2 of
  `gone.py`, line 6 of `b.py` and line 3 of `u.py`. Its end review cites
  line 10 of `a.py`. TE-1's concern cites line 10 of `a.py`.
- In `fields`, TE-1's head is `H1`. TE-2's head is `R2` and its diff base
  is `H1`.
- Nothing here carries a probe. Replace `session.probe_findings` with a
  function that raises, so a probe call fails the test.

The deletion in `R1` shifts the lines below it. So the line past the
insertion's context, line 44 of `a.py`, falls in that hunk's graded side and not
its packaged side. A prototype of this fixture killed every wrong version
listed under criterion 1. The `preserves` witness killed the one under
criterion 2.

**The neighbours.** `tests/test_finish.py`, `tests/test_follow_up.py` and
`tests/test_cli.py` passed against the prototype unchanged.
`follow_up.write_follow_ups` drafts only from `groups`
(`saffron/follow_up.py:288`).
