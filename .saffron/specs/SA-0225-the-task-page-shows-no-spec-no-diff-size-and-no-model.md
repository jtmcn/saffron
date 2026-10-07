---
id: SA-0225
title: The task page shows no spec, no diff size and no model
type: feature
priority: 3
depends_on: []
estimated_lines: 367
estimate_measured: true
touches:
  - saffron/view/graph.py
  - saffron/view/server.py
  - saffron/report/pr_body.py
  - tests/test_view_graph.py
  - tests/test_view_server.py
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
  - records/**
  - hooks/**
  - images/**
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/projection.py
  - saffron/intake.py
  - saffron/repos/**
  - saffron/record/**
  - saffron/gates/**
  - tests/test_report.py
  - tests/test_mirror.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 35
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      `build` states `factory:model` on an attempt whose `attempts.model` is
      not null, as the column's text, and states none on an attempt whose
      model is null. It states `factory:linesAdded` and
      `factory:linesRemoved` on a task as `xsd:integer`, each only where its
      own column (`tasks.added`, `tasks.removed`) is not null. A count of 0
      is stated as 0. The witness drives an attempt with a comma-joined
      model and one with none. It drives four tasks, with lines 12 and 7, 0
      and 0, 5 and null, and null and null.
    witness: tests/test_view_graph.py::test_an_attempt_states_its_model_and_a_task_its_lines_only_where_the_ledger_holds_them
    wrong_versions:
      - A null model is stated as the text `None`.
      - A null line count is stated as 0.
      - A count of 0 is treated as absent and not stated.
      - The two counts are stated under each other's term.
      - The counts are stated as `xsd:decimal`.
      - The counts are stated only when both columns are not null.
      - A comma-joined model is cut to its first name.
  - claim: >-
      A task's `<dl id="summary">` ends with the terms `lines added` and
      `lines removed`, after its five existing terms, each present only when
      the graph states that count. A count of 0 shows as `0`. The values
      come from `V2` bound on `?task`, or from `V5` bound on `?task` when
      `V2` returns no row. The witness drives a batched task with 12 and 0,
      an unbatched task with 3 and 7, an unbatched task with 5 and null, and
      an unbatched task with neither. It drives a batched decoy that `V2`
      returns first when unbound, and an unbatched decoy that `V5` returns
      first when unbound.
    witness: tests/test_view_server.py::test_a_task_summary_shows_the_lines_added_and_removed_the_ledger_holds
    wrong_versions:
      - The counts are read from `V2` alone, so an unbatched task shows none.
      - The counts are read from `V2` or `V5` unbound, so a page shows a decoy's counts.
      - A count of 0 is treated as absent.
      - A null count shows as `0`.
      - Both terms always appear, with an empty value when the ledger holds none.
      - The two terms show each other's value.
  - claim: >-
      The `attempts` table on a task page has a seventh and last column,
      `model`, holding the attempt's `factory:model` text as `V3` returns it.
      An attempt with no model has an empty cell there. The witness drives
      three attempts of one task, with one model, no model and a comma-joined
      pair, and a decoy task whose attempt has its own model.
    witness: tests/test_view_server.py::test_the_attempts_table_names_each_attempts_model
    wrong_versions:
      - The model column sits before `cost`.
      - An attempt with no model shows `None`.
      - A comma-joined model is cut to its first name.
  - claim: >-
      A task page shows its spec's title and type in a `<dl id="spec">`,
      with the terms `title` and `type`, and its `## Problem` section in a
      `<pre id="problem">`. The text is read from the task's repo mirror at
      its run's `base_sha`, from the file under `.saffron/specs/` whose name
      starts with the spec id and a hyphen. It is shown only when its sha256
      equals the task's `spec_sha`. The Problem text is exactly what the pull
      request body's extractor returns for that spec, so it is clipped and
      neutralized the same way. Title and Problem render as text, never as
      markup. A spec with no Problem section has no `<pre id="problem">`. The
      witness drives three specs in one mirror. One carries markup in its
      title and Problem and an `@` mention. One has a Problem past the
      extractor's limit, and one has no Problem. A later commit rewrites
      every spec, so a reader of `HEAD` reads other text.
    witness: tests/test_view_server.py::test_a_task_page_shows_its_specs_title_type_and_problem_read_at_the_runs_base
    wrong_versions:
      - The spec is read at the mirror's `HEAD`, not at the run's `base_sha`.
      - The title is written into the page unescaped.
      - The Problem is written into the page unescaped.
      - The Problem is cut out with a copy of the regex that neither clips nor neutralizes.
      - A spec with no Problem section gets an empty `<pre id="problem">`.
      - The type term shows the spec id.
  - claim: >-
      A task page whose spec text cannot be shown answers 200, shows no
      `<dl id="spec">` and no `<pre id="problem">`, and holds a `<p
      id="spec-unavailable">` whose whole text is `spec text unavailable:`
      and one reason. The reason is `absent` when no file name starts with
      the spec id and a hyphen, and `hash mismatch` when the text does not
      hash to `spec_sha`. It is `unparseable` when the text hashes but the
      spec parser refuses it. It is `unreadable` when git or decoding
      fails. The witness drives `absent` with a file whose name starts with
      the spec id and no hyphen. It drives `unreadable` four ways. They are
      a mirror path that does not exist, a `base_sha` the mirror lacks, a
      symlink leaving the tree, and bytes that are not UTF-8.
    witness: tests/test_view_server.py::test_a_task_page_says_why_its_spec_text_is_unavailable
    wrong_versions:
      - Only `GitError` is caught, so bytes that are not UTF-8 end the request with no response.
      - The file is matched on the spec id with no hyphen, so `SA-001` finds `SA-0012-good.md`.
      - A spec the parser refuses ends the request with no response.
      - The text is shown without the hash check.
      - A mirror path that does not exist reads as `absent`.
      - A `base_sha` the mirror lacks reads as `absent`.
  - claim: >-
      The pull request body still carries the spec's `## Problem` section
      under `## What`, now through the extractor's public name.
    witness: tests/test_report.py::test_the_specs_problem_reaches_what_so_the_heading_answers_itself
    preserves: true
---

## Context

Backlog item **b-5aa016**, which cites §6.2 and §4.1.

§6.2 (`DESIGN.md:1324-1332`) says a task page reads its spec from the
repo's mirror at the run's `base_sha`. It shows the text only when that
text hashes to the task's `spec_sha`. That sentence and the vocabulary
below landed by hand in `ffcfb432`, the base this spec builds on. Line
numbers below were read there.

**What the vocabulary already holds.** `factory:model` is a datatype
property of an attempt, ranged `xsd:string` (`ontology/factory.ttl:134`).
`factory:linesAdded` and `factory:linesRemoved` are task properties,
ranged `xsd:integer` (`ontology/factory.ttl:136-137`). Their shapes allow
at most one of each, and the two counts at least 0
(`ontology/shapes/factory-shapes.ttl:27-28` and `:71`). `V3` selects
`?model` (`ontology/queries/view/V3-task-timeline.rq:8` and `:17`). `V2`
and `V5` select `?added ?removed`
(`ontology/queries/view/V2-batch-tasks.rq:7` and `:18-19`,
`ontology/queries/view/V5-unbatched-tasks.rq:7` and `:19-20`).

**What `build` states now.** A task gets its state, risk, label, run and
pull request (`saffron/view/graph.py:210-220`), and no line count. An
attempt gets its phase, `n`, start, turns, cost and end
(`saffron/view/graph.py:237-259`), and no model. The ledger holds both:
`tasks.added` and `tasks.removed` (`saffron/ledger.py:136-137`) and
`attempts.model` (`saffron/ledger.py:158`). `model` is comma-joined when an
attempt named more than one (`saffron/ledger.py:149-151`).

**What the page shows now.** `_task_summary` reads one row from `V2` bound
on `?task`, then from `V5` (`saffron/view/server.py:456-478`). It keeps
the spec id, state, risk, batch and pull request, and no line count. The
summary `<dl>` has five terms (`saffron/view/server.py:656-662`). The
attempts table has six columns (`saffron/view/server.py:518`). The page
names the spec by id alone (`saffron/view/server.py:696`).

**Where the spec text is.** The ledger keeps `tasks.spec_sha`
(`saffron/ledger.py:126`) and `repos.mirror_path`
(`saffron/ledger.py:83`), and the run keeps `base_sha`
(`saffron/ledger.py:115`). `load_spec` hashes the spec file's bytes
(`saffron/intake.py:340-351`). `file_at` reads one path at a commit and
returns `None` when the tree lacks it (`saffron/repos/mirror.py:241-269`).

Measured on 2026-10-07 over the operator's ledger, read-only. It held 237
tasks. For 235 of them, the file under `.saffron/specs/` at the run's
`base_sha`, named for the spec id and a hyphen, hashed to `spec_sha`. The
text `file_at` returned, encoded as UTF-8, hashed the same for all 235. Two
did not hash, task 38 (`SA-0043`) and task 61 (`SA-0064`). No spec id
matched two files, and no spec file held a carriage return. One of the
235 failed today's `parse_spec`: task 59 (`SA-0063`) raised
`DisclosedMutantError`.

## Problem

1. **The graph.** In `build`, state `factory:model` on each attempt whose
   `model` is not null, as a plain literal of the column's text. State
   `factory:linesAdded` and `factory:linesRemoved` on each task, as
   `xsd:integer`, each where its own column is not null. Compare with
   `None`, so a 0 is stated.
2. **The summary.** Keep `?added` and `?removed` from the row
   `_task_summary` already reads. Write them as two more terms at the end
   of `<dl id="summary">`, each only when bound.
3. **The attempts table.** Add a last column named `model`. Fill it from
   `V3`'s `?model`, and leave it empty where that is unbound.
4. **The spec.** Under the summary, show the spec's title, type and
   Problem, or the one line naming why the text is unavailable. Read the
   task's `spec_id`, `spec_sha`, its run's `base_sha` and its repo's
   `mirror_path` from the ledger by task id. Open it the way the failure
   lines are read (`saffron/view/server.py:676-680`). Find the file, read
   it with `file_at`, compare its sha256 with `spec_sha`, and parse it
   with `parse_spec` (`saffron/intake.py:249`).
5. **The extractor.** `_problem` (`saffron/report/pr_body.py:187-210`)
   cuts out, clips and neutralizes a spec's Problem section. Give it a
   public name and call it from both places. Its one caller is
   `saffron/report/pr_body.py:182`. Change nothing else in that file.

## Out of scope

- Stating spec text in the graph. ADR 9 keeps text out of the graph, and
  the page reads it by id, as it reads failure lines.
- The `spec_texts` table. It held no row on the operator's ledger, and a
  stack revision's text is not at `base_sha`. Such a task shows a reason
  line.
- Two files at `base_sha` whose names both start with the spec id and a
  hyphen. None was measured, and no criterion fixes which one is read.
- Rendering the Problem's Markdown as HTML. It shows as preformatted text.
- A ledger file with no `model`, `added` or `removed` column. A `Ledger`
  open adds the two counts (`saffron/ledger.py:369-372`) and no migration
  adds `model`. Item b-d269f4 holds `build` raising on an older file.
- The index page and the batch page. Neither shows line counts or models.

## Notes for the agent

**This change adds code whose spelling no spec can know.** The graph
lines, the summary terms, the model column and the spec section are new.
So criteria 1 to 5 declare a witness and no mutant, and the `witness` gate
reports `skip` for them. Criterion 6 is `preserves`, since renaming the
extractor changes no output. The wrong versions under each criterion are
what its witness must kill. Do not run them yourself.

**Commit as each witness passes.** Five witnesses and the updated tests
make six commits at least.

**Listing the spec directory.** `saffron/repos/**` is forbidden, and
`mirror.py` has no function that lists a directory. So list
`.saffron/specs/` at `base_sha` with one `git ls-tree` call in the view.
A failed listing is `unreadable`, as a `GitError` from `file_at` is.
`file_at` raises `UnreadablePath`, a `GitError`, for a symlink leaving the
tree (`saffron/repos/mirror.py:254-264`). It decodes with `text=True`
(`saffron/repos/mirror.py:55`), so bytes that are not UTF-8 raise
`UnicodeDecodeError`, which is no `GitError`. Hash the returned text
encoded as UTF-8. `parse_spec` raises `SpecError` and its subclasses
(`saffron/intake.py:51` and `:56`).

**Escaping.** Every value from the spec goes through `html.escape`, as
every other cell on the page does. The extractor's text is already
neutralized for GitHub, and escaping comes after that.

**Tests that change, by name kept.** The `census` gate fails a removed or
renamed test. Three existing tests read the attempts table's width and
must take the seventh column. They are at `tests/test_view_server.py:452`,
`:1376` and `:1627`. Every existing task page now shows `spec text
unavailable: unreadable`, because `_ledger` names a mirror that does not
exist (`tests/test_view_server.py:49`).

**The parser.** `_PageParser` keeps only `<dl id="summary">`
(`tests/test_view_server.py:205` and `:247`). The witnesses also need the
`<dl id="spec">` terms, and the text of a `<p>` or `<pre>` by its id.

**Fixtures.** Build the mirror as a git repo under `tmp_path`, with a
local `user.name` and `user.email`. Commit the specs, keep that sha as
`base_sha`, then commit a rewrite of each spec. Register it with
`ledger.upsert_repo` and a run with `ledger.create_run(repo_id, sha)`. A
task's `spec_sha` is the sha256 of the committed bytes. Build the expected
Problem with the extractor's public name, imported inside the test body. A
module-scope import makes the reverted run a collection error.

**Criterion 2's decoys.** Create the batched decoy before the batched
task, in the same batch, and assert its IRI sorts first as text. Create
the unbatched decoy last, so `V5`'s `DESC(?task)` returns it first.

**Criterion 5's cases.** For `absent`, use a spec id of `SA-001` beside a
file `SA-0012-good.md`. For `unreadable`, use four tasks. One run's
`base_sha` is forty zeros. One repo's mirror path does not exist. One spec
is a symlink to `../../../outside.md`. One spec ends in the two bytes
`\xff\xfe`. For `unparseable`, leave `type` out of the frontmatter.

**Measured on a prototype over `ffcfb432`.** All 50 tests in the two view
test files passed, and `tests/test_report.py` passed unchanged.
Each of the five new witnesses failed against the base source. Each of the
28 wrong versions above, applied as an edit, failed its own witness. The
diff was 1467 changed tokens by the `size` gate's counter, against the
`feature` ceiling of 3000.
