"""One pure function per integrity rule, each returning the violations it
found. The live test asserts the list is empty; the unit tests assert each
function finds the one defect its broken fixture plants."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from records.load import Record

# Where a live `item N` is a promise someone can follow today. Not
# `docs/evidence/`: dated primary records, true on their date.
CITING = ("saffron", "tests", ".saffron/specs", "DESIGN.md")
_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".sh"}

# `item 33`, `items 65, 72`, `items **81**–**85**`, `BACKLOG item 118`. A
# digit run is not followed by another digit, so `item 1000` does not read as
# `item 100`. A range reads its endpoints, as the § citation test does for
# appendices.
_ITEMS = re.compile(
    r"(?i)\b(?:backlog\s+)?items?\s+"
    r"((?:\*{0,2}\d{1,3}(?!\d)\*{0,2}(?:\s*(?:,|and|–|—|-)\s*)?)+)"
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
            out.append(
                Violation(
                    records[0].path.parent,
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


def _citing_files(root: Path) -> list[Path]:
    # tests/records/ quotes citations as data, not promises — never scanned.
    skip = root / "tests" / "records"
    out: list[Path] = []
    for name in CITING:
        path = root / name
        if path.is_file():
            out.append(path)
        elif path.is_dir():
            out.extend(
                p
                for p in path.rglob("*")
                if p.is_file() and p.suffix in _SUFFIXES and skip not in p.parents
            )
    return sorted(out)


def check_item_citations(root: Path, ids: set[int]) -> list[Violation]:
    out: list[Violation] = []
    for path in _citing_files(root):
        for n in sorted(cited_items(path.read_text()) - ids):
            out.append(
                Violation(path, "item", f"cites backlog item {n}, which does not exist")
            )
    return out
