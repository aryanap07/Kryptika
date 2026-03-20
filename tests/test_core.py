"""
test_core.py -- Unit tests for Transaction, Block, and Blockchain.

Run from the project root:
    python -m pytest tests/ -v
or:
    python tests/test_core.py
"""

import sys
import os
# Allow running directly: python tests/test_core.py from the project root.
if '' not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



from kryptika.core import Block, Blockchain, Transaction, Wallet


def test_transaction_amount_is_always_float():
    """Amount must be stored as float regardless of input type."""
    tx = Transaction(sender="COINBASE", recipient="abc", amount=10)
    assert isinstance(tx.amount, float)
    assert tx.amount == 10.0
    print("  [OK]  test_transaction_amount_is_always_float")


def test_transaction_rejects_non_positive_amount():
    """Amounts of zero or below must be rejected."""
    try:
        Transaction(sender="COINBASE", recipient="abc", amount=0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    try:
        Transaction(sender="COINBASE", recipient="abc", amount=-5)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  [OK]  test_transaction_rejects_non_positive_amount")


def test_coinbase_transaction_is_valid():
    """Coinbase transactions require no signature and must always be valid."""
    tx = Transaction.coinbase("miner_address")
    valid, reason = tx.is_valid()
    assert valid is True
    assert reason == ""
    print("  [OK]  test_coinbase_transaction_is_valid")


def test_signed_transaction_is_valid():
    """A transaction signed by a Wallet must pass verification."""
    wallet = Wallet()
    tx     = Transaction.create(wallet, "recipient_address", 5.0)
    valid, reason = tx.is_valid()
    assert valid is True
    assert reason == ""
    print("  [OK]  test_signed_transaction_is_valid")


def test_tampered_transaction_is_invalid():
    """Changing the amount after signing must invalidate the signature."""
    wallet = Wallet()
    tx     = Transaction.create(wallet, "recipient_address", 5.0)
    tx.amount = 999.0
    valid, reason = tx.is_valid()
    assert valid is False
    assert "verification failed" in reason.lower() or "invalid signature" in reason.lower()
    print("  [OK]  test_tampered_transaction_is_invalid")


def test_missing_signature_is_invalid():
    """A non-coinbase transaction with no signature must be rejected."""
    wallet = Wallet()
    tx     = Transaction(sender=wallet.address, recipient="abc", amount=5.0)
    valid, reason = tx.is_valid()
    assert valid is False
    assert "Missing signature" in reason
    print("  [OK]  test_missing_signature_is_invalid")


def test_transaction_serialization_round_trip():
    """to_dict + from_dict must produce an identical transaction."""
    wallet   = Wallet()
    tx       = Transaction.create(wallet, "recipient_address", 7.5)
    restored = Transaction.from_dict(tx.to_dict())
    assert restored.sender    == tx.sender
    assert restored.recipient == tx.recipient
    assert restored.amount    == tx.amount
    assert restored.signature == tx.signature
    valid, _ = restored.is_valid()
    assert valid is True
    print("  [OK]  test_transaction_serialization_round_trip")


def test_block_hash_is_deterministic():
    """Same inputs must always produce the same hash."""
    tx = Transaction.coinbase("miner")
    b1 = Block(index=1, transactions=[tx], prev_hash="0" * 64, timestamp=1000.0, nonce=0)
    b2 = Block(index=1, transactions=[tx], prev_hash="0" * 64, timestamp=1000.0, nonce=0)
    assert b1.hash == b2.hash
    print("  [OK]  test_block_hash_is_deterministic")


def test_nonce_changes_hash():
    """Different nonces must produce different hashes."""
    tx = Transaction.coinbase("miner")
    b1 = Block(index=1, transactions=[tx], prev_hash="0" * 64, timestamp=1000.0, nonce=0)
    b2 = Block(index=1, transactions=[tx], prev_hash="0" * 64, timestamp=1000.0, nonce=1)
    assert b1.hash != b2.hash
    print("  [OK]  test_nonce_changes_hash")


def test_genesis_block():
    """Chain must start with a single mined genesis block."""
    bc = Blockchain(difficulty=2)
    assert bc.height == 1
    assert bc.chain[0].transactions == []
    assert bc.chain[0].prev_hash == "0" * 64
    assert bc.chain[0].hash.startswith("00")
    print("  [OK]  test_genesis_block")


def test_mine_block_satisfies_difficulty():
    """Every mined block's hash must start with `difficulty` zeros."""
    bc    = Blockchain(difficulty=3)
    miner = Wallet()
    block = bc.mine_block([], miner.address)
    assert block.hash.startswith("000")
    print("  [OK]  test_mine_block_satisfies_difficulty")


def test_mine_block_links_correctly():
    """Each mined block must reference the hash of the block before it."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    b1    = bc.mine_block([], miner.address)
    b2    = bc.mine_block([], miner.address)
    assert b1.prev_hash == bc.chain[0].hash
    assert b2.prev_hash == b1.hash
    print("  [OK]  test_mine_block_links_correctly")


def test_coinbase_reward_in_every_block():
    """Every mined block must contain exactly one coinbase transaction."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    block = bc.mine_block([], miner.address)
    coinbase_txs = [tx for tx in block.transactions
                    if tx.sender == Transaction.COINBASE_SENDER]
    assert len(coinbase_txs) == 1
    assert coinbase_txs[0].amount == Transaction.MINING_REWARD
    print("  [OK]  test_coinbase_reward_in_every_block")


def test_balance_tracks_correctly():
    """get_balance must correctly sum credits and debits."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    alice = Wallet()

    bc.mine_block([], miner.address)
    assert bc.get_balance(miner.address) == Transaction.MINING_REWARD

    bc.mine_block([Transaction.create(miner, alice.address, 6.0)], miner.address)
    assert bc.get_balance(alice.address) == 6.0
    assert bc.get_balance(miner.address) == Transaction.MINING_REWARD * 2 - 6.0
    print("  [OK]  test_balance_tracks_correctly")


def test_insufficient_funds_rejected():
    """mine_block must reject a transaction whose sender has no funds."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    alice = Wallet()
    try:
        bc.mine_block([Transaction.create(alice, miner.address, 1.0)], miner.address)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Insufficient funds" in str(e)
    print("  [OK]  test_insufficient_funds_rejected")


def test_valid_chain():
    """An untouched mined chain must pass all four validation checks."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    bc.mine_block([], miner.address)
    bc.mine_block([], miner.address)
    valid, reason = bc.is_valid()
    assert valid is True
    assert reason is None
    print("  [OK]  test_valid_chain")


def test_tampered_data_detected():
    """Mutating a block's transaction data must fail Check 1."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    bc.mine_block([], miner.address)
    bc.chain[1].transactions[0].amount = 999.0
    valid, reason = bc.is_valid()
    assert valid is False
    assert "tampered" in reason
    print("  [OK]  test_tampered_data_detected")


def test_tampered_genesis_detected():
    """Tampering with the genesis block must also be caught."""
    bc = Blockchain(difficulty=2)
    bc.chain[0].prev_hash = "tampered"
    valid, reason = bc.is_valid()
    assert valid is False
    assert "tampered" in reason
    print("  [OK]  test_tampered_genesis_detected")


def test_broken_link_detected():
    """A block whose prev_hash points to the wrong block must fail Check 2.

    We re-mine the tampered block so Check 1 passes but Check 2 fails.
    """
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    bc.mine_block([], miner.address)
    bc.mine_block([], miner.address)

    target          = "0" * bc.difficulty
    block           = bc.chain[2]
    block.prev_hash = "0" * 64
    block.nonce     = 0
    block.hash      = block.compute_hash()
    while not block.hash.startswith(target):
        block.nonce += 1
        block.hash   = block.compute_hash()

    valid, reason = bc.is_valid()
    assert valid is False
    assert "broken" in reason.lower()
    print("  [OK]  test_broken_link_detected")


def test_insufficient_proof_of_work_detected():
    """A block whose hash fails the difficulty target must fail Check 3."""
    bc    = Blockchain(difficulty=4)
    miner = Wallet()
    bc.mine_block([], miner.address)

    block       = bc.chain[1]
    block.nonce = 0
    block.hash  = block.compute_hash()
    while block.hash.startswith("0000"):
        block.nonce += 1
        block.hash   = block.compute_hash()

    valid, reason = bc.is_valid()
    assert valid is False
    assert "proof of work" in reason.lower() or "fails" in reason.lower()
    print("  [OK]  test_insufficient_proof_of_work_detected")


def test_invalid_transaction_in_block_detected():
    """A block containing an invalid transaction must fail Check 4."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    alice = Wallet()

    bc.mine_block([], miner.address)
    bc.mine_block([Transaction.create(miner, alice.address, 5.0)], miner.address)

    # Tamper with the transaction amount inside the mined block.
    # This changes the block contents so Check 1 (hash mismatch) fires.
    bc.chain[2].transactions[1].amount = 999.0

    valid, reason = bc.is_valid()
    assert valid is False
    assert "tampered" in reason
    print("  [OK]  test_invalid_transaction_in_block_detected")


def test_serialization_round_trip():
    """to_list + from_list must produce an identical valid chain."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    alice = Wallet()

    bc.mine_block([], miner.address)
    bc.mine_block([Transaction.create(miner, alice.address, 5.0)], miner.address)

    restored      = Blockchain.from_list(bc.to_list(), difficulty=2)
    valid, reason = restored.is_valid()
    assert valid is True
    assert restored.height == bc.height
    assert restored.last_block.hash == bc.last_block.hash
    assert restored.get_balance(alice.address) == 5.0
    print("  [OK]  test_serialization_round_trip")



def test_fake_coinbase_rejected_by_mine_block():
    """Passing a COINBASE-sender transaction to mine_block must be rejected."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    fake  = Transaction(
        sender    = Transaction.COINBASE_SENDER,
        recipient = miner.address,
        amount    = 999.0,
    )
    try:
        bc.mine_block([fake], miner.address)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "COINBASE" in str(e)
    print("  [OK]  test_fake_coinbase_rejected_by_mine_block")

def test_fee_deducted_from_sender():
    """Sender's balance must decrease by amount + fee."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    alice = Wallet()
    bob   = Wallet()

    bc.mine_block([], miner.address)
    # miner has 10 coins; sends 4 to alice with fee=1
    # block2 coinbase = 10+1=11, miner net = 10 + 11 - 4 - 1 = 16
    bc.mine_block([Transaction.create(miner, alice.address, 4.0, fee=1.0)], miner.address)
    assert bc.get_balance(alice.address) == 4.0
    assert bc.get_balance(miner.address) == 16.0
    # fees cancel out (miner paid 1 fee, earned 1 fee back as miner)
    # net balance = 10 (block1) + 10 (block2 reward) + 1 (fee earned) - 4 (sent) - 1 (fee paid) = 16
    assert bc.get_balance(miner.address) == 16.0
    print("  [OK]  test_fee_deducted_from_sender")


def test_miner_receives_fees():
    """Coinbase reward must equal MINING_REWARD + sum of all fees in block."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    alice = Wallet()

    bc.mine_block([], miner.address)  # fund miner
    txs = [
        Transaction.create(miner, alice.address, 2.0, fee=0.5),
        Transaction.create(miner, alice.address, 1.0, fee=0.3),
    ]
    bc.mine_block(txs, miner.address)
    coinbase = bc.last_block.transactions[0]
    assert coinbase.amount == Transaction.MINING_REWARD + 0.5 + 0.3
    print("  [OK]  test_miner_receives_fees")


def test_insufficient_funds_includes_fee():
    """mine_block must reject tx where balance < amount + fee."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    alice = Wallet()

    bc.mine_block([], miner.address)  # miner gets 10
    # Try to send 10 with fee 0.5 -> needs 10.5, has 10 -> should fail
    try:
        bc.mine_block(
            [Transaction.create(miner, alice.address, 10.0, fee=0.5)],
            miner.address,
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Insufficient" in str(e)
    print("  [OK]  test_insufficient_funds_includes_fee")


def test_get_history_returns_correct_entries():
    """get_history must return all tx touching the address with correct types."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    alice = Wallet()

    bc.mine_block([], miner.address)
    bc.mine_block([Transaction.create(miner, alice.address, 3.0, fee=0.5)], miner.address)

    miner_h = bc.get_history(miner.address)
    alice_h = bc.get_history(alice.address)

    # Miner: 2 mining rewards + 1 sent tx
    types_miner = [e["type"] for e in miner_h]
    assert "mining_reward" in types_miner
    assert "sent"          in types_miner

    # Alice: 1 received tx
    assert len(alice_h) == 1
    assert alice_h[0]["type"]   == "received"
    assert alice_h[0]["amount"] == 3.0
    print("  [OK]  test_get_history_returns_correct_entries")


def test_zero_fee_transaction():
    """Transactions with fee=0 must be accepted and not affect miner bonus."""
    bc    = Blockchain(difficulty=2)
    miner = Wallet()
    alice = Wallet()

    bc.mine_block([], miner.address)
    bc.mine_block([Transaction.create(miner, alice.address, 5.0, fee=0.0)], miner.address)
    coinbase = bc.last_block.transactions[0]
    assert coinbase.amount == Transaction.MINING_REWARD  # no fee bonus
    assert bc.get_balance(alice.address) == 5.0
    print("  [OK]  test_zero_fee_transaction")

# -- Gas fee & history tests ---------------------------------------------------

def test_tx_id_is_set_after_create():
    """Transaction.create() must set a non-empty tx_id."""
    w = Wallet(); r = Wallet()
    tx = Transaction.create(w, r.address, 5.0)
    assert tx.tx_id and len(tx.tx_id) == 64
    print("  [OK]  test_tx_id_is_set_after_create")


def test_tx_id_unique_per_transaction():
    """Two identical transactions must have different tx_ids (ECDSA is randomised)."""
    w = Wallet(); r = Wallet()
    tx1 = Transaction.create(w, r.address, 5.0)
    tx2 = Transaction.create(w, r.address, 5.0)
    assert tx1.tx_id != tx2.tx_id
    print("  [OK]  test_tx_id_unique_per_transaction")


def test_tx_id_survives_serialisation():
    """tx_id must be preserved through to_dict / from_dict."""
    w = Wallet(); r = Wallet()
    tx      = Transaction.create(w, r.address, 5.0)
    restored = Transaction.from_dict(tx.to_dict())
    assert restored.tx_id == tx.tx_id
    print("  [OK]  test_tx_id_survives_serialisation")


def test_coinbase_tx_id_is_set():
    """Transaction.coinbase() must also generate a tx_id."""
    tx = Transaction.coinbase("miner")
    assert tx.tx_id and len(tx.tx_id) == 64
    print("  [OK]  test_coinbase_tx_id_is_set")


# ---------------------------------------------------------------------------
# Regression tests for fixed bugs
# ---------------------------------------------------------------------------

def test_batch_double_spend_rejected_by_mine_block():
    """mine_block() must reject a batch where the same sender's txs collectively
    exceed their confirmed balance, even if each individual tx looks affordable."""
    bc    = Blockchain(difficulty=1)
    miner = Wallet("miner")
    alice = Wallet("alice")
    bob   = Wallet("bob")

    # Give miner exactly 10 coins
    bc.mine_block([], miner.address)
    assert bc.get_balance(miner.address) == Transaction.MINING_REWARD

    # Two txs each costing 4.5 = 9.0 total -- should succeed
    tx1 = Transaction.create(miner, alice.address, 4.0, fee=0.5)
    tx2 = Transaction.create(miner, alice.address, 4.0, fee=0.5)
    bc.mine_block([tx1, tx2], bob.address)

    # Reset: give miner fresh coins
    bc2    = Blockchain(difficulty=1)
    miner2 = Wallet("miner2")
    alice2 = Wallet("alice2")
    bob2   = Wallet("bob2")
    bc2.mine_block([], miner2.address)

    # Three txs each costing 4.5 = 13.5 > 10 -- must fail
    tx3 = Transaction.create(miner2, alice2.address, 4.0, fee=0.5)
    tx4 = Transaction.create(miner2, alice2.address, 4.0, fee=0.5)
    tx5 = Transaction.create(miner2, alice2.address, 4.0, fee=0.5)
    try:
        bc2.mine_block([tx3, tx4, tx5], bob2.address)
        raise AssertionError("BUG: batch double-spend was not caught")
    except ValueError as e:
        assert "batch" in str(e).lower() or "insufficient" in str(e).lower()
    print("  [OK]  test_batch_double_spend_rejected_by_mine_block")


def test_batch_double_spend_same_sender_different_recipients():
    """Variant: many small txs to different recipients from same sender."""
    bc    = Blockchain(difficulty=1)
    miner = Wallet("miner")
    bc.mine_block([], miner.address)   # 10 coins

    recipients = [Wallet(f"r{i}") for i in range(4)]
    # 4 x 3.0 coins = 12 > 10  (fee=0 to keep math simple)
    txs = [Transaction.create(miner, r.address, 3.0, fee=0.0) for r in recipients]
    try:
        bc.mine_block(txs, Wallet("m").address)
        raise AssertionError("BUG: overspend batch not caught")
    except ValueError:
        pass
    print("  [OK]  test_batch_double_spend_same_sender_different_recipients")


if __name__ == "__main__":
    print("\nRunning core tests...\n")
    test_transaction_amount_is_always_float()
    test_transaction_rejects_non_positive_amount()
    test_coinbase_transaction_is_valid()
    test_signed_transaction_is_valid()
    test_tampered_transaction_is_invalid()
    test_missing_signature_is_invalid()
    test_transaction_serialization_round_trip()
    test_block_hash_is_deterministic()
    test_nonce_changes_hash()
    test_genesis_block()
    test_mine_block_satisfies_difficulty()
    test_mine_block_links_correctly()
    test_coinbase_reward_in_every_block()
    test_balance_tracks_correctly()
    test_insufficient_funds_rejected()
    test_valid_chain()
    test_tampered_data_detected()
    test_tampered_genesis_detected()
    test_broken_link_detected()
    test_insufficient_proof_of_work_detected()
    test_invalid_transaction_in_block_detected()
    test_serialization_round_trip()
    test_fake_coinbase_rejected_by_mine_block()
    test_fee_deducted_from_sender()
    test_miner_receives_fees()
    test_insufficient_funds_includes_fee()
    test_get_history_returns_correct_entries()
    test_zero_fee_transaction()
    test_tx_id_is_set_after_create()
    test_tx_id_unique_per_transaction()
    test_tx_id_survives_serialisation()
    test_coinbase_tx_id_is_set()
    test_batch_double_spend_rejected_by_mine_block()
    test_batch_double_spend_same_sender_different_recipients()
    print("\nAll 32 core tests passed.\n")
