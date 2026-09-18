"""One pure function per integrity rule, each returning the violations it
found. The live test asserts the list is empty; the unit tests assert each
function finds the one defect its broken fixture plants. Test support, moved from
`records/`: only these tests ran it."""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from records.kinds import KINDS, RANDOM_ID, BacklogItem, ItemId, as_id
from records.load import _FRONTMATTER, Record, load, split_sections

# Items 1–177 keep their numbers (`records/kinds.py`); `check_ids` refuses a later number.
LAST_NUMBERED = 177

# Where a live `item N` is a promise someone can follow today. Not
# `docs/evidence/`: dated primary records, true on their date.
CITING = ("saffron", "tests", ".saffron/specs", "DESIGN.md", "docs/appendices")
_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".sh"}

# `item 33`, `items 65, 72`, `items **81**–**85**`, `BACKLOG item 118`,
# `items 71/75/80`, `item b-3f9a2c`. A digit run is not followed by another
# digit, so `item 1000` does not read as `item 100`. A range reads its
# endpoints, as the § citation test does for appendices.
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


def _ids(records: list[Record]) -> dict[ItemId, Record]:
    return {r.model.id: r for r in records}


def _backlog(r: Record) -> BacklogItem:
    """Narrow a record's model to `BacklogItem`. A field read via `getattr` on
    another kind's model would silently check nothing instead of refusing it."""
    if not isinstance(r.model, BacklogItem):
        raise TypeError(f"{r.path}: not a BacklogItem")
    return r.model


def check_ids(records: list[Record]) -> list[Violation]:
    out: list[Violation] = []
    counts = Counter(r.model.id for r in records)
    for r in records:
        if counts[r.model.id] > 1:
            out.append(Violation(r.path, "id", f"{r.model.id} is used more than once"))
    for r in records:
        if isinstance(r.model.id, int) and r.model.id > LAST_NUMBERED:
            out.append(
                Violation(
                    r.path,
                    "id",
                    f"numbered ids end at {LAST_NUMBERED}; take one from "
                    "`uv run python -m records new-id`",
                )
            )
        if isinstance(r.model.id, str) and _backlog(r).filed is None:
            # A random id carries no order; `filed:` is what lists it.
            out.append(Violation(r.path, "filed", "a random id needs `filed:`"))
    present = {n for n in counts if isinstance(n, int)}
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


def appendix_letters(n: int) -> list[str]:
    """The first `n` appendix ids: A to Z, then AA, AB, and on."""
    singles = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    return (singles + [a + b for a in singles for b in singles])[:n]


def check_appendix_letters(records: list[Record]) -> list[Violation]:
    ids = [str(r.model.id) for r in records]
    expected = appendix_letters(len(ids))
    if ids == expected:
        return []
    return [
        Violation(
            records[-1].path,
            "id",
            f"appendix letters are {ids}; they run from A with no gap or repeat: {expected}",
        )
    ]


def check_links(records: list[Record]) -> list[Violation]:
    by_id = _ids(records)
    out: list[Violation] = []
    for r in records:
        m = _backlog(r)
        for other in m.related:
            if other not in by_id:
                out.append(
                    Violation(
                        r.path, "related", f"names item {other}, which does not exist"
                    )
                )
        target = m.superseded_by
        if target is not None:
            if target not in by_id:
                out.append(
                    Violation(
                        r.path,
                        "superseded_by",
                        f"names item {target}, which does not exist",
                    )
                )
            elif _backlog(by_id[target]).status == "superseded":
                out.append(
                    Violation(
                        r.path, "superseded_by", f"item {target} is itself superseded"
                    )
                )
    return out


def _spec_paths(root: Path) -> list[tuple[str, Path]]:
    specs = root / ".saffron" / "specs"
    return [
        (match.group(1), path)
        for path in sorted(specs.glob("**/*.md"))
        if (match := _SPEC_FILENAME.match(path.name)) is not None
    ]


