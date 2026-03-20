"""
test_network.py -- Integration tests for the P2P network.

Starts real HTTP servers in daemon threads.

Run from the project root:
    python -m pytest tests/ -v
or:
    python tests/test_network.py
"""

import sys
import os
# Allow running directly: python tests/test_core.py from the project root.
if '' not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import json
import threading
import time
import urllib.request
import urllib.error


from kryptika.network.server import run_server
from kryptika.core.transaction import Wallet

BASE_PORT = 5100  # use a unique port range to avoid conflicts with running nodes


def _start_node(port: int) -> None:
    import gc
    db = f"test_node_{port}.db"
    gc.collect()
    try:
        if os.path.exists(db):
            os.remove(db)
    except OSError:
        pass
    threading.Thread(
        target=run_server,
        kwargs={"port": port, "difficulty": 2, "db_path": db},
        daemon=True,
    ).start()


def _get(url: str) -> dict:
    return json.loads(urllib.request.urlopen(url, timeout=3).read())


def _post(url: str, body: object, expect_error: bool = False) -> dict:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url,
        data    = data,
        headers = {"Content-Type": "application/json"},
        method  = "POST",
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=3).read())
    except urllib.error.HTTPError as e:
        if expect_error:
            return json.loads(e.read())
        raise


def _setup_nodes(port_a: int, port_b: int) -> None:
    """Start two nodes and register them as peers of each other."""
    _start_node(port_a)
    _start_node(port_b)
    time.sleep(0.5)
    _post(f"http://localhost:{port_a}/peers/add", {"address": f"localhost:{port_b}"})
    _post(f"http://localhost:{port_b}/peers/add", {"address": f"localhost:{port_a}"})


def test_chain_endpoint_returns_genesis():
    """GET /chain must return the genesis block on a fresh node."""
    port = BASE_PORT
    _start_node(port)
    time.sleep(0.3)
    chain = _get(f"http://localhost:{port}/chain")
    assert isinstance(chain, list)
    assert len(chain) == 1
    assert chain[0]["index"] == 0
    print("  [OK]  test_chain_endpoint_returns_genesis")


def test_wallet_new_returns_address():
    """GET /wallet/new must return a non-empty address string."""
    port = BASE_PORT + 1
    _start_node(port)
    time.sleep(0.3)
    r = _get(f"http://localhost:{port}/wallet/new")
    assert "address" in r
    assert len(r["address"]) > 0
    print("  [OK]  test_wallet_new_returns_address")


def test_mine_increases_height():
    """GET /mine?address=<addr> must increase the chain height by 1."""
    port = BASE_PORT + 2
    _start_node(port)
    time.sleep(0.3)
    wallet = _get(f"http://localhost:{port}/wallet/new")
    r      = _get(f"http://localhost:{port}/mine?address={wallet['address']}")
    assert r["index"] == 1
    chain = _get(f"http://localhost:{port}/chain")
    assert len(chain) == 2
    print("  [OK]  test_mine_increases_height")


def test_balance_after_mining():
    """GET /balance/<addr> must return the coinbase reward after mining."""
    port = BASE_PORT + 3
    _start_node(port)
    time.sleep(0.3)
    wallet = _get(f"http://localhost:{port}/wallet/new")
    _get(f"http://localhost:{port}/mine?address={wallet['address']}")
    bal = _get(f"http://localhost:{port}/balance/{wallet['address']}")
    assert bal["balance"] == 10.0
    print("  [OK]  test_balance_after_mining")


def test_broadcast_syncs_peer():
    """Mining on node A must automatically sync to node B via broadcast."""
    port_a, port_b = BASE_PORT + 4, BASE_PORT + 5
    _setup_nodes(port_a, port_b)
    wallet = _get(f"http://localhost:{port_a}/wallet/new")
    _get(f"http://localhost:{port_a}/mine?address={wallet['address']}")
    time.sleep(0.3)

    chain_a = _get(f"http://localhost:{port_a}/chain")
    chain_b = _get(f"http://localhost:{port_b}/chain")
    assert len(chain_a) == len(chain_b)
    assert chain_a[-1]["hash"] == chain_b[-1]["hash"]
    print("  [OK]  test_broadcast_syncs_peer")


def test_sync_adopts_longer_chain():
    """GET /peers/sync must adopt a longer valid chain from a peer."""
    port_a, port_b = BASE_PORT + 6, BASE_PORT + 7
    _setup_nodes(port_a, port_b)

    wallet = _get(f"http://localhost:{port_a}/wallet/new")
    _get(f"http://localhost:{port_a}/mine?address={wallet['address']}")
    _get(f"http://localhost:{port_a}/mine?address={wallet['address']}")
    time.sleep(0.3)

    r = _get(f"http://localhost:{port_b}/peers/sync")
    assert r["height"] >= 3
    print("  [OK]  test_sync_adopts_longer_chain")


