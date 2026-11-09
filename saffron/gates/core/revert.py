"""The `revert` gate: does a new test detect the thing it claims to? (§5.4)

The anti-theater gate. Revert the source *files* of the diff, keep the test
files, run only the new tests, and require them to **fail** — file-level, not
hunk-level, which is the ceiling the `ponytail:` below names. "New" is a set
difference over names the host already holds (`collected(head) -
collected(base)`, `census`'s own route). "Changed-body-same-name" is a second
subset instead. It is built from a name's own reported location and the
diff's own changed lines, never a hunk-to-node-id mapping core computes
itself (backlog item 49).

The one sanctioned exception to "core executes nothing" (§2.1): it re-invokes
a gate the repo already declared, through the same JSON contract as every
other gate, with one extra argument — never a tool. Both the worktree
mutation (revert, then restore) and the test re-run are handed in rather than
discovered, so every test here runs against a fake and needs no container.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager

from saffron.gates.contract import Failure, GateResult, Location
from saffron.gates.core.integrity import _DiffError, _parse_block, _split_blocks
from saffron.gates.core.scope import NO_TEST_PATHS, matches
from saffron.intake import Criterion

# Revert the given source paths for the `with` block, restoring them after —
# failing and erroring paths alike. `worktree.source_reverted` is the one
# production implementation; a checkout or restore it cannot make raises,
# which this gate turns into `error`, never `fail` (§5.4).
Reverted = Callable[[list[str]], AbstractContextManager[None]]

# Run the repo's declared `tests` gate over exactly this subset — never
# discovered here; core knows nothing about which gate fills the role (§2.1).
RunTests = Callable[[list[str]], GateResult]

# Read lazily, like the two above, so the skips that never touch the worktree
# cost no container round trip. Required, and for the reason `CLAUDE.md` gives
# for cell creation's `network`/`env`: this one fails *open*, and open here is
# the agent's uncommitted work silently overwritten.
DirtyPaths = Callable[[], Sequence[str]]


def _collected(results: list[GateResult]) -> list[str] | None:
    """`census._collected`'s own route, copied rather than imported: `census`
    is `forbidden` here, and its helper is module-private."""
    reported = [r.collected for r in results if r.collected is not None]
    if not reported:
        return None
    return [name for names in reported for name in names]


def _argv_safe(name: str) -> bool:
    """Whether a collected name may be handed to a process as an argument.

    This gate is the one place a `collected` name is *executed* rather than
    compared: `runner.run_gate` builds `argv = [executable, *subset]` with no
    `--` separator. A name starting with `-` is an option to whatever runs it,
    and this repo's own `tests` gate calls any collection line holding `::` a
    name — so a line reading `--deselect=t.py::test_new` is new at head, joins
    the subset, and deselects the very test the gate is asking about, turning
    the theater case into a `pass`. Dropped rather than skipped on, because a
    dropped name still leaves the real ones judged.

    **This closes the false-`pass` shape and not the family.** Measured: a
    printed line needs no leading `-` to do damage — `zzz::bogus` reaches the
    reverted run as a node id that matches no file, pytest exits 4, and this
    gate reads an untrustworthy run as `skip`. So a `skip` is buyable for one
    line in a new test file, and no name filter closes that: a bogus id can be
    spelled inside `test_paths` as easily as outside them. Named in
    backlog item 51 rather than papered over here, and the drop is
    reported in the summary so the attempt is at least visible. A runner
    that fills `GateResult.uncollected` reads such an id as uncollected, so
    the `skip` is gone. This repo's `tests` gate fills it (item 50).
    """
    return not name.startswith("-")


def _locations(results: list[GateResult]) -> dict[str, Location] | None:
    """`_collected`'s own route, for `locations`: merged across every head
    result, never read from the baseline."""
    reported = [r.locations for r in results if r.locations is not None]
    if not reported:
        return None
    merged: dict[str, Location] = {}
    for mapping in reported:
        merged.update(mapping)
    return merged


def _hunk_changed_lines(hunk: list[tuple[str, str, int | None]]) -> set[int]:
    """New-side lines one hunk changes. An added line always counts. A
    removed line marks the kept lines on each side of it."""
    changed: set[int] = set()
    last_kept: int | None = None
    after_deletion = False
    for kind, _content, new_line in hunk:
        if kind == "-":
            if last_kept is not None:
                changed.add(last_kept)
            after_deletion = True
            continue
        assert new_line is not None  # only a "-" line carries no new-side line
        if kind == "+" or after_deletion:
            changed.add(new_line)
        after_deletion = False
        last_kept = new_line
    return changed


def _changed_lines(diff: str) -> dict[str, set[int]] | None:
    """New-side lines the diff changes, keyed by new path. `None` when
    `diff` is not the shape `integrity`'s own parser trusts."""
    try:
        blocks = _split_blocks(diff)
    except _DiffError:
        return None
    by_file: dict[str, set[int]] = {}
    for block in blocks:
        try:
            file_diff = _parse_block(block)
        except _DiffError:
            return None
        if file_diff.unreadable or file_diff.new_path is None:
            continue
        lines = by_file.setdefault(file_diff.new_path, set())
        for hunk in file_diff.hunks:
            lines.update(_hunk_changed_lines(hunk))
    return by_file


