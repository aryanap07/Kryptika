"""
blockchain.py — Blockchain for Kryptika.

The Blockchain is an append-only list of Blocks secured by:
  1. SHA-256 hashing     — every block hashes its own content.
  2. Chain linking       — every block stores the previous block's hash.
  3. Proof of Work       — every block's hash must start with N zeros.
  4. Transaction signing — every user transaction must be ECDSA-signed.

Tamper with any block and is_valid() immediately catches it.

Balance calculation
-------------------
Balances are computed by walking every block on the chain (UTXO-lite model).
  credit: every tx where address == recipient
  debit:  every tx where address == sender  (amount + fee)

Amounts are rounded to 8 decimal places to avoid floating-point drift.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from .block import Block
from .transaction import Transaction

GENESIS_PREV_HASH = "0" * 64


def _round(value: float) -> float:
    """Round a coin value to 8 decimal places using banker's-grade rounding."""
    return float(Decimal(str(value)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP))


class Blockchain:
    """An append-only chain of Blocks with Proof of Work.

    Invariants enforced by is_valid():
    - Genesis block must have prev_hash = 64 zeros.
    - Every block's stored hash must match its recomputed hash.
    - Every block's prev_hash must equal the previous block's hash.
    - Every block's hash must start with `difficulty` leading zeros.
    - Every non-coinbase transaction must carry a valid ECDSA signature.
    """

    def __init__(self, difficulty: int = 3):
        self.difficulty = difficulty
        self.chain: list[Block] = []
        self._mine_and_add(Block(
            index        = 0,
            transactions = [],
            prev_hash    = GENESIS_PREV_HASH,
        ))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mine_and_add(self, block: Block) -> None:
        """Find a nonce that satisfies Proof of Work, then append the block."""
        target = "0" * self.difficulty
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash   = block.compute_hash()
        self.chain.append(block)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mine_block(self, transactions: list[Transaction], miner_address: str) -> Block:
        """Validate transactions, collect fees, prepend coinbase, mine, append.

        Coinbase reward = MINING_REWARD + sum(all transaction fees).
        Sender balance check accounts for all transactions in the same
        batch — a sender cannot overspend across multiple txs in one block.

        Raises ValueError if:
        - Any transaction uses COINBASE_SENDER.
        - Any transaction has an invalid signature.
        - Any sender has insufficient funds (amount + fee) accounting for
          all earlier transactions from the same sender in this batch.
        """
        fee_total   = 0.0
        batch_spend: dict[str, float] = {}   # cumulative spend per sender this batch

        for tx in transactions:
            if tx.sender == Transaction.COINBASE_SENDER:
                raise ValueError(
                    "Transactions with COINBASE sender are not permitted. "
                    "Coinbase rewards are added automatically by mine_block()."
                )

            valid, reason = tx.is_valid()
            if not valid:
                raise ValueError(f"Invalid transaction: {reason}")

            total_cost    = _round(tx.amount + tx.fee)
            confirmed_bal = self.get_balance(tx.sender)
            already_spent = batch_spend.get(tx.sender, 0.0)
            effective_bal = _round(confirmed_bal - already_spent)

            if effective_bal < total_cost:
                raise ValueError(
                    f"Insufficient funds for {tx.sender[:16]}…: "
                    f"confirmed={confirmed_bal:.8f}, "
                    f"spent-in-batch={already_spent:.8f}, "
                    f"effective={effective_bal:.8f}, "
                    f"needed={total_cost:.8f}."
                )

            batch_spend[tx.sender] = _round(already_spent + total_cost)
            fee_total = _round(fee_total + tx.fee)

        block = Block(
            index        = self.height,
            transactions = [Transaction.coinbase(miner_address, fee_total)] + transactions,
            prev_hash    = self.last_block.hash,
        )
        self._mine_and_add(block)
        return block

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    @property
    def height(self) -> int:
        return len(self.chain)

    def get_balance(self, address: str) -> float:
        """Calculate the confirmed balance for an address.

        Walks the entire chain once:
          + amount  for every tx where address is the recipient
          - amount  for every tx where address is the sender
          - fee     for every tx where address is the sender
        """
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx.recipient == address:
                    balance = _round(balance + tx.amount)
                if tx.sender == address:
                    balance = _round(balance - tx.amount - tx.fee)
        return balance

    def get_history(self, address: str) -> list[dict]:
        """Return all confirmed transactions involving *address*, oldest first.

        Each entry contains:
            block, timestamp, type, sender, recipient, amount, fee, note, tx_id
        where type is one of: mining_reward | sent | received
        """
        history = []
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender != address and tx.recipient != address:
                    continue
                if tx.sender == Transaction.COINBASE_SENDER:
                    tx_type = "mining_reward"
                elif tx.sender == address:
                    tx_type = "sent"
                else:
                    tx_type = "received"
                history.append({
                    "block":     block.index,
                    "timestamp": block.timestamp,
                    "type":      tx_type,
                    "sender":    tx.sender,
                    "recipient": tx.recipient,
                    "amount":    tx.amount,
                    "fee":       tx.fee,
                    "note":      tx.note,
                    "tx_id":     tx.tx_id,
                })
        return history

    def is_valid(self) -> tuple[bool, Optional[str]]:
        """Validate the entire chain. Returns (True, None) or (False, reason).

        Checks performed on every block:
        - Genesis block has the canonical prev_hash (64 zeros).
        - Stored hash matches freshly recomputed hash (tamper detection).
        - prev_hash matches the previous block's hash (link integrity).
        - Hash satisfies Proof of Work (correct number of leading zeros).
        - Every transaction has a valid signature.
        """
        if not self.chain:
            return True, None

        target = "0" * self.difficulty

        # Genesis check
        if self.chain[0].prev_hash != GENESIS_PREV_HASH:
            return False, (
                f"Block #0 (genesis) has wrong prev_hash "
                f"'{self.chain[0].prev_hash[:16]}…' -- expected 64 zeros."
            )

        for i, curr in enumerate(self.chain):
            if curr.hash != curr.compute_hash():
                return False, (
                    f"Block #{i} has been tampered with — "
                    f"stored hash does not match computed hash."
                )

            if i > 0 and curr.prev_hash != self.chain[i - 1].hash:
                return False, (
                    f"Block #{i} has a broken chain link — "
                    f"prev_hash does not match Block #{i - 1}'s hash."
                )

            if not curr.hash.startswith(target):
                return False, (
                    f"Block #{i} fails Proof of Work — "
                    f"hash does not start with {self.difficulty} zero(s)."
                )

            for tx in curr.transactions:
                valid, reason = tx.is_valid()
                if not valid:
                    return False, f"Block #{i} contains an invalid transaction: {reason}"

        return True, None

    def get_block(self, index: int) -> Optional[Block]:
        """Return the block at *index*, or None if out of range."""
        if 0 <= index < self.height:
            return self.chain[index]
        return None

    def to_list(self) -> list[dict]:
        """Serialise the full chain to a list of dicts (for JSON transport)."""
        return [block.to_dict() for block in self.chain]

    @classmethod
    def from_list(cls, data: list[dict], difficulty: int = 3) -> "Blockchain":
        """Reconstruct a Blockchain from a list of block dicts.

        Does NOT re-mine blocks — use is_valid() to verify the result.
        """
        bc            = cls.__new__(cls)
        bc.difficulty = difficulty
        bc.chain      = [Block.from_dict(item) for item in data]
        return bc

    def __repr__(self) -> str:
        return f"Blockchain(height={self.height}, difficulty={self.difficulty})"

    def _build_candidate_block(
        self, transactions: list[Transaction], miner_address: str
    ) -> Block:
        """Validate transactions and mine a candidate block WITHOUT appending it.

        Called by Node.mine() so PoW can run outside the node lock.
        The caller is responsible for appending the returned block to self.chain.

        Raises ValueError on invalid transactions or insufficient funds.
        """
        fee_total   = 0.0
        batch_spend: dict[str, float] = {}

        for tx in transactions:
            if tx.sender == Transaction.COINBASE_SENDER:
                raise ValueError(
                    "Transactions with COINBASE sender are not permitted."
                )
            valid, reason = tx.is_valid()
            if not valid:
                raise ValueError(f"Invalid transaction: {reason}")

            total_cost    = _round(tx.amount + tx.fee)
            confirmed_bal = self.get_balance(tx.sender)
            already_spent = batch_spend.get(tx.sender, 0.0)
            effective_bal = _round(confirmed_bal - already_spent)

            if effective_bal < total_cost:
                raise ValueError(
                    f"Insufficient funds for {tx.sender[:16]}…: "
                    f"confirmed={confirmed_bal:.8f}, "
                    f"spent-in-batch={already_spent:.8f}, "
                    f"effective={effective_bal:.8f}, "
                    f"needed={total_cost:.8f}."
                )
            batch_spend[tx.sender] = _round(already_spent + total_cost)
            fee_total = _round(fee_total + tx.fee)

        block = Block(
            index        = self.height,
            transactions = [Transaction.coinbase(miner_address, fee_total)] + transactions,
            prev_hash    = self.last_block.hash,
        )

        # Run Proof of Work
        target = "0" * self.difficulty
        while not block.hash.startswith(target):
            block.nonce += 1
            block.hash   = block.compute_hash()

        return block
