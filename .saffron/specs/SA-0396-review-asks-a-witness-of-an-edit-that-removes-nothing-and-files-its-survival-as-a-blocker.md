---
id: SA-0396
title: "REVIEW asks a witness of an edit that removes nothing, and files its survival as an adequacy blocker"
type: feature
priority: 3
risk: elevated
estimated_lines: 239
estimate_measured: true
depends_on: [SA-0394, SA-0395]
consumes:
  - saffron/repos/mirror.py:files_after
  - saffron/probe.py:inert_edit
pending_symbols:
  - saffron/repos/mirror.py::files_after
  - saffron/probe.py::inert_edit
  - saffron/repos/policy.py::inert
touches:
  - saffron/cell/session.py
  - saffron/phases/review.py
  - tests/test_session.py
  - tests/test_review.py
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
  - saffron/probe.py
  - saffron/repos/**
  - saffron/qualify.py
  - saffron/cell/worktree.py
  - saffron/gates/**
  - saffron/intake.py
  - saffron/agents/**
  - saffron/report/**
  - saffron/task.py
  - saffron/cli.py
  - tests/test_probe_check.py
  - tests/test_policy.py
  - tests/test_mirror.py
  - tests/test_qualify.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 48
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      REVIEW refuses an inert edit before any cell applies it, for a
      criterion probe and a wrong version alike. `_apply_criterion_probes`
      takes the repo's declared inert patterns, which `_drive_cell` passes
      from `policy.probes.inert`. With a pattern declared, it reads the
      edited files with one `files_after` call, before its check for a
      `tests` gate. The call names the mirror, the spec's `tree_base`, the
      patch the critic cell applies and the set of files the edits name,
      criterion probes' and wrong versions' alike. A pair whose file reads as text, and whose
      edit `inert_edit` refuses under those patterns, is recorded `unproven`.
      Its reason is its `summary` and sits under `refusal`. It never reaches
      the mutator or a witness, so it is never `survived` and files no
      adequacy finding. The REVIEW line counts it among the refused. A pair
      whose file reads `None` reaches the mutator as at base, as does one
      whose `find` is absent from the text or occurs in it twice. The
      witness drives one cell of a stacked spec through REVIEW, under a
      policy declaring two inert patterns. Its `tree_base` differs from its
      `base_sha`. Its criterion-probe session names one inert edit on a
      third file the stubbed read returns as text. Its wrong-version session
      names five edits. They are an inert edit, an
      edit that keeps its find and adds a top-level statement that executes,
      and an inert-shaped edit on a file the stubbed read returns as `None`.
      The last two are inert-shaped edits whose find is absent from the text
      and whose find occurs in it twice. It asserts the read's arguments,
      the `tree_base` and all three files among them. It asserts that only
      the last four reach the mutator. It asserts both inert
      edits' records and the outcomes `unproven`, `survived`, then `killed`
      three times. It asserts that only the survivor reaches
      `rebuttal.json`, and both REVIEW lines' counts.
    witness: tests/test_session.py::test_an_edit_that_removes_nothing_is_refused_before_any_witness_reads_it
    wrong_versions:
      - The refusal applied to wrong versions alone, so the criterion probe's inert edit reaches the mutator.
      - The outcome set to `unproven` with no `refusal` key, so the REVIEW line counts the edit as expressed.
      - The `summary` set to a fixed sentence rather than the edit's own reason.
      - The file read at `tree_base` through `file_at` instead of `files_after`, so the patched text is never judged.
      - A pair whose file reads `None` refused whenever its `replace` keeps its find.
      - Every edit that keeps its find refused, so the edit that adds an executing statement never reaches its witness.
      - An edit whose find is absent from the host's text refused at the host rather than left to the cell.
      - An edit whose find occurs twice in the host's text refused at the host rather than left to the cell.
      - One `files_after` call made per pair, so the tree is built once for each edit.
      - The read built at `base_sha` rather than `tree_base`, so a stacked spec's edits are judged against the wrong tree.
      - The read's paths collected only from wrong versions, so the criterion probe's file is never read and its inert edit reaches the mutator.
      - The read's paths collected only from pairs carrying `version`, with the same effect.
      - The call site passing an empty list rather than `policy.probes.inert`, so nothing is ever refused.
  - claim: >-
      A repo that declares no inert pattern refuses no edit as inert. No
      `files_after` read is made, and every pair reaches the mutator as at
      base. When patterns are declared and `files_after` returns an empty
      dict, no edit is refused as inert either, and each pair reaches the
      mutator as at base. Under declared patterns, a `GitError` from
      `files_after` reaches the caller of `run_one_cell` unchanged, before
      any edit is applied. `_drive_cell`'s `except BaseException` then
      marks the ledger's run row `ABORTED` and the task `ORPHANED`. The witness drives three cells
      through REVIEW, each with one inert-shaped criterion probe and one
      inert-shaped wrong version. Under declared patterns with the read
      stubbed to return an empty dict, both edits reach the mutator, and the
      version is `killed` with no `refusal` key. Under no declared pattern
      with the read stubbed to raise a `GitError`, the same holds and the
      drive returns. Under declared patterns with that raising read, the
      drive raises it. No edit reaches the mutator, and the reopened ledger
      holds those two states.
    witness: tests/test_session.py::test_no_inert_pattern_or_unbuilt_tree_refuses_an_edit_and_a_broken_read_orphans
    wrong_versions:
      - The read made whether or not a pattern is declared, so a broken read orphans a repo that declares none.
      - An empty read taken as leave to judge every edit that keeps its find, so both edits are refused.
      - The read's dict indexed by path, so an empty read raises `KeyError` instead of letting each pair through.
      - A `GitError` from the read caught and treated as an empty read, so every pair reaches the mutator and the task goes on.
---

## Context

Backlog item **b-7fc792**, filed from spec loop run 70 while reviewing
#1203 (`SA-0390`). It cites `DESIGN.md` §5.4.1 and §5.5. This spec is the
third piece of a split. `SA-0394` gives the host a read of the critic
cell's tree, and `SA-0395` gives it the rule. This spec makes REVIEW use
both. Every line number below was read at `841e1257`, where `SA-0395`'s
hand edits sit on `dffa5474`.

**What happened**. `SA-0390` declared a wrong version where `risk` is
left out and reads `standard`. REVIEW's wrong-version session gave a reason
that names deleting the `risk=` keyword from `queue_line`. Its edit kept
the whole `find` and appended `def _risk_placeholder_removed_marker():
pass` after it. The witness passed under an edit that changed nothing, and
the host filed the version `survived` as an adequacy blocker. REBUT argued
it and the host kept it as recorded disagreement. The task's
`wrong-versions.json` under `~/.saffron/batches/v0/SA-0390/` holds the
edit and its outcome.

**What the parents give this spec**. `SA-0394` adds
`files_after(mirror, tree_base, patch, paths)` to
`saffron/repos/mirror.py`. It builds `tree_base` with `patch` applied, the
tree a critic cell holds, and reads each path from it. A path that tree
lacks, or that `file_at` finds unreadable, reads `None`. A tree that
cannot be built, or empty `paths`, returns an empty dict. Any other
`GitError` raises. `SA-0395` adds `inert_edit(before, edit, patterns)` to
`saffron/probe.py`. It returns a reason when the edit keeps its whole
`find`, which occurs once in `before`. Every line the `replace` adds must
match one of the repo's patterns. The first kept line beside the added
text must sit no deeper than the least indented added line. It returns
`None` otherwise, and always for an empty `patterns`. This spec `consumes`
both functions. `SA-0395`'s pull request landed `ProbePatterns` by hand.
`Policy.probes` holds it, and its `inert` list holds the patterns a repo
declares (`saffron/repos/policy.py:196`, `:206`, `:236`). This repo's
`.saffron/policy.yaml` declares four in its `probes:` block.

**Where an expression becomes an outcome**. The REVIEW block calls
`review.run_criterion_probes` and `review.run_wrong_versions` in the critic
cell (`saffron/cell/session.py:3441`, `:3456`). Once that cell is torn
down, it builds one `pairs` list. Each criterion probe comes first, then
each wrong version with its criterion (`saffron/cell/session.py:3514-3531`).
`_drive_cell` hands the list to `_apply_criterion_probes`
(`saffron/cell/session.py:3535`), with the mirror, the spec and
`patch_to_review`. It passes `thread_env` and `test_paths` from the
`policy` it holds (`saffron/cell/session.py:3540-3541`). `_drive_cell`
loads that `policy` from the `.saffron/` it exported at `base_sha`
(`saffron/cell/session.py:2357`). `_apply_criterion_probes` refuses a pair
host-side before any cell. Its first loop records a pair with no edit as
unproven, and one `probe.probe_refusal` refuses too, with a `refusal` key
(`saffron/cell/session.py:2109-2120`). With no pair left it returns
(`saffron/cell/session.py:2122`). The rest are applied in one cell that
`_apply_criterion_probes` opens (`saffron/cell/session.py:2248`), by
`worktree.source_mutated` (`saffron/cell/session.py:2155`). Then the
criterion's witness answers, and a survivor becomes an adequacy finding.

**What refuses an edit today**. `source_mutated` yields a reason for six
edits that apply nothing, among them a `find` that is absent and one that
matches more than once (`saffron/cell/worktree.py:712-717`). An edit that
applies and changes nothing is not among them. `probe_refusal`
(`saffron/probe.py:154`) reads only the path.

**How refusals are counted**. `describe_criterion_probes` and
`describe_wrong_versions` count every entry with a `refusal` key as
refused (`saffron/phases/review.py:663`, `:858`). An inert edit carrying
the key is then counted refused with no change to either function.

**What a host git failure does in a cell's drive today**. `_drive_cell`
creates the run row and the task row (`saffron/cell/session.py:2404`,
`:2407`). It then enters a `try` (`saffron/cell/session.py:2460`) whose
`except BaseException` marks the run row `ABORTED` and the task
`ORPHANED`, then re-raises (`saffron/cell/session.py:4053-4060`). The
REVIEW block sits inside that `try`. Its own inner `try` catches only
`CriticPatchRejected` and `CriticPatchUnrepresentable`
(`saffron/cell/session.py:3469`, `:3476`), and `_apply_criterion_probes`
is called in its `else`. So a `GitError` raised from `files_after` reaches
the outer handler with no new code.

**One direct caller in the tests**. The helper `_run_apply_criterion_probes`
calls `session._apply_criterion_probes` with every keyword spelled out
(`tests/test_session.py:15169`). A new required keyword needs one line
there.

## Problem

Give `_apply_criterion_probes` a required keyword `inert_patterns:
Sequence[str]`. Pass `policy.probes.inert` at its one call in `_drive_cell`,
and an empty list from `_run_apply_criterion_probes`.

In `_apply_criterion_probes`, after the existing refusal loop, read every
remaining pair's file with one `files_after` call when `inert_patterns`
holds a pattern. Put the read and the inert refusal before the check for a
`tests` gate (`saffron/cell/session.py:2124-2130`). An inert edit is then
refused even where nothing could answer it. Make no read when it holds none. Import
`saffron.repos.mirror` inside the function, as its other imports are, and
call it through the module, so a test's stub reaches it. Ask
`probe.inert_edit` of each pair whose file came back as text, with
`inert_patterns`. A pair whose file reads `None`, or is missing from the
result, is never refused. A refused pair gets the `unproven` outcome, the
reason as its `summary`, and the reason under `refusal`, as a
`probe_refusal` refusal does. The rest go on to the existing cell exactly
as before. Let a `GitError` from the read propagate.

Reword the four docstrings that name `probe.probe_refusal` as the only
source of a refusal. They are `describe_criterion_probes`'s and
`describe_wrong_versions`'s (`saffron/phases/review.py:652-659`,
`:847-855`), `_apply_criterion_probes`'s
(`saffron/cell/session.py:2089-2098`), and the docstring of
`test_the_wrong_version_line_counts_refused_versions_apart_from_expressed_ones`
(`tests/test_review.py:2758-2763`).

## Out of scope

- **The rule and the read themselves**. `inert_edit`, `ProbePatterns` and
  `files_after` are the parents' work, and this spec forbids their files.
- **This repo's own patterns**. `.saffron/policy.yaml` is `protected`. Its
  `probes:` block landed by hand with `SA-0395`, and this spec reads it
  unchanged.
- **A lens's own adequacy probe**. `probe_findings` checks it through
  `check_probe` (`saffron/cell/session.py:1877`). An inert lens probe is
  the same defect there. A later spec can call `inert_edit` there.
- **An edit that changes more than its version names** (b-f06097), and an
  expression that gave up (b-12e717).
- **Why an empty read could not judge**. `files_after` returns an empty
  dict and drops `rebuild_tree`'s cause. Each pair then reaches the mutator
  as at base, and no REVIEW line says the inert rule judged nothing. A
  later spec can surface that cause.
- **Checkout filters**. The host reads blobs from the mirror. The critic
  cell applies the patch with `git apply --index`
  (`saffron/cell/session.py:1476-1478`), and `source_mutated` reads the
  working-tree file. A smudge or end-of-line filter can make the two texts
  differ. Where the `find` then fails to occur once in the host's text,
  `inert_edit` returns `None` and the pair reaches the mutator as at base.
  A filter that keeps that match but changes other lines is not judged
  here.
- **Which files the read names**. The claim says the call names the files
  the edits name. Whether a file only a `probe_refusal` refusal named joins
  that set is left open, and the witness holds no such pair.
- **The word "refusal" for a declined probe** (b-c86c4b). The key and the
  REVIEW line keep it, as `probe_refusal` does.
- **A `retired_first`**. The new refusal declines edits REVIEW names, never
  a spec, so no queued spec is refused by it.
- **Hand edits, made in this spec's own pull request**. `DESIGN.md` §2.1's
  table gains a row for REVIEW's inert-edit refusal, core logic over repo
  patterns. Two sentences join the `DESIGN.md` §5.4.1 paragraph on an edit
  a spec lists in prose. They follow the sentence on the gate-only cell.

  > Before any cell, the host declines an edit that keeps its whole `find`
  > and adds only lines the repo declares inert. It does so for a criterion
  > probe too, and records the edit `unproven` (`SA-0396`).

  `CONTEXT.md`'s Wrong version entry names the edits the host declines.
  One sentence follows its sentence on a declared test path.

  > It also declines one that keeps its whole `find` and adds only lines
  > the repo declares inert (`SA-0396`).

## Notes for the agent

**Both behaviours are new code**, so each criterion declares a witness and
no mutant, and `witness` will report `skip`. The refusal loop at
`saffron/cell/session.py:2109-2120` is extended rather than rewritten.

**At base each new witness fails in its body**. Criterion 1's witness sees
no read, and the inert edits reach the mutator. Criterion 2's witness sees
no `GitError` raised, since nothing calls `files_after` at base. Its first
two drives pass at base, and the third fails it.

**The session witnesses** follow
`test_a_wrong_version_its_witness_survives_is_rebutted_as_a_blocker` in
`tests/test_session.py`. Use `_ANCHORING_DIFF`, `_rebuttable`,
`_stub_probe_gates`, `_probe_turns`, `_probe_answer` and
`_wrong_version_answer`. Stub `files_after` on the `saffron.repos.mirror`
module with `monkeypatch.setattr`. `_drive` hands `run_one_cell` the mirror
`tmp_path / "m.git"`. `_spec`'s `base_sha` is forty `b`s. Pass
`stacked_on` forty `c`s in criterion 1, so `tree_base` differs from it. Declare
the patterns in a `probes:` block appended to `_PROBE_POLICY`. One pattern
matches a bare `def` line holding `{name}`, and one its `pass` body.

In criterion 1's witness the stub records its arguments. It returns text
for `src/x.py` and `src/z.py`, and `None` for `src/y.py`. Put the
criterion probe's inert edit on `src/z.py`. Append each inert edit after
the last line of its file, where `SA-0395`'s indentation guard still
refuses it. Give `src/x.py` a word that
occurs twice, and make the twice-found edit's `find` that word. Read the
survivor's line through a `read_at_head` stub. The survivor is applied
twice, once for its witness and once for the whole `tests` gate, so
`cell.mutated` holds it twice. Script the gate results in that order:
`pass`, `pass`, then `fail` for each later edit.

In criterion 2's witness drive each cell under its own `tmp_path`
subdirectory, as
`test_an_orphaned_stamp_from_a_raising_cell_reaches_the_origin_at_exit`
does. Keep each cell's stub in a list, so the raising drive's
`cell.mutated` can be read after `pytest.raises`. Reopen its `Ledger` to
read the `runs` and `tasks` rows.

**Every other drive in `tests/test_session.py`** declares no inert
pattern, so it makes no read and every pair reaches the mutator as at base.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. `_apply_criterion_probes`'s docstring is at ten
lines already, so reword its refusal clause inside the lines it holds.

**Size**. A prototype on top of both parents measured 115 changed tokens
outside `tests/` and 840 under it, about 239 changed lines.
