from __future__ import annotations

import socket
from pathlib import Path

import pytest

from saffron import preflight
from saffron.cell import proxy, runtime
from saffron.repos import image

NETWORK = "saffron-test-cells"


def reach(url: str) -> list[str]:
    """Print STATUS on any HTTP answer, so a container that never started is
    not mistaken for a successful fetch."""
    return [
        "python",
        "-c",
        "import urllib.request as u\n"
        "try:\n"
        f"    print('STATUS', u.urlopen({url!r}, timeout=20).status)\n"
        "except u.HTTPError as e:\n"
        "    print('STATUS', e.code)\n",
    ]


@pytest.fixture
def network():
    runtime.remove_network(NETWORK)
    runtime.create_network(NETWORK)
    yield NETWORK
    runtime.remove_network(NETWORK)


@pytest.mark.cell
def test_the_proxy_allows_anthropic_and_denies_everything_else(network):
    proxy_ip = proxy.start_proxy(network)
    try:
        env = {"HTTPS_PROXY": f"http://{proxy_ip}:{proxy.PROXY_PORT}"}
        allowed = runtime.run_ephemeral(
            image.BASE_TAG,
            reach("https://api.anthropic.com/v1/models"),
            network=network,
            env=env,
            timeout_s=60,
        )
        # 401 is a reachability success: the CONNECT tunnel opened and the API
        # answered. Only a proxy denial or a DNS failure raises URLError.
        assert "STATUS" in allowed.stdout, allowed.stderr

        denied = runtime.run_ephemeral(
            image.BASE_TAG,
            reach("https://example.com"),
            network=network,
            env=env,
            timeout_s=60,
        )
        # URLError, not merely nonzero: the container ran and the proxy refused
        # it, rather than the container failing to start at all.
        assert denied.returncode != 0
        assert "URLError" in denied.stderr, denied.stderr

        # Read against a real log, holding a real tunnel, a real denial and
        # squid's own startup chatter: the parser's quiet half, which no
        # hand-written fixture can establish.
        assert proxy.failed_egress() == [], "a working proxy reported a failure"
        assert len(proxy.denied_egress()) == 1
    finally:
        proxy.stop_proxy()


@pytest.mark.cell
def test_a_cell_without_the_proxy_reaches_nothing(network):
    done = runtime.run_ephemeral(
        image.BASE_TAG,
        reach("https://api.anthropic.com"),
        network=network,
        timeout_s=60,
    )
    assert done.returncode != 0
    assert "URLError" in done.stderr, done.stderr


@pytest.mark.cell
def test_no_host_service_answers_from_inside_a_cell(network):
    """N1 rests on this. Appendix G's spike found a 0.0.0.0-bound service
    reachable at the gateway and the LAN address; the countermeasure is a host
    binding choice, and this is what checks it.

    The ports come from the host's own listener table, so this test is a claim
    about the machine it runs on, not about seven remembered ports. A macOS
    default — Remote Management on 3283, AirPlay Receiver on 5000/7000,
    rapportd on 49152 — fails it, and correctly: those answer from inside a
    cell.

    `SAFFRON_ALLOW_HOST_PROCESS=rapportd` is the accepted risk this machine
    runs with (Appendix G). Without it this test fails here, which is the
    point: the exception is per-invocation and never a default."""
    reachable = preflight.probe_host_bindings(image.BASE_TAG, network)
    assert reachable == [], (
        f"a host service answered from inside a cell at {reachable}; "
        "bind it to 127.0.0.1, or turn it off"
    )


@pytest.mark.cell
def test_the_probe_finds_a_host_service_that_is_actually_there(network):
    """The positive half, and the one the suite was missing: an empty result is
    the passing answer, so a probe that silently covers nothing reads exactly
    like a machine that is clean.

    A real listener is bound on 0.0.0.0 and the probe is pointed at its port.
    The proxy is up first, as it now is in production (`session.py`), because
    that is the topology the probe has to work in on this runtime."""
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 0))
    server.listen(8)
    port = server.getsockname()[1]
    proxy.start_proxy(network)
    try:
        reachable = preflight.probe_host_bindings(image.BASE_TAG, network, [port])
    finally:
        proxy.stop_proxy()
        server.close()
    assert reachable, (
        f"a host service on 0.0.0.0:{port} was not seen from inside a cell — "
        "the probe covers nothing, which is not a probe that passed"
    )
    assert all(hit.endswith(f":{port}") for hit in reachable), reachable