def spec_files(root: Path) -> dict[str, Path]:
    """Spec id → file, over the queue and `done/`."""
    return dict(_spec_paths(root))


def check_spec_ids_unique(root: Path) -> list[Violation]:
    """`spec_files` keeps one file per id; a second one would vanish from it."""
    by_id: dict[str, list[Path]] = {}
    for spec_id, path in _spec_paths(root):
        by_id.setdefault(spec_id, []).append(path)
    specs = root / ".saffron" / "specs"
    return [
        Violation(
            paths[0],
            "specs",
            f"{spec_id} is in more than one file: "
            + ", ".join(str(p.relative_to(specs)) for p in paths),
        )
        for spec_id, paths in by_id.items()
        if len(paths) > 1
    ]


def check_specs_resolve(records: list[Record], root: Path) -> list[Violation]:
    specs = spec_files(root)
    return [
        Violation(r.path, "specs", f"{spec} has no file under .saffron/specs/")
        for r in records
        for spec in _backlog(r).specs
        if spec not in specs
    ]


def check_cites_resolve(records: list[Record], sections: set[str]) -> list[Violation]:
    return [
        Violation(r.path, "cites", f"{cite} is not a DESIGN.md section")
        for r in records
        for cite in _backlog(r).cites
        if cite.lstrip("§") not in sections
    ]


def cited_items(text: str) -> set[ItemId]:
    return {as_id(n) for m in _ITEMS.finditer(text) for n in _NUM.findall(m.group(1))}


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


def check_item_citations(root: Path, ids: set[ItemId]) -> list[Violation]:
    out: list[Violation] = []
    for path in _citing_files(root):
        for n in sorted(cited_items(path.read_text()) - ids, key=str):
            out.append(
                Violation(path, "item", f"cites backlog item {n}, which does not exist")
            )
    return out


def first_cited_item(text: str) -> ItemId | None:
    """The first id of the first `_ITEMS` match, in document order — the
    item a spec's `## Context` came from, not the background it also names."""
    match = _ITEMS.search(text)
    if match is None:
        return None
    return as_id(_NUM.findall(match.group(1))[0])


def _context_section(spec_text: str) -> str:
    match = _FRONTMATTER.match(spec_text)
    body = match.group(2) if match else spec_text
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
    "docs/appendices",
)

_TIER_HEADING = re.compile(r"^### Tier (\d)\b")
_OTHER_HEADING = re.compile(r"^#{2,3} ")
_STRUCK = re.compile(rf"~~\*\*({_ANY_ID})\*\*~~")
_BOLD = re.compile(rf"(?<!~)\*\*({_ANY_ID})\*\*(?!~)")


def check_done_specs_are_done(records: list[Record], root: Path) -> list[Violation]:
    specs = spec_files(root)
    out: list[Violation] = []
    for r in records:
        if _backlog(r).status != "done":
            continue
        for spec in _backlog(r).specs:
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
        if spec_id not in _backlog(item).specs:
            out.append(
                Violation(
                    item.path, "specs", f"{spec_id} cites this item and is not listed"
                )
            )
        if path.parent.name == "done" and _backlog(item).status == "open":
            out.append(
                Violation(item.path, "status", f"open, but {spec_id} is in done/")
            )
    return out


