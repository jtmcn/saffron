"""`python -m records`: list, show, grep, new-id. Plain text, one record per line for
`list`, so it composes with grep and reads cleanly in a tool result."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import get_args

from records.kinds import HASH_ID, KINDS, BacklogItem, Status, new_id
from records.load import Record, RecordError, load

REPO_ROOT = Path(__file__).resolve().parents[1]


def _add_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repo root (default: this checkout)",
    )


def _item(record: Record) -> BacklogItem:
    if not isinstance(record.model, BacklogItem):
        raise RecordError("not a backlog item", record.path)
    return record.model


def _line(record: Record) -> str:
    m = _item(record)
    tier = "-" if m.tier is None else str(m.tier)
    return f"{m.id!s:>8}  {m.status:<10}  {tier}  {m.title}"


def _render(record: Record, section: str | None) -> str | None:
    if section is None:
        return record.path.read_text()
    if section not in record.sections:
        have = list(record.sections)
        print(
            f"{record.model.id} has no section {section!r}; it has {have}",
            file=sys.stderr,
        )
        return None
    return record.sections[section] + "\n"


def cmd_list(args: argparse.Namespace) -> int:
    for record in load(KINDS[args.kind], args.root):
        m = _item(record)
        if args.status and m.status != args.status:
            continue
        if args.tier is not None and m.tier != args.tier:
            continue
        print(_line(record))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    records = load(KINDS["backlog"], args.root)
    if args.id.isdigit() or re.fullmatch(HASH_ID, args.id):
        wanted = [r for r in records if str(r.model.id) == args.id]
        if not wanted:
            print(f"no backlog item {args.id}", file=sys.stderr)
            return 1
        text = _render(wanted[0], args.section)
        if text is None:
            return 1
        print(text, end="")
        return 0
    if args.section is not None:
        print(
            f"--section needs an item number; {args.id} lists the items naming it",
            file=sys.stderr,
        )
        return 2
    # Not a kind yet: a spec id answers with the items whose `specs:` name it.
    naming = [r for r in records if args.id in _item(r).specs]
    if not naming:
        print(f"no backlog item names {args.id}", file=sys.stderr)
        return 1
    for record in naming:
        print(_line(record))
    return 0


def cmd_grep(args: argparse.Namespace) -> int:
    try:
        pattern = re.compile(args.pattern, re.IGNORECASE)
    except re.error as exc:
        print(f"invalid pattern {args.pattern}: {exc}", file=sys.stderr)
        return 2
    matched = False
    for record in load(KINDS["backlog"], args.root):
        hits = [line for line in record.body.splitlines() if pattern.search(line)]
        if hits:
            matched = True
            print(f"{record.model.id!s:>8}  {_item(record).title}")
            for hit in hits:
                print(f"     {hit}")
    return 0 if matched else 1


def cmd_new_id(args: argparse.Namespace) -> int:
    print(new_id({r.model.id for r in load(KINDS["backlog"], args.root)}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="records")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="one line per record")
    p.add_argument("kind", choices=sorted(KINDS))
    p.add_argument("--status", choices=get_args(Status))
    p.add_argument("--tier", type=int)
    _add_root(p)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="one record, or the records naming a spec id")
    p.add_argument("id")
    p.add_argument("--section")
    _add_root(p)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("grep", help="id, title and matching lines across bodies")
    p.add_argument("pattern")
    _add_root(p)
    p.set_defaults(func=cmd_grep)

    p = sub.add_parser("new-id", help="an unused id for a new backlog item")
    _add_root(p)
    p.set_defaults(func=cmd_new_id)

    args = parser.parse_args(argv)
    try:
        code = args.func(args)
        sys.stdout.flush()  # surface EPIPE here, not in the shutdown flush
    except RecordError as exc:
        print(exc, file=sys.stderr)
        return 2
    except BrokenPipeError:
        # Python's documented SIGPIPE pattern: silence the exit flush, exit 1.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
