"""The runtime seam. Command construction is unit-tested; the four assertions
that actually chose this runtime live in spikes/cell-runtime.sh."""

from __future__ import annotations

from saffron.cell import runtime


def test_mount_renders_the_runtime_flag():
    m = runtime.Mount(kind="volume", source="saffron-wt-x", target="/work")
    assert m.to_flag() == "type=volume,source=saffron-wt-x,target=/work"


def test_readonly_mount_carries_the_suffix():
    m = runtime.Mount(kind="volume", source="s", target="/t", readonly=True)
    assert m.to_flag() == "type=volume,source=s,target=/t,readonly"


def test_run_argv_carries_every_control():
    argv = runtime._run_argv(
        image="saffron/cell:saffron",
        command=["nproc"],
        name="cell-1",
        network="saffron-cells",
        env={"HTTPS_PROXY": "http://10.88.0.2:3128"},
        cpus=1,
        memory="4g",
        mounts=[runtime.Mount("volume", "saffron-wt-1", "/work")],
        detach=False,
    )
    assert argv[:2] == ["container", "run"]
    assert "--rm" in argv
    assert "--cap-drop" in argv and "ALL" in argv
    assert "--network" in argv and "saffron-cells" in argv
    assert "--cpus" in argv and "1" in argv
    assert "--memory" in argv and "4g" in argv
    assert "type=volume,source=saffron-wt-1,target=/work" in argv
    assert "HTTPS_PROXY=http://10.88.0.2:3128" in argv
    assert argv[-2:] == ["saffron/cell:saffron", "nproc"]


def test_detached_run_is_not_removed_on_exit():
    argv = runtime._run_argv(
        image="i",
        command=[],
        name="c",
        network=None,
        env=None,
        cpus=None,
        memory=None,
        mounts=[],
        detach=True,
    )
    assert "-d" in argv
    assert "--rm" not in argv


def test_container_ip_ignores_the_gateway():
    inspected = '{"networks":[{"gateway":"10.88.0.1","address":"10.88.0.4/24"}]}'
    assert runtime._first_address(inspected, "10.88.0.") == "10.88.0.4"


def test_container_ip_is_none_when_absent():
    assert runtime._first_address('{"networks":[]}', "10.88.0.") is None


def test_call_is_the_public_form_of_the_private_helper():
    done = runtime.call(["true"], timeout_s=10)
    assert done.returncode == 0
    assert done.timed_out is False


def test_the_subnet_is_the_only_place_the_network_is_written():
    """Derived, not re-typed: a stale second copy probes an address that no
    longer exists and reports 'unreachable' having reached nothing."""
    assert runtime.SUBNET_PREFIX == "10.88.0."
    assert runtime.GATEWAY == "10.88.0.1"
    assert runtime.GATEWAY.startswith(runtime.SUBNET_PREFIX)
