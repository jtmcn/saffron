---
id: SA-0321
title: A stack batch refuses a spec for citations that moved to one place, though the check already names that place
type: feature
priority: 2
estimated_lines: 210
touches:
  - saffron/spec_citations.py
  - tests/test_spec_citations.py
  - saffron/batch.py
  - tests/test_batch.py
  - saffron/cli.py
  - tests/test_cli.py
  - tests/test_spec_loop_driver.py
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
  - saffron/ledger.py
  - saffron/task.py
  - saffron/finish.py
  - saffron/regate.py
  - saffron/scheduler.py
  - saffron/spec_review.py
  - saffron/repos/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 85
max_attempts: 3
max_turns: 240
risk: standard
acceptance:
  - claim: >-
      `rewrite_moved_citations(text, defects, held)` rewrites each defect
      whose citation's offset `held` maps to a name, when that name opens
      exactly one span in the defect. That citation's range in `text`
      becomes the span, written `S` for one line and `S-E` otherwise. Its path, or its bare
      form, and every other character stay as written. It returns the new
      text, one rewrite per such defect in text order, and the defects
      left. Each rewrite names the path, the old range and the new range.
      The witness drives a path citation and a bare one, each as a single
      line and as a range. It drives a new span of one line and one of
      several. It drives two rewrites of different lengths in one sentence,
      and a paragraph wrapped over two lines. It drives one citation text
      written twice, judged right once and moved once. Checked again at the
      same commit, the new text reports no defect.
    witness: tests/test_spec_citations.py::test_a_citation_whose_construct_sits_at_one_span_is_rewritten_to_that_span
    wrong_versions:
      - Every occurrence of a citation's text replaced, so the right `export_saffron_dir` citation of line 21 becomes `4-6` too.
      - The first occurrence of a citation's text replaced, so the right line 21 changes and the moved one stays.
      - Offsets read before earlier rewrites applied, so the `tiny` rewrite after the `4-6` one lands two characters early.
      - The rewrite applied to the paragraph as the checker joins it, so the wrapped paragraph loses its line break and indent.
      - A one-line span written `S-S`, so the `tiny` citations read `2-2`.
      - A bare citation given its anchored path, so the bare `30-32` becomes a path citation.
      - Rewrites returned in defect-kind order or reversed, not text order.
      - A rewritten defect also returned among the defects left.
  - claim: >-
      `rewrite_moved_citations` leaves every other defect, in text order,
      and leaves its citation's text as written. The witness drives each
      kind the check reports. The held map takes every offset whose clause
      names one, mapped to that name. That is a bare citation with no path, a start before line 1, an
      end before its start, a missing file and a range past a file's end.
      It also drives a held name that opens two spans. One rewritable
      citation among them is rewritten and is not left.
    witness: tests/test_spec_citations.py::test_a_citation_defect_with_no_single_span_is_left_and_its_text_kept
    wrong_versions:
      - A held name with two spans rewritten to its first, so the `twin` citation of line 3 becomes `1-2`.
      - A defect with no span dropped from the defects left, so one comes back where six are left.
      - The defects left returned in kind order, so the unanchored bare citation is not first.
      - A past-the-end citation rewritten to the file's last line.
  - claim: >-
      `citations_held_at(mirror, commit, text)` maps the offset of each
      citation held at `commit` to the name that held it. A name holds a
      citation when it opens exactly one construct there, and the range
      sits inside it or holds it whole. A citation that passes only by
      quoting a name on a line outside every construct is not held. Neither
      is one whose names open no construct, or one with no path, a missing
      file, a reversed range or a range past the file's end. None of those
      raises. So a moved definition citation is rewritten, and a moved
      use-site citation of the same name is left as a defect. A clause
      naming two names is held by one and rewritten only onto that name's
      construct. When two names hold it and one construct sits inside the
      other, the inner one's name holds it, in either clause order. Two
      disjoint constructs both held whole hold nothing, and neither do two
      of equal length. A name defined twice at `commit` holds nothing. The
      witness drives every member named here.
    witness: tests/test_spec_citations.py::test_a_use_site_citation_is_left_while_its_definition_citation_is_rewritten
    wrong_versions:
      - The held map ignored, so the use-site citation of lines 9-10 is rewritten to the definition at `4-6`.
      - Every citation that passes at the own commit counted as held, so the use-site citation is rewritten too.
      - The held map read at the later commit, where no citation holds its construct, so nothing is rewritten.
      - Only a range inside a construct counted, so the range 1-4 that holds it whole is left.
      - The file read without checking the tree first, so `mod/new.py`, absent at the own commit, raises.
      - A citation whose names open no construct counted as held, so `digest` at line 2 is in the map.
      - A rewrite onto the union of the clause's spans, so the `alpha` and `beta` citation is moved onto `beta` at `4-5`.
      - A name that opens two constructs at the own commit counted as held, so the `twin` citation is moved onto the second at `4-5`.
      - The first holding name in clause order kept, so the `outer` and `inner` citation becomes `4-7` and not `5-6`.
      - The last holding name in clause order kept, so the `inner` and `outer` citation becomes `4-7` and not `5-6`.
      - The shorter construct's name kept whether or not it sits inside the other, so the disjoint `two` and `one` citation moves onto `one` at `6-7`.
      - A tie broken by clause order, so the `left` and `right` citation moves onto `left` at `4-5`.
  - claim: >-
      In a stack batch, a spec whose `cite` returns defects that
      `rewrite_moved_citations` rewrites, and none it leaves, is not
      refused. Before its review, the batch records the rewritten text as
      the task's spec text. Its origin is `revision`, and its path is the
      candidate's file name under `.saffron/specs/`, as a revision's is. It
      hands that review the rewritten text, and hands a `revise` route the
      same text. It emits one line per rewrite
      in text order,
      `f"{spec_id:<10} moved  {path}:{old} -> {path}:{new}"`. A bare
      citation's line names its anchored path. The witness drives a spec
      of the order with no recorded text, whose text `cite` read from the
      queued file. A spec whose `cite` returns no defect records no text.
    witness: tests/test_batch.py::test_a_stack_batch_records_a_spec_text_with_its_moved_citations_rewritten_before_its_review
    wrong_versions:
      - The batch rewrites the `spec_text` it read from the ledger, so a first text with no row is never rewritten.
      - The rewritten text recorded after the review returns, so the ledger holds the old text while the review runs.
      - The review handed the old text, or no text, while the ledger holds the new one.
      - The writer handed the old `spec_text`, or `None`, on a `revise` route, so it revises the queued citations again.
      - One `moved` line for all rewrites, or none.
      - A spec with no defect records its text anyway.
      - The rewritten text recorded with origin `follow_up` or at a path other than the candidate's own, so `run_task` refuses it.
  - claim: >-
      A spec of the order whose `cite` returns any defect
      `rewrite_moved_citations` leaves is refused before its review. That
      covers a defect of another kind, and a one-span defect whose offset
      `cite` did not return as held. The refused line counts the defects
      left, not every defect. It records no text and emits no `moved` line,
      even when other defects were rewritable. It is still a miss, so a
      spec depending on it is refused.
    witness: tests/test_batch.py::test_a_stack_batch_refuses_a_spec_with_a_citation_left_after_rewriting_and_records_no_text
    wrong_versions:
      - The refused line counts every defect, so it reads `3 citation(s)` where one is left.
      - The batch rewrites a one-span defect `cite` did not return as held, so the use-site spec runs.
      - The rewritable defects recorded before the refusal, so the refused task holds a spec text.
      - The `moved` lines emitted before the refusal.
      - The refusal records no miss, so the dependent spec runs.
  - claim: >-
      `_stack_cite`'s callable returns the text it checked, the defects
      `citation_defects` returned for it unchanged, and the held map.
      Handed `None`, the text is the queued file at `base_sha`. Its held map
      comes from `citations_held_at` at the commit that last changed that
      file in `base_sha`'s history. Handed a text, it returns that text and
      an empty held map. The commit it checks at is resolved as before.
    witness: tests/test_cli.py::test_a_stack_batchs_citation_check_returns_the_text_it_checked
    wrong_versions:
      - The callable returns the text it was handed, so `None` comes back for a spec with no recorded text.
      - The held map read at `base_sha`, which here is a later commit that leaves the spec file alone.
      - The held map read at the head the check resolved.
      - A held map returned for a recorded text, so a revision's own slip is rewritten.
      - The defects converted to strings, so the batch has no span to rewrite.
  - claim: >-
      Each construct defect `citation_defects` returns reads, through
      `str`, as the exact line it read before this change, in the same
      order. Criterion 2's witness holds the line of every other kind.
    witness: tests/test_spec_citations.py::test_citation_defects_judge_a_citation_by_the_construct_its_clause_names
    preserves: true
  - claim: >-
      `driver.py cite` and `check` print the same lines for the same spec
      and ref as before this change.
    witness: tests/test_spec_loop_driver.py::test_cite_and_check_report_what_the_batchs_citation_check_reports
    preserves: true
  - claim: >-
      `cite` still runs before each review and at no other point. A spec
      whose defects carry no single span is still refused with their count,
      and a raise from `cite` is still a miss raised again.
    witness: tests/test_batch.py::test_a_stack_batch_refuses_a_spec_whose_citations_do_not_resolve_before_each_review
    preserves: true
