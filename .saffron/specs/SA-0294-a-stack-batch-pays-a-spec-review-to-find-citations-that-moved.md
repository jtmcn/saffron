---
id: SA-0294
title: A stack batch pays a spec review to find a queued spec's citations that no longer resolve
type: bug
priority: 2
estimated_lines: 200
estimate_measured: true
touches:
  - saffron/spec_citations.py
  - tests/test_spec_citations.py
  - saffron/batch.py
  - tests/test_batch.py
pending_symbols:
  - saffron/spec_citations.py::citation_defects
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
  - saffron/cli.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/spec_review.py
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_cli.py
  - tests/test_spec_loop_driver.py
  - tests/test_scheduler.py
budget_usd: 25
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      `citation_defects` returns one line for each `file:line` citation in a
      spec's text that does not resolve at the given commit, in text order.
      The witness drives a missing file, with a suffix and with none. It
      drives a single line past a file's end, at a bare filename, and a range
      past a file's end. A citation of a directory reports as a missing file.
      A citation of a file's last line resolves. It reads the committed blob,
      never the working tree. A host and port, a dotted
      module name and a clock time are not citations. A commit the repository
      lacks raises `GitError`.
    witness: tests/test_spec_citations.py::test_citation_defects_resolve_each_citation_at_the_given_commit
    wrong_versions:
      - The file's lines read from the working tree, so a file edited after its commit resolves against the edit.
      - The past-the-end check uses `>=`, so a citation of a file's last line reports.
      - The range's end dropped, so `2-999` resolves against a 20-line file.
      - A path needs a `/`, so `run.zzz:9` is never checked.
      - A path needs only a dot, so `importlib.util:3` reports as a missing file.
      - A commit the repository lacks reads as an empty tree, so every citation reports a missing file.
      - Every cited path read through `file_at` with `None` as a missing file, so a citation of the directory `pkg/sub` raises `UnreadablePath`.
  - claim: >-
      A bare `:n` or `:n-m` anchors to the last path named earlier in its own
      paragraph. That path is a plain backticked path or one carried by a
      `path:n` citation. A bare citation with no path earlier in its paragraph
      reports as unanchored, and a paragraph never inherits the path above it.
      An anchored bare citation meets the missing-file and past-the-end checks.
    witness: tests/test_spec_citations.py::test_citation_defects_anchor_a_bare_line_number_inside_its_own_paragraph
    wrong_versions:
      - A bare citation anchors only to a path citation, so one after a plain backticked path reads as unanchored.
      - A bare citation anchors only to a plain backticked path, so one after a path citation reads as unanchored.
      - The text read as one paragraph, so the last paragraph's bare range anchors to the path above it.
      - An unanchored bare citation dropped with no line.
      - A bare range skipped, so the unanchored range reports nothing.
  - claim: >-
      A citation whose range holds none of its sentence's other backticked
      strings reports where they sit instead. It reports only when the file
      holds one of them elsewhere. One of them inside the range clears the
      citation, on any line of the range. A sentence ends at a period before
      a digit too.
    witness: tests/test_spec_citations.py::test_citation_defects_report_quoted_text_that_sits_on_other_lines
    wrong_versions:
      - A report whenever the range lacks the text, so `gamma`, which sits nowhere, reports.
      - The whole file searched in place of the range, so no citation reports a move.
      - Only the range's first line read, so `beta` on line 25 is missed and `21-30` reports.
      - Every other string required inside the range, so `41-50` reports though `epsilon` sits there.
      - Only the sentence's first other string read, so `zeta` hides `omega` and `51-60` reports nothing.
      - A period before a digit not ending a sentence, so `iota` in the next sentence clears `61-70`.
  - claim: >-
      With `cite` given, `run_stack_batch` calls it before each call of
      `review`, and at no other point. That covers a spec of the order's
      first review, its review after a revision, and a follow-up's review. A
      spec offered again after a rate-limited cell is not checked again, and
      neither is a writer turn retried after its wait. It passes the
      candidate, its predecessor and the text `review` reads, which is `None`
      for the queued text. A spec whose `cite` returns defects is refused
      with no review session and no cell. The refusal emits one `refused`
      line naming the defect count, and it sets no task state. A spec of the
      order refused so is a miss, so each spec whose `depends_on` reaches it
      is refused, and the refusal counts toward no abort. A follow-up refused
      so is printed among `follow-ups unrun`. For a spec of the order, a
      raise from `cite` is a miss and is raised again.
    witness: tests/test_batch.py::test_a_stack_batch_refuses_a_spec_whose_citations_do_not_resolve_before_each_review
    wrong_versions:
      - The check runs only before a spec's first review, so a revision whose citations do not resolve reaches its cell.
      - The check runs after the review, so the refused spec still pays a review session.
      - The refusal records no miss, so a spec depending on the refused one runs.
      - The refused line prints a fixed count in place of the number of defects.
      - The refusal raises in place of returning `Refused`, so two refused specs stop the night at the breaker.
      - A raise from `cite` read as no defects, so the spec runs.
      - A raise from `cite` that records no miss, so a spec depending on it runs.
      - The queued text read in place of `None`, or `None` passed for the predecessor.
      - The miss recorded for a follow-up too, so `remaining.remove` raises on a spec the order never held.
      - Follow-ups skipped, so a follow-up whose citations do not resolve runs.
      - The check placed above the `reviewed` guard, so `TE-309` is checked again when it is offered after its rate-limited cell.
      - The check placed at the top of `while True:` before the `pending_revision.pop`, so `TE-310`'s writer retry is checked with its old text.
      - The refusal sets `SPEC_WITHHELD`, so a refused task leaves `QUEUED`.
      - A refused follow-up added to `follow_up_reviewed`, so `follow-ups unrun` no longer names it.
  - claim: >-
      `run_stack_batch` raises `ValueError` when `cite` is given and `review`
      is not, before it opens a batch row.
    witness: tests/test_batch.py::test_a_stack_batch_needs_review_whenever_cite_is_given
    wrong_versions:
      - No check, so `cite` is ignored and the night runs every spec unchecked.
      - The check placed after `create_batch`, so a batch row opens and never closes.
  - claim: >-
      With `cite` left out, a stack batch reviews, revises and runs as it did
      before.
    witness: tests/test_batch.py::test_a_revisable_blocker_is_revised_and_reviewed_again_for_at_most_three_rounds
    preserves: true
