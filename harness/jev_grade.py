"""Grade Jev's noise score on review notes, as the pre-registration fixes it.

`docs/evidence/2026-10-02-jev-noise-preregistration.md` holds the rules. This
module holds no I/O, so the part that decides the result is the part with tests.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

CUTOFF = 0.5
ENOUGH_NOISE = 40
_Q2 = re.compile(
    r"earl:subject <urn:software-factory:jev:[^:]+:[^:]+:([^>]+)> ;\s*"
    r"earl:test jev:Q2 ;.*?jev:distribution (\".*?\")\^\^rdf:JSON",
    re.S,
)


@dataclass(frozen=True)
class Note:
    verified: str
    disposition: str
    # None when Jev gave no Q2 answer. Such a note counts unflagged.
    noise: float | None


@dataclass(frozen=True)
class Grade:
    noise: int
    caught: int
    acted: int
    flagged_acted: int

    @property
    def verdict(self) -> str:
        if self.noise < ENOUGH_NOISE:
            return "inconclusive"
        catch = 2 * self.caught >= self.noise
        cost = 20 * self.flagged_acted <= self.acted
        return "pass" if catch and cost else "fail"


def noise_scores(ttl: str) -> dict[str, float]:
    """Each finding id's Q2 probability of severity 0, read from `jev.ttl`."""
    return {
        fid: json.loads(json.loads(literal)).get("0", 0.0)
        for fid, literal in _Q2.findall(ttl)
    }


def round_notes(findings: str, labels: str, ttl: str | None) -> list[Note]:
    """A review round's notes, or none unless its labels are schema 2."""
    doc = json.loads(labels)
    if doc.get("schema") != 2:
        return []
    scores = noise_scores(ttl) if ttl is not None else {}
    notes = []
    for finding in json.loads(findings):
        if finding["severity"] != "note":
            continue
        label = doc["findings"][finding["id"]]
        notes.append(
            Note(label["verified"], label["disposition"], scores.get(finding["id"]))
        )
    return notes


def grade(notes: list[Note]) -> Grade:
    def flagged(n: Note) -> bool:
        return n.noise is not None and n.noise >= CUTOFF

    noise = [n for n in notes if n.verified == "not-a-defect"]
    acted = [n for n in notes if n.verified == "real" and n.disposition != "no-action"]
    return Grade(
        noise=len(noise),
        caught=sum(map(flagged, noise)),
        acted=len(acted),
        flagged_acted=sum(map(flagged, acted)),
    )
