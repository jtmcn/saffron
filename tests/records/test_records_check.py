"""Each check against the good fixture (no violations) and a broken copy of it
(exactly the violation it exists to find). The broken copy is the mutant the
check is trusted against."""

import shutil
from pathlib import Path

import pytest

from records.check import (
    check_cites_resolve,
    check_ids,
    check_item_citations,
    check_links,
    check_specs_resolve,
    cited_items,
)
from records.kinds import KINDS
from records.load import load

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
BACKLOG = KINDS["backlog"]


@pytest.fixture
def broken(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE, tmp_path / "root")
    return tmp_path / "root"


def _item(root: Path, name: str) -> Path:
    return root / "docs" / "backlog" / name


def _rewrite(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, old
    path.write_text(text.replace(old, new, 1))


def test_the_good_fixture_has_no_violations():
    records = load(BACKLOG, FIXTURE)
    sections = {"4", "4.2", "4.2.1", "5", "5.4"}
    assert check_ids(records) == []
    assert check_links(records) == []
    assert check_specs_resolve(records, FIXTURE) == []
    assert check_cites_resolve(records, sections) == []
    assert check_item_citations(FIXTURE, {r.model.id for r in records}) == []


def test_ids_must_be_contiguous(broken):
    _item(broken, "003-a-corpse-reads-as-drained.md").rename(
        _item(broken, "005-a-corpse.md")
    )
    _rewrite(_item(broken, "005-a-corpse.md"), "id: 3", "id: 5")
    [v] = check_ids(load(BACKLOG, broken))
    assert v.field == "id" and "3" in v.message and "4" in v.message


def test_ids_must_be_unique(broken):
    shutil.copy(
        _item(broken, "003-a-corpse-reads-as-drained.md"), _item(broken, "003-twice.md")
    )
    violations = check_ids(load(BACKLOG, broken))
    assert any(v.field == "id" and "twice" in str(v) for v in violations)


def test_related_must_resolve(broken):
    _rewrite(
        _item(broken, "002-the-index-drifts.md"), "related: [1]", "related: [1, 9]"
    )
    [v] = check_links(load(BACKLOG, broken))
    assert v.field == "related" and "9" in v.message


def test_superseded_by_must_resolve_and_not_be_superseded_itself(broken):
    _rewrite(
        _item(broken, "003-a-corpse-reads-as-drained.md"),
        "status: open\n",
        "status: superseded\nclosed: 2026-09-03\nprs: [1]\nsuperseded_by: 2\n",
    )
    _rewrite(
        _item(broken, "002-the-index-drifts.md"),
        "status: partial\n",
        "status: superseded\nclosed: 2026-09-03\nprs: [1]\nsuperseded_by: 1\n",
    )
    fields = {v.field for v in check_links(load(BACKLOG, broken))}
    assert fields == {"superseded_by"}


def test_specs_must_resolve_to_a_spec_file(broken):
    _rewrite(
        _item(broken, "001-a-gate-that-never-ran.md"),
        "specs: [SA-0001]",
        "specs: [SA-0001, SA-0099]",
    )
    [v] = check_specs_resolve(load(BACKLOG, broken), broken)
    assert v.field == "specs" and "SA-0099" in v.message


def test_cites_must_resolve_to_a_design_section():
    # Against {"4", "5"}, both item 1's §5.4 and item 3's §4.2.1 fail to
    # resolve (neither section is in the set) — two violations, not one.
    records = load(BACKLOG, FIXTURE)
    violations = check_cites_resolve(records, {"4", "5"})
    assert {v.field for v in violations} == {"cites"}
    assert sorted(v.message for v in violations) == [
        "§4.2.1 is not a DESIGN.md section",
        "§5.4 is not a DESIGN.md section",
    ]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("see backlog item 33.", {33}),
        ("(`docs/BACKLOG.md` items 65, 72)", {65, 72}),
        ("items **81**–**85** are done", {81, 85}),
        ("BACKLOG item 118 and item 119", {118, 119}),
        ("the third item in the list", set()),
        ("item 3 of `touches`", {3}),
        ("item 1000 of them", set()),
    ],
)
def test_cited_items_reads_every_form_the_corpus_uses(text, expected):
    assert cited_items(text) == expected


def test_a_code_comment_citing_a_missing_item_is_a_violation(broken):
    (broken / "saffron" / "example.py").write_text("# backlog item 77 says so\n")
    [v] = check_item_citations(broken, {1, 2, 3})
    assert v.path == broken / "saffron" / "example.py" and "77" in v.message


def test_a_spec_context_citing_a_missing_item_is_a_violation(broken):
    spec = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    _rewrite(spec, "backlog item 1.", "backlog item 1 and item 12.")
    [v] = check_item_citations(broken, {1, 2, 3})
    assert "12" in v.message


def test_evidence_is_not_scanned(broken):
    ev = broken / "docs" / "evidence"
    ev.mkdir(parents=True)
    (ev / "2026-01-01-x.md").write_text("item 999 was true then\n")
    assert check_item_citations(broken, {1, 2, 3}) == []


def test_tests_records_is_not_scanned(broken):
    # Its own tests quote citations like `item 999` as data, not promises.
    target = broken / "tests" / "records" / "x.py"
    target.parent.mkdir(parents=True)
    target.write_text("# backlog item 77\n")
    assert check_item_citations(broken, {1, 2, 3}) == []
