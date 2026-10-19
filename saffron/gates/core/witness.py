"""The `witness` gate: does a claim's witness notice its own mutant? (§5.4.1)

**A failing test is the passing result** — the same inversion `revert`
already makes, at a granularity `revert` cannot reach: `revert` reverts whole
files and asks whether the new tests test *anything*, this reverts one named
edit and asks whether one witness tests *that thing*.

A criterion may declare a `mutant` — the smallest edit that would falsify
its `claim`. This gate applies that edit to the head tree,
invokes the repo's declared `tests` gate over exactly the one witness node id
the criterion names, and reads a `fail` as the answer it wanted: the witness
noticed the mutant and died. A witness that stays green under its own mutant
is asserting nothing, and that is the finding, not a pass.

It is `revert`'s exception, not a new one (§2.1). This gate executes no
tool: it applies a text edit the *spec* supplied — data, not code — through
an injected `mutate` context manager, and then invokes a gate the repo
already declared, through the same JSON contract every gate uses, with the
subset argument `revert` established. A constant mutant arrives the same
way, in a criterion `constant_mutants` derived from the repo's own declared
`witness:` patterns. It runs no runner and knows no framework. It reads a
node id only through the repo's `witness_name` pattern. It does no file I/O
of its own. `mutate` is a callable from a `Mutant` to a context manager,
and holds whatever path it needs so this gate never has to (`SA-0060`).

**`error` is not `fail`.** A `tests` gate that could not start under the
mutant — collection crashed, the toolchain broke — has answered nothing
about whether the witness guards its claim. It aborts this gate as `error`,
charged to nobody, exactly the collapse `DESIGN.md` refuses everywhere else.

A mutant that does not apply — `find` absent or ambiguous in the tree the
spec anticipated a different implementation for — is the ordinary case, not
a defect: it is named in the summary and counted toward nothing, never
silently bought as a `pass`.

Every mutant is applied to a clean tree and restored before the next is
touched, and restoration is attempted on every exit path — `error`, `skip`,
`pass` and `fail` alike. Restoring is not this gate's own file I/O: it is
whatever `mutate` does on the way out of its context manager, and this gate
holds no path of its own to do it a second way. A restore that itself fails
surfaces here as an ordinary exception out of that context manager, which
this gate reports as `error` with the tree left mutated: nothing further
here can fix that, and reporting anything else would be the false `pass`
this gate exists to refuse.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from typing import Literal

from saffron.gates.contract import Failure, GateResult
from saffron.gates.core.integrity import (
    _DiffError,
    _FileDiff,
    _parse_block,
    _split_blocks,
)
from saffron.intake import Criterion, Mutant
from saffron.repos.policy import WitnessPatterns

# Run the repo's declared `tests` gate over exactly this subset — never
# discovered here; core knows nothing about which gate fills the role (§2.1).
# The same shape `revert.py` declares, redeclared rather than imported: this
# module owes `revert` a precedent, not a dependency.
RunTests = Callable[[list[str]], GateResult]

# `revert.Reverted`, one noun over: a callable from a `Mutant` to a context
# manager that applies it on entry and undoes it on exit. This gate performs
# no file I/O of its own and holds no path — `tests.mutation.host_mutator`
# is the host-tree implementation, and a cell's volume can supply
# another without this module changing at all (`SA-0060`).
#
# Entering yields `None` when the mutant is now live and must be undone, or a
# `str` reason when it could not be applied or the mutator could not reach
# the tree at all — both are the identical non-committal outcome, "unproven",
# never a task's problem. Anything the context manager *raises*, on entry or
# on exit, is instead this gate's `error`: something broke, rather than
# something the spec merely got wrong.
# Two obligations the type cannot carry, and `SA-0062`'s cell mutator is who
# has to meet them. A yielded reason means *nothing was changed* — yielding one
# after writing to the tree leaves it mutated and reported as merely unproven,
# the silent dirty tree this gate exists to refuse. And the exit must not
# suppress: an exit returning `True` swallows a `KeyboardInterrupt` out of
# `run_tests` and this gate then trips its own narrowing assert.
#
# And the third, which the `applied` flag below creates and which is the one
# that can *understate* a dirty tree: a raise from `__enter__` must mean
# nothing was changed. A mutator that writes and then raises on the way out of
# entry is reported "could not apply" over a mutated tree — the flag has not
# been set yet — where "could not restore" is the true and louder answer.
# Unreachable from `host_mutator`, which returns before anything can raise
# between the write and the yield; a container exec that applies the edit and
# then loses the connection is exactly the shape that is not.
#
# All three bind every implementation, `SA-0061`'s stub included — it is the
# first, not `SA-0062`'s.
Mutated = Callable[[Mutant], AbstractContextManager[str | None]]


def _named(criterion: Criterion, reason: str) -> str:
    return f"{criterion.witness} ({reason})"


# What a summary calls the edit. A criterion probe is no mutant (b-37924b).
EditNoun = Literal["mutant", "criterion probe", "wrong version"]


def witness_gate(
    *,
    acceptance: Sequence[Criterion],
    mutate: Mutated,
    run_tests: RunTests,
    collected: Sequence[str] | None = None,
    edit_noun: EditNoun = "mutant",
) -> GateResult:
    """Each criterion's mutant, applied through `mutate`, tested alone, and
    undone.

    `skip` answers when no criterion carries a mutant, declared by the spec
    or derived from the repo's `witness:` patterns. No task fails for a
    field its spec predates. `skip` also answers a spec whose every mutant
    failed to apply, or whose mutator could not reach the tree at all: named in the
    summary, never counted as a witness that did its job. `error` ends the
    attempt the moment the repo's `tests` gate could not answer for one
    mutant; nothing already restored is undone, and nothing not yet touched
    is applied. The one exception is a restore that itself failed — `error`
    too, and it leaves the tree mutated, because nothing here can put back
    what it could not read or write, and this gate has no path of its own to
    try.

    `collected` is the set of node ids the repo's `tests` gate enumerated on
    the unmutated tree. A criterion whose `witness` is not in it is unproven
    and its mutant is never applied: there is no witness to kill, which is the
    expected state at base for every test the task has yet to write (item 83).
    Compared, never parsed — an opaque string against a list the `tests` gate
    itself produced, so this stays a gate that knows no framework (§2.1). It
    answers per criterion, unlike the subset probe in `run_witness`, which must
    condemn the whole gate because one bad id cannot be told apart from a
    `tests` gate that refuses subsets at all. `None` means the caller had no
    enumeration to offer, which is not evidence about any witness: every
    criterion is tried, exactly as before this argument existed.
    """
    declared = [c for c in acceptance if c.mutant is not None]
    if not declared:
        return GateResult(
            gate="witness", status="skip", summary="the spec declares no mutants"
        )

    died: list[str] = []
    survived: list[Failure] = []
    unproven: list[str] = []
    tool: str | None = None

    for criterion in declared:
        mutant = criterion.mutant
        assert mutant is not None  # narrowed by the `declared` filter above

        # Before `mutate`, so nothing is written for a question that cannot be
        # answered and nothing has to be restored (item 83).
        if collected is not None and criterion.witness not in collected:
            unproven.append(_named(criterion, "no such witness in this tree"))
            continue

        # `mutate`'s exit is where restoration happens now — a context
        # manager's exit is the one place a `BaseException` cannot route
        # around, unlike a `finally` this gate would have to write by hand
        # (`tests.mutation._mutated` carries the history of what that hand
        # gets wrong). Only a `BaseException` from `run_tests` skips straight
        # through both handlers — and `mutate`'s exit still restores on the
        # way past. Why `run_tests`'s ordinary exception is recorded rather
        # than raised is said where it is recorded, below.
        failed_to_run: Exception | None = None
        tests_result = None
        applied = False
        try:
            with mutate(mutant) as reason:
                if reason is not None:
                    unproven.append(_named(criterion, reason))
                    continue
                # Past the reason check, so the tree really is mutated now.
                # What this flag buys is the verb below: "could not restore"
                # is the loudest thing this gate says — it means a mutated
                # tree is still out there and will ship in the diff — and
                # saying it about a `mutate` that failed on entry sends an
                # operator hunting a poisoned worktree that does not exist.
                applied = True
                try:
                    tests_result = run_tests([criterion.witness])
                except Exception as exc:
                    # Recorded rather than raised, and not because `mutate`
                    # needs the block to end normally — its own exit restores
                    # either way. It buys attribution: a run that failed and a
                    # restore that failed are different sentences, and when
                    # both happen the operator gets both.
                    failed_to_run = exc
        except Exception as exc:
            # Whatever `mutate` itself raised getting here is the worse fact,
            # the one that ships in the diff if nothing says so. This gate does
            # not know or care what exception type a given `mutate`
            # implementation raises; that knowledge stays with whoever built
            # it. `SA-0062`'s cell mutator enters through a container exec,
            # which can fail routinely, so the entry case is not a corner.
            verb = (
                f"could not restore {mutant.file} after its {edit_noun}"
                if applied
                else f"could not apply {mutant.file}'s {edit_noun}"
            )
            return GateResult(
                gate="witness",
                status="error",
                summary=(
                    f"{verb} — {exc}"
                    + (
                        f" (the run also failed — {failed_to_run})"
                        if failed_to_run is not None
                        else ""
                    )
                ),
            )
        if failed_to_run is not None:
            return GateResult(
                gate="witness",
                status="error",
                summary=(
                    f"the `tests` gate could not be executed for "
                    f"{criterion.witness}'s {edit_noun} — {failed_to_run}"
                ),
            )
        assert tests_result is not None  # both failure paths returned above

        # ponytail: an inner `error` ends the attempt through
        # `suite.aborted_gates`, and a mutant that kills its witness by making
        # a fixture raise produces exactly that — `.saffron/gates/tests.py`
        # reports `error` when pytest exits non-zero with no `FAILED ` line to
        # parse. `revert.py` met the identical trap and chose **`skip`** — its
        # own comment is emphatic that `error` "ends the attempt" and that this
        # is "the whole gate's usability". This spec asked for `error`. Left as
        # asked, and the disagreement is `error`-vs-`skip`, not
        # `error`-vs-`fail` — resolve it in `SA-0058` or the backlog, not by
        # editing one of the two to match.
        if tests_result.status == "error":
            # Not `fail`: a runner that could not start under the mutant has
            # answered nothing about whether the witness guards its claim.
            return GateResult(
                gate="witness",
                status="error",
                tool=tests_result.tool,
                summary=(
                    f"the `tests` gate errored under {criterion.witness}'s "
                    f"{edit_noun} — {tests_result.summary}"
                ),
            )
        if tests_result.status == "fail":
            died.append(criterion.witness)
            tool = tool or tests_result.tool
            continue
        if tests_result.status == "pass":
            # The claim and the file, never the edit: this message reaches
            # REPAIR verbatim at every tier, and a mutant is withheld (§5.4.1).
            survived.append(
                Failure(
                    file=criterion.witness,
                    code="survived-mutant",
                    message=(
                        f"ran and passed with its {edit_noun} applied to "
                        f"{mutant.file} — {criterion.claim}"
                    ),
                )
            )
            tool = tool or tests_result.tool
            continue
        # `skip`, or any other status: no trustworthy verdict was produced,
        # which is not evidence the witness guards its claim — the same
        # non-answer as a mutant that never applied.
        unproven.append(
            _named(criterion, f"the `tests` gate reported {tests_result.status}")
        )

    note = (
        f" — {len(unproven)} {edit_noun}(s) not proven: {', '.join(unproven)}"
        if unproven
        else ""
    )

    if survived:
        return GateResult(
            gate="witness",
            status="fail",
            tool=tool,
            failures=survived,
            summary=(
                f"{len(survived)} of {len(declared)} witness(es) survived their "
                f"own {edit_noun}{note}"
            ),
        )
    if died:
        return GateResult(
            gate="witness",
            status="pass",
            tool=tool,
            summary=(
                f"{len(died)} of {len(declared)} witness(es) died under their "
                f"own {edit_noun}{note}"
            ),
        )
    return GateResult(
        gate="witness",
        status="skip",
        summary=f"no declared {edit_noun} produced a trustworthy verdict{note}",
    )


# A mutant the repo derives from the diff itself (§5.4.1, b-5b1f8a),
# through its own declared `witness:` patterns (`WitnessPatterns`).

CLAIM_TEMPLATE = (
    "the witness names `{name}` and passes with any value of it, so pin the "
    "value as a literal"
)


def _new_side(
    hunk: list[tuple[str, str, int | None]],
) -> tuple[str, list[tuple[int, int]]]:
    """A hunk's context and added lines, joined with `\\n`.

    Also the `(start, end)` offset of each added line in that text. A
    removed line contributes nothing: it has no new side.
    """
    lines = [content for kind, content, _ in hunk if kind != "-"]
    kinds = [kind for kind, _content, _ in hunk if kind != "-"]
    text_parts: list[str] = []
    spans: list[tuple[int, int]] = []
    pos = 0
    for content in lines:
        start = pos
        end = start + len(content)
        spans.append((start, end))
        text_parts.append(content)
        pos = end + 1  # the "\n" this function joins with
    return "\n".join(text_parts), [
        span for span, kind in zip(spans, kinds, strict=True) if kind == "+"
    ]


def _overlaps_added(span: tuple[int, int], added: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < a_end and end > a_start for a_start, a_end in added)


def _readable_files(diff: str, test_paths: Sequence[str]) -> list[_FileDiff]:
    try:
        blocks = _split_blocks(diff)
    except _DiffError:
        return []
    files = []
    for block in blocks:
        try:
            file_diff = _parse_block(block)
        except _DiffError:
            continue
        if file_diff.unreadable or file_diff.new_path is None:
            continue
        if file_diff.matches_any(list(test_paths)):
            continue
        files.append(file_diff)
    return files


def _candidate_constants(
    diff: str, patterns: WitnessPatterns, test_paths: Sequence[str]
) -> list[tuple[str, str, str, str]]:
    """Every `(name, file, find, replace)` the diff's non-test files add or
    change, where the match overlaps an added line."""
    candidates: list[tuple[str, str, str, str]] = []
    for file_diff in _readable_files(diff, test_paths):
        for hunk in file_diff.hunks:
            text, added = _new_side(hunk)
            for entry in patterns.constants:
                for match in re.finditer(entry.pattern, text):
                    if not _overlaps_added((match.start(), match.end()), added):
                        continue
                    name = match.group("name")
                    find = text[match.start() : match.end()]
                    value_start = match.start("value") - match.start()
                    value_end = match.end("value") - match.start()
                    expanded = match.expand(entry.replace)
                    replace = find[:value_start] + expanded + find[value_end:]
                    candidates.append((name, file_diff.path, find, replace))
    return candidates


def _witness_name(criterion: Criterion, patterns: WitnessPatterns) -> str | None:
    assert patterns.witness_name is not None  # callers check this first
    found = re.search(patterns.witness_name, criterion.witness)
    if found is None:
        return None
    return found.group("name")


def _witness_text(name: str, diff: str, patterns: WitnessPatterns) -> str:
    """Every `witness_body` match, over every file's hunks' new sides,
    concatenated. Not filtered by `test_paths`: a witness commonly lives
    under one."""
    assert patterns.witness_body is not None  # callers check this first
    body_pattern = patterns.witness_body.replace("{name}", re.escape(name))
    pieces = []
    for file_diff in _readable_files(diff, ()):
        for hunk in file_diff.hunks:
            text, _added = _new_side(hunk)
            pieces.extend(m.group(0) for m in re.finditer(body_pattern, text))
    return "\n".join(pieces)


def _names_whole_word(text: str, name: str) -> bool:
    return re.search(rf"\b{re.escape(name)}\b", text) is not None


def constant_mutants(
    diff: str,
    acceptance: Sequence[Criterion],
    patterns: WitnessPatterns,
    test_paths: Sequence[str],
) -> list[Criterion]:
    """A derived `Criterion` carries a `Mutant`. One exists for each pair
    of a constant and a criterion whose own witness names that constant.

    `[]`, never a raise, when the repo declares no patterns, or `diff`
    is not the shape `integrity`'s own parser trusts (§5.4.1).
    """
    if not patterns.witness_name or not patterns.witness_body or not patterns.constants:
        return []

    candidates = _candidate_constants(diff, patterns, test_paths)
    if not candidates:
        return []

    witness_texts: dict[str, str] = {}
    derived: list[Criterion] = []
    emitted: set[tuple[str, str]] = set()
    for criterion in acceptance:
        if criterion.witness not in witness_texts:
            name = _witness_name(criterion, patterns)
            witness_texts[criterion.witness] = (
                _witness_text(name, diff, patterns) if name is not None else ""
            )
        text = witness_texts[criterion.witness]
        if not text:
            continue
        for name, file_, find, replace in candidates:
            key = (criterion.witness, name)
            if key in emitted:
                continue
            if not _names_whole_word(text, name):
                continue
            emitted.add(key)
            derived.append(
                Criterion(
                    claim=CLAIM_TEMPLATE.format(name=name),
                    witness=criterion.witness,
                    mutant=Mutant(file=file_, find=find, replace=replace),
                )
            )
    return derived
