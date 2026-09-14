"""A closed set under `saffron/` is spelled once and imported everywhere else.

`SA-0029` restated `saffron.gates.contract.GateStatus` as a second `Literal` with
the same four members, and nothing held the two together; review commit
`030044e` replaced it with an import. Two spellings drift the first time a
member is added to one of them.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def closed_sets(source: str) -> list[tuple[str, int, frozenset[object]]]:
    """Each module-level name bound to a `Literal` of constants: name, line, members.

    ponytail: `Literal` is read by name, so an aliased import of it is not seen —
    `SA-0077`'s move against `integrity`. Resolve imports if that ever ships."""
    found = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        elif isinstance(node, ast.TypeAlias):
            target, value = node.name, node.value
        else:
            continue
        if not (isinstance(target, ast.Name) and isinstance(value, ast.Subscript)):
            continue
        head = value.value
        spelled = head.id if isinstance(head, ast.Name) else getattr(head, "attr", "")
        if spelled != "Literal":
            continue
        members = (
            value.slice.elts if isinstance(value.slice, ast.Tuple) else [value.slice]
        )
        constants = [m for m in members if isinstance(m, ast.Constant)]
        if len(constants) == len(members):
            found.append(
                (target.id, node.lineno, frozenset(c.value for c in constants))
            )
    return found


def spelled_twice(files: dict[str, str]) -> list[list[str]]:
    sites: dict[frozenset[object], list[str]] = defaultdict(list)
    for path, source in files.items():
        for name, line, members in closed_sets(source):
            sites[members].append(f"{path}:{line} {name}")
    return [where for where in sites.values() if len(where) > 1]


def _saffron() -> dict[str, str]:
    return {
        str(path.relative_to(REPO)): path.read_text()
        for path in sorted((REPO / "saffron").rglob("*.py"))
    }


def test_no_closed_set_is_spelled_twice_under_saffron():
    assert spelled_twice(_saffron()) == [], (
        "import the first spelling rather than restating it"
    )


def test_the_check_would_catch_a_restated_set():
    """Through the same scan, over the real tree plus a restatement of one of its
    own sets — a guard that only re-derived set equality would stay green with
    the scan gutted."""
    files = _saffron()
    name, _line, members = next(s for src in files.values() for s in closed_sets(src))
    spelling = ", ".join(repr(m) for m in sorted(members, key=repr))
    files["saffron/restated.py"] = (
        f"from typing import Literal\n\n{name} = Literal[{spelling}]\n"
    )
    assert len(spelled_twice(files)) == 1


def test_every_way_of_binding_a_literal_is_read():
    source = (
        "import typing\n"
        "from typing import Literal, TypeAlias\n"
        'A = Literal["x", "y"]\n'
        'B: TypeAlias = typing.Literal["x", "y"]\n'
        'type C = Literal["x", "y"]\n'
    )
    assert [name for name, _line, _members in closed_sets(source)] == ["A", "B", "C"]
