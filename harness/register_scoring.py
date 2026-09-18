"""Score the register of the claims a lens wrote, from passes already on disk.

`lens_scoring.py` answers whether a declared defect was caught. It says nothing
about how the finding reads, so a prompt change that moves register alone is
invisible to it (`docs/superpowers/specs/2026-09-17-prompt-change-measurement-design.md`).

This module holds no I/O beyond reading a pass directory and it spends nothing:
every claim it scores is already stored in `docs/evidence/passes/*/run-N.json`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from collections.abc import Sequence
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


# Not a spec and not a root document: `trailing-condition` is spec-only and
# `_rendered` looks for spans only in DESIGN.md and CONTEXT.md. A claim is
# neither, and naming one here would score it as something it is not.
_CLAIM_PATH = "claim.md"


def load_gate(repo: Path):
    """The `prose` gate script, loaded by path as `tests/test_prose_gate.py` does."""
    script = repo / ".saffron" / "gates" / "prose.py"
    spec = importlib.util.spec_from_file_location("saffron_prose_gate", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered first: `Hit` is a dataclass under postponed annotations.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def score_claim(gate, text: str, repo: Path) -> tuple[str, ...]:
    """The house-style rule codes this claim carries.

    `root` is the repo because `protected_words` reads `CONTEXT.md`: Saffron's
    own vocabulary must not read as filler.
    """
    return tuple(hit.code for hit in gate.check(text, _CLAIM_PATH, "prose", root=repo))


@dataclass(frozen=True)
class RunScore:
    """One run's claims, scored. `per_1k` is the comparable number."""

    run: int
    claims: int
    words: int
    hits: Counter[str]

    @property
    def per_1k(self) -> float:
        if not self.words:
            return 0.0
        return 1000 * sum(self.hits.values()) / self.words


def score_pass(pass_dir: Path, repo: Path) -> list[RunScore]:
    """Every run in a pass, scored, in run order."""
    gate = load_gate(repo)
    claims: dict[int, list[Claim]] = {}
    for claim in claims_in(pass_dir):
        claims.setdefault(claim.run, []).append(claim)
    scores = []
    for run in sorted(claims):
        hits: Counter[str] = Counter()
        words = 0
        for claim in claims[run]:
            hits.update(score_claim(gate, claim.text, repo))
            words += len(claim.text.split())
        scores.append(RunScore(run, len(claims[run]), words, hits))
    return scores


def spread(scores: Sequence[RunScore]) -> dict[str, tuple[int, int]]:
    """The lowest and highest count of each rule across runs.

    With the prompts unchanged this is the metric's noise floor: a prompt
    change counts as measured only when it moves a rule further than this.
    """
    codes = {code for score in scores for code in score.hits}
    return {
        code: (min(s.hits[code] for s in scores), max(s.hits[code] for s in scores))
        for code in sorted(codes)
    }