@pytest.mark.cell
def test_preflight_confirms_the_real_proxy_reaches_the_upstream(network):
    """The assertion against a real proxy, started the way production starts
    one. This is the check that would have ended the 2026-08-28 run in seconds
    (DESIGN.md §5.1.1)."""
    proxy_ip = proxy.start_proxy(network)
    try:
        preflight.assert_proxy_reaches_upstream(image.BASE_TAG, network, proxy_ip)
    finally:
        proxy.stop_proxy()


@pytest.mark.cell
def test_preflight_fails_closed_when_nothing_is_listening(network):
    """The positive half of the assertion itself: a probe that cannot tell a
    reachable upstream from an unreachable one passes every run and is worth
    nothing. No proxy is started, so the address answers nothing."""
    with pytest.raises(runtime.CellRuntimeError, match="could not reach"):
        preflight.assert_proxy_reaches_upstream(
            image.BASE_TAG, network, "10.88.0.253", timeout_s=120
        )


def test_only_the_denials_are_reported_and_only_before_teardown(monkeypatch):
    """A denied CONNECT is the one proxy event an operator has to see: the
    allowlist is a hostname list, and a missing host reads as an API error."""
    log = "\n".join(
        [
            "1755800000.1 12 10.88.0.3 TCP_TUNNEL/200 5 CONNECT api.anthropic.com:443",
            "1755800001.2 0 10.88.0.3 TCP_DENIED/403 4 CONNECT platform.claude.com:443",
            "1755800002.3 0 10.88.0.3 TCP_DENIED/403 4 CONNECT pypi.org:443",
        ]
    )
    monkeypatch.setattr(
        proxy.runtime, "call", lambda *a, **k: runtime.Completed(0, log, "")
    )
    denied = proxy.denied_egress()
    assert len(denied) == 2
    assert "platform.claude.com:443" in denied[0]
    assert not any("TCP_TUNNEL" in line for line in denied)


def test_a_tunnel_the_allowlist_permitted_but_squid_could_not_open_is_reported(
    monkeypatch,
):
    """The failure that shipped, verbatim from
    `docs/evidence/2026-08-28-attach-order-takes-the-proxys-route.md`: an allowed
    CONNECT squid could not complete, which reaches the operator as the same
    unexplained API error a denial would."""
    log = "\n".join(
        [
            "1787975974.588     17 10.88.0.3 TCP_TUNNEL/200 39 CONNECT api.anthropic.com:443 - HIER_DIRECT/160.79.104.10 -",
            "1787975617.589  35022 10.88.0.4 TCP_TUNNEL/503 0 CONNECT api.anthropic.com:443 - HIER_NONE/- -",
            "1787975454.753      0 10.88.0.5 TCP_DENIED/403 3370 CONNECT pypi.org:443 - HIER_NONE/- text/html",
        ]
    )
    monkeypatch.setattr(
        proxy.runtime, "call", lambda *a, **k: runtime.Completed(0, log, "")
    )
    failed = proxy.failed_egress()
    assert len(failed) == 1
    assert "TCP_TUNNEL/503" in failed[0]
    # The denial is the other report's job, and the answered tunnel is nobody's.
    assert not any("TCP_DENIED" in line for line in failed)
    assert not any("/200" in line for line in failed)


