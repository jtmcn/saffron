---
id: SA-0384
title: "A citation that no single construct it names holds passes `cite` at its base, so a parent's move stops the stack batch"
type: bug
priority: 2
estimated_lines: 57
estimate_measured: true
touches:
  - saffron/spec_citations.py
  - tests/test_spec_citations.py
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
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/agents/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/follow_up.py
  - saffron/finish.py
  - saffron/spec_review.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_follow_up.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      Called without `movable`, `citation_count_and_defects` refuses a
      citation that passes every check it made before, when the names of
      its clause open a construct at the commit and no single name holds it.
      A name holds it by the rule `citations_held_at` applies. The refusal
      reads `<path>:<range>: no single construct it names holds it (they sit
      at <path>:<spans>)`, with every span those names open. It sits in
      text order among the other defects. A citation `_construct_defect`
      refuses keeps that one defect alone.
      `citation_defects`, and `citation_count_and_defects` given
      `movable=False`, report what each reported before. The witness drives
      four refused shapes. A clause names one construct and a second name
      the lines quote, which opens none. A clause names a construct whose
      name the lines quote outside it. One name opens two constructs. One
      range holds two disjoint constructs. The second shape is driven
      through a bare citation as well. Four citations stay unflagged. One
      single construct holds the first, and the inner of two nested ones
      holds the second. The third names no construct, and the fourth spans
      its whole construct. A construct defect is reported once, in its old
      words.
    witness: tests/test_spec_citations.py::test_a_citation_no_single_construct_it_names_holds_is_refused_at_its_own_commit
    wrong_versions:
      - A range line that quotes a name opening a construct still passes the citation, so only the first shape is refused.
      - A name opening two constructs holds when one of them holds the range, so the third shape passes.
      - Of two holders the first one holds, so the fourth shape passes.
      - Two holders never hold, so the nested pair is refused too.
      - The new line is added beside a construct defect, so that citation is reported twice.
      - "`citation_defects` applies the new rule as well."
      - "`movable` defaults to false, so a call without it reports nothing new."
      - A bare citation is skipped by the new check.
      - The citation is refused only when no span holds the range, so the third and fourth shapes pass.
      - The line leaves out where the constructs sit.
  - claim: >-
      `driver.py cite` and `driver.py check` block a spec whose one
      citation names `_finish` beside the lines of another function. Those
      lines quote the `EXHAUSTED` the clause also names. `cite` prints the
      new line, then `1 citation(s) checked`, and exits 1. `check` prints
      the line after `cite: `, reports that 1 of 1 citations does not
      resolve, as a blocker, and exits 1. The driver itself is not edited.
    witness: tests/test_spec_loop_driver.py::test_cite_and_check_block_a_citation_no_single_construct_it_names_holds
    wrong_versions:
      - "`movable` defaults to false, so the driver's call reports nothing."
      - The new check skips a citation whose range a quoted name sits in, so this spec passes.
      - The line leaves out where the constructs sit.
---

## Context

Backlog item **b-b664d1**, filed 2026-11-02. It cites `DESIGN.md` §4.2.1.
Its three Record lines are this spec's evidence. Every line number below was
read at `cb4ad504`.

**How a citation is judged now.** `citation_count_and_defects` reads each
citation's clause names (`saffron/spec_citations.py:337-418`). It passes a
citation by `_construct_defect`'s rule (`saffron/spec_citations.py:266-304`).
`_construct_defect` passes one whose names open no construct
(`_construct_defect`, `saffron/spec_citations.py:277-278`). It also
passes one whose range sits inside a construct, or holds one whole
(`_construct_defect`, `saffron/spec_citations.py:279-280`). It also passes one
whose range has a line outside every construct quoting any of its names
(`_construct_defect`, `saffron/spec_citations.py:281-291`).
`citation_defects` returns its defects half
(`citation_defects`, `saffron/spec_citations.py:421-424`).

**How a moved citation is followed.** `citations_held_at` gives a citation a
name only when that name opens exactly one construct holding the range. Of
several such names, the inner one of a nested pair holds it
(`citations_held_at`, `saffron/spec_citations.py:476-486`).
`rewrite_moved_citations` moves a defect only through that held name
(`rewrite_moved_citations`, `saffron/spec_citations.py:505`).

**Who calls what.** The stack batch's adapter holds names at the spec's own
commit and judges at the layer's head (`_stack_cite`,
`saffron/cli.py:1494-1497`). The batch refuses the spec when a defect is
left after the move (`run_stack_batch`, `saffron/batch.py:736-747`). The
finish's `cite` adapter calls `citation_defects` on each follow-up draft
(`saffron/cli.py:1939-1945`). The loop driver's `_cite_defects` calls
`citation_count_and_defects` with no keyword
(`_cite_defects`, `.claude/skills/run-saffron-spec-loop/driver.py:3100-3111`).
`_cite_blocker` reads it for `cmd_check`
(`.claude/skills/run-saffron-spec-loop/driver.py:2963`). So does `cmd_cite`
(`:3051`).

