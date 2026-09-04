---
id: SA-0048
title: preflight is paid per task, and the check that would catch a dead token does not exist
type: feature
priority: 1
depends_on:
  - SA-0046
touches:
  - saffron/preflight.py
  - saffron/cli.py
  - tests/test_preflight.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/replay.py
budget_usd: 12
max_attempts: 3
max_turns: 90
risk: standard
acceptance:
  - claim: >-
      One entry point performs a night's readiness in the order §4.2.1 gives —
      auth, mirror fetch, origin refusal, default-branch pin, policy
      validation, disk headroom — and returns a result naming which check
      failed rather than a bare boolean. A caller can skip the repo and say why
      (§4.4 step 1: a repo that fails preflight is skipped, not fatal). The
      order is asserted, not merely documented: a disk check that runs before
      the auth check spends a mirror fetch to learn something free.
    witness: tests/test_preflight.py::test_readiness_runs_its_checks_in_the_order_4_2_1_gives
  - claim: >-
      A policy that does not parse or names a gate whose executable is missing
      fails readiness before the night starts, rather than being discovered by
      the first cell after an image build. This is the other half of §4.2.1's
      "plus two", and it is the half a repo gets wrong while onboarding.
    witness: tests/test_preflight.py::test_a_policy_that_does_not_load_fails_readiness
  - claim: >-
      A token that is present but not valid is refused. Presence alone is what
      is checked today, and Appendix J measured the failure that hides behind
      it: a cell whose agent cannot authenticate returns success with
      is_error true and zero cost, so an expired token at 22:00 buys a night of
      clean-looking nothing against a budget that never counts down. The
      validity probe is injected, so no test reaches the network.
    witness: tests/test_preflight.py::test_a_present_but_invalid_token_fails_readiness
  - claim: >-
      An empty or whitespace token fails, not merely an absent one — the
      distinction the existing presence check already makes with strip(), kept
      rather than re-derived.
    witness: tests/test_preflight.py::test_a_whitespace_token_fails_readiness
  - claim: >-
      A check that cannot execute reports failure rather than passing. The rule
      host_probe_ports already follows: a probe that covers nothing is not a
      probe that passed.
    witness: tests/test_preflight.py::test_a_check_that_cannot_run_is_a_failure_not_a_pass
  - claim: >-
      Disk headroom is checked on the filesystem that actually fills — the one
      holding the batch tree and the runtime's volumes — against a named
      constant whose comment says what it was chosen against. Nothing checks it
      today, and §4.2.1 refuses to defer the detection alongside the
      reclamation it pairs with, because that turns a warned failure into a
      silent one.
    witness: tests/test_preflight.py::test_insufficient_disk_headroom_fails_readiness
  - claim: >-
      Running one cell still prepares itself in the same order after the hoist —
      the token refusal before the mirror fetch, and the mirror, the origin
      refusal and the default-branch pin all before a cell starts. Asserted on
      the ordering, not on a return code: a smoke test that only checks the exit
      would pass while the refusal moved after the money.
    witness: tests/test_cli.py::test_one_cell_still_prepares_itself_in_order_after_the_hoist
---

## Context

§4.2.1: *"Preflight is what a task already does, hoisted, plus two. `_run_cell`
today does the mirror fetch, the origin refusal and the default-branch pin per
task; a batch does them once per run. Added: `load_policy` validation, and an
auth check."*

**The auth check is not hygiene. It guards a measured landmine.** Appendix J
found that a cell whose agent cannot authenticate returns `subtype: "success"`,
`is_error: true`, `total_cost_usd: 0.0`. Unattended, an expired token at 22:00
produces a night of clean-looking nothing against a budget that never counts
down — the worst failure mode in the design, because every other failure at
least reports itself.

§4.2.1 also refuses to defer the disk-headroom check alongside `saffron gc`:
*"with gc deferred the accumulation is still unbounded, so dropping the
detection as well turns a warned failure into a silent one."*

## Problem

- **Per-task preparation is paid per task.** The mirror fetch, the origin
  refusal and the default-branch pin run on every invocation. A night pays them
  once.
- **Only the token's *presence* is checked.** `cli.py:348` refuses an unset or
  whitespace token, which is right and is not the failure Appendix J measured.
  A present, expired token passes that check and buys the silent night.