---

## Context

Backlog item **b-d31930**. It cites `DESIGN.md` §3.2, and the change sits in
the stack batch of §4.2.1. Every line number below was read at `c2f817d3`.

`SA-0273` was written against `bc879e2c`. Nine specs landed before it ran
and moved the files it cited. The batch's spec review found 15 citations
pointing at the wrong code and blocked the spec, at a cost of $2.32. The
spec loop's `driver.py cite` finds that shape in seconds. Nothing in the
batch runs it.

**The check exists only in the spec loop's driver.** `cmd_cite` reads a spec
as text and resolves each citation at `--base`
(`.claude/skills/run-saffron-spec-loop/driver.py:2489-2538`). Its helpers
start at `_Citation` (`.claude/skills/run-saffron-spec-loop/driver.py:2382-2391`).
They end at `_moved_lines` (`.claude/skills/run-saffron-spec-loop/driver.py:2474-2486`).
Three tests hold its behaviour. They are
`test_cite_resolves_a_specs_citations_at_the_base_commit`
(`tests/test_spec_loop_driver.py:2260`),
`test_cite_anchors_a_bare_line_number_inside_its_own_paragraph`
(`tests/test_spec_loop_driver.py:2315`) and
`test_cite_reports_a_citation_whose_quoted_text_sits_on_other_lines`
(`tests/test_spec_loop_driver.py:2358`). Each builds its repository with the
`empty_repo` fixture (`tests/test_spec_loop_driver.py:135-143`).

**A stack batch reviews each spec before its cell.** `run_stack_batch` takes
`review` as an injected callable that defaults to `None`
(`saffron/batch.py:441-443`). It refuses `follow_ups` without `review`
(`saffron/batch.py:477-478`). Inside `wrapped`, each pass of the review loop
reads the task's recorded spec text and hands it to `review` as `spec_text`
(`saffron/batch.py:608-610`). It then calls `review(candidate, pred, **kwargs)`
(`saffron/batch.py:614`). A revision loops back to that read
(`saffron/batch.py:604-606`). An escalation is a miss for a spec of the order
alone (`saffron/batch.py:674-677`). A `mint` that raises is a miss and is
raised again (`saffron/batch.py:584-588`). `_drive` counts a returned
`Refused` toward no abort (`saffron/batch.py:308-311`).

**Only the production `review` knows the commit it reads.** In
`saffron/cli.py`, `_stack_review` asks `_seed_branch` for a branch
(`saffron/cli.py:1029`). That is the predecessor's branch, else the stack
base's, else none (`saffron/cli.py:657-661`). It reads at that branch's
fetched head, or at `pinned.base_sha` when there is none
(`saffron/cli.py:1030-1033`). `SA-0295` builds the production `cite` there.

## Problem

