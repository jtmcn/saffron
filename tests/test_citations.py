"""Every `§N` and `Appendi<x|ces> <letter>` citation resolves to something that exists.

`DESIGN.md` section numbers are an API — specs cite them, and `CLAUDE.md` says to
add subsections and never renumber. A citation is prose, so a renumbering breaks no
import and trips no gate: it orphans references silently, across `saffron/`,
`tests/`, `.saffron/specs/`, `spikes/`, `images/` and `docs/`.

**What is checked, and what is not.** A citation qualified by an adjacent document
name is checked against that document. An unqualified one is checked against
`DESIGN.md`, per the convention the specs state — *"a bare `§` cites `DESIGN.md`"* —
widened to include the citing file's own sections when that file numbers its own,
because `CONTEXT.md` says "§4 and §5 *here*" about itself. That widening is the one
hole left, and it is six citations wide: in a document that numbers its own, a bare
`§N` is satisfied by either that document or `DESIGN.md` — five inside `CONTEXT.md`
and one inside `docs/HOST-HARDENING.md`. The count is asserted, not asserted-in-prose:
adding a document to `NUMBERED` widens the hole and nothing else would say so.

The rule matters more than it looks. Resolving every unqualified citation against
the union of all three documents — the first version of this file — left **347**
of them unfalsifiable, because `CONTEXT.md` defines exactly `1`–`11` and so shadows
every top-level `DESIGN.md` section: renumbering `## 9.` dangled nothing.

Written while deciding *against* splitting `DESIGN.md` into per-decision files.
It is what let the appendices move out as records with every letter intact
(Appendix U).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from records.kinds import KINDS
from records.load import load
from saffron.agents import context

ROOT = Path(__file__).resolve().parents[1]

# The documents that number their own sections. A citation qualified with a name
# outside this set is not checkable here, and `test_no_citation_names_an_unlisted
# _document` fails rather than skipping it quietly.
NUMBERED = ("DESIGN.md", "CONTEXT.md", "docs/HOST-HARDENING.md")
DEFAULT = "DESIGN.md"

# `.sh`, `.conf`, `.plist` and the Dockerfiles are here because they cite too:
# `spikes/cell-runtime.sh` alone carries ten, four of them `Appendix G`, and a
# rename would have orphaned every one of them under the first suffix list.
SUFFIXES = {
    ".md",
    ".py",
    ".yaml",
    ".yml",
    ".ttl",
    ".rq",
    ".sh",
    ".toml",
    ".conf",
    ".plist",
    ".Dockerfile",
}
NAMES = {"Dockerfile"}
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
# They carry no dangling citation today; this is about who owns them, not cover.
SKIP_PATHS = (Path("docs") / "evidence" / "fixtures",)

_FENCE = re.compile(r"^\s*```")
_ANY_H2 = re.compile(r"^## ")
_HEADING = re.compile(r"^#{2,5} (\d+(?:\.\d+)*[a-z]?)\.? ")
# A bolded numbered rule inside a section is an address too: `ontology/RATIONALE.md`
# cites §4.6.2b, which is rule 2b inside §4.6 and no heading anywhere.
_RULE = re.compile(r"^\*\*(\d+[a-z]?)\. ")

# The document name binds only when it is *adjacent*. `DESIGN.md:5`'s status line
# names `CONTEXT.md` once and then cites a dozen `DESIGN.md` sections, so "the
# nearest mention anywhere on the line" reads the wrong document six times.
_CITATION = re.compile(
    r"(?:`?(?P<doc>[A-Za-z._-]+\.md)`?(?:'s)?[ ]+)?§[ ]{0,2}(?P<num>\d+(?:\.\d+)*[a-z]?)"
)
# Plural and ranged forms are real: "Appendices I–L" (`docs/backlog/`), "Appendices
# F and G" (`docs/appendices/H-what-v0-found.md`). A range checks its endpoints, not its middle.
_APPENDIX_CITATION = re.compile(
    r"Appendi(?:x|ces) ((?:[A-Z]{1,2}\b(?:[ ]*(?:[–—-]|,|and)[ ]*)?)+)"
)


def cited_letters(line: str) -> list[str]:
    """Every appendix letter a line cites, a range read at its endpoints."""
    return [
        letter
        for match in _APPENDIX_CITATION.finditer(line)
        for letter in re.findall(r"\b[A-Z]{1,2}\b", match.group(1))
    ]


def addresses(document: Path) -> set[str]:
    """Every address a document defines: headings, plus the bolded numbered rules
    under the heading they appear beneath.

    Fenced blocks are skipped and any unnumbered `##` closes the current section:
    `DESIGN.md` §3.2 shows a spec's own `## Context` / `## Acceptance criteria`
    headings, and a numbered line under one of those is the example's, not §3.2's.
    """
    sections: set[str] = set()
    section: str | None = None
    fenced = False
    for line in document.read_text().splitlines():
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if heading := _HEADING.match(line):
            section = heading.group(1)
            sections.add(section)
        elif _ANY_H2.match(line):
            section = None
        elif (rule := _RULE.match(line)) and section:
            sections.add(f"{section}.{rule.group(1)}")
    return sections


def _by_document() -> dict[str, set[str]]:
    per_document: dict[str, set[str]] = {}
    for name in NUMBERED:
        per_document[Path(name).name] = addresses(ROOT / name)
    return per_document


def _citing_files() -> list[Path]:
    """Walk with pruning rather than `rglob`, which descends `.venv` and every
    sibling worktree's `.venv` before filtering, at import time, on every run."""
    found: list[Path] = []
    for parent, directories, names in os.walk(ROOT):
        directories[:] = [d for d in directories if d not in SKIP_DIRS]
        here = Path(parent)
        if any(here.relative_to(ROOT).is_relative_to(skip) for skip in SKIP_PATHS):
            directories[:] = []
            continue
        found.extend(
            here / name
            for name in names
            if Path(name).suffix in SUFFIXES or name in NAMES
        )
    return sorted(found)


