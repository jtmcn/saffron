"""Split `DESIGN.md`'s appendices into `docs/appendices/`, and later cut them.

`split` writes one record per appendix and leaves `DESIGN.md` alone. `cut`
proves the records rebuild the appendix range byte for byte, then removes it.
Design: docs/superpowers/specs/2026-09-18-appendices-as-records-design.md.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from records.kinds import KINDS, Appendix
from records.load import load

ROOT = Path(__file__).resolve().parents[3]
DESIGN = ROOT / "DESIGN.md"
OUT = ROOT / KINDS["appendix"].directory
HEADING = re.compile(r"^## Appendix ([A-Z]) — (.*)$", re.MULTILINE)
ROW = re.compile(
    r"^\| \*\*([A-Z])\*\* \| ([0-9, ]+) \| (.*) \| [0-9–]* \|$", re.MULTILINE
)
FIRST = "\n## Appendix A — "


def slug(title: str) -> str:
    bare = re.sub(r"^rev \d+: ", "", title)
    return re.sub(r"[^a-z0-9]+", "-", bare.lower()).strip("-")[:60].rstrip("-")


def split() -> None:
    text = DESIGN.read_text()
    rows = {m.group(1): (m.group(2), m.group(3)) for m in ROW.finditer(text)}
    headings = list(HEADING.finditer(text))
    OUT.mkdir(exist_ok=True)
    for i, m in enumerate(headings):
        letter, title = m.group(1), m.group(2)
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[m.end() + 1 : end]
        revisions, question = rows[letter]
        (OUT / f"{letter}-{slug(title)}.md").write_text(
            "---\n"
            f"id: {letter}\n"
            f"title: {json.dumps(title, ensure_ascii=False)}\n"
            f"revisions: [{revisions}]\n"
            f"question: {json.dumps(question, ensure_ascii=False)}\n"
            "---\n"
            f"{body}"
        )
    print(f"wrote {len(headings)} records to {OUT.relative_to(ROOT)}")


def cut() -> None:
    text = DESIGN.read_text()
    kept = text[: text.index(FIRST) + 1]
    rebuilt = ""
    for r in load(KINDS["appendix"], ROOT):
        assert isinstance(r.model, Appendix)
        rebuilt += f"## Appendix {r.model.id} — {r.model.title}\n{r.body}"
    # `kept` already ends with the newline before `## Appendix A`.
    if kept + rebuilt != text:
        sys.exit("the records do not rebuild DESIGN.md's appendix range; nothing cut")
    # The `---` that closed the principle index before Appendix A closes nothing now.
    kept = kept.rstrip().removesuffix("---").rstrip() + "\n"
    DESIGN.write_text(kept)
    print(f"cut {len(text) - len(kept)} bytes from DESIGN.md")


if __name__ == "__main__":
    {"split": split, "cut": cut}[sys.argv[1]]()
