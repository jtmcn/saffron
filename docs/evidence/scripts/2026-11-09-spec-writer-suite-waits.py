"""Per-round active time, suite waits and suite failures in spec-writer transcripts.

Pass the subagent `.jsonl` paths whose `.meta.json` names `spec-writer`. A
round starts at each prompt that is not a tool result. Tool time is the union
of tool intervals, since parallel calls overlap.
"""

import json
import re
import sys
from collections import Counter
from datetime import datetime

# A whole-suite run, or a poll waiting on one. A single test file is neither.
SUITE = re.compile(r"make check|make test|\bpytest\b(?![^|;&\n]*tests/\S+\.py)")
WAIT = re.compile(r"^\s*until |\bsleep \d")
TREE = (
    "tests/test_queued_specs.py",
    "tests/records",
    "tests/ontology",
    "tests/test_scheduler.py",
)


def stamp(text: str) -> float:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def union(intervals: list[tuple[float, float]]) -> float:
    total, end = 0.0, None
    for start, stop in sorted(intervals):
        if end is None or start > end:
            total, end = total + stop - start, stop
        elif stop > end:
            total, end = total + stop - end, stop
    return total


def result_text(block: dict) -> str:
    body = block.get("content")
    if isinstance(body, str):
        return body
    return " ".join(x.get("text", "") for x in body or [] if isinstance(x, dict))


def main(paths: list[str]) -> None:
    active = waiting = 0.0
    hooks: Counter[str] = Counter()
    tests: Counter[str] = Counter()
    results = 0
    for path in paths:
        rounds: list[list] = []
        pending: dict[str, tuple[float, str]] = {}
        with open(path) as handle:
            lines = handle.readlines()
        for line in lines:
            row = json.loads(line)
            if "timestamp" not in row:
                continue
            at = stamp(row["timestamp"])
            content = row.get("message", {}).get("content")
            blocks = content if isinstance(content, list) else []
            prompt = row.get("type") == "user" and not any(
                b.get("type") == "tool_result" for b in blocks
            )
            if prompt or not rounds:
                rounds.append([at, at, [], []])
            rounds[-1][1] = at
            for block in blocks:
                if block.get("type") == "tool_use":
                    command = block.get("input", {}).get("command", "")
                    pending[block["id"]] = (at, command)
                elif block.get("tool_use_id") in pending:
                    began, command = pending.pop(block["tool_use_id"])
                    rounds[-1][2].append((began, at))
                    if SUITE.search(command) or WAIT.search(command):
                        rounds[-1][3].append((began, at))
                        text = result_text(block)
                        if re.search(r"passed|failed|Passed|Failed", text):
                            results += 1
                            for hook in re.findall(r"^(.+?)\.{3,}Failed", text, re.M):
                                hooks[hook.strip()[:40]] += 1
                            for test in re.findall(
                                r"^FAILED (\S+?)(?:::|\s)", text, re.M
                            ):
                                tests["tree" if test.startswith(TREE) else test] += 1
        cells = []
        for start, stop, _tools, suite in rounds:
            minutes = (stop - start) / 60
            if minutes < 0.5:
                continue
            active += minutes
            waiting += union(suite) / 60
            cells.append(f"{minutes:.1f}m (suite {union(suite) / 60:.1f}m)")
        print(path[-24:-6], " | ".join(cells))
    print(f"active {active:.0f}m, suite waits {waiting:.0f}m")
    print(
        f"suite results {results}, failed hooks {dict(hooks)}, failed tests {dict(tests)}"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
