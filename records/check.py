"""One pure function per integrity rule, each returning the violations it
found. The live test asserts the list is empty; the unit tests assert each
function finds the one defect its broken fixture plants."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from records.kinds import KINDS
from records.load import Record, load, split_sections

# Where a live `item N` is a promise someone can follow today. Not
# `docs/evidence/`: dated primary records, true on their date.
CITING = ("saffron", "tests", ".saffron/specs", "DESIGN.md")
_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".sh"}

# `item 33`, `items 65, 72`, `items **81**–**85**`, `BACKLOG item 118`,
# `items 71/75/80`. A digit run is not followed by another digit, so
# `item 1000` does not read as `item 100`. A range reads its endpoints, as
# the § citation test does for appendices.
_ITEMS = re.compile(
    r"(?i)\b(?:backlog\s+)?items?\s+"
    r"((?:\*{0,2}\d{1,3}(?!\d)\*{0,2}(?:\s*(?:,|and|–|—|-|/)\s*)?)+)"
)
_NUM = re.compile(r"\d+")
_SPEC_FILENAME = re.compile(r"^([A-Za-z0-9]+-\d+)-")


@dataclass(frozen=True)
class Violation:
    path: Path
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.field}: {self.message}"


def _ids(records: list[Record]) -> dict[int, Record]:
    return {r.model.id: r for r in records}


def check_ids(records: list[Record]) -> list[Violation]:
    out: list[Violation] = []
    counts = Counter(r.model.id for r in records)
    for r in records:
        if counts[r.model.id] > 1:
            out.append(Violation(r.path, "id", f"{r.model.id} is used more than once"))
    present = set(counts)
    if present:
        missing = sorted(set(range(1, max(present) + 1)) - present)
        if missing:
            # Named against the highest id present, the file after which the gap shows.
            highest = _ids(records)[max(present)]
            out.append(
                Violation(
                    highest.path,
                    "id",
                    f"ids are not contiguous; missing {missing}",
                )
            )
    return out


def check_links(records: list[Record]) -> list[Violation]:
    by_id = _ids(records)
    out: list[Violation] = []
    for r in records:
        m = r.model
        for other in getattr(m, "related", []):
            if other not in by_id:
                out.append(
                    Violation(
                        r.path, "related", f"names item {other}, which does not exist"
                    )
                )
        target = getattr(m, "superseded_by", None)
        if target is not None:
            if target not in by_id:
                out.append(
                    Violation(
                        r.path,
                        "superseded_by",
                        f"names item {target}, which does not exist",
                    )
                )
            elif by_id[target].model.status == "superseded":
                out.append(
                    Violation(
                        r.path, "superseded_by", f"item {target} is itself superseded"
                    )
                )
    return out


def spec_files(root: Path) -> dict[str, Path]:
    """Spec id → file, over the queue and `done/`."""
    found: dict[str, Path] = {}
    for path in (root / ".saffron" / "specs").glob("**/*.md"):
        match = _SPEC_FILENAME.match(path.name)
        if match is not None:
            found[match.group(1)] = path
    return found


def check_specs_resolve(records: list[Record], root: Path) -> list[Violation]:
    specs = spec_files(root)
    return [
        Violation(r.path, "specs", f"{spec} has no file under .saffron/specs/")
        for r in records
        for spec in getattr(r.model, "specs", [])
        if spec not in specs
    ]


def check_cites_resolve(records: list[Record], sections: set[str]) -> list[Violation]:
    return [
        Violation(r.path, "cites", f"{cite} is not a DESIGN.md section")
        for r in records
        for cite in getattr(r.model, "cites", [])
        if cite.lstrip("§") not in sections
    ]


def cited_items(text: str) -> set[int]:
    return {int(n) for m in _ITEMS.finditer(text) for n in _NUM.findall(m.group(1))}


def _walk(root: Path, surfaces: tuple[str, ...], skip: tuple[Path, ...]) -> list[Path]:
    """Every file under `surfaces`, in `_SUFFIXES`, outside any `skip` prefix."""
    out: list[Path] = []
    for name in surfaces:
        path = root / name
        candidates = (
            [path] if path.is_file() else path.rglob("*") if path.is_dir() else []
        )
        out.extend(
            p
            for p in candidates
            if p.is_file()
            and p.suffix in _SUFFIXES
            and not any(s in p.parents for s in skip)
        )
    return sorted(out)


def _citing_files(root: Path) -> list[Path]:
    # tests/records/ quotes citations as data, not promises — never scanned.
    return _walk(root, CITING, (root / "tests" / "records",))


def check_item_citations(root: Path, ids: set[int]) -> list[Violation]:
    out: list[Violation] = []
    for path in _citing_files(root):
        for n in sorted(cited_items(path.read_text()) - ids):
            out.append(
                Violation(path, "item", f"cites backlog item {n}, which does not exist")
            )
    return out


def first_cited_item(text: str) -> int | None:
    """The first number of the first `_ITEMS` match, in document order — the
    item a spec's `## Context` came from, not the background it also names."""
    match = _ITEMS.search(text)
    if match is None:
        return None
    return int(_NUM.findall(match.group(1))[0])


