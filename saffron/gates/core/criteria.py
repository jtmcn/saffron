"""The `criteria` gate: did each criterion's witness run, and turn green? (§5.4)

Core, and it executes nothing — the route `census` took, and `docs/BACKLOG.md`'s
reasoning applies unchanged. Both suites already ran the repo's tests, at
`base_sha` for the baseline and at head on every attempt, so what a witness did
on each side is two lists the host is already holding. Fetching it would need a
§2.1 exception, a second suite execution charged to every task, and it would
turn an absent witness at base into a baseline `error` — which `session.py`
turns into `PREFLIGHT_FAILED` and §4.4 turns into a skipped repo for the night.

What a `pass` here means, exactly: *a test by this name ran at head and passed,
and if it existed at base it was not green there.* It does not mean the criterion
was met. The witness's body is out of reach — `revert` is the gate that reads it
(§5.4), and `def test_w(): assert True` satisfies everything expressible here.

Every name is opaque, as in `census`: never split, never parsed, never assumed to
contain a path or a separator. A gate that recognises `::` has learned a language.
"""

from __future__ import annotations

from collections.abc import Sequence

from saffron.gates.contract import Failure, GateResult
from saffron.intake import Criterion

# (collected, failed) for one tree.
_Side = tuple[set[str], set[str]]


def _side(results: list[GateResult]) -> _Side | None:
    """What one tree's enumerating gates reported, or `None` if unreadable.

    Readable iff some gate enumerated *and* its failures are empty or at least
    one `failures[].code` appears in that enumeration. That membership test is
    the whole of how core learns the field carries node ids — no name is
    inspected, because a gate that looks for a separator has learned a language.

    Measured, which is why it is not optional: this repo's own `tests` gate
    reaches node ids only through a fallback that runs when a regex over the
    whole output matched nothing, and one printed `path:N: word: message` line
    inside a failing test satisfies that regex. Every node id vanishes from
    `code` for that run, and the naive rule then reports `pass` for a witness
    that failed.
    """
    enumerating = [r for r in results if r.collected is not None]
    if not enumerating:
        return None
    collected = {name for r in enumerating for name in r.collected}
    failed = {f.code for r in enumerating for f in r.failures}
    # ponytail: "at least one overlap", not "every code is a node id" — a mixed
    # side reads as fully readable, so a non-node-id-keyed failure on it stays
    # invisible. Unreachable with this repo's own runner (all-or-nothing per
    # run); upgrade path is per-failure membership, once a runner mixes them.
    if failed and not (failed & collected):
        return None
    return collected, failed


def _green(side: _Side, witness: str) -> bool:
    """Ran on this side and did not fail. Two set lookups, no subset argument."""
    collected, failed = side
    return witness in collected and witness not in failed


def _fail(criterion: Criterion, code: str, why: str) -> Failure:
    # The witness goes in `file`, as `census` puts a name there: it is what the
    # baseline subtraction and `pr_body` both key on.
    return Failure(
        file=criterion.witness, code=code, message=f"{why} — {criterion.claim}"
    )


def _judge(criterion: Criterion, before: _Side, after: _Side) -> Failure | None:
    """`None` when the criterion holds.

    The direction is the load-bearing part: a criterion claiming the change
    *did* something must name a witness that was not green at `base_sha`,
    because one that already passed proves nothing about this change.
    `preserves: true` claims the opposite and is checked the opposite way.
    """
    collected, _ = after
    if criterion.witness not in collected:
        return _fail(
            criterion, "witness-not-collected", "names nothing the suite ran at head"
        )
    if not _green(after, criterion.witness):
        return _fail(criterion, "witness-failed", "collected at head and failed there")
    if criterion.preserves:
        if _green(before, criterion.witness):
            return None
        return _fail(
            criterion,
            "witness-not-preserved",
            "declared `preserves` but was not green at base_sha",
        )
    if _green(before, criterion.witness):
        return _fail(
            criterion,
            "witness-green-at-base",
            "passed at base_sha, so it proves nothing about this change",
        )
    return None


def criteria_gate(
    acceptance: Sequence[Criterion],
    base: list[GateResult],
    head: list[GateResult],
) -> GateResult:
    """Each criterion's witness, judged on two sides by name and outcome.

    `skip` is the common case and is not a failure: ten specs predate this key,
    and a spec that declares no witness must gate exactly as it did before.
    Reaching for a default witness would be worse — a criterion checked against
    an invented test is the defect this gate exists to close, wearing the fix's
    clothes.

    There is almost no `error` to produce. Reading lists cannot break; a `tests`
    gate that errored already aborted the attempt before this runs, and a runner
    that keys failures on something other than a node id is `skip`.
    """
    if not acceptance:
        return GateResult(
            gate="criteria", status="skip", summary="the spec declares no witnesses"
        )

    before, after = _side(base), _side(head)
    if before is None or after is None:
        # Both sides degrade the same way, as `census` does when a runner does
        # not enumerate: never report `pass` on a field you could not read.
        return GateResult(
            gate="criteria",
            status="skip",
            summary=(
                f"no readable enumeration at {'base_sha' if before is None else 'head'}: "
                "the runner reported no collected tests, or keyed its failures "
                "on something other than a node id"
            ),
        )

    unmet = [f for f in (_judge(c, before, after) for c in acceptance) if f is not None]
    if not unmet:
        return GateResult(
            gate="criteria",
            status="pass",
            summary=f"{len(acceptance)} criteria witnessed at head",
        )
    return GateResult(
        gate="criteria",
        status="fail",
        failures=unmet,
        summary=f"{len(unmet)} of {len(acceptance)} criteria have no passing witness",
    )