- **Nothing checks disk.** Measured: no `statvfs`, no `disk_usage`, nothing.
- **A repo that fails cannot be skipped.** The presence check raises, so there
  is no result a caller could record and step over.

## Out of scope

**Calling it from a batch.** `SA-0049`. This builds the check; the loop runs it
once per repo and records the skip.

**`saffron gc` (§4.5).** Deferred at K=1 deliberately. The disk *check* is not
deferred with it, and that pairing is the point.

**The host-binding probes.** `assert_host_is_unreachable` and
`assert_proxy_reaches_upstream` are properties of a container that does not
exist until a task starts. They stay per-cell.

**Changing what any existing check tests.** This hoists and adds; it does not
alter a probe's meaning.

**The ledger.** `saffron/ledger.py` is `forbidden`. Recording a preflight
outcome against a run is a different spec.

## Notes for the agent

**Four existing tests already pin what witness 7 asserts, and they are the
regression risk.** `tests/test_cli.py` is in `touches`, so they can be edited —
they must not be weakened. One of them monkeypatches `ensure_mirror` *by
dotted string* through `saffron.cli`'s namespace, so a hoist that moves the
mirror fetch out of that namespace breaks the patch target. Repoint the patch;
do not delete the test. The others pin the non-forge origin refusal firing
before the cell starts, the base being the remote default branch rather than
the checkout, and a setup failure exiting `2`.

**Do not move the origin refusal's timing.** `_run_cell` reads `github_slug`
*for its refusal, not its value*, and the comment says why: PACKAGE needs the
slug and only reaches it after the budget is spent. Hoisting it must keep it
before the money, not after.

**The validity probe must be injectable, and no test may reach the network.**
Take a callable the way `scheduler.build_queue` takes `gh` and
`phases/package.py` takes its runner — the shape this repo already uses three
times for exactly this reason, with a real default bound as a keyword. Stdlib
`urllib` reaches the upstream; no new dependency, which matters because
`pyproject.toml` is not in `touches`.

**There is already a function in this module that hits the same URL and treats
the opposite answer as success. Do not reuse it.**
`assert_proxy_reaches_upstream` probes the upstream and its comment says a
`401` *is a pass* — "the route is what is being established, not a credential."
That is exactly inverted from this check, which exists to fail on a credential
the route accepted a connection for. Two functions, one host, opposite
verdicts: say so in a comment beside the new one, or the next reader collapses
them.

**Assert the default probe's request shape without sending it.** With the probe
injected everywhere, the real one is exercised by no test — which is Appendix
H's vacuous pass, in the check written against it, and this module already
names that failure. Assert the URL and the header the default builds.

**No new test may carry the `cell` marker.** `pyproject.toml` sets
`addopts = "-m 'not cell'"` and the `tests` gate passes the same argv to
`--collect-only` deliberately, so a cell-marked witness is never collected at
head, `criteria` reports `witness-not-collected`, and the attempt is spent on a
test that was correct.

**It goes in `saffron/preflight.py`.** Not "somewhere sensible": that is the
only module `touches` permits, and `scope` fails a *created* file exactly as it
fails an edited one, so a new `saffron/readiness.py` loses the attempt with no
legal repair. `preflight.py` is also the name that already means this and the
word §4.2.1 uses.

Read `host_probe_ports` first — it is the worked example of the fourth witness,
raising rather than covering nothing when `lsof` cannot be read.

**The sixth witness is about not breaking things, and it is a new test.** It
asserts the single-cell path still prepares itself after the hoist.
`preserves: false` is correct despite the claim reading like preservation: a
new test cannot preserve, because it did not pass at base. Flipping it to
`true` fails with `witness-not-preserved`.

**`saffron cell` calls the hoisted preparation only — never the full
readiness — and this is the sentence that decides the spec.** The auth-validity
probe and the disk check are reached through the readiness entry point, whose
first caller is `SA-0049`. Wiring `_run_cell` to the whole thing would fire a
network probe in every test in `tests/test_cli.py`: its `a_token` fixture is
`autouse` and sets a fake token, and `tests/conftest.py`'s tripwire blocks the
cell runtime and `gh` at the subprocess boundary but does not block `urllib`.
That fixture must keep working untouched.

**Do not add a `--check-only` flag or any new subcommand.** `saffron/cli.py` is
in `touches` for the hoist, not for new surface. The command that runs a night
is `SA-0050`'s.
