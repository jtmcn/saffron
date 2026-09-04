from __future__ import annotations

import subprocess
import types
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from saffron import preflight
from saffron.cell import proxy, runtime

LSOF = (Path(__file__).parent / "fixtures" / "lsof-listen.txt").read_text()


NONE: frozenset[str] = frozenset()


def _ports(lsof_output: str, tolerated: frozenset[str] = NONE) -> list[int]:
    return preflight.probed_ports(preflight.listening_sockets(lsof_output), tolerated)[
        0
    ]


def test_real_lsof_output_yields_the_ports_a_cell_can_reach():
    """Captured from the machine v0.5 ran on. Its redis, its postgres and its
    six python servers are loopback-bound; four macOS services are not."""
    assert _ports(LSOF) == [3283, 5000, 7000, 49152, 60215, 60216]
    # The guessed list would have reported a clean probe against every one.
    assert not {5432, 6379, 8000}.intersection(_ports(LSOF))


def test_a_command_name_holding_a_space_still_parses():
    """lsof truncates COMMAND to nine characters, spaces included, so the row
    is read from the right."""
    row = (
        "COMMAND     PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME\n"
        "Google Ch  1234 joel   30u  IPv4 0x0000000000000001      0t0  "
        "TCP *:9222 (LISTEN)\n"
    )
    assert preflight.listening_sockets(row) == [("Google Ch", 9222)]


def test_a_listing_with_only_loopback_listeners_is_a_real_empty():
    """The floor: enumeration ran, and nothing it found is reachable."""
    rows = [
        line for line in LSOF.splitlines() if "127.0.0.1" in line or "[::1]" in line
    ]
    assert rows
    assert _ports(LSOF.splitlines()[0] + "\n" + "\n".join(rows)) == []


def test_lsof_missing_raises_rather_than_narrowing_the_probe_to_nothing(monkeypatch):
    """The `_lan_address` defect, one function over: an enumeration that fails
    silently makes the probe cover nothing and report green."""

    def _no_lsof(*_a, **_k):
        raise FileNotFoundError("lsof")

    monkeypatch.setattr(subprocess, "run", _no_lsof)
    with pytest.raises(runtime.CellRuntimeError, match="could not be enumerated"):
        preflight.host_probe_ports()


@pytest.mark.parametrize(
    "returncode,stdout,stderr",
    [
        (1, "", "lsof: WARNING: can't stat() ..."),  # nothing listed at all
        (0, "some other tool's output\n", ""),  # not lsof's listing
    ],
)
def test_a_listing_that_is_not_lsofs_raises(monkeypatch, returncode, stdout, stderr):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, returncode, stdout, stderr),
    )
    with pytest.raises(runtime.CellRuntimeError, match="produced no listing"):
        preflight.host_probe_ports()


def test_the_probe_script_carries_the_enumerated_ports():
    script = preflight._probe_script(["10.88.0.1"], [8000, 8001])
    assert "ports=[8000, 8001]" in script
    assert "addrs=['10.88.0.1']" in script


def test_nothing_is_tolerated_unless_it_is_named(monkeypatch):
    """The default, and the whole point of it: an unnamed listener is probed."""
    monkeypatch.delenv("SAFFRON_ALLOW_HOST_PROCESS", raising=False)
    assert preflight.tolerated_processes() == NONE
    ports, tolerated = preflight.probed_ports(
        preflight.listening_sockets(LSOF), preflight.tolerated_processes()
    )
    assert 49152 in ports and tolerated == []


def test_a_named_process_drops_out_of_the_probe(monkeypatch):
    """rapportd's three sockets, accepted by name — and only its three."""
    monkeypatch.setenv("SAFFRON_ALLOW_HOST_PROCESS", " rapportd , ")
    assert preflight.tolerated_processes() == {"rapportd"}
    ports, tolerated = preflight.probed_ports(
        preflight.listening_sockets(LSOF), preflight.tolerated_processes()
    )
    assert ports == [3283, 5000, 7000]
    assert tolerated == ["rapportd:49152", "rapportd:60215", "rapportd:60216"]


def test_a_different_process_on_a_tolerated_port_is_still_probed():
    """The name is what was accepted, not the number it happened to hold —
    rapportd's ports are dynamic, so the next thing on 49152 is a stranger."""
    assert preflight.probed_ports([("nc", 49152)], frozenset({"rapportd"}))[0] == [
        49152
    ]
    # Sharing a port with a tolerated process does not launder it, and it takes
    # the tolerated one back into the probe with it.
    ports, tolerated = preflight.probed_ports(
        [("nc", 49152), ("rapportd", 49152)], frozenset({"rapportd"})
    )
    assert ports == [49152] and tolerated == []


