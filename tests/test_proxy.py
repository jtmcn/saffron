from __future__ import annotations

import pytest

from saffron import preflight
from saffron.cell import proxy, runtime
from saffron.repos import image

NETWORK = "saffron-test-cells"


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
            [
                "python",
                "-c",
                "import urllib.request as u;"
                "u.urlopen('https://api.anthropic.com/v1/models', timeout=20)",
            ],
            network=network,
            env=env,
            timeout_s=60,
        )
        # 401 is a reachability success: the CONNECT tunnel opened and the API
        # answered. Only a proxy denial or a DNS failure raises URLError.
        assert "URLError" not in allowed.stderr, allowed.stderr

        denied = runtime.run_ephemeral(
            image.BASE_TAG,
            [
                "python",
                "-c",
                "import urllib.request as u;"
                "u.urlopen('https://example.com', timeout=20)",
            ],
            network=network,
            env=env,
            timeout_s=60,
        )
        assert denied.returncode != 0
    finally:
        proxy.stop_proxy()


@pytest.mark.cell
def test_a_cell_without_the_proxy_reaches_nothing(network):
    done = runtime.run_ephemeral(
        image.BASE_TAG,
        [
            "python",
            "-c",
            "import urllib.request as u;"
            "u.urlopen('https://api.anthropic.com', timeout=10)",
        ],
        network=network,
        timeout_s=60,
    )
    assert done.returncode != 0


@pytest.mark.cell
def test_no_host_service_answers_from_inside_a_cell(network):
    """N1 rests on this. Appendix G's spike found a 0.0.0.0-bound service
    reachable at the gateway and the LAN address; the countermeasure is a host
    binding choice, and this is what checks it."""
    reachable = preflight.probe_host_bindings(image.BASE_TAG, network)
    assert reachable == [], (
        f"a host service answered from inside a cell at {reachable}; "
        "bind it to 127.0.0.1"
    )
