"""
server.py — HTTP server for Kryptika.

Exposes the node's functionality as a simple JSON REST API.
Uses ThreadingHTTPServer so that long-running requests (like /mine
doing Proof of Work) do not block other endpoints.

CORS headers are included on every response so the API can be called
from a browser-based dashboard or developer tools.
"""

import json
import time
import socketserver
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from .node import Node
from ..core.transaction import Transaction, Wallet

_MAX_BODY_SIZE = 10 * 1024 * 1024   # 10 MB hard cap on incoming request bodies


class _Handler(BaseHTTPRequestHandler):
    node: Node
    start_time: float

    def log_message(self, format, *args):
        pass

    # ------------------------------------------------------------------ helpers

    def _send(self, status: int, body: object) -> None:
        try:
            payload = json.dumps(body, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > _MAX_BODY_SIZE:
                try:
                    self.rfile.read(min(length, 4096))
                except OSError:
                    pass
                self._send(413, {"error": f"Request body too large (max {_MAX_BODY_SIZE // (1024*1024)} MB)."})
                return None
            return json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, ValueError):
            return None

    def _path(self) -> str:
        return urlparse(self.path).path

    # ------------------------------------------------------------------ routing

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self._path()
        if path.startswith("/balance/"):
            self._balance(); return
        if path.startswith("/history/"):
            self._history(); return
        routes = {
            "/chain":                self._chain,
            "/status":               self._status,
            "/peers":                self._peers_list,
            "/peers/sync":           self._sync,
            "/mine":                 self._mine,
            "/transactions/pending": self._pending,
            "/wallet/new":           self._new_wallet,
        }
        fn = routes.get(path)
        if fn:
            fn()
        else:
            self._send(404, {"error": f"Unknown endpoint: {path}"})

    def do_POST(self):
        path = self._path()
        routes = {
            "/peers/add":            self._add_peer,
            "/peers/receive":        self._receive_chain,
            "/transactions/new":     self._new_transaction,
            "/transactions/receive": self._receive_transaction,
        }
        fn = routes.get(path)
        if fn:
            fn()
        else:
            self._send(404, {"error": f"Unknown endpoint: {path}"})

    # ------------------------------------------------------------------ GET

    def _chain(self):
        with self.node._lock:
            data = self.node.blockchain.to_list()
        self._send(200, data)

    def _status(self):
        with self.node._lock:
            bc    = self.node.blockchain
            peers = sorted(self.node.peers)
            mpool = len(self.node.mempool)
            last  = bc.last_block.hash[:16] + "..."
            h     = bc.height
            diff  = bc.difficulty
        self._send(200, {
            "status":      "ok",
            "height":      h,
            "difficulty":  diff,
            "peers":       peers,
            "mempool":     mpool,
            "uptime_secs": round(time.time() - self.start_time, 1),
            "last_block":  last,
        })

    def _peers_list(self):
        with self.node._lock:
            peers = sorted(self.node.peers)
        self._send(200, {"peers": peers})

    def _sync(self):
        replaced = self.node.sync_with_peers()
        with self.node._lock:
            height = self.node.blockchain.height
        self._send(200, {
            "message":  "Chain replaced." if replaced else "Already up to date.",
            "replaced": replaced,
            "height":   height,
        })

    def _mine(self):
        address = parse_qs(urlparse(self.path).query).get("address", [None])[0]
        if not address:
            self._send(400, {"error": "Query param 'address' is required."}); return
        ok, reason = self.node.mine(address)
        if not ok:
            self._send(400, {"error": reason}); return
        with self.node._lock:
            block    = self.node.blockchain.last_block
            coinbase = block.transactions[0]
        self._send(200, {
            "message":      "Block mined and broadcast.",
            "index":        block.index,
            "transactions": len(block.transactions),
            "nonce":        block.nonce,
            "hash":         block.hash,
            "miner_reward": coinbase.amount,
        })

    def _balance(self):
        address = self._path()[len("/balance/"):]
        if not address:
            self._send(400, {"error": "Address is required."}); return
        with self.node._lock:
            balance = self.node.blockchain.get_balance(address)
        self._send(200, {"address": address, "balance": balance})

    def _history(self):
        address = self._path()[len("/history/"):]
        if not address:
            self._send(400, {"error": "Address is required."}); return
        with self.node._lock:
            history = self.node.blockchain.get_history(address)
        self._send(200, {"address": address, "count": len(history), "history": history})

    def _pending(self):
        with self.node._lock:
            txs = [tx.to_dict() for tx in self.node.mempool]
        self._send(200, {"count": len(txs), "transactions": txs})

    def _new_wallet(self):
        wallet = Wallet()
        self._send(200, {
            "address": wallet.address,
            "warning": "Private key is not stored. Use wallet_cli.py to manage wallets.",
        })

    # ------------------------------------------------------------------ POST

    def _add_peer(self):
        body = self._read_json()
        if body is None or "address" not in body:
            self._send(400, {"error": "Body must contain 'address'."}); return
        self.node.add_peer(body["address"])
        with self.node._lock:
            peers = sorted(self.node.peers)
        self._send(200, {"message": "Peer added.", "peers": peers})

    def _receive_chain(self):
        body = self._read_json()
        if not isinstance(body, list):
            self._send(400, {"error": "Body must be a JSON array."}); return
        replaced = self.node.receive_chain(body)
        with self.node._lock:
            height = self.node.blockchain.height
        self._send(200, {
            "message":  "Chain replaced." if replaced else "Chain kept (not longer).",
            "replaced": replaced,
            "height":   height,
        })

    def _new_transaction(self):
        body = self._read_json()
        if body is None:
            self._send(400, {"error": "Invalid or missing JSON body."}); return
        try:
            tx = Transaction.from_dict(body)
        except (KeyError, ValueError) as exc:
            self._send(400, {"error": str(exc)}); return
        ok, reason = self.node.add_transaction(tx)
        if not ok:
            self._send(400, {"error": reason}); return
        self.node.broadcast_transaction(tx)
        self._send(201, {
            "message":   "Transaction added to mempool.",
            "tx_id":     tx.tx_id,
            "recipient": tx.recipient,
            "amount":    tx.amount,
            "fee":       tx.fee,
        })

    def _receive_transaction(self):
        body = self._read_json()
        if body is None:
            self._send(400, {"error": "Invalid or missing JSON body."}); return
        try:
            tx = Transaction.from_dict(body)
        except (KeyError, ValueError) as exc:
            self._send(400, {"error": str(exc)}); return
        self.node.add_transaction(tx)
        self._send(200, {"message": "Transaction received."})


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class _ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """HTTP server that handles each request in a dedicated thread."""
    daemon_threads = True