def test_enumeration_that_cannot_run_still_raises_when_a_process_is_named(monkeypatch):
    """Tolerating a listener must not become tolerating a probe that covered
    nothing — the `_lan_address` defect, wearing an allowlist."""
    monkeypatch.setenv("SAFFRON_ALLOW_HOST_PROCESS", "rapportd")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", "lsof: no listing"),
    )
    with pytest.raises(runtime.CellRuntimeError, match="produced no listing"):
        preflight.host_probe_ports()


def test_the_probe_checks_the_ports_it_was_given(monkeypatch):
    """One enumeration per run: probing a second, freshly-taken list means the
    line the operator read is not the one that was checked."""
    seen: dict = {}

    def _run_ephemeral(image, command, **kwargs):
        seen["script"] = command[-1]
        return runtime.Completed(0, "", "")

    monkeypatch.setattr("saffron.cell.runtime.run_ephemeral", _run_ephemeral)

    def _boom():
        raise AssertionError("the probe re-enumerated instead of using its argument")

    monkeypatch.setattr("saffron.preflight.host_probe_ports", _boom)
    preflight.probe_host_bindings("img", "net", [4242])
    assert "ports=[4242]" in seen["script"]
    # And the connects are concurrent, or ~100 listeners exhaust the 300s cap.
    assert "ThreadPoolExecutor" in seen["script"]


def test_any_http_status_from_the_upstream_is_reachability(monkeypatch):
    """401 is the expected answer and it is a pass: what is established is the
    route, and no credential is being tested (DESIGN.md §5.1.1)."""
    seen = {}

    def fake(image, command, *, network=None, env=None, timeout_s=120, **kw):
        seen["env"] = env
        seen["network"] = network
        seen["command"] = command
        return runtime.Completed(0, "STATUS 401\n", "")

    monkeypatch.setattr(preflight.runtime, "run_ephemeral", fake)
    assert (
        preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")
        == "401"
    )
    # The command is asserted, not just the answer: a probe pointed at the wrong
    # host would pass every run and establish nothing.
    assert proxy.UPSTREAM_HOST in seen["command"][-1]
    assert "/v1/models" in seen["command"][-1]
    # Through the proxy, by IP: an internal network has no DNS to resolve a name.
    assert seen["env"]["HTTPS_PROXY"] == "http://10.88.0.2:3128"
    assert seen["network"] == "saffron-cells"


def test_a_proxy_that_cannot_reach_the_upstream_aborts_before_the_cell(monkeypatch):
    """The failure that shipped: squid answered, and answered 503. An abort
    here is `error` — the repo's code is not what is wrong."""
    monkeypatch.setattr(
        preflight.runtime,
        "run_ephemeral",
        # The measured shape: the probe ran, so there is a traceback, and its
        # last line is the diagnosis.
        lambda *a, **k: runtime.Completed(
            1,
            "",
            "Traceback (most recent call last):\n"
            '  File "<string>", line 3, in <module>\n'
            "urllib.error.URLError: <urlopen error tunnel failed>",
        ),
    )
    with pytest.raises(runtime.CellRuntimeError, match="could not reach"):
        preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")


def test_a_probe_that_printed_nothing_is_not_a_pass(monkeypatch):
    """Exit 0 with no STATUS line is a container that started and did not run
    the probe — the same shape as the vacuous pass Appendix H is about."""
    monkeypatch.setattr(
        preflight.runtime, "run_ephemeral", lambda *a, **k: runtime.Completed(0, "", "")
    )
    with pytest.raises(runtime.CellRuntimeError, match="did not run"):
        preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")


def test_the_abort_reports_the_exception_not_the_runtimes_progress_output(monkeypatch):
    """`container run` prints image-pull progress to stderr before the container
    says anything, so a head-truncated message reports the pull and not the
    failure — which is the one line an operator needs."""
    noise = "\n".join(
        [
            "[0/6] [0s]",
            "[1/6] Fetching image [0s]",
            "[6/6] Starting container [0s]",
            "Traceback (most recent call last):",
            '  File "<string>", line 3, in <module>',
            "urllib.error.URLError: <urlopen error timed out>",
        ]
    )
    monkeypatch.setattr(
        preflight.runtime,
        "run_ephemeral",
        lambda *a, **k: runtime.Completed(1, "", noise),
    )
    with pytest.raises(runtime.CellRuntimeError) as raised:
        preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")
    assert "urlopen error timed out" in str(raised.value)
    assert "Fetching image" not in str(raised.value)


