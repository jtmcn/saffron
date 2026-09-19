# Dead-code gate implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a blocking `dead` gate that fails a task which adds code no production caller reaches, then triage the 55 symbols already there.

**Architecture:** `.saffron/gates/dead.py` runs vulture over the production roots and turns each line into a gate-contract failure. An open spec's `pending_symbols` defers a symbol. The baseline subtraction (§5.4) makes the gate block only new failures.

**Tech Stack:** Python 3.12, vulture 2.16, pyyaml, pydantic, pytest.

**Spec:** `docs/superpowers/specs/2026-09-18-dead-code-gate-design.md`

## Global Constraints

- Scan roots: `saffron`, `harness`, `images`, `.saffron/gates`. `tests/` is never a root.
- `--min-confidence 60`.
- vulture pinned `vulture==2.16` in `[dependency-groups] dev`.
- vulture exit 0 is clean and 3 is dead code found. Any other exit is `error`.
- A pending entry is `<path>::<name>` and matches `^[^\s:]+::[A-Za-z_][A-Za-z0-9_]*$`.
- Only `.saffron/specs/*.md` is read. `.saffron/specs/done/` is never read.
- A stale pending entry never fails the gate.
- `error` never collapses into `fail` (CLAUDE.md).
- No integrity suppression token in any new line: no `# noqa`, no `# type: ignore`, no skip or `importorskip`. Describe a token, never quote one.
- Comments are one or two lines. Function docstrings stay within ten lines (`prose` gate).
- Commit subjects are lowercase `type(scope): <sentence about the defect>`. No co-author line.
- Branch: tasks 1 to 6 on `joel/dead-code-gate`. Task 7 on a branch stacked on it with `gh stack`.

---

## File map

| File | Change | Responsibility |
| --- | --- | --- |
| `saffron/intake.py` | modify | `Spec.pending_symbols` |
| `tests/test_intake.py` | modify | the field's tests |
| `docs/agents/issue-tracker.md` | modify | document the field |
| `pyproject.toml` | modify | pin vulture, exclude the whitelist from ruff and ty |
| `uv.lock` | regenerate | the pin |
| `.saffron/Dockerfile` | modify | run `vulture --version` at build |
| `.saffron/deadcode-allow.py` | create | vulture whitelist |
| `.saffron/gates/dead.py` | create | the gate |
| `.saffron/gates/dead` | create | `sh` wrapper |
| `.saffron/policy.yaml` | modify | declare `dead` |
| `tests/test_dead_gate.py` | create | the gate's tests |
| `tests/test_saffron_gates.py` | modify | the declared gate set |
| `Makefile` | modify | `make deadcode` |
| `docs/backlog/<new-id>-*.md` | create | tracking record |

---

### Task 1: `pending_symbols` on `Spec`

**Files:**
- Modify: `saffron/intake.py:16` (imports) and `saffron/intake.py:122-146` (`Spec`)
- Modify: `docs/agents/issue-tracker.md` (the **Frontmatter** bullet)
- Test: `tests/test_intake.py`

**Interfaces:**
- Produces: `Spec.pending_symbols: list[str]`, default `[]`. Each entry matches `PENDING_SYMBOL = r"^[^\s:]+::[A-Za-z_][A-Za-z0-9_]*$"`, a module constant in `saffron/intake.py`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_intake.py`)

```python
def test_a_spec_defers_the_symbols_it_will_bring_into_use():
    spec = parse_spec(
        "---\nid: TE-1\ntitle: t\ntype: chore\n"
        "pending_symbols:\n  - saffron/events.py::GateResult\n---\n"
    )
    assert spec.pending_symbols == ["saffron/events.py::GateResult"]


def test_a_spec_defers_nothing_by_default():
    assert parse_spec("---\nid: TE-1\ntitle: t\ntype: chore\n---\n").pending_symbols == []


@pytest.mark.parametrize(
    "entry", ["GateResult", "saffron/events.py:GateResult", "saffron/events.py::1x", "a b::c"]
)
def test_a_pending_symbol_not_of_the_form_path_and_name_is_rejected(entry):
    with pytest.raises(SpecError):
        parse_spec(f"---\nid: TE-1\ntitle: t\ntype: chore\npending_symbols: ['{entry}']\n---\n")
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/test_intake.py -k "pending or defers" -v`
Expected: the first and third FAIL with `SpecError` (an unknown key is refused). The second FAILS with `AttributeError`.

- [ ] **Step 3: Add the field**

In `saffron/intake.py`, add `Annotated` to the `typing` import and `StringConstraints` to the pydantic import:

```python
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)
```

Below `_FRONTMATTER`, add:

```python
# What vulture reports, as `.saffron/gates/dead.py` keys it; that script reads this field itself.
PENDING_SYMBOL = r"^[^\s:]+::[A-Za-z_][A-Za-z0-9_]*$"
```

In `Spec`, after `forbidden`:

```python
    # Dead symbols this spec will bring into use; the `dead` gate skips them while it is open.
    pending_symbols: list[Annotated[str, StringConstraints(pattern=PENDING_SYMBOL)]] = Field(
        default_factory=list
    )
