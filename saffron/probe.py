"""Does a lens's vacuity probe survive the suite? (the design spec of 2026-09-09)

**A green suite is the positive result** — the inversion of `witness_gate`,
which applies a mutant a criterion declared and reads a `fail` as the answer it
wanted. Here the edit comes from a lens's finding, and a suite whose counted
tests stay green under it is the finding confirmed: the tests the diff added
do not notice the behaviour breaking, which is what the finding said.

This module holds the verdict and no I/O. `mutate` and `run_tests` are injected
exactly as `witness_gate` takes them, so every branch below is reachable without
a container — and so the host never holds a path into a cell.

**Three verdicts, and a fourth that is not this module's to give.** A `killed`
probe may be a test doing its job or a probe that broke the program; nothing
here can tell that from a real kill, so `killed` carries its failure identities
and a person annotates the ones that are collateral. A heuristic in this spot
would be a silently-wrong step inside the one number that exists because
reading is not running.

**A kill must be counted** (b-19b255). This repo's own suite runs its lint
and format checks as tests. A probe that lengthens one line can fail those
checks, and no test the diff added would notice. `check_probe` takes
`counted`, the tests allowed to kill it. Only a new failure whose `code` is
among them kills the probe. Every other new failure lands in `uncounted` and
decides nothing. `added_tests` builds that set from two suites' own `tests`
results.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Callable, Collection, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Literal

from saffron.gates.baseline import subtract_baseline
from saffron.gates.contract import GateResult
from saffron.gates.core.scope import NO_TEST_PATHS, matches
from saffron.intake import Mutant
from saffron.repos.policy import INERT_NAME

# Redeclared rather than imported from `witness`/`revert`: this module owes
# them a precedent, not a dependency.
RunTests = Callable[[list[str]], GateResult]
Mutated = Callable[[Mutant], AbstractContextManager[str | None]]

Verdict = Literal["survived", "killed", "unproven"]


def _no_longer_collected(baseline: GateResult, mutated: GateResult) -> list[str]:
    """Node ids the baseline collected and the mutated run did not.

    A **set** difference, and deliberately not `subtract_baseline`'s counting
    rule: a node id is unique in a suite, so a name that stopped collecting is
    a removal, where two failures can share an identity legitimately. `census`
    draws the same distinction on the same field. One-directional for the same
    reason it is there — a name that *appeared* is not breakage.

    `None` is not `[]` (`GateResult.collected`): a runner that does not
    enumerate has said nothing about which tests exist, which is not evidence
    that a probe removed one.

    Not `suite_drift`, which answers a different question — whether a *gate*
    stopped running or changed tool between two suites — and never reads
    `collected`.
    """
    if baseline.collected is None or mutated.collected is None:
        return []
    return sorted(set(baseline.collected) - set(mutated.collected))


@dataclass(frozen=True)
class BaselineRecord:
    """The suite a verdict is subtracted from, as it answered (item 94)."""

    failures: tuple[str, ...]
    """What was already red. `()` is a baseline that was read and was green."""
    tool: str | None
    collected: int | None
    """On `GateResult.collected`'s terms: `None` for a gate that does not
    enumerate, never `0`."""
    summary: str
    """The only field a baseline's skip count reaches."""

    @classmethod
    def of(cls, baseline: GateResult) -> BaselineRecord | None:
        """`None` for an `error` or `skip`, which measured no failures — an
        empty tuple there would read as a baseline that was green."""
        if baseline.status not in ("pass", "fail"):
            return None
        return cls(
            # ponytail: codes only, like `ProbeResult.failures`; the
            # subtraction also keys on file and message.
            failures=tuple(failure.code for failure in baseline.failures),
            tool=baseline.tool,
            collected=None if baseline.collected is None else len(baseline.collected),
            summary=baseline.summary,
        )


