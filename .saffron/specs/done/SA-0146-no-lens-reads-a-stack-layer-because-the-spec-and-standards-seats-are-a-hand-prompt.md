---
id: SA-0146
title: No lens can read a layer of a stack, because the Spec and Standards seats exist only as a hand prompt
type: feature
priority: 1
depends_on: [SA-0145]
touches:
  - saffron/end_review.py
  - saffron/phases/review.py
  - saffron/agents/prompts/end-review-spec.md
  - saffron/agents/prompts/end-review-standards.md
  - tests/test_end_review.py
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
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/rebut.py
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - saffron/agents/context.py
  - saffron/agents/findings.py
  - saffron/agents/artifacts.py
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/prompts/turns/**
  - tests/test_review.py
  - tests/test_context.py
  - tests/test_batch.py
  - tests/test_ledger.py
budget_usd: 27
max_attempts: 3
max_turns: 200
pending_symbols:
  - saffron/end_review.py::layer_fields
  - saffron/end_review.py::review_layer
acceptance:
  - claim: >-
      `end_review.layer_fields(ledger, task_key)` returns the `LayerFields`
      of the `stack_layers` row that key names. `base` is the row's
      `predecessor_head` when the row names a predecessor, and the layer's
      run's `base_sha` when it names none. `head` is the layer's own
      `pushed_sha`, and `spec_id`, `branch` and `pr_url` are its task's.
      `known` holds one line for each finding an in-cell lens filed on that
      task, in the order they were recorded. Each line carries the
      finding's severity, lens, `file:line` and claim, and its verdict and
      rebuttal where REBUT recorded them. Each run of whitespace inside a
      claim or a rebuttal becomes one space. `known` holds no finding of
      another task, nor of a lens outside `review.LENSES`. It raises
      `ValueError` for a key that names no layer, a layer with no pushed
      head, and a layer whose predecessor had no head. The witness drives
      the three in-cell lenses and the lenses `spec`, `standards` and
      `join`. It drives all three severities, a finding with a verdict and
      one without, a claim and a rebuttal that hold a newline, and a
      predecessor pushed again after the layer was recorded. It drives
      tasks of the same spec before and after the layer.
    witness: tests/test_end_review.py::test_a_layers_fields_come_from_its_own_row_and_its_own_task
  - claim: >-
      `end_review.end_review_prompt(lens, fields, ...)` fills that lens's
      own file from `END_LENSES`, whose keys are `spec` then `standards`,
      each on its own file. Each of the two prompts carries REVIEW's
      vocabulary, the spec body, the diff, the spec id, the branch, the
      pull request URL, `known` and the whole block
      `context.standing_instructions(claude_md)` returns, each verbatim,
      and the range as `<base>..<head>`. Braces in the spec body and in
      `known` pass through. The Spec prompt carries one line per acceptance
      criterion, holding its claim and its witness node id, and `preserves`
      only on a criterion that preserves. It carries
      `context.constraints_block(touches, forbidden, [])` whole. Each
      lens's raw prompt file holds the sentence "do not manufacture one"
      in any case, the three severities `blocker`, `concern` and `note`,
      and the fields `file`, `line`, `severity` and `claim`, each in
      backticks. The Spec file names `probe`, `find` and `replace` in
      backticks, and the Standards file names no `probe`. The Standards prompt file holds
      the phrase "never against a file in the worktree", and not the value
      of `worktree.WORKTREE_MOUNT`. It holds the phrase "is Saffron's
      process glossary, not this repository's", said of its vocabulary.
      Neither prompt file holds `.claude`, `CLAUDE.md`, `CONTEXT.md`,
      `DESIGN.md`, `driver.py`, `pytest`, `uv run`, `make check`, `ruff`,
      `prek`, `saffron/`, `docs/`, `/opt/` or `://`, matched without regard
      to case. The witness checks each of those fourteen strings in each
      file.
    witness: tests/test_end_review.py::test_each_end_review_prompt_is_its_own_file_filled_with_the_layers_fields
  - claim: >-
      `end_review.review_layer(container, fields, ...)` runs the Spec lens
      and then the Standards lens through `review.run_lens`, in
      `container`. Each is a fresh session with its own prompt from
      `end_review_prompt`, the read-only review tools, and the `max_turns`
      and `budget_usd` it was given. It returns their two `LensReview`s in
      that order. A Spec finding keeps the probe it carried, and a Spec
      finding whose output omits the `probe` key keeps none. The Standards
      lens keeps the default report model. It anchors nothing, so a finding on a
      changed line keeps `anchored` false. A Spec lens whose session fails
      comes back with its error and its cost, and the Standards lens still
      runs.
    witness: tests/test_end_review.py::test_a_layer_is_read_by_the_spec_lens_then_the_standards_lens
  - claim: >-
      `review.LENSES` still names the three in-cell lenses, so no cell's
      REVIEW runs an end-review lens.
    witness: tests/test_review.py::test_the_declared_lenses_are_the_three_that_run
    preserves: true
  - claim: >-
      A correctness finding still carries no probe field.
    witness: tests/test_review.py::test_a_correctness_finding_carries_no_probe_field_at_all
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 3 of its Done. It cites `DESIGN.md` §2.1,
§5.3 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 2 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "The end review",
is the design.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, cut from the head of the
layer below it, its **predecessor**. Once the last queued task settles, one
**end review** reads the stack. Two end-review lenses, Spec and Standards,
read each layer. One join lens reads the joins between layers. ADR 7 takes
four exceptions to ADR 4 for them. None of the three is one of ADR 4's
declared lenses.

**This spec is the first of three for step 3.** It builds the two seat
lenses: their prompts, their fields filled from the ledger, and one call
that runs both on a layer. `SA-0153` runs them over a stack after the batch
settles. It adds the reserve, the order down from the top, and the record
of each layer's end review, reviewed or not. `SA-0154` adds the join lens
and the critic cell a layer is read in, and wires the end review into
`saffron batch --stack`. `SA-0147` then qualifies the findings.

**What the tree base holds.** This spec's tree base is `SA-0145`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-147`), and the chain
`SA-0142` to `SA-0145` puts `stack_layers` and `Ledger.record_stack_layer`
there. `SA-0145` keys each row on record keys. Its columns are `task_key`,
`batch_key`, `position`, `spec_id`, `predecessor_key`, `predecessor_head`
and `generation`. `predecessor_head` is the predecessor's `pushed_sha` when
the layer was recorded. Every other line number below was read at
`642a26c3`.

**The two seats today.** `.claude/skills/run-saffron-spec-loop/REVIEW-PROMPT.md`
holds them as a delegate's hand prompt: an Opening (`:29-44`), the Spec seat
(`:46-72`), the Standards seat (`:74-92`) and the Report rules (`:94-115`).
The delegate fills nine fields by hand (`:15-27`). For a stacked spec, `{BASE}`
is a merge base with the parent's branch (`:17-18`). `{KNOWN}` is the in-cell findings the delegate
checked, and any blocker a lens withdrew at REBUT (`:25-27`). The seats name
this repository's files and tools, such as the loop's driver (`:72`) and
`CONTEXT.md` (`:77`). So they stay the hand path's own, and differ from
core's prompts by design
(`docs/superpowers/specs/2026-09-23-stack-batch-design.md:164-168`).

**Whose prompts these are.** ADR 7 makes the end-review lens prompts
core's, in `saffron/agents/prompts/`, and they name no repo file, tool or
URL. A repo's facts reach them as input the host fills. The host reads
those "at the `base_sha` export, never at a layer's head"
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:63-67`).
A layer's head is what that layer's agent wrote, so a standard read there
is one the agent could have rewritten (principle 43,
`docs/superpowers/specs/2026-09-23-stack-batch-design.md:105-109`).

**How a lens runs today.** `review.LENSES` maps each in-cell lens to its
prompt file (`saffron/phases/review.py:39-43`). `lens_prompt` fills that
file through `context.build_system_prompt` (`:168-188`). That call passes
the spec body around `str.format`, so braces in it pass through, and every
other value goes in as a `format` argument (`saffron/agents/context.py:190-198`).
`run_lens` runs one fresh session with `REVIEW_TOOLS`
(`saffron/phases/review.py:35`, `:208-234`). It parses the findings against
`reported_model(lens)` (`:102-111`). That model forbids any extra field
(`:58-70`), and only `adequacy` maps to one that requires a `probe`
(`:73-82`). A failed session comes back as a `LensReview` with its error
and its cost (`:237-241`).

**Where the fields live.** `Ledger.findings(task_id)` returns a task's
findings in the order they were recorded (`saffron/ledger.py:1190-1196`).
Each row carries `lens`, `severity`, `file`, `line`, `claim`, `anchored`,
REBUT's `verdict` and the `rebuttal` (`:153-165`). A task's run carries the
`base_sha` it was pinned at (`saffron/cell/session.py:1702`). An unstacked
cell's tree base is that `base_sha` (`saffron/cell/session.py:293-301`).
Reading `ledger._db` from another module has precedent in
`chain_walk._task_rows` (`saffron/chain_walk.py:54`) and
`session.previous_cut_orphan` (`saffron/cell/session.py:394-401`).

## Problem

Build four things.

1. **Two prompt files.** Add `saffron/agents/prompts/end-review-spec.md`
   and `end-review-standards.md`. Core owns both, and they name no repo
   file, tool or URL (ADR 7, principle 41). Write them in core's own
   words, covering the two remits below. Copy nothing from the hand
   seats, which name this repository's tools. Each is a system prompt for
   a read-only session in
   a critic cell, over one layer that already reached `READY_FOR_REVIEW`.
   It emits the `<output>` block the in-cell lenses emit, and each finding
   has `file`, `line`, `severity` and `claim`.
   - The **Spec** lens asks whether the diff does what the spec asks, no
     more and no less. It reads each criterion's claim, witness and
     `preserves` flag, and the spec's `touches` and `forbidden`, from its
     own slots. It walks each acceptance criterion to the
     `file:line` that satisfies it. A criterion
     nothing satisfies is a finding, and so is one a comment alone
     satisfies. A criterion whose witness would pass a wrong version gets a
     finding with a `probe` of `file`, `find` and `replace`. `find`
     matches exactly once in that file at the layer's head. The host runs the probe later, because the lens holds no tool
     that runs anything. The lens then looks past the criteria: behaviour
     the spec did not ask for, call sites the change leaves uncovered,
     and anything the diff does to get past a gate.
   - The **Standards** lens asks whether the diff follows the standards
     the repository wrote down. They reach it as the standing
     instructions block the host fills, read at the run's `base_sha`
     (`SA-0157` passes `CLAUDE.md` at the pinned `base_sha`). The lens
     never reads a standard from the worktree, which holds the layer's
     head (principle 43). The prompt tells it to judge against the
     standards the prompt carries, "never against a file in the
     worktree". Its three questions are vocabulary, the stated invariants
     and conventions, and one source. It judges vocabulary against the
     standing instructions it carries. `{vocabulary}` is Saffron's
     process glossary, not the repository's. The prompt says so in the
     glossary phrase criterion 2 names. It leaves format, lint,
     types and structure to the gates. It names no probe.

   Core knows nothing of one repository (§2.1). So neither file holds any
   of criterion 2's fourteen strings. The standing instructions reach the
   prompt as a filled value, as the in-cell lenses' do. Each file carries these slots: `{vocabulary}`,
   `{spec_id}`, `{branch}`, `{pr}`, `{base}`, `{head}`, `{known}`,
   `{standing_instructions}`, `{diff}` and `{spec}`. The Spec file also
   carries `{criteria}` and `{constraints}`.
2. **The layer's fields.** Add `saffron/end_review.py`. It holds a frozen
   dataclass `LayerFields` with `spec_id`, `branch`, `pr_url`, `base`,
   `head` and `known`. `layer_fields(ledger, task_key)` reads the layer's
   `stack_layers` row, its task and its run, and the task's findings.
   `base` is the head its predecessor had when the layer was recorded.
   A layer with no predecessor was cut from its run's `base_sha`. `known`
   is the layer's in-cell findings, those whose lens is in `review.LENSES`,
   one line each. A claim or a rebuttal can hold a newline, so each is
   folded onto its line. Read the findings through
   `Ledger.findings(task_id)`, which orders them by `finding_id`
   (`saffron/ledger.py:1190-1196`), not through SQL of your own.
3. **The prompt.** `END_LENSES` maps `spec` and then `standards` to their
   two files. `end_review_prompt(lens, fields, *, spec_body, diff,
   acceptance, touches, forbidden, context_md, claude_md, prompts_dir)`
   fills `END_LENSES[lens]` through `context.build_system_prompt` at phase
   `REVIEW`. The standing instructions come from
   `context.standing_instructions(claude_md)`. `{criteria}` is one line per
   `Criterion` in `acceptance`. `context.criteria_section` will not do,
   since it drops the witness and the flag (`saffron/agents/context.py:120-131`).
   `{constraints}` is `context.constraints_block(touches, forbidden, [])`
   (`:62-86`). The lens has no policy, so the protected list is empty.
4. **The lenses on one layer.** Add `review_layer(container, fields,
   ...)`. Its keywords are `end_review_prompt`'s eight, then `max_turns`,
   `budget_usd`, `agent` and `emit`. It runs `review.run_lens` once per entry of
   `END_LENSES`, in order, and returns the `LensReview`s. The Spec lens's
   id maps to a report model in `review._REPORTED` whose `probe` is
   optional. The Standards lens keeps the default model. Two docstrings
   then need a sentence each: `_ReportedWithProbe`'s
   (`saffron/phases/review.py:74-77`) and `reported_model`'s
   (`saffron/phases/review.py:88-89`). Each says only adequacy
   asks for an edit, and the Spec lens now does too.

No production code calls `layer_fields` or `review_layer` until `SA-0153`.
So both are `pending_symbols`, and the `dead` gate defers them while this
spec is open (`.saffron/gates/dead.py:4-6`).

## Out of scope

- **Running the lenses over a stack.** `SA-0153` owns the order down from
  the top and the reserve. It owns a layer the end review did not reach,
  and the record of each layer's end review. `SA-0153` also records the
  findings. It passes `spec.body` alone. REVIEW appends
  `context.criteria_section` to it (`saffron/cell/session.py:2539`), but
  here the Spec lens's `{criteria}` slot carries the criteria, so the
  append would send them twice.
- **How a repo declares its standards documents.** ADR 7 leaves it open
  (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:268`).
  This spec builds no declaration surface, reads no `.saffron/` key for
  one, and adds no slot for one. Until a spec answers it, the Standards
  lens carries the standing instructions alone, and a glossary or
  document they name is not read. Reading it from the worktree would
  read the layer's head, which principle 43 bars.
- **The join lens.** Its prompt, its fields and its run are `SA-0154`'s.
- **The critic cell a layer is read in.** It is seeded at the layer's
  pushed head. `review_layer` takes a container name, and `SA-0154` builds
  the cell and wires the end review into `saffron batch --stack`.
- **Qualification.** Anchoring, running a probe, severity and grouping are
  `SA-0147`'s. So `review_layer` anchors nothing, and its findings keep
  `Finding`'s default `anchored` of false.
- **Four seat fields.** `{REPO}` is the critic cell's worktree, which a
  prompt calls the worktree in prose. For a layer with a predecessor, `{CELL_BASE}` is
  the fetched head of its branch. It differs from `{BASE}` only after a
  hand push, which `SA-0145` leaves to the finishing layer.
  `{SPEC}` is replaced by the spec body itself. `{WHAT}` is the delegate's
  own summary, and the host writes none, so the prompt carries the diff.
- **The gate table.** An in-cell lens sees one (`review.gate_summary`).
  An end-review lens reads a layer whose gates already passed, and no
  Gate-only cell runs for it.
- **The vocabulary.** `CONTEXT.md` has no entry for an end review or an
  end-review lens. Backlog item b-466005 files both by hand.

## Notes for the agent

**Every criterion but the last two is new code.** No text at the tree base
fills an end-review prompt or reads a layer's fields. So criteria 1 to 3
declare a witness and no mutant, and `witness` reports `skip` for them.
Criteria 4 and 5 are `preserves` and name tests that pass now.

**Import `end_review` inside each test body.** It does not exist at the
tree base. A module-scope import fails collection when the source is
reverted, and `revert` reads that as `skip`. Every test in
`tests/test_end_review.py` is judged by `revert`, so none passes without
the source.

**Criterion 1's witness** builds a `Ledger` with no record in `tmp_path`.
It closes the ledger only after its last call. It creates one repo, and a
run and a task for each row below, in this order. Each run's `base_sha` is
the one shown.

| task | spec | run base | what it holds |
|---|---|---|---|
| `T9a` | `TE-9` | `b` | a push of `a`, `EXHAUSTED`, one correctness finding "c6" |
| `T7` | `TE-7` | `d` | packaged `READY_FOR_REVIEW` at `7`, one correctness finding "c5" |
| `T9` | `TE-9` | `b` | packaged `READY_FOR_REVIEW` at `9`, the six findings below |
| `T9c` | `TE-9` | `b` | a push of `f`, `EXHAUSTED` |
| `T11` | `TE-11` | `b` | no push |
| `T12` | `TE-12` | `b` | a push of `c` |

Each letter or digit stands for a sha of forty of it. `T9`'s findings, in
the order they are recorded:

1. A correctness `blocker` on `z.py:8`, anchored, whose claim is "q first
   half", a newline and "second half".
2. An adequacy `note` on `y.py:5`, "k middle", unanchored.
3. A contract `concern` on `x.py:3`, "b last {braces}", anchored, with
   verdict `withdrawn` and a rebuttal of "r1", a newline, two spaces and
   "argued".

No field sorts to that order. By file and line it runs 3, 2, 1, by claim
3, 2, 1, and by severity 1, 3, 2. Then come three findings on `x.py:4` of the lenses `spec`, `standards` and
`join`, "c4", "c7" and "c8". It records layers with
`record_stack_layer`: `T7` at 1 with no predecessor, `T9` at 2 on `T7`.
Then it pushes `e` to `T7`. It then records `T11` at 3 on `T9`, and `T12` at
4 on `T11`. `T11` has no push, so `T12`'s `predecessor_head` is `NULL`.

It asserts:

- `T9`'s fields: spec `TE-9`, its branch and URL, `base` `7`, `head` `9`.
- `T7`'s fields: `base` `d`, `head` `e`.
- `T9`'s `known` has one line holding "q first half second half",
  `blocker`, `correctness` and `z.py:8`. One line holds "k middle",
  `note`, `adequacy` and `y.py:5`. One holds "b last {braces}", `concern`,
  `contract`, `x.py:3`, `withdrawn` and "r1 argued". The three appear in
  that order.
- `known` holds none of "c4", "c7", "c8", "c5" and "c6".
- `ValueError` for `T9c`'s key, for `T11`'s and for `T12`'s.

These fail it, each measured:

- `base` read from the predecessor's current `pushed_sha`, which gives `e`
- `base` from the layer's own run in every case, which gives `b`
- `base` as `COALESCE(predecessor_head, base_sha)`, which runs `T12`
- the bottom layer's `base` left `None`
- the task found by spec id, newest or oldest, which reads `T9c` or `T9a`
- `head` taken from `predecessor_head`
- a layer with no head returned, not refused
- a key that names no layer returned as empty fields
- `known` with every lens, with anchored findings only, or with no notes
- `known` that drops the lens `spec` by name, or `spec` and `standards`
- `known` gathered from every task of the spec, which holds "c6"
- `known` sorted by severity, by file and line, or by claim
- `known` with no severity on a line, or no verdict and rebuttal
- a `known` line without its lens
- rebuttals listed apart from the findings they answer
- a claim or a rebuttal whose newline is kept

**Criterion 2's witness** builds `LayerFields` directly: `TE-9`, the
branch `saffron/layer-b`, the URL `https://h/pull/41`, `base` `7`, `head`
`9`, and a `known` holding "b last {braces}". The spec body is "Fix the {gap}, and keep {{this}} as
written." The diff holds `{}`. `claude_md` is two lines, and the witness
looks for `context.standing_instructions(claude_md)` whole. It passes two
criteria, one plain and one `preserves`, with distinct witness ids. It
passes one `touches` path and one `forbidden` path. The spec id appears
in no other value, so it reaches the prompt only through `{spec_id}`.
It reads `CONTEXT.md` from the repository root, as `tests/test_review.py:18` does.
For each lens it asserts each value appears verbatim, with
`context.sections_for("REVIEW", CONTEXT_MD)` as the vocabulary. It checks
the range as the two shas joined by `..`. It checks the other filled
values in a whitespace-flattened copy of the filled prompt.

It checks each file's own text in that file's raw text, never in the
filled prompt. The filled prompt holds text the file does not. Measured
at `060a758c`, the REVIEW vocabulary holds `` `blocker` `` five times,
`` `concern` `` three times, `` `note` `` four times and `/work` twice.
The standing instructions block names `/work` too
(`saffron/agents/context.py:146-148`). So a prompt with no severity
scale, or one naming the mount, would pass a check of the filled text.
In each raw file, whitespace-flattened, it checks the sentence, the three
severities, the four fields, and the Spec file's `probe`, `find` and
`replace`. It asserts the Standards file holds no `` `probe` ``. It
lowers each raw file and checks each of the fourteen strings, lowered,
against it. It reads the Standards file for the worktree phrase and the
glossary phrase, and asserts `worktree.WORKTREE_MOUNT` is not in it.

These fail it, each measured:

- both lenses on one file
- `base` and `head` swapped
- `known` or the spec body pasted into the template before `format`,
  which raises `KeyError`
- the standing instructions left out
- raw `CLAUDE.md` in place of the block
- the criteria from `context.criteria_section`, with no witness ids
- no `preserves` flag, or the flag on every criterion
- no `touches` and `forbidden` block, or the two lists swapped
- a Standards prompt that asks for a `probe`
- a prompt with no "do not manufacture one", or no vocabulary slot
- a Standards prompt judging vocabulary against `{vocabulary}`
- a Spec prompt with no `{spec_id}` slot

Four more are reasoned, not measured, since they came after the
simulations:

- a prompt with no severity scale, which a check of the filled prompt
  passes on the vocabulary's severities
- a Standards prompt that reads the files its instructions name from
  the worktree mount, as this spec's earlier text asked
- a Standards prompt with no sentence keeping its standards off the
  worktree
- a prompt that names this repository's tools or files, as the hand
  seats do

**The Standards lens's vocabulary is the repository's.** `{vocabulary}`
is Saffron's own `CONTEXT.md`, read from Saffron's root
(`saffron/cell/session.py:1811`). It holds the REVIEW sections with the
_Avoid_ lines stripped (`saffron/agents/context.py:28-31`, `:41`,
`:58`). It names the factory's terms. The Standards lens judges the
diff's words against the target repository's standing instructions,
which the host read at `base_sha`. Its prompt says which is which, in
the glossary phrase criterion 2 names.

**The constraints block is the implementer's rules, and the lens only
reads them.** `constraints_block` speaks to an implementer ("the only paths
you may change", `saffron/agents/context.py:76`). So the Spec prompt
introduces it as the rules the implementer was held to.

**Criterion 3's witness** calls `review_layer` twice, with a container
name, `max_turns` 17 and `budget_usd` 1.25. Its diff carries the `---` and
`+++` headers. Every scripted finding sits on a line one of its hunks
changed, so `findings.anchor` would mark it. Its agent double records each
call's container, options and keywords, and returns the next scripted
reply. It raises `AssertionError` on a call with no reply left. A default
reply would hide a lens that never ran, or one that ran twice.

- First call: the Spec reply holds a finding with a probe and one whose
  JSON omits the `probe` key. It must not write `"probe": null`.
  The Standards reply holds one finding. It asserts exactly two calls. Each
  has the container, `REVIEW_TOOLS`, `max_turns` 17, `max_budget_usd`
  1.25, and no `resume`. Call *i*'s system prompt equals `end_review_prompt`
  for the *i*th lens, `spec` then `standards`. The result's lenses are
  `spec` then `standards`, and neither has an error. The first finding's
  probe equals the `Mutant` it carried, and the second's is `None`. No
  returned finding is anchored. `review.reported_model("standards")` is
  `review.reported_model("correctness")`, so the Standards lens keeps the
  default model.
- Second call: the Spec lens raises `implement.AgentFailed` with an
  attempt costing 0.4. It asserts two calls, the Spec review's error set
  and cost 0.4, and the Standards finding returned.

These fail it, each measured:

- the Spec lens alone
- a loop that stops at the first lens with an error
- one prompt for both lenses
- the two lenses in the other order
- a fixed budget, or a fixed `max_turns`
- the second lens resuming the first lens's session
- each lens's findings run through `findings.anchor`
- the Standards lens on the optional-probe model
- the Spec lens on the default model, which refuses the probe
- the Spec lens on `adequacy`'s model, which requires one
- a nullable `probe` with no default, which pydantic reads as required

The three model cases fail on the re-prompt `run_lens` makes after a finding
that is not the schema (`saffron/phases/review.py:242-260`). It takes the
Standards reply and leaves the Standards lens a call with no reply.

**How the lists were measured.** Two throwaway simulations ran on
2026-09-23 at `0b1b4b96`. Criterion 1's built `stack_layers` with
`SA-0145`'s columns and wrote each row as `record_stack_layer` does.
Criterion 2's used two stand-in prompt files that held the slots above.
Criterion 3's ran the real `review.run_lens`, with `review._REPORTED`
patched for each model. The right build passed each witness, and every
wrong version listed failed. After the first spec review all three ran
again, with `T9`'s findings reordered, the criteria and constraints slots,
and the nullable model. The round-1 order let a sort by file or by claim
pass, since it matched the recorded order. After the second review they
ran once more. That run added each `known` line's lens, the glossary
phrase, a branch and URL free of the spec id, and the Standards model. The double's strictness decided no case in
that run. A lax double failed each wrong version too, on the call count or
the Standards finding. It stays strict, because a later edit to the
witness would lose that. The nullable model accepts `"probe": null` and
refuses an omitted key, measured, so only an omitted key kills it.

**The bottom layer's `base`.** It is not the pushed head's parent once
`main` moves. PACKAGE squashes the cell's work into one commit onto the fetched default
head (`saffron/phases/package.py:666`, `:776-786`). So for a layer with
no predecessor, `base..head` can hold commits that are not the layer's.
`layer_fields` still returns the run's `base_sha`, and this spec changes no
behaviour for it. `SA-0153` builds the diff, and diffs `head^..head`,
which is exact because PACKAGE pushes one commit.

**What the witnesses leave undriven.** A finding whose `line` is `NULL` is
not driven. `Finding.line` is a required `int`
(`saffron/agents/findings.py:39`), so no write path the witness can use
makes one. A layer with no in-cell findings is not driven, and its `known`
is empty. A Standards lens that fails is not
driven, and neither is output that is not the schema after the re-prompt.
`run_lens` handles both the same way for every lens
(`saffron/phases/review.py:235-293`). A layer whose `pr_url` or `branch` is
`NULL` is not driven. PACKAGE writes both for `READY_FOR_REVIEW`
(`saffron/ledger.py:1109-1119`). A prompt can name a repo file, tool or
URL by a string outside criterion 2's fourteen, and it passes. So does a
Standards prompt that keeps the worktree phrase and still reads a
standard there. The first layer an end review reads measures each
prompt's quality.

**The prompts are prose the `prose` gate reads**
(`.saffron/gates/prose.py:43-44`). A new file starts at zero, so write no
em dash, semicolon, contraction, perfect tense, hedge or sentence over 25
words. The same holds for every new comment and docstring, and a docstring
stays within ten lines. Check each file with
`python3 hooks/prose_limit.py --file <path>` before you commit it.

**A brace in a prompt file is a slot.** `build_system_prompt` runs
`format` over the file (`saffron/agents/context.py:194-197`). So a
literal brace, as in a JSON example, is written doubled or not at all.
Criterion 2's witness raises on a single one.

**Commit as each witness passes**, before the full suite runs.

**The turn ceiling.** `max_turns` is 200. The nearest history row,
`SA-0133`, peaked at 161 turns, cut off at its own ceiling of 160. So 161
is a floor, and what that cell needed above it was never measured. 200
leaves 39 turns above the floor, as `SA-0169` does.

**Size.** No path here is in `elevate_on`, so `size` is advisory. Two
prompt files of about 35 lines each run near 10 tokens a line, about 700.
About 100 lines in `saffron/end_review.py` at 5.5 is about 550, and 8 in
`review.py` about 40. About 210 test lines at 4.8 is about 1010. That is
about 2300 tokens of the `feature` ceiling of 3000
(`saffron/gates/core/size.py:26`). The criteria and constraints slots, the
Standards lens's worktree phrase and their asserts add about 190 more.
The second review's asserts and the glossary phrase add about 40. The
fourteen-string check adds about 50 over the three names it replaces.
Reading each file's own text raw adds about 40. That is about 2620 in
all, 87% of the ceiling. Keep the prompts near the length of
`criterion-probe.md` (56 lines), not of the in-cell lenses'.
