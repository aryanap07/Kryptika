"""
main.py -- Kryptika demo script.

Demonstrates the full lifecycle in a single process:
  - Create wallets
  - Mine initial coins
  - Send signed transactions
  - Verify balances and chain validity

Run from the project root:
    python -m kryptika.main
"""

from .core import Blockchain, Transaction, Wallet


def main() -> None:
    print("\n" + "=" * 56)
    print("  Kryptika Demo")
    print("=" * 56)

    # ── 1. Create wallets ────────────────────────────────────────
    print("\n[1] Creating wallets...")
    alice = Wallet(name="Alice")
    bob   = Wallet(name="Bob")
    carol = Wallet(name="Carol")
    print(f"  Alice : {alice.address[:32]}...")
    print(f"  Bob   : {bob.address[:32]}...")
    print(f"  Carol : {carol.address[:32]}...")

    # ── 2. Create blockchain and mine genesis + reward blocks ────
    print("\n[2] Initialising blockchain (difficulty=2)...")
    bc = Blockchain(difficulty=2)
    print(f"  Genesis block mined.  Height={bc.height}")

    print("\n[3] Mining reward blocks...")
    bc.mine_block([], alice.address)
    print(f"  Block mined -> Alice earns {Transaction.MINING_REWARD} coins.  Height={bc.height}")
    bc.mine_block([], alice.address)
    print(f"  Block mined -> Alice earns {Transaction.MINING_REWARD} coins.  Height={bc.height}")

    # ── 3. Show balances ─────────────────────────────────────────
    print("\n[4] Balances after mining:")
    for w in [alice, bob, carol]:
        print(f"  {w.name:<6} : {bc.get_balance(w.address):.4f} coins")

    # ── 4. Send transactions ─────────────────────────────────────
    print("\n[5] Alice sends 7 coins to Bob (fee=0.5)...")
    tx1 = Transaction.create(alice, bob.address, 7.0, fee=0.5)
    print(f"  tx_id : {tx1.tx_id[:24]}...")

    print("  Bob sends 3 coins to Carol (fee=0.5)...")
    # Bob needs coins first -- mine the block above so Alice's tx is confirmed
    bc.mine_block([tx1], carol.address)   # carol mines, earns reward + fee
    print(f"  Block #{bc.height - 1} mined.  Height={bc.height}")

    tx2 = Transaction.create(bob, carol.address, 3.0, fee=0.5)
    bc.mine_block([tx2], alice.address)
    print(f"  Block #{bc.height - 1} mined.  Height={bc.height}")

    # ── 5. Final balances ────────────────────────────────────────
    print("\n[6] Final balances:")
    for w in [alice, bob, carol]:
        print(f"  {w.name:<6} : {bc.get_balance(w.address):.4f} coins")

    # ── 6. Chain validity ────────────────────────────────────────
    print("\n[7] Validating chain...")
    valid, reason = bc.is_valid()
    print(f"  Chain valid : {valid}")
    if not valid:
        print(f"  Reason      : {reason}")

    # ── 7. Tamper test ───────────────────────────────────────────
    print("\n[8] Tamper test -- modifying a transaction amount...")
    bc.chain[1].transactions[0].amount = 9999.0
    valid2, reason2 = bc.is_valid()
    print(f"  Chain valid after tamper : {valid2}")
    print(f"  Reason                   : {reason2}")

    print("\n" + "=" * 56)
    print("  Demo complete.")
    print("=" * 56 + "\n")


if __name__ == "__main__":
    main()