@dataclass(frozen=True)
class ProbeResult:
    """One probe, applied and asked."""

    verdict: Verdict
    reason: str
    """Why, in the lens's own terms where there is one. Always populated for
    `unproven`, where the reason is the whole content of the result."""
    failures: tuple[str, ...] = ()
    """The new failure identities behind a `killed`. Itemised rather than
    a number: telling a real kill from program breakage is a person's call and
    they cannot make it from a number."""
    tool: str | None = None
    """What the gate ran, as it reported it. `None` when no gate answered."""
    collected: int | None = None
    """How many node ids the gate enumerated on the mutated run. `None` when
    no gate answered, or when the gate does not enumerate — never `0` for
    either, because `GateResult.collected` makes `None` and `[]` different
    facts and this count inherits that."""
    summary: str = ""
    """The gate's own one-line summary of the run — for this repo's `tests`
    gate, pytest's "N passed in Xs".

    These three exist because a `survived` verdict means "no new failure
    against the baseline", and a suite that collected almost nothing is green
    too. Without them nothing in the record can tell those apart: the first
    end-to-end pass put the in-cell suite at ~14s where the same tree takes
    78-87s on the host, and the verdict kept nothing that could adjudicate it
    (`docs/superpowers/specs/2026-09-09-mutation-verified-capability-design.md`).
    Taken from the *mutated* run, which is the one the verdict is about."""
    baseline: BaselineRecord | None = None
    """The baseline in hand when the probe was checked. `None` only when there
    was none, which is not a green one (`failures == ()`)."""
    uncounted: tuple[str, ...] = ()
    """Every new failure's `code` whose test was not in `counted`, recognised
    by the probed run's own `collected` or not. Never what decides the verdict
    alone. A `killed` result carries the new failures beside its kill that no
    counted test names. A `survived` or `unproven` one can carry every new
    failure's (b-19b255)."""


def _repo_relative(file: str) -> str | None:
    """`file` normalised, or `None` when it names nothing inside the tree.

    The path is model-authored, so it is normalised before anything compares
    it: `ls-tree HEAD --` resolves `tests/x.py`, `./tests/x.py` and
    `a/../tests/x.py` to the same blob (measured 2026-09-09).
    """
    normalised = posixpath.normpath(file)
    escapes = normalised == ".." or normalised.startswith("../")
    return None if posixpath.isabs(normalised) or escapes else normalised


def probe_refusal(file: str, test_paths: Sequence[str]) -> str | None:
    """Why a probe aimed at `file` is refused, or `None` if it may proceed.

    A path outside the tree first, then `revert`'s rule: no declared test
    paths at all, then a declared glob (`scope.matches`, never a prefix, never
    `fnmatch`) the normalised path matches.
    """
    target = _repo_relative(file)
    if target is None:
        return f"{file} is not a relative path inside the tree"
    if not test_paths:
        return NO_TEST_PATHS
    if any(matches(target, pattern) for pattern in test_paths):
        return f"{target} is a test; a probe must target source"
    return None


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _added_lines(text: str) -> list[str]:
    """`text`'s non-blank lines, in order. A blank line is neither matched
    against a pattern nor counted toward an indent."""
    return [line for line in text.split("\n") if line.strip()]


def _kept_line_at(before: str, start: int) -> str:
    """The line in `before` that holds offset `start`, read from its own
    start. `find`'s own line is never blank, since it holds `find`."""
    line_start = before.rfind("\n", 0, start) + 1
    line_end = before.find("\n", start)
    return before[line_start : line_end if line_end != -1 else len(before)]


def _first_kept_line_after(before: str, end: int) -> str | None:
    """The first non-blank line of `before` strictly after offset `end`, or
    `None` when every remaining line is blank."""
    for line in before[end:].split("\n"):
        if line.strip():
            return line
    return None


def _match_added_side(
    text: str, compiled: Sequence[re.Pattern[str]]
) -> list[str] | None:
    """Every name an added side binds through `{name}`, or `None` when one
    of its non-blank lines matches no pattern."""
    bound: list[str] = []
    for line in _added_lines(text):
        match = next((c.fullmatch(line) for c in compiled if c.fullmatch(line)), None)
        if match is None:
            return None
        name = match.groupdict().get("name")
        if name is not None:
            bound.append(name)
    return bound


