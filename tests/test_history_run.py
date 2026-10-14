"""`session.run_history` and REVIEW's wiring of it (backlog item b-a8270f).

`History` is imported inside each test body, never at module scope. `revert`
re-runs these witnesses with the source files reverted. A module-scope
import of a name this spec adds would turn that run into a collection error.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from saffron.cell import runtime, worktree
from saffron.gates.contract import GateResult
from saffron.phases import review
from tests.test_session import (
    _APPLY,
    _GATE_CONTAINER,
    _PLAN,
    _block,
    _drive,
    _spec,
    _stub_the_runtime,
    _turn,
)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout


def _bare_mirror_with_a_done_spec(tmp_path: Path, spec_id: str) -> tuple[Path, str]:
    """A real bare `r.git`, one commit, `spec_id`'s spec at
    `.saffron/specs/done/`. Returns the mirror path and the spec's sha256."""
    mirrors_dir = tmp_path / "mirrors"
    mirrors_dir.mkdir(parents=True)
    work = tmp_path / "mirror-work"
    specs_dir = work / ".saffron" / "specs" / "done"
    specs_dir.mkdir(parents=True)
    spec_path = specs_dir / f"{spec_id}-done.md"
    spec_path.write_text(
        "---\n"
        f"id: {spec_id}\n"
        "title: t\n"
        "type: feature\n"
        "---\n"
        "## Acceptance criteria\n"
        "- [ ] does the thing\n"
    )
    _git(work, "init", "-q")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "T")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "spec")
    mirror = mirrors_dir / "r.git"
    subprocess.run(
        ["git", "clone", "-q", "--bare", str(work), str(mirror)],
        check=True,
        capture_output=True,
    )
    sha = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    return mirror, sha


def _ledger_with_a_merged_task(tmp_path: Path, spec_id: str, spec_sha: str):
    from saffron.ledger import Ledger

    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", "origin", "/host/mirrors/r.git", None)
    run_id = ledger.create_run(repo_id, "b" * 40)
    task_id = ledger.create_task(run_id, spec_id, spec_sha, "saffron/x")
    ledger.set_task_state(task_id, "MERGED")
    return ledger


# Non-empty, so the env check tells `dict(thread_env)` from a literal `{}`.
_THREAD_ENV = {"SAFFRON_THREAD_PROBE": "declared"}


def _call_history(spec, mirror, case, ledger, *, out_dir=None):
    """Every `run_history` call's shared, uninteresting kwargs, named once."""
    from saffron.cell import session

    return session.run_history(
        spec=spec,
        repo=case / "repo",
        mirror=mirror,
        gates_dir=case / "gates",
        thread_env=_THREAD_ENV,
        patch="",
        ledger=ledger,
        out_dir=case / "out" if out_dir is None else out_dir,
        created=set(),
        note=lambda *a: None,
    )


_HISTORY_COMMAND_SCRIPT = """\
import json, os, sqlite3, sys
from pathlib import Path

sys.path.insert(0, {root!r})
from saffron import projection
from saffron.ledger import Ledger

home = Path(os.environ["SAFFRON_HISTORY_HOME"])
conn = sqlite3.connect(home / "ledger.db")
conn.execute("CREATE TABLE history_probe (n INTEGER)")
conn.commit()
print("tasks=" + str(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]))
batch_file = home / "batches" / "v0" / "marker.txt"
print("batch_file=" + (batch_file.read_text() if batch_file.is_file() else "None"))
out = home / "out"
out.mkdir(exist_ok=True)
result = projection.materialize(Ledger(home / "ledger.db"), out, home / "p.ttl")
print("reasons=" + json.dumps({{str(k): v.reason for k, v in result.left_out.items()}}))
print("HISTORY_PROBE_DONE", file=sys.stderr)
sys.exit(3)
"""


class _FakeCriticCell:
    """Stands in for `session.critic_cell`, recording each call's keywords
    and giving each entry its own writable state directory."""

    def __init__(self, tmp_path: Path, *, raises: Exception | None = None):
        self.tmp_path = tmp_path
        self.raises = raises
        self.calls: list[dict] = []
        self.entries = 0
        self.mapping: dict[str, str] = {}

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self._cm(kwargs)

    def _cm(self, kwargs):
        import contextlib

        @contextlib.contextmanager
        def _inner():
            self.entries += 1
            state_dir = self.tmp_path / f"state-{self.entries}"
            state_dir.mkdir(parents=True, exist_ok=True)
            mapping = {worktree.STATE_MOUNT: str(state_dir)}
            for mount in kwargs["extra_mounts"]:
                mapping[mount.target] = mount.source
            self.mapping = mapping
            if self.raises is not None:
                raise self.raises
            yield f"container-{self.entries}"

        return _inner()


