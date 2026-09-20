"""A record is its frontmatter plus its body split at `## ` headings; a file
that breaks a rule is refused with the file and the field named."""

import datetime as dt
import shutil
from pathlib import Path

import pytest

from records.kinds import KINDS
from records.load import Record, RecordError, load, parse, split_sections

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
BACKLOG = KINDS["backlog"]


def test_sections_split_at_h2_and_keep_h3_inside():
    body = "## Problem\n\nA.\n\n### Defect A\n\nB.\n\n## Record\n\nC.\n"
    assert split_sections(body) == {
        "Problem": "A.\n\n### Defect A\n\nB.",
        "Record": "C.",
    }


def test_a_fenced_h2_is_not_a_heading():
    body = "## Problem\n\n```\n## not a heading\n```\n\n## Record\n\nx\n"
    assert list(split_sections(body)) == ["Problem", "Record"]


def test_load_reads_every_item_in_id_order():
    records = load(BACKLOG, FIXTURE)
    assert [r.model.id for r in records] == [1, 2, 3]
    assert all(isinstance(r, Record) for r in records)
    assert records[0].sections["Done looks like"].startswith("`tool` is obtained")


def test_load_ignores_the_hand_written_files():
    names = {r.path.name for r in load(BACKLOG, FIXTURE)}
    assert "README.md" not in names and "PRIORITY.md" not in names


def test_a_filename_whose_prefix_disagrees_with_its_id_is_refused(tmp_path):
    item = tmp_path / "docs" / "backlog" / "009-nine.md"
    item.parent.mkdir(parents=True)
    item.write_text(
        "---\nid: 8\ntitle: Eight\nstatus: open\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n"
    )
    with pytest.raises(RecordError, match="009-nine.md.*id"):
        load(BACKLOG, tmp_path)


def test_a_file_with_no_frontmatter_is_refused():
    with pytest.raises(RecordError, match="frontmatter"):
        parse("## Problem\n\nx\n", BACKLOG)


def test_a_bad_field_names_the_field():
    with pytest.raises(RecordError, match="tier"):
        parse(
            "---\nid: 1\ntitle: T\nstatus: open\ntier: 9\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n",
            BACKLOG,
        )


@pytest.mark.parametrize("status", ["open", "partial"])
def test_an_unfinished_item_needs_done_looks_like(status):
    text = f"---\nid: 1\ntitle: T\nstatus: {status}\n---\n\n## Problem\n\nx\n\n## Record\n\n**Done, 2026-01-01.** half\n"
    with pytest.raises(RecordError, match="Done looks like"):
        parse(text, BACKLOG)


def test_a_partial_item_needs_a_dated_record_entry():
    text = "---\nid: 1\ntitle: T\nstatus: partial\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n\n## Record\n\nno date here\n"
    with pytest.raises(RecordError, match="Record.*dated"):
        parse(text, BACKLOG)


def test_an_unknown_section_is_refused():
    text = "---\nid: 1\ntitle: T\nstatus: open\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n\n## Notes\n\nz\n"
    with pytest.raises(RecordError, match="Notes"):
        parse(text, BACKLOG)


def test_sections_must_keep_their_order():
    text = "---\nid: 1\ntitle: T\nstatus: open\n---\n\n## Done looks like\n\ny\n\n## Problem\n\nx\n"
    with pytest.raises(RecordError, match="order"):
        parse(text, BACKLOG)


def test_a_missing_directory_is_refused_naming_it(tmp_path):
    missing = tmp_path / "docs" / "backlog"
    with pytest.raises(RecordError, match=str(missing)):
        load(BACKLOG, tmp_path)


def test_a_misnamed_item_file_is_refused_not_skipped(tmp_path):
    item = tmp_path / "docs" / "backlog" / "12-foo.md"
    item.parent.mkdir(parents=True)
    item.write_text(
        "---\nid: 12\ntitle: Foo\nstatus: open\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n"
    )
    with pytest.raises(RecordError, match="12-foo.md"):
        load(BACKLOG, tmp_path)


def test_an_unknown_key_set_to_null_is_still_refused():
    text = "---\nid: 1\ntitle: T\nstatus: open\nbogus_unknown_field: null\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n"
    with pytest.raises(RecordError, match="bogus_unknown_field"):
        parse(text, BACKLOG)


def _open_item(frontmatter: str) -> str:
    return f"---\n{frontmatter}\n---\n\n## Problem\n\nx\n\n## Done looks like\n\ny\n"


