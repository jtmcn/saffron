"""The record rules a tool outside `tests/` also runs. `records/check.py`
imports them, so `make check` applies the definition the driver prints from."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from records.kinds import RANDOM_ID, BacklogItem, ItemId, as_id
from records.load import _FRONTMATTER, Record, split_sections

# Reads `items 65, 72`, `items **81**–**85**` and `item b-3f9a2c`. A range reads its ends.
# A digit run never ends before another digit, so `item 1000` is not `item 100`.
_ID = rf"(?-i:{RANDOM_ID})\b|\d{{1,3}}(?!\d)"
_ITEMS = re.compile(
    r"(?i)\b(?:backlog\s+)?items?\s+"
    rf"((?:\*{{0,2}}(?:{_ID})\*{{0,2}}(?:\s*(?:,|and|–|—|-|/)\s*)?)+)"
)
_ANY_ID = rf"{RANDOM_ID}|\d+"
_NUM = re.compile(_ANY_ID)
_SPEC_FILENAME = re.compile(r"^([A-Za-z0-9]+-\d+)-")


@dataclass(frozen=True)
class Violation:
    path: Path
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.field}: {self.message}"


def records_by_id(records: list[Record]) -> dict[ItemId, Record]:
    return {r.model.id: r for r in records}


def as_backlog(r: Record) -> BacklogItem:
    """Narrow a record's model to `BacklogItem`. A field read via `getattr` on
    another kind's model would silently check nothing instead of refusing it."""
    if not isinstance(r.model, BacklogItem):
        raise TypeError(f"{r.path}: not a BacklogItem")
    return r.model


def spec_paths(root: Path) -> list[tuple[str, Path]]:
    specs = root / ".saffron" / "specs"
    return [
        (match.group(1), path)
        for path in sorted(specs.glob("**/*.md"))
        if (match := _SPEC_FILENAME.match(path.name)) is not None
    ]


def spec_files(root: Path) -> dict[str, Path]:
    """Spec id → file, over the queue and `done/`."""
    return dict(spec_paths(root))


def cited_items(text: str) -> set[ItemId]:
    return {as_id(n) for m in _ITEMS.finditer(text) for n in _NUM.findall(m.group(1))}


def first_cited_item(text: str) -> ItemId | None:
    """The first id of the first `_ITEMS` match, in document order. It is the
    item a spec's `## Context` came from, not the background it also names."""
    match = _ITEMS.search(text)
    if match is None:
        return None
    return as_id(_NUM.findall(match.group(1))[0])


def context_section(spec_text: str) -> str:
    match = _FRONTMATTER.match(spec_text)
    body = match.group(2) if match else spec_text
    return split_sections(body).get("Context", "")


_TIER_HEADING = re.compile(r"^### Tier (\d)\b")
_OTHER_HEADING = re.compile(r"^#{2,3} ")
_STRUCK = re.compile(rf"~~\*\*({_ANY_ID})\*\*~~")
_BOLD = re.compile(rf"(?<!~)\*\*({_ANY_ID})\*\*(?!~)")


def check_priority(records: list[Record], priority_md: Path) -> list[Violation]:
    if not priority_md.is_file():
        return [Violation(priority_md, "index", "does not exist")]
    by_id = records_by_id(records)
    out: list[Violation] = []
    named_under: dict[ItemId, set[int]] = {}
    tier: int | None = None
    for line in priority_md.read_text().splitlines():
        if heading := _TIER_HEADING.match(line):
            tier = int(heading.group(1))
            continue
        if _OTHER_HEADING.match(line) or line.strip() == "---":
            tier = None  # The scope ends here. Its ids are checked but not credited.
        struck = [as_id(n) for n in _STRUCK.findall(line)]
        bold = [as_id(n) for n in _BOLD.findall(line)]
        for n in struck:
            if n not in by_id:
                out.append(
                    Violation(
                        priority_md, "index", f"strikes item {n}, which does not exist"
                    )
                )
            elif as_backlog(by_id[n]).status not in ("done", "superseded"):
                out.append(
                    Violation(
                        priority_md,
                        "index",
                        f"strikes item {n}, which is {as_backlog(by_id[n]).status}",
                    )
                )
        for n in bold:
            if n not in by_id:
                out.append(
                    Violation(
                        priority_md, "index", f"names item {n}, which does not exist"
                    )
                )
        if tier is not None:
            for n in struck + bold:
                named_under.setdefault(n, set()).add(tier)
    for n, r in by_id.items():
        t = as_backlog(r).tier
        ranked = sorted(named_under.get(n, set()))
        if t is None and ranked:
            out.append(
                Violation(
                    r.path,
                    "tier",
                    f"item {n} has no tier, but PRIORITY.md names it under tier "
                    + " and ".join(map(str, ranked)),
                )
            )
        if t is not None and t not in named_under.get(n, set()):
            out.append(
                Violation(
                    r.path,
                    "tier",
                    f"item {n} is tier {t}, but PRIORITY.md does not name it under tier {t}",
                )
            )
    return out