---

## Context

Backlog item **b-009d51**. It cites `DESIGN.md` §3.4. The check runs in the
stack batch of §4.2.1, under ADR 7, which this spec's own pull request
amends. Every line number below was read at `068862d9`.

**The check already names where a construct moved.** `_construct_defect`
builds its line from every span the citation's names open
(`saffron/spec_citations.py:208-239`). It passes a range inside a span or
holding one whole first. Only then does it pass a range that quotes a name
on a line outside every span. `citation_count_and_defects` returns each
defect as a `str` (`saffron/spec_citations.py:253-308`), and
`citation_defects` returns its second half
(`saffron/spec_citations.py:311-314`). No caller can read a span back
except by parsing that string.

**The batch refuses on any defect.** `run_stack_batch` reads the task's
latest recorded text, or `None` when there is none
(`saffron/batch.py:679-680`). It calls `cite` with that value. Any non-empty
return emits `refused  N citation(s) do not resolve`, records a miss for a
spec of the order, and returns `Refused` (`saffron/batch.py:681-699`). The
review then reads `spec_text` when it is not `None`
(`saffron/batch.py:700`). A revision's text is recorded with origin
`revision` at `.saffron/specs/<file>` (`saffron/batch.py:861-867`).

**The adapter reads the queued file itself.** `_stack_cite`'s callable
reads `_queued_spec_text` when handed `None`, and returns only
`citation_defects(pinned.mirror, head, spec_text)`
(`saffron/cli.py:1273-1300`). The queued file is read at `base_sha`
(`saffron/cli.py:749-756`). The batch never sees the queued text, so it
cannot rewrite it without the adapter handing it back.

