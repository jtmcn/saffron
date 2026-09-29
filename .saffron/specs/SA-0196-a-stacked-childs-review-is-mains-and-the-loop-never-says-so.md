---
id: SA-0196
title: A stacked child's REVIEW is main's, and neither the loop's check nor its record says so
type: feature
priority: 2
depends_on: []
estimated_lines: 260
touches:
  - .claude/skills/run-saffron-spec-loop/driver.py
  - .claude/skills/run-saffron-spec-loop/SKILL.md
  - tests/test_spec_loop_driver.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/agents/**
  - .claude/skills/run-saffron-spec-loop/GOTCHAS.md
  - .claude/skills/run-saffron-spec-loop/REVIEW-PROMPT.md
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - records/**
  - harness/**
  - saffron/**
  - tests/test_spec_size_estimate.py
  - tests/test_jev_driver.py
  - tests/test_review.py
  - tests/test_rebut.py
  - tests/test_session.py
budget_usd: 24
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      `driver.py check` prints one `review:` line for each spec the target
      reaches through `depends_on`, every entry and every depth, whose file
      is not retired to `done/` and whose `touches` names a REVIEW or REBUT
      source. Those are `saffron/phases/review.py`, `saffron/phases/rebut.py`,
      the turn prompts `review.md`, `rebut.md`, `verdict.md` and
      `rebut-extract.md` under `saffron/agents/prompts/turns/`, and any path
      matching `saffron/agents/prompts/review-*.md`. The line names that spec
      and its matching entries in `touches` order, and says the target's
      REVIEW is main's and will not run that change. It prints whether or not
      past cells match the target's shape. It prints nothing for the target
      itself, for a retired ancestor, for an ancestor that touches no such
      source, or for an id no spec file declares. A target with no
      `depends_on` parses no spec for the walk. It is not a concern, so the
      exit status stays 0 and the clear line still prints.
    witness: tests/test_spec_loop_driver.py::test_check_says_an_unretired_ancestors_review_change_is_not_in_this_specs_review
    wrong_versions:
      - A trigger set without the four turn prompts, so an ancestor editing REBUT's verdict turn prints nothing.
      - A trigger that matches any path under `saffron/agents/prompts/turns/`.
      - A walk that starts at the target itself, so a target touching `review.py` names itself.
      - A walk that lists the live specs even when the target declares no `depends_on`.
      - A walk that follows only `depends_on[0]`, as `_depends_on_chain` does, so an ancestor reached through a second entry prints nothing.
      - A walk over the target's own `depends_on` entries only, so a grandparent prints nothing.
      - A line printed for an ancestor whose spec file sits in `done/`.
      - A prompt match against the four prompt files the tree holds, so a new prompt path or the glob entry itself prints nothing.
      - A line printed only after the history rows exist, so a target with no past cells gets none.
      - A line printed as a `concern:`, or counted as one, so the clear line vanishes or the exit status moves.
      - One line per matching path rather than one per ancestor.
      - An ancestor reached twice printed twice.
      - A `depends_on` id no spec file declares raising rather than being passed over.
  - claim: >-
      `driver.py record` prints a second stdout line naming the lenses the
      spec's latest REVIEW ran, for a reviewable task, a task that ended
      `EXHAUSTED` and a task halted at `REBUTTING` alike. It reads
      `findings.json` in the spec's directory under `JEV_ROOT / "v0"`. The
      names keep that file's order, and a lens whose `error` is set carries
      ` (error)`. The file counts as the latest run's when no `gates/`
      directory sits beside it, or when its mtime is not older than that
      directory's, a tie included. A `baseline.json` beside it plays no
      part. A file that is missing, older than `gates/`, not JSON, empty,
      not a list, or holding an entry with no `lens` prints the
      none-recorded line instead. The exit status is unchanged.
    witness: tests/test_spec_loop_driver.py::test_record_names_the_lenses_the_specs_latest_review_ran
    wrong_versions:
      - A lens line printed only for a `READY_FOR_REVIEW` task.
      - A lens line printed only inside the `DONE_STATES` branch, so a halt gets none.
      - A staleness rule anchored on `baseline.json`, as `_jev_cell`'s is.
      - A strict comparison, so a file whose mtime ties with `gates/` reads as stale.
      - An entry with no `lens` skipped, so the line names the rest.
      - Lens names read from the ledger's findings rows, so a lens that filed no finding goes unnamed.
      - An errored lens dropped from the line, or printed without its marker.
      - The lens names sorted rather than kept in the file's order.
      - A file older than `gates/` read as the latest run's REVIEW.
      - A file with no `gates/` beside it read as no REVIEW.
      - A corrupt file raising rather than printing the none-recorded line.
      - The lens line written to stderr, or the exit status moved by it.
---

## Context

Backlog item **b-66d1c3**, from the spec loop's run 21
(`docs/evidence/2026-09-29-spec-loop-skill-feedback-run-21.md`, point 7).
It cites `DESIGN.md` §5.5 and §5.6. Every line number below was read at
`791d9a88`.

**The operator's decision.** A stacked child's REVIEW is main's REVIEW,
said aloud. The control plane never executes model-authored code
(`DESIGN.md:123`, §2). So REVIEW, REBUT and the probes run from the host's
checkout, and a parent's new lens runs in none of its children's cells.
Nothing in the design changes, and no ADR is written. This spec makes the
loop say so twice. `check` says it before a cell, and `record` names the
lenses after one.

**What run 21 showed.** `SA-0191` added the conventions lens to `LENSES`.
`SA-0192` depended on it, and its budget was raised to $26 for a four-lens
REVIEW. Its REVIEW ran three lenses, and the whole cell cost $7.16. The
three names are in `~/.saffron/batches/v0/SA-0192/findings.json`, read on
2026-09-29.

**Where the lens set is recorded today.** The ledger does not name it. It
holds a finding row per finding, each with its lens
(`saffron/ledger.py:1565-1590`, the lens at `:1577`). A lens that filed no
finding leaves no row. `SA-0191`'s three lenses filed none, so its task,
189 in the host's ledger, has no finding row and names no lens. The `attempts` table carries no lens column
(`saffron/ledger.py:120-133`). `criterion-probes.json` holds one entry per
criterion, not per lens (`saffron/cell/session.py:2802-2805`).

`findings.json` does name it. `run_review` runs every entry of `LENSES` in
order (`saffron/phases/review.py:344`). `session.py` writes the whole list
as `findings.json`, one `as_dict` per lens (`saffron/cell/session.py:2832-2834`).
Each dict carries `lens` and `error` (`saffron/phases/review.py:159-165`). A
lens that crashed or broke the schema is still in the list, with `error`
set. So this spec adds no core field and reads that file.

**Its limit.** The file lives in the spec's directory, `out_dir / spec_id`
(`saffron/cell/session.py:1758`), so a re-run of the spec overwrites it.
Each run removes and recreates `gates/` in that directory
(`saffron/cell/session.py:1768-1769`, `saffron/repos/mirror.py:182-197`).
That happens before the run creates its task row
(`saffron/cell/session.py:1817-1822`). Nothing later writes to `gates/`,
which the cell mounts read-only (`saffron/cell/worktree.py:37`). So a
`findings.json` older than `gates/` is an earlier run's REVIEW. One not
older belongs to the run that made the spec's newest task row.

`baseline.json` is a weaker anchor. It is written after the task row
(`saffron/cell/session.py:1914-1916`). A run that dies between the two
leaves the prior `findings.json` newer than the prior `baseline.json`.
`_jev_cell` still uses that anchor
(`.claude/skills/run-saffron-spec-loop/driver.py:1390-1410`).

**What `check` does today.** `cmd_check` prints the ceilings line, then a
size concern, then returns early when no past cell matches
(`.claude/skills/run-saffron-spec-loop/driver.py:2089-2115`). It reads no
`depends_on`.

`_known_specs` reads every spec, live and retired, through `SPECS_DIR`
(`.claude/skills/run-saffron-spec-loop/driver.py:1733-1744`).
`_depends_on_chain` follows only `depends_on[0]`
(`.claude/skills/run-saffron-spec-loop/driver.py:614-626`).

**What REVIEW and REBUT load.** Each lens reads its `review-*.md` prompt
(`saffron/phases/review.py:40-45`) and the turn prompt `review.md`
(`saffron/phases/review.py:66`). REBUT loads the turns `rebut.md`,
`verdict.md` and `rebut-extract.md` (`saffron/phases/rebut.py:30-36`).
`context.turn_prompt` reads each from `prompts/turns/`
(`saffron/agents/context.py:177-178`).

**What `record` prints today.** One stdout line, the spec, its state, its
pull request and its spend
(`.claude/skills/run-saffron-spec-loop/driver.py:1077-1133`). A halt adds a
stderr line. The test at `tests/test_spec_loop_driver.py:783` pins that
stdout exactly (`tests/test_spec_loop_driver.py:820-822`). The `loop`
fixture leaves `JEV_ROOT` at the host's `~/.saffron/batches`
(`tests/test_spec_loop_driver.py:613-660`).

## Problem

1. **`check`.** Walk every spec the target reaches through `depends_on`.
   Follow every entry, at any depth. The target itself is not on the walk.
   Print one line for each spec that meets both tests.
   - Its file is in `SPECS_DIR` itself, not in `done/`.
   - Its `touches` has an entry equal to one of six paths, or one matching
     `saffron/agents/prompts/review-*.md` under `fnmatch.fnmatchcase`. The
     glob entry itself matches. The six are `saffron/phases/review.py`,
     `saffron/phases/rebut.py` and these four turn prompts.
     - `saffron/agents/prompts/turns/review.md`
     - `saffron/agents/prompts/turns/rebut.md`
     - `saffron/agents/prompts/turns/verdict.md`
     - `saffron/agents/prompts/turns/rebut-extract.md`

   A target with no `depends_on` has nothing to walk. Then list no live
   specs and parse nothing for it.

   The line reads as below, with the matching entries joined by `, ` in
   `touches` order. Print it after the size concern and before the early
   return, so a target with no past cells gets it too.

   ```text
   review: <ID> is not retired and touches <entries>. This spec's REVIEW is main's and will not run that change, so budget_usd should not assume it.
   ```

2. **`record`.** After the existing stdout line, print one more. For a
   `findings.json` that counts as the latest run's, it names each entry's
   `lens` in file order, joined by `, `. An entry with a non-null `error`
   gets ` (error)` after its name. Otherwise it prints the none-recorded
   line. Both forms are below.

   ```text
   lenses: correctness, contract (error), adequacy, conventions
   lenses: none recorded for this spec's latest run
   ```

   The file counts as the latest run's when no `gates/` directory sits
   beside it, or its mtime is equal to or newer than that directory's. A
   file that is missing, older than `gates/`, not JSON, empty, not a list,
   or holding an entry with no `lens` prints the none-recorded line. Print
   the line outside the state branches, so it follows every state `record`
   reports, halts included. It moves no exit status.

3. **`SKILL.md`.** Section 1b has a paragraph opening "It applies three
   blocker rules". Add a sentence to it. A `review:` line means the
   spec's REVIEW is main's, so its budget leaves that ancestor's change
   out. Section b opens "Record it once the process exits". Add there that
   `record` also prints the lenses the REVIEW ran. The task's report
   carries that line.

## Out of scope

- **Running a child's REVIEW from its parent.** The operator chose main's
  REVIEW. The host checkout stays the only source of REVIEW code.
- **A core record of the lens set.** `findings.json` names it. A fact in
  `refs/saffron/*` is item 170's direction, and not this spec's.
- **The probe prompts.** `criterion-probe.md`, `wrong-version.md` and
  their two turns shape the probe sessions REVIEW pays for. They add no
  lens and no verdict, so a change to them moves no finding a child's
  budget assumes. The operator left them out.
- **`rebut-verdict.md`.** It is the system prompt of REBUT's verdict
  session (`saffron/phases/rebut.py:30`). The operator's trigger set of
  2026-09-29 leaves it out, and this spec keeps that call.
- **A broader glob in a parent's `touches`,** such as `saffron/phases/**`.
  It equals none of the six paths and prints nothing.
- **Pricing.** `check`'s arithmetic is unchanged. Its history rows already
  price main's REVIEW, since every past cell ran it.
- **`_jev_cell`.** It keeps its `baseline.json` rule, the weaker anchor
  above. Moving it to `gates/` is its own change, so leave it as it is.
- **An older task's first line.** `record` names the task that holds a
  pull request, which can be older than the latest run
  (`.claude/skills/run-saffron-spec-loop/driver.py:1077-1107`). The lens
  line always reads the latest run.

## Notes for the agent

**Both criteria are new code.** Neither declares a mutant. The `review:`
line and the `lenses:` line do not exist at base, so no text there fixes
their spelling. The `witness` gate reports `skip` for both.

**Where the code goes.** Put the six trigger paths and the glob in
module-scope constants in `driver.py`. Walk ancestors with a seen set. When
the target declares a `depends_on`, take the specs from `_known_specs()`
and the unretired ids from `intake.discover_specs(SPECS_DIR)`, both read
through `SPECS_DIR`. Call neither for a target with none. Read the batch
directory through the module's `JEV_ROOT`, never `Path.home()`. Import
inside the functions, as the driver does now.

**The `loop` fixture.** Point `JEV_ROOT` at `tmp_path / "batches"` there,
so no test reads the host's batch tree. Then
`test_record_keeps_what_package_pushed_and_says_what_the_cell_spent`
expects the none-recorded line after its spend line. Keep that test's
name. `census` fails a test collected at base and absent at head.

**Criterion 1's witness.** One plain `def`, not parametrised. Write these
spec files under a `tmp_path` specs directory and point `SPECS_DIR` at
it. Each has `title: x` and `type: feature`.

| id | where | `depends_on` | `touches` |
|---|---|---|---|
| `SA-0910` | live | `[SA-0906, SA-0903, SA-0999]` | `[saffron/phases/review.py]` |
| `SA-0906` | live | `[SA-0901, SA-0903]` | `[saffron/phases/implement.py, saffron/agents/prompts/turns/implement.md]` |
| `SA-0903` | live | `[SA-0904]` | `[saffron/phases/rebut.py, saffron/agents/prompts/turns/verdict.md]` |
| `SA-0901` | live | `[SA-0905]` | `[saffron/phases/review.py, tests/test_review.py, saffron/agents/prompts/review-conventions.md]` |
| `SA-0904` | live | `[]` | `[saffron/agents/prompts/review-*.md, saffron/agents/prompts/review-security.md]` |
| `SA-0905` | `done/` | `[]` | `[saffron/phases/review.py]` |
| `SA-0911` | live | `[SA-0905]` | `[f.py]` |

No file declares `SA-0999`. Stub `_ledger_and_repo` with `_StubLedger`,
`_overrun` with a ratio of 1, and `_elevate_on` with an empty list.

- Stub `_past_cells` to return nothing. Run `check SA-0910`. Assert it
  returns 0. Assert the sorted lines opening `review:` equal the sorted
  three below, exactly.
- Stub `_past_cells` to return one `_cell("SA-2000", "feature", 1, 0)`
  row. Run it again. Assert it returns 0, the same three lines, and the
  line `check: ceilings clear this shape's history`.
- Run `check SA-0911`. Assert no line opens `review:`.
- Last, inside `monkeypatch.context()`, stub `_known_specs` to return one
  spec, `SA-0912`, with no `depends_on` and `touches` of
  `[saffron/phases/review.py]`. Replace `saffron.intake.discover_specs`
  with a function that raises `AssertionError`. Run `check SA-0912`.
  Assert it returns 0 and no line opens `review:`.

`SA-0910` touches `review.py` itself, so a walk that includes the target
names it. `SA-0906`'s `turns/implement.md` is a turn prompt outside the
four. None of the three lines below names either.

```text
review: SA-0903 is not retired and touches saffron/phases/rebut.py, saffron/agents/prompts/turns/verdict.md. This spec's REVIEW is main's and will not run that change, so budget_usd should not assume it.
review: SA-0901 is not retired and touches saffron/phases/review.py, saffron/agents/prompts/review-conventions.md. This spec's REVIEW is main's and will not run that change, so budget_usd should not assume it.
review: SA-0904 is not retired and touches saffron/agents/prompts/review-*.md, saffron/agents/prompts/review-security.md. This spec's REVIEW is main's and will not run that change, so budget_usd should not assume it.
```

**Criterion 2's witness.** One plain `def`, beside the existing `record`
tests. Build the ledger the way
`test_record_keeps_what_package_pushed_and_says_what_the_cell_spent`
does, with its `$7.55` spend, `$6.00` budget and `#247`. Its stdout's
first line is `<id>  READY_FOR_REVIEW  #247  $7.55 of $6.00`. The ledger
holds no finding row. `record` closes the ledger it gets, so close the
setup ledger and stub `_ledger_and_repo` to open a fresh `Ledger` on the
same file each call. Write the files under
`driver.JEV_ROOT / "v0" / <id>`. Set every mtime with `os.utime` from a
fixed epoch `T`, the directory's included. After each of steps 1 to 9,
assert `record` returns 0 and its whole stdout is the first line plus the
lens line named.

1. `findings.json` lists `correctness`, `contract`, `adequacy` and
   `conventions` in that order, each with `"findings": []`. Only
   `contract` has `"error": "boom"`, and the rest `null`. Its mtime is
   `T`. There is no `gates/`. Expect
   `lenses: correctness, contract (error), adequacy, conventions`.
2. Make a `gates/` directory with mtime `T + 100`. Expect the
   none-recorded line.
3. Set `findings.json` to `T + 200`. Write `baseline.json` at `T + 300`.
   Expect step 1's line. Leave `baseline.json` in place from here on.
4. Set `findings.json` to `T + 100`, equal to `gates/`. Expect step 1's
   line.
5. Overwrite `findings.json` with `{` at `T + 200`. Expect the
   none-recorded line. Keep it at `T + 200` in steps 6 to 8.
6. Overwrite it with `[]`. Expect the none-recorded line.
7. Overwrite it with `{"lens": "correctness"}`. Expect the none-recorded
   line.
8. Overwrite it with step 1's list plus a fifth entry,
   `{"error": null, "findings": []}`. Expect the none-recorded line.
9. Delete it. Expect the none-recorded line.
10. Write step 1's file again at `T + 200`. Set the task to `EXHAUSTED`
    with `set_task_state` on a fresh `Ledger`. Assert `record` returns 1
    and its stdout's last line is step 1's line.
11. Set the task to `REBUTTING` the same way, and stub `_cell_running` to
    return `False`. Assert `record` returns 1 and its stdout's last line
    is step 1's line.

**Measured on a prototype, 2026-09-29.** Both witnesses above passed on a
prototype of this change and failed on the driver at `791d9a88`. Every
wrong version under both criteria was then applied to the prototype. Each
one failed its criterion's witness.

**Every test you add must fail with this diff's source reverted.** At base,
`check` prints no `review:` line. `record` prints one stdout line. So each
witness fails on an assertion. Neither fails to collect. Import
nothing new at module scope.

**Size.** The prototype's driver change and both witnesses measured 828
tokens under `size_gate`'s counter, with no docstring and no `SKILL.md`
edit. Those add about 200 more. `estimated_lines` is 260, that total over
four, with no overrun added.

**The prose gate** counts every new comment, docstring and line of
`SKILL.md`. Write none with an em dash, a semicolon, a contraction, the
perfect tense, a hedge or a sentence over 25 words.

**Commit as each witness passes**, before the full suite runs.
