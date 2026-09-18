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
   baseline subtraction (§5.4) means a task fails only when it adds a failure.
   A task can add dead code only through an entry a person wrote: a
   `pending_symbols` entry or a whitelist entry.
3. **An open spec can defer a symbol.** A spec lists the symbols it will bring
   into use under `pending_symbols`. The deferral ends when the spec moves to
   `.saffron/specs/done/`. The main case is a spec whose child spec calls what
   it adds.
4. **Vulture, pinned.** It is one line in `dev`, like `ast-grep-cli`.

## Design

### The `dead` gate

`.saffron/gates/dead` is a `sh` wrapper that runs `dead.py`, in the same form
as `structure`.

1. Run `vulture --version`. Its output fills `tool` (§5.4, Appendix H).
2. Run vulture over the four roots at `--min-confidence 60`, with
   `.saffron/deadcode-allow.py` as its whitelist.
3. Parse each line of the form `path:line: unused <kind> '<name>' (N%
   confidence)` into a failure. `file` is the path, `code` is `unused-<kind>`
   and `message` is vulture's text.
4. Drop each failure that an open spec lists in `pending_symbols`.

The identity is `contract.identity`: gate, file, code and the normalized
message. Normalization turns digits into `N`, so the line and the confidence
drop out. Two names that differ only in digits in one file share an identity.
The count-aware subtraction keeps both.

`.saffron/policy.yaml` declares `dead: { blocking: true }`.

### `pending_symbols`

A new optional field on `Spec` in `saffron/intake.py`. `Spec` sets
`extra="forbid"`, so without the field a spec that uses it does not parse.

```yaml
pending_symbols:
  - saffron/events.py::GateResult
```

An entry is `<path>::<name>`. `dead.py` builds the same form from each vulture
line and compares the two. A `ponytail:` note in `dead.py` names the ceiling:
vulture reports no class, so an entry naming a method exempts every method of
that name in the file.

`dead.py` reads the field from each `.saffron/specs/*.md` with `yaml.safe_load`,
which is what `intake.py` uses. It imports pyyaml after the version probe, as
`shacl.py` imports rdflib. It does not import `saffron.intake`, because a cell
can edit that file. A test asserts that both readers return the same entries
for every spec in the tree.

An entry is **stale** when vulture does not report its symbol. That covers a
symbol that has a caller, one that does not exist, and one the whitelist
already covers. A stale entry does not fail the gate. The task that implements
a spec is the one that gives its entries a caller, and its spec stays open
until it is moved to `done/` after merge (`RETIRED_DIRNAME`,
`saffron/scheduler.py:499`). A gate is not told which spec
its task runs, so a failing stale rule would fail that task. `make deadcode`
lists stale entries instead.

### False positives

`.saffron/deadcode-allow.py` holds vulture's whitelist. Examples are pydantic
validators, `typer` commands and the entry point of `images/agent_runner.py`.
Each entry carries a one-line reason. `integrity` fails a change to a file
under `.saffron/**` unless the task's spec declares it in `touches`, and a
person writes the spec.

The whitelist is bare expressions. It is excluded from ruff and ty in
`pyproject.toml`, or `lint` and `types` report it (F821, B018).

### Errors

`error`, never `fail`, when:

- vulture is missing, cannot run or reports no version,
- vulture exits with a code other than 0 or 3 (3 means it reported dead code),
- pyyaml cannot be imported,
- a spec's frontmatter does not parse.

### Tracking

`make deadcode` prints the failures, the count and the stale entries. One
backlog record holds the count from this document and the triage list, and is
updated as the count goes down.

## Delivery

Two stacked pull requests.

1. **The gate.** `dead.py`, its wrapper, the policy line, `pending_symbols` on
   `Spec`, the field in `docs/agents/issue-tracker.md`, an empty whitelist and
   its ruff and ty exclusions, the pinned dependency, the `.saffron/Dockerfile`
   version check, `make deadcode` and the backlog record. The 55 failures stay
   as baseline.
2. **The triage.** Each of the 55 is removed, moved into a spec's
   `pending_symbols`, or whitelisted with its reason. `harness/` functions that
   only `docs/evidence/scripts/` calls will appear here. Each one is
   whitelisted or its caller is moved.

## Not in this design

The `spec-reviewer` agent is not taught to check `pending_symbols`. A missing
entry shows up as a `dead` failure in the task that adds the symbol, and the
fix is a one-line spec edit.

## Testing

`tests/test_dead_gate.py` runs the gate over a fixture tree.

- A new dead function is a `fail`.
- A function that only a test calls is a `fail`.
- A function listed in an open spec's `pending_symbols` passes.
- The same entry in a spec under `done/` does not exempt it.
- A stale entry passes, and `make deadcode` lists it.
- A missing vulture binary is an `error`.
- The identity does not change when the line number changes.
- `dead.py` and `intake.py` read the same entries from every spec in the tree.

Each test is run against a mutant that breaks what it guards before it is
trusted. `tests/test_intake.py` covers the new field and a malformed entry.
