"""Tests for the `witness` gate (§5.4.1, `docs/BACKLOG.md` item 69).

This spec's own acceptance criteria deliberately declare no mutants — a gate
whose own tests depend on the gate is a circle — so everything here drives
`witness_gate` directly with fabricated `Criterion`/`Mutant` objects and a
fake `run_tests` callable, against real files on disk so `apply_mutant` and
`restore_mutant` do genuine byte-level work.
"""

from __future__ import annotations

import contextlib
import json

import pytest

from saffron.gates.contract import Failure, GateResult, GateStatus, identity
from saffron.gates.core.witness import witness_gate
from saffron.intake import Criterion, Mutant
from saffron.mutation import host_mutator


def _tests(
    *, status: GateStatus, collected: tuple[str, ...] = (), tool: str = "pytest 8.3.2"
) -> GateResult:
    """A canned `tests`-gate result for exactly the one-node subset this gate
    invokes it with."""
    return GateResult(gate="tests", status=status, tool=tool, collected=list(collected))


def _criterion(
    *,
    claim: str = "the total is clamped at zero",
    witness: str = "tests/test_billing.py::test_clamped",
    file: str = "a.py",
    find: str = "max(x, 0)",
    replace: str = "x",
) -> Criterion:
    return Criterion(
        claim=claim,
        witness=witness,
        mutant=Mutant(file=file, find=find, replace=replace),
    )


def _write(tmp_path, name: str, text: str) -> None:
    (tmp_path / name).write_text(text)


def test_a_witness_that_dies_under_its_mutant_passes(tmp_path):
    """The gate applies the edit, invokes the repo's declared `tests` gate
    over exactly that one node id, and reads a `fail` as the answer it
    wanted. The same inversion `revert` makes, at a granularity `revert`
    cannot reach — not, as the spec claimed, the only one in the system."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def run_tests(subset):
        assert subset == [criterion.witness]
        return _tests(status="fail", collected=(criterion.witness,))

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=run_tests
    )

    assert result.status == "pass"
    assert result.gate == "witness"


def test_a_witness_that_survives_its_mutant_fails(tmp_path):
    """A witness that survives its mutant fails, and the failure names the
    criterion, the witness and the edit."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    # `replace="0"`, not the helper's default `"x"`: `"x"` is a substring of
    # `find`, so an assertion on it could not tell whether the message named
    # the replacement at all.
    criterion = _criterion(claim="the total is clamped at zero", replace="0")

    def run_tests(subset):
        return _tests(status="pass", collected=(criterion.witness,))

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=run_tests
    )

    assert result.status == "fail"
    assert len(result.failures) == 1
    failure = result.failures[0]
    assert isinstance(failure, Failure)
    assert failure.file == criterion.witness  # the witness
    assert "the total is clamped at zero" in failure.message  # the criterion's claim
    # Both halves of the edit, and `replace` chosen so it is not a substring
    # of `find`: with the default `replace="x"` the second assertion was a
    # substring of the first and held whether or not the message named it —
    # deleting `{mutant.replace!r}` from the message left this green.
    assert "max(x, 0)" in failure.message  # what was there
    # `repr`, and `replaced` read off the criterion rather than restated:
    # asserting the fixture equals its own literal tests nothing.
    assert criterion.mutant is not None
    replaced = criterion.mutant.replace  # "0" — not a substring of `find`
    assert repr(replaced) in failure.message  # what replaced it