def run_server(port: int = 5000, difficulty: int = 3, db_path: str = "chain.db") -> None:
    node       = Node(difficulty=difficulty, db_path=db_path)
    start_time = time.time()

    class Handler(_Handler):
        pass

    Handler.node       = node
    Handler.start_time = start_time

    server = _ThreadingHTTPServer(("", port), Handler)

    W = 49   # inner width
    bar  = "\u2500" * W
    tl, tr, bl, br = "\u250C", "\u2510", "\u2514", "\u2518"
    side = "\u2502"
    tee_l, tee_r = "\u251C", "\u2524"

    def row(text=""):
        pad = W - len(text) - 2
        return f"  {side} {text}{' ' * pad} {side}"

    print(f"\n  {tl}{bar}{tr}")
    print(row())
    print(row("  Kryptika Node"))
    print(row())
    print(f"  {tee_l}{bar}{tee_r}")
    print(row(f"  Port       : {port}"))
    print(row(f"  Difficulty : {difficulty}"))
    print(row(f"  Database   : {db_path}"))
    print(f"  {tee_l}{bar}{tee_r}")
    print(row(f"  GET  /chain  /status  /peers  /peers/sync"))
    print(row(f"  GET  /mine?address=<addr>"))
    print(row(f"  GET  /balance/<addr>  /history/<addr>"))
    print(row(f"  GET  /transactions/pending  /wallet/new"))
    print(row(f"  POST /peers/add  /peers/receive"))
    print(row(f"  POST /transactions/new  /transactions/receive"))
    print(f"  {bl}{bar}{br}")
    print(f"  Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n  Node on port {port} stopped.")
    finally:
        server.server_close()


def main() -> None:
    """Entry point for `kryptika-node` CLI and run_node.py."""
    import sys

    def _int(val: str, name: str) -> int:
        try:
            return int(val)
        except ValueError:
            print(f"Error: {name} must be an integer, got '{val}'.")
            sys.exit(1)

    port       = _int(sys.argv[1], "port")       if len(sys.argv) > 1 else 5000
    difficulty = _int(sys.argv[2], "difficulty") if len(sys.argv) > 2 else 3
    db_path    = f"chain_{port}.db"
    run_server(port=port, difficulty=difficulty, db_path=db_path)
