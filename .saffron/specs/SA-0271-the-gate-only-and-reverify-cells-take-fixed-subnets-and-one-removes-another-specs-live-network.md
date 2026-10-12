---
id: SA-0271
title: The gate-only cell and reverify's cells take fixed subnets, and the gate-only cell's pre-clean removes another spec's live network
type: feature
priority: 3
depends_on: [SA-0270, SA-0268]
consumes:
  - saffron/cell/runtime.py:allocate_network
estimated_lines: 520
estimate_measured: true
touches:
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/cell/session.py
  - saffron/cell/runtimes/podman.py
  - saffron/phases/package.py
  - saffron/preflight.py
  - saffron/task.py
  - tests/conftest.py
  - tests/test_session.py
  - tests/test_package.py
  - tests/test_runtime.py
  - tests/test_preflight.py
  - tests/test_events.py
  - tests/test_proxy.py
  - tests/test_worktree.py
  - tests/test_agent_runner.py
  - tests/test_review_cells.py
  - tests/test_cli.py
  - docs/evidence/scripts/2026-08-28-egress-nat-order.py
  - docs/evidence/scripts/2026-10-01-critic-cell-peer-reach.py
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
  - docs/backlog/**
  - docs/appendices/**
  - docs/adr/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/cli.py
  - saffron/scheduler.py
  - tests/test_scheduler.py
budget_usd: 36
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      Two gate-only cells of two specs can be up at once. Each claims its
      network from the pool with `allocate_network`, so their names and
      subnets are disjoint and each subnet lies inside `SUBNETS["pool"]`.
      The second one's pre-clean and its teardown leave the first one's
      network in place. A leftover under the second one's own name is still
      removed before its claim, and each one's teardown removes its own
      network. The witness brings both up through `critic_cell` with
      `network=None`, one inside the other, over a model of the runtime's
      networks.
    witness: tests/test_session.py::test_two_gate_only_cells_at_once_hold_disjoint_networks_and_neither_removes_the_other
    wrong_versions:
      - The gate network created on one fixed subnet, so the second create collides with the first.
      - The sweep kept, now over the pool, removing every `saffron-` holder on it before the claim.
      - The by-name pre-clean dropped, so a leftover under the cell's own name makes its claim raise.
      - The teardown's network removal dropped, so the second cell's network outlives it.
  - claim: >-
      Two reverify runs for two packaged commits can overlap. Each of
      reverify's two gate-only cells, baseline and head, claims its network
      from the pool with `allocate_network`. All four subnets the two runs
      claim lie inside `SUBNETS["pool"]`. The second run's networks are
      disjoint by name and subnet from the first run's live baseline
      network. The second run's pre-clean and teardown leave that network in
      place. A leftover under either cell's own network name is removed
      before that cell's claim, and every cell's teardown removes its own
      network. The witness starts the second run from inside the first
      run's baseline cell, over a model of the runtime's networks.
    witness: tests/test_package.py::test_two_reverify_runs_at_once_hold_disjoint_networks_and_neither_removes_the_other
    wrong_versions:
      - The network created on one fixed subnet, so the second run's create collides with the first's.
      - A pre-clean that removes every `saffron-pkg-` network on the pool, so the first run's live one goes.
      - No pre-clean by name, so a leftover under a cell's own network name makes its claim raise.
      - The teardown's network removal dropped.
      - The head cell claiming from the pool and the baseline cell still on a fixed subnet.
  - claim: >-
      No subnet is assumed any more. Each of these six parameters is
      required, with no default: `create_network`'s subnet,
      `container_ip`'s subnet prefix, `proxy.start_proxy`'s subnet, and the
      gateway of `probe_addresses`, `probe_host_bindings` and
      `assert_host_is_unreachable`. `runtime` defines none of
      `DEFAULT_SUBNET`, `SUBNET_PREFIX` and `GATEWAY`. `SUBNETS` has no
      "gate" key, and `session` defines no `_GATE_CELL_SUBNET`.
    witness: tests/test_runtime.py::test_every_network_call_names_its_subnet_and_no_default_subnet_is_left
    mutant:
      file: saffron/cell/runtime.py
      find: "def container_ip(name: str, subnet_prefix: str) -> str | None:"
      replace: "def container_ip(name: str, subnet_prefix: str = \"10.88.0.\") -> str | None:"
    wrong_versions:
      - One of the six parameters keeps a default, such as the gateway of `assert_host_is_unreachable`.
      - "`start_proxy`'s subnet defaults to a fixed subnet."
      - A default of `None` resolved to the old subnet inside the function.
      - "`DEFAULT_SUBNET`, `SUBNET_PREFIX` or `GATEWAY` kept as a constant nothing reads."
      - The "gate" entry left in `SUBNETS`.
  - claim: >-
      `allocate_network` admits the host once, before its walk. On a host
      the selected runtime refuses, it raises that refusal after one `info`
      call and no `network` call. When every /24 of the pool is refused,
      its error carries the last refused create's own error text, and not
      the first one's.
    witness: tests/test_runtime.py::test_allocate_network_admits_the_host_before_its_walk_and_names_the_last_refusal
    wrong_versions:
      - "`_admit` left to `create_network`, so the walk lists holders after the refusal and raises the pool as spent."
      - The walk catches the host's refusal like any refused create and moves to the next /24.
      - The exhaustion error names the holders and drops every refusal's text.
      - The exhaustion error carries the first refused create's text.
  - claim: >-
      `saffron package`'s host probe claims its network from the pool. The
      probe in `package_ready_task` claims `saffron-hostprobe-<spec id>` with
      `allocate_network`, and the subnet it gets lies inside
      `SUBNETS["pool"]`. It passes that subnet's gateway to
      `probe_addresses` and to `assert_host_is_unreachable`, both by
      keyword. A leftover under its own name is still removed before the
      claim, and its `finally` removes its network before `package()` runs.
      Another spec's live network on the pool survives the probe. The
      witness runs the command with another spec's network held in the
      model of the runtime's networks.
    witness: tests/test_cli.py::test_package_probe_claims_its_network_from_the_pool_and_probes_its_gateway
    wrong_versions:
      - The probe network created on a fixed subnet, so it collides with the held network.
      - The probe passing a gateway other than its claimed subnet's.
      - The by-name pre-clean dropped, so a leftover under the probe's name makes its claim raise.
      - The probe network left behind after `package()` runs.
---

## Context

Backlog item **b-ca3bc6**, with **b-6a692d**. It cites `DESIGN.md` §5.1
and §5.7. This is the last of three specs. `SA-0269` names the proxy and
every task network from the task. `SA-0270`, the parent, adds a pool to
`runtime.SUBNETS` and the function `allocate_network`. That function walks
the pool's /24s, claims one by creating the network on it, and returns the
subnet it claimed. It raises `CellRuntimeError` when the pool is spent. Read
both at the tree base before you start. `SA-0268`, the second entry in
`depends_on`, adds `saffron package`. Its cell lands first, so its code is
at your base too. Every line number below was read at
`60f8b3f5`, the parent's own base, in code the parent leaves alone.

**The gate-only cell takes one fixed subnet for every spec.** `critic_cell`
with `network=None` names its network from the spec id
(`saffron/cell/session.py:1393`). It creates it on `_GATE_CELL_SUBNET`
(`:1416`), which is `runtime.SUBNETS["gate"]` (`:1331`). Its pre-clean then
removes every `saffron-` network on that subnet (`:1405-1410`). So a second
spec's gate-only cell removes the first spec's live network. The test of
that sweep is
`test_the_gate_cells_pre_clean_removes_a_leftover_saffron_network_on_its_subnet_and_nothing_else`
(`tests/test_session.py:8314`).

**Reverify's cells take the default subnet.** `reverify`'s `_gate_cell`
names its network from the packaged commit (`saffron/phases/package.py:530-532`).
It creates it with `create_network(network)` (`:539`), so on
`DEFAULT_SUBNET`, `10.88.0.0/24` (`saffron/cell/runtime.py:161`, `:311`).
Any live network on that subnet makes the create fail. It pre-cleans
nothing, and removes the network in its `finally` (`:564-568`).

**The default subnet is still the default everywhere.** `create_network`
defaults its subnet to `DEFAULT_SUBNET` (`saffron/cell/runtime.py:311`).
`container_ip` defaults its prefix to `SUBNET_PREFIX` (`:618`).
`probe_addresses`, `probe_host_bindings` and `assert_host_is_unreachable`
default their gateway to `GATEWAY` (`saffron/preflight.py:158`, `:187`,
`:233`). In the last two it follows `ports`, which defaults to `None`
(`:186`, `:232`). `SUBNET_PREFIX` and `GATEWAY` are derived at
`saffron/cell/runtime.py:195-196`. `_NETWORK` is derived at
`saffron/cell/runtime.py:182`, and nothing reads it. At base, `start_proxy`
(`saffron/cell/proxy.py:51`) reads its own address with the default prefix
(`saffron/cell/proxy.py:69`). A comment names `DEFAULT_SUBNET` at
`saffron/cell/runtimes/podman.py:84`. A test reads `GATEWAY` at
`tests/test_events.py:1895` and `:1899`.

**What the parent leaves for you.** By its own text, `SA-0270` keeps
`DEFAULT_SUBNET`, `SUBNET_PREFIX`, `GATEWAY` and the "gate" entry. It makes
`start_proxy` take its subnet as a keyword. Its cell-marked callers of
`start_proxy` pass `DEFAULT_SUBNET`, since their networks are still
created on it. Its witness
`test_the_pool_is_declared_once_and_overlaps_no_fixed_subnet` checks that
the pool misses `DEFAULT_SUBNET`. Its `_stub_the_runtime` fake refuses a
create on a held subnet. Read each at the tree base.

**`census` fails a removed test name** (`saffron/gates/core/census.py:34-38`).
So an existing test whose subject goes keeps its name, and its body is
rewritten.

## Problem

Claim the gate-only cell's network with `allocate_network`, and delete the
sweep, `_GATE_CELL_SUBNET` and `SUBNETS["gate"]`. Keep the by-name pre-clean
of the cell's own network. Another spec's network is never removed.
Fix the docstring of `networks_on_subnet` (`saffron/cell/runtime.py:336`).
Its last lines say the Gate-only cell's pre-clean removes nothing (`:342-344`).
Once the sweep goes, that cell never reads it.

Claim each of reverify's two networks with `allocate_network`. Remove the
cell's own network by name before the claim, since a leftover under that
name would make the claim raise.

Then delete `DEFAULT_SUBNET`, `SUBNET_PREFIX`, `GATEWAY` and `_NETWORK`, and
drop each default above, so each caller names its subnet. A parameter with
no default cannot follow one with a default. So in the two probe functions
the gateway moves ahead of `ports`, and every caller follows. Any reader
of a removed name that the parent leaves names its subnet instead. Rewrite
the podman comment to name the subnet the host refused, `10.88.0.0/24`. One evidence script,
`docs/evidence/scripts/2026-08-28-egress-nat-order.py`, keeps the setup it
measured. It calls `runtime.create_network(NETWORK)` with no subnet (`:57`).
Pass the literal `"10.88.0.0/24"` there. Its `start_proxy` call
(`docs/evidence/scripts/2026-08-28-egress-nat-order.py:61`) takes it too.

If `start_proxy`'s `subnet` has a default at your base, drop it.

Call `preflight.assert_host_is_unreachable` at `saffron/cell/session.py:1109`
with `ports` and `gateway` by keyword. It passes them by position today. A
fake that keeps the old order would then swap the two in silence, and `ty`
cannot see it.

Rewrite three comments the change makes false. One is `_gate_cell`'s
comment that the name is ours to hold because `create_network` returns
`None` (`saffron/phases/package.py:533-534`). Another is `critic_cell`'s
docstring sentence on `_GATE_CELL_SUBNET`
(`saffron/cell/session.py:1363-1366`). The third is the parent's comment
above `SUBNETS`, which says PACKAGE still creates on `DEFAULT_SUBNET`.

In `allocate_network`, call `_admit()` once before the walk. A host refusal
then raises as itself, never as an exhausted pool. The exhaustion error also
carries the last refused create's own error text. The parent left both here
on size.

**`saffron package`'s host probe reads the names this spec deletes.**
`SA-0268` adds `package_ready_task` to `saffron/task.py`. Its probe creates
`saffron-hostprobe-<spec id>` with `runtime.create_network(name)` and no
subnet. It passes `runtime.GATEWAY` to `preflight.probe_addresses` and, by
position after `ports`, to `assert_host_is_unreachable`. Claim that network
with `allocate_network` and pass `runtime.gateway` of the claimed subnet to
both, by keyword. Keep its by-name pre-clean and its `finally` removal.
Read `package_ready_task` and its witnesses in `tests/test_cli.py` at the
tree base. Each witness that fakes `create_network` or records
`assert_host_is_unreachable`'s arguments keeps its name and takes the new
order. A wrong version in `SA-0268` names "the gate subnet", which this spec
deletes. Leave that spec's text alone.

## Out of scope

- **One spec in two cells at once.** The gate-only cell stays named from
  the spec id (b-d9ed45).
- **Batch concurrency.** b-a714d2, item 108, K above one and the spec loop
  driver.
- **Two `DESIGN.md` lines.** §5.1's worked example names `saffron-cells`,
  `saffron-proxy` and `10.88.0.0/24`. `DESIGN.md:680` says the one measured
  host refused `DEFAULT_SUBNET`, a name this spec deletes. Both are edited
  by hand with this spec.

## Notes for the agent

**Commit as each witness passes.** A cut-off attempt keeps the work.

**Witness and mutant.** Criteria 1, 2 and 4 declare a witness and no
mutant, so `witness` reports `skip` for them. Their code rests on
`allocate_network`, which the parent writes after this spec. Criterion 3
declares a mutant over a signature the change determines.

**A model of the runtime's networks.** Criteria 1 and 2 fake
`saffron.cell.runtime._call`, so the real `allocate_network` runs however
it reaches the runtime. Put the model in one fixture in `tests/conftest.py`,
not autouse. It keeps a name-to-subnet map. A create whose name is taken
fails with "already exists". A create whose subnet overlaps a held one
fails with a message holding "overlap". A listing prints a header row, then
one name and subnet per line, as `networks_on_subnet` parses them
(`saffron/cell/runtime.py:353-362`). A removal drops the name. Anything else
returns a clean success. `create_network` reads that wording at `:329-333`.

**Criterion 1** calls `critic_cell` directly, as
`test_critic_cell_creates_its_own_network_only_when_it_is_not_given_one`
does (`tests/test_session.py:7797`). Stub `prepare_worktree` and
`_apply_and_commit_patch`. Seed a leftover under the second spec's own
network name on a pool /24. Enter the first spec's cell, then the second's
inside it. Assert which names the model holds inside the second, after it,
and after the first.

**Criterion 2** drives `reverify` as `_reverify_stubbed` does
(`tests/test_package.py:261`), with its own stubs over the model in place
of `_stub_package_cells`. The first run's first `run_suite` call starts the
second run for another packaged commit. Guard that re-entry with a flag.
Seed a leftover under each of the second run's two network names. Record
the subnet each of the four cells claims, and assert each lies inside the
pool. The first run's head cell is never live beside the second run, so
only the pool check reaches its subnet.

**Criterion 3** reads each parameter with `inspect.signature` and asserts
its default is `inspect.Parameter.empty`. Import `proxy`, `preflight` and
`session` inside the test body.

**Criterion 5** drives `saffron package` as `SA-0268`'s witnesses do,
over the model of the runtime's networks. Seed another spec's network on a
pool /24 and a leftover under the probe's own name. Record the gateway each
probe call receives. Assert the probe's subnet lies inside the pool and
differs from the held one. Assert both probe calls received its gateway.
After the command, assert the held network survives and the probe's does
not.

**Criterion 4** is one test with two halves.

- Select podman as `_as_podman` does (`tests/test_runtime.py:95-107`). It
  sets `runtime._selected` and `runtime._admitted` and fakes `_call`.
  Answer `info` with "false", so the host is rootful. Answer a listing
  with a holder on every pool /24, and refuse every create. Record every
  argv. Assert `CellRuntimeError` with "rootful" in its text, which pins
  the refusal raising as itself. Assert exactly one argv whose second word
  is `info`, which pins one admission before the walk. Assert no argv
  whose second word is `network`, which pins that no create and no listing
  ran. Assert no holder's name is in the error, which pins that it is no
  exhausted pool. Unmarked tests run under apple/container, whose
  `host_refusal` returns `None` (`saffron/cell/runtimes/apple.py:56-58`).
  So only podman reaches the refusal.
- Under the default runtime, list a holder on every pool /24. Refuse each
  create with stderr carrying its own ordinal, such as `r1x` to `r256x`.
  Assert the error holds the last create's ordinal and not the first's.
  That pins the last refusal's text.

**At the tree base each witness fails.** The sweep removes the first
cell's network. Reverify's second create overlaps the first on the default
subnet. The defaults exist. `create_network` admits the host inside the
walk, and the exhaustion error carries no refusal's text.

**Existing tests that change.** Each keeps its name, since `census` fails
a removed one.

- The sweep test asserts that another spec's networks survive and its own
  leftover does not.
- The lens gate cell test asserts `10.90.0.0/24`
  (`tests/test_session.py:8146`). Assert the pool there instead.
- `test_critic_cell_creates_its_own_network_only_when_it_is_not_given_one`
  (`tests/test_session.py:7797`) asserts no overlap with `DEFAULT_SUBNET`
  at `:7847`. Assert the subnet lies inside the pool instead.
- `_stub_package_cells` stubs `create_network`
  (`tests/test_package.py:227-234`). The real `allocate_network` creates
  through that stub, so the first /24 succeeds with no runtime call.
  Stubbing `allocate_network` as well is optional.
- `test_every_subnet_saffron_allocates_is_declared_in_one_place`
  (`tests/test_runtime.py:685`) reads `SUBNETS["gate"]` and
  `_GATE_CELL_SUBNET` at `:709`, and `DEFAULT_SUBNET` at `:707` unless the
  parent changed that line. Its AST loop looks up `"_GATE_CELL_SUBNET"` by
  string at `:717`. `ty` cannot see that string or the dict key, and the
  loop fails only at run time, on `(value,) = []`. Drop the gate entry
  from both.
- `test_the_subnet_is_the_only_place_the_network_is_written`
  (`tests/test_runtime.py:502`) asserts `subnet_prefix` and `gateway` over
  one pool /24.
- The parent's pool test drops its `DEFAULT_SUBNET` half.
- Calls of `create_network` with no subnet, at `tests/test_runtime.py:148`,
  `:658` and `:761`.
- Calls of the probes with no gateway, at `tests/test_preflight.py:151`,
  `:197`, `:206` and `:237`. `saffron/preflight.py:236` calls
  `probe_host_bindings` by position too.
- Fakes whose defaults read a removed name. These are `_create_network` at
  `tests/test_session.py:1032`, `_container_ip` at `:7541`, and the
  `container_ip` lambda at `:7584`.
- The `_host` fake at `tests/test_session.py:7576`, and the parent's
  criterion 5 recorder of `assert_host_is_unreachable`. Each takes the
  gateway ahead of `ports`, and the call now passes both by keyword.
- `tests/test_events.py:1895` and `:1899` read `GATEWAY`. Use the gateway
  of a pool /24. The parent keeps `DEFAULT_SUBNET`'s gateway in
  `_GATEWAYS`. Drop it.
- Every `SA-0269` or `SA-0270` test that reads a removed name. The `types`
  gate checks `tests/` and `docs/`, so it names any attribute read you
  miss, but not a string.

**`cell`-marked tests, which you cannot run.** In `tests/test_proxy.py`,
the `network` fixture's `runtime.create_network(NETWORK)` (`:30-34`) now
claims a subnet and yields it with the name. Each
`preflight.probe_host_bindings` call (`:101`, `:124`) passes the gateway
ahead of `ports`. The same holds for `tests/test_worktree.py` (`:26-29`,
`:282`) and `tests/test_agent_runner.py` (`:422`, `:455`). A `cell`-marked
test claims its network with `allocate_network`, so a by-hand run beside a
live task never collides with it. `tests/test_review_cells.py` calls
neither probe nor `create_network`. Its two subnet readers at `:193` and
`:231` are the parent's to change. It sits in `touches` only for a reader
of a removed name the parent leaves. Only `ty` checks these files.

**The two-task test is not yours.** Write no
`tests/test_two_tasks_beside_each_other.py`. The delegate adds it by hand
as a review commit on this pull request. It brings two tasks up at once
with `cell_up` and probes each from the other. The operator then runs
`uv run pytest -m cell tests/test_proxy.py tests/test_worktree.py tests/test_agent_runner.py tests/test_review_cells.py tests/test_two_tasks_beside_each_other.py`
by hand before the pull request merges.

**`saffron/cell/**` is in `elevate_on`,** so this task runs `elevated` and
`size` blocks.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype over a stand-in for the parent's `allocate_network`,
at an emulated base, measured 1535 tokens with `size_gate`'s counter. Its
two-task file (408) and its `start_proxy` edit (12) are not this spec's.
That leaves 1115 tokens, or 279 lines. They cover the source edits,
criteria 1 to 3 and the conftest model. The rest is counted by hand. The
edits on the parent's real text come to about 95 lines. Criterion 4 and
its `_admit` and error edits add about 45. The `saffron package` probe and
criterion 5 add about 40, from `SA-0268`'s prototype, where the probe is
about 25 lines. The `start_proxy` default, the
keyword call, the three comments and the pool check add about 16. That
sums to 475 lines. A margin of 45 for comments makes `estimated_lines`
520, and the measured part is 54% of it. The `feature` ceiling is 3000
tokens.
