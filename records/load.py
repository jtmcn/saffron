"""Frontmatter and body → `Record`. Mirrors `saffron/intake.py`'s shape on
purpose, so an agent that can write a spec can write an item; it does not
import it, because `records/` stays outside `saffron/`."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from records.kinds import CLOSED, BacklogItem, Identified, ItemId, Kind, as_id

# Character for character `saffron/intake.py`'s: a file one reads, the other must.
_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
_H2 = re.compile(r"^## (.+?)\s*$")
_FENCE = re.compile(r"^\s*```")
_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")

REQUIRED_SECTIONS = ("Problem", "Done looks like", "Record")

_INT, _BOOL = "tag:yaml.org,2002:int", "tag:yaml.org,2002:bool"


class _Loader(yaml.SafeLoader):
    """SafeLoader minus YAML 1.1's octal ints and `yes`/`no` booleans: `033`
    stays the string "033", so a strict int field refuses it by name."""


_Loader.yaml_implicit_resolvers = {
    first: [(tag, rx) for tag, rx in resolvers if tag not in (_INT, _BOOL)]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver(
    _INT, re.compile(r"^(?:0|[1-9][0-9]*)$"), list("0123456789")
)
_Loader.add_implicit_resolver(_BOOL, re.compile(r"^(?:true|false)$"), list("tf"))


class RecordError(ValueError):
    def __init__(self, message: str, path: Path | None = None) -> None:
        super().__init__(f"{path}: {message}" if path else message)
        self.path = path


@dataclass(frozen=True)
class Record:
    model: Identified
    path: Path
    body: str
    sections: dict[str, str]


def split_sections(body: str) -> dict[str, str]:
    """`## ` headings outside fences open a section; `###` stays inside it."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    fenced = False
    for line in body.splitlines():
        if _FENCE.match(line):
            fenced = not fenced
        if not fenced and (heading := _H2.match(line)):
            current = heading.group(1)
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _preamble(body: str) -> str:
    """Text before the first `## ` heading, fence-aware like `split_sections`."""
    lines: list[str] = []
    fenced = False
    for line in body.splitlines():
        if _FENCE.match(line):
            fenced = not fenced
        if not fenced and _H2.match(line):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def parse(text: str, kind: Kind, path: Path | None = None) -> Record:
    match = _FRONTMATTER.match(text)
    if match is None:
        raise RecordError("no YAML frontmatter block", path)
    raw, body = match.group(1), match.group(2)
    try:
        fields = yaml.load(raw, Loader=_Loader) or {}
    except yaml.YAMLError as exc:
        raise RecordError(f"frontmatter is not valid YAML: {exc}", path) from exc
    if not isinstance(fields, dict):
        raise RecordError("frontmatter is not a mapping", path)
    declared = kind.model.model_fields
    fields = {k: v for k, v in fields.items() if k not in declared or v is not None}
    try:
        model = kind.model.model_validate(fields)
    except ValidationError as exc:
        raise RecordError(f"frontmatter is invalid: {exc}", path) from exc

    preamble = _preamble(body)
    if preamble:
        raise RecordError(f"prose before the first `## ` heading: {preamble!r}", path)
    sections = split_sections(body)
    unknown = [s for s in sections if s not in REQUIRED_SECTIONS]
    if unknown:
        raise RecordError(
            f"unknown section(s) {unknown}; the body is {REQUIRED_SECTIONS}", path
        )
    order = [s for s in REQUIRED_SECTIONS if s in sections]
    if list(sections) != order:
        raise RecordError(
            f"sections out of order: {list(sections)}; the order is {REQUIRED_SECTIONS}",
            path,
        )
    if isinstance(model, BacklogItem):
        _check_sections(model, sections, path)
    return Record(
        model=model, path=path or Path("<text>"), body=body, sections=sections
    )


def _check_sections(
    model: BacklogItem, sections: dict[str, str], path: Path | None
) -> None:
    if "Problem" not in sections:
        raise RecordError("missing required `## Problem` section", path)
    status = model.status
    if status not in CLOSED and not sections.get("Done looks like"):
        raise RecordError(
            f"status {status} needs a non-empty `## Done looks like`", path
        )
    if status == "partial" and not _DATE.search(sections.get("Record", "")):
        raise RecordError(
            "`## Record` needs a dated entry when status is partial", path
        )


def load(kind: Kind, root: Path) -> list[Record]:
    directory = root / kind.directory
    if not directory.is_dir():
        raise RecordError(f"no directory {directory}", path=directory)
    pattern = re.compile(kind.pattern)
    records: list[Record] = []
    for path in sorted(directory.glob("*.md")):
        match = pattern.match(path.name)
        if match is None:
            if path.name in kind.hand_written:
                continue
            raise RecordError(
                f"not a record filename ({kind.pattern}) and not a hand-written file",
                path,
            )
        record = parse(path.read_text(), kind, path)
        if as_id(match.group(1)) != record.model.id:
            raise RecordError(
                f"filename prefix {match.group(1)} but id {record.model.id}", path
            )
        records.append(record)
    return sorted(records, key=order)


def order(record: Record) -> tuple[bool, dt.date, ItemId]:
    """Numbered items by number, then random ids by filing date."""
    m = record.model
    filed = getattr(m, "filed", None) or dt.date.max
    return (
        isinstance(m.id, str),
        filed if isinstance(m.id, str) else dt.date.min,
        m.id,
    )
