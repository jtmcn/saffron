# The paths the in-cell agent cannot write

Measured on 2026-10-10 for backlog item b-f8fa24. The script is at the end.

## What was run

The script drives `claude-agent-sdk==0.2.142`, the version
`images/cell-base.python.Dockerfile` pins. It passes the options IMPLEMENT
passes: `permission_mode="dontAsk"`, `setting_sources=[]`, and one list for
both `tools` and `allowed_tools`. The list was `Read` and `Write`. The agent
read each candidate file and then wrote one line to it.

The run was on the macOS host, not in a cell. The SDK and its bundled CLI
were the cell's version, and the working directory was a fresh `git init`.

Three runs agree. Two scratch runs covered 36 and 35 paths and cost $1.08
and $0.67. The committed script then ran their union of 69 paths and cost
$5.46. It left out a file named `.claude`, which collides with the
directory. It reproduced every verdict the scratch runs gave.

## Refused

Each refusal was a `permission_denied` event with `decision_reason_type`
set to `mode`. That is the event `SA-0255` logged in run 32.

| Kind | Refused at the root and under `sub/` |
|---|---|
| A file name | `.pre-commit-config.yaml`, `.gitmodules`, `.gitconfig`, `.mcp.json`, `.claude.json`, `.envrc`, `.npmrc`, `.bashrc`, `lefthook.yml` |
| A directory name | `.claude/`, `.vscode/`, `.idea/`, `.husky/`, `.devcontainer/` |

These were refused at the root, and the nested form was not tried:
`.git/hooks/pre-commit`, `.zshrc`, `.profile`, `.bash_profile`,
`.bash_login`, `.zprofile`, `.zshenv`, `.ripgreprc`, `.yarnrc.yml`,
`.lefthook.yml`, `lefthook.yaml` and `.config/git/config`.

A plain file named `.claude` at the root was refused too, in the second
scratch run.

## Written

`control.txt`, `src/control.py`, `.gitignore`, `.gitattributes`,
`.github/workflows/ci.yml`, `.env`, `Makefile`, `pyproject.toml`,
`package.json`, `.editorconfig`, `tox.ini`, `setup.cfg`, `CLAUDE.md`,
`.saffron/policy.yaml`, `.pre-commit-hooks.yaml`, `.tool-versions`,
`.git-blame-ignore-revs`, `.gitignore_global`, `.pypirc`, `.netrc` and
`.ssh/config`.

The near misses were written as well. Those were `.pre-commit-config.yml`,
`.pre-commit-config.yaml.bak`, `docs/.pre-commit-config.yaml.bak`,
`.claudeignore`, `claude/x.md`, `.vscode-test/x.txt` and `.cursor/rules.md`.

## What it means

The refusal keys on a path component, at any depth, and the match is exact.
A suffix, a prefix or a sibling extension escapes it. No Saffron option
grants these paths, since every tool was both offered and auto-approved.
`SA-0255`'s agent tried `Edit`, `Write` and a `Bash` heredoc on
`.pre-commit-config.yaml`, and each was refused.

## What this does not show

- The set belongs to this CLI version. A new `SDK_VERSION` can move it.
- The candidates were chosen by hand, so the set can hold paths no run tried.
- `Edit` and `Bash` were not run against the whole list. Run 32 saw both
  refused on one path.
- Linux was not run. The cell is Linux, and the host is macOS.

## The script

It stays here, not under `docs/evidence/scripts/`, because only
`images/agent_runner.py` may import the SDK (`DESIGN.md` §2.1). Save it and run it
with `uv run`, and pass candidate paths as arguments.

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["claude-agent-sdk==0.2.142"]
# ///
"""Which paths the agent's Claude Code refuses to Write under `dontAsk` (b-f8fa24).

Run with `uv run` and no `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` in the
environment. The bundled CLI then uses the host login. Ten paths cost about $1.
"""

import asyncio
import json
import pathlib
import subprocess
import sys
import tempfile

from claude_agent_sdk import ClaudeAgentOptions, query

CANDIDATES = sys.argv[1:] or [
    "control.txt",
    ".pre-commit-config.yaml",
    "sub/.pre-commit-config.yaml",
    ".pre-commit-config.yml",
    ".gitignore",
    ".gitmodules",
    ".claude/settings.json",
    "sub/.claude/x.md",
    ".vscode-test/x.txt",
    "claude/x.md",
]


async def main() -> None:
    work = pathlib.Path(tempfile.mkdtemp(prefix="unwritable-", dir=".")).resolve()
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    for c in CANDIDATES:
        if c.startswith(".git/"):
            continue
        (work / c).parent.mkdir(parents=True, exist_ok=True)
        (work / c).write_text("old\n")
    listing = "\n".join(f"- {work / c}" for c in CANDIDATES)
    prompt = (
        "For each path below, first Read it, then use the Write tool to write the single "
        "line `new` to it. Some writes will be refused. After a refusal, move on to the "
        "next path. Attempt every path, and retry nothing. Use no tool but Read and Write. "
        "Then reply DONE.\n" + listing
    )
    # The options IMPLEMENT passes, cut to the two tools the probe needs.
    options = ClaudeAgentOptions(
        tools=["Read", "Write"],
        allowed_tools=["Read", "Write"],
        permission_mode="dontAsk",
        setting_sources=[],
        cwd=str(work),
        # Context grows with each path. Measured: 69 paths cost $5.46.
        max_turns=4 * len(CANDIDATES) + 20,
        max_budget_usd=0.12 * len(CANDIDATES) + 1.0,
    )
    denials, cost = 0, None
    async for message in query(prompt=prompt, options=options):
        data = getattr(message, "data", None)
        if isinstance(data, dict) and data.get("subtype") == "permission_denied":
            denials += 1
        cost = getattr(message, "total_cost_usd", cost)
    written = {
        c: (work / c).is_file() and (work / c).read_text().strip() == "new"
        for c in CANDIDATES
    }
    print(
        json.dumps({"written": written, "denials": denials, "cost_usd": cost}, indent=1)
    )


asyncio.run(main())
```
