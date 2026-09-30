"""§4.2.1 states how many things the refusal gate refuses (backlog item 48).

The count went wrong twice, each time found by a reader. These tests fail when a
ninth `RefusalKind` lands and `DESIGN.md` still says eight.
"""

import ast
import re
from collections import Counter
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


# Sites per kind in `scheduler.py`. A new site under an old kind changes a count here,
# so a ninth refusal cannot hide inside one of the eight.
SITES = {
    "open_pr_on_spec": 1,
    "open_pr_overlap": 1,
    # A live spec that does not parse, and a retired one in `done/` (§4.2.1).
    "malformed_spec": 2,
    "unmatched_criterion_path": 1,
    # One entry at a time, and the stack order that replaces it under `--stack`.
    "depends_on": 2,
    "protected_touch": 1,
    # A marker `touches` does not reach, and one naming an id nothing declares.
    "retirement_marker": 2,
}


def _sites() -> Counter[str]:
    """Each kind `scheduler.py` passes as `kind=` or returns first in a tuple."""
    tree = ast.parse(Path(scheduler.__file__).read_text())
    kinds = set(get_args(RefusalKind))
    found: Counter[str] = Counter()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "kind":
            value = node.value
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
            value = node.value.elts[0]
        else:
            continue
        if isinstance(value, ast.Constant) and value.value in kinds:
            found[str(value.value)] += 1
    return found


def test_design_states_as_many_refusals_as_the_scheduler_names():
    assert _stated_count() == len(get_args(RefusalKind))


def test_every_refusal_kind_but_preflight_has_its_pinned_sites_in_the_scan():
    assert set(SITES) == set(get_args(RefusalKind)) - {"preflight"}
    assert _sites() == SITES


def test_only_the_scan_constructs_a_refusal():
    # The site count reads `scheduler.py` alone, so a refusal built elsewhere goes uncounted.
    builders = [
        path
        for path in (ROOT / "saffron").rglob("*.py")
        if path.name != "scheduler.py" and "Refusal(" in path.read_text()
    ]
    assert builders == []
