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
from harness.probe_check import ProbeResult
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

    `seen` and `graded` count *defects*, not runs: a defect seen in any run
    counts once. That makes the aggregate best-of-n, which rises with
    `--runs` — compare passes of different depth through `graded_per_run`,
    never through this.
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


def graded_per_run(
    fixtures: Sequence[Fixture],
    runs: Mapping[str, Sequence[Sequence[LensReview]]],
) -> list[CorpusScore | None]:
    """Run index k across every fixture, scored alone as one corpus pass —
    one sample of the aggregate per run, which is the spread item 93 asks for.
    `None` where no fixture's run k survived: unscored, never zero."""
    depth = max((len(r) for r in runs.values()), default=0)
    out: list[CorpusScore | None] = []
    for k in range(depth):
        sliced = {sid: list(r[k : k + 1]) for sid, r in runs.items() if len(r) > k}
        try:
            out.append(score_corpus(fixtures, sliced))
        except LensErrored:
            out.append(None)
    return out


@dataclass(frozen=True)
class ProbeScore:
    """The corpus's second number: how many vacuity probes survived their suite."""

    survived: int
    killed: int
    unproven: int
    fixtures: int
    """How many fixtures this invocation actually probed. Not always every
    fixture in the table: recall is re-derived from every run JSON on disk, so
    a `--skip-existing` resume scores eight fixtures and probes three, and the
    summary has to say which set the second number covers."""
    runs: int
    """How many runs per fixture the probes were collected from. This is a
    total, not a rate: `--runs 3` files three chances to name a distinct edge
    where `--runs 1` files one, and only byte-identical edits collapse. Recall
    above is averaged over runs, so without this the two numbers scale
    differently and a reader compares passes that are not comparable."""

    @property
    def asked(self) -> int:
        """Probes that produced an answer. Never the number filed — an
        `unproven` probe says nothing about the lens, so it is in no
        denominator, exactly as a dropped run is in no n."""
        return self.survived + self.killed


def score_probes(
    results: Mapping[str, Sequence[ProbeResult]], *, runs: int
) -> ProbeScore:
    """One aggregate over every fixture's probes.

    `runs` is keyword and required for the same reason `check_probe`'s
    `test_paths` is: a total whose run basis went unstated is the hole, so
    forgetting it is a `TypeError` rather than a number nobody can place.

    Probes, never findings: a finding whose lens was never asked for an edit
    carries no probe and is not a probe that failed.

    A key with an empty list is a fixture that *was* probed and had nothing to
    apply, which is coverage; a fixture missing from `results` was not probed
    at all. That is the whole of `fixtures`.
    """
    flat = [r for rs in results.values() for r in rs]
    return ProbeScore(
        survived=sum(r.verdict == "survived" for r in flat),
        killed=sum(r.verdict == "killed" for r in flat),
        unproven=sum(r.verdict == "unproven" for r in flat),
        fixtures=len(results),
        runs=runs,
    )


def render_probe_summary(score: ProbeScore) -> str:
    """The second line, and what it is not.

    Rendered under the declared-recall aggregate, never beside it: the two are
    not comparable. Recall is over every lens's declared defects; this is one
    lens's vacuity capability, and it is a lower bound — a `killed` probe may
    be a test doing its job or a probe that broke the program, and only a
    person reading the itemised failures can tell.

    The fixture count is in the line for the same reason: a resumed pass
    probes fewer fixtures than it scores, and a number over three fixtures
    beside a recall line over eight is a comparison the document has to refuse
    in writing rather than leave to the reader. The run count is there on that
    same argument — this is a total over the runs, where recall is a rate over
    them, so two passes at different `--runs` do not compare.
    """
    one = score.survived == 1
    return (
        f"**{score.survived} verified {'vacuity' if one else 'vacuities'}** — "
        f"adequacy-lens {'finding' if one else 'findings'} whose named edit "
        f"left the fixture's suite green. {score.survived} of {score.asked} "
        f"probe(s) that answered survived; {score.unproven} unproven and in no "
        f"denominator, over {score.fixtures} fixture(s) probed this invocation "
        f"at {score.runs} run(s) each — which need not be every fixture in the "
        f"table, since recall is re-derived from every run JSON on disk and a "
        f"resumed pass probes only what it ran. A total over those runs, not a "
        f"rate over them, so it does not compare with a pass at a different "
        f"`--runs`. Not comparable with the recall line above either: one lens, and "
        f"a lower bound — a killed probe may have broken the program rather "
        f"than been noticed, which is adjudicated per probe and not computed."
    )


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
    probes: ProbeScore | None = None,
    per_run: Sequence[CorpusScore | None] = (),
) -> str:
    """The pass as markdown, for pasting into a `docs/evidence/` record.

    The aggregate leads, because it is the number Track C reads; the per-fixture
    rows are under it so a moved aggregate can be attributed.

    `probes` is `None` when the pass asked none — a scoring-only re-run,
    `--skip-probes`, or a `--skip-existing` resume that ran no fixture at all.
    Rendering `0 of 0` there would read as a lens that verified nothing, which
    is not what a pass that never applied a probe found out.

    `per_run` renders the best-of-n headline's spread (`graded_per_run`) —
    omitted at one run, where there is none to state.
    """
    lines = [
        f"**{score.graded}/{score.declared} declared defects graded** "
        f"({score.seen}/{score.declared} seen) across "
        f"{len(score.per_fixture)} fixture(s)."
    ]
    if len(per_run) > 1:
        totals = " · ".join(
            "unscored" if s is None else f"{s.graded}/{s.declared}" for s in per_run
        )
        lines += [
            "",
            f"Per run, each scored alone: {totals} graded. The headline counts a "
            "defect graded in any run, so it rises with `--runs`; these are the spread.",
        ]
    lines += [
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
    if probes is not None:
        lines += ["", render_probe_summary(probes)]
    if score.dropped:
        lines += [
            "",
            f"**{len(score.dropped)} fixture(s) dropped** — produced no scored "
            f"run (a lens errored, or the fixture never ran), so they say "
            f"nothing about their diff and are in no n above: "
            f"{', '.join(score.dropped)}.",
        ]
    return "\n".join(lines)