**The cell reads the recorded text.** Given a task id, `run_task` rebinds
the spec to its latest recorded text (`saffron/task.py:697-702`). A
`revision` row passes when an earlier row has its path, or when the spec
file at `base_sha` there carries the same id (`saffron/task.py:630-640`).

**Run 48 measured both shapes.** `SA-0315`'s text at `c6e12a59`, checked
at `origin/saffron/SA-0313` (`a0ec477e`), reports four defects. `SA-0316`'s
text at `66d30a90`, checked at `origin/saffron/SA-0315` (`78f1453b`),
reports seven. Each text reports none at its own commit. All seven of
`SA-0316`'s name one span, and each held its construct at `66d30a90`. The
hand refresh in `bc39d878` moved each onto that span. Of `SA-0315`'s four,
two cite a call of a helper and passed at `c6e12a59` only by quoting its
name. A plain one-span rewrite would move each onto the helper's `def`,
where the hand refresh in `5c02dee1` kept the call. The other two held a
construct there. One is «saffron/cli.py» 512-538, held by
`_pushed_landed`. The other names a test and the `fake_ready_task` nested
in it, and the shorter construct holds it. These counts come from running
today's checker and a prototype of the held map at those commits.

**It is not only a parent's moves.** The own commit is on `main`. So the
rewrite also corrects drift that later merges to `main` made before
`base_sha`, for a spec with no parent at all.

## Problem

Rewrite a citation when one name in its clause held it at the spec's own
commit, and that name opens exactly one construct now. Move it onto that
construct. Refuse only for the defects left.

**The spec's own commit.** It is the commit that last changed the queued
spec file in `base_sha`'s history. The spec was written and reviewed there,
so its citations were read against that tree. The batch reads it from the
mirror it already holds, with `git log -1 --format=%H <base_sha> -- <path>`.
Measured at the merge `ddf48856`, that returns `c6e12a59` for
`SA-0315`'s file. A recorded text, a revision's or a follow-up's, has no such commit. It is
never rewritten.

**A structured defect.** Each defect carries the line it prints today
unchanged and its citation's place in the text. A construct defect also
carries the spans each clause name opens. Its `str` is that line. A
defect of any other kind carries no span.