def _rewrite_mount_paths(text: str, mapping: dict[str, str]) -> str:
    """Every mount target, as a whole path only, replaced by its host
    source: `/history` must not match inside `/agent-state/history`."""
    for target, source in mapping.items():
        pattern = re.compile(r"(?<![\w/])" + re.escape(target) + r"(?=[/'\"]|$)")
        text = pattern.sub(source.replace("\\", "\\\\"), text)
    return text


def _hash_tree(mapping: dict[str, str]) -> dict[str, str]:
    """Every file's digest under every mount source but the writable state
    directory. A read-only mount must still read this way after an exec."""
    hashes: dict[str, str] = {}
    for target, source in mapping.items():
        if target == worktree.STATE_MOUNT:
            continue
        for path in sorted(Path(source).rglob("*")):
            if path.is_file():
                hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _run_one_history_case(monkeypatch, case, *, batches, saffron_root):
    """One pass of the unit witness, isolated so no closure below it binds a
    variable a caller's own loop still owns (B023)."""
    from saffron.cell import session
    from saffron.intake import History

    case.mkdir()
    monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", case / "history-root")

    mirror, spec_sha = _bare_mirror_with_a_done_spec(case, "SY-1")
    ledger = _ledger_with_a_merged_task(case, "SY-1", spec_sha)

    out_dir = case / "out"
    out_dir.mkdir()
    if batches:
        (out_dir / "marker.txt").write_text("a batch-tree file")

    # A stale file left in the snapshot's directory by a killed History run.
    stale_dir = session.HISTORY_SOURCE_ROOT / "SY-1"
    stale_dir.mkdir(parents=True)
    (stale_dir / "stale.txt").write_text("leftover")

    fake = _FakeCriticCell(case)
    monkeypatch.setattr(session, "critic_cell", fake)

    mount_listings: list[list[str]] = []
    hash_pairs: list[tuple[dict, dict]] = []
    timeouts: list[float | None] = []
    workdirs: list[str | None] = []

    command_script = case / "history_command.py"
    command_script.write_text(_HISTORY_COMMAND_SCRIPT.format(root=saffron_root))

    def _exec(container, argv, *, workdir=None, timeout_s=None):
        timeouts.append(timeout_s)
        workdirs.append(workdir)
        before = _hash_tree(fake.mapping)
        rewritten = [_rewrite_mount_paths(str(a), fake.mapping) for a in argv]
        mount_listings.append(
            sorted(p.name for p in Path(fake.mapping[worktree.HISTORY_MOUNT]).iterdir())
        )
        result = subprocess.run(
            rewritten, capture_output=True, text=True, cwd=str(case)
        )
        after = _hash_tree(fake.mapping)
        hash_pairs.append((before, after))
        return runtime.Completed(result.returncode, result.stdout, result.stderr)

    monkeypatch.setattr(runtime, "exec_", _exec)

    history = History(command=f"{sys.executable} {command_script}", batches=batches)
    spec = _spec(spec_id="SY-1", history=history)
    result = _call_history(spec, mirror, case, ledger, out_dir=out_dir)

    # The stale file never reached the mount: the directory was cleared
    # before the snapshot was written.
    assert mount_listings[0] == ["ledger.db"]

    # Neither read-only mount source changed across either exec.
    for before, after in hash_pairs:
        assert before == after

    # Both execs ran at the 600-second bound, never `exec_`'s own default.
    assert timeouts == [600.0, 600.0]
    assert workdirs == [worktree.WORKTREE_MOUNT] * 2

    # `network=None`, and the repo's declared env alone, no proxy.
    assert fake.calls[0]["network"] is None
    assert fake.calls[0]["env"] == _THREAD_ENV

    mounts_by_target = {m.target: m for m in fake.calls[0]["extra_mounts"]}
    assert all(m.kind == "bind" and m.readonly for m in mounts_by_target.values())
    assert mounts_by_target[worktree.HISTORY_MOUNT].readonly
    # The mirrors mount: the real directory holding `r.git`.
    assert mounts_by_target[worktree.MIRRORS_MOUNT].source == str(mirror.parent)

    # The batch tree mount is present only when declared, and is the real
    # `out_dir`, never a copy.
    batch_mounts = [
        m for m in fake.calls[0]["extra_mounts"] if m.target == worktree.BATCHES_MOUNT
    ]
    if batches:
        (mount,) = batch_mounts
        assert mount.source == str(out_dir)
        assert mount.readonly
    else:
        assert batch_mounts == []

    assert result["started"] is True
    assert result["exit_code"] == 3
    assert "HISTORY_PROBE_DONE" in result["stderr"]
    assert "tasks=1" in result["stdout"]
    if batches:
        assert "batch_file=a batch-tree file" in result["stdout"]
    else:
        assert "batch_file=None" in result["stdout"]
    # The projection never read this task out as `spec_not_found`: the
    # rewritten `mirror_path` let it find the spec in the real mirror.
    reasons_line = next(
        line for line in result["stdout"].splitlines() if line.startswith("reasons=")
    )
    reasons = json.loads(reasons_line.removeprefix("reasons="))
    assert "spec_not_found" not in reasons.values()

    # The snapshot directory is gone once `run_history` returns.
    assert not (session.HISTORY_SOURCE_ROOT / "SY-1").exists()