```

- [ ] **Step 4: Run them and see them pass**

Run: `uv run pytest tests/test_intake.py -v`
Expected: all PASS.

- [ ] **Step 5: Mutant check**

Change `PENDING_SYMBOL` to `r".*"`. Run `uv run pytest tests/test_intake.py -k rejected -v`. Expected: the parametrized test FAILS for all four entries. Revert.

- [ ] **Step 6: Document the field**

In `docs/agents/issue-tracker.md`, in the **Frontmatter** bullet, change `` `depends_on`, `envelope`, `touches` and `forbidden` empty`` to `` `depends_on`, `envelope`, `touches`, `forbidden` and `pending_symbols` empty``. Add this bullet after the **Frontmatter** bullet:

```markdown
- **`pending_symbols`** lists dead code this spec will bring into use, one
  `<path>::<name>` per entry (`saffron/events.py::GateResult`). The `dead` gate
  skips each one while the spec is open, so a parent spec can add what only its
  child calls. A method is named without its class.
```

- [ ] **Step 7: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS. A failure in a test that pins `Spec`'s fields means that list needs `pending_symbols` added.

- [ ] **Step 8: Commit**

```bash
git add saffron/intake.py tests/test_intake.py docs/agents/issue-tracker.md
git commit -m "feat(intake): a spec had no way to name the dead code it will bring into use"
```

---

### Task 2: vulture, the whitelist and their exclusions

**Files:**
- Modify: `pyproject.toml` (`dev` list, `[tool.ruff] extend-exclude`, new `[tool.ty.src]`)
- Modify: `uv.lock`
- Modify: `.saffron/Dockerfile:38-41`
- Create: `.saffron/deadcode-allow.py`
- Test: `tests/test_saffron_gates.py`

**Interfaces:**
- Produces: `vulture` on the venv's PATH. `.saffron/deadcode-allow.py` exists.

- [ ] **Step 1: Write the failing test** (append to `tests/test_saffron_gates.py`)

```python
def test_the_dead_code_whitelist_is_kept_from_the_linter_and_the_type_checker():
    """vulture's whitelist is bare `_.name` lines, which ruff and ty both reject."""
    config = tomllib.loads((REPO / "pyproject.toml").read_text())
    assert ".saffron/deadcode-allow.py" in config["tool"]["ruff"]["extend-exclude"]
    assert ".saffron/deadcode-allow.py" in config["tool"]["ty"]["src"]["exclude"]
```

- [ ] **Step 2: Run it and see it fail**

Run: `uv run pytest tests/test_saffron_gates.py -k whitelist -v`
Expected: FAIL with `AssertionError` on the ruff line.

- [ ] **Step 3: Pin vulture**

In `pyproject.toml` `dev`, after `"ast-grep-cli==0.45.3",`, add `"vulture==2.16",`. In the comment above `dev`, extend the pinning sentence: `ast-grep-cli is pinned for the same reason` becomes `ast-grep-cli and vulture are pinned for the same reason`, and `the structure gate parses its JSON` becomes `the structure and dead gates parse their output`.

Run: `uv lock && uv sync`
Expected: `uv run vulture --version` prints `vulture 2.16`.

- [ ] **Step 4: Create the whitelist**

`.saffron/deadcode-allow.py`:

```python
# vulture's whitelist for the `dead` gate: one `_.name` per line, each with its reason.
# A person writes it: `integrity` fails a cell's change here unless its spec names the file.
```

- [ ] **Step 5: Exclude it**

In `pyproject.toml`, change `extend-exclude = ["docs", ".saffron/specs"]` to:

```toml
extend-exclude = ["docs", ".saffron/specs", ".saffron/deadcode-allow.py"]
```

After the `[tool.ty.environment]` table, add:

```toml
# vulture's whitelist is bare `_.name` expressions, never imported.
[tool.ty.src]
exclude = [".saffron/deadcode-allow.py"]
```

- [ ] **Step 6: Verify the exclusions with a real entry**

Temporarily append `_.visible_cpus  # probe` to `.saffron/deadcode-allow.py`.
Run: `uv run ruff check . && uv run ty check`
Expected: both clean. Remove the probe line.

