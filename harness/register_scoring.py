"""Score the register of the claims a lens wrote, from passes already on disk.

`lens_scoring.py` answers whether a declared defect was caught. It says nothing
about how the finding reads, so a prompt change that moves register alone is
invisible to it (`docs/superpowers/specs/2026-09-17-prompt-change-measurement-design.md`).

This module holds no I/O beyond reading a pass directory and it spends nothing:
every claim it scores is already stored in `docs/evidence/passes/*/run-N.json`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Claim:
    """One `claim` string, tagged with what produced it."""

    fixture: str
    run: int
    lens: str
    text: str


def claims_in(pass_dir: Path) -> list[Claim]:
    """Every claim in a pass, in fixture then run then file order.

    A lens that errored carries `findings: null`, and a finding with an empty
    claim is nothing to score. Neither is a miss, so neither raises.
    """
    found = []
    for fixture in sorted(p for p in pass_dir.iterdir() if p.is_dir()):
        for path in sorted(fixture.glob("run-*.json")):
            run = int(path.stem.split("-")[1])
            for lens in json.loads(path.read_text()):
                for finding in lens.get("findings") or []:
                    text = finding.get("claim")
                    if text:
                        found.append(Claim(fixture.name, run, lens["lens"], text))
    return found
