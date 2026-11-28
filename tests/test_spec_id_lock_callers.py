"""Four callers outside `run_task`'s own lock (`saffron/task.py:980`) each
pre-clean a spec-keyed runtime name with no lock (`b-d9ed45`). Each now takes
`cell_name_lock` first. `saffron.cell_name_lock` is imported inside each test
body, the convention `tests/test_cell_name_lock.py` sets.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest


class _SpyStop(KeyboardInterrupt):
    """Raised by a `runtime._call` spy below, never a bare
    `KeyboardInterrupt`: a bare one would stop the whole pytest session
    rather than failing one test (`tests/test_cell_name_lock.py`)."""


def _call_spy(calls: list[list[str]]):
    def _spy(argv, timeout_s=120):
        calls.append(list(argv))
        raise _SpyStop("stopped before any real runtime call")

    return _spy


def _assert_locked(lock_root: Path, spec_id: str, *, names: str) -> str:
    """Asserts a second open of `spec_id`'s own lock file, from this
    process, is refused right now, and that the holder's text names
    `names`. Returns the raise's own `str()`."""
    from saffron import cell_name_lock

    with (
        pytest.raises(cell_name_lock.LockHeld) as info,
        cell_name_lock.lock(lock_root, spec_id, "a contender"),
    ):
        pass
    reason = str(info.value)
    assert re.search(rf"\b{os.getpid()}\b", reason)
    assert names in reason
    return reason


