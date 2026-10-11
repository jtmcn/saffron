---
id: SA-0260
title: Every task cell and end-review cell joins a network and a proxy of one fixed name, so a second one started tears down the first
type: feature
priority: 3
depends_on: []
estimated_lines: 370
touches:
  - saffron/cell/proxy.py
  - saffron/cell/egress_report.py
  - saffron/cell/session.py
  - saffron/end_review.py
  - tests/test_proxy.py
  - tests/test_session.py
  - tests/test_end_review.py
  - tests/test_cli.py
  - tests/test_review_cells.py
  - tests/test_worktree.py
  - docs/evidence/scripts/2026-08-28-egress-nat-order.py
  - docs/evidence/scripts/2026-09-07-lens-scoring.py
  - docs/evidence/scripts/2026-09-08-lens-corpus.py
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
  - docs/adr/**
  - docs/appendices/**
  - docs/backlog/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cell/runtime.py
  - saffron/phases/**
  - saffron/gates/**
  - saffron/preflight.py
  - saffron/cli.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - tests/test_runtime.py
  - tests/test_preflight.py
  - tests/test_scheduler.py
budget_usd: 36
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `proxy.proxy_name` names a key's proxy `saffron-proxy-` followed by
      the key lowercased, so two keys get two names. `start_proxy`,
      `denied_egress`, `failed_egress` and `stop_proxy` each act on the
      proxy name they are given and on no other container. That covers the
      pre-clean and the address poll in `start_proxy`, the removal when no
      address comes, and the log read under both reports. The witness drives
      each of those for the keys "SA-1" and "SA-2" against a recording fake
      runtime.
    witness: tests/test_proxy.py::test_each_proxy_call_acts_on_the_proxy_it_is_named_and_no_other
    wrong_versions:
      - A name that keeps the key's case, so "SA-1" names "saffron-proxy-SA-1".
      - A `start_proxy` that pre-cleans the old fixed "saffron-proxy" before starting its own.
      - A `start_proxy` that removes a fixed name when no address comes.
      - A log read that names a fixed proxy, so both reports read one key's log for every key.
  - claim: >-
      `_drive_cell` names its cells network `saffron-cells-` and its critic
      network `saffron-critic-net-`, each followed by the spec id
      lowercased. It starts the proxy `proxy.proxy_name` gives the spec id,
      on exactly those two networks. It reads that proxy's two reports, stops
      it, and reads every proxy address from it, the critic cells' included. No network either task removes, in its pre-clean or its
      teardown, is one the other created, and neither removes a bare
      "saffron-cells" or "saffron-critic-net". The witness drives one whole
      task for "SY-1" and one for "SY-2", each through REVIEW.
    witness: tests/test_session.py::test_two_tasks_bring_up_and_tear_down_only_their_own_networks_and_proxy
    wrong_versions:
      - The cells network keyed by spec id and the critic network left as the fixed "saffron-critic-net".
      - A spec id left in its own case, which the fake runtime's `create_network` refuses.
      - A `cell_down` that also removes the bare "saffron-cells" as a leftover.
      - A `stop_proxy` or a report read handed a proxy name other than the one `start_proxy` was given.
      - A `proxy_address` that reads a fixed proxy name, so the critic cells' address comes from no task's own proxy.
  - claim: >-
      `end_review.layer_cell` brings a layer's cell up on
      `saffron-cells-endreview-` followed by the spec id lowercased. Its
      proxy is the one `proxy.proxy_name` gives `endreview-` and the spec
      id. Its teardown takes down that same network and proxy. That holds
      with `spec_session` false and with it true. The two layer cells share
      no network or proxy name. Neither shares one with the names
      `_drive_cell` gives the same spec id. Neither removes a network the
      other used. The witness opens "SA-1" with `spec_session` false and
      "SA-2" with it true.
    witness: tests/test_end_review.py::test_two_layer_cells_name_their_own_network_and_proxy_apart_from_any_task
    wrong_versions:
      - The fixed "saffron-cells" kept on the `spec_session` true branch alone.
      - A layer cell keyed by the bare spec id, so its names equal the task cell's for the same spec.
      - A teardown handed a proxy name other than the one `cell_up` was given.
  - claim: >-
      When the plan turn's first call is served nothing, the proxy state and
      proxy log the teardown reads are those of the task's own proxy. The
      witness drives that path once for "SY-1" and once for "SY-2". Each
      run's two reads name the proxy `proxy.proxy_name` gives its own spec
      id.
    witness: tests/test_session.py::test_the_egress_reads_name_each_tasks_own_proxy
    wrong_versions:
      - A `read_egress` that reads a fixed proxy name.
      - A `_drive_cell` that hands `read_egress` the proxy name of a fixed key.
---

## Context

Backlog item **b-ca3bc6**, filed reviewing #633. It also answers the naming
half of **b-6a692d**. Both cite `DESIGN.md` §5.1. This is the first of three
specs. `SA-0261` gives each task network its own subnet from one pool, and
`SA-0262` moves the Gate-only cell and PACKAGE's reverify onto that pool.
Every line number below was read at `60f8b3f5`.

**The proxy has one fixed name.** `PROXY_NAME` is `saffron-proxy`
(`saffron/cell/proxy.py:15`). `start_proxy` removes that container before
it starts one (`:54`). `stop_proxy` removes it (`:145-146`). `_proxy_log`
reads its log for both reports (`:109`). `proxy_address` reads the proxy's
address by that name (`saffron/cell/session.py:992-996`). The egress report
reads its state and log by that name too (`saffron/cell/egress_report.py:34-35`).

**Each task network takes a fixed name.** `_drive_cell` binds its cells
network to "saffron-cells" and its critic network to `CRITIC_NETWORK`
(`saffron/cell/session.py:1897-1898`), which is "saffron-critic-net"
(`:979`). `end_review.layer_cell` binds "saffron-cells" too
(`saffron/end_review.py:589`). Five sites in `saffron/cli.py` open a
cell through it. The end review's is `:709` and the spec review's is `:969`.

**So a second cell started tears down the first.** `cell_up` removes each
network it is given by name before it creates it
(`saffron/cell/session.py:1056-1065`). It then starts the proxy, whose
start removes the fixed one (`:1072`). `cell_down` stops the proxy and
removes both networks (`:1174-1179`). A layer cell opened beside a running
task therefore removes that task's proxy and network partway through. So
does a by-hand `pytest -m cell` run during a spec loop's cell.

## Problem

Name the proxy and every task network from the task.

- `saffron/cell/proxy.py` gains `proxy_name(key: str) -> str`, returning
  `saffron-proxy-` and the key lowercased. `PROXY_NAME` goes.
  `start_proxy`, `denied_egress`, `failed_egress`, `_proxy_log` and
  `stop_proxy` each take the proxy name as their first argument.
- `session.proxy_address` takes `(proxy_name, subnet)`.
  `egress_report.read_egress` takes the proxy name beside the container.
- `cell_up` and `cell_down` take a required keyword `proxy_name`, with no
  default, as `network` and `env` are required where a cell is created
  (`DESIGN.md` §5.1). Each pre-cleans and tears down only the networks it
  is given and that proxy. A leftover of the same name, from a SIGKILLed
  run of the same key, is still pre-cleaned by name.
- `_drive_cell` names its networks `saffron-cells-<id>` and
  `saffron-critic-net-<id>`, `<id>` being the spec id lowercased. Its
  proxy is `proxy_name(spec.spec_id)`. `CRITIC_NETWORK` goes.
- `layer_cell` names its network `saffron-cells-endreview-<id>` and its
  proxy `proxy_name("endreview-" + spec id)`.

Network names are lowercased because apple/container refuses an uppercase
one (`saffron/cell/session.py:1391-1393`).

**Subnets stay fixed, and that is the deliberate intermediate state.**
Every cells network still takes `runtime.DEFAULT_SUBNET` and every critic
network `runtime.SUBNETS["critic"]` (`saffron/cell/runtime.py:161-170`).
So a second task brought up beside a first now fails at its own
`create_network`. The runtime refuses an overlapping subnet, and
`create_network` raises naming the holder (`saffron/cell/runtime.py:329-333`,
measured as `:337-341` records). That failure is loud and leaves the first
task running, where today the second silently tears the first down. A
SIGKILLed task's leftover network now blocks the next task the same way,
since no later pre-clean names it. `SA-0261` removes both.

## Out of scope

- **Subnets.** `runtime.SUBNETS` and every subnet a network takes stay as
  they are. `SA-0261` and `SA-0262` own them.
- **The Gate-only cell and PACKAGE's reverify.** Each already names its
  network from its own spec or commit (`saffron/cell/session.py:1393`,
  `saffron/phases/package.py:530-532`). The sweep of every `saffron-`
  holder on the gate subnet (`saffron/cell/session.py:1408-1410`) stays.
  `SA-0262` removes it.
- **The egress network.** `saffron-egress` stays one network every proxy
  joins, created once and never removed (`saffron/cell/proxy.py:27-48`).
- **More than one cell at a time.** K stays 1 (`DESIGN.md` §4.2.1). No
  scheduler change, and no cell-marked test starting two tasks.
- **Backlog items b-a714d2, b-d9ed45 and 108**, and the spec loop's driver.
- **`DESIGN.md`.** Its §5.1 block names "saffron-cells" and "saffron-proxy"
  as one-time objects (`DESIGN.md:626-628`). It is edited by hand.

## Notes for the agent

**Commit as each witness passes**, so an attempt cut off keeps what it
finished.

**No mutant is declared.** Every line that carries a name is rewritten, so
no text at head is fixed by the code at base. Each criterion lists its
wrong versions instead, and `witness` reports `skip`.

**Every witness fails at base.** Each reads `proxy.proxy_name` in its
body. So the reverted run fails inside the test, not at collection.

**Criterion 1** goes in `tests/test_proxy.py` beside
`test_a_proxy_that_is_already_gone_reports_nothing_rather_than_its_error`.
Record every name `runtime.remove_container`, `runtime.run_detached` and
`runtime.container_ip` get, and every `runtime.call` argv. For each key,
start its proxy with an address, read both reports, then stop it. Then
start each again with `container_ip` answering `None` and `timeout_s=0`,
so it gives up and removes. Assert every name recorded under a key is
that key's proxy name, the `logs` argv included.

**Criterion 2** drives `_drive` twice in one plain test, each run with its
own `_stub_the_runtime` and its own `tmp_path` subdirectory. Use
`_spec(spec_id=..., branch=...)` and the turns
`test_the_critic_cell_is_not_on_the_implementers_network` uses, so REVIEW
runs. After `_stub_the_runtime`, replace `start_proxy`, `stop_proxy`,
`denied_egress`, `failed_egress` and `runtime.container_ip` with recorders.
`cell.networks_created` and `cell.removed` hold the rest.

**Criterion 3** follows
`test_only_a_spec_sessions_layer_cell_is_granted_capabilities_and_checked`
in `tests/test_end_review.py`. Record each `cell_up` and `cell_down`
keyword set, and every `runtime.remove_network` and
`runtime.remove_container` call.

**Criterion 4** follows
`test_a_first_call_the_provider_never_served_reports_the_proxy_and_the_cell_before_teardown`
and its `_rigged_cell`, once per spec id.

**`_CRITIC_SUBNET` stays** in `saffron/cell/session.py`, since
`tests/test_runtime.py:710` reads it and `SA-0261` replaces it.

**Existing tests that name the old values change with them.**

- `tests/test_session.py`: 1098-1118, 1780, 1915-1916, 6480 and 7021-7022.
- `tests/test_session.py` again: 7550-7551, 7566-7601, 8200, 10653-10655
  and 11054-11069.
- `tests/test_cli.py`: the `_fake_cell_up` and `_fake_cell_down`
  signatures at 3750, 5653 and 6507 take the new keyword.
- `tests/test_end_review.py:1439` and `tests/test_review_cells.py:169-257`.
- `tests/test_worktree.py:282-305` and every `proxy.` call in
  `tests/test_proxy.py`.
- The four evidence scripts in `touches` call what changes, and `ty`
  checks `docs/`.

**`saffron/cell/**` is in `elevate_on`**, so this task runs `elevated` and
`size` blocks. The estimate is about 90 lines of source, 90 of edited
tests and 190 of new witnesses.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words.
