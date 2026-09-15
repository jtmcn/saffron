"""Passes 1 and 2 of the backlog migration (spec: 2026-09-14-backlog-as-records-design.md).

Pass 1 splits `docs/BACKLOG.md` into one file per item with the item text
verbatim under `## Problem`. Pass 2 fills the frontmatter from what a regex
can read without judgement; `specs`, `prs`, `commits` and `related` are
candidates the agent pass confirms or prunes. Run once, from the repo root:

    uv run python docs/evidence/scripts/2026-09-14-split-backlog.py
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "docs" / "BACKLOG.md"
OUT = ROOT / "docs" / "backlog"

ITEM = re.compile(r"^## (\d+)\. (.+)$")
PRIORITY = "## Priority — the order to work in"
NOT_HERE = "## What is *not* here, deliberately"

# Mirrors tests/test_citations.py's `_CITATION`: the document name binds only
# when it is immediately adjacent. A `§` bound to anything other than
# `DESIGN.md` (e.g. `CONTEXT.md §11`) is not a `cites` candidate.
CITATION = re.compile(
    r"(?:`?(?P<doc>[A-Za-z._-]+\.md)`?(?:'s)?[ ]+)?§[ ]{0,2}(?P<num>\d+(?:\.\d+)*[a-z]?)"
)
SPEC = re.compile(r"\bSA-\d{4}\b")
PR = re.compile(r"(?:PR|pull request) #(\d+)", re.IGNORECASE)
COMMIT = re.compile(r"`([0-9a-f]{7,10})`")
ITEMS = re.compile(r"(?i)\b(?:backlog\s+)?items?\s+((?:\*{0,2}\d{1,3}\*{0,2}(?:\s*(?:,|and|–|—|-)\s*)?)+)")
DONE_DATE = re.compile(r"^\*\*Done, (20\d\d-\d\d-\d\d)", re.MULTILINE)
# Two ways the file spells a status line: colon outside the bold
# (`**Status:** done, ...`) or inside it (`**Status: done** — ...`, sometimes
# wrapped, so the closing `**` lands on the next physical line).
STATUS_LINE = re.compile(
    r"^\*\*Status:(?:\*\*[ ]+(?P<rest1>.+)|[ ]+(?s:(?P<rest2>.+?))\*\*(?P<tail2>.*))$",
    re.MULTILINE,
)
STATUS_DATE = re.compile(r"20\d\d-\d\d-\d\d")
PARTIAL_CUES = ("partly", "partial", "half", "done bar", "done except", "bar the")
TIER_HEADING = re.compile(r"^### Tier (\d)\b")
STRUCK = re.compile(r"~~\*\*(\d+)\*\*~~")
BOLD = re.compile(r"\*\*(\d+)\*\*")


def slug(title: str) -> str:
    words = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-").split("-")
    out = ""
    for w in words:
        if len(out) + len(w) + 1 > 70:
            break
        out = f"{out}-{w}" if out else w
    return out


def split(text: str) -> tuple[str, str, list[tuple[int, str, str]], str]:
    lines = text.splitlines()
    p = next(i for i, l in enumerate(lines) if l == PRIORITY)
    first = next(i for i, l in enumerate(lines) if ITEM.match(l))
    end = next(i for i, l in enumerate(lines) if l == NOT_HERE)
    preamble = "\n".join(lines[:p]).rstrip()
    priority = "\n".join(lines[p:first]).rstrip()
    items: list[tuple[int, str, str]] = []
    current: tuple[int, str] | None = None
    body: list[str] = []

    def flush() -> None:
        if current is not None:
            text = "\n".join(body).strip()
            text = re.sub(r"\n---\s*$", "", text).rstrip()  # the `---` rule between items
            items.append((current[0], current[1], text))

    for line in lines[first:end]:
        if m := ITEM.match(line):
            flush()
            current, body = (int(m.group(1)), m.group(2)), []
        else:
            body.append(line)
    flush()
    closing = "\n".join(lines[end:]).rstrip()
    return preamble, priority, items, closing


def tiers(priority: str) -> tuple[dict[int, int], set[int]]:
    """id → lowest tier it is named under; ids struck through anywhere."""
    tier_of: dict[int, int] = {}
    struck: set[int] = set()
    tier: int | None = None
    for line in priority.splitlines():
        if m := TIER_HEADING.match(line):
            tier = int(m.group(1))
            continue
        struck.update(map(int, STRUCK.findall(line)))
        if tier is not None:
            for n in map(int, BOLD.findall(line)):
                tier_of[n] = min(tier, tier_of.get(n, 9))
    return tier_of, struck


def status_of(body: str, struck: bool) -> tuple[str, str | None]:
    dates = DONE_DATE.findall(body)
    m = STATUS_LINE.search(body)
    head = ""
    if m:
        rest1 = m.group("rest1")
        head = rest1 if rest1 is not None else (m.group("rest2") or "") + (m.group("tail2") or "")
    head = head.lower()
    if any(cue in head for cue in PARTIAL_CUES):
        return "partial", None
    if "done" in head or "merged" in head or "closed" in head or dates or struck:
        closed = dates[-1] if dates else None
        if closed is None and (found := STATUS_DATE.search(head)):
            closed = found.group(0)
        return "done", closed
    return "open", None


def cites_of(body: str) -> list[str]:
    addresses = {
        m.group("num")
        for m in CITATION.finditer(body)
        if m.group("doc") is None or m.group("doc") == "DESIGN.md"
    }
    return sorted(
        {f"§{s}" for s in addresses},
        key=lambda s: [int(p) if p.isdigit() else p for p in re.findall(r"\d+|[a-z]", s)],
    )


def frontmatter(n: int, title: str, body: str, tier: int | None, struck: bool) -> dict:
    status, closed = status_of(body, struck)
    related = sorted({int(x) for m in ITEMS.finditer(body) for x in re.findall(r"\d+", m.group(1))} - {n})
    fm: dict = {"id": n, "title": title, "status": status, "tier": tier}
    if closed:
        fm["closed"] = dt.date.fromisoformat(closed)
    fm["specs"] = sorted(set(SPEC.findall(body)))
    fm["prs"] = sorted({int(x) for x in PR.findall(body)})
    fm["commits"] = sorted(set(COMMIT.findall(body)))
    fm["cites"] = cites_of(body)
    fm["related"] = related
    return fm


def main() -> None:
    preamble, priority, items, closing = split(SOURCE.read_text())
    OUT.mkdir(exist_ok=True)
    tier_of, struck = tiers(priority)
    for n, title, body in items:
        fm = frontmatter(n, title, body, tier_of.get(n), n in struck)
        head = yaml.safe_dump(
            fm, default_flow_style=None, allow_unicode=True, sort_keys=False, width=10_000
        ).rstrip()
        (OUT / f"{n:03d}-{slug(title)}.md").write_text(f"---\n{head}\n---\n\n## Problem\n\n{body}\n")
    (OUT / "README.md").write_text(preamble + "\n\n" + closing + "\n")
    (OUT / "PRIORITY.md").write_text("# " + priority.removeprefix("## ") + "\n")
    print(f"{len(items)} items → {OUT}")


if __name__ == "__main__":
    main()