def test_the_pass_token_is_anchored_because_it_is_inside_the_argv(monkeypatch):
    """`STATUS` is a literal in the script this sends, so a runtime echoing its
    own command back would read as a pass — Appendix H's vacuous pass, in the
    check written against it."""
    echoed = (
        "Usage: container run [<options>] <image>\n"
        "while applying: python -c import urllib.request as u\n"
        "    print('STATUS', u.urlopen('https://api.anthropic.com/v1/models'))\n"
    )
    assert "STATUS" in echoed  # the substring a weaker check would have accepted
    monkeypatch.setattr(
        preflight.runtime,
        "run_ephemeral",
        lambda *a, **k: runtime.Completed(0, echoed, ""),
    )
    with pytest.raises(runtime.CellRuntimeError, match="did not run"):
        preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")


def test_a_run_that_timed_out_is_a_probe_that_did_not_run(monkeypatch):
    """A wall timeout is the runtime hanging, not the route being dead, and the
    advice for the two differs. `probe_host_bindings` already draws this line."""
    monkeypatch.setattr(
        preflight.runtime,
        "run_ephemeral",
        lambda *a, **k: runtime.Completed(124, "STATUS 20", "", timed_out=True),
    )
    with pytest.raises(runtime.CellRuntimeError, match="did not run"):
        preflight.assert_proxy_reaches_upstream("img", "saffron-cells", "10.88.0.2")


def test_a_cell_is_not_made_to_proxy_its_own_loopback():
    """BACKLOG item 41. `proxy_env` set `NO_PROXY: ""`, so `urllib` routed
    everything through squid — `127.0.0.1` included, which squid denies
    because it allowlists only the upstream. A cell could not reach a server
    it had started itself, so the test below failed at baseline on every cell
    run (ten `TCP_DENIED/403` lines in one) and baseline subtraction hid it.

    The environment is built, not inherited: `getproxies_environment` gives
    lowercase `no_proxy` the last word, so `os.environ | proxy_env(...)`
    cannot override one and the test reads the developer's shell instead of
    the value under test. Measured — with `no_proxy=127.0.0.1,localhost` set
    ambiently this passed against the unfixed code, and with
    `no_proxy=example.com` it failed against the fixed one.

    The status is asserted, not just the exit code: `_UPSTREAM_PROBE` catches
    `HTTPError` and exits 0 on any answer, so `returncode == 0` would accept a
    `403 TCP_DENIED` from a real proxy as a pass. The skip below then guards
    only against a spurious *failure*, never a silent pass.
    """
    import os
    import socket
    import subprocess
    import sys
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    with socket.socket() as listening:
        if listening.connect_ex(("127.0.0.1", proxy.PROXY_PORT)) == 0:
            pytest.skip(f"something answers on 127.0.0.1:{proxy.PROXY_PORT}")

    class Unauthorized(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(401)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Unauthorized)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/models"
        done = subprocess.run(
            [sys.executable, "-c", preflight._UPSTREAM_PROBE.format(url=url)],
            capture_output=True,
            text=True,
            timeout=60,
            env={"PATH": os.environ["PATH"]} | proxy.proxy_env("127.0.0.1"),
        )
    finally:
        server.shutdown()
    assert done.returncode == 0, done.stderr
    status = preflight._STATUS.search(done.stdout)
    assert status is not None, done.stdout
    assert status.group(1) == "401"


def _stub_prepare(monkeypatch, *, exported: Path) -> None:
    """Every step `check_readiness` runs before "policy", stubbed to pass —
    so a test can fail exactly one later step without reaching git or the
    network for the earlier ones."""
    monkeypatch.setattr(preflight.git_mirror, "ensure_mirror", lambda repo, path: path)
    monkeypatch.setattr(
        preflight.package_phase,
        "real_remote",
        lambda repo: "https://github.com/o/r.git",
    )
    monkeypatch.setattr(preflight.package_phase, "github_slug", lambda url: "o/r")
    monkeypatch.setattr(
        preflight.package_phase,
        "fetch_default_branch",
        lambda mirror, url: ("main", "a" * 40),
    )
    monkeypatch.setattr(
        preflight.git_mirror,
        "export_saffron_dir",
        lambda mirror, sha, scratch: exported,
    )


