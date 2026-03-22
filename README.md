<div align="center">

<br/>

<pre>
██╗  ██╗██████╗ ██╗   ██╗██████╗ ████████╗██╗██╗  ██╗ █████╗
██║ ██╔╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██║██║ ██╔╝██╔══██╗
█████╔╝ ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║█████╔╝ ███████║
██╔═██╗ ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║██╔═██╗ ██╔══██║
██║  ██╗██║  ██║   ██║   ██║        ██║   ██║██║  ██╗██║  ██║
╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝   ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
</pre>

**A blockchain built from scratch in pure Python.**  
*No frameworks. No shortcuts. Every line written to be read, not just run.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Version](https://img.shields.io/badge/Version-1.1.0-6C63FF?style=for-the-badge)](https://github.com/aryanap07/Kryptika)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)
<br/>

</div>

---

## What is Kryptika?

Kryptika is a complete blockchain built from the ground up in pure Python — SHA-256 hashing, Proof of Work mining, ECDSA-signed transactions, live peer-to-peer networking, SQLite persistence, and a fully thread-safe node. Every primitive is hand-written and readable.

It's for developers who want to stop wondering how blockchains work and just see it happen. Clone it, run it, break it, read it.

---

## Table of Contents

1. [Features](#1-features)
2. [How It Works](#2-how-it-works)
3. [Project Structure](#3-project-structure)
4. [Requirements & Installation](#4-requirements-installation)
5. [Quick Start](#5-quick-start)
6. [Running a Node](#6-running-a-node)
7. [Wallet CLI](#7-wallet-cli)
8. [Multi-Node Network](#8-multi-node-network)
9. [REST API Reference](#9-rest-api-reference)
10. [Running the Tests](#10-running-the-tests)
11. [Architecture Notes](#11-architecture-notes)
12. [Security Model](#12-security-model)
13. [Known Limitations](#13-known-limitations)
14. [License](#14-license)

---

## 1. Features

### Chain

| Feature | Detail |
|---|---|
| SHA-256 Hashing | Tamper-evident block linking |
| Genesis Block | Deterministic chain bootstrap |

### Mining

| Feature | Detail |
|---|---|
| Proof of Work | Configurable leading-zero difficulty |
| Mining Reward | Fixed 10-coin base reward + fees |

### Wallets

| Feature | Detail |
|---|---|
| ECDSA P-256 Key Pairs | Cryptographically secure key generation |
| Address Derivation | Address = SHA-256 of public key |

### Transactions

| Feature | Detail |
|---|---|
| Cryptographic Signatures | ECDSA-signed; verified by all nodes |
| Gas Fees | Per-transaction fee that rewards the miner; defaults to 0.5 coins |
| Replay Protection | `tx_id` checked against chain + mempool |
| Decimal Precision | 8 decimal places — no floating-point drift |

### Network

| Feature | Detail |
|---|---|
| P2P Broadcast | New blocks propagate to all peers instantly |
| Longest-Chain Consensus | Forks resolve automatically |
| REST API | Full HTTP interface with CORS support |

### Safety

| Feature | Detail |
|---|---|
| Mempool Guard | Effective-balance checked before queuing |
| Double-Spend Guard | Per-sender spend tracked across each block |
| Thread Safety | PoW runs outside the node lock; reads always non-blocking |

### Storage

| Feature | Detail |
|---|---|
| Atomic Persistence | SQLite with explicit `BEGIN / COMMIT / ROLLBACK` |
| Per-Node Databases | Each node keeps its own `chain_<port>.db` |

---

## 2. How It Works

### Blocks and the Chain

Every block holds a list of transactions, a timestamp, a nonce, and a hash of the block before it. Change even a single byte anywhere and the hash changes — snapping every link that follows. Tampering is caught immediately.

Block `0` is the **genesis block** — always empty, always identical. Every block after it locks onto the previous block's hash, forming a chain that can't be quietly rewritten.

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Block 0         │     │  Block 1         │     │  Block 2         │
│  (Genesis)       │────→│                  │────→│                  │
│  prev: 000000    │     │  prev: 000a1b2c  │     │  prev: 000f3d9a  │
│  hash: 000a1b2c  │     │  hash: 000f3d9a  │     │  hash: 000c77e1  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

### Proof of Work

To add a block, a miner must find a `nonce` that makes the block's SHA-256 hash start with a specific number of zeros. There's no shortcut — it takes thousands of attempts. That's the point. Rewriting history would mean redoing all that work, which is what makes the chain trustworthy.

```python
# Conceptual example — difficulty 3
while not block_hash.startswith("000"):
    block.nonce += 1
    block_hash = sha256(block)
```

> Each extra leading zero requires roughly 16× more hashes — the difficulty scales exponentially.

### Wallets and Addresses

A wallet is an ECDSA P-256 key pair. Your address is just a SHA-256 hash of your public key — safe to share with anyone. Your private key never leaves your machine; it's what you use to prove you authorised a transaction.

```
Private key  ──(ECDSA P-256)──→  Public key  ──(SHA-256)──→  Address
  SECRET — never share              shareable                  shareable
```

### Transactions

When you send coins, you sign a small payload with your private key. That signature gets attached to the transaction and broadcast to the network. Every node can verify it's genuinely from you using your public key — without ever needing to see the private key itself.

```
{ sender, recipient, amount, fee }  +  private key
                         │
                    ECDSA P-256
                         │
                    signature ──→ broadcast to all nodes
                                        │
                              node verifies with public key ✓
```

### The Mempool

Before a transaction lands on the chain, it sits in the **mempool** — a waiting room for unconfirmed transactions. Miners pick them up and bundle them into the next block. The miner earns the base reward plus every fee in that block, so if you want faster confirmation, offer a higher fee.

```
Mempool:  [alice→bob 5.0 | fee: 0.5]  [bob→carol 2.0 | fee: 0.5]  [carol→dave 1.0 | fee: 0.5]
                                    ↓  miner picks up & mines
                         Block mined → miner earns base reward + all fees
```

### Consensus — Longest Chain Wins

Sometimes two nodes mine a block at exactly the same moment. That's a fork — two valid but competing chains. Kryptika resolves it the same way Bitcoin does: the longest valid chain wins. As soon as any node mines the next block and broadcasts it, every other node sees the longer chain and switches over. No votes, no coordination, no manual intervention.

```
Fork:
  Node A: [0]──[1]──[2]──[3a]          ← tied
  Node B: [0]──[1]──[2]──[3b]          ← tied

Node A mines next:
  Node A: [0]──[1]──[2]──[3a]──[4]     ← broadcasts, wins (longer)
  Node B: [0]──[1]──[2]──[3a]──[4]     ← drops [3b], adopts A's chain
```

---

## 3. Project Structure

```
kryptika/                       ← project root — run all commands here
│
├── run_node.py                 ← start a blockchain node
├── wallet_cli.py               ← interactive wallet & transaction manager
├── pyproject.toml              ← package metadata and entry points
├── LICENSE
│
├── kryptika/                   ← main Python package
│   │
│   ├── core/                   ← blockchain primitives
│   │   ├── transaction.py      ← Wallet (keygen, sign) + Transaction (create, verify)
│   │   ├── block.py            ← Block (hash, nonce, serialisation)
│   │   └── blockchain.py       ← Blockchain (mine, validate, balance, history)
│   │
│   ├── network/                ← P2P layer
│   │   ├── node.py             ← Node (mempool, broadcast, sync — thread-safe)
│   │   └── server.py           ← HTTP REST server (all endpoints)
│   │
│   ├── storage/                ← persistence layer
│   │   └── storage.py          ← SQLiteStorage (atomic save + load + migration)
│   │
│   └── main.py                 ← standalone demo script
│
└── tests/
    ├── test_core.py            ← 34 unit tests (core primitives)
    ├── test_storage.py         ←  5 unit tests (persistence)
    └── test_network.py         ← 13 integration tests (live HTTP servers)
```

---

## 4. Requirements & Installation

You'll need **Python 3.10 or newer**. Kryptika has exactly one external dependency — the `cryptography` library for ECDSA. Everything else is the Python standard library.

### Option A — Quick install

```bash
pip install cryptography>=41.0
```

That's all you need to run every script.

### Option B — Install as a package

```bash
pip install -e .
```

This gives you the `kryptika-node` command globally inside your environment — handy if you're running multiple nodes and don't want to `cd` each time.

**Activate a virtual environment first (recommended):**

```bash
# Create
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows — Command Prompt
.venv\Scripts\activate.bat

# Windows — PowerShell
.venv\Scripts\Activate.ps1
```

---

## 5. Quick Start

Don't want to spin up a server yet? Run the full blockchain lifecycle — wallets, mining, transactions, tamper detection — in a single script:

```bash
python -m kryptika.main
```

Here's what it does:
- Creates wallets for Alice, Bob, and Carol
- Mines a few blocks
- Sends signed transactions between wallets
- Checks balances
- Deliberately corrupts a block and shows the chain catching it

Expected output:

```
[Blockchain] Genesis block mined.
[Wallet] Alice:  3f9a2b1c...
[Wallet] Bob:    7d4e8f0a...
[Mine]   Block #1 mined — reward → Alice
[Send]   Alice → Bob: 5.0 coins (fee: 0.1)
[Mine]   Block #2 mined — reward → Alice
[Balance] Alice: 14.9  Bob: 5.0
[Tamper] Modified block detected — chain is INVALID ✓
```

---

## 6. Running a Node

```bash
python run_node.py              # port 5000, difficulty 3
python run_node.py 5001         # port 5001, difficulty 3
python run_node.py 5001 4       # port 5001, difficulty 4
```

Each node writes its chain to its own `chain_<port>.db` file, so you can run multiple nodes on the same machine without them stepping on each other.

When a node starts, you'll see this:

```
  ╔═══════════════════════════════════════════════╗
  ║  Kryptika Node                                ║
  ╠═══════════════════════════════════════════════╣
  ║  Port       : 5000                            ║
  ║  Difficulty : 3                               ║
  ║  Database   : chain_5000.db                   ║
  ╠═══════════════════════════════════════════════╣
  ║  GET  /chain  /status  /peers  /peers/sync    ║
  ║  GET  /mine?address=<addr>                    ║
  ║  GET  /balance/<addr>  /history/<addr>        ║
  ║  GET  /transactions/pending  /wallet/new      ║
  ║  POST /peers/add  /peers/receive              ║
  ║  POST /transactions/new  /transactions/receive ║
  ╚═══════════════════════════════════════════════╝
```

> **Tip:** If you installed via `pip install -e .`, you can also use `kryptika-node` instead of `python run_node.py`.

---

## 7. Wallet CLI

The wallet CLI is your terminal interface for everything wallet-related — creating wallets, checking balances, sending coins, mining, and managing peers.

### Launching

```bash
python wallet_cli.py                    # scans ports 5000–5010 and lets you pick
python wallet_cli.py 5001               # connect directly to port 5001
python wallet_cli.py 192.168.1.5:5000   # connect to a node on another machine
```

### Picking a node

If you don't specify a port, the CLI scans for whatever nodes are already running and shows you a list:

```
  ╔════════════════════════════════════════════════════════╗
  ║  Kryptika Wallet CLI  -  Node Selection                ║
  ╠════════════════════════════════════════════════════════╣
  ║  Scanning for running nodes...                         ║
  ║                                                        ║
  ║  [1] localhost:5000   height=4  peers=1  mempool=0     ║
  ║  [2] localhost:5001   height=4  peers=1  mempool=2     ║
  ║                                                        ║
  ║  [c] Enter a custom address                            ║
  ║                                                        ║
  ║  Select node (Enter for [1]):                          ║
  ╚════════════════════════════════════════════════════════╝
```

### Menu

```
  ╔════════════════════════════════════════╗
  ║  Kryptika Wallet                       ║
  ╠════════════════════════════════════════╣
  ║  1. Create / load wallet               ║
  ║  2. Show balance                       ║
  ║  3. Send coins                         ║
  ║  4. Transaction history                ║
  ║  5. Mine a block                       ║
  ║  6. View pending transactions          ║
  ║  7. View the full chain                ║
  ║  8. Node status                        ║
  ║  9. Manage peers / multi-node          ║
  ║  0. Exit                               ║
  ╚════════════════════════════════════════╝
```

> ⚠️ **Heads up:** `wallets.json` stores your private keys in plain hex. Don't share this file and don't commit it to version control.

---

## 8. Multi-Node Network

### Setting up a 3-node network

Open three terminals from the project root and start a node in each:

```bash
# Terminal 1
python run_node.py 5000

# Terminal 2
python run_node.py 5001

# Terminal 3
python run_node.py 5002
```

### Connecting the nodes

```bash
python wallet_cli.py 5000
```

Go to **option 9 → Add a peer** and add the other two:

```
Add peer: localhost:5001    ← syncs and registers both ways
Add peer: localhost:5002    ← syncs and registers both ways
```

Then open the CLI on port 5001 and do the last connection:

```
Add peer: localhost:5002    ← all three nodes now know each other
```

Your network is now **fully meshed** — mine on any node and every other node sees the new block instantly.

### Recommended workflow

1. Mine a few blocks on port 5000 to get some coins in circulation.
2. Connect all three peers together.
3. Submit transactions from any node — they'll propagate automatically.
4. Mine from any node — the new block broadcasts to everyone.
5. All nodes settle on the same chain.

### How forks resolve

If two nodes happen to mine at the same height at the same time, a temporary fork forms. This is normal. As soon as any node mines the next block, it broadcasts a chain that's one block longer. Every other node sees it, validates it, and switches over. Forks self-heal in seconds.

> Transactions broadcast to one node's mempool immediately reach all peers. If a peer misses the initial broadcast, it picks up the transaction when the block syncs anyway.

---

## 9. REST API Reference

Every response is JSON. If something goes wrong, the response will have an `"error"` key explaining what happened.

### GET Endpoints

| Endpoint | Description | Response |
|---|---|---|
| `GET /chain` | Full chain as a JSON array | `[{"index": 0, ...}, ...]` |
| `GET /status` | Node health summary | `{"height": 4, "mempool": 1, ...}` |
| `GET /peers` | List of connected peers | `{"peers": ["localhost:5001"]}` |
| `GET /peers/sync` | Pull chains from all peers; adopt the longest | `{"replaced": true, "height": 5}` |
| `GET /mine?address=<addr>` | Mine pending transactions; send reward to `<addr>` | `{"index": 4, "miner_reward": 10.5}` |
| `GET /balance/<address>` | Confirmed coin balance for an address | `{"balance": 9.5}` |
| `GET /history/<address>` | All confirmed transactions for an address | `{"count": 3, "history": [...]}` |
| `GET /transactions/pending` | Transactions sitting in the mempool | `{"count": 1, "transactions": [...]}` |
| `GET /wallet/new` | Generate a fresh address (private key is not saved) | `{"address": "abc123..."}` |

### POST Endpoints

| Endpoint | Body | Description |
|---|---|---|
| `POST /peers/add` | `{"address": "localhost:5001"}` | Connect to another node |
| `POST /peers/receive` | `[{block}, ...]` | Accept a chain broadcast from a peer |
| `POST /transactions/new` | `{transaction dict}` | Submit a signed transaction |
| `POST /transactions/receive` | `{transaction dict}` | Accept a peer-broadcast transaction |

### curl Examples

```bash
# Check node status
curl http://localhost:5000/status

# Check a balance
curl http://localhost:5000/balance/<address>

# Mine a block (reward goes to your address)
curl "http://localhost:5000/mine?address=<your_address>"

# Submit a signed transaction
curl -X POST http://localhost:5000/transactions/new \
  -H "Content-Type: application/json" \
  -d '{"sender": "...", "recipient": "...", "amount": 5.0, "fee": 0.5, "signature": "...", "public_key": "..."}'

# Connect to another node
curl -X POST http://localhost:5000/peers/add \
  -H "Content-Type: application/json" \
  -d '{"address": "localhost:5001"}'

# Sync with all peers
curl http://localhost:5000/peers/sync
```

---

## 10. Running the Tests

Make sure your virtual environment is active, then run from the project root:

```bash
python tests/test_core.py        # 34 unit tests
python tests/test_storage.py     #  5 storage tests
python tests/test_network.py     # 13 integration tests
```

Or run everything at once with pytest:

```bash
pytest
```

All 52 tests should go green. The network tests spin up real HTTP servers on ports 5100–5114 and clean up after themselves, so they won't interfere with any nodes you have running.

### What's covered

**Core — 34 tests**
- Transaction creation, signing, and signature verification
- Tamper detection on signed transactions
- Coinbase transactions and mining rewards
- Block hashing and determinism
- Proof of Work enforcement and difficulty compliance
- Chain validation — tampered data, broken links, invalid signatures
- Balance calculation and fee accounting
- Replay attack prevention via `tx_id`
- Batch double-spend rejection inside `mine_block()`

**Storage — 5 tests**
- Full save/load round-trip with chain integrity verified
- Hash preservation across serialise / deserialise cycle
- Atomic overwrite — a new save fully replaces old data without corruption

**Network — 13 tests**
- All HTTP endpoints: chain, mine, balance, peers, transactions
- P2P broadcast — mine on one node, watch it show up on a connected peer
- Sync — a shorter chain adopts the longer one from a peer
- Threading — `/status` stays responsive while `/mine` is grinding through PoW

---

## 11. Architecture Notes

### Why PoW runs outside the node lock

When you call `/mine`, the Proof of Work computation happens before the lock is acquired. Only the final step — appending the block and saving to disk — is protected. This means `/status`, `/balance`, `/history`, and all read endpoints stay fast and responsive even when mining is in progress. If a peer pushes a longer chain while you're mid-mine, the block you were building gets quietly discarded instead of creating a conflict.

### Why amounts use Decimal arithmetic

Python's `float` type drifts. After enough transactions, `balance == expected_value` can return `False` even when the math is correct. Kryptika avoids this by rounding every coin value to exactly 8 decimal places using `decimal.Decimal` with `ROUND_HALF_UP` — the same precision model Bitcoin uses with satoshis.

### Why `wallets.json` is written atomically

When saving wallets, the code writes to a temporary `.tmp` file first, then calls `os.replace()`. On every platform, `os.replace()` is atomic — either the full file lands or nothing changes. A crash in the middle of writing can't leave you with a half-written, unreadable wallet file.

### Why the confirmed `tx_id` cache is incremental

`Node._confirmed_ids` is a set that grows with the chain rather than being rebuilt from scratch on every transaction check. When a block is mined, only its `tx_id`s get added. When a longer chain is adopted via sync, the set rebuilds once. This avoids an O(N×M) scan on every incoming transaction while keeping replay protection intact.

---

## 12. Security Model

Here's what Kryptika does and doesn't protect against:

| Property | How it's enforced |
|---|---|
| **Signature forgery** | ECDSA P-256 — you can't sign a transaction without the private key |
| **Tamper detection** | SHA-256 chain hashing — one changed byte breaks all downstream links |
| **Replay attacks** | `tx_id` is checked against both the confirmed chain and the mempool on every submission |
| **Mempool double-spend** | Effective balance = confirmed minus pending; checked before any transaction is queued |
| **Block double-spend** | `batch_spend` tracks cumulative spend per sender within each call to `mine_block()` |
| **Thread safety** | `RLock` protects all state mutations; PoW runs outside the lock so reads never block |
| **Disk integrity** | SQLite writes use explicit `BEGIN / COMMIT / ROLLBACK` — no partial saves |
| **Request flooding** | Incoming HTTP request bodies are hard-capped at 10 MB |

---

## 13. Known Limitations

Kryptika is built for learning, not production. Here's what it deliberately leaves out — and what a real system would do instead:

| What's missing | Why it matters |
|---|---|
| **No wallet encryption** | Private keys sit in `wallets.json` as plain hex. Real wallets encrypt keys at rest (BIP-38, AES with a password, etc.). |
| **No peer authentication** | Anyone who knows your IP can push a chain to `/peers/receive`. Production nodes verify and whitelist peers before accepting data. |
| **No Merkle tree** | Blocks store the full transaction list. Real blockchains use Merkle trees so you can prove a transaction is in a block without downloading the whole thing. |
| **No UTXO set** | Checking your balance means scanning every block from genesis. Bitcoin keeps a set of unspent outputs so lookups are constant-time instead. |
| **Fixed mining reward** | The reward is always 10 coins. Bitcoin halves it roughly every four years to limit total supply — Kryptika doesn't. |
| **No fee-priority queue** | Every pending transaction gets included in the next block regardless of fee size. Real mempools sort by fee and drop low-priority transactions when congested. |
| **localhost-only peer discovery** | The node listens on all interfaces, but the CLI only scans `localhost` ports automatically. To connect a remote node, you have to add it manually. |

---

## 14. License

Released under the **MIT License** — see the [`LICENSE`](LICENSE) file for details.

---

<div align="center">

Built with pure Python · No blockchain frameworks · No shortcuts

*Read the source. Break things. Learn how it works.*

</div>