@pytest.mark.parametrize(
    "frontmatter, field",
    [
        # YAML 1.1 reads `033` as octal 27 and `yes` as True; both must be refused.
        ("id: 1\ntitle: T\nstatus: open\nrelated: [033]", "related"),
        ("id: 1\ntitle: T\nstatus: open\ntier: yes", "tier"),
        ("id: 010\ntitle: T\nstatus: open", "id"),
    ],
)
def test_a_yaml_1_1_coercion_is_refused_naming_the_field(frontmatter, field):
    with pytest.raises(RecordError, match=field):
        parse(_open_item(frontmatter), BACKLOG)


_CLOSED_ITEM = "id: 1\ntitle: T\nstatus: done\nclosed: 2026-09-01\nspecs: [SA-0001]"


def test_frontmatter_that_intake_reads_a_record_reads():
    text = _open_item("id: 1\ntitle: T\nstatus: open").replace("\n", "\r\n")
    assert parse(text, BACKLOG).model.id == 1


def test_a_file_ending_at_its_closing_fence_is_refused_for_its_body():
    # Naming Problem, not "no YAML frontmatter", is proof the fence was read.
    with pytest.raises(RecordError, match="Problem"):
        parse(f"---\n{_CLOSED_ITEM}\n---", BACKLOG)


def test_an_unquoted_all_digit_commit_sha_is_refused_naming_commits():
    # Refused, not coerced, like every other field that YAML reads as a number.
    text = f"---\n{_CLOSED_ITEM}\ncommits: [1234567]\n---\n"
    with pytest.raises(RecordError, match="commits"):
        parse(text, BACKLOG)


def test_a_quoted_or_leading_zero_sha_loads_as_written():
    text = f"---\n{_CLOSED_ITEM}\ncommits: ['1234567', 0123456, 57b676c]\n---\n\n## Problem\n\nx\n"
    assert parse(text, BACKLOG).model.model_dump(include={"commits"}) == {
        "commits": ["1234567", "0123456", "57b676c"]
    }


def test_plain_decimals_booleans_and_dates_still_load():
    record = parse(
        _open_item(
            "id: 1\ntitle: T\nstatus: open\nrelated: [33]\nby_hand: true\nfiled: 2026-09-01"
        ),
        BACKLOG,
    )
    assert record.model.model_dump(include={"related", "by_hand", "filed"}) == {
        "related": [33],
        "by_hand": True,
        "filed": dt.date(2026, 9, 1),
    }


def test_a_record_with_no_problem_section_is_refused():
    text = "---\nid: 1\ntitle: T\nstatus: open\n---\n\n## Done looks like\n\ny\n"
    with pytest.raises(RecordError, match="Problem"):
        parse(text, BACKLOG)


def test_prose_before_the_first_heading_is_refused(tmp_path):
    item = tmp_path / "docs" / "backlog" / "001-x.md"
    item.parent.mkdir(parents=True)
    item.write_text(
        "---\nid: 1\ntitle: T\nstatus: open\n---\n\n"
        "A stray paragraph before any heading.\n\n"
        "## Problem\n\nx\n\n## Done looks like\n\ny\n"
    )
    with pytest.raises(RecordError, match="001-x.md"):
        load(BACKLOG, tmp_path)


def _hash_item(root: Path, item_id: str, filed: str | None = None) -> Path:
    path = root / "docs" / "backlog" / f"{item_id}-a-later-item.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    filed_line = f"filed: {filed}\n" if filed else ""
    path.write_text(
        f"---\nid: {item_id}\ntitle: Later\nstatus: open\n{filed_line}---\n\n"
        "## Problem\n\nx\n\n## Done looks like\n\ny\n"
    )
    return path


def test_random_ids_load_after_the_numbered_items_in_filing_order(tmp_path):
    root = tmp_path / "root"
    shutil.copytree(FIXTURE, root)
    _hash_item(root, "b-000001", "2026-09-18")
    _hash_item(root, "b-ffffff", "2026-09-17")
    ids = [r.model.id for r in load(BACKLOG, root)]
    assert ids == [1, 2, 3, "b-ffffff", "b-000001"]


def test_a_random_id_filename_disagreeing_with_its_id_is_refused(tmp_path):
    path = _hash_item(tmp_path, "b-3f9a2c")
    path.rename(path.with_name("b-3f9a2d-a-later-item.md"))
    with pytest.raises(RecordError, match="b-3f9a2d.*id"):
        load(BACKLOG, tmp_path)


APPENDIX = KINDS["appendix"]


def test_an_appendix_body_with_no_h2_heading_loads():
    """The backlog refuses prose before the first `## `; an appendix is all such prose."""
    records = load(APPENDIX, FIXTURE)
    assert [r.model.id for r in records] == ["A", "B"]
    assert records[1].body.startswith("\nThe whole body is prose")
    assert records[0].sections == {}


