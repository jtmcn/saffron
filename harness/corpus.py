"""A corpus of fixtures, and the one number a pass reports.

`lens_scoring` answers a question about one run and one defect. This composes
it across fixtures, because a prompt change cannot be read through one
fixture's noise (`docs/evidence/2026-09-08-lens-scoring-second-pass.md`: the
per-defect scores moved by a third between two passes that changed nothing
relevant, while the blocker count stayed identical).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from harness.lens_scoring import (
    Fixture,
    LensErrored,
    Score,
    calibrate,
    load_fixture,
    score_pass,
)
from saffron.phases.review import LENSES, LensReview


def load_corpus(root: Path) -> list[Fixture]:
    """Every fixture under `root`, ordered by spec id.

    A directory declares itself a fixture by holding a `fixture.toml`; a
    README or a stray export beside them is not one. Ordered so a pass's
    fixtures, its output files and its table all agree without a caller
    sorting three times.
    """
    found = [
        load_fixture(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "fixture.toml").is_file()
    ]
    return sorted(found, key=lambda fixture: fixture.spec_id)


def calibrate_corpus(fixtures: Sequence[Fixture]) -> None:
    """Every fixture's own recorded answer, before any money is spent.

    Raises on the first failure rather than collecting them: a pass must not
    start with one predicate known wrong, and the message names which.
    """
    for fixture in fixtures:
        calibrate(fixture)


@dataclass(frozen=True)
class CorpusScore:
    """A pass over the corpus. `declared` counts the defects of fixtures that
    produced a scored run, never all of them: a dropped fixture leaves the
    denominator rather than contributing misses."""

    per_fixture: dict[str, dict[str, Score]]
    dropped: tuple[str, ...]

    @property
    def declared(self) -> int:
        return sum(len(scores) for scores in self.per_fixture.values())

    @property
    def seen(self) -> int:
        return sum(
            s.seen > 0 for scores in self.per_fixture.values() for s in scores.values()
        )

    @property
    def graded(self) -> int:
        return sum(
            s.graded > 0
            for scores in self.per_fixture.values()
            for s in scores.values()
        )


def score_corpus(
    fixtures: Sequence[Fixture],
    runs: Mapping[str, Sequence[Sequence[LensReview]]],
    expect: Collection[str] = tuple(LENSES),
) -> CorpusScore:
    """k/n per fixture, and one aggregate over defects.

    `seen` and `graded` count *defects*, not runs: at n=1 a defect contributes
    0 or 1, and at higher n a defect seen in any run counts once. That keeps
    the aggregate comparable across passes of different depth, which is the
    whole reason it exists.
    """
    per_fixture: dict[str, dict[str, Score]] = {}
    dropped: list[str] = []
    for fixture in fixtures:
        try:
            per_fixture[fixture.spec_id] = score_pass(
                fixture, runs.get(fixture.spec_id, []), expect
            )
        except LensErrored:
            dropped.append(fixture.spec_id)
    if not per_fixture:
        raise LensErrored(
            f"no fixture survived scoring — {len(fixtures)} fixture(s), "
            f"{len(dropped)} dropped. Nothing here is a measurement."
        )
    return CorpusScore(per_fixture=per_fixture, dropped=tuple(dropped))


def anchored_blockers(
    runs: Mapping[str, Sequence[Sequence[LensReview]]],
) -> dict[str, list[int]]:
    """Anchored blockers per run, per fixture.

    Unanchored findings are excluded: reconciliation could not place them in
    the diff, so they would not have routed the pull request anywhere (§5.5).
    """
    return {
        spec_id: [
            sum(
                finding.severity == "blocker" and finding.anchored
                for review in run
                for finding in review.findings
            )
            for run in fixture_runs
        ]
        for spec_id, fixture_runs in runs.items()
    }


def render_corpus_table(
    fixtures: Sequence[Fixture],
    score: CorpusScore,
    blockers: Mapping[str, list[int]],
) -> str:
    """The pass as markdown, for pasting into a `docs/evidence/` record.

    The aggregate leads, because it is the number Track C reads; the per-fixture
    rows are under it so a moved aggregate can be attributed.
    """
    lines = [
        f"**{score.graded}/{score.declared} declared defects graded** "
        f"({score.seen}/{score.declared} seen) across "
        f"{len(score.per_fixture)} fixture(s).",
        "",
        "| Fixture | Defect | Seen | Graded | Anchored blockers |",
        "|---|---|---|---|---|",
    ]
    for fixture in fixtures:
        scores = score.per_fixture.get(fixture.spec_id)
        if scores is None:
            continue
        counts = ", ".join(str(n) for n in blockers.get(fixture.spec_id, []))
        for defect in fixture.defects:
            entry = scores[defect.id]
            lines.append(
                f"| {fixture.spec_id} | `{defect.id}` "
                f"| {entry.seen}/{entry.runs} | {entry.graded}/{entry.runs} "
                f"| {counts} |"
            )
    if score.dropped:
        lines += [
            "",
            f"**{len(score.dropped)} fixture(s) dropped** — a lens errored, so "
            f"they say nothing about their diff and are in no n above: "
            f"{', '.join(score.dropped)}.",
        ]
    return "\n".join(lines)
