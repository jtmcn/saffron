---
id: SA-0282
title: A policy loads two fields nothing reads, and a shared-kernel cell never says its thread pool is uncapped
type: feature
priority: 2
depends_on: [SA-0281, SA-0271, SA-0262, SA-0264]
estimated_lines: 200
estimate_measured: true
touches:
  - saffron/repos/policy.py
  - saffron/cell/runtimes/__init__.py
  - saffron/cell/runtimes/apple.py
  - saffron/cell/runtimes/podman.py
  - saffron/cell/session.py
  - saffron/ledger.py
  - tests/test_policy.py
  - tests/test_runtime.py
  - tests/test_session.py
  - tests/test_package.py
  - tests/test_setup_saffron.py
  - .claude/skills/setup-saffron/templates/policy.yaml
  - .claude/skills/setup-saffron/SKILL.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/backlog/**
  - docs/appendices/**
  - docs/adr/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/record/**
  - saffron/events.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/scheduler.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
budget_usd: 52
max_attempts: 3
max_turns: 220
acceptance:
  - claim: >-
      `load_policy` refuses a gate declaration that carries a `when` key. It
      raises `PolicyError`, and the error text names the gate and the `when`
      key.
    witness: tests/test_policy.py::test_a_gate_declaring_when_is_refused_at_load
    mutant:
      file: saffron/repos/policy.py
      find: "blocking: bool = True"
      replace: "blocking: bool = True\n    when: str | None = None"
    wrong_versions:
      - The gate model keeps its `when` field, so the key still loads and nothing reads it.
      - A `when` key draws a printed warning and the policy still loads.
  - claim: >-
      `load_policy` refuses a policy that declares `envelope_default`, an
      empty list included. It raises `PolicyError`, and the error text names
      `envelope_default`.
    witness: tests/test_policy.py::test_a_policy_declaring_envelope_default_is_refused_at_load
    mutant:
      file: saffron/repos/policy.py
      find: "    elevate_on: list[str] = Field(default_factory=list)"
      replace: "    elevate_on: list[str] = Field(default_factory=list)\n    envelope_default: list[str] = Field(default_factory=list)"
    wrong_versions:
      - The policy model keeps its `envelope_default` field, so the key still loads.
      - A rule that refuses a non-empty list only, so `envelope_default` set to an empty list still loads.
  - claim: >-
      Each of the two dialects states whether a cell shares the host kernel.
      `shares_kernel` is `False` for apple/container's dialect and `True` for
      podman's.
    witness: tests/test_runtime.py::test_each_dialect_says_whether_it_shares_the_host_kernel
    wrong_versions:
      - Both dialects report the same value.
      - The member is declared on `Dialect` and implemented by podman's dialect alone.
  - claim: >-
      A cell that mints its own task decides at policy load whether its
      thread pools run uncapped. That holds when the selected dialect's
      `shares_kernel` is true and the policy's `thread_env` holds no
      entries. Then the cell emits one `Preflight` event with step
      `thread_env`, whose detail names `thread_env` and the runtime's
      binary. The task still runs its plan and implement turns, and its
      `task_created` fact carries `thread_pool_uncapped` set to `True`.
      Otherwise no such event is emitted and the fact carries `False`. The
      witness drives five cells. Podman with no `thread_env` key, and podman
      with an empty map, each warn and record `True`. Podman with one entry,
      apple/container with no key, and a stub VM dialect whose `unattended`
      is false, with no key, each record `False`.
    witness: tests/test_session.py::test_a_shared_kernel_task_with_no_thread_env_entries_warns_and_records_an_uncapped_pool
    wrong_versions:
      - An empty map counts as declared, so podman with `thread_env` set to an empty map records `False`.
      - The check ignores the runtime, so apple/container with no key warns too.
      - The check reads `not unattended` in place of `shares_kernel`.
      - The warning names `thread_env` and not the runtime.
      - The warning is emitted and the payload key is never passed, so the fact carries `None`.
      - The payload key is written only when the pool is uncapped, so a capped task records `None`.
      - The warning is computed and never emitted.
      - An uncapped pool refuses the task instead of warning.
  - claim: >-
      The setup skill's policy template,
      `.claude/skills/setup-saffron/templates/policy.yaml`, still names
      exactly the policy model's fields. So it declares no
      `envelope_default`.
    witness: tests/test_setup_saffron.py::test_the_policy_template_names_every_policy_field
    preserves: true
    wrong_versions:
      - The template keeps its `envelope_default` line, which the policy now refuses.
---

## Context

Backlog item **b-0569f7**, with item **19**. It cites `DESIGN.md` §3.2
and §5.4, and ADR 10. ADR 10 makes `.saffron/` an interface that other
operators write against. Its consequences say the engine refuses a field
it parses and never reads. Its principle 7 accepts an uncapped pool on a
shared kernel, provided b-0569f7 warns and records it on the task. This
is the first of two specs. `SA-0283` adds a schema version to the policy,
the spec and the gate contract, and depends on this one. Every line
number below was read at `bc879e2c`. The parents move `session.py`, so
re-find each line at your tree base.

**Two policy fields load and nothing reads them.** `GateDeclaration`
declares `when` (`saffron/repos/policy.py:49`). `Policy` declares
`envelope_default` (`saffron/repos/policy.py:72`). Both models forbid
unknown keys (`saffron/repos/policy.py:46`, `:67`). `load_policy` turns a
validation error into `PolicyError` (`saffron/repos/policy.py:129-132`).
No module in `saffron/` but `policy.py` reads either field.
`test_a_field_the_skill_calls_unread_is_still_unread`
(`tests/test_setup_saffron.py:174`) asserts exactly that.

**The shared-kernel gap is a docstring.** Podman's `cpu_flags` docstring
says a repo with no `thread_env` has an uncapped pool there
(`saffron/cell/runtimes/podman.py:65-71`). `DESIGN.md` §5.1 says the same.
Nothing acts on it. The `Dialect` protocol has no member that says whether
a cell shares the host kernel (`saffron/cell/runtimes/__init__.py:29-87`).

**Where the policy and the task meet.** The cell calls `load_policy` on
the export (`saffron/cell/session.py:1934`), inside `_drive_cell`
(`:1859`). It resolves the gate executables at `:1942`. When the spec carries no `task_id`, it mints the
task with `ledger.create_task` at `:1969`. `_preflight` emits a
`Preflight` event (`:1879-1884`). `describe` renders a `Preflight` with
any other step as `preflight: <detail>` (`saffron/events.py:757-762`).
`create_task` is defined at `saffron/ledger.py:1365`. Its fact's payload
is a dict literal at `saffron/ledger.py:1401-1410`. The fold's insert reads named payload keys
only (`saffron/ledger.py:726-743`), so a new key folds to nothing.

## Problem

Delete `when` from `GateDeclaration` and `envelope_default` from
`Policy`. The models already forbid unknown keys, so each is then refused
at load.

Add a property, `shares_kernel`, to `Dialect`, with a short docstring.
Declare it above `unattended` in the protocol and in both dialects. The
module docstring calls the last two members the exception in kind
(`saffron/cell/runtimes/__init__.py:15-17`), and they stay last.
Apple/container's dialect returns `False`, since each cell is its own VM.
Podman's returns `True`. Cite the measurement each value rests on, in one
comment line. For podman that is the CPU count measured inside a cell, as its
docstring records it (`saffron/cell/runtimes/podman.py:62-69`), and the
evidence record's shared kernel
(`docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md:246-249`).
For apple/container it is the VM per cell (`docs/appendices/G-the-cell-runtime.md:34`),
beside the vCPU offset measured at `saffron/cell/runtimes/apple.py:31-33`. Add the member to
`test_every_declared_runtime_satisfies_the_dialect`
(`tests/test_runtime.py:226`).

After the policy loads in `_drive_cell`, decide whether the pool is
uncapped. That is the selected dialect's `shares_kernel`, and a
`thread_env` that holds no entries. An absent key and an empty map read
alike, since neither caps a pool. This repo's policy and the setup
skill's template both declare an empty map (`.saffron/policy.yaml:133`,
`.claude/skills/setup-saffron/templates/policy.yaml:33`). When the pool is
uncapped, emit one `Preflight` with step `thread_env`, naming the
runtime's binary and `thread_env`. Then run the task as before.

Give `create_task` a keyword parameter, `thread_pool_uncapped`, default
`None`. Write it into the `task_created` payload under that name.
`_drive_cell` passes the decision there. Every other caller passes
nothing, so their facts carry `None`.

Update what the change makes false or breaks:

- `tests/test_policy.py:14` declares `when` in `VALID`, and `:47` asserts
  it parses. Drop both.
- `tests/test_package.py:2161` declares `envelope_default` to change the
  policy's bytes. Declare `elevate_on: []` there instead.
- `test_a_field_the_skill_calls_unread_is_still_unread`
  (`tests/test_setup_saffron.py:174`) keeps its name and both parameters.
  `census_gate` fails a name collected at base and missing at head
  (`saffron/gates/core/census.py:41`). Rewrite its body. It asserts that
  neither the template nor `SKILL.md` holds the field's name in
  backticks. It checks the backticked form only, because `SKILL.md` uses
  the English word "when". Criterion 5 holds the template's YAML key.
- `.claude/skills/setup-saffron/templates/policy.yaml:10` calls `when`
  unread, and `:19-20` declare `envelope_default`. Remove both.
- `.claude/skills/setup-saffron/SKILL.md:41` says to declare a gate
  without `when`, and `:53` says `envelope_default` stays empty. Say
  instead that Saffron executes every declared gate on every task, and
  drop the second.
- `.claude/skills/setup-saffron/SKILL.md:55`, section E, tells an operator
  with no pool to skip `thread_env`. Add one sentence: on a runtime that
  shares the host kernel, an empty `thread_env` draws a warning on every
  task, and that is expected.

## Out of scope

- **Schema versions.** `SA-0283` owns them.
- **A task a stack batch mints.** `_stack_mint` creates its task before
  any policy is read (`saffron/cli.py:1108-1131`). Its fact carries
  `None`. The warning still fires when its cell loads the policy. Backlog
  item b-e9153f owns the record.
- **The `dead` allow entry for `envelope_default`.**
  `.saffron/deadcode-allow.py:12` names it, and `.saffron/**` is
  forbidden here. At `bc879e2c`, `dead` fails without that entry while
  the field exists. A person removes the entry once this spec lands. The
  entry names nothing afterwards, and `dead` passed with it in the
  prototype.
- **A `tasks` column.** Nothing reads the value from the ledger. The
  record is where it is read. `_TASKS_COLUMNS_NO_READER`
  (`tests/test_ledger.py:992`) lists the only columns allowed no reader.
- **`DESIGN.md`, `CONTEXT.md` and `.saffron/policy.yaml`.** Their lines on
  `when` and `envelope_default` are edited by hand with this spec. They
  describe the refusal before the cell lands it.
- **Conditional gates.** Item 19 offered two fixes, reading `when`
  against changed paths or refusing it. This spec takes the second.

## Notes for the agent

**Two paths sit under `.claude/`.** Your Edit and Write tools refuse a
path there. Write each of the two with a python3 script run through Bash,
which reads the file, replaces the exact text and writes it back.

**Witness and mutant.** Criteria 1 and 2 remove existing code, so each
declares a mutant that puts its field back. Criteria 3 and 4 add code
whose spelling is yours, so each declares a witness alone, and `witness`
reports `skip` for them. Criterion 5 preserves an existing test that the
template edit keeps green.

**Criterion 1** loads `VALID` with `when: "**/*.ttl"` put back on the
`shacl` gate. Assert `PolicyError` with a pattern matching the gate name
and then `when`, across lines.

