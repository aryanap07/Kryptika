"""
block.py — Block for Kryptika.

A block is a container that holds:
- A list of transactions
- A timestamp
- A nonce (the number found during Proof of Work)
- The hash of the previous block (the chain link)
- Its own SHA-256 hash

Changing any field changes the hash, which breaks the chain link to
the next block — this is how tampering is detected.
"""

import hashlib
import json
import time
from typing import Optional
from .transaction import Transaction


class Block:
    """A single block in the blockchain."""

    def __init__(
        self,
        index:        int,
        transactions: list[Transaction],
        prev_hash:    str,
        timestamp:    Optional[float] = None,
        nonce:        int = 0,
    ):
        self.index        = index
        self.transactions = transactions
        self.prev_hash    = prev_hash
        self.timestamp    = timestamp if timestamp is not None else time.time()
        self.nonce        = nonce
        self.hash         = self.compute_hash()

    def compute_hash(self) -> str:
        """Return the SHA-256 hash of this block's contents.

        sort_keys=True ensures the output is deterministic regardless
        of dictionary insertion order across Python versions or platforms.
        """
        content = json.dumps(
            {
                "index":        self.index,
                "transactions": [tx.to_dict() for tx in self.transactions],
                "prev_hash":    self.prev_hash,
                "timestamp":    self.timestamp,
                "nonce":        self.nonce,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> dict:
        """Serialise this block to a plain dictionary."""
        return {
            "index":        self.index,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "prev_hash":    self.prev_hash,
            "timestamp":    self.timestamp,
            "nonce":        self.nonce,
            "hash":         self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        """Reconstruct a Block from a dictionary.

        The stored hash is restored as-is.  Blockchain.is_valid() will
        recompute and compare hashes to catch any tampering.
        """
        block      = cls(
            index        = data["index"],
            transactions = [Transaction.from_dict(tx) for tx in data["transactions"]],
            prev_hash    = data["prev_hash"],
            timestamp    = data["timestamp"],
            nonce        = data["nonce"],
        )
        block.hash = data["hash"]
        return block

    def __repr__(self) -> str:
        return (
            f"Block(index={self.index}, "
            f"txs={len(self.transactions)}, "
            f"nonce={self.nonce}, "
            f"hash={self.hash[:12]}...)"
        )