def inert_edit(before: str, edit: Mutant, patterns: Sequence[str]) -> str | None:
    """Why `edit` added nothing but inert lines, or `None` to leave the
    question to `source_mutated` in the cell.

    `find` stays whole inside `replace` and occurs once in `before`. Every
    added line fully matches one of `patterns`, filled through plain text
    replacement so a pattern's own regex braces survive. Every name a line
    binds through `{name}` appears nowhere in `before`. No added side leaves
    a kept line indented deeper than its own least indented addition, since
    that line would shift into the added one's body.
    """
    if not patterns:
        return None
    find = edit.find
    replace = edit.replace
    if find not in replace:
        return None
    if before.count(find) != 1:
        return None

    split_at = replace.find(find)
    added_before = replace[:split_at]
    added_after = replace[split_at + len(find) :]

    compiled = [
        re.compile(pattern.replace("{name}", INERT_NAME)) for pattern in patterns
    ]

    before_names = _match_added_side(added_before, compiled)
    if before_names is None:
        return None
    after_names = _match_added_side(added_after, compiled)
    if after_names is None:
        return None

    for name in (*before_names, *after_names):
        if re.search(rf"\b{re.escape(name)}\b", before):
            return None

    start = before.find(find)
    end = start + len(find)

    added_before_lines = _added_lines(added_before)
    if added_before_lines:
        least = min(_indent(line) for line in added_before_lines)
        if _indent(_kept_line_at(before, start)) > least:
            return None

    added_after_lines = _added_lines(added_after)
    if added_after_lines:
        least = min(_indent(line) for line in added_after_lines)
        kept_after = _first_kept_line_after(before, end)
        if kept_after is not None and _indent(kept_after) > least:
            return None

    return f"{edit.file}: keeps its whole find and adds only inert lines"