def test_letters_sort_a_to_z_then_aa(tmp_path: Path):
    directory = tmp_path / APPENDIX.directory
    directory.mkdir(parents=True)
    for letter in ("AA", "B", "A"):
        (directory / f"{letter}-x.md").write_text(
            f'---\nid: {letter}\ntitle: "t"\nrevisions: [1]\nquestion: "q"\n---\n\nx\n'
        )
    assert [r.model.id for r in load(APPENDIX, tmp_path)] == ["A", "B", "AA"]


def test_the_backlog_still_refuses_prose_before_its_first_heading(tmp_path: Path):
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    item = next((tmp_path / "docs" / "backlog").glob("001-*.md"))
    text = item.read_text()
    item.write_text(text.replace("## Problem", "stray prose\n\n## Problem", 1))
    with pytest.raises(RecordError, match="prose before the first"):
        load(BACKLOG, tmp_path)


ADR = KINDS["adr"]
_ADR_BODY = (
    "\n## Context\n\nx\n\n## Decision\n\ny\n\n"
    "## Principles\n\nJudged against no principle.\n\n## Consequences\n\nz\n"
)


def _adr_text(adr_id: int, extra: str = "", status: str = "accepted") -> str:
    return f"---\nid: {adr_id}\ntitle: T\nstatus: {status}\ndate: 2026-09-01\n{extra}---\n{_ADR_BODY}"


def test_an_adr_loads_from_a_four_digit_prefix_and_refuses_what_it_does_not_declare(
    tmp_path: Path,
):
    good = tmp_path / "good"
    (good / "docs" / "adr").mkdir(parents=True)
    (good / "docs" / "adr" / "0001-x.md").write_text(_adr_text(1))
    [record] = load(ADR, good)
    assert record.model.id == 1

    short = tmp_path / "short"
    (short / "docs" / "adr").mkdir(parents=True)
    (short / "docs" / "adr" / "1-x.md").write_text(_adr_text(1))
    with pytest.raises(RecordError, match="1-x.md"):
        load(ADR, short)

    long = tmp_path / "long"
    (long / "docs" / "adr").mkdir(parents=True)
    (long / "docs" / "adr" / "00001-x.md").write_text(_adr_text(1))
    with pytest.raises(RecordError, match="00001-x.md"):
        load(ADR, long)

    unpadded = tmp_path / "unpadded"
    (unpadded / "docs" / "adr").mkdir(parents=True)
    (unpadded / "docs" / "adr" / "0002-x.md").write_text(_adr_text(1))
    with pytest.raises(RecordError, match="0002-x.md.*id"):
        load(ADR, unpadded)

    with pytest.raises(RecordError, match="bogus_unknown_field"):
        parse(_adr_text(1, extra="bogus_unknown_field: true\n"), ADR)

    with pytest.raises(RecordError, match="status"):
        parse(_adr_text(1, status="proposed"), ADR)


def test_an_adr_body_requires_four_sections_in_order_and_allows_options_to_be_absent():
    front = "---\nid: 1\ntitle: T\nstatus: accepted\ndate: 2026-09-01\n---\n"

    with_options = (
        "\n## Context\n\nx\n\n## Decision\n\ny\n\n## Options considered\n\no\n\n"
        "## Principles\n\nJudged against no principle.\n\n## Consequences\n\nz\n"
    )
    record = parse(front + with_options, ADR)
    assert "Options considered" in record.sections
    assert parse(front + _ADR_BODY, ADR).sections.get("Options considered") is None

    missing = {
        "Context": "\n## Decision\n\ny\n\n## Principles\n\nJudged against no principle.\n\n## Consequences\n\nz\n",
        "Decision": "\n## Context\n\nx\n\n## Principles\n\nJudged against no principle.\n\n## Consequences\n\nz\n",
        "Principles": "\n## Context\n\nx\n\n## Decision\n\ny\n\n## Consequences\n\nz\n",
        "Consequences": "\n## Context\n\nx\n\n## Decision\n\ny\n\n## Principles\n\nJudged against no principle.\n",
    }
    for heading, body in missing.items():
        with pytest.raises(RecordError, match=heading):
            parse(front + body, ADR)

    unknown = "\n## Context\n\nx\n\n## Decision\n\ny\n\n## Notes\n\nn\n\n## Principles\n\nJudged against no principle.\n\n## Consequences\n\nz\n"
    with pytest.raises(RecordError, match="Notes"):
        parse(front + unknown, ADR)

    swapped = "\n## Decision\n\ny\n\n## Context\n\nx\n\n## Principles\n\nJudged against no principle.\n\n## Consequences\n\nz\n"
    with pytest.raises(RecordError, match="order"):
        parse(front + swapped, ADR)