def test_regate_declines_a_spec_id_another_process_holds_before_any_runtime_call(
    tmp_path, monkeypatch, capsys
):
    from saffron import cell_name_lock, regate
    from saffron import task as task_module
    from saffron.cell import runtime
    from saffron.repos import image as repo_image
    from tests.test_regate import (
        _build_fixture,
        _fake_reverify,
        _gh_pr_view,
        _install_probe_fakes,
        _seed_task,
        _seeding_ledger,
    )

    lock_root = tmp_path / "locks"
    monkeypatch.setattr(task_module, "CELL_NAME_LOCK_ROOT", lock_root)

    def _case(name: str):
        case_dir = tmp_path / name
        case_dir.mkdir()
        fixture = _build_fixture(case_dir)
        home = case_dir / "home"
        pr_url = "https://github.com/o/r/pull/9"
        ledger = _seeding_ledger(home / "ledger.db", fixture.origin_url)
        mirror_path = home / "mirror.git"
        task_id = _seed_task(
            ledger,
            origin_url=fixture.origin_url,
            mirror_path=mirror_path,
            base_sha=fixture.base_sha,
            spec_sha=fixture.spec_sha,
            branch="saffron/SA-0005",
            pr_url=pr_url,
            pushed_sha=fixture.packaged_sha,
        )
        return case_dir, fixture, home, mirror_path, pr_url, ledger, task_id

    package_phase_module = __import__("saffron.phases.package", fromlist=["x"])

    # 1. Held as `SA-0005`, then as `sa-0005`: declined before any of the
    # image build, the probe or `reverify` is reached.
    for n, holder_id in enumerate(("SA-0005", "sa-0005")):
        case_dir, fixture, home, mirror_path, pr_url, ledger, task_id = _case(
            f"held-{n}"
        )
        with pytest.MonkeyPatch.context() as case_mp:
            build_calls: list = []
            case_mp.setattr(
                repo_image,
                "build_cell_image",
                lambda repo, calls=build_calls: calls.append(repo) or "img",
            )
            order: list = []
            _install_probe_fakes(case_mp, order)
            reverify_calls: list = []
            case_mp.setattr(
                package_phase_module, "reverify", _fake_reverify(reverify_calls)
            )

            held_pid = cell_name_lock.lock(lock_root, holder_id, "the holder")
            held_pid.__enter__()
            capsys.readouterr()
            try:
                result = regate.run_regate(
                    task_id,
                    repo=fixture.work.resolve(),
                    ledger=ledger,
                    out_dir=home / "out",
                    mirror_path=mirror_path,
                    gh=_gh_pr_view(pr_url, "OPEN", "main", []),
                )
            finally:
                held_pid.__exit__(None, None, None)
        printed = capsys.readouterr().out
        assert result == 1
        assert build_calls == []
        assert order == []
        assert reverify_calls == []
        expected_line = (
            f"regate: SA-0005's cell is held by pid {os.getpid()}'s the holder"
        )
        assert expected_line in printed
        ledger.close()

    # 2. Beside a holder of `SA-0006`, a take of `SA-0005` inside the probe's
    # own network removal is refused, naming `saffron regate <task id>`.
    case_dir, fixture, home, mirror_path, pr_url, ledger, task_id = _case("sibling")
    with pytest.MonkeyPatch.context() as case_mp:
        build_calls = []
        case_mp.setattr(
            repo_image,
            "build_cell_image",
            lambda repo: build_calls.append(repo) or "img",
        )
        held_sibling = cell_name_lock.lock(lock_root, "SA-0006", "sibling holder")
        held_sibling.__enter__()
        texts: list[str] = []
        argvs: list[list[str]] = []
        try:

            def _spy(argv, timeout_s=120):
                argvs.append(list(argv))
                with (
                    pytest.raises(cell_name_lock.LockHeld) as info,
                    cell_name_lock.lock(lock_root, "SA-0005", "a contender"),
                ):
                    pass
                texts.append(str(info.value))
                raise _SpyStop("stopped before any real runtime call")

            case_mp.setattr(runtime, "_call", _spy)
            with pytest.raises(_SpyStop):
                regate.run_regate(
                    task_id,
                    repo=fixture.work.resolve(),
                    ledger=ledger,
                    out_dir=home / "out",
                    mirror_path=mirror_path,
                    gh=_gh_pr_view(pr_url, "OPEN", "main", []),
                )
        finally:
            held_sibling.__exit__(None, None, None)
    assert build_calls == [fixture.work.resolve()]
    assert argvs and argvs[0][-3:] == [
        "network",
        "rm",
        f"saffron-regate-probe-{task_id}",
    ]
    assert texts and f"saffron regate {task_id}" in texts[0]
    with cell_name_lock.lock(lock_root, "SA-0005", "after"):
        pass
    ledger.close()

    # 3. Clean: the lock spans the image build, `reverify` and
    # `record_regate`, and lets go once `run_regate` returns 0.
    case_dir, fixture, home, mirror_path, pr_url, ledger, task_id = _case("green")

    def _build_image(repo):
        _assert_locked(lock_root, "SA-0005", names=f"saffron regate {task_id}")
        build_calls.append(repo)
        return "img"

    with pytest.MonkeyPatch.context() as case_mp:
        build_calls = []
        case_mp.setattr(repo_image, "build_cell_image", _build_image)
        order = []
        _install_probe_fakes(case_mp, order)
        reverify_calls = []
        fake_reverify = _fake_reverify(reverify_calls)

        def _wrapped_reverify(**kwargs):
            _assert_locked(lock_root, "SA-0005", names=f"saffron regate {task_id}")
            return fake_reverify(**kwargs)

        case_mp.setattr(package_phase_module, "reverify", _wrapped_reverify)
        orig_record_regate = ledger.record_regate
        record_calls: list = []

        def _wrapped_record_regate(*a, **k):
            _assert_locked(lock_root, "SA-0005", names=f"saffron regate {task_id}")
            record_calls.append((a, k))
            return orig_record_regate(*a, **k)

        ledger.record_regate = _wrapped_record_regate

        result = regate.run_regate(
            task_id,
            repo=fixture.work.resolve(),
            ledger=ledger,
            out_dir=home / "out",
            mirror_path=mirror_path,
            gh=_gh_pr_view(pr_url, "OPEN", "main", []),
        )
    assert result == 0
    assert len(record_calls) == 1
    with cell_name_lock.lock(lock_root, "SA-0005", "after-green"):
        pass
    ledger.close()