def check_priority(records: list[Record], priority_md: Path) -> list[Violation]:
    if not priority_md.is_file():
        return [Violation(priority_md, "index", "does not exist")]
    by_id = _ids(records)
    out: list[Violation] = []
    named_under: dict[ItemId, set[int]] = {}
    tier: int | None = None
    for line in priority_md.read_text().splitlines():
        if heading := _TIER_HEADING.match(line):
            tier = int(heading.group(1))
            continue
        if _OTHER_HEADING.match(line) or line.strip() == "---":
            tier = None  # scope ends; ids are still checked, just not credited
        struck = [as_id(n) for n in _STRUCK.findall(line)]
        bold = [as_id(n) for n in _BOLD.findall(line)]
        for n in struck:
            if n not in by_id:
                out.append(
                    Violation(
                        priority_md, "index", f"strikes item {n}, which does not exist"
                    )
                )
            elif _backlog(by_id[n]).status not in ("done", "superseded"):
                out.append(
                    Violation(
                        priority_md,
                        "index",
                        f"strikes item {n}, which is {_backlog(by_id[n]).status}",
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
        t = _backlog(r).tier
        if t is not None and t not in named_under.get(n, set()):
            out.append(
                Violation(
                    r.path,
                    "tier",
                    f"item {n} is tier {t}, but PRIORITY.md does not name it under tier {t}",
                )
            )
    return out


_OPEN_AS = re.compile(r"\bopen as (?:PR )?#(\d+)")
_MERGE_SUBJECT = re.compile(r"^Merge pull request #(\d+) ")
_PULL_REF = re.compile(r"^refs/pull/(\d+)/")


def merged_prs(root: Path) -> frozenset[int]:
    """Pull requests whose merge commit HEAD contains. Reads merge-commit
    subjects, so it needs full history and a repo that does not squash."""
    log = subprocess.run(
        ["git", "-C", str(root), "log", "--merges", "--format=%s", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return frozenset(
        int(m.group(1))
        for line in log.splitlines()
        if (m := _MERGE_SUBJECT.match(line))
    )


def building_pr(github_ref: str | None) -> int | None:
    """The pull request this CI run builds, from `GITHUB_REF`, or `None`."""
    m = _PULL_REF.match(github_ref or "")
    return int(m.group(1)) if m else None


def _says_merged(text: str, n: int) -> bool:
    return re.search(rf"(?:PR )?#{n} merged|merged as (?:PR )?#{n}\b", text) is not None


def check_awaiting(
    records: list[Record], merged: frozenset[int], building: int | None
) -> list[Violation]:
    """An open item waiting on a pull request says so in `awaiting`, and that
    wait ends when the pull request merges. #287 wrote "open as PR #287 … stays
    open until that merges" into its own records, which then never closed."""

    def problem(n: int, awaited: bool, record: str) -> str | None:
        if n == building:
            return (
                f"#{n} is this pull request: close the item in its own diff "
                f"(status, closed, prs: [{n}]) rather than wait on itself"
            )
        if awaited:
            if n in merged:
                return f"#{n} has merged: close the item, or record what is left and move {n} to prs"
            return None
        if _says_merged(record, n):
            return None
        return (
            f"the record says #{n} is open: list it in awaiting, or, if it "
            f'merged, say "PR #{n} merged" and what that left'
        )

    out: list[Violation] = []
    for r in records:
        m = _backlog(r)
        if m.status not in ("open", "partial"):
            continue
        record = r.sections.get("Record", "")
        named = {int(x) for x in _OPEN_AS.findall(record)}
        for n in sorted(set(m.awaiting) | named):
            if (message := problem(n, n in m.awaiting, record)) is not None:
                out.append(Violation(r.path, "awaiting", message))
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


def check_all(
    root: Path,
    sections: set[str],
    merged: frozenset[int] = frozenset(),
    building: int | None = None,
) -> list[Violation]:
    records = load(KINDS["backlog"], root)
    priority = root / KINDS["backlog"].directory / "PRIORITY.md"
    return (
        check_ids(records)
        + check_links(records)
        + check_spec_ids_unique(root)
        + check_specs_resolve(records, root)
        + check_cites_resolve(records, sections)
        + check_item_citations(root, {r.model.id for r in records})
        + check_done_specs_are_done(records, root)
        + check_specs_name_their_items(records, root)
        + check_priority(records, priority)
        + check_no_old_path(root)
        + check_awaiting(records, merged, building)
        + check_appendix_letters(load(KINDS["appendix"], root))
    )