def test_the_history_command_reads_a_writable_copy_and_never_writes_the_mount(
    monkeypatch, tmp_path
):
    """The unit witness: a real ledger, a real bare mirror, and a real
    command script. Drives `run_history` directly, with a stubbed
    `critic_cell` and a `runtime.exec_` that runs the rewritten argv on
    the host."""
    import contextlib

    from saffron.cell import session
    from saffron.intake import History

    saffron_root = str(Path(__file__).resolve().parents[1])

    _run_one_history_case(
        monkeypatch, tmp_path / "batches", batches=True, saffron_root=saffron_root
    )
    _run_one_history_case(
        monkeypatch, tmp_path / "no-batches", batches=False, saffron_root=saffron_root
    )

    # A `critic_cell` that raises still removes the snapshot directory.
    case = tmp_path / "raises"
    case.mkdir()
    monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", case / "history-root")
    mirror, spec_sha = _bare_mirror_with_a_done_spec(case, "SY-1")
    ledger = _ledger_with_a_merged_task(case, "SY-1", spec_sha)
    fake = _FakeCriticCell(case, raises=runtime.CellRuntimeError("boom"))
    monkeypatch.setattr(session, "critic_cell", fake)
    spec = _spec(spec_id="SY-1", history=History(command="true"))
    with contextlib.suppress(runtime.CellRuntimeError):
        _call_history(spec, mirror, case, ledger)
    assert not (session.HISTORY_SOURCE_ROOT / "SY-1").exists()


