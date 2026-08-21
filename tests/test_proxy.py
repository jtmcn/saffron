from __future__ import annotations

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