def _second_subset(
    *,
    before: list[str],
    after: list[str],
    candidates: set[str],
    preserved: set[str],
    exempt: Sequence[str],
    locations: dict[str, Location],
    changed_lines: dict[str, set[int]],
    test_paths: Sequence[str],
) -> list[str]:
    """Old names a diff-changed line reaches through their own location,
    net of every name the first subset already owns."""
    old_names = (set(before) & set(after)) - candidates - preserved - set(exempt)
    rewritten = []
    for name in sorted(old_names):
        location = locations.get(name)
        if location is None:
            continue
        if not any(matches(location.file, pattern) for pattern in test_paths):
            continue
        lines = changed_lines.get(location.file)
        if not lines:
            continue
        if not any(location.first <= line <= location.last for line in lines):
            continue
        if not _argv_safe(name):
            continue
        rewritten.append(name)
    return rewritten


def _rewritten_clause(
    second_subset: list[str],
    result: GateResult | None,
    failed_to_run: Exception | None,
    *,
    diff_unreadable: bool,
) -> str:
    """The advisory clause a second, rewritten-test run earns. An unreadable
    diff returns its own clause, and an empty second subset returns an empty
    string."""
    if diff_unreadable:
        return (
            " — advisory, does not block: the diff could not be read, so no "
            "rewritten test could be checked"
        )
    if not second_subset:
        return ""
    unreadable = (
        failed_to_run is not None
        or result is None
        or result.status not in ("pass", "fail")
        or result.collected is None
    )
    collected: set[str] = set()
    failed: set[str] = set()
    if not unreadable:
        assert result is not None  # narrowed by the checks above
        collected = set(result.collected or [])
        failed = {f.code for f in result.failures}
        if failed and not (failed & collected):
            unreadable = True
    if unreadable:
        return (
            " — advisory, does not block: no readable verdict for the rewritten test(s)"
        )
    passed = sorted(
        name for name in second_subset if name in collected and name not in failed
    )
    base = f"{len(passed)} of {len(second_subset)} rewritten test(s) passed without their source"
    if passed:
        base += f": {', '.join(passed[:3])}"
    return f" — advisory, does not block: {base}"