def test_the_tree_is_unchanged_however_the_gate_ends(tmp_path):
    """Byte-identical once the gate is done, whether the witness died,
    survived, or the mutant never applied. It executes inside the worktree
    the task is packaged from, so a mutant left behind would ship in the
    diff."""
    original = "def total(x):\n    return max(x, 0)\n"
    _write(tmp_path, "a.py", original)
    target = tmp_path / "a.py"

    for status in ("fail", "pass", "error"):
        result = witness_gate(
            acceptance=[_criterion()],
            mutate=host_mutator(tmp_path),
            run_tests=lambda subset, s=status: _tests(status=s),
        )
        assert result.status in ("pass", "fail", "error")
        assert target.read_bytes() == original.encode()

    # And when the mutant does not apply at all, the file was never touched.
    _write(tmp_path, "a.py", "def total(x):\n    return x\n")
    unchanged = target.read_bytes()
    witness_gate(
        acceptance=[_criterion()],
        mutate=host_mutator(tmp_path),
        run_tests=lambda subset: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    assert target.read_bytes() == unchanged


def test_a_mutant_that_did_not_apply_is_named_not_counted(tmp_path):
    """A mutant that does not apply is `skip` for that criterion and is named
    in the summary — never `pass`, and never counted as a witness that did
    its job."""
    _write(tmp_path, "a.py", "def total(x):\n    return x\n")  # `find` absent
    criterion = _criterion()

    def run_tests(subset):
        raise AssertionError("the tests gate must not run for an unapplied mutant")

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=run_tests
    )

    assert result.status == "skip"
    assert criterion.witness in result.summary
    assert not result.failures


def test_a_runner_that_broke_under_the_mutant_is_an_error(tmp_path):
    """A `tests` gate that reports `error` under the mutant is `error` here
    too, not `fail`. A test runner that could not start says nothing about
    whether the witness guards its claim, and charging that to the task is
    the collapse `DESIGN.md` refuses everywhere else."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def run_tests(subset):
        return GateResult(
            gate="tests", status="error", summary="pytest could not collect"
        )

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=run_tests
    )

    assert result.status == "error"


def test_a_spec_with_no_mutants_skips(tmp_path):
    """A spec whose criteria declare no mutants reports `skip` with a summary
    saying so. Every spec that exists today is in that state, and this gate
    must not fail a task for a field its own spec predates."""
    criterion = Criterion(claim="unrelated", witness="tests/test_x.py::test_a")

    # Asserted on the distinguishing phrase, not on "no" and "mutant" being
    # present: deleting the early return entirely left this green, because the
    # empty loop falls through to the terminal skip whose summary satisfies
    # both words just as well. That is the exact failure this criterion warns
    # about — a `skip` assertion passing for a different skip.
    result = witness_gate(
        acceptance=[criterion],
        mutate=host_mutator(tmp_path),
        run_tests=lambda subset: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    assert result.status == "skip"
    assert result.summary == "the spec declares no mutants"


def test_two_criteria_do_not_see_each_others_mutants(tmp_path):
    """The gate restores the tree before invoking anything else, so two
    criteria cannot interact. Each mutant is applied to a clean tree and
    undone before the next, which is what makes a survivor attributable to
    one claim rather than to the pair."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    _write(tmp_path, "b.py", "def other(y):\n    return min(y, 10)\n")

    first = _criterion(
        witness="tests/test_a.py::test_a",
        file="a.py",
        find="max(x, 0)",
        replace="x",
    )
    second = _criterion(
        witness="tests/test_b.py::test_b",
        file="b.py",
        find="min(y, 10)",
        replace="y",
    )

    seen_content: dict[str, tuple[bytes, bytes]] = {}

    def run_tests(subset):
        # Record exactly what the tree looks like for each invocation, so a
        # leaked mutant from the other criterion would show up here.
        seen_content[subset[0]] = (
            (tmp_path / "a.py").read_bytes(),
            (tmp_path / "b.py").read_bytes(),
        )
        return _tests(status="fail", collected=tuple(subset))

    result = witness_gate(
        acceptance=[first, second], mutate=host_mutator(tmp_path), run_tests=run_tests
    )

    assert result.status == "pass"
    a_during_first, b_during_first = seen_content[first.witness]
    assert a_during_first == b"def total(x):\n    return x\n"  # first's mutant applied
    assert (
        b_during_first == b"def other(y):\n    return min(y, 10)\n"
    )  # second untouched

    a_during_second, b_during_second = seen_content[second.witness]
    assert a_during_second == b"def total(x):\n    return max(x, 0)\n"  # first restored
    assert (
        b_during_second == b"def other(y):\n    return y\n"
    )  # second's mutant applied

    # And by the time the gate returns, both are back to their originals.
    assert (tmp_path / "a.py").read_bytes() == b"def total(x):\n    return max(x, 0)\n"
    assert (tmp_path / "b.py").read_bytes() == b"def other(y):\n    return min(y, 10)\n"