# The column is field 3 of squid's default logformat. Every other field is a
# candidate for a stray `WORD/NNN` — the hierarchy peer, and the request URL,
# which the cell chooses.
_ROWS = [
    (
        "the outage's own row",
        "1787975617.589 35022 10.88.0.4 TCP_TUNNEL/503 0 CONNECT api.anthropic.com:443 - HIER_NONE/- -",
        True,
    ),
    (
        "an answered tunnel",
        "1787975974.588 17 10.88.0.3 TCP_TUNNEL/200 39 CONNECT api.anthropic.com:443 - HIER_DIRECT/160.79.104.10 -",
        False,
    ),
    (
        "a denial",
        "1787975454.753 0 10.88.0.5 TCP_DENIED/403 3370 CONNECT pypi.org:443 - HIER_NONE/- text/html",
        False,
    ),
    # squid.conf allows plain HTTP to the allowlisted host, so a 4xx is the
    # upstream answering: the proxy worked, and saying otherwise sends the
    # operator to the network. 429 is the one CLAUDE.md singles out.
    (
        "the upstream said 404",
        "1755800003.400 30 10.88.0.3 TCP_MISS/404 512 GET http://api.anthropic.com/v1/nope - HIER_DIRECT/160.79.104.10 text/html",
        False,
    ),
    (
        "the upstream said 429",
        "1755800004.500 30 10.88.0.3 TCP_MISS/429 900 GET http://api.anthropic.com/v1/messages - HIER_DIRECT/160.79.104.10 application/json",
        False,
    ),
    # squid wrote no reply at all, which is a route failure by any reading.
    (
        "squid answered nothing",
        "1755800009.000 20 10.88.0.3 TCP_TUNNEL/000 0 CONNECT api.anthropic.com:443 - HIER_NONE/- -",
        True,
    ),
    # The cell picks the URL. Scanning fields for a slash let it hide this.
    (
        "a URL naming TCP_DENIED",
        "1755800008.900 10 10.88.0.3 TCP_MISS/503 4000 GET http://api.anthropic.com/TCP_DENIED - HIER_NONE/- text/html",
        True,
    ),
    (
        "squid's own cache.log",
        "2026/08/29 10:00:00| ERROR: Connection to 160.79.104.10 failed; peer said HTTP/503",
        False,
    ),
    ("a truncated row", "1755800009.000 20 10.88.0.3", False),
]


@pytest.mark.parametrize("name,line,expected", _ROWS, ids=[r[0] for r in _ROWS])
def test_the_status_column_is_read_by_position_not_by_hunting_for_a_slash(
    name, line, expected
):
    assert proxy._is_failure(line) is expected


def test_a_cell_chosen_url_cannot_forge_a_denial(monkeypatch):
    """`denied_egress` reads the same column. A cell fetching `/TCP_DENIED`
    otherwise puts a denial that never happened in the operator's teardown."""
    log = "1755800008.900 10 10.88.0.3 TCP_MISS/503 4000 GET http://api.anthropic.com/TCP_DENIED - HIER_NONE/- text/html"
    monkeypatch.setattr(
        proxy.runtime, "call", lambda *a, **k: runtime.Completed(0, log, "")
    )
    assert proxy.denied_egress() == []
    assert len(proxy.failed_egress()) == 1


def test_both_reports_are_capped_so_one_outage_cannot_fill_the_teardown(monkeypatch):
    """The measured log held twenty near-identical rows and a real one holds
    hundreds; teardown is a handful of lines, not a transcript."""
    row = "1787975617.589 35022 10.88.0.4 TCP_TUNNEL/503 0 CONNECT api.anthropic.com:443 - HIER_NONE/- -"
    denial = "1787975454.753 0 10.88.0.5 TCP_DENIED/403 3370 CONNECT pypi.org:443 - HIER_NONE/- text/html"
    log = "\n".join([row] * 50 + [denial] * 50)
    monkeypatch.setattr(
        proxy.runtime, "call", lambda *a, **k: runtime.Completed(0, log, "")
    )
    assert len(proxy.failed_egress()) == 10
    assert len(proxy.denied_egress()) == 10
    assert len(proxy.failed_egress(limit=3)) == 3


def test_a_proxy_that_is_already_gone_reports_nothing_rather_than_its_error(
    monkeypatch,
):
    """`container logs` on a removed container exits nonzero with a message that
    is not a log. Both readers run from teardown's `finally`."""
    monkeypatch.setattr(
        proxy.runtime,
        "call",
        lambda *a, **k: runtime.Completed(
            1, "", "Error: failed to get logs (notFound)"
        ),
    )
    assert proxy.failed_egress() == []
    assert proxy.denied_egress() == []


def test_a_proxy_that_never_answered_reports_nothing_rather_than_raising(
    monkeypatch,
):
    """`failed_egress` runs from the same `finally` as `denied_egress`."""

    def boom(*a, **k):
        raise runtime.CellRuntimeError("the runtime binary is gone")

    monkeypatch.setattr(proxy.runtime, "call", boom)
    assert proxy.failed_egress() == []


def test_the_allowlisted_host_and_the_squid_acl_agree():
    """`UPSTREAM_HOST` is what preflight probes and `squid.conf` is what admits
    it. Two copies of one decision, so the drift is worth a test: probing a host
    the ACL does not name would fail every run, and probing one it no longer
    names would pass while the agent is refused."""
    acl = Path("images/squid.conf").read_text()
    assert f"acl allowed_hosts dstdomain {proxy.UPSTREAM_HOST}" in acl, acl