**The held map.** `citations_held_at(mirror, commit, text)` in
`saffron/spec_citations.py` reads the same citations and the same policy
patterns at `commit`. A clause name holds a citation when it opens
exactly one construct there, with the range inside it or holding it
whole. When two names hold one and one construct sits inside the other,
the inner one's name holds it. Two disjoint constructs, or two of equal
length, hold nothing, and the citation stays a defect. It reads only files
the tree at `commit` lists, and skips a range that does not resolve there.
A clause that names nothing is never in the map.

**The pure rewrite.** `rewrite_moved_citations(text, defects, held)` takes
the text the defects were found in. It returns the new text, the rewrites
in text order and the defects left. It reads no git and no file.

**The batch.** `cite` returns the text it checked, its defects and the
held map. The batch passes all three to `rewrite_moved_citations`. Any
defect left refuses the spec as today, counting only those left.
Otherwise, when a rewrite happened, it records the new text and emits one
`moved` line per rewrite before the review. Then it hands the review that
text. With no defect, nothing changes. After that review routes `run`,
`_revised_spec_refusal` re-runs gate 0's open-pull-request refusal on any
spec of the order whose latest row is a `revision`
(`saffron/batch.py:435-437`). A rewritten spec has such a row. The
rewrite leaves `touches` as it was, so the re-run asks gate 0's own
question again, and that is harmless.

**The adapter.** Update `cite`'s type and the comment above it
(`saffron/batch.py:490-492`), and `_stack_cite`'s docstring.

**The driver.** `_cite_defects` in `driver.py` already maps each defect
through `str`, since this spec's pull request changed it by hand. A cell
cannot write under `.claude/`. So `driver.py cite` and `check` print the
same lines once defects are structured.

## Out of scope

- **The committed spec file.** The batch never writes `.saffron/specs/`.
  `commit_finish` already writes each layer's latest recorded text into the
  finishing layer (`saffron/finish.py:161-163`). A rewritten text reaches
  it there as a revision does. This spec does not change that.
- **`regate`.** It declines a task holding a recorded text
  (`saffron/regate.py:55-58`). A task whose citations were rewritten is
  declined the same way.
- **`driver.py check`.** It still blocks on every defect before a batch.
  Telling a rewritable one apart there is a separate change.
- **A new origin.** `SPEC_TEXT_ORIGINS` stays as it is
  (`saffron/ledger.py:80-82`). The rewritten text is a `revision` row. The
  comment above it lists what writes each origin and does not name the
  rewrite. That stale prose stays, since `saffron/ledger.py` is forbidden.

## Notes for the agent

**The change is new code, so no criterion declares a mutant.** Each new
witness tests code that does not exist at base. The `witness` gate reports
`skip` for each, and that is expected. The last three criteria are
`preserves` and name tests at base.

**What the cut leaves.** A citation of code that was not in the tree at the
spec's own commit holds nothing there. A child citing its parent's new
code is then refused as today. So is a citation already stale at its own
commit. A spec last edited for prose only takes that edit as its own
commit, and a citation stale there is refused too. In run 48 the
prototype rewrites all seven of `SA-0316`'s defects, each to the span the
hand refresh chose. It rewrites two of `SA-0315`'s four, «tests/test_cli.py»
2599-2603 to 3735-3737 among them, as the hand refresh did. `SA-0315` stays
refused on its two use-site citations.

**`max_turns` is 240.** `history` names `SA-0312`'s 221 turns as the peak.
That row was cut off at its own ceiling, so 221 is a floor and not a
measured need. The extra turns cover that. The budget stays at 85.

**A suggested shape, not a rule.** A frozen dataclass `CitationDefect`
holds the printed line, the path and the old range as written. It also
holds that range's offset in the text, and a tuple of spans. Its
`__str__` returns the line. Its spans can be a mapping from each clause
name to that name's spans. `citation_count_and_defects` and
`citation_defects` return it, and `cli.py` keeps calling
`citation_defects`. A `NamedTuple` can carry `cite`'s three values. Choose
other names if they read better, and keep the two function names.

**The `dead` gate.** It scans `saffron/` and not `tests/`
(`.saffron/gates/dead.py:4-5`). A function only tests or the driver call
is dead. So keep `citation_defects` as the adapter's call, and keep
`citation_count_and_defects` as its source. A string-returning wrapper
beside a new structured function leaves one of them dead.

