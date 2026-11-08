"""One pure function per integrity rule, each returning the violations it
found. The live test asserts the list is empty. The unit tests assert each
function finds the one defect its broken fixture plants. A rule the driver also
runs lives in `records/rules.py` instead."""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path

import records.kinds
from records.kinds import KINDS, ItemId
from records.load import Record, load
from records.rules import (
    Violation,
    as_backlog,
    check_priority,
    cited_items,
    context_section,
    first_cited_item,
    records_by_id,
    spec_files,
    spec_paths,
)

# Items 1–177 keep their numbers (`records/kinds.py`). `check_ids` refuses a later number.
LAST_NUMBERED = 177

# Where a live `item N` is a promise someone can follow today. Not
# `docs/evidence/`: dated primary records, true on their date.
CITING = (
    "saffron",
    "tests",
    ".saffron/specs",
    "DESIGN.md",
    "docs/appendices",
    "docs/adr",
)
_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".toml", ".sh"}

# `- **62** upholds. <why>`, one per principle an ADR lists. The verb is read to
# whitespace, so `upholds:` is reported as a bad verb rather than as no bullet.
_PRINCIPLE_BULLET = re.compile(r"^- \*\*(\d+)\*\* (\S+)", re.MULTILINE)
_NO_PRINCIPLE = "Judged against no principle."


def _adr(r: Record) -> records.kinds.Adr:
    """Narrow a record's model to `Adr`, the same way `as_backlog` does."""
    if not isinstance(r.model, records.kinds.Adr):
        raise TypeError(f"{r.path}: not an Adr")
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
        if isinstance(r.model.id, str) and as_backlog(r).filed is None:
            # A random id carries no order. `filed:` is what lists it.
            out.append(Violation(r.path, "filed", "a random id needs `filed:`"))
    present = {n for n in counts if isinstance(n, int)}
    if present:
        missing = sorted(set(range(1, max(present) + 1)) - present)
        if missing:
            # Named against the highest id present, the file after which the gap shows.
            highest = records_by_id(records)[max(present)]
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


def check_adr_ids(records: list[Record]) -> list[Violation]:
    """ADR ids run 1, 2, 3 … with no gap or repeat."""
    out: list[Violation] = []
    counts = Counter(_adr(r).id for r in records)
    for r in records:
        adr_id = _adr(r).id
        if counts[adr_id] > 1:
            out.append(Violation(r.path, "id", f"{adr_id} is used more than once"))
    ids = {_adr(r).id for r in records}
    if ids:
        missing = sorted(set(range(1, max(ids) + 1)) - ids)
        if missing:
            # Named against the highest id present, the file after which the gap shows.
            highest = records_by_id(records)[max(ids)]
            out.append(
                Violation(
                    highest.path, "id", f"ids are not contiguous; missing {missing}"
                )
            )
    return out


def check_adr_supersession(records: list[Record]) -> list[Violation]:
    """Supersession is recorded on both sides."""
    out: list[Violation] = []
    by_id = records_by_id(records)
    for r in records:
        m = _adr(r)
        for other in m.supersedes:
            if other not in by_id:
                out.append(
                    Violation(
                        r.path, "supersedes", f"names ADR {other}, which does not exist"
                    )
                )
            elif other >= m.id:
                out.append(
                    Violation(
                        r.path,
                        "supersedes",
                        f"names ADR {other}, which is not lower than {m.id}",
                    )
                )
            elif m.id not in _adr(by_id[other]).superseded_by:
                out.append(
                    Violation(
                        r.path,
                        "supersedes",
                        f"names ADR {other}, but {other} does not list "
                        f"{m.id} in superseded_by",
                    )
                )
        for other in m.superseded_by:
            if other not in by_id:
                out.append(
                    Violation(
                        r.path,
                        "superseded_by",
                        f"names ADR {other}, which does not exist",
                    )
                )
            elif m.id not in _adr(by_id[other]).supersedes:
                out.append(
                    Violation(
                        r.path,
                        "superseded_by",
                        f"names ADR {other}, but {other} does not list "
                        f"{m.id} in supersedes",
                    )
                )
        if m.status == "superseded" and not m.superseded_by:
            out.append(
                Violation(
                    r.path,
                    "superseded_by",
                    "status is superseded but superseded_by is empty",
                )
            )
        if m.superseded_by and m.status != "superseded":
            out.append(
                Violation(
                    r.path, "status", f"superseded_by is set but status is {m.status}"
                )
            )
        if m.status == "deprecated" and m.superseded_by:
            out.append(
                Violation(
                    r.path,
                    "superseded_by",
                    f"status is deprecated but superseded_by is {m.superseded_by}",
                )
            )
    return out


def check_adr_appendices(records: list[Record], letters: set[str]) -> list[Violation]:
    """An ADR's `appendices` names only letters that exist."""
    out: list[Violation] = []
    for r in records:
        m = _adr(r)
        bad = [a for a in m.appendices if a not in letters]
        if bad:
            out.append(
                Violation(r.path, "appendices", f"names {bad}, which do not exist")
            )
    return out