A stack batch pays for a spec review before anything checks that the spec's
`file:line` citations still resolve. Port the driver's check into core, and
let `run_stack_batch` run it before each review.

**The module.** Add `saffron/spec_citations.py`, holding `citation_defects`.

```python
def citation_defects(mirror: Path, commit: str, text: str) -> list[str]: ...
```

It returns the lines `cmd_cite` prints for its defects, in the same order and
the same words. Each names `commit` as given where the driver names `--base`.
It drops the count line. `mirror` is any git repository holding `commit`,
bare or not. Read the tree and each blob at `commit` through
`saffron.repos.mirror` (`_git` at `saffron/repos/mirror.py:60`, `file_at` at
`saffron/repos/mirror.py:245`). `saffron/qualify.py:29` imports both. A
commit the repository lacks raises `GitError` from that module. The module
knows git and spec text, and nothing about any repo's language or tools.

**The batch.** Add a `cite` keyword to `run_stack_batch`, defaulting to
`None`, with a comment in the style of `review`'s. `None` checks nothing.
Raise `ValueError` when `cite` is given and `review` is not, beside the
`follow_ups` check. Call `cite` in `wrapped`, right before each `review`
call. That is inside the `pending is None` branch, after `spec_text` is read.
So it sits below the `reviewed` guard (`saffron/batch.py:603`) and below the
`pending_revision.pop` (`saffron/batch.py:606`). A reviewed spec offered again
and a writer retry each skip it.

The callable's shape is this.

```python
cite: Callable[[Candidate, Candidate | None, str | None], list[str]] | None = None
```

It takes the candidate, `pred`, and the `spec_text` read at that point. That
is `None` when the task holds no recorded text. It returns the defects, empty
when every citation resolves.

- **Defects.** Emit one line, `f"{spec_id:<10} refused  {n} citation(s) do not resolve"`,
  with `n` the number of defects. Return `Refused` whose reason is that
  line's text after `refused`. Call no `review`, record no spec review and
  open no attempt. Set no task state. For a spec of the order, record the miss and
  remove it from `remaining`, as the escalation does. Do neither for a
  follow-up. Leave a refused follow-up out of `follow_up_reviewed`, so it is
  printed in `follow-ups unrun` and passed to `finish` as unrun. An open pull
  request refusal does the same (`saffron/batch.py:596-602`).
- **A raise.** For a spec of the order, record the miss and remove the spec.
  Record neither for a follow-up. Then raise again, as a `mint` raise does.
  `_drive` counts it as an abort.

Name `cite` in `run_stack_batch`'s docstring within its existing ten lines.
It sits at the `prose` gate's `DOCSTRING_LIMIT` of 10 already
(`.saffron/gates/prose.py:67`), so fold it into the `review` sentence.

**What `SA-0295` passes.** For a candidate and its predecessor, it resolves
the commit as `_stack_review` does. Then it calls
`citation_defects(pinned.mirror, head, text)`. `text` is `spec_text` when
given. Otherwise it is `.saffron/specs/<candidate.path.name>` read at the
pinned `base_sha`, the export the review reads (ADR 7).

## Out of scope

- **The production callable and `saffron batch`'s wiring.** `SA-0295` builds
  it in `saffron/cli.py` and depends on this spec.
- **A plain batch, `saffron cell` and `saffron queue`.** None of them runs a
  spec review, and none calls this check.
- **The spec loop's driver.** `driver.py cite` keeps its own copy. Pointing
  it at the core module is a separate edit under `.claude/`.
- **A task state for this refusal.** The minted task stays `QUEUED`, as it does
  after the open pull request refusal at `saffron/batch.py:702-708`. A new
  state needs vocabulary in `CONTEXT.md`.
- **Printing each defect.** The refused line carries the count alone. The
  operator runs `driver.py cite` for the list.

## Notes for the agent

**The change is new code, so no criterion declares a mutant.** The module is
new, and the batch's call sits where no text yet exists. The `witness` gate
reports `skip` for each new criterion, and that is expected. The last
criterion is `preserves` and names a test at base.

**Criteria 1 to 3 port the driver's three tests.** Copy each one's fixture
and its spec text into `tests/test_spec_citations.py`. Give that file its own
`_git` helper and its own `empty_repo` fixture, copied from
`tests/test_spec_loop_driver.py:122-143`. Do not import from that test
module. Replace each `cmd_cite` call with `citation_defects(repo, base, text)`,
and assert the returned list where the driver test asserted printed lines.
Leave out the count line. In criterion 1, commit a directory `pkg/sub`
holding one file, and cite that directory at line 3 in the defective text.
Its expected line is the missing-file line, last in the list. Check
`path in names` against the `ls-tree -r --name-only` listing before any
`file_at` read, as the driver does. `file_at` raises `UnreadablePath` for a
directory (`saffron/repos/mirror.py:266-271`). Also add one call with a
commit of forty zeros and assert it raises `GitError`. Import `citation_defects` inside each
test body, never at module scope. A module-scope import of a name the change
adds turns the reverted run into a collection error, which `revert` reads as
`skip`.

