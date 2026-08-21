---
id: SA-0004
title: The anti-gaming gate is declared, parsed, and enforced by nothing
type: feature
priority: 1
touches:
  - saffron/gates/core/integrity.py
  - tests/test_integrity.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
budget_usd: 4.5
max_attempts: 4
risk: elevated
---

## Context
`DESIGN.md` §5.4 calls `integrity` the anti-gaming gate and states the failure
mode it exists for: *"The dominant failure mode of a hard-gate self-repair loop
is not the agent giving up; it is the agent making the gate pass"* — by deleting
a failing test, adding `@pytest.mark.skip`, sprinkling `# type: ignore`, or
loosening a threshold in gate configuration.

`.saffron/policy.yaml` already declares the vocabulary, and
`saffron/repos/policy.py` already parses it into `IntegrityPatterns`:

```yaml
integrity:
  test_paths:   ["tests/**"]
  suppressions: ["@pytest.mark.skip", "xfail", "# type: ignore", "# noqa"]
  gate_config:  ["pyproject.toml", ".saffron/**"]
```

`IntegrityPatterns`' own docstring says it is "Read in v0, acted on in v1 — the
`integrity` gate exists to catch an agent gaming a gate, and v0 has no agent."
There is an agent now.

## Problem
Nothing reads those patterns. An attempt that deletes a test to go green, or
adds a suppression comment to silence a type error, passes every gate in the
suite — and the repair loop's incentive is precisely to find that path, because
it is the cheapest route to a green suite.

## Acceptance criteria
- [ ] `saffron/gates/core/integrity.py` provides a gate over a unified diff and
      an `IntegrityPatterns`, returning a `GateResult` satisfying the contract
- [ ] Deleting or removing an existing test is a failure
- [ ] Adding any declared suppression token is a failure, and the failure names
      the file and the token
- [ ] Changing a file matched by `gate_config` is a failure
- [ ] Adding a *new* test is not a failure — the gate must not punish the thing
      the acceptance criteria of every other spec require
- [ ] A file's classification as a test comes from `test_paths`, never from a
      hardcoded path or a guess about the language
- [ ] The gate is `pass`/`fail` over a diff it can read; a diff it cannot parse
      is `error`, and the distinction is not blurred
- [ ] A regression test exists per criterion above, each with a realistic diff
      fixture rather than a synthetic one-liner

## Out of scope
Wiring the gate into `run_one_cell`'s suite. `scope` is wired and is the model
to follow, but doing both in one task conflates writing a gate with changing the
driver, and the driver is where a mistake is expensive.

Detecting a *loosened assertion* (`==` to `is not None`). §5.4 assigns that to
the `revert` gate, which is a different mechanism and a different task.

## Notes for the agent
`saffron/gates/core/scope.py` is the pattern for a core gate: it reads the diff
as text, executes no repo code, and owns its own glob matching. Follow its shape,
its docstring density, and its test style.

The split this gate embodies is `DESIGN.md` §2.1 in miniature — the *question*
("was a test removed or silenced?") is universal and belongs in core; the
*tokens* (`@pytest.mark.skip`, `tests/**`) are language-specific and arrive from
the repo's policy. Do not hardcode a token that `IntegrityPatterns` should supply,
and do not add a pattern field that `.saffron/policy.yaml` does not already
declare — that file is `forbidden` to you, so a gate needing a new field is a
gate that cannot be finished in this task. Say so rather than working around it.