So a citation `citation_count_and_defects` passes at its base can still hold
no name. A later move of its lines then leaves it a defect the batch cannot
move.

## Problem

Three stack batches refused a spec for one such citation. Each spec's
citations passed `cite` at its base.

| batch | spec | file and lines then | why no name held them |
| --- | --- | --- | --- |
| 63 | `SA-0331` | `saffron/phases/package.py`, 633 to 634 | It named `_finish` and `EXHAUSTED`. The lines held `_state`, and line 634 quoted `EXHAUSTED`. |
| 68 | `SA-0337` | `saffron/ledger.py`, 1807 to 1825 | It named `stack_finish`, a fact kind. A reader method of that name opened two lines past the range, which quoted the kind. |
| 84 | `SA-0381` | `saffron/cli.py`, 1878 to 1913 | `write` opened two constructs in that file, and the lines held one. |

A prototype of this change refused each of the three at the commit that
last edited its spec text. `SA-0331`'s text was read at `f2a76a07^`,
`SA-0337`'s at `b362fe8b` and `SA-0381`'s at `b87c79b8`.
`citation_defects` reported none of them there.

**What it costs a writer.** The prototype read the 55 specs from `SA-0260`
on whose commit declared citation patterns. It read each at the commit that
last edited it. It refused 108 of their 2165 citations, in 43 of the 55
specs. 88 passed only because a range line quoted one of their names. 12
named a construct that opens twice, and 8 held two disjoint constructs. Each is fixed by naming the construct that holds the lines in the
same clause, or by giving the citation a clause of its own. The queued
`SA-0381` holds four.

## Out of scope

- **The item's second sentence.** A bare citation into a file a parent
  layer changes still goes unchecked. Following it needs the layer's diff at
  the batch, in `saffron/cli.py` and `saffron/batch.py`. It stays on
  b-b664d1.
- **The batch and the finish.** Both read `citation_defects`, which keeps
  its rule. Their behaviour does not change.
- **The driver.** Its `cite` and `check` take the new rule through the core
  call they already make. A follow-up can correct `cmd_cite`'s docstring,
  which says it holds the batch's own rule. It can also add the rule to
  `.claude/skills/create-saffron-spec/references/preflight.md` check 5.
- **`citations_held_at`'s rule.** It does not change. The new check reuses
  it, so the two agree.
- **A queued spec.** Nothing in load, the queue scan, intake or a batch
  applies the new rule. So no queued spec is refused, and `retired_first`
  stays empty. The four in `SA-0381` block only a later `driver.py check`
  of that spec.

## Notes for the agent

1. **`saffron/spec_citations.py`.** Give `citation_count_and_defects` a
   keyword-only `movable` that defaults to true. With it, a citation that
   passes `_construct_defect` meets one more check. Move the holder rule
   out of `citations_held_at`'s loop into a helper both call, so the two
   cannot drift. The new defect carries the citation's `path` and `offset`,
   with `replace` and `spans` both `None`. `rewrite_moved_citations` then
   leaves it as it stands. `citation_defects` passes `movable=False`.
   Keep `citation_count_and_defects`'s docstring within ten lines.
2. **`tests/test_spec_citations.py`.** The first witness builds one file on
   `cite_repo` and one text of ten one-sentence paragraphs. It compares the
   whole defect list by `==` and the count by `==`. The prototype's file
   held, in order, `package` with a nested `_state` returning `"EXHAUSTED"`
   and `_finish`. Then came `record_stack_finish` quoting
   `"stack_finish"`, `stack_finish`, two `def twin()`, and `alpha` with
   `beta` on adjacent lines. A module-level `EXHAUSTED` came last.
3. **`tests/test_spec_loop_driver.py`.** The second witness reuses
   `_cite_tree` and commits a two-function file with a `def` pattern in
   `.saffron/policy.yaml`. It compares `cmd_cite`'s whole output by `==`, as
   `test_cite_and_check_report_what_the_batchs_citation_check_reports` does.

**Edit or new.** Both criteria test new behaviour of an existing function.
No mutant is declared, so `witness` reports `skip` for each. The wrong
versions name what each witness must still kill.

**Each absence has its positive case.** The first witness reads one text
three ways. The default call reports the new lines. `citation_defects` and
`movable=False` each report the old list. The unflagged citations sit in
the same text as the refused ones.

**At base both witnesses fail in their bodies.** Import nothing the change
adds at module scope. `movable=False` raises `TypeError` at base, inside the
test.

**What stays green.** Every other test in both files passed on the
prototype, with the citation tests of `tests/test_cli.py` and
`tests/test_batch.py`. The driver test comparing `cmd_cite` with
`citation_defects` has no unheld citation in its text.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words.

**No `depends_on`.** No queued spec touches these three files.

**Size.** The prototype measured 229 changed tokens with `size_gate`,
against the `bug` ceiling of 1300. It measured 430 more under the test paths.