- [ ] **Step 7: Check vulture at image build**

In `.saffron/Dockerfile`, change ` && ast-grep --version \` to:

```dockerfile
 && ast-grep --version \
 && vulture --version \
```

- [ ] **Step 8: Run the test and see it pass**

Run: `uv run pytest tests/test_saffron_gates.py -k whitelist -v`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock .saffron/Dockerfile .saffron/deadcode-allow.py tests/test_saffron_gates.py
git commit -m "build(gates): nothing that could see an uncalled function was installed in a cell"
```

---

### Task 3: `dead.py`'s parser and spec reader

**Files:**
- Create: `.saffron/gates/dead.py` (functions only here, `main` in Task 4)
- Test: `tests/test_dead_gate.py`

**Interfaces:**
- Consumes: `saffron.intake.parse_spec` and `PENDING_SYMBOL` (Task 1), in tests only.
- Produces, in `dead.py`:
  - `@dataclass(frozen=True) class Unused: file: str; line: int; code: str; message: str; name: str | None` with property `symbol -> str | None` returning `f"{file}::{name}"`, or `None` when `name` is `None`.
  - `parse(stdout: str) -> list[Unused]`. Raises `ValueError` on a line it cannot read.
  - `entries(text: str) -> list[str]`. One spec's `pending_symbols`. Raises `ValueError` on bad frontmatter or a bad entry, and `ImportError` without pyyaml.
  - `pending(specs_dir: Path) -> dict[str, str]`. Entry to spec filename, for `specs_dir/*.md` only.

- [ ] **Step 1: Write the failing tests** (`tests/test_dead_gate.py`)

```python
"""The `dead` gate (docs/superpowers/specs/2026-09-18-dead-code-gate-design.md).

The script is loaded inside each test, never at module scope: the `revert`
gate re-runs a new witness with the script deleted.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from saffron.intake import parse_spec

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / ".saffron" / "gates" / "dead.py"


def _dead():
    spec = importlib.util.spec_from_file_location("saffron_dead_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered first: `Unused` is a dataclass under postponed annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_each_vulture_line_becomes_one_failure_keyed_by_kind_and_symbol():
    [unused] = _dead().parse(
        "saffron/util.py:12: unused function 'visible_cpus' (60% confidence)\n"
    )
    assert (unused.file, unused.line, unused.code) == ("saffron/util.py", 12, "unused-function")
    assert unused.message == "unused function 'visible_cpus' (60% confidence)"
    assert unused.symbol == "saffron/util.py::visible_cpus"


def test_unreachable_code_is_a_failure_with_no_symbol_to_defer():
    [unused] = _dead().parse(
        "saffron/util.py:30: unreachable code after 'return' (100% confidence)\n"
    )
    assert unused.code == "unreachable-code"
    assert unused.symbol is None


def test_a_line_the_parser_cannot_read_is_an_error_not_a_pass():
    with pytest.raises(ValueError, match="cannot read"):
        _dead().parse("vulture changed its format\n")


SPEC = "---\nid: SA-9001\ntitle: t\ntype: chore\n{extra}---\n\n## Context\nx\n"


def test_an_open_spec_defers_the_symbols_it_lists(tmp_path):
    (tmp_path / "SA-9001-x.md").write_text(
        SPEC.format(extra="pending_symbols:\n  - saffron/util.py::visible_cpus\n")
    )
    assert _dead().pending(tmp_path) == {"saffron/util.py::visible_cpus": "SA-9001-x.md"}


def test_a_retired_spec_defers_nothing(tmp_path):
    (tmp_path / "done").mkdir()
    (tmp_path / "done" / "SA-9001-x.md").write_text(
        SPEC.format(extra="pending_symbols:\n  - saffron/util.py::visible_cpus\n")
    )
    assert _dead().pending(tmp_path) == {}


@pytest.mark.parametrize(
    "extra",
    [
        "pending_symbols: saffron/util.py::visible_cpus\n",
        "pending_symbols:\n  - visible_cpus\n",
        "pending_symbols: [unclosed\n",
    ],
)
def test_a_malformed_pending_list_is_an_error(extra):
    with pytest.raises(ValueError):
        _dead().entries(SPEC.format(extra=extra))


AGREEMENT = [
    SPEC.format(extra=""),
    SPEC.format(extra="pending_symbols:\n"),
    SPEC.format(extra="pending_symbols: [saffron/a.py::b, 'saffron/c.py::d']\n"),
    SPEC.format(extra="pending_symbols:\n  # a comment\n  - \"saffron/a.py::b\"\n"),
]


@pytest.mark.parametrize(
    "text",
    AGREEMENT
    + [p.read_text() for p in sorted((REPO / ".saffron" / "specs").rglob("*.md"))],
)
def test_the_gate_reads_the_same_entries_intake_does(text):
    assert _dead().entries(text) == parse_spec(text).pending_symbols
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/test_dead_gate.py -v`
Expected: every test FAILS with `FileNotFoundError` for `dead.py`.