def test_pending_transactions_empty_initially():
    """GET /transactions/pending must return 0 on a fresh node."""
    port = BASE_PORT + 8
    _start_node(port)
    time.sleep(0.3)
    r = _get(f"http://localhost:{port}/transactions/pending")
    assert r["count"] == 0
    assert r["transactions"] == []
    print("  [OK]  test_pending_transactions_empty_initially")


def test_add_peer_returns_peer_list():
    """POST /peers/add must return the updated peer list."""
    port = BASE_PORT + 9
    _start_node(port)
    time.sleep(0.3)
    r = _post(f"http://localhost:{port}/peers/add", {"address": "localhost:9999"})
    assert "localhost:9999" in r["peers"]
    print("  [OK]  test_add_peer_returns_peer_list")


def test_add_peer_missing_address_returns_400():
    """POST /peers/add with missing 'address' key must return 400."""
    port = BASE_PORT + 10
    _start_node(port)
    time.sleep(0.3)
    r = _post(f"http://localhost:{port}/peers/add",
              {"wrong_key": "x"}, expect_error=True)
    assert "error" in r
    print("  [OK]  test_add_peer_missing_address_returns_400")


def test_mine_without_address_returns_400():
    """GET /mine with no address param must return 400."""
    port = BASE_PORT + 11
    _start_node(port)
    time.sleep(0.3)
    try:
        _get(f"http://localhost:{port}/mine")
        assert False, "Should have raised HTTPError"
    except urllib.error.HTTPError as e:
        assert e.code == 400
    print("  [OK]  test_mine_without_address_returns_400")


def test_unknown_endpoint_returns_404():
    """Requesting an unknown endpoint must return 404."""
    port = BASE_PORT + 12
    _start_node(port)
    time.sleep(0.3)
    try:
        _get(f"http://localhost:{port}/nonexistent")
        assert False, "Should have raised HTTPError"
    except urllib.error.HTTPError as e:
        assert e.code == 404
    print("  [OK]  test_unknown_endpoint_returns_404")



def test_fake_coinbase_transaction_rejected():
    """POST /transactions/new with COINBASE sender must be rejected with 400."""
    port = BASE_PORT + 13
    _start_node(port)
    time.sleep(0.3)
    fake_tx = {
        "sender":    "COINBASE",
        "recipient": "someaddress",
        "amount":    999.0,
        "signature": "",
    }
    r = _post(f"http://localhost:{port}/transactions/new", fake_tx, expect_error=True)
    assert "error" in r
    print("  [OK]  test_fake_coinbase_transaction_rejected")


def test_concurrent_requests_during_mining():
    """Server must respond to /status while /mine is running (threading test).

    With a single-threaded server, /mine (Proof of Work) would block all other
    requests.  With ThreadingHTTPServer each request runs in its own thread,
    so /status should respond immediately even while mining is in progress.
    """
    port = BASE_PORT + 14
    _start_node(port)
    time.sleep(0.3)

    wallet = Wallet()

    # Fire /mine in a background thread (difficulty=2, should still take a moment)
    mine_done   = []
    mine_errors = []

    def do_mine():
        try:
            r = _get(f"http://localhost:{port}/mine?address={wallet.address}")
            mine_done.append(r)
        except Exception as e:
            mine_errors.append(str(e))

    t = threading.Thread(target=do_mine)
    t.start()

    # While mining runs, /status must still respond
    responded = False
    deadline  = time.time() + 5.0
    while time.time() < deadline:
        try:
            r = _get(f"http://localhost:{port}/status")
            if "height" in r:
                responded = True
                break
        except Exception:
            pass
        time.sleep(0.05)

    t.join(timeout=10)

    assert not mine_errors, f"Mine thread error: {mine_errors}"
    assert responded, "Server did not respond to /status while /mine was running"
    print("  [OK]  test_concurrent_requests_during_mining")


if __name__ == "__main__":
    print("\nRunning network tests...\n")
    test_chain_endpoint_returns_genesis()
    test_wallet_new_returns_address()
    test_mine_increases_height()
    test_balance_after_mining()
    test_broadcast_syncs_peer()
    test_sync_adopts_longer_chain()
    test_pending_transactions_empty_initially()
    test_add_peer_returns_peer_list()
    test_add_peer_missing_address_returns_400()
    test_mine_without_address_returns_400()
    test_unknown_endpoint_returns_404()
    test_fake_coinbase_transaction_rejected()
    test_concurrent_requests_during_mining()
    print("\nAll 13 network tests passed.\n")