"""
wallet_cli.py -- Interactive wallet and transaction manager for Kryptika.

Run from the project root:
    python wallet_cli.py              (interactive node selection at startup)
    python wallet_cli.py 5001         (skip selection, connect to localhost:5001)
    python wallet_cli.py localhost:5001  (explicit host:port, skip selection)
    python wallet_cli.py 192.168.1.5:5000  (connect to a remote node directly)

Requires at least one node running:
    python run_node.py 5000

MULTI-NODE QUICK START
----------------------
Terminal 1:  python run_node.py 5000
Terminal 2:  python run_node.py 5001
Terminal 3:  python wallet_cli.py 5000
  -> option 9 (Manage peers) -> add localhost:5001

Now both nodes are peered and will sync chains automatically after mining.

REMOTE NODE DISCOVERY
---------------------
Known remote peers are saved to peers.json automatically when you add them
via option 9. On the next startup they will be scanned alongside localhost
ports, so you no longer need to re-enter remote addresses manually.
"""

import json
import os
import sys
import datetime
import urllib.request
import urllib.error

from kryptika.core import Wallet, Transaction
from kryptika.storage import SQLiteStorage

# -------------------------------------------------------------------------
# Config
# -------------------------------------------------------------------------

WALLETS_FILE  = "wallets.json"
PEERS_FILE    = "peers.json"          # <-- NEW: persisted remote peer list
DEFAULT_FEE   = Transaction.DEFAULT_FEE
_PROBE_PORTS  = list(range(5000, 5011))  # localhost:5000-5010 scanned at startup

NODE: str   # set by select_node()
DB:   str   # set by select_node()


# -------------------------------------------------------------------------
# NEW: peers.json helpers
# -------------------------------------------------------------------------

def load_saved_peers() -> list[str]:
    """
    Return the list of host:port strings previously saved in peers.json.
    These are remote (non-localhost) nodes the user has connected to before.
    """
    if not os.path.exists(PEERS_FILE):
        return []
    try:
        with open(PEERS_FILE) as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(p) for p in data]
    except (json.JSONDecodeError, ValueError):
        pass
    return []


def save_peer(host_port: str) -> None:
    """
    Persist host_port into peers.json so it is auto-scanned next startup.
    localhost entries are intentionally excluded — they are already covered
    by _PROBE_PORTS.
    """
    # Don't bother saving localhost entries
    host = host_port.split(":")[0].lower()
    if host in ("localhost", "127.0.0.1", ""):
        return

    peers = load_saved_peers()
    if host_port not in peers:
        peers.append(host_port)
        tmp = PEERS_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(peers, f, indent=2)
        os.replace(tmp, PEERS_FILE)   # atomic write — same pattern as wallets


# -------------------------------------------------------------------------
# Node probing
# -------------------------------------------------------------------------

def _probe_node(host_port: str) -> dict | None:
    """Return /status dict if the node is reachable, else None."""
    try:
        url  = f"http://{host_port}/status"
        data = urllib.request.urlopen(url, timeout=1).read()
        return json.loads(data)
    except Exception:
        return None


def _parse_arg(arg: str) -> str:
    """
    Accept either a bare port number ("5001") or a host:port string
    ("localhost:5001", "192.168.1.5:5000") and normalise to host:port.
    """
    if ":" not in arg:
        return f"localhost:{arg}"
    return arg


# -------------------------------------------------------------------------
# Node selection  (CHANGED: now also scans saved remote peers)
# -------------------------------------------------------------------------