def revert_gate(
    *,
    prior: list[GateResult],
    results: list[GateResult],
    acceptance: Sequence[Criterion],
    changed_files: Sequence[str],
    test_paths: Sequence[str],
    dirty: DirtyPaths,
    reverted: Reverted,
    run_tests: RunTests,
    exempt: Sequence[str],
    diff: str,
) -> GateResult:
    """New tests, run with their own source reverted, must not pass.

    `skip` is not evidence. Most skips touch neither `reverted` nor
    `run_tests`. No readable enumeration exists at base. The repo declares
    no test paths. Every changed file sits inside them. Uncommitted work sits on a
    path this would revert. No new test is left to run, because none was
    added, all are exempt or none reaches changed source. If `locations`
    finds a rewritten test there, the second subset runs alone inside the
    revert. A reverted run with no trustworthy result also skips.
    """
    before = _collected(prior)
    after = _collected(results)
    if before is None or after is None:
        return GateResult(
            gate="revert",
            status="skip",
            summary="no readable test enumeration to compare — nothing to revert",
        )

    # Arithmetic on lists the host already holds — never a second enumeration
    # — minus any witness a criterion declared `preserves`: that criterion is
    # specified to be green at base and at head, and requiring it to fail
    # without the source would contradict its own declaration (§5.4).
    preserved = {c.witness for c in acceptance if c.preserves}
    # The union, not the difference alone: a criterion's witness is declared to
    # be *not* green at base (`criteria._judge` enforces that for anything not
    # `preserves`), so it is a name this change is claiming to make pass — and
    # a name whose source dependence is exactly what this gate asks about. A
    # witness that already appears at head joins by set union anyway; one the
    # runner did not enumerate at head is dropped below rather than asserted.
    # No `preserves` filter here: the `- preserved` below already removes them,
    # and a second guard for the same thing is a branch no test can kill.
    #
    # ponytail: a witness that was red at base *by flake* is pulled in by this
    # union, and reported as theater if it passes reverted — blocking, and no
    # repair turn can fix a test that is fine. §5.4 already names the flaky
    # witness as a live `criteria` hole; this widens the same hole rather than
    # opening a new one, and the spec's own subset claim is what asks for it.
    declared = {c.witness for c in acceptance}
    before_exempt = ((set(after) - set(before)) | (declared & set(after))) - preserved
    # Named only where it was a candidate: a test never added, or one
    # `preserves` dropped, was never going to reach `run_tests` either way.
    exempted = sorted(before_exempt & set(exempt))
    candidates = before_exempt - set(exempt)
    subset = sorted(name for name in candidates if _argv_safe(name))
    # A dropped name is the only evidence the operator gets that something in
    # the cell printed a collection line it had no business printing. Carried
    # on the verdicts and on the skip a drop can itself cause — the later
    # skips already say the gate produced no evidence, and none of them is a
    # judgement the narrowing changed.
    dropped = sorted(candidates - set(subset))
    note = (
        f" — ignored {len(dropped)} collected name(s) reading as command-line "
        f"options: {', '.join(dropped[:3])}"
        if dropped
        else ""
    )
    if exempted:
        note += f" — {len(exempted)} exempt test(s): {', '.join(exempted)}"

    # Read only when a merged map names something: `None` and `{}` are both
    # "not reported" for this gate's purposes (backlog item 49).
    locations = _locations(results)
    changed_lines: dict[str, set[int]] | None = None
    diff_unreadable = False
    if locations:
        changed_lines = _changed_lines(diff)
        diff_unreadable = changed_lines is None
    second_subset = (
        _second_subset(
            before=before,
            after=after,
            candidates=candidates,
            preserved=preserved,
            exempt=exempt,
            locations=locations,
            changed_lines=changed_lines,
            test_paths=test_paths,
        )
        if locations and changed_lines is not None
        else []
    )

    # The message a `not subset` skip carries. Narrowing below replaces it
    # once narrowing itself empties `subset`.
    what = "every new test is exempt" if exempted else "the diff adds no new test"
    skip_summary = f"{what}{note}" if not subset else None
    if not subset and not second_subset:
        assert skip_summary is not None
        return GateResult(
            gate="revert",
            status="skip",
            summary=skip_summary
            + _rewritten_clause(
                second_subset, None, None, diff_unreadable=diff_unreadable
            ),
        )

    # File-level, not hunk-level: a changed file matching none of the repo's
    # declared test paths is source.
    #
    # ponytail: a file that is half test and half source is therefore reverted
    # whole or not at all — the spec's own Out of scope names this and asks for
    # the marker.
    if not test_paths:
        # A fourth kind of nothing, and it must be caught before the worktree is
        # touched: with no declared test paths every changed file reads as
        # source, so the gate would revert the very tests it is about to run.
        # `policy.integrity.test_paths` defaults to `[]`, so this is every repo
        # that has not declared them.
        return GateResult(
            gate="revert",
            status="skip",
            summary=NO_TEST_PATHS,
        )
    source = [
        p for p in changed_files if not any(matches(p, pat) for pat in test_paths)
    ]
    if not source:
        return GateResult(
            gate="revert",
            status="skip",
            summary="the diff has no source outside the repo's declared test paths",
        )

    # A revert cannot reach a mutant outside `source` and the test paths
    # (item 84), unless a declared subject the diff reaches keeps it judged.
    subset_was_present = bool(subset)
    aside: set[tuple[str, str]] = set()
    kept: set[tuple[str, str]] = set()
    for c in acceptance:
        if c.mutant is None or c.witness not in subset:
            continue
        file_outside = c.mutant.file not in source and not any(
            matches(c.mutant.file, pat) for pat in test_paths
        )
        if not file_outside:
            continue
        subject_reached = c.subject is not None and (
            c.subject in source or any(matches(c.subject, pat) for pat in test_paths)
        )
        if subject_reached:
            kept.add((c.witness, c.subject))
        else:
            aside.add((c.witness, c.mutant.file))
    unreachable = sorted(aside)
    kept_by_subject = sorted(
        (witness, subject)
        for witness, subject in kept
        if witness not in {w for w, _ in aside}
    )
    if unreachable:
        unreached = {witness for witness, _ in unreachable}
        subset = [name for name in subset if name not in unreached]
        note += (
            f" — {len(unreached)} witness(es) whose mutant's file this diff "
            "never touched: " + ", ".join(f"{w} ({f})" for w, f in unreachable)
        )
    if kept_by_subject:
        note += (
            f" — {len({w for w, _ in kept_by_subject})} witness(es) a declared subject kept "
            "judged: " + ", ".join(f"{w} ({s})" for w, s in kept_by_subject)
        )
    if not subset and subset_was_present:
        skip_summary = f"no new test depends on source this diff changed{note}"
    if not subset and not second_subset:
        assert skip_summary is not None
        return GateResult(
            gate="revert",
            status="skip",
            summary=skip_summary
            + _rewritten_clause(
                second_subset, None, None, diff_unreadable=diff_unreadable
            ),
        )

    # The restore checks out `HEAD`, not the tree as it stood a moment ago, so
    # an uncommitted edit to a source path does not survive this gate — and
    # `committed` runs next and would report the tree clean, which is the one
    # gate whose whole job is to notice that it is not. Refusing to run is the
    # only honest answer: no evidence about theater is worth destroying the
    # agent's uncommitted work and blinding the gate that would have caught it.
    if collides := sorted(set(dirty()) & set(source)):
        return GateResult(
            gate="revert",
            status="skip",
            summary=(
                "uncommitted changes to source this gate would revert: "
                f"{', '.join(collides[:3])} — restoring to HEAD would destroy "
                "them and hide them from `committed`"
            ),
        )

    reverted_result: GateResult | None = None
    run_failed: Exception | None = None
    rewritten_result: GateResult | None = None
    rewritten_failed: Exception | None = None
    try:
        with reverted(source):
            # Recorded rather than raised, so the `with` unwinds normally and
            # the restore in its `finally` still runs — then reported on its
            # own below. An exception out of the repo's `tests` gate is not a
            # failed checkout, and one message for both sends the operator to
            # the wrong subsystem.
            try:
                if subset:
                    reverted_result = run_tests(subset)
            except Exception as exc:  # noqa: BLE001 — reported below, not swallowed
                run_failed = exc
            # A second, advisory run: a broken one only changes the clause
            # below, never the verdict above.
            try:
                if second_subset:
                    rewritten_result = run_tests(second_subset)
            except Exception as exc:
                rewritten_failed = exc
    except Exception as exc:
        # A checkout or a restore that did not happen means this gate never
        # ran — infrastructure, charged to nobody, never the task's `fail`.
        return GateResult(
            gate="revert",
            status="error",
            summary=f"could not revert or restore the source — {exc}",
        )

    clause = _rewritten_clause(
        second_subset,
        rewritten_result,
        rewritten_failed,
        diff_unreadable=diff_unreadable,
    )
    if not subset:
        # `second_subset` must be non-empty here, or an earlier check
        # already returned.
        assert skip_summary is not None
        return GateResult(gate="revert", status="skip", summary=skip_summary + clause)

    if reverted_result is None:
        # `reverted_result is None` and `run_failed is not None` are the same
        # fact stated twice — the result is assigned only where no exception
        # escaped — so testing both is a branch no input can kill. The
        # exception itself still carries the message.
        #
        # ponytail: unreachable through `runner.run_gate`, which turns every
        # failure it has — `GateNotExecutable`, a timeout, unparseable stdout,
        # a missing `tool` — into `GateResult(status="error")`, i.e. the branch
        # below. This catches a `run_tests` that raises outright, which only a
        # different injection could do.
        return GateResult(
            gate="revert",
            status="error",
            summary=f"the reverted run could not be executed — {run_failed}",
        )
    if reverted_result.status not in ("pass", "fail"):
        # **Not `error`, and this is the whole gate's usability.** `error` ends
        # the attempt through `suite.aborted_gates` — so mapping this here
        # killed the task in the gate's own canonical case. Measured: a spec
        # that lands a module and its tests together has its module removed by
        # `_revert_source`, the tests then fail to *import*, and this repo's
        # `tests` gate reports `error` ("pytest exited N with no parsed
        # failures") rather than `fail`, because a collection error prints no
        # line its regex or its `FAILED ` fallback can read. `DESIGN.md` §5.4
        # says that exact case must report green. A runner that instead
        # reports `fail` or `pass` with the failed-to-import names in
        # `uncollected` (backlog item 50) skips this branch and is judged
        # below. This repo's own gate does that for a handed subset.
        #
        # `skip` rather than `pass`, for the reason the three nothings above
        # are skips: a run that produced no trustworthy result is not evidence
        # that these tests failed without their source, only that none of them
        # was *seen* to pass. Non-blocking either way, and honest about which.
        return GateResult(
            gate="revert",
            status="skip",
            summary=(
                f"the reverted run returned {reverted_result.status} and no "
                "readable verdict — no new test was seen to pass without its "
                "source, which is not the same as one having failed"
            )
            + clause,
        )

    # `criteria._side`'s readability guard, which the naive form of this
    # verdict drops. Both halves are `_side`'s, for `_side`'s measured reason:
    # this repo's own `tests` gate keys `failures[].code` on the caught
    # exception type on its common path and reaches node ids only through a
    # fallback, so `failed` can be a set of strings no node id ever equals.
    # Read that way, every genuinely-failing reverted test stays out of
    # `failed` while remaining in `collected` and reads as a clean pass — a
    # false `fail` on a correct, source-dependent test, which is the expensive
    # direction. `criteria` degrades to `skip` rather than report `pass` on a
    # field it could not read; this gate degrades the same way rather than
    # report `fail`.
    #
    # `collected is None` (did not enumerate), not `not collected`: a run that
    # enumerated and found nothing is readable, and it is the ordinary answer
    # when every reverted test fails at import — which is a `pass` here, not a
    # skip.
    if reverted_result.collected is None:
        return GateResult(
            gate="revert",
            status="skip",
            summary="the reverted run reported no collected tests — nothing to read"
            + clause,
        )
    collected = set(reverted_result.collected)

    # A runner filling `uncollected` (item 50) must place each handed name
    # in exactly one of `collected` or `uncollected`, checked against `subset`.
    listed: set[str] = set()
    if reverted_result.uncollected is not None:
        handed = set(subset)
        listed = set(reverted_result.uncollected) & handed
        unaccounted = sorted(
            (handed - collected - listed) | (handed & collected & listed)
        )
        if unaccounted:
            return GateResult(
                gate="revert",
                status="error",
                summary=(
                    "the reverted run left "
                    f"{len(unaccounted)} handed name(s) unaccounted for: "
                    f"{', '.join(unaccounted[:3])}"
                ),
            )
        if listed:
            # Rides the same channel a dropped option name already uses.
            note += (
                f" — {len(listed)} handed name(s) the reverted run could not "
                f"collect, read as failed without their source: "
                f"{', '.join(sorted(listed)[:3])}"
            )

    failed = {f.code for f in reverted_result.failures}
    # ponytail: "at least one overlap", not "every code is a node id" — the
    # same ceiling `criteria._side` names, and the same upgrade path
    # (per-failure membership) once a runner mixes the two keyings in one run.
    #
    # ponytail: and a runner reporting `fail` with an *empty* `failures` list
    # reads below as "every name in the subset passed" — a blocking `fail` on a
    # correct spec. `criteria._side` has the same hole and it degrades to
    # `skip`; here the blast radius is the opposite way round. Closing either
    # means obliging the `tests` role to key its failures, which is item 50.

    # `listed` too: a runner filling `uncollected` can key a failure on a
    # handed name it never collected. Empty when the field is `None`.
    if failed and not (failed & (collected | listed)):
        return GateResult(
            gate="revert",
            status="skip",
            summary=(
                "the reverted run keyed its failures on something other than a "
                "node id, so a failing test cannot be told from a passing one"
            )
            + clause,
        )

    # A name is theater iff it ran (is in `collected`) and did not fail (its
    # code is absent from `failures`). A name that failed, errored, or vanished
    # from collection entirely are three acceptable answers; only a clean pass
    # is the defect.
    passed = sorted(name for name in subset if name in collected and name not in failed)

    if passed:
        return GateResult(
            gate="revert",
            status="fail",
            tool=reverted_result.tool,
            failures=[
                Failure(
                    file=name,
                    code="passed-without-source",
                    message="ran and passed with its own source reverted",
                )
                for name in passed
            ],
            summary=(
                f"{len(passed)} of {len(subset)} new test(s) passed "
                f"without their source{note}"
            )
            + clause,
        )
    return GateResult(
        gate="revert",
        status="pass",
        # The tool that actually ran, never a literal (§5.4, Appendix H): this
        # gate is unlike `census`/`criteria` in that it does execute one, and a
        # pass without it is indistinguishable from a gate that never ran.
        tool=reverted_result.tool,
        summary=(
            f"{len(subset)} new test(s) failed without their source, as required{note}"
        )
        + clause,
    )