def check_probe(
    probe: Mutant,
    *,
    baseline: GateResult,
    mutate: Mutated,
    run_tests: RunTests,
    test_paths: Sequence[str],
    counted: Collection[str] | None,
) -> ProbeResult:
    """Apply one vacuity probe at the head tree and ask the repo's declared
    `tests` gate.

    `test_paths` carries no default. The refusal below is the one guard the
    design spec calls required, and a default would leave it unchecked.

    `counted` carries no default either (b-19b255). It names the tests a
    kill can be read from, typically the tests the diff added. A forgotten
    argument must raise, not read every new failure as a kill.
    """
    # Before any refusal, so a `None` baseline means the same thing whichever
    # path returns: there was no baseline verdict to record.
    record = BaselineRecord.of(baseline)
    reason = probe_refusal(probe.file, test_paths)
    if reason is not None:
        # Refused before `mutate`, so nothing is written for a question that
        # must not be asked.
        return ProbeResult("unproven", reason, baseline=record)
    if record is None:
        # `error` or `skip`: a baseline that measured no failures would read
        # every probe against it as a kill of tests that never ran.
        return ProbeResult(
            "unproven",
            f"the baseline tests gate reported `{baseline.status}`, so there "
            "is nothing to subtract from",
        )

    with mutate(probe) as refusal:
        if refusal is not None:
            # One of `source_mutated`'s six refusals. None is evidence about
            # the lens, and the tree is untouched.
            return ProbeResult("unproven", refusal, baseline=record)
        # The whole suite, never a subset, unlike `witness_gate`'s one named
        # witness: a probe's question is whether *anything* notices.
        mutated = run_tests([])

    if mutated.status not in ("pass", "fail"):
        # `error` is not `fail`, and here not `pass` either. `skip` the same:
        # a suite that never ran is not a suite that failed to notice.
        return ProbeResult(
            "unproven",
            f"the tests gate reported `{mutated.status}` under the probe: "
            f"{mutated.summary}",
            baseline=record,
        )
    # From here a gate answered, so every verdict below carries what answered
    # it. By name, not splatted: `ty` reads a splat as filling `failures`.
    tool = mutated.tool
    collected = None if mutated.collected is None else len(mutated.collected)
    summary = mutated.summary

    gone = _no_longer_collected(baseline, mutated)
    if gone:
        # Broke the program at import time. The subtraction below is
        # untrustworthy rather than merely non-empty.
        return ProbeResult(
            "unproven",
            f"the probe stopped these collecting: {', '.join(gone)}",
            tool=tool,
            collected=collected,
            summary=summary,
            baseline=record,
        )

    new = subtract_baseline([mutated], [baseline])
    if not new:
        return ProbeResult(
            "survived",
            "no new failure against the baseline",
            tool=tool,
            collected=collected,
            summary=summary,
            baseline=record,
        )

    # ponytail: any failure of a counted test counts as a kill. `Failure`
    # has no field that tells an assertion apart from an error in the test.
    enumerated = None if mutated.collected is None else set(mutated.collected)
    # ponytail: one matched code makes a run readable. `criteria._side`'s
    # own ponytail comment states the same rule, not "every code is known".
    readable = counted is not None and any(
        n.failure.code in counted
        or (enumerated is not None and n.failure.code in enumerated)
        for n in new
    )
    if not readable:
        return ProbeResult(
            "unproven",
            "a new failure exists but the run cannot say which tests the diff added"
            if counted is None
            else "no new failure names a test the run collected",
            tool=tool,
            collected=collected,
            summary=summary,
            baseline=record,
            uncounted=tuple(n.failure.code for n in new),
        )

    assert counted is not None  # `readable` is `False` whenever it is
    killing = tuple(n.failure.code for n in new if n.failure.code in counted)
    uncounted = tuple(n.failure.code for n in new if n.failure.code not in counted)
    if killing:
        return ProbeResult(
            "killed",
            f"{len(killing)} new failure(s) matched a counted test",
            killing,
            tool=tool,
            collected=collected,
            summary=summary,
            baseline=record,
            uncounted=uncounted,
        )
    return ProbeResult(
        "survived",
        "a new failure exists but matched no counted test",
        tool=tool,
        collected=collected,
        summary=summary,
        baseline=record,
        uncounted=uncounted,
    )


def added_tests(base: Sequence[GateResult], head: GateResult) -> frozenset[str] | None:
    """The names `head` collected that the `tests` result in `base` did not
    (b-19b255). This is the set a probe's kill is counted against.

    `base` is a whole suite's results. Only the one among them with
    `gate == "tests"` is read, by role, as `runner.py` reads it, and unlike
    `census`'s union. `None` covers three cases, and none of them means the diff added
    nothing: no `tests` result in `base`, that result's `collected` is
    `None`, or `head.collected` is `None`. A `base` result that collected
    `[]` makes every name `head` collected an addition.
    """
    base_tests = next((r for r in base if r.gate == "tests"), None)
    if base_tests is None or base_tests.collected is None or head.collected is None:
        return None
    return frozenset(head.collected) - frozenset(base_tests.collected)


def record_fields(probe: Mutant, result: ProbeResult) -> dict[str, object]:
    """The eleven fields a `probes.json` entry owes `probe` and `result`, flat.

    It returns no verdict key and no `findings`. Each caller adds its own.
    The baseline fields are `null` when `result.baseline` is `None`, never
    `[]`."""
    baseline = result.baseline
    return {
        "probe": probe.model_dump(),
        "reason": result.reason,
        "failures": list(result.failures),
        "uncounted": list(result.uncounted),
        "tool": result.tool,
        "collected": result.collected,
        "summary": result.summary,
        "baseline_failures": None if baseline is None else list(baseline.failures),
        "baseline_tool": None if baseline is None else baseline.tool,
        "baseline_collected": None if baseline is None else baseline.collected,
        "baseline_summary": None if baseline is None else baseline.summary,
    }
