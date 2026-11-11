"""A batch bounds the cell runtime's build cache at its start (b-2bc0d5)."""

from __future__ import annotations

from saffron import cli
from saffron.cell import runtime
from saffron.cell.runtimes import apple, podman
from saffron.cli import main


def _reclaim_spy(monkeypatch, calls, done):
    """Record each reclaim and readiness call, in order, and answer the
    reclaim with `done`, or raise it when it is an exception."""

    def _reclaim(timeout_s=0.0):
        calls.append("reclaim")
        if isinstance(done, BaseException):
            raise done
        return done

    def _readiness(*_a, **_k):
        calls.append("readiness")
        return cli.preflight.Readiness(False, "auth", "stopped here")

    monkeypatch.setattr(runtime, "reclaim_build_cache", _reclaim, raising=False)
    monkeypatch.setattr(cli.preflight, "check_readiness", _readiness)


def _cache_lines(capsys) -> list[str]:
    return [
        line for line in capsys.readouterr().out.splitlines() if "build cache" in line
    ]


def test_a_batch_reclaims_the_build_cache_before_readiness_on_both_forms(
    tmp_path, monkeypatch, capsys
):
    """Each batch form reclaims once, before readiness reads the disk, and
    says nothing when it worked. A night refused on a runtime never proven
    reclaims nothing."""
    argv = ["--home", str(tmp_path / "h"), "batch", "--repo", str(tmp_path)]
    for form in ([], ["--stack"]):
        monkeypatch.setattr(runtime, "_selected", apple.DIALECT)
        calls: list[str] = []
        _reclaim_spy(monkeypatch, calls, runtime.Completed(1, "", "refused"))
        assert main([*argv, *form]) == 2
        assert len(_cache_lines(capsys)) == 1, form

        calls.clear()
        _reclaim_spy(monkeypatch, calls, runtime.Completed(0, "", ""))
        assert main([*argv, *form]) == 2
        assert calls == ["reclaim", "readiness"], form
        assert _cache_lines(capsys) == [], form

        monkeypatch.setattr(runtime, "_selected", podman.DIALECT)
        calls.clear()
        assert main([*argv, *form]) == 2
        assert calls == [], form
        assert "batch: refused" in capsys.readouterr().out


def test_a_reclaim_that_fails_is_printed_and_the_batch_goes_on(
    tmp_path, monkeypatch, capsys
):
    """A refused, silent, timed-out or unrunnable reclaim each prints why, and
    readiness still runs after it."""
    monkeypatch.setattr(runtime, "_selected", apple.DIALECT)
    argv = ["--home", str(tmp_path / "h"), "batch", "--repo", str(tmp_path)]
    cases = [
        (runtime.Completed(1, "", "Error: builder is stopping"), "builder is stopping"),
        (runtime.Completed(3, "", ""), "exit 3"),
        (
            runtime.Completed(124, "", "killed", timed_out=True, bound="wall"),
            "timed out",
        ),
        (runtime.CellRuntimeError("container could not be executed"), "could not be"),
    ]
    for done, detail in cases:
        calls: list[str] = []
        _reclaim_spy(monkeypatch, calls, done)
        assert main(argv) == 2
        assert calls == ["reclaim", "readiness"], detail
        lines = _cache_lines(capsys)
        assert len(lines) == 1, detail
        assert lines[0].startswith("batch: build cache not reclaimed — "), detail
        assert detail in lines[0]