- [ ] **Step 3: Write the functions**

`.saffron/gates/dead.py`:

```python
#!/usr/bin/env python3
"""vulture -> the gate contract: code that no production caller reaches.

Design: `docs/superpowers/specs/2026-09-18-dead-code-gate-design.md`. `tests/`
is not scanned, so a symbol only a test calls is dead. An open spec defers a
symbol it will bring into use by listing it under `pending_symbols`.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

GATE = "dead"
ROOTS = ("saffron", "harness", "images", ".saffron/gates")
MIN_CONFIDENCE = "60"
# Anchored on this file, as `structure.py` anchors its config: a cell runs the base's copy.
SAFFRON_DIR = Path(__file__).resolve().parent.parent
WHITELIST = SAFFRON_DIR / "deadcode-allow.py"
SPECS = SAFFRON_DIR / "specs"
# Measured on vulture 2.16: 3 means it reported dead code, 1 a syntax error or a missing path.
OK_EXITS = (0, 3)

_LINE = re.compile(r"^(?P<file>.+?):(?P<line>\d+): (?P<message>.+ \(\d+% confidence\))$")
_UNUSED = re.compile(r"^unused (?P<kind>\w+) '(?P<name>[^']+)'")
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
# The same pattern as `saffron.intake.PENDING_SYMBOL`; a test holds the two readers together.
_ENTRY = re.compile(r"^[^\s:]+::[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Unused:
    file: str
    line: int
    code: str
    message: str
    name: str | None

    # ponytail: vulture names no class, so an entry for a method defers every
    # method of that name in the file.
    @property
    def symbol(self) -> str | None:
        return None if self.name is None else f"{self.file}::{self.name}"


def parse(stdout: str) -> list[Unused]:
    """One `Unused` per vulture line. A line it cannot read raises `ValueError`."""
    found = []
    for raw in stdout.splitlines():
        if not raw.strip():
            continue
        line = _LINE.match(raw)
        if line is None:
            raise ValueError(f"cannot read vulture line: {raw[:200]}")
        message = line["message"]
        unused = _UNUSED.match(message)
        if unused:
            code, name = f"unused-{unused['kind']}", unused["name"]
        elif message.startswith("unreachable code"):
            code, name = "unreachable-code", None
        else:
            raise ValueError(f"cannot read vulture line: {raw[:200]}")
        found.append(Unused(line["file"], int(line["line"]), code, message, name))
    return found


def entries(text: str) -> list[str]:
    """One spec's `pending_symbols`, validated as `saffron.intake` validates it."""
    import yaml  # here, so a cell without pyyaml reports `error` after the version probe

    match = _FRONTMATTER.match(text)
    if match is None:
        raise ValueError("no YAML frontmatter block")
    try:
        fields = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(fields, dict):
        raise ValueError("frontmatter is not a mapping")
    listed = fields.get("pending_symbols") or []
    if not isinstance(listed, list) or not all(
        isinstance(e, str) and _ENTRY.match(e) for e in listed
    ):
        raise ValueError(f"pending_symbols is not a list of <path>::<name>: {listed!r}")
    return listed


def pending(specs_dir: Path) -> dict[str, str]:
    """Each open spec's entries, mapped to the spec file that names it."""
    found: dict[str, str] = {}
    for path in sorted(specs_dir.glob("*.md")):
        try:
            listed = entries(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ValueError(f"{path.name}: {exc}") from exc
        found.update(dict.fromkeys(listed, path.name))
    return found
```

- [ ] **Step 4: Run the tests and see them pass**

Run: `uv run pytest tests/test_dead_gate.py -v`
Expected: all PASS.

- [ ] **Step 5: Mutant checks** (one at a time, revert after each)

| Mutant | Test that must fail |
| --- | --- |
| `specs_dir.glob` → `specs_dir.rglob` | `test_a_retired_spec_defers_nothing` |
| `raise ValueError(f"cannot read …")` in the `if line is None` branch → `continue` | `test_a_line_the_parser_cannot_read_is_an_error_not_a_pass` |
| drop `and _ENTRY.match(e)` | `test_a_malformed_pending_list_is_an_error[…visible_cpus…]` |
| `or []` → `or ["saffron/x.py::y"]` | `test_the_gate_reads_the_same_entries_intake_does` |