def select_node() -> None:
    """
    Determine which node to connect to.

    Priority:
      1. If a CLI argument was given, use it directly (no prompt).
      2. Otherwise build a candidate list from:
           a. localhost:5000-5010  (always)
           b. any host:port saved in peers.json  (NEW)
         Probe all candidates, show what's reachable, and ask the user.
    """
    global NODE, DB

    # -- CLI argument shortcut -------------------------------------------
    if len(sys.argv) > 1:
        host_port = _parse_arg(sys.argv[1])
        NODE = f"http://{host_port}"
        port_part = host_port.split(":")[-1]
        DB   = f"chain_{port_part}.db"
        return

    # -- Build candidate list: localhost ports + saved remote peers -------
    candidates: list[str] = [f"localhost:{p}" for p in _PROBE_PORTS]

    saved_remote = load_saved_peers()          # NEW
    for peer in saved_remote:
        if peer not in candidates:
            candidates.append(peer)

    # -- Auto-discover running nodes -------------------------------------
    print()
    line("=")
    print(" Kryptika Wallet CLI  -  Node Selection")
    line("=")
    print(" Scanning for running nodes...\n")

    found: list[tuple[str, dict]] = []  # [(host_port, status_dict), ...]

    for hp in candidates:
        status = _probe_node(hp)
        if status:
            found.append((hp, status))
            tag = " (remote)" if hp in saved_remote else ""
            print(f"  [{len(found)}] {hp}{tag}  "
                  f"height={status['height']}  "
                  f"peers={len(status.get('peers', []))}  "
                  f"mempool={status['mempool']}")

    if not found:
        print("  No nodes found on default ports or saved peers.")

    print(f"\n  [c] Enter a custom address")
    if found:
        print(f"  [1] (default)" if len(found) == 1 else "")
    print()

    while True:
        default_hint = " (Enter for [1])" if len(found) == 1 else \
                       f" (Enter for [1])" if found else ""
        raw = input(f"  Select node{default_hint}: ").strip()

        if raw == "" and found:
            raw = "1"

        if raw.lower() == "c" or (raw == "" and not found):
            custom = input("  Enter host:port or port (e.g. 192.168.1.5:5000 or 5001): ").strip()
            if not custom:
                print("  Cancelled -- using localhost:5000.")
                custom = "5000"
            host_port = _parse_arg(custom)
            save_peer(host_port)               # NEW: persist remote for next time
            break

        if raw.isdigit() and 1 <= int(raw) <= len(found):
            host_port = found[int(raw) - 1][0]
            break

        print("  Invalid choice, try again.")

    NODE = f"http://{host_port}"
    port_part = host_port.split(":")[-1]
    DB   = f"chain_{port_part}.db"
    print(f"\n  Connected to {NODE}  (DB: {DB})\n")


# =========================================================================
# HTTP helpers
# =========================================================================

def get(url: str) -> dict | list | None:
    try:
        return json.loads(urllib.request.urlopen(url, timeout=5).read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())
    except urllib.error.URLError:
        print(f"\n  Error: cannot reach node at {NODE}")
        print("  Make sure a node is running: python run_node.py\n")
        return None


def post(url: str, body: dict) -> dict | None:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=5).read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())
    except urllib.error.URLError:
        print(f"\n  Error: cannot reach node at {NODE}\n")
        return None


# =========================================================================
# Wallet file helpers
# =========================================================================

def load_local_wallets() -> dict:
    if not os.path.exists(WALLETS_FILE):
        return {}
    try:
        with open(WALLETS_FILE) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        print(f"  Warning: {WALLETS_FILE} is corrupted -- starting fresh.")
        return {}


def save_local_wallets(wallets_data: dict) -> None:
    """Write wallets atomically -- crash mid-write leaves the file intact."""
    tmp = WALLETS_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(wallets_data, f, indent=2)
    os.replace(tmp, WALLETS_FILE)


def wallet_to_data(wallet: Wallet) -> dict:
    return {
        "name":            wallet.name,
        "address":         wallet.address,
        "private_key_hex": wallet.private_key_hex(),
    }


def wallet_from_data(data: dict) -> Wallet:
    return Wallet.from_private_key(data["private_key_hex"], name=data["name"])


# =========================================================================
# UI helpers
# =========================================================================