@pytest.mark.parametrize(
    ("target", "boom", "step"),
    [
        ("ensure_mirror", preflight.git_mirror.GitError("fetch failed"), "mirror"),
        ("real_remote", preflight.package_phase.PackageError("no remote"), "origin"),
        (
            "github_slug",
            preflight.package_phase.PackageError("not a forge remote"),
            "origin",
        ),
        (
            "fetch_default_branch",
            preflight.package_phase.PackageError("no head"),
            "default_branch",
        ),
    ],
)
def test_a_failing_preparation_step_is_named_not_raised(
    monkeypatch, tmp_path, target, boom, step
):
    """§4.4 step 1 skips a repo that fails preflight rather than taking the
    batch down, so every one of these has to arrive as a named `Readiness`.
    Each of the four was caught by a branch no test drove: stubbing all of
    them to succeed, as every other test here does, leaves the `except` arms
    dead and deleting one changes nothing the suite can see."""
    exported = tmp_path / "export"
    (exported / ".saffron").mkdir(parents=True)
    _stub_prepare(monkeypatch, exported=exported)

    owner = (
        preflight.git_mirror if target == "ensure_mirror" else preflight.package_phase
    )

    def _raise(*_a, **_k):
        raise boom

    monkeypatch.setattr(owner, target, _raise)

    result = preflight.check_readiness(
        tmp_path / "repo",
        tmp_path / "mirror",
        tmp_path / "scratch",
        tmp_path / "home",
        token="tok",
        validate_token=lambda token: True,
    )

    assert result.ok is False
    assert result.step == step


def test_a_disk_check_that_cannot_run_is_named_not_raised(monkeypatch, tmp_path):
    """`disk_headroom_ok` raises rather than reading an unrunnable check as a
    pass — correct, and not this function's contract. Unguarded, that raise
    left `check_readiness` as a bare exception, which is the one failure a
    caller cannot skip a repo on."""
    exported = tmp_path / "export"
    (exported / ".saffron").mkdir(parents=True)
    _stub_prepare(monkeypatch, exported=exported)

    def _boom(_path):
        raise OSError("no such file or directory")

    monkeypatch.setattr(preflight.shutil, "disk_usage", _boom)

    result = preflight.check_readiness(
        tmp_path / "repo",
        tmp_path / "mirror",
        tmp_path / "scratch",
        tmp_path / "home",
        token="tok",
        validate_token=lambda token: True,
    )

    assert result.ok is False
    assert result.step == "disk"


def test_readiness_runs_its_checks_in_the_order_4_2_1_gives(monkeypatch, tmp_path):
    """§4.2.1: auth, mirror fetch, origin refusal, default-branch pin, policy
    validation, disk headroom — asserted on the order calls land in, and on
    the result naming what passed rather than a bare boolean."""
    order: list[str] = []

    def _mk(name, result):
        def _fn(*_a, **_k):
            order.append(name)
            return result

        return _fn

    exported = tmp_path / "exported"
    (exported / ".saffron").mkdir(parents=True)
    (exported / ".saffron" / "policy.yaml").write_text("gates: {}\n")

    monkeypatch.setattr(
        preflight.git_mirror, "ensure_mirror", _mk("mirror", tmp_path / "m")
    )
    monkeypatch.setattr(preflight.package_phase, "real_remote", _mk("real_remote", "u"))
    monkeypatch.setattr(preflight.package_phase, "github_slug", _mk("origin", "o/r"))
    monkeypatch.setattr(
        preflight.package_phase,
        "fetch_default_branch",
        _mk("default_branch", ("main", "a" * 40)),
    )
    monkeypatch.setattr(
        preflight.git_mirror, "export_saffron_dir", _mk("export", exported)
    )
    monkeypatch.setattr(preflight, "load_policy", _mk("policy", (object(), "sha")))
    monkeypatch.setattr(preflight, "disk_headroom_ok", _mk("disk", True))

    def _auth(token):
        order.append("auth")
        return True

    result = preflight.check_readiness(
        tmp_path / "repo",
        tmp_path / "mirror",
        tmp_path / "scratch",
        tmp_path / "home",
        token="tok",
        validate_token=_auth,
    )

    assert result.ok
    assert (
        order.index("auth")
        < order.index("mirror")
        < order.index("real_remote")
        < order.index("origin")
        < order.index("default_branch")
        < order.index("export")
        < order.index("policy")
        < order.index("disk")
    )


def test_a_policy_that_does_not_load_fails_readiness(monkeypatch, tmp_path):
    """The other half of §4.2.1's "plus two": a policy that declares a gate
    whose executable is missing fails readiness before the night starts,
    rather than being discovered by the first cell after an image build."""
    exported = tmp_path / "exported"
    (exported / ".saffron").mkdir(parents=True)
    (exported / ".saffron" / "policy.yaml").write_text("gates:\n  lint: {}\n")
    _stub_prepare(monkeypatch, exported=exported)

    result = preflight.check_readiness(
        tmp_path / "repo",
        tmp_path / "mirror",
        tmp_path / "scratch",
        tmp_path / "home",
        token="tok",
        validate_token=lambda token: True,
    )

    assert result.ok is False
    assert result.step == "policy"
    assert result.detail is not None and "lint" in result.detail


