"""Score REVIEW's lenses against a diff whose defects are already written down.

`docs/BACKLOG.md` item 79: REVIEW filed 0 blockers on PR #154 and 0 findings on
PR #160, and nobody knows what it would say about a diff with a known defect in
it, because no such diff was kept. Every lens change so far has been argued,
which `CLAUDE.md`'s own rule — a measured fact beats a reasoned one — forbids.

This module is the scorer, and it holds no I/O beyond reading a fixture
directory. The driver that builds a cell and spends money is
`docs/evidence/scripts/2026-09-07-lens-scoring.py`; it is deliberately not
importable from here, because the part that can be silently wrong is this part,
and it is the part that gets tests.

Two numbers per defect, not one. **seen** is anchored, in the declared file and
line range, and mentioning one of the declared phrases, at any severity: did the
lens look at this and say what it is? **graded** additionally requires the
severity the independent review gave it. They answer different questions — Track
C moves a prompt and wants to know whether the lens now sees the defect at all;
item 79's exit criterion is about the grade — and one number would hide a lens
that sees a critical defect and files it as a note.

The phrase list is what separates seeing the defect from landing on its lines.
On the fixture this module was built against, the adequacy lens filed a concern
inside one defect's exact line range about a different property of those same
lines. Positional matching scores that a hit; `calibrate` is the assertion that
it does not.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from saffron.agents.findings import Finding, Severity
from saffron.phases.review import LensReview

# `note` < `concern` < `blocker`, the order `_describe` already renders them in.
SEVERITY_RANK: dict[Severity, int] = {"note": 0, "concern": 1, "blocker": 2}

FROZEN = {
    "diff": "diff.patch",
    "spec_body": "spec_body.md",
    "gates": "gates.txt",
    "context_md": "context.md",
}


class FixtureError(ValueError):
    """The fixture cannot be read, or declares something unscoreable."""


class LensErrored(ValueError):
    """A run carried a lens that did not run, so the run is not a sample.

    `error` is not `fail` (§5.4): a lens that crashed, blew its turn ceiling or
    returned something that is not the schema has said nothing about the diff.
    Averaging it in reads as the lens looking and finding nothing, which is the
    one thing `review.run_lens`'s own comment forbids — and it lands as a miss,
    understating exactly what a pass exists to measure.
    """


class CalibrationError(AssertionError):
    """The predicate no longer reproduces a score that is already known.

    Raised before a paid pass is scored, never after: a predicate that cannot
    answer the one run whose answer is written down may not be trusted with a
    run nobody has read.
    """


@dataclass(frozen=True)
class Defect:
    """One defect a fixture declares, and the predicate that recognises it."""

    id: str
    file: str
    lines: tuple[int, int]
    owner: str
    """The lens whose remit this belongs to. Recorded, never enforced — a
    defect caught by the wrong lens is a fact about disjointness (§5.5) worth
    seeing in the table, not a miss."""
    min_severity: Severity
    must_mention: tuple[str, ...]
    """Lowercased substrings, any one of which is enough. Authored after
    reading one run's vocabulary, which is a real way to tune toward a hit —
    which is why `calibrate` exists."""


@dataclass
class Fixture:
    """A known-bad range, its frozen prompt inputs, and its declared defects."""

    root: Path
    spec_id: str
    pr: int
    base_sha: str
    head_sha: str
    source: str
    recorded_seen: int
    recorded_graded: int
    defects: tuple[Defect, ...]

    def _frozen(self, name: str) -> str:
        path = self.root / FROZEN[name]
        if not path.is_file():
            raise FixtureError(f"{self.spec_id}: frozen input {path} is missing")
        return path.read_text()

    @property
    def diff(self) -> str:
        return self._frozen("diff")

    @property
    def spec_body(self) -> str:
        return self._frozen("spec_body")

    @property
    def gates(self) -> str:
        return self._frozen("gates")

    @property
    def context_md(self) -> str:
        return self._frozen("context_md")

    def recorded_reviews(self) -> list[LensReview]:
        """The real output of the run this fixture was built from.

        Ground truth for `calibrate`, and the reason a fixture is a directory
        rather than a line in a table.
        """
        path = self.root / "recorded-findings.json"
        if not path.is_file():
            raise FixtureError(f"{self.spec_id}: {path} is missing")
        return [
            LensReview(
                lens=row["lens"],
                findings=[Finding(**f) for f in row["findings"]],
                cost_usd=row.get("cost_usd", 0.0),
                error=row.get("error"),
            )
            for row in json.loads(path.read_text())
        ]


@dataclass(frozen=True)
class Match:
    """What one defect got out of one run."""

    seen: bool
    graded: bool
    finding: Finding | None
    """The finding that matched, for the record. `None` when nothing did."""


@dataclass(frozen=True)
class Score:
    """What one defect got across a pass of `runs` runs."""

    runs: int
    """Runs actually scored. Never the number requested — a run with an
    errored lens is dropped, and n has to say so."""
    seen: int
    graded: int
    matches: tuple[Match, ...]
    errored: int = 0
    """Runs dropped because a lens in them did not run. Rendered beside the
    table: a pass quietly averaging four runs as three is the shape of claim
    item 69 charged the mutation-vs-lens record with."""


def _required(table: dict, key: str, where: str):
    """A missing key is a malformed fixture, not a crash. `KeyError` from
    inside a loader reads as a bug in the loader."""
    if key not in table:
        raise FixtureError(f"{where}: no {key}")
    return table[key]


def load_fixture(root: Path) -> Fixture:
    """Read a fixture directory. Does not read the frozen inputs — they are
    large, and a caller that only scores never needs them."""
    declaration = root / "fixture.toml"
    if not declaration.is_file():
        raise FixtureError(f"no fixture.toml in {root}")
    raw = tomllib.loads(declaration.read_text())
    defects = []
    for entry in raw.get("defects", ()):
        where = f"{declaration}: defect {entry.get('id', '?')!r}"
        phrases = tuple(p.lower() for p in entry.get("must_mention", ()))
        if not phrases:
            # An empty list would make `any()` false for every finding, so the
            # defect could never be seen and the fixture would score a
            # permanent, silent 0. Refused at load rather than at read.
            raise FixtureError(
                f"{entry.get('id', '?')}: must_mention is empty, so no finding "
                "could ever match it"
            )
        severity = _required(entry, "min_severity", where)
        if severity not in SEVERITY_RANK:
            raise FixtureError(
                f"{where}: min_severity {severity!r} is not "
                f"one of {sorted(SEVERITY_RANK)}"
            )
        lines = tuple(_required(entry, "lines", where))
        if len(lines) != 2 or lines[0] > lines[1]:
            raise FixtureError(f"{where}: lines must be [low, high]")
        defects.append(
            Defect(
                id=_required(entry, "id", where),
                file=_required(entry, "file", where),
                lines=(lines[0], lines[1]),
                owner=_required(entry, "owner", where),
                min_severity=severity,
                must_mention=phrases,
            )
        )
    if not defects:
        raise FixtureError(f"{root}: declares no defects")
    # A phrase in two defects' lists credits one claim to both, so k/n stops
    # being per-defect. Narrow: it catches a copied list, not this fixture's own
    # failure — `dirty` was unique and still matched the other defect's claim,
    # which only the regression tests' real claim text catches.
    for defect in defects:
        for other in defects:
            shared = set(defect.must_mention) & set(other.must_mention)
            if other.id != defect.id and shared:
                raise FixtureError(
                    f"{declaration}: {defect.id} and {other.id} both declare "
                    f"{sorted(shared)}, so a claim carrying it scores both"
                )
    where = str(declaration)
    return Fixture(
        root=root,
        spec_id=_required(raw, "spec_id", where),
        pr=_required(raw, "pr", where),
        base_sha=_required(raw, "base_sha", where),
        head_sha=_required(raw, "head_sha", where),
        source=raw.get("source", ""),
        recorded_seen=_required(raw, "recorded_seen", where),
        recorded_graded=_required(raw, "recorded_graded", where),
        defects=tuple(defects),
    )


def _sees(defect: Defect, finding: Finding) -> bool:
    if not finding.anchored:
        # `anchor` already ruled this points at nothing the diff touched
        # (§5.5). Counting it would let a hallucinating lens score.
        return False
    if finding.file != defect.file:
        return False
    low, high = defect.lines
    if not low <= finding.line <= high:
        return False
    claim = finding.claim.lower()
    return any(phrase in claim for phrase in defect.must_mention)


def match(defect: Defect, findings: Sequence[Finding]) -> Match:
    """The best a run did on one defect.

    Best, not first: a run where one lens sees it as a note and another as a
    blocker scores graded, and the finding kept is the one that graded.
    """
    seen = [f for f in findings if _sees(defect, f)]
    if not seen:
        return Match(seen=False, graded=False, finding=None)
    floor = SEVERITY_RANK[defect.min_severity]
    graded = [f for f in seen if SEVERITY_RANK[f.severity] >= floor]
    return Match(
        seen=True,
        graded=bool(graded),
        finding=max(graded or seen, key=lambda f: SEVERITY_RANK[f.severity]),
    )


def score_run(fixture: Fixture, reviews: Sequence[LensReview]) -> dict[str, Match]:
    """One run of every lens, scored against every declared defect.

    Refuses a run in which any lens errored, rather than scoring what is left:
    the lens that owns a defect is often the only one that would have raised
    it, so a run missing that lens scores the defect missed for a reason that
    is not about the lens prompt at all.
    """
    errored = [r for r in reviews if r.error]
    if errored:
        detail = "; ".join(f"{r.lens}: {r.error}" for r in errored)
        raise LensErrored(f"{fixture.spec_id}: {detail}")
    findings = [f for review in reviews for f in review.findings]
    return {d.id: match(d, findings) for d in fixture.defects}


def score_pass(
    fixture: Fixture, runs: Sequence[Sequence[LensReview]]
) -> dict[str, Score]:
    """k/n across the runs of one pass.

    k counts *runs that saw it*, never findings that matched: two matching
    findings in one run are one run that saw it, or a verbose lens outscores an
    accurate one.

    A run with an errored lens is dropped and counted, never scored as a miss
    (`LensErrored`). If that leaves nothing, this raises rather than returning
    `0/0`: a table of zeroes over zero runs reads like a measurement.
    """
    scored = []
    errored = 0
    for run in runs:
        try:
            scored.append(score_run(fixture, run))
        except LensErrored:
            errored += 1
    if not scored:
        raise LensErrored(
            f"{fixture.spec_id}: no run survived scoring — {len(runs)} run(s), "
            f"{errored} with an errored lens. Nothing here is a measurement."
        )
    return {
        d.id: Score(
            runs=len(scored),
            seen=sum(s[d.id].seen for s in scored),
            graded=sum(s[d.id].graded for s in scored),
            matches=tuple(s[d.id] for s in scored),
            errored=errored,
        )
        for d in fixture.defects
    }


def calibrate(fixture: Fixture) -> None:
    """Score the fixture's own recorded findings and check the known answer.

    Called before a paid pass, and again as a test in `make check`. The failure
    it is built to catch is a predicate loosened until a lens looks better: a
    range widened or a phrase dropped far enough that the run item 79 grades
    0 of 2 starts scoring above it.

    Its reach is exactly the lines the recorded findings landed on, and that is
    narrower than it sounds. On `SA-0062` the three recorded findings sit at
    `worktree.py:358`, `worktree.py:379` and `runner.py:308`, so this asserts
    one thing: that the adequacy concern at 379 — inside `truncating-write`'s
    range, about the test rather than about what the raise leaves on disk —
    does not match its phrases. Nothing recorded lands in `dirty-restore`'s
    range at all, so that defect's predicate is **unconstrained here** and its
    guard is the pair of regression tests carrying real claim text instead. A
    fixture whose defects are all missed by the run it was built from can only
    be calibrated where that run happened to look.
    """
    scored = score_run(fixture, fixture.recorded_reviews())
    seen = sum(m.seen for m in scored.values())
    graded = sum(m.graded for m in scored.values())
    if (seen, graded) != (fixture.recorded_seen, fixture.recorded_graded):
        hit = ", ".join(d for d, m in scored.items() if m.seen) or "nothing"
        raise CalibrationError(
            f"{fixture.spec_id}: the predicate scores its own recorded findings "
            f"{seen} seen / {graded} graded, but the fixture declares "
            f"{fixture.recorded_seen} / {fixture.recorded_graded}. Matched: "
            f"{hit}. Fix the predicate, or say in fixture.toml why the recorded "
            "answer changed."
        )


def render_table(fixture: Fixture, scores: dict[str, Score]) -> str:
    """The pass as a markdown table, for pasting into a `docs/evidence/` record.

    n is in every cell rather than in a caption: a score without its sample size
    is the shape of claim item 69 charged the mutation-vs-lens record with.
    """
    lines = [
        f"### {fixture.spec_id} (PR #{fixture.pr}) — {fixture.base_sha[:8]}"
        f"..{fixture.head_sha[:8]}",
        "",
        "| Defect | Owner | Seen | Graded | Where it landed |",
        "|---|---|---|---|---|",
    ]
    for defect in fixture.defects:
        score = scores[defect.id]
        landed = sorted(
            {
                f"`{m.finding.lens}` {m.finding.file.rsplit('/', 1)[-1]}:{m.finding.line}"
                for m in score.matches
                if m.finding is not None
            }
        )
        lines.append(
            f"| `{defect.id}` | {defect.owner} "
            f"| {score.seen}/{score.runs} | {score.graded}/{score.runs} "
            f"| {', '.join(landed) or '—'} |"
        )
    dropped = max((s.errored for s in scores.values()), default=0)
    if dropped:
        lines += [
            "",
            f"**{dropped} run(s) dropped**: a lens errored, so the run says "
            "nothing about the diff and is not in any n above.",
        ]
    return "\n".join(lines)
