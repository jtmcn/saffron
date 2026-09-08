"""Tests for wiring `witness` into the host-invoked runner (§5.4.1,
`docs/BACKLOG.md` item 69).

`SA-0056` built the mutant/witness data model and `SA-0057` built
`saffron/gates/core/witness.py`'s `witness_gate`, but nothing invoked it. This
covers the wiring in `saffron/gates/runner.py` (`run_witness`, `run_suite`)
and the blocking-level decision in `saffron/gates/contract.py`
(`witness_blocking`) that turns it on.
"""

from __future__ import annotations

from pathlib import Path

from saffron.gates.contract import GateResult, witness_blocking
from saffron.gates.core.witness import witness_gate
from saffron.gates.runner import run_suite, run_witness
from saffron.intake import Criterion, Mutant
from saffron.mutation import host_mutator


def _gate_script(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return path


def _criterion(
    *,
    claim: str = "the total is clamped at zero",
    witness: str = "tests/test_billing.py::test_clamped",
    file: str = "a.py",
    find: str = "max(x, 0)",
    replace: str = "0",
) -> Criterion:
    return Criterion(
        claim=claim,
        witness=witness,
        mutant=Mutant(file=file, find=find, replace=replace),
    )


def test_the_witness_gate_runs_after_the_tests_it_re_invokes(tmp_path):
    """`witness` re-invokes `tests`'s own result, so it must run after it —
    regardless of where `tests` sits in the repo's declared gate order."""
    (tmp_path / "a.py").write_text("def total(x):\n    return max(x, 0)\n")

    lint = _gate_script(
        tmp_path,
        "lint",
        'echo \'{"gate":"lint","status":"pass","tool":"fixture 1.0",'
        '"failures":[],"summary":"clean"}\'\n',
    )
    # `tests` is declared *first* here, and a naive "append witness at the
    # end" wiring would still put it after `lint` — this is only a real test
    # if `lint` is declared *after* `tests` and still ends up after `witness`.
    tests = _gate_script(
        tmp_path,
        "tests",
        'echo \'{"gate":"tests","status":"fail","tool":"pytest 8.3.2",'
        f'"collected":["{_criterion().witness}"],'
        '"failures":[{"file":"'
        f"{_criterion().witness}"
        '","code":"AssertionError","message":"boom"}],"summary":"1 failed"}\'\n',
    )

    criterion = _criterion()
    results = run_suite(
        {"tests": tests, "lint": lint},
        cwd=tmp_path,
        acceptance=[criterion],
        mutate=host_mutator(tmp_path),
    )

    assert [r.gate for r in results] == ["tests", "witness", "lint"]
    assert results[1].status == "pass"  # the witness died under its mutant


def test_witness_is_advisory_at_standard_and_blocking_when_elevated():
    assert witness_blocking("standard") is False
    assert witness_blocking("elevated") is True


def test_a_tests_gate_that_takes_no_subset_skips_the_witness_gate(tmp_path):
    """A `tests` gate that errors on any subset argument — even before any
    mutant is applied — is not evidence about a witness. `witness` reports
    `skip`, not `error`, and no mutant is ever touched."""
    original = "def total(x):\n    return max(x, 0)\n"
    (tmp_path / "a.py").write_text(original)

    # Answers cleanly with no subset, but breaks the moment it is given one —
    # the shape of a `tests` gate that never met `revert`'s subset obligation.
    tests = _gate_script(
        tmp_path,
        "tests",
        'if [ "$#" -gt 0 ]; then\n'
        "  exit 3\n"
        "fi\n"
        'echo \'{"gate":"tests","status":"pass","tool":"pytest 8.3.2",'
        '"collected":[],"failures":[],"summary":"all pass"}\'\n',
    )

    criterion = _criterion()
    # The plain (no-subset) run's own enumeration — a real, collected node
    # id the probe is entitled to trust, distinct from `criterion.witness`
    # itself, so this test cannot pass for the wrong reason (a stale
    # criterion id, rather than a genuine subset limitation).
    tests_result = GateResult(
        gate="tests",
        status="pass",
        tool="pytest 8.3.2",
        collected=["tests/test_other.py::test_unrelated"],
    )
    result = run_witness(
        gates={"tests": tests},
        cwd=tmp_path,
        acceptance=[criterion],
        mutate=host_mutator(tmp_path),
        tests_result=tests_result,
    )

    assert result is not None
    assert result.status == "skip"
    assert result.gate == "witness"
    # The probe ran before any mutant was applied, so the file is untouched.
    assert (tmp_path / "a.py").read_text() == original


def test_a_stale_witness_id_does_not_discard_another_criterions_finding(tmp_path):
    """The subset-capability probe must never be drawn from a criterion's own
    declared `witness` — that id is operator-written and can be stale (a
    typo, a renamed test, a moved file). Probing with it would read "this one
    criterion's id no longer exists" as "this repo's `tests` gate cannot be
    filtered at all" and `skip` the whole gate without ever really trying —
    which would be silently wrong for a repo whose `tests` gate handles
    subset filtering perfectly well.

    This asserted `error` for the stale id until item **83**. `witness.py`'s
    own comment had recorded that `error`-vs-`skip` as unresolved and said to
    settle it in the backlog rather than by editing one side to match; 83 is
    that resolution, measured on a real run that exited 2 before buying a
    turn. A witness the suite never collected is **unproven**, not broken.

    What the test protects is unchanged and is now asserted directly rather
    than through the status: one bad id must not cost another criterion its
    real verdict. The stale one is named in the summary, the sound one still
    survives its mutant, and that survival is still a `fail`."""
    (tmp_path / "a.py").write_text("def total(x):\n    return max(x, 0)\n")
    stale = _criterion(
        witness="tests/test_gone.py::test_does_not_exist_anymore",
        file="a.py",
        find="max(x, 0)",
        replace="0",
    )

    # Genuinely supports subset filtering — it only errors for the one id
    # that was never collected, exactly how a real pytest-backed `tests`
    # gate answers a node id that no longer exists.
    tests = _gate_script(
        tmp_path,
        "tests",
        'case "$1" in\n'
        "  *test_gone*)\n"
        "    exit 3\n"
        "    ;;\n"
        "esac\n"
        'echo "{\\"gate\\":\\"tests\\",\\"status\\":\\"pass\\",'
        '\\"tool\\":\\"pytest 8.3.2\\",\\"collected\\":[\\"$1\\"],'
        '\\"failures\\":[],\\"summary\\":\\"1 passed\\"}"\n',
    )
    tests_result = GateResult(
        gate="tests",
        status="pass",
        tool="pytest 8.3.2",
        # A real, collected id — never `stale.witness` itself.
        collected=["tests/test_other.py::test_unrelated"],
    )

    # A second criterion whose witness the suite did collect, and whose mutant
    # it survives: the real finding that must not be lost to the stale id.
    sound = _criterion(
        witness="tests/test_other.py::test_unrelated",
        file="a.py",
        find="return max",
        replace="return  max",
    )

    result = run_witness(
        gates={"tests": tests},
        cwd=tmp_path,
        acceptance=[stale, sound],
        mutate=host_mutator(tmp_path),
        tests_result=tests_result,
    )

    # The old, buggy probe (drawn from `stale.witness` itself) would have
    # errored immediately and reported `witness` as `skip` without ever
    # calling `witness_gate`. The fixed probe succeeds on the real canary, so
    # `witness_gate` genuinely runs — and the stale id is now set aside by
    # name instead of aborting the attempt for everyone else.
    assert result is not None
    assert result.status == "fail"
    assert "test_does_not_exist_anymore" in result.summary
    assert [f.file for f in result.failures] == [sound.witness]


def test_the_result_names_each_criterion_not_a_count(tmp_path):
    """Two criteria, two different fates: one survives its mutant (a real
    finding), one never applies at all. The composed result must still be
    able to say which is which — not just "N of M" — so the survivor is
    named in `failures` and the one that never applied is still traceable in
    the summary."""
    (tmp_path / "a.py").write_text("def total(x):\n    return max(x, 0)\n")
    (tmp_path / "b.py").write_text("def other(y):\n    return min(y, 10)\n")

    survivor = _criterion(
        witness="tests/test_a.py::test_a", file="a.py", find="max(x, 0)", replace="0"
    )
    never_applies = _criterion(
        witness="tests/test_b.py::test_b",
        file="b.py",
        find="not-there-at-all",
        replace="0",
    )

    # A `tests` gate that answers `pass` for whatever single witness it is
    # asked about — the survivor's mutant is applied, run, and reported
    # `pass` (survives); the other criterion's mutant never applies, so this
    # script is never even invoked for it.
    tests = _gate_script(
        tmp_path,
        "tests",
        'echo "{\\"gate\\":\\"tests\\",\\"status\\":\\"pass\\",'
        '\\"tool\\":\\"pytest 8.3.2\\",\\"collected\\":[\\"$1\\"],'
        '\\"failures\\":[],\\"summary\\":\\"1 passed\\"}"\n',
    )

    tests_result = GateResult(
        gate="tests",
        status="pass",
        tool="pytest 8.3.2",
        collected=[survivor.witness, never_applies.witness],
    )
    result = run_witness(
        gates={"tests": tests},
        cwd=tmp_path,
        acceptance=[survivor, never_applies],
        mutate=host_mutator(tmp_path),
        tests_result=tests_result,
    )

    assert result is not None
    assert result.status == "fail"
    # Named, not counted: exactly the surviving criterion's witness, not a
    # bare "1 of 2" summary standing in for which one it was.
    assert [f.file for f in result.failures] == [survivor.witness]
    assert survivor.claim in result.failures[0].message
    # The criterion whose mutant never applied is still nameable, even
    # though it produced no `Failure` entry of its own.
    assert never_applies.witness in result.summary

    # And the tree is restored: both files are back to their originals.
    assert (tmp_path / "a.py").read_text() == "def total(x):\n    return max(x, 0)\n"
    assert (tmp_path / "b.py").read_text() == "def other(y):\n    return min(y, 10)\n"


def test_a_tests_gate_that_ignores_the_subset_cannot_attribute_a_death(tmp_path):
    """Tolerating the subset argument is not honouring it. A `tests` gate that
    accepts the argument and runs everything anyway passed the probe — and then
    an *unrelated* test failing under a mutant read as "the witness died",
    reporting `pass`. That is the false confidence §5.4.1 exists to refuse,
    wearing a verification.

    Told apart by what the probe collected: a gate that honoured the filter
    enumerates the one id it was given."""
    (tmp_path / "a.py").write_text("def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    # Answers `pass`, and reports every test it collected — the whole suite,
    # not the one id it was handed.
    tests = _gate_script(
        tmp_path,
        "tests",
        'echo \'{"gate":"tests","status":"pass","tool":"pytest 8.3.2",'
        f'"collected":["{criterion.witness}","tests/t.py::other"],'
        '"failures":[],"summary":"2 passed"}\'\n',
    )
    tests_result = GateResult(
        gate="tests",
        status="pass",
        tool="pytest 8.3.2",
        collected=[criterion.witness, "tests/t.py::other"],
    )

    result = run_witness(
        gates={"tests": tests},
        cwd=tmp_path,
        acceptance=[criterion],
        mutate=host_mutator(tmp_path),
        tests_result=tests_result,
    )

    assert result is not None
    assert result.status == "skip"
    assert "did not honour" in result.summary
    # No mutant was applied, so the tree is untouched.
    assert (tmp_path / "a.py").read_text() == "def total(x):\n    return max(x, 0)\n"


def test_a_collected_line_that_is_an_option_is_not_probed_with(tmp_path):
    """`run_gate` builds `argv = [executable, *subset]` with no `--`, and this
    repo's `tests` gate calls any collection line holding `::` a name. A
    printed `--deselect=…` line is therefore an option to whatever runs it —
    the measured attack `revert._argv_safe` exists for.

    Worse here than in `revert`: one sample decided the whole gate, so a single
    stray line bought a blanket `skip` and discarded every criterion's real
    finding. The probe now skips unsafe names and tries more than one."""
    (tmp_path / "a.py").write_text("def total(x):\n    return max(x, 0)\n")
    criterion = _criterion()

    tests = _gate_script(
        tmp_path,
        "tests",
        'echo \'{"gate":"tests","status":"fail","tool":"pytest 8.3.2",'
        f'"collected":["{criterion.witness}"],'
        '"failures":[{"file":"'
        f"{criterion.witness}"
        '","code":"AssertionError","message":"boom"}],"summary":"1 failed"}\'\n',
    )
    # The poisoned line sorts first; the real id is behind it.
    tests_result = GateResult(
        gate="tests",
        status="pass",
        tool="pytest 8.3.2",
        collected=[f"--deselect={criterion.witness}", criterion.witness],
    )

    result = run_witness(
        gates={"tests": tests},
        cwd=tmp_path,
        acceptance=[criterion],
        mutate=host_mutator(tmp_path),
        tests_result=tests_result,
    )

    assert result is not None
    # It got past the probe on the safe id rather than skipping on the unsafe
    # one, so a real verdict was reached.
    assert result.status == "pass"


def test_a_repo_with_no_tests_gate_has_no_witness_gate(tmp_path):
    """`None`, not a `skip`: a repo that declares no `tests` gate has no runner
    for `witness` to re-invoke, so it leaves the suite entirely — the shape
    `revert` already uses. The docstring argued this at length and nothing
    executed it."""
    lint = _gate_script(
        tmp_path,
        "lint",
        'echo \'{"gate":"lint","status":"pass","tool":"fixture 1.0",'
        '"failures":[],"summary":"clean"}\'\n',
    )

    assert (
        run_witness(
            gates={"lint": lint},
            cwd=tmp_path,
            acceptance=[_criterion()],
            mutate=host_mutator(tmp_path),
            tests_result=None,
        )
        is None
    )


def test_no_readable_enumeration_is_a_skip_with_no_mutant_applied(tmp_path):
    """The other branch the docstring argued for and no test reached: nothing
    to probe *with*. `skip`, and no mutant is touched — "not proof of
    anything", the same as `revert`'s identical answer."""
    (tmp_path / "a.py").write_text("def total(x):\n    return max(x, 0)\n")
    tests = _gate_script(
        tmp_path,
        "tests",
        'echo \'{"gate":"tests","status":"pass","tool":"pytest 8.3.2",'
        '"failures":[],"summary":"ok"}\'\n',
    )

    for collected in (None, []):
        result = run_witness(
            gates={"tests": tests},
            cwd=tmp_path,
            acceptance=[_criterion()],
            mutate=host_mutator(tmp_path),
            tests_result=GateResult(
                gate="tests", status="pass", tool="pytest 8.3.2", collected=collected
            ),
        )
        assert result is not None
        assert result.status == "skip"
        assert "nothing to verify" in result.summary
        assert (
            tmp_path / "a.py"
        ).read_text() == "def total(x):\n    return max(x, 0)\n"


def test_the_wiring_passes_a_mutator_through_and_changes_no_verdict(tmp_path):
    """`run_suite` and `run_witness` pass the callable through in place of a
    path, and every existing caller and test still gets the same answers.
    This is a refactor: calling `witness_gate` directly with a real
    `host_mutator` and calling it through the wiring must produce the same
    verdict, and gate ordering, the pre-flight probe and the unproven
    accounting are all untouched."""
    (tmp_path / "a.py").write_text("def total(x):\n    return max(x, 0)\n")

    lint = _gate_script(
        tmp_path,
        "lint",
        'echo \'{"gate":"lint","status":"pass","tool":"fixture 1.0",'
        '"failures":[],"summary":"clean"}\'\n',
    )
    tests = _gate_script(
        tmp_path,
        "tests",
        'echo \'{"gate":"tests","status":"fail","tool":"pytest 8.3.2",'
        f'"collected":["{_criterion().witness}"],'
        '"failures":[{"file":"'
        f"{_criterion().witness}"
        '","code":"AssertionError","message":"boom"}],"summary":"1 failed"}\'\n',
    )
    criterion = _criterion()

    direct = witness_gate(
        acceptance=[criterion],
        mutate=host_mutator(tmp_path),
        run_tests=lambda subset: GateResult(
            gate="tests",
            status="fail",
            tool="pytest 8.3.2",
            collected=list(subset),
            failures=[],
            summary="1 failed",
        ),
    )

    results = run_suite(
        {"tests": tests, "lint": lint},
        cwd=tmp_path,
        acceptance=[criterion],
        mutate=host_mutator(tmp_path),
    )

    assert [r.gate for r in results] == ["tests", "witness", "lint"]
    wired = next(r for r in results if r.gate == "witness")
    assert wired.status == direct.status == "pass"

    # Omitted, as every real caller does today (`saffron/cell/**` wires no
    # mutator yet): `witness` is left out of the suite entirely, exactly as
    # `mutate=None` behaved before this callable existed under that name.
    unwired = run_suite({"tests": tests, "lint": lint}, cwd=tmp_path)
    assert [r.gate for r in unwired] == ["tests", "lint"]

    # And the tree the gate is packaged from is back to its original state.
    assert (tmp_path / "a.py").read_text() == "def total(x):\n    return max(x, 0)\n"