def test_qualification_probes_nothing_for_a_held_spec_id_and_says_why(
    tmp_path, monkeypatch
):
    from saffron import cell_name_lock
    from saffron import task as task_module
    from saffron.cell import session
    from saffron.qualify import qualify
    from tests.test_qualify import _build, _spec_key

    lock_root = tmp_path / "locks"
    monkeypatch.setattr(task_module, "CELL_NAME_LOCK_ROOT", lock_root)
    this_pid = os.getpid()

    probed_claims = ("f1", "f2", "f3", "f4", "f7", "f8", "f10")

    for n, holder_id in enumerate(("TE-2", "te-2")):
        case_dir = tmp_path / f"held-{n}"
        case_dir.mkdir()
        built = _build(case_dir, monkeypatch)
        te2_key = _spec_key(built.ledger, "TE-2")

        held = cell_name_lock.lock(lock_root, holder_id, "the holder")
        held.__enter__()
        try:
            result = built.run(qualify)
        finally:
            held.__exit__(None, None, None)

        assert built.calls == []
        pool = {(q.task_key, q.finding.claim): q for q in result.pool}
        for claim in probed_claims:
            q = pool[(te2_key, claim)]
            assert q.outcome == "unverified"
            assert re.search(rf"\b{this_pid}\b", q.reason)
            assert "the holder" in q.reason
        f5 = pool[(te2_key, "f5")]
        assert (f5.outcome, f5.reason) == ("unanchored", "")
        s1 = pool[(te2_key, "s1")]
        assert (s1.outcome, s1.reason) == ("note", "")
        grouped_claims = {
            claim
            for g in result.groups
            for claim in (f.finding.claim for f in g.findings)
        }
        assert {"f6", "s2"} <= grouped_claims

    # Beside a holder of `TE-1`: `TE-2`'s own probe still runs, once, and a
    # take of `TE-2` inside that call is refused naming `qualification`.
    case_dir = tmp_path / "sibling"
    case_dir.mkdir()
    built = _build(case_dir, monkeypatch)
    original_probe = session.probe_findings
    texts: list[str] = []

    def _wrapped(targets, **kw):
        with (
            pytest.raises(cell_name_lock.LockHeld) as info,
            cell_name_lock.lock(lock_root, "TE-2", "a contender"),
        ):
            pass
        texts.append(str(info.value))
        return original_probe(targets, **kw)

    monkeypatch.setattr(session, "probe_findings", _wrapped)

    held = cell_name_lock.lock(lock_root, "TE-1", "sibling holder")
    held.__enter__()
    try:
        built.run(qualify)
    finally:
        held.__exit__(None, None, None)
    assert len(built.calls) == 1
    assert texts and "qualification" in texts[0]


def test_a_layer_cell_beside_a_held_spec_id_raises_before_any_runtime_call(
    tmp_path, monkeypatch
):
    from saffron import cell_name_lock, end_review
    from saffron import task as task_module
    from saffron.cell import runtime, session

    lock_root = tmp_path / "locks"
    monkeypatch.setattr(task_module, "CELL_NAME_LOCK_ROOT", lock_root)

    repo = tmp_path / "repo"
    mirror = tmp_path / "mirror"
    gates_dir = tmp_path / "gates"
    fields = end_review.LayerFields(
        spec_id="SY-1",
        branch="saffron/SY-1",
        pr_url="https://h/pull/1",
        base="b" * 40,
        head="h" * 40,
        known="",
        diff_base="b" * 40,
    )

    calls: list[list[str]] = []
    monkeypatch.setattr(runtime, "_call", _call_spy(calls))

    # 1. Held as `SY-1`, then as `sy-1`: raised before any runtime call.
    for holder_id in ("SY-1", "sy-1"):
        held = cell_name_lock.lock(lock_root, holder_id, "the holder")
        held.__enter__()
        try:
            with (
                pytest.raises(cell_name_lock.LockHeld) as info,
                end_review.layer_cell(
                    fields,
                    repo=repo,
                    mirror=mirror,
                    gates_dir=gates_dir,
                    thread_env={},
                ),
            ):
                pass
            reason = str(info.value)
            assert re.search(rf"\b{os.getpid()}\b", reason)
            assert "the holder" in reason
        finally:
            held.__exit__(None, None, None)
        assert calls == []

    # 2. Beside a holder of `SY-2`, a take of `SY-1` inside the pre-clean
    # `remove_container` is refused, naming `a layer cell (...)`.
    held2 = cell_name_lock.lock(lock_root, "SY-2", "sibling holder")
    held2.__enter__()
    texts: list[str] = []
    try:

        def _spy(argv, timeout_s=120):
            calls.append(list(argv))
            with (
                pytest.raises(cell_name_lock.LockHeld) as info,
                cell_name_lock.lock(lock_root, "SY-1", "a contender"),
            ):
                pass
            texts.append(str(info.value))
            raise _SpyStop("stopped before any real runtime call")

        monkeypatch.setattr(runtime, "_call", _spy)
        with (
            pytest.raises(_SpyStop),
            end_review.layer_cell(
                fields, repo=repo, mirror=mirror, gates_dir=gates_dir, thread_env={}
            ),
        ):
            pass
        assert calls[0][-3:] == ["rm", "-f", "saffron-endreview-SY-1"]
        assert texts and "a layer cell (end_review.layer_cell)" in texts[0]
    finally:
        held2.__exit__(None, None, None)
    with cell_name_lock.lock(lock_root, "SY-1", "after"):
        pass

    # 3. With `cell_up`, `cell_down` and `remove_container` faked: a take is
    # refused from inside each, and succeeds once the block exits.
    monkeypatch.setattr(runtime, "remove_container", lambda name: None)
    up_calls: list = []
    down_calls: list = []

    def _cell_up(**kw):
        _assert_locked(lock_root, "SY-1", names="a layer cell (end_review.layer_cell)")
        up_calls.append(kw)

    def _cell_down(**kw):
        _assert_locked(lock_root, "SY-1", names="a layer cell (end_review.layer_cell)")
        down_calls.append(kw)

    monkeypatch.setattr(session, "cell_up", _cell_up)
    monkeypatch.setattr(session, "cell_down", _cell_down)
    with end_review.layer_cell(
        fields, repo=repo, mirror=mirror, gates_dir=gates_dir, thread_env={}
    ):
        pass
    assert len(up_calls) == 1
    assert len(down_calls) == 1
    with cell_name_lock.lock(lock_root, "SY-1", "after-block"):
        pass


