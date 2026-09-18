# Code that nothing calls

2026-09-18. Designed with the operator.

**Status:** designed, not built.

## Why

Nothing in Saffron measures code that no caller reaches. Ruff's `F` rules catch
unused imports and locals inside one file. They cannot see a function that no
other module calls. A cell can add such a function, and every gate passes.

## Measurements

From commit `66c71ca` with vulture 2.16 at `--min-confidence 60`, over
`saffron/ harness/ images/ .saffron/gates/`:

| Kind      | Count |
| --------- | ----- |
| variable  | 31    |
| function  | 16    |
| method    | 6     |
| property  | 1     |
| attribute | 1     |
| **total** | 55    |

With `tests/` counted as callers, the total is 37. So 18 symbols are called
only by tests. At `--min-confidence 100` the count is 0.

A spike with ast-grep found 10 of vulture's 22 unused functions and methods.
ast-grep matches one node in one file and has no project-wide symbol table.
Matching vulture means rebuilding its name tables, so ast-grep was rejected.

## Decisions

1. **Dead means no production caller.** Only `saffron/`, `harness/`, `images/`
   and `.saffron/gates/` are scanned. A symbol that only a test calls is dead.
2. **The gate blocks new dead code only.** It fails at base as well, and the
   baseline subtraction (§5.4) means a task fails only when it adds a finding.
   The count can only go down.
3. **An open spec can defer a symbol.** A spec lists the symbols it will bring
   into use under `pending_symbols`. The deferral ends when the spec moves to
   `.saffron/specs/done/`.
4. **Vulture, pinned.** It is one line in `dev`, like `ast-grep-cli`.

## Design

### The `dead` gate

`.saffron/gates/dead` is a `sh` wrapper that runs `dead.py`, in the same form
as `structure`. `dead.py` uses the stdlib only.

1. Run `vulture --version`. Its output fills `tool` (§5.4, Appendix H).
2. Run vulture over the four roots at `--min-confidence 60`, with
   `.saffron/deadcode-allow.py` as its whitelist.
3. Parse each line into a failure. The identity is the file, the kind and the
   name. The line number and the confidence are in the message and are never
   part of the identity.
4. Remove each finding that an open spec lists in `pending_symbols`.
5. Add a failure for each stale `pending_symbols` entry (see below).

`.saffron/policy.yaml` declares `dead: { blocking: true }`.

### `pending_symbols`

A new optional field on `Spec` in `saffron/intake.py`. `Spec` sets
`extra="forbid"`, so without the field a spec that uses it does not parse.

```yaml
pending_symbols:
  - saffron/events.py::GateResult
```

An entry is `<path>::<name>`, which is what vulture reports. A method is
named by its bare name, because vulture reports no class.

`dead.py` reads the field from the frontmatter of each `.saffron/specs/*.md`
itself. It does not import `saffron.intake`, because a cell can edit that file
and `.saffron/**` is protected.

An entry is stale when its file has no definition of that name, or when
vulture does not report it. A stale entry is a `fail`, so the list cannot turn
into a permanent allowlist.

### False positives

`.saffron/deadcode-allow.py` holds vulture's whitelist. Examples are pydantic
validators, `typer` commands and the entry point of `images/agent_runner.py`.
Each entry carries a one-line reason. The file is under `.saffron/**`, so a
cell cannot add to it.

### Errors

`error`, never `fail`, when:

- vulture is missing, cannot run or reports no version,
- vulture exits with a code other than 0 or 3 (3 means it found dead code),
- a spec's frontmatter does not parse.

### Tracking

`make deadcode` prints the findings and the count. One backlog record holds
the count from this document and the triage list, and is updated as the count
goes down.

## Delivery

Two stacked pull requests.

1. **The gate.** `dead.py`, its wrapper, the policy line, `pending_symbols`,
   an empty whitelist, the pinned dependency, the `.saffron/Dockerfile`
   version check, `make deadcode` and the backlog record. The 55 findings
   stay as baseline.
2. **The triage.** Each of the 55 is removed, moved into a spec's
   `pending_symbols`, or whitelisted with its reason.

## Testing

`tests/test_dead_gate.py` runs the gate over a fixture tree.

- A new dead function is a `fail`.
- A function that only a test calls is a `fail`.
- A function listed in an open spec's `pending_symbols` passes.
- The same entry in a spec under `done/` does not exempt it.
- A stale entry is a `fail`.
- A missing vulture binary is an `error`.
- The identity does not change when the line number changes.

Each test is run against a mutant that breaks what it guards before it is
trusted. `tests/test_intake.py` covers the new field and a malformed entry.