**Criterion 4 drives one arrangement.** Build it on `StackDoubles`
(`tests/test_batch.py:5158`). Write a `cite` double that logs
`cite:<spec id>` into the doubles' shared `order` list. Each call pops that
spec's next scripted result, a defect list or an exception to raise. Record
each call's spec id, predecessor's id and text, and the candidate's
`task_id`. The order is ten specs at a budget of 1 each. Pass a budget of
40, `reserve_usd=6.0`, `writer_usd=2.0` and a `sleep` double that returns
at once. Set both session costs to 1.0, as `tests/test_batch.py:5752-5753` does.

1. A spec whose first check returns two defects.
2. A spec depending on the first.
3. A spec routed `revise` then `run`, whose first check is clean and whose
   second returns three defects.
4. A spec depending on the third.
5. A spec routed `revise` then `run`, clean both times. It becomes the first
   layer.
6. A spec whose check raises.
7. A spec depending on the sixth.
8. A clean spec, which runs on the fifth.
9. `TE-309`, a clean spec whose first cell returns `RATE_LIMITED` with a
   `resets_at`. It is offered again already reviewed, and runs on the eighth.
10. `TE-310`, a clean spec routed `revise` then `run`. Its first writer turn
    carries `resets_at`, so `_drive` waits and the retry reaches `revise`
    with no read. Its check runs on the queued text and on the revised text,
    and no third time.

Rows 9 and 10 need a runner and a writer `StackDoubles` lacks. Wrap
`doubles.runner` and `doubles.revise` in the test body. Each wrapper changes
one call and leaves the shared `order` log to the double it wraps. Then two
follow-ups, one clean and one whose check returns one defect.
Assert the stop is `DRAINED`. Assert the cite calls exactly, with the revised
and follow-up texts `StackDoubles` builds. Assert the whole shared `order`
list, and the runner calls. Assert the emitted lines that hold `refused` or
`raised`, in order. That list holds the three counts, the three `reaches`
lines and the one `raised` line. Assert the line naming the defective
follow-up alone under `follow-ups unrun` is among the emitted lines. Assert
the tasks of rows 1 and 3 and of that follow-up are still `QUEUED`. Read
them through `_task_state` (`tests/test_batch.py:3857`) by the `task_id`
the double recorded. Read each one's routes through `_task_routes`
(`tests/test_batch.py:3864`). Row 1 and that follow-up have `[]`, and row 3
has `["revise"]`. A refusal that records a spec review then fails.

A prototype measured both rows. Without them, the two placements in
criterion 4's `wrong_versions` pass this witness. Row 9 kills the check
above the `reviewed` guard. Row 10 kills the check before the
`pending_revision.pop`.

**Criterion 5** calls `run_stack_batch` with `cite` and no `review`. Assert
`ValueError` and that `ledger.latest_batch_id()` is still 0.

**At base each new witness fails in its body.** The batch witnesses pass
`cite`, which `run_stack_batch` does not take at base. That raises
`TypeError`. The module witnesses fail on their in-body import.

**The `dead` gate.** It scans no test (`.saffron/gates/dead.py:4-5`), and
only `SA-0295` calls `citation_defects` from `saffron/`. So
`pending_symbols` defers it. Its `pending` reads the files directly in
`specs_dir` (`.saffron/gates/dead.py:113-127`), so a retired spec defers
nothing. Once this spec is retired to `done/`, and until `SA-0295`
merges, `dead` reports `citation_defects` at base. Baseline subtraction absorbs that for every other task.

**Where the port and the driver part.** The driver's `_git` strips its output
(`.claude/skills/run-saffron-spec-loop/driver.py:111-115`). So `cmd_cite`
drops a blob's leading and trailing blank lines. Its line numbers and its
line count shift for such a file. `file_at` keeps the exact text, so the port numbers those lines
correctly. The driver's three tests build no such file. A symlink or a
submodule is listed by `ls-tree` and read through `file_at`, which can raise
for one. No criterion covers either.

**The `prose` gate** counts every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words.

**Size.** A prototype of the module and the batch edit measured 711 changed
tokens with `size_gate`'s counter, against the `bug` ceiling of 1300. Tests
are not counted. `estimated_lines` is that count over four, plus a margin
for the docstring update.
