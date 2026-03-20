"""
node.py — Node for Kryptika.

The Node is the brain of a Kryptika instance.  It owns:
  - The blockchain (in-memory + persisted to SQLite)
  - The mempool  (pending unconfirmed transactions)
  - The peer set (addresses of other nodes)

Thread safety
-------------
All state mutations are protected by a single RLock (_lock).
Proof-of-Work computation in mine() runs OUTSIDE the lock so that
read endpoints (/status, /balance, etc.) remain responsive during mining.
Only the final chain-append + save step is locked.

Broadcast calls (broadcast_chain, broadcast_transaction) always take a
snapshot of self.peers before doing I/O so that a concurrent add_peer
cannot cause RuntimeError mid-iteration.
"""

import json
import threading
import urllib.request
import urllib.error
from ..core.blockchain import Blockchain
from ..core.transaction import Transaction
from ..storage.storage import SQLiteStorage


class Node:

    def __init__(self, difficulty: int = 3, db_path: str = "chain.db"):
        self._lock   = threading.RLock()
        self.storage = SQLiteStorage(db_path)

        self.mempool: list[Transaction] = []
        self.peers:   set[str]          = set()
        self._confirmed_ids: set[str]   = set()

        try:
            self.blockchain = self.storage.load(difficulty=difficulty)
            self._rebuild_confirmed_ids()
            print(f"[Node] Resumed  {db_path}  (height={self.blockchain.height})")
        except ValueError:
            self.blockchain = Blockchain(difficulty=difficulty)
            self._rebuild_confirmed_ids()
            try:
                self.storage.save(self.blockchain)
                print(f"[Node] Started  {db_path}  (genesis saved)")
            except Exception as exc:
                print(f"[Node] Warning: could not save genesis: {exc}")
        except Exception as exc:
            print(f"[Node] Could not load {db_path}: {exc} — starting fresh.")
            self.blockchain = Blockchain(difficulty=difficulty)
            self._rebuild_confirmed_ids()
            try:
                self.storage.save(self.blockchain)
            except Exception:
                pass

    # ------------------------------------------------------------------ cache

    def _rebuild_confirmed_ids(self) -> None:
        """Rebuild the confirmed-tx-id set from the current chain (full scan)."""
        self._confirmed_ids = {
            tx.tx_id
            for block in self.blockchain.chain
            for tx in block.transactions
            if tx.tx_id
        }

    def _index_block(self, block) -> None:
        """Incrementally add one block's tx_ids to the confirmed-id cache."""
        for tx in block.transactions:
            if tx.tx_id:
                self._confirmed_ids.add(tx.tx_id)

    # ------------------------------------------------------------------ disk

    def _save(self) -> None:
        """Persist the current blockchain.  Raises on failure."""
        self.storage.save(self.blockchain)   # propagate exceptions to caller

    # ------------------------------------------------------------------ mempool

    def _pending_spend(self, sender: str) -> float:
        """Total (amount + fee) already queued in the mempool for *sender*."""
        return sum(
            tx.amount + tx.fee
            for tx in self.mempool
            if tx.sender == sender
        )

    def _load_mempool_from_disk(self) -> None:
        """Reload pending transactions from the mempool table on startup."""
        from ..core.transaction import Transaction as _Tx
        try:
            rows = self.storage.load_mempool()
            restored = []
            for row in rows:
                # Skip any that were confirmed while the node was offline
                if row.get("tx_id") and row["tx_id"] in self._confirmed_ids:
                    continue
                try:
                    restored.append(_Tx.from_dict(row))
                except Exception:
                    pass   # malformed row -- skip silently
            self.mempool = restored
        except Exception as exc:
            print(f"[Node] Warning: could not restore mempool: {exc}")

    def _flush_mempool_to_disk(self) -> None:
        """Persist the current mempool to disk (best-effort)."""
        try:
            self.storage.save_mempool(self.mempool)
        except Exception as exc:
            print(f"[Node] Warning: could not save mempool: {exc}")

    def _prune_mempool(self) -> None:
        """Drop any mempool txs that are now confirmed on the current chain."""
        self.mempool = [
            tx for tx in self.mempool
            if not (tx.tx_id and tx.tx_id in self._confirmed_ids)
        ]

    # ------------------------------------------------------------------ peers

    def add_peer(self, address: str) -> None:
        with self._lock:
            self.peers.add(address)

    # ------------------------------------------------------------------ transactions

    def add_transaction(self, tx: Transaction) -> tuple[bool, str]:
        """Validate and enqueue a transaction.

        Checks (in order):
        1. Reject COINBASE_SENDER.
        2. Verify ECDSA signature.
        3. Reject duplicate tx_id (mempool or confirmed-chain cache).
        4. Effective-balance check: confirmed − already_pending ≥ amount + fee.
        """
        with self._lock:
            if tx.sender == Transaction.COINBASE_SENDER:
                return False, "Transactions with COINBASE sender are not accepted."

            valid, reason = tx.is_valid()
            if not valid:
                return False, reason

            if tx.tx_id:
                if any(t.tx_id == tx.tx_id for t in self.mempool if t.tx_id):
                    return False, "Duplicate: transaction already in mempool."
                if tx.tx_id in self._confirmed_ids:
                    return False, "Duplicate: transaction already confirmed on chain."

            confirmed  = self.blockchain.get_balance(tx.sender)
            pending    = self._pending_spend(tx.sender)
            effective  = round(confirmed - pending, 8)
            total_cost = round(tx.amount + tx.fee, 8)

            if effective < total_cost:
                return False, (
                    f"Insufficient funds: "
                    f"confirmed={confirmed:.8f}, "
                    f"pending={pending:.8f}, "
                    f"effective={effective:.8f}, "
                    f"needed={total_cost:.8f}."
                )

            self.mempool.append(tx)
            self._flush_mempool_to_disk()
            return True, ""

    def broadcast_transaction(self, tx: Transaction) -> None:
        with self._lock:
            peers = set(self.peers)
        data = json.dumps(tx.to_dict()).encode()
        for peer in peers:
            try:
                req = urllib.request.Request(
                    f"http://{peer}/transactions/receive",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=3)
            except (urllib.error.URLError, OSError):
                pass

    # ------------------------------------------------------------------ mining

    def mine(self, miner_address: str) -> tuple[bool, str]:
        """Mine the current mempool into a new block.

        Proof of Work runs OUTSIDE the lock so the node stays responsive.
        The lock is only held for the final chain-append and disk save.

        Steps:
        1. Snapshot the mempool (outside lock).
        2. Validate txs and run PoW -- this can take time (outside lock).
        3. Acquire lock: check the chain hasn't moved on since we started.
        4. Append the block, save to disk, update caches, clear mempool.
        5. Broadcast the new chain to all peers (outside lock).
        """
        # Step 1 — snapshot mempool
        with self._lock:
            mempool_snapshot = list(self.mempool)
            prev_height      = self.blockchain.height

        # Step 2 — validate + PoW (no lock held — node stays responsive)
        try:
            new_block = self.blockchain._build_candidate_block(
                mempool_snapshot, miner_address
            )
        except ValueError as exc:
            return False, str(exc)

        # Step 3 & 4 — lock, check, append, save
        with self._lock:
            # If the chain grew while we were mining (peer broadcast a longer
            # chain), discard this block — it would be stale.
            if self.blockchain.height != prev_height:
                return False, (
                    "Chain height changed during mining "
                    "(a peer broadcast a longer chain). Please try again."
                )

            self.blockchain.chain.append(new_block)

            try:
                self._save()
            except Exception as exc:
                self.blockchain.chain.pop()   # roll back
                return False, f"Failed to save block to disk: {exc}"

            self._index_block(new_block)

            # Remove mined txs from mempool and persist the updated mempool
            mined_ids = {tx.tx_id for tx in mempool_snapshot if tx.tx_id}
            self.mempool = [t for t in self.mempool if t.tx_id not in mined_ids]
            self._flush_mempool_to_disk()

        # Step 5 — broadcast (outside lock)
        self.broadcast_chain()
        return True, ""

    # ------------------------------------------------------------------ sync

    def _is_better_chain(self, data: list[dict]) -> "Blockchain | None":
        """Return a validated candidate chain if it is longer than ours."""
        candidate = Blockchain.from_list(data, difficulty=self.blockchain.difficulty)
        valid, _  = candidate.is_valid()
        if valid and candidate.height > self.blockchain.height:
            return candidate
        return None

    def broadcast_chain(self) -> None:
        with self._lock:
            data  = json.dumps(self.blockchain.to_list()).encode()
            peers = set(self.peers)
        for peer in peers:
            try:
                req = urllib.request.Request(
                    f"http://{peer}/peers/receive",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=3)
            except (urllib.error.URLError, OSError):
                pass

    def sync_with_peers(self) -> bool:
        """Pull chains from all peers, adopt the longest valid one,
        and absorb any pending transactions from peer mempools.

        Chain sync: replaces our chain only if a peer has a strictly
        longer valid chain (height > ours).

        Mempool sync: adds any valid peer transactions we don't already
        have, so pending txs propagate even when chains are equal height.
        """
        with self._lock:
            peers = set(self.peers)

        best: "Blockchain | None" = None
        chain_replaced = False

        # ── Step 1: find the best chain across all peers ──
        for peer in peers:
            try:
                response = urllib.request.urlopen(
                    f"http://{peer}/chain", timeout=3)
                data = json.loads(response.read())
                with self._lock:
                    candidate = self._is_better_chain(data)
                    if candidate and (best is None or
                                      candidate.height > best.height):
                        best = candidate
            except (urllib.error.URLError, OSError):
                pass

        if best is not None:
            with self._lock:
                self.blockchain = best
                self._rebuild_confirmed_ids()
                self._prune_mempool()
                self._flush_mempool_to_disk()
                chain_replaced = True
                try:
                    self._save()
                except Exception as exc:
                    print(f"[Node] Warning: sync succeeded but save failed: {exc}")

        # ── Step 2: absorb pending txs from all peers ──
        for peer in peers:
            try:
                response = urllib.request.urlopen(
                    f"http://{peer}/transactions/pending", timeout=3)
                data = json.loads(response.read())
                for tx_dict in data.get("transactions", []):
                    from ..core.transaction import Transaction as _Tx
                    try:
                        tx = _Tx.from_dict(tx_dict)
                        self.add_transaction(tx)   # validates + dedupes
                    except Exception:
                        pass
            except (urllib.error.URLError, OSError):
                pass

        return chain_replaced

    def receive_chain(self, data: list[dict]) -> bool:
        """Accept a chain pushed by a peer. Replace ours if it is longer."""
        with self._lock:
            candidate = self._is_better_chain(data)
            if not candidate:
                return False
            self.blockchain = candidate
            self._rebuild_confirmed_ids()
            self._prune_mempool()
            self._flush_mempool_to_disk()
            try:
                self._save()
            except Exception as exc:
                print(f"[Node] Warning: chain accepted but save failed: {exc}")
            return True