def test_package_refuses_a_spec_id_another_process_holds_before_its_probe_network(
    tmp_path, monkeypatch
):
    from saffron import cell_name_lock, mutants, preflight
    from saffron import task as task_module
    from saffron.cell import runtime
    from saffron.cell.session import CellOutcome
    from saffron.intake import Spec
    from saffron.ledger import Ledger
    from saffron.phases import package as package_phase
    from saffron.record.memory import MemoryRecord
    from saffron.repos import image as repo_image

    lock_root = tmp_path / "locks"
    monkeypatch.setattr(task_module, "CELL_NAME_LOCK_ROOT", lock_root)
    this_pid = os.getpid()
    spec = Spec(
        id="SY-1",
        title="A spec",
        type="feature",
        touches=["src/**"],
        acceptance_criteria=["it works"],
    )

    def _ready(out_dir: Path) -> task_module.ReadyTask:
        outcome = CellOutcome(
            state="READY_FOR_REVIEW", task_id=1, run_id=1, task_dir=out_dir / "SY-1"
        )
        return task_module.ReadyTask(outcome=outcome, spec=spec, parent_branch=None)

    def _no_mutants(*a: object, **k: object) -> str | None:
        return None

    def _common(monkeypatch, out_dir: Path) -> Ledger:
        ledger = Ledger(out_dir.parent / "ledger.db", record=MemoryRecord())
        # `object.__setattr__`, not a plain assignment `ty` would refuse to
        # re-type: still an instance attribute, read the same way at call time.
        object.__setattr__(ledger, "task_mutants_commit", _no_mutants)
        monkeypatch.setattr(task_module, "ready_task", lambda *a, **k: _ready(out_dir))
        monkeypatch.setattr(
            preflight,
            "prepare_mirror",
            lambda repo, mirror_path: (mirror_path, "u", "b" * 40),
        )
        monkeypatch.setattr(
            mutants, "attach_mutants_at", lambda mirror, commit, spec: spec
        )
        return ledger

    # 1. Held as `SY-1`, then as `sy-1`: `Refused` before any network, with
    # the image still built outside the lock.
    for n, holder_id in enumerate(("SY-1", "sy-1")):
        case_dir = tmp_path / f"held-{n}"
        out_dir = case_dir / "out"
        out_dir.mkdir(parents=True)
        ledger = _common(monkeypatch, out_dir)
        build_calls: list = []
        monkeypatch.setattr(
            repo_image,
            "build_cell_image",
            lambda repo, built=build_calls: built.append(repo) or "img",
        )
        calls: list = []
        monkeypatch.setattr(runtime, "_call", _call_spy(calls))

        held = cell_name_lock.lock(lock_root, holder_id, "the holder")
        held.__enter__()
        try:
            result = task_module.package_ready_task(
                "SY-1",
                repo=case_dir / "repo",
                repo_id=1,
                ledger=ledger,
                out_dir=out_dir,
                mirror_path=case_dir / "mirror",
                token=None,
            )
        finally:
            held.__exit__(None, None, None)
        assert isinstance(result, task_module.Refused)
        assert re.search(rf"\b{this_pid}\b", result.reason)
        assert "the holder" in result.reason
        assert build_calls == [case_dir / "repo"]
        assert calls == []
        ledger.close()

    # 2. Beside a holder of `SY-2`, a take of `SY-1` inside the probe
    # network's own removal is refused, naming the batch tree.
    case_dir = tmp_path / "sibling"
    out_dir = case_dir / "out"
    out_dir.mkdir(parents=True)
    ledger = _common(monkeypatch, out_dir)
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "img")
    held2 = cell_name_lock.lock(lock_root, "SY-2", "sibling holder")
    held2.__enter__()
    argvs: list[list[str]] = []
    texts: list[str] = []
    try:

        def _spy(argv, timeout_s=120):
            argvs.append(list(argv))
            with (
                pytest.raises(cell_name_lock.LockHeld) as info,
                cell_name_lock.lock(lock_root, "SY-1", "a contender"),
            ):
                pass
            texts.append(str(info.value))
            raise _SpyStop("stopped before any real runtime call")

        monkeypatch.setattr(runtime, "_call", _spy)
        with pytest.raises(_SpyStop):
            task_module.package_ready_task(
                "SY-1",
                repo=case_dir / "repo",
                repo_id=1,
                ledger=ledger,
                out_dir=out_dir,
                mirror_path=case_dir / "mirror",
                token=None,
            )
    finally:
        held2.__exit__(None, None, None)
    assert argvs and argvs[0][-3:] == ["network", "rm", "saffron-hostprobe-sy-1"]
    assert texts and str(out_dir) in texts[0]
    with cell_name_lock.lock(lock_root, "SY-1", "after"):
        pass
    ledger.close()

    # 3. Clean: a take is refused inside each of the pre-clean and the
    # final `remove_network`, `allocate_network` and the host probe.
    case_dir = tmp_path / "green"
    out_dir = case_dir / "out"
    out_dir.mkdir(parents=True)
    ledger = _common(monkeypatch, out_dir)
    monkeypatch.setattr(repo_image, "build_cell_image", lambda repo: "img")
    order: list[str] = []

    def _remove_network(name):
        order.append("remove")
        _assert_locked(lock_root, "SY-1", names=str(out_dir))

    def _allocate_network(name):
        order.append("allocate")
        _assert_locked(lock_root, "SY-1", names=str(out_dir))
        return "10.44.0.0/24"

    def _assert_unreachable(image_tag, network, *, gateway, ports, sockets):
        order.append("assert")
        _assert_locked(lock_root, "SY-1", names=str(out_dir))

    monkeypatch.setattr(runtime, "remove_network", _remove_network)
    monkeypatch.setattr(runtime, "allocate_network", _allocate_network)
    monkeypatch.setattr(runtime, "gateway", lambda subnet: "10.44.0.1")
    monkeypatch.setattr(preflight, "host_probe_ports", lambda: ([], [], []))
    monkeypatch.setattr(preflight, "probe_addresses", lambda gateway: [gateway])
    monkeypatch.setattr(preflight, "assert_host_is_unreachable", _assert_unreachable)

    package_calls: list = []

    def _fake_package(outcome, **kwargs):
        with cell_name_lock.lock(lock_root, "SY-1", "inside package"):
            pass
        package_calls.append(kwargs)
        return package_phase.PackageResult(
            state="READY_FOR_REVIEW", pr_url="https://x/pull/1", branch="saffron/SY-1"
        )

    monkeypatch.setattr(package_phase, "package", _fake_package)

    result = task_module.package_ready_task(
        "SY-1",
        repo=case_dir / "repo",
        repo_id=1,
        ledger=ledger,
        out_dir=out_dir,
        mirror_path=case_dir / "mirror",
        token=None,
    )
    assert isinstance(result, package_phase.PackageResult)
    assert order == ["remove", "allocate", "assert", "remove"]
    assert len(package_calls) == 1
    ledger.close()