**Criterion 2** loads `VALID` plus a top-level `envelope_default` set to
an empty list. The empty list is what kills the second wrong version.

**Criterion 3** compares with `is`, so a truthy stand-in fails.

**Criterion 4** drives `_drive` five times in one test, each in its own
directory (`tests/test_session.py:1350`). The record-backed pattern is
`test_the_task_created_fact_carries_the_cells_declared_tier_and_null_where_none`
(`tests/test_session.py:3857`). Per case:

- Set `runtime._selected` to the dialect and `runtime._admitted` to
  `True`. The autouse fixture `default_cell_runtime` selects
  apple/container for every unmarked test (`tests/conftest.py:52`). So a
  test that never sets `_selected` drives apple/container alone, and a
  check that ignores the runtime passes it.
- The stub VM dialect subclasses apple/container's and overrides
  `unattended` to return `False`. Both real dialects pair `unattended`
  with the opposite of `shares_kernel`, so only the stub kills a build
  that reads `not unattended`.
- Pass `policy=` to `_drive`. Its default is `"gates: {}\n"`, which has no
  `thread_env` key. Pass `capture=` and `record=MemoryRecord()`.
- Count `Preflight` events with step `thread_env`. Where one is expected,
  assert its detail holds `thread_env` and the dialect's `binary`. Assert
  the plan and implement turns ran, from `len(cell.turns)`. Read the
  `task_created` fact and compare `thread_pool_uncapped` with `is`.

**At the tree base each witness fails.** Both fields load. No dialect has
`shares_kernel`. No `thread_env` event exists and the payload has no such
key.

**`saffron/cell/**` and `saffron/ledger.py` are in `elevate_on`,** so this
task runs `elevated` and `size` blocks.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep `create_task`'s docstring within ten lines,
so explain the new key in a comment beside it.

**Size.** A prototype at `bc879e2c` measured 582 tokens with `size_gate`'s
counter, or 146 lines. It held every source edit in all six files, the four new
tests, the four test edits and both `.claude/` edits. Every wrong version above failed its witness there.
It was measured without the three parents, which move the lines it edits.
A margin of 54 lines for docstrings makes `estimated_lines` 200. The
`feature` ceiling is 3000 tokens.