def test_a_present_but_invalid_token_fails_readiness(monkeypatch, tmp_path):
    """Presence alone is what the guard checks today; Appendix J measured the
    failure that hides behind it. The validity probe here is injected, so
    this never reaches the network."""

    def _unreached(*_a, **_k):
        raise AssertionError("readiness moved past an invalid token")

    monkeypatch.setattr(preflight.git_mirror, "ensure_mirror", _unreached)

    result = preflight.check_readiness(
        tmp_path / "repo",
        tmp_path / "mirror",
        tmp_path / "scratch",
        tmp_path / "home",
        token="sk-expired",
        validate_token=lambda token: False,
    )

    assert result.ok is False
    assert result.step == "auth"


def test_a_whitespace_token_fails_readiness(monkeypatch, tmp_path):
    """An empty or whitespace token fails, not merely an absent one — the
    distinction the existing presence check already makes with `strip()`."""

    def _unreached(_token):
        raise AssertionError("a validity probe ran against an empty token")

    result = preflight.check_readiness(
        tmp_path / "repo",
        tmp_path / "mirror",
        tmp_path / "scratch",
        tmp_path / "home",
        token="   ",
        validate_token=_unreached,
    )

    assert result.ok is False
    assert result.step == "auth"


def test_a_check_that_cannot_run_is_a_failure_not_a_pass(monkeypatch, tmp_path):
    """The rule `host_probe_ports` already follows, one check over: a
    headroom check that cannot even run must not read as a pass."""

    def _boom(_path):
        raise OSError("no such file or directory")

    monkeypatch.setattr(preflight.shutil, "disk_usage", _boom)

    with pytest.raises(RuntimeError, match="could not be checked"):
        preflight.disk_headroom_ok(tmp_path)


def test_insufficient_disk_headroom_fails_readiness(monkeypatch, tmp_path):
    """Checked on the filesystem holding the batch tree — the one holding the
    mirrors, worktrees and the runtime's own volumes — against the named
    constant, not against `/` and not skipped."""
    exported = tmp_path / "exported"
    exported.mkdir()
    _stub_prepare(monkeypatch, exported=exported)

    seen: dict[str, Path] = {}

    def _fake_usage(path):
        seen["path"] = Path(path)
        return types.SimpleNamespace(total=0, used=0, free=0)

    monkeypatch.setattr(preflight.shutil, "disk_usage", _fake_usage)
    home = tmp_path / "home"

    result = preflight.check_readiness(
        tmp_path / "repo",
        tmp_path / "mirror",
        tmp_path / "scratch",
        home,
        token="tok",
        validate_token=lambda token: True,
    )

    assert result.ok is False
    assert result.step == "disk"
    assert seen["path"] == home


def test_the_token_probes_default_request_shape_is_asserted_not_sent(monkeypatch):
    """With the probe injected everywhere else, the real one is exercised by
    no test — Appendix H's vacuous pass, in the check written against it.
    The URL and the header the default builds are asserted here without
    ever sending the request."""
    seen: dict[str, str] = {}
    headers: dict[str, str] = {}

    def _capture(request, timeout=None):
        seen["url"] = request.full_url
        headers.update(request.headers)
        raise urllib.error.URLError("not actually sent")

    monkeypatch.setattr(urllib.request, "urlopen", _capture)

    assert preflight.validate_claude_token("tok-123") is False
    assert seen["url"] == f"https://{proxy.UPSTREAM_HOST}/v1/models"
    assert headers["Authorization"] == "Bearer tok-123"


def test_the_probe_script_itself_answers_a_401(tmp_path):
    """The script, executed — not its output, fabricated. Every other test here
    asserts the pass *condition*; this one runs `_UPSTREAM_PROBE` against a real
    server so the `HTTPError` branch and `.status` are covered, which is the
    behaviour the section's "401 is a pass" claim rests on."""
    import subprocess
    import sys
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Unauthorized(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(401)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Unauthorized)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/v1/models"
        done = subprocess.run(
            [sys.executable, "-c", preflight._UPSTREAM_PROBE.format(url=url)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        server.shutdown()
    assert done.returncode == 0, done.stderr
    status = preflight._STATUS.search(done.stdout)
    assert status is not None, done.stdout
    assert status.group(1) == "401"
