"""Each check against the good fixture (no violations) and a broken copy of it
(exactly the violation it exists to find). The broken copy is the mutant the
check is trusted against."""

import inspect
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

import tests.records.check
from records.kinds import KINDS, Identified
from records.load import Record, load
from tests.records.check import (
    Violation,
    appendix_letters,
    building_pr,
    check_all,
    check_appendix_letters,
    check_awaiting,
    check_cites_resolve,
    check_done_specs_are_done,
    check_ids,
    check_item_citations,
    check_links,
    check_no_old_path,
    check_priority,
    check_spec_ids_unique,
    check_specs_name_their_items,
    check_specs_resolve,
    cited_items,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
BACKLOG = KINDS["backlog"]
APPENDIX = KINDS["appendix"]


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


def test_ids_must_be_contiguous(broken):
    _item(broken, "003-a-corpse-reads-as-drained.md").rename(
        _item(broken, "005-a-corpse.md")
    )
    _rewrite(_item(broken, "005-a-corpse.md"), "id: 3", "id: 5")
    [v] = check_ids(load(BACKLOG, broken))
    assert v.field == "id" and "3" in v.message and "4" in v.message
    assert v.path == _item(broken, "005-a-corpse.md")


def test_ids_must_be_unique(broken):
    shutil.copy(
        _item(broken, "003-a-corpse-reads-as-drained.md"), _item(broken, "003-twice.md")
    )
    violations = check_ids(load(BACKLOG, broken))
    assert any(v.field == "id" and "twice" in str(v) for v in violations)


def _hash_item(
    root: Path, item_id: str, extra: str = "", filed: str | None = "2026-09-18"
) -> Path:
    path = _item(root, f"{item_id}-a-later-item.md")
    dated = "" if filed is None else f"filed: {filed}\n"
    path.write_text(
        f"---\nid: {item_id}\ntitle: Later\nstatus: open\n{dated}{extra}---\n\n"
        "## Problem\n\nx\n\n## Done looks like\n\ny\n"
    )
    return path


def test_random_ids_leave_no_gap_in_the_numbered_ids(broken):
    _hash_item(broken, "b-3f9a2c")
    assert check_ids(load(BACKLOG, broken)) == []


def test_a_numbered_id_past_the_last_is_a_violation(broken, monkeypatch):
    monkeypatch.setattr(tests.records.check, "LAST_NUMBERED", 2)
    [v] = check_ids(load(BACKLOG, broken))
    assert v.path == _item(broken, "003-a-corpse-reads-as-drained.md")
    assert "new-id" in v.message


def test_a_random_id_must_say_when_it_was_filed(broken):
    path = _hash_item(broken, "b-3f9a2c", filed=None)
    [v] = check_ids(load(BACKLOG, broken))
    assert v.path == path
    assert "filed:" in v.message


def test_a_random_id_must_be_unique(broken):
    _hash_item(broken, "b-3f9a2c")
    shutil.copy(
        _item(broken, "b-3f9a2c-a-later-item.md"), _item(broken, "b-3f9a2c-twice.md")
    )
    violations = check_ids(load(BACKLOG, broken))
    assert any("b-3f9a2c is used more than once" in str(v) for v in violations)


def test_links_resolve_to_random_ids(broken):
    _hash_item(broken, "b-3f9a2c", "related: [1]\n")
    _rewrite(
        _item(broken, "002-the-index-drifts.md"),
        "related: [1]",
        "related: [1, b-3f9a2c, b-000000]",
    )
    [v] = check_links(load(BACKLOG, broken))
    assert v.message == "names item b-000000, which does not exist"


def test_priority_names_random_ids(broken):
    _hash_item(broken, "b-3f9a2c", "tier: 2\n")
    priority = broken / "docs" / "backlog" / "PRIORITY.md"
    _rewrite(priority, "**2**.", "**2**, **b-3f9a2c**, **b-000000**.")
    [v] = check_priority(load(BACKLOG, broken), priority)
    assert v.message == "names item b-000000, which does not exist"


def test_a_citation_of_a_missing_random_id_is_a_violation(broken):
    (broken / "saffron" / "example.py").write_text(
        "# backlog items b-3f9a2c and b-000000\n"
    )
    [v] = check_item_citations(broken, {1, 2, 3, "b-3f9a2c"})
    assert v.message == "cites backlog item b-000000, which does not exist"


def test_a_spec_context_names_its_random_id_item(broken):
    _hash_item(broken, "b-3f9a2c")
    spec = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    _rewrite(spec, "backlog item 1.", "backlog item b-3f9a2c.")
    violations = check_specs_name_their_items(load(BACKLOG, broken), broken)
    assert {v.message for v in violations} == {
        "SA-0001 cites this item and is not listed",
        "open, but SA-0001 is in done/",
    }


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
    # Item 3 → 2 is a chain; item 2 → 1 is fine, since item 1 is done.
    [v] = check_links(load(BACKLOG, broken))
    assert v.field == "superseded_by" and v.message == "item 2 is itself superseded"
    assert v.path == _item(broken, "003-a-corpse-reads-as-drained.md")


def test_superseded_by_must_name_an_item_that_exists(broken):
    _rewrite(
        _item(broken, "003-a-corpse-reads-as-drained.md"),
        "status: open\n",
        "status: superseded\nclosed: 2026-09-03\nprs: [1]\nsuperseded_by: 9\n",
    )
    [v] = check_links(load(BACKLOG, broken))
    assert v.field == "superseded_by"
    assert v.message == "names item 9, which does not exist"


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
        ("items 71/75/80, SA-0058", {71, 75, 80}),
        ("items 71/75", {71, 75}),
        ("item 3/4 of the way", {3, 4}),
        ("item b-3f9a2c says so", {"b-3f9a2c"}),
        ("items **b-3f9a2c**, 12 and b-00aa11", {"b-3f9a2c", 12, "b-00aa11"}),
        ("item B-3F9A2C, uppercase", set()),
        ("item b-3f9a2cc is not an id", set()),
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


def test_the_good_fixture_passes_every_check():
    assert check_all(FIXTURE, {"4", "4.2", "4.2.1", "5", "5.4"}) == []


def test_check_all_runs_every_check(monkeypatch):
    # The expected set is every `check_*` the module defines, not check_all's body.
    # check_appendix_letters is not wired in yet; a later task does that.
    UNWIRED = {"check_appendix_letters"}
    names = {
        name
        for name, fn in inspect.getmembers(tests.records.check, inspect.isfunction)
        if name.startswith("check_")
        and name != "check_all"
        and name not in UNWIRED
        and fn.__module__ == "tests.records.check"
    }
    for name in names:
        sentinel = Violation(Path(name), "sentinel", name)
        monkeypatch.setattr(
            tests.records.check, name, lambda *_, sentinel=sentinel: [sentinel]
        )
    ran = {v.message for v in check_all(FIXTURE, set())}
    assert ran == names


def test_a_spec_id_in_two_files_is_a_violation_naming_both(broken):
    specs = broken / ".saffron" / "specs"
    shutil.copy(specs / "done" / "SA-0001-a-gate.md", specs / "SA-0001-again.md")
    [v] = check_spec_ids_unique(broken)
    assert v.field == "specs" and "SA-0001" in v.message
    assert "done/SA-0001-a-gate.md" in v.message and "SA-0001-again.md" in v.message


def test_a_non_backlog_record_is_refused_naming_the_file():
    # A field read via getattr(..., default) on the wrong model would silently
    # check nothing; narrowing to BacklogItem must refuse it instead.
    records = load(BACKLOG, FIXTURE)
    bogus = replace(records[0], model=Identified(id=records[0].model.id))
    with pytest.raises(TypeError, match=str(bogus.path)):
        check_links([bogus])


def test_the_priority_check_refuses_a_non_backlog_record_too():
    records = load(BACKLOG, FIXTURE)
    bogus = replace(records[0], model=Identified(id=records[0].model.id))
    with pytest.raises(TypeError, match=str(bogus.path)):
        check_priority([bogus], FIXTURE / "docs" / "backlog" / "PRIORITY.md")


def test_a_done_item_may_not_name_a_spec_still_in_the_queue(broken):
    done = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    done.rename(broken / ".saffron" / "specs" / "SA-0001-a-gate.md")
    [v] = check_done_specs_are_done(load(BACKLOG, broken), broken)
    assert v.field == "specs" and "SA-0001" in v.message


def test_a_spec_citing_an_item_must_be_listed_by_it(broken):
    _rewrite(
        _item(broken, "001-a-gate-that-never-ran.md"),
        "specs: [SA-0001]\n",
        "specs: []\ncommits: [abc1234]\n",
    )
    [v] = check_specs_name_their_items(load(BACKLOG, broken), broken)
    assert v.field == "specs" and "SA-0001" in v.message


def test_a_done_spec_may_not_leave_its_item_open(broken):
    spec = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    _rewrite(spec, "backlog item 1.", "backlog item 3.")
    _rewrite(
        _item(broken, "003-a-corpse-reads-as-drained.md"),
        "cites:",
        "specs: [SA-0001]\ncites:",
    )
    violations = check_specs_name_their_items(load(BACKLOG, broken), broken)
    assert any(v.field == "status" and "SA-0001" in v.message for v in violations)


def test_the_inverse_rule_keys_on_the_first_cited_item(broken):
    # Context cites item 1 first, item 3 second — only item 1 must list the spec.
    spec = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    _rewrite(spec, "backlog item 1.", "backlog item 1 and item 3.")
    assert check_specs_name_their_items(load(BACKLOG, broken), broken) == []


def test_priority_may_not_name_a_missing_item(broken):
    _rewrite(broken / "docs" / "backlog" / "PRIORITY.md", "**3**.", "**3**, **9**.")
    [v] = check_priority(
        load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md"
    )
    assert "9" in v.message


def test_priority_may_not_strike_a_missing_item(broken):
    _rewrite(broken / "docs" / "backlog" / "PRIORITY.md", "**3**.", "**3**, ~~**9**~~.")
    [v] = check_priority(
        load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md"
    )
    assert v.message == "strikes item 9, which does not exist"


def test_a_missing_priority_file_is_a_violation_naming_it(broken):
    priority = broken / "docs" / "backlog" / "PRIORITY.md"
    priority.unlink()
    [v] = check_priority(load(BACKLOG, broken), priority)
    assert v.path == priority and "does not exist" in v.message


def test_priority_may_not_strike_an_open_item(broken):
    _rewrite(broken / "docs" / "backlog" / "PRIORITY.md", "**3**.", "~~**3**~~.")
    [v] = check_priority(
        load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md"
    )
    assert "3" in v.message and "open" in v.message


def test_a_tiered_item_is_named_under_its_tier(broken):
    _rewrite(_item(broken, "002-the-index-drifts.md"), "tier: 2", "tier: 1")
    [v] = check_priority(
        load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md"
    )
    assert v.field == "tier" and "2" in v.message


def test_an_id_named_under_another_tier_in_prose_is_fine(broken):
    # The index narrates a move under the old tier; the rule runs records → index.
    _rewrite(
        broken / "docs" / "backlog" / "PRIORITY.md",
        "**2**.",
        "**2**. (**3** moved to tier 1.)",
    )
    assert (
        check_priority(
            load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md"
        )
        == []
    )


def test_an_id_named_only_after_the_tier_index_is_not_credited_to_a_stale_tier(broken):
    # Item 3 moves out of Tier 1's line into a footer heading; the tier scope
    # must end there, or the stale `tier` value would still credit it.
    _rewrite(
        broken / "docs" / "backlog" / "PRIORITY.md",
        "~~**1**~~, **3**.",
        "~~**1**~~.\n\n### Notes\n\n**3** is discussed here.",
    )
    [v] = check_priority(
        load(BACKLOG, broken), broken / "docs" / "backlog" / "PRIORITY.md"
    )
    assert v.field == "tier" and "3" in v.message


def test_no_live_surface_names_the_old_path(broken):
    (broken / "saffron" / "example.py").write_text("# see docs/BACKLOG.md item 1\n")
    [v] = check_no_old_path(broken)
    assert v.path.name == "example.py"


def test_a_done_spec_may_still_name_the_old_path(broken):
    spec = broken / ".saffron" / "specs" / "done" / "SA-0001-a-gate.md"
    _rewrite(spec, "backlog item 1.", "`docs/BACKLOG.md` item 1.")
    assert check_no_old_path(broken) == []


def test_tests_records_may_name_the_old_path(broken):
    # Its own tests quote the old path as data, not a promise.
    target = broken / "tests" / "records" / "x.py"
    target.parent.mkdir(parents=True)
    target.write_text("# docs/BACKLOG.md\n")
    assert check_no_old_path(broken) == []


_OPEN = "003-a-corpse-reads-as-drained.md"


def _with_record(root: Path, record: str, front: str = "") -> list[Record]:
    path = _item(root, _OPEN)
    if front:
        _rewrite(path, "tier: 1\n", f"tier: 1\n{front}")
    path.write_text(path.read_text() + f"\n## Record\n\n{record}\n")
    return load(BACKLOG, root)


def test_an_item_awaiting_an_unmerged_pull_request_holds(broken):
    records = _with_record(broken, "A fix is open as PR #300.", "awaiting: [300]\n")
    assert check_awaiting(records, frozenset({287}), building=296) == []


def test_an_item_awaiting_a_merged_pull_request_is_a_violation(broken):
    records = _with_record(broken, "Waiting.", "awaiting: [287]\n")
    [v] = check_awaiting(records, frozenset({287}), building=None)
    assert v.field == "awaiting" and "#287 has merged" in v.message


def test_an_item_awaiting_the_pull_request_that_carries_it_is_a_violation(broken):
    # What #287 did: the wait could only end by the merge that lands it.
    records = _with_record(broken, "A fix is open as PR #296.", "awaiting: [296]\n")
    [v] = check_awaiting(records, frozenset(), building=296)
    assert "#296 is this pull request" in v.message


def test_a_record_saying_a_pull_request_is_open_must_await_it(broken):
    records = _with_record(broken, "A fix is open as PR #287.")
    [v] = check_awaiting(records, frozenset({287}), building=None)
    assert "says #287 is open" in v.message


def test_a_record_that_says_the_pull_request_merged_needs_no_wait(broken):
    records = _with_record(
        broken, "A fix is open as PR #287.\n\nPR #287 merged; half is left."
    )
    assert check_awaiting(records, frozenset({287}), building=None) == []


def test_a_closed_item_is_not_read_for_waits(broken):
    _rewrite(
        _item(broken, _OPEN),
        "status: open\n",
        "status: done\nclosed: 2026-09-16\nprs: [287]\n",
    )
    records = _with_record(broken, "A fix is open as PR #287.")
    assert check_awaiting(records, frozenset({287}), building=None) == []


def test_building_pr_reads_only_a_pull_request_ref():
    assert building_pr("refs/pull/296/merge") == 296
    assert building_pr("refs/heads/main") is None
    assert building_pr(None) is None


def test_appendix_letters_run_a_to_z_then_aa():
    letters = appendix_letters(28)
    assert letters[:2] == ["A", "B"] and letters[25:] == ["Z", "AA", "AB"]


def test_the_fixture_appendices_are_contiguous():
    assert check_appendix_letters(load(APPENDIX, FIXTURE)) == []


def test_a_skipped_letter_is_a_violation(tmp_path: Path):
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    directory = tmp_path / APPENDIX.directory
    (directory / "B-a-second-revision.md").rename(directory / "C-a-second-revision.md")
    text = (directory / "C-a-second-revision.md").read_text()
    (directory / "C-a-second-revision.md").write_text(text.replace("id: B", "id: C"))
    [v] = check_appendix_letters(load(APPENDIX, tmp_path))
    assert v.field == "id" and "['A', 'C']" in v.message


def test_a_letter_used_twice_is_a_violation(tmp_path: Path):
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    directory = tmp_path / APPENDIX.directory
    shutil.copy(directory / "B-a-second-revision.md", directory / "B-again.md")
    [v] = check_appendix_letters(load(APPENDIX, tmp_path))
    assert "['A', 'B', 'B']" in v.message