**Finding a citation's place.** Paragraphs are split on blank lines and
each is joined with single spaces before sentences are read
(`saffron/spec_citations.py:71-88`, `:157-162`). A citation token holds no
whitespace, and joining never adds or removes a backtick. So the k-th
backtick pair in a paragraph's original text is the k-th in its joined
form. Record each citation's offset in the original text. The offsets in
`citations_held_at`'s map are read over the same text, so they match.

**Existing tests.** Tests that compare a defect list with strings compare
`[str(d) for d in ...]` instead. Their expected strings stay byte for byte.
The batch test behind criterion 9 has a `cite` double returning lists. Make
it return its text, defects that carry no span, and an empty held map. Keep
every assertion it makes.

**Import new names inside each test body.** A module-scope import of
`rewrite_moved_citations` makes the reverted run a collection error, which
`revert` reads as `skip`.

**The fixtures.** In each block below, write «x» as x between backticks. The
spec spells them so, or its own citation check reads the fixture paths.

**Criteria 1 and 2** use the `cite_repo` fixture in
`tests/test_spec_citations.py`, with one more file committed on top.
`mod/tiny.py` holds four lines: `x = 1`, `def tiny(): pass`, `y = 2` and
`z = 3`. Criterion 2 also commits `mod/twice.py`, five lines:
`def twin():`, `    return 1`, a blank line, `def twin():` and
`    return 2`. Each witness's held map takes every defect's offset whose
clause names one, mapped to that name.

Criterion 1's text, with its seven defects as the checker reports them now:

```text
«_review_one_layer» reads
  those fields («mod/lib.py:4-15»).

«_print_summary» checks «IF NOT EXISTS» («mod/lib.py:44»).

«tiny» does nothing («mod/tiny.py:3-4»).

The module «mod/lib.py» holds «Ledger» at «:30-32».

The module «mod/tiny.py» holds «tiny» at «:4».

«export_saffron_dir» writes it («mod/lib.py:21»).

«_diff» returns it («mod/lib.py:21»), and «tiny» does nothing («mod/tiny.py:3»).
```

```text
mod/lib.py:4-15: the construct it names sits at mod/lib.py:9-16
mod/lib.py:44: the construct it names sits at mod/lib.py:38-39
mod/tiny.py:3-4: the construct it names sits at mod/tiny.py:2
mod/lib.py:30-32: the construct it names sits at mod/lib.py:26-28
mod/tiny.py:4: the construct it names sits at mod/tiny.py:2
mod/lib.py:21: the construct it names sits at mod/lib.py:4-6
mod/tiny.py:3: the construct it names sits at mod/tiny.py:2
```

The new text equals the old with exactly seven ranges changed. `4-15`
becomes `9-16`, `44` becomes `38-39`, and `3-4` becomes `2`. The bare
`30-32` becomes `26-28`, and the bare `4` becomes `2`. The second `21`
becomes `4-6`, and the last `3` becomes `2`. Assert the
whole new text with `==`, and assert no defect is left. Checked again, the
new text reports no defect at all. That was measured at base with today's
checker.

Criterion 2's text, with one rewritable citation in the middle:

```text
The «_diff» helper sits at «:4-6».

See «mod/lib.py:0» for it.

See «mod/lib.py:6-2» for it.

«tiny» does nothing («mod/tiny.py:3»).

See «gone.py:1» for it.

See «pkg/other.py:9» for it.

«twin» returns its value («mod/twice.py:3»).
```

Its six defects left, in this order, read through `str`:

```text
:4-6: no path named earlier in its paragraph
mod/lib.py:0: starts before line 1
mod/lib.py:6-2: ends before it starts
gone.py:1: no such file at <commit>
pkg/other.py:9: pkg/other.py has 3 lines at <commit>
mod/twice.py:3: the construct it names sits at mod/twice.py:1-2, 4-5
```

The new text differs from the old only where the `tiny` citation's `3`
becomes `2`.

**Criterion 3** is shaped like `SA-0315`'s `_mirror_path` citation. Build
a repository from `empty_repo` with the `cite_repo` policy and two
commits. At the first, `mod/cli.py` holds these ten lines.

```python
CLI = [
    "def _mirror_path(repo, home):",
    "    digest = repo",
    "    return home / digest",
    "",
    "",
    "def package(repo, home):",
    "    x = 1",
    "    y = 2",
    "    mirror_path = _mirror_path(repo, home)",
    "    return mirror_path",
]
```