def line(char: str = "-", width: int = 56) -> None:
    print(char * width)


def header(title: str) -> None:
    print()
    line("=")
    print(f"  {title}")
    line("=")


def fmt_time(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def resolve_wallet(choice: str, names: list, wallets_data: dict) -> str | None:
    if choice.isdigit() and 1 <= int(choice) <= len(names):
        return names[int(choice) - 1]
    if choice in wallets_data:
        return choice
    print("  Invalid choice.")
    return None


# =========================================================================
# Menu actions
# =========================================================================

def create_wallet(wallets_data: dict, storage: SQLiteStorage) -> None:
    header("Create Wallet")
    name = input("  Enter wallet name: ").strip()
    if not name:
        print("  Name cannot be empty.")
        return
    if name in wallets_data:
        print(f"  Wallet '{name}' already exists.")
        return
    wallet = Wallet(name=name)
    wallets_data[name] = wallet_to_data(wallet)
    save_local_wallets(wallets_data)
    storage.save_wallet(wallet)
    print(f"\n  Wallet '{name}' created.")
    print(f"  Address : {wallet.address}")
    print(f"  Saved to {WALLETS_FILE}")


def check_balance(wallets_data: dict) -> None:
    header("Check Balances")
    if not wallets_data:
        print("  No wallets yet. Create one first.")
        return
    r = get(f"{NODE}/status")
    if r:
        print(f"  Node height: {r['height']}  mempool: {r['mempool']} pending\n")
    print(f"  {'Name':<14} {'Balance':>10}  Address")
    line()
    for name, data in wallets_data.items():
        r       = get(f"{NODE}/balance/{data['address']}")
        balance = r["balance"] if r and "balance" in r else "?"
        short   = data["address"][:32] + "..."
        print(f"  {name:<14} {str(balance):>10}  {short}")


def mine_coins(wallets_data: dict) -> None:
    header("Mine a Block")
    if not wallets_data:
        print("  No wallets yet. Create one first.")
        return
    r = get(f"{NODE}/transactions/pending")
    if r:
        print(f"  Pending transactions in mempool: {r['count']}")
        if r["count"] > 0:
            fee_sum = sum(tx.get("fee", 0) for tx in r["transactions"])
            print(f"  Total fees you will earn: {fee_sum:.4f} coins")
    print()
    names = list(wallets_data.keys())
    print("  Your wallets:")
    for i, name in enumerate(names, 1):
        print(f"    {i}. {name}")
    choice = input("\n  Pick wallet to receive reward (number or name): ").strip()
    name   = resolve_wallet(choice, names, wallets_data)
    if name is None:
        return
    address = wallets_data[name]["address"]
    print(f"\n  Mining... reward goes to '{name}'")
    r = get(f"{NODE}/mine?address={address}")
    if r is None:
        return
    if "error" in r:
        print(f"  Error: {r['error']}")
        return
    print(f"  Block #{r['index']} mined!  nonce={r['nonce']}")
    print(f"  Transactions confirmed : {r['transactions']}")
    print(f"  Miner reward          : {r.get('miner_reward', 0):.4f} coins")
    r2 = get(f"{NODE}/balance/{address}")
    if r2:
        print(f"  '{name}' new balance   : {r2['balance']} coins")


def send_coins(wallets_data: dict) -> None:
    header("Send Coins")
    if not wallets_data:
        print("  No wallets yet. Create one first.")
        return
    names    = list(wallets_data.keys())
    balances = {}
    print("  Your wallets:")
    for i, name in enumerate(names, 1):
        r              = get(f"{NODE}/balance/{wallets_data[name]['address']}")
        balances[name] = r["balance"] if r and "balance" in r else 0.0
        print(f"    {i}. {name:<14} ({balances[name]} coins)")

    sender_name = resolve_wallet(
        input("\n  Pick sender (number or name): ").strip(),
        names, wallets_data,
    )
    if sender_name is None:
        return

    print("\n  Recipient wallets:")
    for i, name in enumerate(names, 1):
        print(f"    {i}. {name}")
    print("  (or paste any external address)")

    recipient_input = input("\n  Recipient (number, name, or address): ").strip()
    if not recipient_input:
        print("  Recipient cannot be empty.")
        return

    if recipient_input.isdigit() and 1 <= int(recipient_input) <= len(names):
        recipient_name    = names[int(recipient_input) - 1]
        recipient_address = wallets_data[recipient_name]["address"]
    elif recipient_input in wallets_data:
        recipient_name    = recipient_input
        recipient_address = wallets_data[recipient_input]["address"]
    else:
        recipient_name    = recipient_input[:20] + "..."
        recipient_address = recipient_input

    if wallets_data[sender_name]["address"] == recipient_address:
        print("  Warning: sender and recipient are the same wallet.")
        if input("  Continue anyway? (y/n): ").strip().lower() != "y":
            print("  Cancelled.")
            return

    amount_str = input("  Amount to send: ").strip()
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError
    except ValueError:
        print("  Invalid amount -- must be a positive number.")
        return

    print(f"\n  Gas fee (default {DEFAULT_FEE} coins, press Enter to use default): ", end="")
    fee_str = input().strip()
    if fee_str == "":
        fee = DEFAULT_FEE
    else:
        try:
            fee = float(fee_str)
            if fee < 0:
                raise ValueError
        except ValueError:
            print("  Invalid fee -- using default.")
            fee = DEFAULT_FEE

    total_cost     = amount + fee
    sender_balance = balances.get(sender_name, 0.0)
    if sender_balance < total_cost:
        print(f"\n  Insufficient funds:")
        print(f"    Balance : {sender_balance} coins")
        print(f"    Need    : {total_cost} coins ({amount} + {fee} fee)")
        return

    note = input("  Note (press Enter to skip): ").strip()
    if not note:
        note = f"{sender_name} -> {recipient_name}"

    print(f"\n  Summary:")
    print(f"    From      : {sender_name}")
    print(f"    To        : {recipient_name}")
    print(f"    Amount    : {amount} coins")
    print(f"    Gas fee   : {fee} coins")
    print(f"    Total out : {total_cost} coins")
    print(f"    Note      : {note}")

    if input("\n  Confirm? (y/n): ").strip().lower() != "y":
        print("  Cancelled.")
        return

    tx = Transaction.create(
        wallet    = wallet_from_data(wallets_data[sender_name]),
        recipient = recipient_address,
        amount    = amount,
        fee       = fee,
        note      = note,
    )
    r = post(f"{NODE}/transactions/new", tx.to_dict())
    if r is None:
        return
    if "error" in r:
        print(f"\n  Transaction rejected: {r['error']}")
        return
    print(f"\n  {r['message']}")
    print(f"  Amount : {r['amount']} coins  Fee : {r.get('fee', 0)} coins")
    print("  Mine a block to confirm it.")


def view_chain(storage: SQLiteStorage) -> None:
    header("Chain History")
    chain = get(f"{NODE}/chain")
    if chain is None:
        return
    names = storage.load_wallets()
    for block in chain:
        ts = fmt_time(block["timestamp"])
        print(f"\n  Block #{block['index']}  [{ts}]  nonce={block['nonce']}")
        line()
        if not block["transactions"]:
            label = "(genesis)" if block["index"] == 0 else "(no transactions)"
            print(f"    {label}")
        for tx in block["transactions"]:
            sender    = storage.resolve_name(tx["sender"],    names)
            recipient = storage.resolve_name(tx["recipient"], names)
            fee_str   = f"  fee={tx.get('fee', 0)}" if tx.get("fee") else ""
            note_str  = f"  [{tx['note']}]"         if tx.get("note") else ""
            print(f"    {sender:<14} -> {recipient:<14}  {tx['amount']} coins{fee_str}{note_str}")
    print(f"\n  Total blocks: {len(chain)}")


def view_pending(storage: SQLiteStorage) -> None:
    header("Pending Transactions (Mempool)")
    r = get(f"{NODE}/transactions/pending")
    if r is None:
        return
    if r["count"] == 0:
        print("  No pending transactions.")
        return
    names     = storage.load_wallets()
    fee_total = sum(tx.get("fee", 0) for tx in r["transactions"])
    print(f"  {r['count']} pending  (total fees: {fee_total:.4f} coins)")
    line()
    for tx in r["transactions"]:
        sender    = storage.resolve_name(tx["sender"],    names)
        recipient = storage.resolve_name(tx["recipient"], names)
        note_str  = f"  [{tx['note']}]"   if tx.get("note") else ""
        fee_str   = f"  fee={tx.get('fee', 0)}"
        print(f"  {sender:<14} -> {recipient:<14}  {tx['amount']} coins{fee_str}{note_str}")


def view_history(wallets_data: dict, storage: SQLiteStorage) -> None:
    header("Transaction History")
    if not wallets_data:
        print("  No wallets yet.")
        return
    names_list = list(wallets_data.keys())
    print("  Wallets:")
    for i, name in enumerate(names_list, 1):
        print(f"    {i}. {name}")
    print("  (or paste any external address)")

    choice = input("\n  View history for (number, name, or address): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(names_list):
        address = wallets_data[names_list[int(choice) - 1]]["address"]
        label   = names_list[int(choice) - 1]
    elif choice in wallets_data:
        address = wallets_data[choice]["address"]
        label   = choice
    else:
        address = choice
        label   = choice[:20] + "..."

    r = get(f"{NODE}/history/{address}")
    if r is None:
        return
    names = storage.load_wallets()
    print(f"\n  History for: {label}")
    print(f"  Address    : {address[:40]}...")
    print(f"  Total txns : {r['count']}")
    line()
    if r["count"] == 0:
        print("  No transactions found.")
        return

    running_balance = 0.0
    TYPE_ICONS = {
        "mining_reward": "▶ REWARD  ",
        "sent":          "↑ SENT   ",
        "received":      "↓ RECEIVED",
    }
    for tx in r["history"]:
        ts        = fmt_time(tx["timestamp"])
        sender    = storage.resolve_name(tx["sender"],    names)
        recipient = storage.resolve_name(tx["recipient"], names)
        icon      = TYPE_ICONS.get(tx["type"], "? OTHER  ")
        fee_str   = f"  fee={tx['fee']:.4f}" if tx.get("fee") else ""
        note_str  = f"  [{tx['note']}]"      if tx.get("note") else ""

        if tx["type"] in ("received", "mining_reward"):
            running_balance += tx["amount"]
            delta = f"+{tx['amount']}"
        else:
            running_balance -= (tx["amount"] + tx.get("fee", 0))
            delta = f"-{tx['amount'] + tx.get('fee', 0):.4f}"

        print(f"\n  Block #{tx['block']:<4}  {ts}")
        print(f"  {icon}  {delta:>12} coins  (balance: {running_balance:.4f})")
        print(f"  From: {sender:<16}  To: {recipient:<16}{fee_str}{note_str}")


def manage_peers() -> None:
    header("Manage Peers (Multi-Node)")
    r = get(f"{NODE}/status")
    if r is None:
        return
    print(f"  This node : {NODE}")
    print(f"  Height    : {r['height']}")
    peers = r.get("peers", [])
    print(f"  Peers     : {len(peers)}")
    for p in peers:
        print(f"    - {p}")
    print()
    line()
    print("  1. Add a peer")
    print("  2. Sync with peers (adopt longest valid chain)")
    print("  3. Back")
    line()
    choice = input("  Choose: ").strip()

    if choice == "1":
        addr = input("  Peer address (e.g. 192.168.1.5:5001 or localhost:5001): ").strip()
        if not addr:
            print("  Cancelled.")
            return
        r = post(f"{NODE}/peers/add", {"address": addr})
        if r and "error" not in r:
            print(f"\n  Peer added. Known peers: {r['peers']}")

            save_peer(addr)            # NEW: persist remote peers to peers.json
            if addr in load_saved_peers():
                print(f"  Saved {addr} to {PEERS_FILE} — will auto-scan next startup.")

            my_host_port = NODE.replace("http://", "")
            r2 = post(f"http://{addr}/peers/add", {"address": my_host_port})
            if r2 and "error" not in r2:
                print(f"  Also registered this node on {addr}.")

            print(f"\n  Auto-syncing with {addr}...")
            _do_sync(show_header=False)
        elif r:
            print(f"  Error: {r.get('error')}")

    elif choice == "2":
        _do_sync()


def _do_sync(show_header: bool = True) -> None:
    """Pull the longest chain from all known peers."""
    status_before = get(f"{NODE}/status")
    height_before = status_before["height"] if status_before else "?"
    r = get(f"{NODE}/peers/sync")
    if r is None:
        return
    replaced     = r.get("replaced", False)
    height_after = r["height"]
    if replaced:
        print(f"  ✓ Chain updated!  {height_before} → {height_after} blocks")
        print(f"  Your node has adopted the longest valid chain from its peers.")
    else:
        if height_before == height_after:
            print(f"  ✓ Already up to date (height={height_after}).")
            print(f"  Make sure the peer has mined blocks before syncing.")
        else:
            print(f"  ✓ Already on the longest chain (height={height_after}).")


def node_status() -> None:
    header("Node Status")
    r = get(f"{NODE}/status")
    if r is None:
        return
    print(f"  Node URL   : {NODE}")
    print(f"  Height     : {r['height']}")
    print(f"  Difficulty : {r['difficulty']}")
    print(f"  Mempool    : {r['mempool']} pending transactions")
    print(f"  Last hash  : {r['last_block'][:40]}...")
    peers = r.get("peers", [])
    print(f"  Peers      : {len(peers)}")
    for p in peers:
        print(f"    - {p}")

    # NEW: show saved remote peers from peers.json
    saved = load_saved_peers()
    if saved:
        print(f"\n  Saved remote peers ({PEERS_FILE}):")
        for p in saved:
            print(f"    - {p}")


# =========================================================================
# Main loop
# =========================================================================

def main() -> None:
    select_node()
    print()
    line("=")
    print("  Kryptika Wallet CLI")
    print(f"  Node : {NODE}   DB : {DB}")
    line("=")

    wallets_data = load_local_wallets()
    storage      = SQLiteStorage(DB)

    MENU = [
        ("1", "Create wallet"),
        ("2", "Check balances"),
        ("3", "Mine a block"),
        ("4", "Send coins"),
        ("5", "View chain history"),
        ("6", "View pending transactions"),
        ("7", "Transaction history (by address)"),
        ("8", "Node status"),
        ("9", "Manage peers / multi-node"),
        ("0", "Exit"),
    ]

    while True:
        print()
        line()
        for key, label in MENU:
            print(f"  {key}. {label}")
        line()
        choice = input("  Choose: ").strip()

        if   choice == "1": create_wallet(wallets_data, storage)
        elif choice == "2": check_balance(wallets_data)
        elif choice == "3": mine_coins(wallets_data)
        elif choice == "4": send_coins(wallets_data)
        elif choice == "5": view_chain(storage)
        elif choice == "6": view_pending(storage)
        elif choice == "7": view_history(wallets_data, storage)
        elif choice == "8": node_status()
        elif choice == "9": manage_peers()
        elif choice == "0":
            print("  Bye.")
            break
        else:
            print("  Invalid choice. Pick 0-9.")


if __name__ == "__main__":
    main()
