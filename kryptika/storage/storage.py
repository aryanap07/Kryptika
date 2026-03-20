"""
storage.py — SQLite persistence for Kryptika.

Schema
------
  blocks        (block_index PK, timestamp, prev_hash, nonce, hash)
  transactions  (id AUTOINCREMENT, block_index FK, sender, recipient,
                 amount, fee, signature, note, public_key, tx_id)
  wallets       (address PK, name)

All writes use an explicit BEGIN / COMMIT / ROLLBACK transaction so that
a crash mid-save leaves the database in its previous valid state rather
than a partially-written, corrupt state.
"""

import sqlite3
from pathlib import Path
from ..core.blockchain import Blockchain
from ..core.transaction import Wallet


class SQLiteStorage:

    def __init__(self, filepath: str = "chain.db"):
        self.filepath = Path(filepath)
        self._init_db()

    # ------------------------------------------------------------------ schema

    def _init_db(self) -> None:
        with sqlite3.connect(self.filepath) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS blocks (
                    block_index  INTEGER PRIMARY KEY,
                    timestamp    REAL    NOT NULL,
                    prev_hash    TEXT    NOT NULL,
                    nonce        INTEGER NOT NULL,
                    hash         TEXT    NOT NULL
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    block_index  INTEGER NOT NULL REFERENCES blocks(block_index),
                    sender       TEXT    NOT NULL,
                    recipient    TEXT    NOT NULL,
                    amount       REAL    NOT NULL,
                    fee          REAL    NOT NULL DEFAULT 0.0,
                    signature    TEXT    NOT NULL DEFAULT '',
                    note         TEXT    NOT NULL DEFAULT '',
                    public_key   TEXT    NOT NULL DEFAULT '',
                    tx_id        TEXT    NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS wallets (
                    address  TEXT PRIMARY KEY,
                    name     TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS mempool (
                    tx_id      TEXT PRIMARY KEY,
                    sender     TEXT NOT NULL,
                    recipient  TEXT NOT NULL,
                    amount     REAL NOT NULL,
                    fee        REAL NOT NULL DEFAULT 0.0,
                    signature  TEXT NOT NULL DEFAULT '',
                    note       TEXT NOT NULL DEFAULT '',
                    public_key TEXT NOT NULL DEFAULT ''
                );
            """)

            # Migrate older databases that are missing newer columns
            existing = {
                row[1]
                for row in conn.execute("PRAGMA table_info(transactions)").fetchall()
            }
            for col, typedef in [
                ("fee",        "REAL NOT NULL DEFAULT 0.0"),
                ("public_key", "TEXT NOT NULL DEFAULT ''"),
                ("tx_id",      "TEXT NOT NULL DEFAULT ''"),
            ]:
                if col not in existing:
                    conn.execute(
                        f"ALTER TABLE transactions ADD COLUMN {col} {typedef}"
                    )
            conn.commit()

    # ------------------------------------------------------------------ blockchain

    def save(self, blockchain: Blockchain) -> None:
        """Atomically replace all chain data on disk.

        Uses an explicit transaction so a crash mid-write leaves the
        previous data intact rather than a partially-written state.
        """
        with sqlite3.connect(self.filepath) as conn:
            conn.execute("BEGIN")
            try:
                conn.execute("DELETE FROM transactions")
                conn.execute("DELETE FROM blocks")
                for block in blockchain.chain:
                    conn.execute(
                        "INSERT INTO blocks VALUES (?, ?, ?, ?, ?)",
                        (block.index, block.timestamp, block.prev_hash,
                         block.nonce, block.hash),
                    )
                    for tx in block.transactions:
                        conn.execute(
                            "INSERT INTO transactions "
                            "(block_index, sender, recipient, amount, fee, "
                            " signature, note, public_key, tx_id) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (block.index, tx.sender, tx.recipient,
                             tx.amount, tx.fee, tx.signature, tx.note,
                             tx.public_key, tx.tx_id),
                        )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def load(self, difficulty: int = 3) -> Blockchain:
        """Load and reconstruct the blockchain from disk.

        Raises ValueError if the database is empty (no blocks found).
        """
        with sqlite3.connect(self.filepath) as conn:
            blocks = conn.execute(
                "SELECT block_index, timestamp, prev_hash, nonce, hash "
                "FROM blocks ORDER BY block_index"
            ).fetchall()

            if not blocks:
                raise ValueError("Database is empty — no blocks found.")

            txs_by_block: dict[int, list] = {b[0]: [] for b in blocks}
            for row in conn.execute(
                "SELECT block_index, sender, recipient, amount, fee, "
                "       signature, note, public_key, tx_id "
                "FROM transactions ORDER BY id"
            ).fetchall():
                txs_by_block[row[0]].append({
                    "sender":     row[1],
                    "recipient":  row[2],
                    "amount":     row[3],
                    "fee":        row[4],
                    "signature":  row[5],
                    "note":       row[6],
                    "public_key": row[7],
                    "tx_id":      row[8],
                })

        chain_data = [
            {
                "index":        b[0],
                "timestamp":    b[1],
                "prev_hash":    b[2],
                "nonce":        b[3],
                "hash":         b[4],
                "transactions": txs_by_block[b[0]],
            }
            for b in blocks
        ]
        return Blockchain.from_list(chain_data, difficulty=difficulty)

    # ------------------------------------------------------------------ wallets

    def save_mempool(self, transactions: list) -> None:
        """Atomically replace the persisted mempool with current pending txs."""
        with sqlite3.connect(self.filepath) as conn:
            conn.execute("BEGIN")
            try:
                conn.execute("DELETE FROM mempool")
                for tx in transactions:
                    conn.execute(
                        "INSERT OR REPLACE INTO mempool "
                        "(tx_id, sender, recipient, amount, fee, signature, note, public_key) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (tx.tx_id, tx.sender, tx.recipient, tx.amount,
                         tx.fee, tx.signature, tx.note, tx.public_key),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def load_mempool(self) -> list[dict]:
        """Return all persisted mempool transactions as dicts."""
        with sqlite3.connect(self.filepath) as conn:
            rows = conn.execute(
                "SELECT tx_id, sender, recipient, amount, fee, "
                "       signature, note, public_key "
                "FROM mempool"
            ).fetchall()
        return [
            {
                "tx_id":      row[0],
                "sender":     row[1],
                "recipient":  row[2],
                "amount":     row[3],
                "fee":        row[4],
                "signature":  row[5],
                "note":       row[6],
                "public_key": row[7],
            }
            for row in rows
        ]

    def save_wallet(self, wallet: Wallet) -> None:
        with sqlite3.connect(self.filepath) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO wallets (address, name) VALUES (?, ?)",
                (wallet.address, wallet.name),
            )
            conn.commit()

    def load_wallets(self) -> dict[str, str]:
        with sqlite3.connect(self.filepath) as conn:
            rows = conn.execute("SELECT address, name FROM wallets").fetchall()
        return {row[0]: row[1] for row in rows}

    def resolve_name(self, address: str, names: dict[str, str] | None = None) -> str:
        """Return the wallet name for *address*, or a shortened address string."""
        if address == "COINBASE":
            return "COINBASE"
        if names is not None:
            return names.get(address, address[:16] + "…")
        with sqlite3.connect(self.filepath) as conn:
            row = conn.execute(
                "SELECT name FROM wallets WHERE address = ?", (address,)
            ).fetchone()
        return row[0] if row and row[0] else address[:16] + "..."