- [ ] **Step 6: Commit**

```bash
git add .saffron/gates/dead.py tests/test_dead_gate.py
git commit -m "feat(gates): nothing turned vulture's report or a spec's pending symbols into gate failures"
```

---

### Task 4: the gate's `main` and wrapper

**Files:**
- Modify: `.saffron/gates/dead.py` (append `main`)
- Create: `.saffron/gates/dead` (mode 755)
- Test: `tests/test_dead_gate.py`

**Interfaces:**
- Consumes: `Unused`, `parse`, `pending`, `ROOTS`, `WHITELIST`, `SPECS`, `OK_EXITS` (Task 3). `saffron.gates.contract.parse_gate_json` and `identity`, in tests only.
- Produces: `main(argv: list[str]) -> int`. `[]` prints one gate-contract JSON object. `["--report"]` prints the human report (Task 6). A run with no failures has status `pass`, and one with failures `fail`. The summary is `"<n> unused, <d> deferred by open specs, <s> stale pending entries"`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_dead_gate.py`; add `import os`, `import shutil`, `import subprocess` and `from saffron.gates.contract import identity, parse_gate_json` to the imports)

```python
CLEAN = "def used():\n    return 1\n\n\nprint(used())\n"
ORPHAN = "def orphan():\n    return 2\n"


def _tree(tmp_path: Path) -> Path:
    """A repo with the gate, an empty whitelist and one clean module."""
    gates = tmp_path / ".saffron" / "gates"
    gates.mkdir(parents=True)
    shutil.copy(SCRIPT, gates / "dead.py")
    shutil.copy(REPO / ".saffron" / "gates" / "dead", gates / "dead")
    (tmp_path / ".saffron" / "deadcode-allow.py").write_text("# Nothing yet.\n")
    (tmp_path / ".saffron" / "specs" / "done").mkdir(parents=True)
    (tmp_path / "saffron").mkdir()
    (tmp_path / "saffron" / "core.py").write_text(CLEAN)
    return tmp_path


def _env(path: str | None = None) -> dict[str, str]:
    venv_bin = str(Path(sys.executable).parent)
    return {**os.environ, "PATH": path or f"{venv_bin}{os.pathsep}{os.environ['PATH']}"}


def _script(tree: Path, *args: str, python=(sys.executable,), env=None) -> str:
    done = subprocess.run(
        [*python, str(tree / ".saffron" / "gates" / "dead.py"), *args],
        cwd=tree, capture_output=True, text=True, timeout=120, env=env or _env(),
    )
    return done.stdout


def _run(tree: Path, python=(sys.executable,), env=None):
    return parse_gate_json(_script(tree, python=python, env=env), expected_gate="dead")


def _spec(tree: Path, entry: str, folder: str = "") -> None:
    (tree / ".saffron" / "specs" / folder / "SA-9001-x.md").write_text(
        SPEC.format(extra=f"pending_symbols:\n  - {entry}\n")
    )


def test_a_tree_with_no_dead_code_passes_and_names_its_tool(tmp_path):
    result = _run(_tree(tmp_path))
    assert result.status == "pass", result.summary
    assert result.tool and result.tool.startswith("vulture")


def test_the_wrapper_runs_the_script(tmp_path):
    tree = _tree(tmp_path)
    done = subprocess.run(
        [str(tree / ".saffron" / "gates" / "dead")],
        cwd=tree, capture_output=True, text=True, timeout=120, env=_env(),
    )
    assert parse_gate_json(done.stdout, expected_gate="dead").status == "pass"