def test_the_tool_is_the_one_the_tests_gate_reported(tmp_path):
    """The `tool` field is obtained by executing the `tests` gate, never
    written as a literal. This is the invariant that separates a gate that
    ran from one that never did, and it is the whole reason this gate
    re-invokes a declared gate rather than shelling out to a runner."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def run_tests(subset):
        return _tests(status="fail", collected=tuple(subset), tool="pytest 9.9.9")

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=run_tests
    )

    assert result.tool == "pytest 9.9.9"


def test_a_tree_that_could_not_be_restored_is_an_error_not_a_pass(tmp_path):
    """The one branch that leaves a mutant in the worktree the task is
    packaged from, and it was guarded by nothing: mutating its `status` to
    `"pass"` left all eight tests green, so the gate could report success on a
    run whose mutant shipped in the diff.

    `run_tests` writes to the file here — a formatter hook, a concurrent
    write, the agent's own tooling — which is what makes `restore_mutant`'s
    whole-file digest refuse. That refusal exists precisely so this branch can
    fire; nothing exercised the caller's response to it."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def run_tests(subset):
        (tmp_path / "a.py").write_text("something else entirely\n")
        return _tests(status="fail", collected=(criterion.witness,))

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=run_tests
    )

    assert result.status == "error"
    assert "a.py" in result.summary
    assert "restore" in result.summary


def test_a_tests_gate_that_raises_is_an_error_not_a_pass(tmp_path):
    """`except Exception` records rather than swallows — but nothing asserted
    the status it records with. Mutating it to `"pass"` left eight green."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def run_tests(subset):
        raise RuntimeError("the runner would not start")

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=run_tests
    )

    assert result.status == "error"
    assert "the runner would not start" in result.summary
    # *Which* failure it was, on the ordinary path. Under the mutant that
    # raises the run's exception through the `with` instead of recording it,
    # the outer handler says "could not restore" about a cleanly restored tree
    # and this test passed anyway — the dual-failure test below only catches
    # that when the exit also raises.
    assert "could not be executed" in result.summary
    assert "could not restore" not in result.summary
    # And the tree is still restored, because the `finally` ran before the
    # recorded failure was reported.
    assert (tmp_path / "a.py").read_text() == "def total(x):\n    return max(x, 0)\n"


def test_an_inner_skip_is_not_counted_as_a_witness_that_died(tmp_path):
    """`status == "fail"` is the death test, and `!= "pass"` would read a
    `skip` as one — a witness that never ran, counted as a witness that
    noticed. That is the "quietly buys nothing" defect this gate exists to
    catch, one level up. The code gets it right; nothing held it there."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def run_tests(subset):
        return _tests(status="skip", collected=())

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=run_tests
    )

    assert result.status == "skip"
    assert criterion.witness in result.summary
    assert "skip" in result.summary