def _cited() -> tuple[
    list[tuple[Path, int, str, str | None]], list[tuple[Path, int, str]]
]:
    """Every citation in the repo, as (file, line, address, qualifying document)."""
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
            appendices.extend((path, number, letter) for letter in cited_letters(line))
    return sections, appendices


PER_DOCUMENT = _by_document()
APPENDICES = {str(r.model.id) for r in load(KINDS["appendix"], ROOT)}
SECTION_CITATIONS, APPENDIX_CITATIONS = _cited()


def _resolves_against(path: Path, document: str | None) -> set[str]:
    """The addresses a citation at `path` may name.

    Qualified: that document alone. Unqualified: `DESIGN.md`, widened with the
    citing file's own sections when it numbers them, because a bare `§` inside
    `CONTEXT.md` sometimes means `CONTEXT.md`.
    """
    if document is not None:
        return PER_DOCUMENT.get(document, set())
    own = PER_DOCUMENT.get(path.name, set()) if path.name in PER_DOCUMENT else set()
    return PER_DOCUMENT[DEFAULT] | own


def test_a_two_letter_appendix_citation_is_read_whole():
    """Split into single capitals, AA read as two citations of A and passed."""
    # Joined so this file does not itself cite the two-letter id it tests.
    line = " ".join(["Appendix", "AA", "and", "Appendices", "I–L"])
    assert cited_letters(line) == ["AA", "I", "L"]


def test_every_section_citation_resolves():
    """A `§N` names a heading, or a numbered rule beneath one."""
    dangling = [
        f"{path.relative_to(ROOT)}:{line} cites §{number}"
        + (f" of {document}" if document else "")
        for path, line, number, document in SECTION_CITATIONS
        # A citation naming a document outside `NUMBERED` is unverifiable, not
        # dangling, and it belongs to the test below. Reporting it here too fails
        # two tests for one defect and names the wrong fix in one of them.
        if document is None or document in PER_DOCUMENT
        if number not in _resolves_against(path, document)
    ]
    assert not dangling, "citations to sections that do not exist:\n" + "\n".join(
        dangling
    )