The first commit also holds `mod/pair.py`, defining `alpha` at lines 1-2
and `beta` at 5-6. It holds `mod/twin.py`, defining `twin` at 1-2 and
again at 5-6. Each body is one `return` line, with two blank lines
between. The second commit puts `import os` and two blank lines above
`mod/cli.py`'s lines. It cuts `mod/pair.py` to those three lines and
`beta`, and `mod/twin.py` to those three lines and the second `twin`. It
adds `mod/new.py`, defining `fresh` at lines 1-2. Both commits hold
`mod/nest.py`, four lines: `def outer():`, `    def inner():`,
`        return 1` and `    return inner`. The second commit puts the same
three lines above them. Both commits hold `mod/both.py`, defining `one` at
lines 1-2 and `two` at 3-5. The second commit puts those three lines and
two more blank lines above it. Both commits hold `mod/even.py`, defining
`left` at 1-2 and `right` at 3-4. The second commit puts the same three
lines above it. The text is fourteen paragraphs.

```text
«_mirror_path» and the blank line after it sit at «mod/cli.py:1-4».

«_mirror_path» returns its path at «mod/cli.py:3».

It builds «mirror_path» with «_mirror_path(repo, home)» and hands it over («mod/cli.py:9-10»).

«_mirror_path» is called at «mod/cli.py:12».

«fresh» returns one at «mod/new.py:1-2».

«_mirror_path» sits at «:1-3».

«_mirror_path» sits at «mod/cli.py:3-1».

«digest» is read at «mod/cli.py:2».

«alpha» and «beta» both matter («mod/pair.py:2»).

«twin» returns one («mod/twin.py:2»).

«outer» returns «inner» («mod/nest.py:2-3»).

«inner» is returned by «outer» («mod/nest.py:2-3»).

«two» and «one» sit together («mod/both.py:1-5»).

«left» and «right» sit together («mod/even.py:1-4»).
```

Measured on a prototype at base, the held map at the first commit holds
five citations. The first and second are held by `_mirror_path`, the
ninth by `alpha`, and the eleventh and twelfth by `inner`. Nothing raises.
Assert that map exactly, by offset and name. Pass the second commit's
defects and that map to the rewrite. `1-4` and `3` both become `4-6`, and
both `2-3` ranges become `5-6`. No other range changes. The defects left,
in order, read as follows.

```text
mod/cli.py:9-10: the construct it names sits at mod/cli.py:4-6
:1-3: no path named earlier in its paragraph
mod/cli.py:3-1: ends before it starts
mod/pair.py:2: the construct it names sits at mod/pair.py:4-5
mod/twin.py:2: the construct it names sits at mod/twin.py:4-5
mod/both.py:1-5: the construct it names sits at mod/both.py:6-7, 8-10
mod/even.py:1-4: the construct it names sits at mod/even.py:4-5, 6-7
```

The prototype killed each of criterion 3's wrong versions on this text.
The exact held map kills every one, and the new text kills all but the
`digest` one.

**Criteria 4 and 5** extend `StackDoubles` in `tests/test_batch.py` with a
`cite` double. It returns a text, defects built in the test, and a held
map. Find each offset with `str.index` on that text. Wrap the review
double to keep each `spec_text` it was handed and the ledger's latest text
at that moment. Build each text as `_spec_text(...)` with a line of
citations appended, so it parses. Criterion 4 drives two specs of the
order. The first has no recorded text, and its `cite` returns a queued
text with two held one-span defects, one of them bare. The second returns
no defect. The third returns one held one-span defect, and its review
routes `revise`, then `run`. Its revise double keeps the `spec_text` it was
handed, which must be the rewritten text. Its re-check returns that text
and no defect. Criterion 5 drives three specs of the order. The first returns
two held one-span defects and one with no span. The second returns one
held one-span defect and one one-span defect not held. The third declares
`depends_on` on the first. A follow-up takes the same branch. Criterion 9
drives a follow-up refused on a defect with no span. No witness drives one
refused beside a rewritable defect.

**Criterion 6** extends the `_spec_session_rig` arrangement of
`test_a_stack_batchs_citation_check_resolves_at_the_commit_its_review_reads`
in `tests/test_cli.py`. From the rig's base commit, commit one more change
that leaves the spec file alone, and pin `base_sha` there. Patch
`cli.citation_defects` to return a sentinel list, and patch
`cli.citations_held_at` to record its commit and return a sentinel map.
Handed `None`, the callable must ask for the rig's original base commit.
Handed a text, it must not call it and must return an empty held map.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.