def test_an_interrupt_during_a_mutated_run_is_not_swallowed(tmp_path):
    """The regression test for this gate's own worst defect, and it needs two
    things at once — which is why the original bug report overstated it.

    The swallow lived in a `return` inside a `finally`. Reaching it required
    the restore to *also* fail, because the `return` sat inside the `except`
    that a failed restore triggers. A plain interrupt with a clean restore
    always propagated. So the test corrupts the file **and** interrupts.

    Measured: the whole restructure that fixed this passed against the
    unfixed file — 11 green — so until this test existed the fix was itself a
    claim guarded by nothing, in the pull request that builds the gate for
    exactly that."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def interrupt_and_corrupt(subset):
        (tmp_path / "a.py").write_text("something else entirely\n")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        witness_gate(
            acceptance=[criterion],
            mutate=host_mutator(tmp_path),
            run_tests=interrupt_and_corrupt,
        )


def test_a_clean_interrupt_still_restores_through_the_real_mutator(tmp_path):
    """The spy in `test_an_interrupt_still_propagates_through_the_new_seam`
    proves this gate lets *any* injected context manager's exit run; it says
    nothing about `saffron.mutation`'s real restore path, and every other
    interrupt test in this file corrupts or deletes the file before
    interrupting, so `KeyboardInterrupt` would propagate whether or not
    `restore_mutant` was ever called. This one does neither: the file is left
    alone, so a restore skipped entirely — not merely one that failed — would
    be caught here and nowhere else in this file."""
    original = "def total(x):\n    return max(x, 0)\n"
    _write(tmp_path, "a.py", original)
    target = tmp_path / "a.py"
    criterion = _criterion()

    def interrupt_cleanly(subset):
        assert target.read_bytes() != original.encode()  # the mutant is live
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        witness_gate(
            acceptance=[criterion],
            mutate=host_mutator(tmp_path),
            run_tests=interrupt_cleanly,
        )

    assert target.read_bytes() == original.encode(), (
        "the tree was left mutated by a clean interrupt — the restore was "
        "skipped, not merely raced"
    )


def test_a_restore_that_cannot_read_the_file_does_not_replace_the_interrupt(tmp_path):
    """`restore_mutant` guards neither its read nor its write, so a deleted
    file raises `OSError` from inside the `finally` — and an exception raised
    there *replaces* whatever was in flight. Measured before the fix: a
    `KeyboardInterrupt` came out as `FileNotFoundError` with the interrupt
    demoted to `__context__`, where nothing looks, so an `except Exception` up
    the stack would have swallowed what was a `BaseException`.

    Catching `OSError` beside `MutationError` is what keeps the `finally` from
    raising at all."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def interrupt_and_delete(subset):
        (tmp_path / "a.py").unlink()
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        witness_gate(
            acceptance=[criterion],
            mutate=host_mutator(tmp_path),
            run_tests=interrupt_and_delete,
        )


def test_a_deleted_file_is_an_error_not_an_escaping_oserror(tmp_path):
    """The same hole without an interrupt: the `OSError` escaped the gate
    entirely, so a caller expecting a `GateResult` got a traceback."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    def delete_the_file(subset):
        (tmp_path / "a.py").unlink()
        return _tests(status="fail", collected=(criterion.witness,))

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=delete_the_file
    )

    assert result.status == "error"
    assert "a.py" in result.summary


def test_a_blocking_witness_failure_is_an_ordinary_blocking_failure(tmp_path):
    """A blocking `witness` failure needs no special case downstream: it is
    an ordinary `GateResult` — it round-trips through the same JSON contract
    every gate uses, and its failure's `identity()` is the same stable
    4-tuple any other gate's blocking failure produces. It happens to invert
    one comparison internally (a `pass` is the bad news); nothing about its
    shape says so.

    **What this cannot assert, and why.** The claim this witnesses says the
    failure "reaches the phase that reads gate results". No test here drives
    that phase: `session._blocking` is a closure inside `run_one_cell`, and
    `saffron/cell/**` is `forbidden` to this spec. Measured while reviewing —
    inserting `if failure.gate == "witness": return False` into
    `session._blocking`, the literal special case this claim forbids, fails
    nothing in the whole suite.

    So this guards the *shape* half and not the *reaches* half, and the
    reaches half is currently false: `witness` is in no `advisory_gates` set,
    so a failure blocks at every tier rather than at `elevated` only
    (`docs/BACKLOG.md` item 71). Said here rather than left as an apparent
    omission — the assertions below are real, and they are not the claim."""
    _write(tmp_path, "a.py", "def total(x):\n    return max(x, 0)\n")
    criterion = _criterion(claim="the total is clamped at zero", replace="0")

    def run_tests(subset):
        return _tests(status="pass", collected=(criterion.witness,))

    result = witness_gate(
        acceptance=[criterion], mutate=host_mutator(tmp_path), run_tests=run_tests
    )
    assert result.status == "fail"

    # The failure's own fields, which nothing pinned: `identity()` is built
    # from `(gate, file, code, message)`, so an empty `file` or `code` makes
    # every survivor collide with every other and baseline subtraction cancel
    # the wrong one. Both mutated freely before this.
    assert result.failures[0].file == criterion.witness
    assert result.failures[0].code == "survived-mutant"

    # Round-trips exactly like any other gate's result — no field only
    # `witness` carries, nothing lost or added by serializing it.
    round_tripped = GateResult.model_validate(json.loads(result.model_dump_json()))
    assert round_tripped == result

    # `identity()` reads it the same way it reads every gate's failure: by
    # (gate, file, code, normalized message) — never by anything special to
    # `witness` — and it is stable across two structurally-identical calls,
    # which is what makes a repeat failure comparable to a baseline one.
    again = witness_gate(
        acceptance=[criterion],
        mutate=host_mutator(tmp_path),
        run_tests=lambda subset: _tests(status="pass", collected=(criterion.witness,)),
    )
    assert identity("witness", result.failures[0]) == identity(
        "witness", again.failures[0]
    )


def test_the_gate_mutates_through_an_injected_context_manager():
    """The gate takes a callable from a mutant to a context manager, and
    holds no path of its own. This drives it with a fake `mutate` that never
    touches a real filesystem at all — no `tmp_path`, no disk — which is the
    whole reason this refactor exists: one gate that can serve a host tree or
    a cell's volume without knowing which it has."""
    events: list[tuple[str, Mutant]] = []

    @contextlib.contextmanager
    def fake_mutate(mutant: Mutant):
        events.append(("entered", mutant))
        yield None
        events.append(("exited", mutant))

    criterion = _criterion()

    def run_tests(subset):
        assert subset == [criterion.witness]
        return _tests(status="fail", collected=(criterion.witness,))

    result = witness_gate(
        acceptance=[criterion], mutate=fake_mutate, run_tests=run_tests
    )

    assert result.status == "pass"
    assert criterion.mutant is not None
    assert events == [
        ("entered", criterion.mutant),
        ("exited", criterion.mutant),
    ]