def check_adr_principles(
    records: list[Record], principles: set[int]
) -> list[Violation]:
    """An ADR's `principles` names only numbers an appendix declares, and its
    `## Principles` section has one `upholds` or `departs` bullet per number.
    An empty list is written down as `Judged against no principle.`"""
    out: list[Violation] = []
    for r in records:
        listed = _adr(r).principles
        bad = [p for p in listed if p not in principles]
        if bad:
            out.append(
                Violation(r.path, "principles", f"names {bad}, which do not exist")
            )
        section = r.sections.get("Principles", "")
        if not listed and not (
            section.startswith(_NO_PRINCIPLE) and "\n" not in section
        ):
            out.append(
                Violation(
                    r.path,
                    "principles",
                    f"is empty, so the section is one line beginning `{_NO_PRINCIPLE}`",
                )
            )
        bullets = _PRINCIPLE_BULLET.findall(section)
        counts = Counter(int(n) for n, _ in bullets)
        for n, verb in bullets:
            if verb not in ("upholds.", "departs."):
                out.append(
                    Violation(
                        r.path,
                        "principles",
                        f"the bullet for {n}'s verb is {verb}, not upholds. or departs.",
                    )
                )
        for n, c in sorted(counts.items()):
            if c > 1:
                out.append(
                    Violation(
                        r.path, "principles", f"the bullet for {n} appears {c} times"
                    )
                )
        if missing := sorted(set(listed) - set(counts)):
            out.append(
                Violation(
                    r.path, "principles", f"lists {missing} and no bullet names them"
                )
            )
        if extra := sorted(set(counts) - set(listed)):
            out.append(
                Violation(
                    r.path,
                    "principles",
                    f"bullets name {extra}, which principles does not list",
                )
            )
    return out


def check_links(records: list[Record]) -> list[Violation]:
    by_id = records_by_id(records)
    out: list[Violation] = []
    for r in records:
        m = as_backlog(r)
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
            elif as_backlog(by_id[target]).status == "superseded":
                out.append(
                    Violation(
                        r.path, "superseded_by", f"item {target} is itself superseded"
                    )
                )
    return out


def check_spec_ids_unique(root: Path) -> list[Violation]:
    """`spec_files` keeps one file per id. A second one would vanish from it."""
    by_id: dict[str, list[Path]] = {}
    for spec_id, path in spec_paths(root):
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
        for spec in as_backlog(r).specs
        if spec not in specs
    ]


def check_cites_resolve(records: list[Record], sections: set[str]) -> list[Violation]:
    return [
        Violation(r.path, "cites", f"{cite} is not a DESIGN.md section")
        for r in records
        for cite in as_backlog(r).cites
        if cite.lstrip("§") not in sections
    ]


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
    # tests/records/ quotes citations as data, not promises, so it is never scanned.
    return _walk(root, CITING, (root / "tests" / "records",))


def check_item_citations(root: Path, ids: set[ItemId]) -> list[Violation]:
    out: list[Violation] = []
    for path in _citing_files(root):
        for n in sorted(cited_items(path.read_text()) - ids, key=str):
            out.append(
                Violation(path, "item", f"cites backlog item {n}, which does not exist")
            )
    return out


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
    "docs/adr",
)


def check_done_specs_are_done(records: list[Record], root: Path) -> list[Violation]:
    specs = spec_files(root)
    out: list[Violation] = []
    for r in records:
        if as_backlog(r).status != "done":
            continue
        for spec in as_backlog(r).specs:
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
    by_id = records_by_id(records)
    out: list[Violation] = []
    for spec_id, path in spec_files(root).items():
        context = context_section(path.read_text())
        n = first_cited_item(context)
        if n is None:
            continue
        item = by_id.get(n)
        if item is None:
            continue  # check_item_citations reports it
        if spec_id not in as_backlog(item).specs:
            out.append(
                Violation(
                    item.path, "specs", f"{spec_id} cites this item and is not listed"
                )
            )
        if path.parent.name == "done" and as_backlog(item).status == "open":
            out.append(
                Violation(item.path, "status", f"open, but {spec_id} is in done/")
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
        m = as_backlog(r)
        if m.status not in ("open", "partial"):
            continue
        record = r.sections.get("Record", "")
        named = {int(x) for x in _OPEN_AS.findall(record)}
        for n in sorted(set(m.awaiting) | named):
            if (message := problem(n, n in m.awaiting, record)) is not None:
                out.append(Violation(r.path, "awaiting", message))
    return out


def head_commits(root: Path) -> frozenset[str]:
    """Every commit HEAD contains, as full shas. Needs CI's full clone."""
    log = subprocess.run(
        ["git", "-C", str(root), "rev-list", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return frozenset(log.split())


def check_commits_reachable(
    records: list[Record], reachable: frozenset[str] | None
) -> list[Violation]:
    """A cited commit is in HEAD's history. A rebase or a squash replaces a
    commit, and the record then names one `main` never held (stack #617).
    `None` means no history was read, which says nothing about any commit."""
    if reachable is None:
        return []
    return [
        Violation(
            r.path,
            "commits",
            f"{sha} is not in HEAD's history: a rebase or a squash replaced it. "
            "Cite the pull request in prs, or the commit that landed",
        )
        for r in records
        for sha in as_backlog(r).commits
        if not any(full.startswith(str(sha)) for full in reachable)
    ]


def check_no_old_path(root: Path) -> list[Violation]:
    # tests/records/ quotes the old path as data. .saffron/specs/done/ is dated history.
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
    *,
    principles: set[int],
    merged: frozenset[int] = frozenset(),
    building: int | None = None,
    reachable: frozenset[str] | None = None,
) -> list[Violation]:
    records = load(KINDS["backlog"], root)
    appendices = load(KINDS["appendix"], root)
    adrs = load(KINDS["adr"], root)
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
        + check_commits_reachable(records, reachable)
        + check_appendix_letters(appendices)
        + check_adr_ids(adrs)
        + check_adr_supersession(adrs)
        + check_adr_principles(adrs, principles)
        + check_adr_appendices(adrs, {str(r.model.id) for r in appendices})
    )
