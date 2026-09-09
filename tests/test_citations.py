"""Every `§N` and `Appendix <letter>` citation resolves to something that exists.

`DESIGN.md` section numbers are an API — specs cite them, and `CLAUDE.md` says to
add subsections and never renumber. Nothing enforced that. Roughly 2,400 section
citations and 300 appendix citations reach these documents from `saffron/`,
`tests/`, `.saffron/specs/` and `docs/`, and a renumbering would orphan an unknown
number of them in silence: a citation is prose, so no import breaks and no gate
reads it.

Written while deciding *against* splitting `DESIGN.md` into per-decision files.
The uninsured citation count was the argument for "not now" rather than "not
ever", which makes this the test that would change that answer.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The documents that number their own sections. A citation qualified with a name
# outside this set is not checkable here, and `test_no_citation_names_an_unlisted
# _document` fails rather than skipping it quietly.
NUMBERED = ("DESIGN.md", "CONTEXT.md", "docs/HOST-HARDENING.md")

SUFFIXES = {".md", ".py", ".yaml", ".yml", ".ttl", ".rq"}
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    ".claude",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
}

# Frozen inputs to the scoring harness, `context.md` among them — a snapshot of
# `CONTEXT.md` as one fixture saw it. They are meant to drift from the live file,
# so a test that forced an edit to one is a test that would be weakened later.
SKIP_PATHS = (Path("docs") / "evidence" / "fixtures",)

_HEADING = re.compile(r"^#{2,5} (\d+(?:\.\d+)*[a-z]?)\.? ")
_APPENDIX = re.compile(r"^## Appendix ([A-Z])\b")
# A bolded numbered rule inside a section is an address too: `ontology/RATIONALE.md`
# cites §4.6.2b, which is rule 2b of §4.6 and never a heading.
_RULE = re.compile(r"^\*\*(\d+[a-z]?)\. ")

# The document name binds only when it is *adjacent*. `DESIGN.md:5`'s status line
# names `CONTEXT.md` once and then cites a dozen `DESIGN.md` sections, so "the
# nearest mention anywhere on the line" reads the wrong document six times.
_CITATION = re.compile(
    r"(?:`?(?P<doc>[A-Za-z._-]+\.md)`?(?:'s)?[ ]+)?§\s?(?P<num>\d+(?:\.\d+)*[a-z]?)"
)
_APPENDIX_CITATION = re.compile(r"Appendix ([A-Z])\b")


def addresses(document: Path) -> tuple[set[str], set[str]]:
    """Every address a document defines: headings, plus the bolded numbered rules
    under the heading they appear beneath."""
    sections: set[str] = set()
    appendices: set[str] = set()
    section: str | None = None
    for line in document.read_text().splitlines():
        if heading := _HEADING.match(line):
            section = heading.group(1)
            sections.add(section)
        if appendix := _APPENDIX.match(line):
            appendices.add(appendix.group(1))
            # An appendix's numbered lists are principles, not addresses.
            section = None
        if (rule := _RULE.match(line)) and section:
            sections.add(f"{section}.{rule.group(1)}")
    return sections, appendices


def _by_document() -> tuple[dict[str, set[str]], set[str]]:
    per_document: dict[str, set[str]] = {}
    appendices: set[str] = set()
    for name in NUMBERED:
        sections, found = addresses(ROOT / name)
        per_document[Path(name).name] = sections
        appendices |= found
    return per_document, appendices


def _citing_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.suffix in SUFFIXES
        and not any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts)
        and not any(path.relative_to(ROOT).is_relative_to(skip) for skip in SKIP_PATHS)
    )


def _cited() -> tuple[
    list[tuple[Path, int, str, str | None]], list[tuple[Path, int, str]]
]:
    """Every citation in the repo, as (file, line, number, qualifying document)."""
    sections: list[tuple[Path, int, str, str | None]] = []
    appendices: list[tuple[Path, int, str]] = []
    for path in _citing_files():
        try:
            text = path.read_text()
        except UnicodeDecodeError:  # pragma: no cover - no such file today
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for match in _CITATION.finditer(line):
                sections.append((path, number, match.group("num"), match.group("doc")))
            for match in _APPENDIX_CITATION.finditer(line):
                appendices.append((path, number, match.group(1)))
    return sections, appendices


PER_DOCUMENT, APPENDICES = _by_document()
UNION = set().union(*PER_DOCUMENT.values())
SECTION_CITATIONS, APPENDIX_CITATIONS = _cited()


def test_every_section_citation_resolves():
    """A `§N` names a heading, or a numbered rule beneath one.

    An unqualified citation is checked against the union of the three documents,
    because prose says "§5.4" far more often than it says which file. That is
    weaker than binding each one, and it is the part that catches a renumbering:
    the number has to exist *somewhere*.
    """
    dangling = [
        f"{path.relative_to(ROOT)}:{line} cites §{number}"
        + (f" of {document}" if document else "")
        for path, line, number, document in SECTION_CITATIONS
        # A citation naming a document outside `NUMBERED` is unverifiable, not
        # dangling, and it belongs to the test below. Reporting it here too fails
        # two tests for one defect and names the wrong fix in one of them.
        if document is None or document in PER_DOCUMENT
        if number not in (PER_DOCUMENT[document] if document else UNION)
    ]
    assert not dangling, "citations to sections that do not exist:\n" + "\n".join(
        dangling
    )


def test_every_appendix_citation_resolves():
    """`Appendix <letter>` is unambiguous — only `DESIGN.md` has appendices."""
    dangling = [
        f"{path.relative_to(ROOT)}:{line} cites Appendix {letter}"
        for path, line, letter in APPENDIX_CITATIONS
        if letter not in APPENDICES
    ]
    assert not dangling, "citations to appendices that do not exist:\n" + "\n".join(
        dangling
    )


def test_no_citation_names_an_unlisted_document():
    """A qualified citation whose document is not in `NUMBERED` is unchecked.

    Silently skipping it is how this test would rot: a fourth numbered document
    could accumulate dangling references while the suite stayed green.
    """
    unlisted = sorted(
        {
            document
            for _, _, _, document in SECTION_CITATIONS
            if document is not None and document not in PER_DOCUMENT
        }
    )
    assert not unlisted, (
        f"add these to NUMBERED, or stop citing their sections: {unlisted}"
    )


@pytest.mark.parametrize(
    ("where", "least"),
    [("saffron", 100), ("tests", 100), (".saffron/specs", 100), ("docs", 500)],
)
def test_the_scan_reaches_the_trees_that_cite(where: str, least: int):
    """A scan that reaches nothing passes every assertion above.

    Principle 34 in its file-glob disguise: the counts are floors an ordinary
    edit cannot cross, not the measured figures, so this fails when the walk
    stops reaching a tree rather than when someone deletes a paragraph.
    """
    prefix = Path(where)
    found = sum(
        1
        for path, _, _, _ in SECTION_CITATIONS
        if path.relative_to(ROOT).is_relative_to(prefix)
    )
    assert found >= least, f"only {found} section citations found under {where}/"


def test_a_bolded_rule_is_an_address():
    """§4.6.2b is a citation `ontology/RATIONALE.md` makes and no heading answers."""
    assert "4.6.2b" in PER_DOCUMENT["DESIGN.md"]
    assert "4.6" in PER_DOCUMENT["DESIGN.md"]