def test_the_mutation_is_undone_however_the_block_ends():
    """The context manager restores on exit however the block ends — a
    witness that died, one that survived, an inner `error`, or an exception
    in flight. Driven with a spy `mutate` rather than real files, so what is
    checked is that the gate always lets the context manager's own exit run,
    never that particular bytes come back."""
    criterion = _criterion()

    def make_mutate(events: list[str]):
        @contextlib.contextmanager
        def mutate(mutant: Mutant):
            events.append("entered")
            try:
                yield None
            finally:
                events.append("exited")

        return mutate

    for status in ("fail", "pass", "error"):
        events: list[str] = []
        witness_gate(
            acceptance=[criterion],
            mutate=make_mutate(events),
            run_tests=lambda subset, s=status: _tests(status=s),
        )
        assert events == ["entered", "exited"]

    # An exception raised by `run_tests` (not a `BaseException`) is recorded,
    # not raised through the `with` — the exit still runs, and runs before
    # this gate decides anything.
    events = []
    witness_gate(
        acceptance=[criterion],
        mutate=make_mutate(events),
        run_tests=lambda subset: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    assert events == ["entered", "exited"]


def test_an_interrupt_still_propagates_through_the_new_seam():
    """An interrupt during a mutated run still propagates and still
    restores — the defect this gate already shipped once, now guarded at the
    new seam: the context manager's exit, not a `finally` this gate writes
    itself. `KeyboardInterrupt` is a `BaseException`; the recorded-exception
    handling around `run_tests` only ever catches `Exception`, so this one
    goes straight through the `with`, into `mutate`'s own exit, and out."""
    events: list[str] = []

    @contextlib.contextmanager
    def mutate(mutant: Mutant):
        events.append("entered")
        try:
            yield None
        finally:
            events.append("exited")

    criterion = _criterion()

    def run_tests(subset):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        witness_gate(acceptance=[criterion], mutate=mutate, run_tests=run_tests)

    assert events == ["entered", "exited"]


def test_a_mutator_that_cannot_reach_the_tree_skips():
    """A mutator that cannot reach the tree reports `skip`, never `error`. A
    gate that could not run says so; ending the attempt over it would charge
    a task for infrastructure. This is the branch a not-yet-wired cell
    mutator relies on: yielding a reason rather than applying anything is the
    identical, non-committal outcome as a mutant that simply did not apply."""
    criterion = _criterion()

    @contextlib.contextmanager
    def unreachable(mutant: Mutant):
        yield "the cell's volume is not wired yet"

    result = witness_gate(
        acceptance=[criterion],
        mutate=unreachable,
        run_tests=lambda subset: (_ for _ in ()).throw(
            AssertionError("must not run — the mutant never applied")
        ),
    )

    assert result.status == "skip"
    assert criterion.witness in result.summary
    assert "not wired" in result.summary
    assert not result.failures


def test_a_mutator_that_fails_on_entry_is_not_reported_as_a_failed_restore():
    """ "Could not restore" is the loudest thing this gate says: its own
    docstring makes it mean a mutated tree is still out there and will ship in
    the diff. Saying it about a `mutate` that raised on *entry* — where nothing
    was ever applied — sends an operator hunting a poisoned worktree that does
    not exist.

    Not a corner case for long. `SA-0062`'s cell mutator enters through a
    container exec, which can fail routinely, so this wording lands on the
    common path the moment that spec merges."""

    @contextlib.contextmanager
    def raises_on_entry(mutant):
        raise OSError("read-only volume")
        # Unreachable, and not decoration: the `yield` is what makes this a
        # generator, which is what makes the raise land in `__enter__`
        # rather than at the `mutate(mutant)` call.
        yield None

    result = witness_gate(
        acceptance=[_criterion()],
        mutate=raises_on_entry,
        run_tests=lambda subset: _tests(status="fail", collected=()),
    )

    assert result.status == "error"
    assert "could not apply" in result.summary
    assert "could not restore" not in result.summary
    assert "read-only volume" in result.summary


def test_a_failed_restore_is_still_reported_as_one():
    """The other side of the verb: once the mutant is applied, a raising exit
    *is* a failed restore and must keep saying so. A flag that always read
    "could not apply" would be as wrong as the one that always read "could not
    restore"."""

    @contextlib.contextmanager
    def raises_on_exit(mutant):
        yield None
        raise OSError("volume went away")

    result = witness_gate(
        acceptance=[_criterion()],
        mutate=raises_on_exit,
        run_tests=lambda subset: _tests(status="fail", collected=()),
    )

    assert result.status == "error"
    assert "could not restore" in result.summary
    assert "volume went away" in result.summary


def test_a_run_failure_and_a_restore_failure_are_both_named():
    """What recording the run's exception actually buys. Deleting the inner
    `try/except` — letting `run_tests`'s exception propagate through the `with`
    and be caught by the outer handler — passed all 1437 tests: `mutate`
    restores either way, so nothing observable changed except that the run's
    failure vanished from the summary.

    Two different subsystems failed and the operator gets both sentences."""

    @contextlib.contextmanager
    def raises_on_exit(mutant):
        yield None
        raise OSError("volume went away")

    def run_tests(subset):
        raise RuntimeError("the runner would not start")

    result = witness_gate(
        acceptance=[_criterion()], mutate=raises_on_exit, run_tests=run_tests
    )

    assert result.status == "error"
    assert "could not restore" in result.summary
    assert "the run also failed" in result.summary
    assert "the runner would not start" in result.summary


def test_a_later_criterion_failing_on_entry_is_not_blamed_on_an_earlier_one():
    """`applied` resets per criterion, and hoisting it out of the loop passes
    every other test in this file — measured. Under that mutant a spec whose
    first criterion applies cleanly and whose second raises on entry reports
    `could not restore` about a tree that is clean: the exact defect the flag
    was added to remove, in the multi-criterion case, which is the ordinary
    one.

    A single-criterion test cannot see this, which is what makes it the most
    valuable line here and the easiest to leave out."""
    first = _criterion(witness="tests/t.py::one", file="a.py")
    second = _criterion(witness="tests/t.py::two", file="b.py")

    @contextlib.contextmanager
    def clean_then_raising(mutant):
        if mutant.file == "a.py":
            yield None  # applies and restores without complaint
            return
        raise OSError("container exec lost its connection")
        # Unreachable, and load-bearing: it makes this a generator, so the
        # raise lands in `__enter__`.
        yield None

    result = witness_gate(
        acceptance=[first, second],
        mutate=clean_then_raising,
        run_tests=lambda subset: _tests(status="fail", collected=(first.witness,)),
    )

    assert result.status == "error"
    assert "b.py" in result.summary
    assert "could not apply" in result.summary
    assert "could not restore" not in result.summary