def test_the_widening_stays_six_citations_wide():
    """The docstring's "six citations wide" is the one hole left, and prose is
    what this file exists to distrust: a document added to `NUMBERED` that
    renumbers `1`-`N` widens it in silence and every other test stays green.
    """
    shadowed = [
        f"{path.relative_to(ROOT)}:{line} cites §{number}"
        for path, line, number, document in SECTION_CITATIONS
        if document is None
        if path.name in PER_DOCUMENT and path.name != DEFAULT
        if number in PER_DOCUMENT[path.name] and number in PER_DOCUMENT[DEFAULT]
    ]
    assert len(shadowed) == 6, (
        f"the widening is now {len(shadowed)} citations wide, not six — update the "
        f"module docstring or narrow it:\n" + "\n".join(shadowed)
    )


def test_every_appendix_citation_resolves():
    """An appendix letter is unambiguous: every appendix is a record in `docs/appendices/`."""
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
    [
        ("saffron", 100),
        ("tests", 100),
        (".saffron", 100),
        ("docs", 500),
        ("ontology", 20),
        # 1, not the measured 5: all five are in one file, so any floor above
        # one fails when a comment is edited rather than when the walk stops.
        ("spikes", 1),
        ("images", 3),
    ],
)
def test_the_scan_reaches_the_trees_that_cite(where: str, least: int):
    """A scan that reaches nothing passes every assertion above.

    Principle 34 in its file-glob disguise: the counts are floors an ordinary edit
    cannot cross, not the measured figures, so this fails when the walk stops
    reaching a tree rather than when someone deletes a paragraph. `spikes/` and
    `images/` are here because the first suffix list did not reach them at all.
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


def test_saffron_keeps_no_adrs():
    """`CONTEXT.md` §11 refuses a `docs/adr/` tree beside the appendix records, and prose is what failed last time.

    `CLAUDE.md` and `docs/agents/domain.md` promised `docs/adr/` for months. The
    promise was wrong from the day it landed and nothing noticed, because a claim
    in a document has no reader that fails.
    """
    assert not (ROOT / "docs" / "adr").exists(), (
        "docs/adr/ exists — either CONTEXT.md §11 changed its mind and this test "
        "should go, or a directory arrived that the design record does not want"
    )


# A path rooted at the repo, which is what a rename or a spec's retirement breaks.
_ROOTED_PATH = re.compile(
    r"(?<![\w/~.-])((?:\.saffron|saffron|tests|docs|images|ontology|harness)/[\w./*<>-]*)"
)
# Container image tags share the `saffron/` prefix and are not paths.
IMAGE_TAGS = {"saffron/cell-base", "saffron/proxy"}


def test_every_path_claude_md_cites_exists():
    """`CLAUDE.md` is every cell's instruction surface, and its example command
    named `SA-0002`'s spec at the top level for weeks after it was retired to
    `done/`. Specs retire by design, so a concrete spec path is stale on a
    schedule; a placeholder (`SA-NNNN`, `<slug>`) is not, and only its
    directory has to exist."""
    cited = {
        path.rstrip("./")
        for path in _ROOTED_PATH.findall((ROOT / "CLAUDE.md").read_text())
    }
    assert cited >= IMAGE_TAGS, (
        f"{sorted(IMAGE_TAGS - cited)} no longer in CLAUDE.md — drop from IMAGE_TAGS"
    )
    placeholders = {p for p in cited if "NNNN" in p or "<" in p}
    missing = [
        p
        for p in sorted(cited - IMAGE_TAGS - placeholders)
        if not (any(ROOT.glob(p)) if "*" in p else (ROOT / p).exists())
    ] + [p for p in sorted(placeholders) if not (ROOT / p).parent.is_dir()]
    assert missing == [], f"CLAUDE.md cites paths that do not exist: {missing}"


def test_the_context_table_agrees_with_its_headings_and_the_injector():
    """`CONTEXT.md`'s header table names each section and the phases receiving it.

    Three surfaces, hand-maintained, and nothing bound them: the table, the `## N.`
    headings, and `SECTIONS_BY_PHASE`. A section tagged `—` must reach no phase, and
    one tagged with phases must reach at least one — a table that says a section is
    injected while the injector disagrees is the drift `CONTEXT.md` exists to stop.
    """
    text = (ROOT / "CONTEXT.md").read_text()
    rows = {
        int(number): injected.strip()
        for number, _, injected in re.findall(
            r"^\| (\d+) \| ([^|]+) \| ([^|]+) \|$", text, re.MULTILINE
        )
    }
    headings = {int(n) for n in addresses(ROOT / "CONTEXT.md")}
    assert set(rows) == headings, (
        f"table rows {sorted(set(rows) ^ headings)} have no heading, or vice versa"
    )

    injected = {n for phase in context.SECTIONS_BY_PHASE.values() for n in phase}
    for number, cell in rows.items():
        if cell == "—":
            assert number not in injected, f"§{number} is tagged '—' but is injected"
        else:
            assert number in injected, f"§{number} names phases but reaches none"


# Every rule in `.saffron/rules/`, mapped to the phrase in `CLAUDE.md` that carries
# it. Two rules can share one invariant: the runtime pair is a single rule — spell
# your own binary — enforced once per product, which is why the preamble's number
# counts these values and not the files.
GATED = {
    "agent-sdk-import-is-runner-only": "file permitted to import the Agent SDK",
    "container-runtime-is-runtime-only": "may spell their own binary",
    "gate-tool-must-be-executed": "**The `tool` field**",
    "no-reexport": "**Import a name from the module that defines it.**",
    "one-task-driver": "**One module drives a task.**",
    "podman-runtime-is-runtime-only": "may spell their own binary",
    "skip-is-spelled-in-full": "**A skip is spelled in full where it is used.**",
}
COUNTED = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine")


def test_every_gated_rule_is_named_in_claude_md():
    """A rule fires in a cell; `CLAUDE.md` is where an agent reads it first.

    `skip-is-spelled-in-full` landed in PR #241 and reached no line of the standing
    instructions, so for months an agent here could meet a blocking `structure`
    gate the instruction surface never mentioned — which is how `SA-0077` burned a
    turn on it (item 112). Nothing failed, because a rule's own existence is not a
    claim that any reader checks.
    """
    ids = set()
    for path in sorted((ROOT / ".saffron" / "rules").glob("*.yml")):
        found = re.findall(r"^id: (\S+)$", path.read_text(), re.MULTILINE)
        assert len(found) == 1, f"{path.name}: one `id:` expected, found {found}"
        ids.add(found[0])
    assert ids == set(GATED), (
        f"{sorted(ids ^ set(GATED))}: a rule arrived or left. Give it a bullet in "
        "CLAUDE.md's invariants and name it here, or drop it from both"
    )

    text = (ROOT / "CLAUDE.md").read_text()
    unnamed = sorted(rule for rule, phrase in GATED.items() if phrase not in text)
    assert unnamed == [], (
        f"CLAUDE.md no longer carries {unnamed} — restore the bullet, or fix the "
        "phrase here if the wording moved on"
    )


def test_the_invariants_preamble_counts_the_gated_invariants():
    """`CLAUDE.md` said "four" for the whole life of its fifth gated rule.

    The preamble promises to name the gated invariants, so the number is a claim
    about the list below it. It is also the only line that a new rule silently
    falsifies: the bullet can be written and the count left alone.
    """
    expected = len(set(GATED.values()))
    claim = f"The {COUNTED[expected - 1]} marked **(gated)**"
    assert claim in (ROOT / "CLAUDE.md").read_text(), (
        f"CLAUDE.md's invariants preamble does not say {claim!r}, and "
        f"{expected} gated invariants are named below it"
    )
