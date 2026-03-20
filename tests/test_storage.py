"""
test_storage.py -- Unit tests for SQLiteStorage.

Run from the project root:
    python tests/test_storage.py
"""

import sys
import os
import gc
import sqlite3

if '' not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kryptika.core import Blockchain, Transaction, Wallet
from kryptika.storage import SQLiteStorage

DB_PATH = "test_chain.db"


def _cleanup():
    """Delete the test DB file.

    On Windows, SQLite may keep the file handle open even after the
    `with sqlite3.connect(...)` block exits.  We force garbage collection
    to release any lingering connection objects before attempting deletion.
    """
    gc.collect()
    # Close any open sqlite3 connections by running a dummy connect/close cycle
    # that flushes the internal connection cache (no-op on Linux/macOS).
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.close()
    except Exception:
        pass
    gc.collect()
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            # Last resort on Windows: rename then delete
            tmp = DB_PATH + ".del"
            os.rename(DB_PATH, tmp)
            try:
                os.remove(tmp)
            except Exception:
                pass


def _make_storage() -> SQLiteStorage:
    """Return a fresh SQLiteStorage whose connection is released after use.

    SQLiteStorage opens connections inside `with sqlite3.connect(...)` blocks
    which are closed when the block exits, but CPython may defer the actual
    file-handle release until GC.  Creating the storage object here (rather
    than keeping it alive across the whole test) lets _cleanup() succeed.
    """
    return SQLiteStorage(DB_PATH)


def test_save_and_load_empty_chain():
    """A chain with only the genesis block must survive a save/load cycle."""
    _cleanup()
    bc      = Blockchain(difficulty=2)
    storage = _make_storage()
    storage.save(bc)
    del storage

    restored      = _make_storage().load(difficulty=2)
    valid, reason = restored.is_valid()
    assert valid is True
    assert restored.height == 1
    assert restored.chain[0].hash == bc.chain[0].hash
    del restored
    _cleanup()
    print("  [OK]  test_save_and_load_empty_chain")


def test_save_and_load_with_transactions():
    """All transactions must be preserved exactly after save/load."""
    _cleanup()
    miner   = Wallet()
    alice   = Wallet()
    bc      = Blockchain(difficulty=2)

    bc.mine_block([], miner.address)
    bc.mine_block([Transaction.create(miner, alice.address, 5.0)], miner.address)

    storage = _make_storage()
    storage.save(bc)
    del storage

    restored      = _make_storage().load(difficulty=2)
    valid, reason = restored.is_valid()
    assert valid is True
    assert restored.height == bc.height
    assert restored.get_balance(alice.address) == 5.0
    assert restored.get_balance(miner.address) == bc.get_balance(miner.address)
    del restored
    _cleanup()
    print("  [OK]  test_save_and_load_with_transactions")


def test_hashes_match_after_reload():
    """Every block hash must be identical before and after storage round-trip."""
    _cleanup()
    miner   = Wallet()
    bc      = Blockchain(difficulty=2)
    bc.mine_block([], miner.address)
    bc.mine_block([], miner.address)

    storage = _make_storage()
    storage.save(bc)
    del storage

    restored = _make_storage().load(difficulty=2)
    for original, loaded in zip(bc.chain, restored.chain):
        assert original.hash == loaded.hash, (
            f"Block #{original.index} hash mismatch: "
            f"{original.hash[:16]} != {loaded.hash[:16]}"
        )
    del restored
    _cleanup()
    print("  [OK]  test_hashes_match_after_reload")


def test_load_empty_db_raises():
    """Loading from an empty database must raise ValueError."""
    _cleanup()
    storage = _make_storage()
    try:
        storage.load()
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "empty" in str(e).lower()
    del storage
    _cleanup()
    print("  [OK]  test_load_empty_db_raises")


def test_save_overwrites_previous_data():
    """Saving twice must replace the first save, not append to it."""
    _cleanup()
    miner   = Wallet()
    bc1     = Blockchain(difficulty=2)
    storage = _make_storage()
    storage.save(bc1)
    del storage

    bc2 = Blockchain(difficulty=2)
    bc2.mine_block([], miner.address)
    bc2.mine_block([], miner.address)
    storage = _make_storage()
    storage.save(bc2)
    del storage

    restored = _make_storage().load(difficulty=2)
    assert restored.height == bc2.height
    assert restored.last_block.hash == bc2.last_block.hash
    del restored
    _cleanup()
    print("  [OK]  test_save_overwrites_previous_data")


if __name__ == "__main__":
    print("\nRunning storage tests...\n")
    test_save_and_load_empty_chain()
    test_save_and_load_with_transactions()
    test_hashes_match_after_reload()
    test_load_empty_db_raises()
    test_save_overwrites_previous_data()
    print("\nAll 5 storage tests passed.\n")