def test_a_function_nothing_calls_is_a_failure(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    result = _run(tree)
    assert result.status == "fail"
    assert [(f.file, f.code) for f in result.failures] == [("saffron/extra.py", "unused-function")]


def test_a_function_only_a_test_calls_is_a_failure(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    (tree / "tests").mkdir()
    (tree / "tests" / "test_extra.py").write_text(
        "from saffron.extra import orphan\n\n\ndef test_it():\n    assert orphan() == 2\n"
    )
    assert _run(tree).status == "fail"


def test_an_open_spec_defers_the_symbol_it_lists(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    _spec(tree, "saffron/extra.py::orphan")
    result = _run(tree)
    assert result.status == "pass", result.summary
    assert "1 deferred" in result.summary


def test_a_retired_spec_defers_nothing_at_the_gate(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    _spec(tree, "saffron/extra.py::orphan", folder="done")
    assert _run(tree).status == "fail"


def test_a_stale_pending_entry_does_not_fail_the_gate(tmp_path):
    """The task that implements a spec gives its entries a caller while the spec is open."""
    tree = _tree(tmp_path)
    _spec(tree, "saffron/core.py::used")
    result = _run(tree)
    assert result.status == "pass", result.summary
    assert "1 stale" in result.summary


def test_a_missing_vulture_is_an_error(tmp_path):
    result = _run(_tree(tmp_path), env=_env(path=str(tmp_path / "no-bin")))
    assert result.status == "error"


def test_a_missing_pyyaml_is_an_error(tmp_path):
    tree = _tree(tmp_path)
    _spec(tree, "saffron/core.py::used")
    # `-S` drops site-packages, where pyyaml lives; vulture is still on PATH.
    assert _run(tree, python=(sys.executable, "-S")).status == "error"


def test_a_file_vulture_cannot_read_is_an_error_not_a_failure(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "broken.py").write_text("def (:\n")
    assert _run(tree).status == "error"


def test_a_malformed_spec_is_an_error(tmp_path):
    tree = _tree(tmp_path)
    _spec(tree, "orphan")
    assert _run(tree).status == "error"


def test_a_failure_keeps_its_identity_when_its_line_moves(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    before = [identity("dead", f) for f in _run(tree).failures]
    (tree / "saffron" / "extra.py").write_text("\n" * 30 + ORPHAN)
    after = _run(tree).failures
    assert after[0].line != 1
    assert [identity("dead", f) for f in after] == before
```

- [ ] **Step 2: Run them and see them fail**

Run: `uv run pytest tests/test_dead_gate.py -v`
Expected: the Task 3 tests PASS. Every new test FAILS: the wrapper is missing and the script prints nothing.

- [ ] **Step 3: Write `main`** (append to `.saffron/gates/dead.py`)

```python
def _emit(payload: dict[str, object]) -> int:
    print(json.dumps(payload))
    return 0


def _error(summary: str, tool: str | None = None) -> int:
    return _emit({"gate": GATE, "status": "error", "tool": tool, "summary": summary})


def main(argv: list[str]) -> int:
    report = argv == ["--report"]
    if argv and not report:
        print("usage: dead.py [--report]", file=sys.stderr)
        return 2
    try:
        version = subprocess.run(["vulture", "--version"], capture_output=True, text=True)
    # Not just FileNotFoundError: a present-but-unrunnable binary raises PermissionError.
    except OSError as exc:
        return _error(f"vulture could not be run: {exc}")
    tool = version.stdout.strip()
    if version.returncode != 0 or not tool:
        return _error("vulture reported no version")
    if not WHITELIST.is_file():
        return _error(f"no whitelist at {WHITELIST}", tool)
    roots = [r for r in ROOTS if Path(r).is_dir()]
    if not roots:
        return _error(f"none of {', '.join(ROOTS)} is here, so nothing was scanned", tool)
    scan = subprocess.run(
        ["vulture", *roots, str(WHITELIST), "--min-confidence", MIN_CONFIDENCE],
        capture_output=True,
        text=True,
    )
    if scan.returncode not in OK_EXITS:
        detail = (scan.stderr or scan.stdout).strip()[-400:]
        return _error(f"vulture exited {scan.returncode}: {detail}", tool)
    try:
        found = parse(scan.stdout)
        deferred = pending(SPECS)
    except (ImportError, OSError, ValueError) as exc:
        return _error(f"{type(exc).__name__}: {exc}", tool)

    failures = [u for u in found if u.symbol not in deferred]
    reported = {u.symbol for u in found}
    stale = sorted(e for e in deferred if e not in reported)
    summary = (
        f"{len(failures)} unused, {len(found) - len(failures)} deferred by open specs, "
        f"{len(stale)} stale pending entries"
    )
    if report:
        for u in failures:
            print(f"{u.file}:{u.line}: {u.message}")
        for entry in stale:
            print(f"stale: {entry} ({deferred[entry]})")
        print(summary)
        return 0
    return _emit(
        {
            "gate": GATE,
            "status": "fail" if failures else "pass",
            "tool": tool,
            "failures": [
                {"file": u.file, "line": u.line, "code": u.code, "message": u.message}
                for u in failures
            ],
            "summary": summary,
        }
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Write the wrapper**

`.saffron/gates/dead`:

```sh
#!/bin/sh
exec python3 "$(dirname "$0")/dead.py"
```

Run: `chmod +x .saffron/gates/dead`

- [ ] **Step 5: Run the tests and see them pass**

Run: `uv run pytest tests/test_dead_gate.py -v`
Expected: all PASS. If `test_a_tree_with_no_dead_code_passes_and_names_its_tool` fails on a failure inside `.saffron/gates/dead.py`, vulture has flagged the gate itself. Fix the gate code. Do not whitelist it.

- [ ] **Step 6: Mutant checks** (one at a time, revert after each)

| Mutant | Test that must fail |
| --- | --- |
| `failures = [u for u in found if u.symbol not in deferred]` → `failures = list(found)` | `test_an_open_spec_defers_the_symbol_it_lists` |
| `ROOTS` gains `"tests"` | `test_a_function_only_a_test_calls_is_a_failure` |
| `OK_EXITS = (0, 1, 3)` | `test_a_file_vulture_cannot_read_is_an_error_not_a_failure` |
| `"status": "fail" if failures else "pass"` → `"fail" if failures or stale else "pass"` | `test_a_stale_pending_entry_does_not_fail_the_gate` |
| `"message": u.message` → `"message": f"line {u.line}: {u.message}"` | `test_a_failure_keeps_its_identity_when_its_line_moves` |
| `except OSError as exc:` → `except FileNotFoundError as exc:`, and the test's PATH points at a non-executable file named `vulture` | `test_a_missing_vulture_is_an_error` (confirm the traceback, then revert both) |

- [ ] **Step 7: Commit**

```bash
git add .saffron/gates/dead.py .saffron/gates/dead tests/test_dead_gate.py
git commit -m "feat(gates): no gate failed a task that added a function nothing calls"
```

---

### Task 5: declare the gate

**Files:**
- Modify: `.saffron/policy.yaml` (the `gates:` map, after `prose`)
- Modify: `tests/test_saffron_gates.py:32-43`

**Interfaces:**
- Consumes: `.saffron/gates/dead` (Task 4).
- Produces: `dead` in `load_policy(REPO).gates`, blocking.

- [ ] **Step 1: Update the failing test**

In `tests/test_saffron_gates.py::test_the_policy_parses`, add `"dead",` to the expected set after `"prose",`.

- [ ] **Step 2: Run it and see it fail**

Run: `uv run pytest tests/test_saffron_gates.py::test_the_policy_parses -v`
Expected: FAIL. The set lacks `dead`.

- [ ] **Step 3: Declare it**

In `.saffron/policy.yaml`, after `prose: { blocking: true }`:

```yaml
  # Code no production caller reaches. It fails at base too, so only a task's new
  # failures count; an open spec's `pending_symbols` defers one.
  dead: { blocking: true }
```

- [ ] **Step 4: Run it and see it pass, then run the gate on this repo**

Run: `uv run pytest tests/test_saffron_gates.py::test_the_policy_parses -v`
Expected: PASS.

Run: `uv run .saffron/gates/dead | python3 -m json.tool | tail -5`
Expected: `"status": "fail"` and a summary starting `55 unused`. A different count means the tree moved since `66c71ca`. Record the number printed and use it in Task 6.

- [ ] **Step 5: Run everything**

Run: `make check`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .saffron/policy.yaml tests/test_saffron_gates.py
git commit -m "feat(policy): code no caller reaches passed every gate this repo declares"
```

---

### Task 6: `make deadcode` and the backlog record

**Files:**
- Modify: `Makefile`
- Create: `docs/backlog/<id>-code-no-caller-reaches.md`
- Test: `tests/test_dead_gate.py`

**Interfaces:**
- Consumes: `main(["--report"])` (Task 4).

- [ ] **Step 1: Write the failing test** (append to `tests/test_dead_gate.py`)

```python
def test_the_report_lists_each_failure_and_each_stale_entry(tmp_path):
    tree = _tree(tmp_path)
    (tree / "saffron" / "extra.py").write_text(ORPHAN)
    _spec(tree, "saffron/core.py::used")
    lines = _script(tree, "--report").splitlines()
    assert lines[0].startswith("saffron/extra.py:1: unused function 'orphan'")
    assert "stale: saffron/core.py::used (SA-9001-x.md)" in lines
    assert lines[-1] == "1 unused, 0 deferred by open specs, 1 stale pending entries"


def test_make_deadcode_runs_the_report():
    makefile = (REPO / "Makefile").read_text()
    assert "deadcode:\n\tuv run python .saffron/gates/dead.py --report\n" in makefile
```

- [ ] **Step 2: Run them**

Run: `uv run pytest tests/test_dead_gate.py -k "report" -v`
Expected: the first PASSES, because Task 4 wrote the report. The second FAILS.

- [ ] **Step 3: Add the target**

In `Makefile`, add `deadcode` to `.PHONY` and append:

```make
deadcode:
	uv run python .saffron/gates/dead.py --report
```

Run: `make deadcode | tail -1`
Expected: `55 unused, 0 deferred by open specs, 0 stale pending entries`, or the count Task 5 recorded.

- [ ] **Step 4: File the backlog record**

Run: `uv run python -m records new-id` and use the id it prints. Create `docs/backlog/<id>-code-no-caller-reaches.md`:

```markdown
---
id: <id>
title: 55 symbols no production caller reaches, and the `dead` gate only stops new ones
status: open
tier: 3
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§5.4]
related: []
---

## Problem

The `dead` gate (`docs/superpowers/specs/2026-09-18-dead-code-gate-design.md`)
blocks new dead code. The 55 symbols vulture reported at `66c71ca` are its
baseline, so nothing removes them.

| Kind      | Count |
| --------- | ----- |
| variable  | 31    |
| function  | 16    |
| method    | 6     |
| property  | 1     |
| attribute | 1     |

`make deadcode` prints the current list and count.

## Done when

Each of the 55 is removed, listed in an open spec's `pending_symbols`, or
whitelisted in `.saffron/deadcode-allow.py` with its reason. `make deadcode`
reports `0 unused`.
```

Run: `uv run python -m records show <id>`
Expected: the record prints without a parse error.

- [ ] **Step 5: Run everything**

Run: `uv run pytest tests/test_dead_gate.py -v && make check`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add Makefile tests/test_dead_gate.py docs/backlog/<id>-code-no-caller-reaches.md
git commit -m "feat(make): nothing printed the dead-code count or held its triage"
```

- [ ] **Step 7: Open the first pull request**

Read `.github/pull_request_template.md` first, since `gh pr create --body` skips it. Ask the operator before pushing. Then invoke the `gh-stack` skill to submit `joel/dead-code-gate` as the stack's base.

---

### Task 7: triage the 55 (second pull request)

**Files:**
- Modify: the files `make deadcode` names
- Modify: `.saffron/deadcode-allow.py`
- Modify: `.saffron/specs/SA-*.md`, for deferrals only
- Modify: `docs/backlog/<id>-code-no-caller-reaches.md`

- [ ] **Step 1: Branch**

Invoke the `gh-stack` skill to add `joel/dead-code-triage` on top of `joel/dead-code-gate`.

- [ ] **Step 2: List them**

Run: `make deadcode`
Expected: one line per symbol, then the count Task 5 recorded.

- [ ] **Step 3: Decide each one, in this order**

For each line, grep the name across the tree:

```bash
grep -rn --include='*.py' --include='*.md' '\b<name>\b' . | grep -v '^./.venv'
```

1. **Framework-called** (a pydantic field or validator, a `typer` command, a `pytest` hook, a dataclass field read by `asdict`, a module `__getattr__`, the entry point of `images/agent_runner.py`): add `_.<name>  # <who calls it>` to `.saffron/deadcode-allow.py`.
2. **Called only from `docs/evidence/scripts/`** (expected under `harness/`): whitelist it with `_.<name>  # docs/evidence/scripts/<file>`.
3. **Named in an open spec's body as something that spec will call**: add `<path>::<name>` to that spec's `pending_symbols`. Adding a field to an open spec is a change that `tests/test_scheduler.py::test_saffron_queue_smoke_reproduces_this_repos_measured_queue` may pin. Run it.
4. **Called only by tests**: delete the symbol and the tests that exercise only it. A test that also covers live code keeps that part.
5. **Called by nothing**: delete it.

If a deletion leaves a new symbol with no caller, `make deadcode` shows it on the next run. Handle it by the same rules.

- [ ] **Step 4: Verify after each file**

Run: `make deadcode | tail -1 && uv run pytest -q`
Expected: the count falls and the tests pass. A test failing after a deletion means the symbol was live. Restore it and whitelist it with the caller vulture missed.

- [ ] **Step 5: Reach zero**

Run: `make deadcode`
Expected: `0 unused, <d> deferred by open specs, 0 stale pending entries`.

- [ ] **Step 6: Close the record**

In `docs/backlog/<id>-code-no-caller-reaches.md`, set `status: done`. Append `## Resolution` with the counts removed, whitelisted and deferred.

- [ ] **Step 7: Run everything and commit**

Run: `make check`
Expected: PASS.

```bash
git add -A saffron harness images tests .saffron/deadcode-allow.py .saffron/specs docs/backlog
git commit -m "refactor: 55 symbols no production caller reached were kept alive by nothing but tests or habit"
```

- [ ] **Step 8: Open the second pull request**

Ask the operator before pushing. Then invoke the `gh-stack` skill to submit the triage branch.