def _context_section(spec_text: str) -> str:
    # maxsplit=1: a `---` rule inside the body must not truncate the Context.
    body = spec_text.split("\n---\n", 1)[-1]
    return split_sections(body).get("Context", "")


OLD_PATH = "docs/BACKLOG.md"
LIVE_SURFACES = (
    "saffron",
    "tests",
    ".saffron/specs",
    "CLAUDE.md",
    "DESIGN.md",
    "README.md",
    "docs/agents",
)

_TIER_HEADING = re.compile(r"^### Tier (\d)\b")
_OTHER_HEADING = re.compile(r"^#{2,3} ")
_STRUCK = re.compile(r"~~\*\*(\d+)\*\*~~")
_BOLD = re.compile(r"(?<!~)\*\*(\d+)\*\*(?!~)")


def check_done_specs_are_done(records: list[Record], root: Path) -> list[Violation]:
    specs = spec_files(root)
    out: list[Violation] = []
    for r in records:
        if r.model.status != "done":
            continue
        for spec in getattr(r.model, "specs", []):
            path = specs.get(spec)
            if path is not None and path.parent.name != "done":
                out.append(
                    Violation(
                        r.path,
                        "specs",
                        f"item is done but {spec} is still in the queue",
                    )
                )
    return out


def check_specs_name_their_items(records: list[Record], root: Path) -> list[Violation]:
    """The inverse link: a spec's `## Context` names the first backlog item it
    cites, and a spec in `done/` leaves that item not open."""
    by_id = _ids(records)
    out: list[Violation] = []
    for spec_id, path in spec_files(root).items():
        context = _context_section(path.read_text())
        n = first_cited_item(context)
        if n is None:
            continue
        item = by_id.get(n)
        if item is None:
            continue  # check_item_citations reports it
        if spec_id not in getattr(item.model, "specs", []):
            out.append(
                Violation(
                    item.path, "specs", f"{spec_id} cites this item and is not listed"
                )
            )
        if path.parent.name == "done" and item.model.status == "open":
            out.append(
                Violation(item.path, "status", f"open, but {spec_id} is in done/")
            )
    return out


def check_priority(records: list[Record], priority_md: Path) -> list[Violation]:
    by_id = _ids(records)
    out: list[Violation] = []
    named_under: dict[int, set[int]] = {}
    tier: int | None = None
    for line in priority_md.read_text().splitlines():
        if heading := _TIER_HEADING.match(line):
            tier = int(heading.group(1))
            continue
        if _OTHER_HEADING.match(line) or line.strip() == "---":
            tier = None  # scope ends; ids are still checked, just not credited
        for n in map(int, _STRUCK.findall(line)):
            if n not in by_id:
                out.append(
                    Violation(
                        priority_md, "index", f"strikes item {n}, which does not exist"
                    )
                )
            elif by_id[n].model.status not in ("done", "superseded"):
                out.append(
                    Violation(
                        priority_md,
                        "index",
                        f"strikes item {n}, which is {by_id[n].model.status}",
                    )
                )
        for n in map(int, _BOLD.findall(line)):
            if n not in by_id:
                out.append(
                    Violation(
                        priority_md, "index", f"names item {n}, which does not exist"
                    )
                )
        if tier is not None:
            for n in map(
                int, _NUM.findall(" ".join(_STRUCK.findall(line) + _BOLD.findall(line)))
            ):
                named_under.setdefault(n, set()).add(tier)
    for n, r in by_id.items():
        t = getattr(r.model, "tier", None)
        if t is not None and t not in named_under.get(n, set()):
            out.append(
                Violation(
                    r.path,
                    "tier",
                    f"item {n} is tier {t}, but PRIORITY.md does not name it under tier {t}",
                )
            )
    return out


def check_no_old_path(root: Path) -> list[Violation]:
    # tests/records/ quotes the old path as data; .saffron/specs/done/ is dated history.
    skip = (root / "tests" / "records", root / ".saffron" / "specs" / "done")
    out = [
        Violation(file, "path", f"names {OLD_PATH}, which no longer exists")
        for file in _walk(root, LIVE_SURFACES, skip)
        if OLD_PATH in file.read_text()
    ]
    return sorted(out, key=lambda v: v.path)


def check_all(root: Path, sections: set[str]) -> list[Violation]:
    records = load(KINDS["backlog"], root)
    priority = root / KINDS["backlog"].directory / "PRIORITY.md"
    return (
        check_ids(records)
        + check_links(records)
        + check_specs_resolve(records, root)
        + check_cites_resolve(records, sections)
        + check_item_citations(root, {int(r.model.id) for r in records})
        + check_done_specs_are_done(records, root)
        + check_specs_name_their_items(records, root)
        + check_priority(records, priority)
        + check_no_old_path(root)
    )
