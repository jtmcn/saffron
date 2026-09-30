"""§4.2.1 states how many things the refusal gate refuses (backlog item 48).

The count went wrong twice, each time found by a reader. These tests fail when a
ninth `RefusalKind` lands and `DESIGN.md` still says eight.
"""

import ast
import re
from pathlib import Path
from typing import get_args

from saffron import scheduler
from saffron.scheduler import RefusalKind

ROOT = Path(__file__).resolve().parents[1]

NUMBER_WORDS = {
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _stated_count() -> int:
    text = (ROOT / "DESIGN.md").read_text()
    stated = re.findall(r"The refusal gate refuses (\w+) things", text)
    assert len(stated) == 1, stated
    return NUMBER_WORDS[stated[0]]


def _kinds_emitted() -> set[str]:
    """Every kind `scheduler.py` passes as `kind=` or returns first in a tuple."""
    tree = ast.parse(Path(scheduler.__file__).read_text())
    kinds = set(get_args(RefusalKind))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "kind":
            value = node.value
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
            value = node.value.elts[0]
        else:
            continue
        if isinstance(value, ast.Constant) and value.value in kinds:
            found.add(str(value.value))
    return found


def test_design_states_as_many_refusals_as_the_scheduler_names():
    assert _stated_count() == len(get_args(RefusalKind))


def test_every_refusal_kind_but_preflight_has_a_site_in_the_scan():
    # A kind with no site would let the count pass while a refusal went unnamed.
    assert _kinds_emitted() == set(get_args(RefusalKind)) - {"preflight"}