def test_each_history_stream_is_cut_at_the_bound_and_says_how_much_it_cut(
    monkeypatch, tmp_path
):
    """Over the bound by different counts on each stream, and both within
    it, driven through `run_history` with a scripted command exec."""
    from saffron.cell import session
    from saffron.intake import History

    monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", tmp_path / "history-root")
    mirror, spec_sha = _bare_mirror_with_a_done_spec(tmp_path, "SY-1")
    ledger = _ledger_with_a_merged_task(tmp_path, "SY-1", spec_sha)

    fake = _FakeCriticCell(tmp_path)
    monkeypatch.setattr(session, "critic_cell", fake)

    # Not a uniform fill, so keeping the tail reads back differently.
    over_out = "a" * session.HISTORY_OUTPUT_CHARS + "z" * 37
    over_err = "b" * session.HISTORY_OUTPUT_CHARS + "z" * 5
    within_out = "x" * 10
    within_err = "y" * 20

    calls = {"n": 0}

    def _exec(container, argv, *, workdir=None, timeout_s=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return runtime.Completed(0, "", "")
        return runtime.Completed(0, over_out, over_err)

    monkeypatch.setattr(runtime, "exec_", _exec)
    spec = _spec(spec_id="SY-1", history=History(command="true"))
    result = _call_history(spec, mirror, tmp_path, ledger)
    assert (
        result["stdout"] == "a" * session.HISTORY_OUTPUT_CHARS + "\n[37 characters cut]"
    )
    assert (
        result["stderr"] == "b" * session.HISTORY_OUTPUT_CHARS + "\n[5 characters cut]"
    )

    # Within the bound, on a second run, both streams come back whole.
    monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", tmp_path / "history-root-2")
    fake2 = _FakeCriticCell(tmp_path)
    monkeypatch.setattr(session, "critic_cell", fake2)
    calls2 = {"n": 0}

    def _exec2(container, argv, *, workdir=None, timeout_s=None):
        calls2["n"] += 1
        if calls2["n"] == 1:
            return runtime.Completed(0, "", "")
        return runtime.Completed(0, within_out, within_err)

    monkeypatch.setattr(runtime, "exec_", _exec2)
    result2 = _call_history(spec, mirror, tmp_path, ledger)
    assert result2["stdout"] == within_out
    assert result2["stderr"] == within_err


def _override_history_execs(monkeypatch, cell, *, command, copy_result, command_result):
    """After `_stub_the_runtime`: the exec whose argv mentions `command`
    returns `command_result`. The one that mentions `HISTORY_MOUNT` and not
    `command` is the copy and returns `copy_result`. Everything else gets a
    clean result, which is what every other cell `critic_cell` opens sees on its own commit."""

    def _exec(container, argv, **kwargs):
        cell.execs.append((container, tuple(argv), ""))
        if any(command in str(a) for a in argv):
            # Network=None, exactly as the gate table's own Gate-only cell: the
            # same name, reused once that cell has already torn down.
            assert container == _GATE_CONTAINER
            return command_result
        if any(worktree.HISTORY_MOUNT in str(a) for a in argv):
            assert container == _GATE_CONTAINER
            return copy_result
        return runtime.Completed(0, "", "")

    monkeypatch.setattr("saffron.cell.runtime.exec_", _exec)


_HISTORY_COMMAND = "python3 /work/marker-history-command.py"


def _history_json(case):
    return json.loads((case / "out" / "SY-1" / "history.json").read_text())


def _lens_prompts(cell):
    return cell.system_prompts[2 : 2 + len(review.LENSES)]


def _drive_with_history(
    monkeypatch, case, cell, *, command=_HISTORY_COMMAND, capture=None
):
    from saffron.intake import Criterion, History

    # A criterion, so the section follows `criteria_section`'s last line.
    acceptance = [Criterion(claim="the last claim", witness="tests/t.py::test_w")]

    return _drive(
        monkeypatch,
        case,
        cell=cell,
        turns=[_turn(_block(_PLAN)), _turn()],
        spec=_spec(history=History(command=command), acceptance=acceptance),
        capture=capture,
    )


def test_every_lens_reads_the_history_run_and_the_task_dir_records_it(
    monkeypatch, tmp_path
):
    """REVIEW runs the history copy and command once, after a clean gate
    comparison and before any lens, and records `history.json`. Every
    lens's prompt carries the command and what happened. A spec with no
    `history` gets none of it."""
    from saffron.cell import session

    command = _HISTORY_COMMAND

    # 1: a run that exits 3.
    case = tmp_path / "exits-3"
    monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", case / "history-root")
    cell = _stub_the_runtime(monkeypatch)
    _override_history_execs(
        monkeypatch,
        cell,
        command=command,
        copy_result=runtime.Completed(0, "", ""),
        command_result=runtime.Completed(3, "some output", "some stderr"),
    )
    outcome, _ledger = _drive_with_history(monkeypatch, case, cell)
    assert outcome.state == "READY_FOR_REVIEW"
    history_json = _history_json(case)
    assert history_json["started"] is True
    assert history_json["exit_code"] == 3
    assert history_json["timed_out"] is False
    assert history_json["stdout"] == "some output"
    assert history_json["stderr"] == "some stderr"
    assert history_json["command"] == command
    # Each once: one copy exec, then one command exec.
    history_execs = [
        argv
        for _c, argv, _in in cell.execs
        if any(worktree.HISTORY_MOUNT in str(a) or command in str(a) for a in argv)
    ]
    assert len(history_execs) == 2
    assert sum(any(command in str(a) for a in argv) for argv in history_execs) == 1
    lens_prompts = _lens_prompts(cell)
    assert len(lens_prompts) == len(review.LENSES)
    for prompt in lens_prompts:
        assert "- [ ] the last claim\n\n## History run\n" in prompt
        assert command in prompt
        assert "exited 3" in prompt
        assert "some output" in prompt
        assert "some stderr" in prompt
    # `critic_cell` forwarded the history mount to `prepare_worktree`.
    assert any(
        any(m.target == worktree.HISTORY_MOUNT for m in w.get("extra_mounts", ()))
        for w in cell.worktrees
    )

    # 2: a run that times out.
    case = tmp_path / "times-out"
    monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", case / "history-root")
    cell = _stub_the_runtime(monkeypatch)
    _override_history_execs(
        monkeypatch,
        cell,
        command=command,
        copy_result=runtime.Completed(0, "", ""),
        command_result=runtime.Completed(
            124, "partial", "cut short", timed_out=True, bound="wall"
        ),
    )
    outcome, _ledger = _drive_with_history(monkeypatch, case, cell)
    assert outcome.state == "READY_FOR_REVIEW"
    assert _history_json(case)["timed_out"] is True
    for prompt in _lens_prompts(cell):
        assert "timed out" in prompt
        assert "exited 124" not in prompt

    # 3: an errored gate comparison never runs the history cell.
    case = tmp_path / "gate-errored"
    monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", case / "history-root")
    cell = _stub_the_runtime(
        monkeypatch,
        gate_cell_suite=[
            GateResult(gate="tests", status="error", tool="pytest 1", summary="boom")
        ],
    )
    outcome, _ledger = _drive_with_history(monkeypatch, case, cell)
    assert outcome.state == "GATE_ERROR"
    assert not (case / "out" / "SY-1" / "history.json").exists()
    assert not any(command in str(argv) for _c, argv, _in in cell.execs)

    # 4: the history cell's own patch apply fails (the second `_APPLY`).
    case = tmp_path / "history-cell-refused"
    monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", case / "history-root")
    cell = _stub_the_runtime(monkeypatch)
    applies = {"n": 0}

    def _exec_stream(container, argv, *, stdin_data="", on_line=None, **k):
        cell.execs.append((container, tuple(argv), stdin_data))
        if tuple(argv) == _APPLY:
            applies["n"] += 1
            if applies["n"] == 2:
                return runtime.Completed(1, "", "error: patch does not apply")
        return runtime.Completed(0, "", "")

    monkeypatch.setattr("saffron.cell.runtime.exec_stream", _exec_stream)
    from saffron.events import PhaseStart

    events: list = []
    outcome, _ledger = _drive_with_history(monkeypatch, case, cell, capture=events)
    assert outcome.state == "EXHAUSTED"
    assert not (case / "out" / "SY-1" / "history.json").exists()
    # The Gate-only cell refused it, which is not the critic cell (CONTEXT.md).
    refusal = [
        e.detail
        for e in events
        if isinstance(e, PhaseStart) and "did not apply" in e.detail
    ]
    assert refusal == [
        "the exported patch did not apply in the Gate-only cell — error: patch does not apply"
    ]
    # No lens ran: only the plan and implement turns.
    assert len(cell.turns) == 2

    # 5: a spec with no `history` gets no history cell and no section.
    case = tmp_path / "no-history"
    monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", case / "history-root")
    cell = _stub_the_runtime(monkeypatch)
    outcome, _ledger = _drive(
        monkeypatch, case, cell=cell, turns=[_turn(_block(_PLAN)), _turn()]
    )
    assert outcome.state == "READY_FOR_REVIEW"
    assert not (case / "out" / "SY-1" / "history.json").exists()
    for prompt in _lens_prompts(cell):
        assert "## History run" not in prompt
    # No history cell either: no exec names the mount, no worktree carries it.
    assert not any(worktree.HISTORY_MOUNT in str(argv) for _c, argv, _in in cell.execs)
    assert not any(w.get("extra_mounts") for w in cell.worktrees)


def test_a_history_run_whose_copy_fails_never_runs_the_command_and_says_so(
    monkeypatch, tmp_path
):
    """The in-cell copy runs as its own exec, before the command's. A copy
    that exits non-zero, or times out, ends the run there: `started` is
    false, the other fields are the copy's, and no lens reads an `exited`
    line."""
    from saffron.cell import session

    command = _HISTORY_COMMAND
    copies = {
        "exits-1": runtime.Completed(1, "", "no space left on device"),
        "times-out": runtime.Completed(
            0, "", "no space left on device", timed_out=True, bound="wall"
        ),
    }
    for name, copy_result in copies.items():
        case = tmp_path / name
        monkeypatch.setattr(session, "HISTORY_SOURCE_ROOT", case / "history-root")
        cell = _stub_the_runtime(monkeypatch)
        _override_history_execs(
            monkeypatch,
            cell,
            command=command,
            copy_result=copy_result,
            command_result=runtime.Completed(0, "should never run", ""),
        )
        outcome, _ledger = _drive_with_history(monkeypatch, case, cell)
        assert outcome.state == "READY_FOR_REVIEW"
        history_json = _history_json(case)
        assert history_json["started"] is False
        assert history_json["exit_code"] == copy_result.returncode
        assert history_json["stderr"] == "no space left on device"
        assert not any(command in str(argv) for _c, argv, _in in cell.execs)
        for prompt in _lens_prompts(cell):
            assert "did not start" in prompt
            assert "no space left on device" in prompt
            assert "exited" not in prompt
