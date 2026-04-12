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
[![Version](https://img.shields.io/badge/Version-1.2.0-6C63FF?style=for-the-badge)](https://github.com/aryanap07/Kryptika)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)

</div>

---

## What is Kryptika?

Kryptika is a complete, working blockchain written entirely in pure Python. It covers the full stack — SHA-256 hashing, Proof of Work mining, ECDSA-signed transactions, live peer-to-peer networking, SQLite persistence, and a thread-safe HTTP node. Every primitive is hand-written and meant to be read.

It's for developers who want to stop wondering how blockchains work and just *see* it happen. Clone it, run it, break it, read the source.

---

## What's New in v1.2.0

- **Streamlit Dashboard** — a browser-based GUI covering everything the CLI can do, plus live Plotly charts and a visual chain explorer. Launch it with `streamlit run dashboard.py`.
- **Transaction Notes** — every transaction now accepts an optional `note` field. Notes are included in the ECDSA signature, so they're tamper-evident, not just cosmetic.
- **Wallet Import** — restore any existing wallet from its private key hex using `Wallet.from_private_key()`, available in both the dashboard and the CLI.
- **Node Uptime** — the `/status` endpoint now includes `uptime_secs`, so you can see how long a node has been running.

---

## Table of Contents

1. [Features](#1-features)
2. [How It Works](#2-how-it-works)
3. [Project Structure](#3-project-structure)
4. [Installation](#4-installation)
5. [Quick Start](#5-quick-start)
6. [Running a Node](#6-running-a-node)
7. [Streamlit Dashboard](#7-streamlit-dashboard)
8. [Wallet CLI](#8-wallet-cli)
9. [Multi-Node Network](#9-multi-node-network)
10. [REST API Reference](#10-rest-api-reference)
11. [Running the Tests](#11-running-the-tests)
12. [Architecture Notes](#12-architecture-notes)
13. [Security Model](#13-security-model)
14. [Known Limitations](#14-known-limitations)
15. [License](#15-license)

---

## 1. Features

Kryptika implements the core ideas behind real blockchains — nothing simulated, nothing mocked out.

| Area | What's included |
|---|---|
| **Chain** | SHA-256 block hashing, tamper-evident linking, deterministic genesis block |
| **Mining** | Proof of Work with configurable difficulty; 10 KRY base reward plus transaction fees |
| **Wallets** | ECDSA P-256 key pairs, address derivation via SHA-256, wallet import from private key |
| **Transactions** | Cryptographic signatures, replay protection via `tx_id`, 8-decimal precision, optional notes |
| **Network** | P2P broadcast, longest-chain consensus, full REST API with CORS, node uptime reporting |
| **Dashboard** | Streamlit GUI with live charts, multi-wallet manager, chain explorer, and chain validator |
| **Safety** | Mempool balance checks, per-block double-spend tracking, thread-safe node with non-blocking reads |
| **Storage** | SQLite with atomic `BEGIN / COMMIT / ROLLBACK`; each node keeps its own database file |

---

## 2. How It Works

### Blocks and the Chain

Every block contains a list of transactions, a timestamp, a nonce, and the hash of the block before it. Change even a single byte anywhere and the hash changes — breaking every link that follows it. Tampering is immediately detectable.

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

To add a block, a miner must find a `nonce` value that makes the block's SHA-256 hash start with a specific number of leading zeros. There's no shortcut — it requires thousands of attempts. That's the point. Rewriting history would mean redoing all that computation, which is what makes the chain trustworthy.

```python
# Conceptual example — difficulty 3
while not block_hash.startswith("000"):
    block.nonce += 1
    block_hash = sha256(block)
```

> Each extra leading zero requires roughly 16× more hashes — difficulty scales exponentially.

### Wallets and Addresses

A wallet is an ECDSA P-256 key pair. Your address is simply a SHA-256 hash of your public key — safe to share with anyone. Your private key stays on your machine; it's what you use to prove that you authorised a transaction.

```
Private key  ──(ECDSA P-256)──→  Public key  ──(SHA-256)──→  Address
  SECRET — never share              shareable                  shareable
```

### Transactions

When you send coins, you sign a payload containing the sender, recipient, amount, fee, and an optional note. That signature gets broadcast to the network alongside the transaction. Every node verifies it against your public key — without ever needing your private key.

```
{ sender, recipient, amount, fee, note }  +  private key
                         │
                    ECDSA P-256
                         │
                    signature ──→ broadcast to all nodes
                                        │
                              node verifies with public key ✓
```

Because the `note` field is part of the signed payload, it's cryptographically protected — anyone who alters a note after the transaction is signed will invalidate the signature.

### The Mempool

Before a transaction lands on the chain, it waits in the **mempool** — a queue of unconfirmed transactions. Miners pick them up and bundle them into the next block. The miner earns the base reward plus every fee in that block, so transactions with higher fees tend to confirm faster.

```
Mempool:  [alice→bob 5.0 | fee: 0.5]  [bob→carol 2.0 | fee: 0.5]  [carol→dave 1.0 | fee: 0.5]
                                    ↓  miner picks up & mines
                         Block mined → miner earns 10 KRY base + 1.5 KRY in fees
```

### Consensus — Longest Chain Wins

Sometimes two nodes mine a block at exactly the same moment. That creates a fork — two valid but competing chains. Kryptika resolves it the same way Bitcoin does: the longest valid chain wins. As soon as any node mines the next block, it broadcasts a chain that's one block longer. Every other node sees it, validates it, and switches over automatically. No votes, no manual intervention — forks self-heal in seconds.

```
Fork:
  Node A: [0]──[1]──[2]──[3a]          ← tied
  Node B: [0]──[1]──[2]──[3b]          ← tied

Node A mines next:
  Node A: [0]──[1]──[2]──[3a]──[4]     ← broadcasts; wins (longer chain)
  Node B: [0]──[1]──[2]──[3a]──[4]     ← drops [3b], adopts A's chain
```

---

## 3. Project Structure

```
kryptika/                       ← project root — run all commands from here
│
├── run_node.py                 ← start a blockchain node
├── wallet_cli.py               ← interactive terminal wallet
├── dashboard.py                ← Streamlit browser dashboard (new in v1.2.0)
├── pyproject.toml              ← package metadata and entry points
├── LICENSE
│
├── kryptika/                   ← main Python package
│   ├── core/
│   │   ├── transaction.py      ← Wallet (keygen, sign, import) + Transaction (create, verify, notes)
│   │   ├── block.py            ← Block (hash, nonce, serialisation)
│   │   └── blockchain.py       ← Blockchain (mine, validate, balance, history)
│   │
│   ├── network/
│   │   ├── node.py             ← Node (mempool, broadcast, sync — thread-safe)
│   │   └── server.py           ← HTTP REST server (all endpoints)
│   │
│   ├── storage/
│   │   └── storage.py          ← SQLiteStorage (atomic save + load + migration)
│   │
│   └── main.py                 ← standalone demo script
│
└── tests/
    ├── test_core.py            ← 34 unit tests
    ├── test_storage.py         ←  5 storage tests
    └── test_network.py         ← 13 integration tests
```

---

## 4. Installation

You'll need **Python 3.10 or newer**.

It's strongly recommended to work inside a virtual environment so Kryptika's dependencies don't interfere with anything else on your machine.

```bash
# Create and activate a virtual environment
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows — Command Prompt
.venv\Scripts\activate.bat

# Windows — PowerShell
.venv\Scripts\Activate.ps1
```

Then install Kryptika and all its dependencies in one step:

```bash
pip install -e .
```

This installs the `cryptography`, `requests`, `streamlit`, and `plotly` packages automatically, and also registers the `kryptika-node` command so you can start nodes without typing `python run_node.py` every time.

**If you'd rather not install as a package**, you can install the dependencies manually:

```bash
pip install "cryptography>=41.0" "requests>=2.31" "streamlit>=1.35" "plotly>=5.20"
```

Then run everything with `python run_node.py`, `python wallet_cli.py`, etc.

---

## 5. Quick Start

Don't want to spin up a server yet? This single command runs the full blockchain lifecycle — key generation, mining, transactions, and tamper detection — entirely in memory:

```bash
python -m kryptika.main
```

It creates wallets for Alice, Bob, and Carol; mines a few blocks; sends signed transactions between them; and then deliberately corrupts a block to show the chain catching the tampering. You'll see output like this:

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

This is the fastest way to verify that everything is working before you run a real node.

---

## 6. Running a Node

A node is the core of Kryptika — it maintains the chain, validates transactions, mines blocks, and communicates with peers over HTTP.

```bash
python run_node.py              # starts on port 5000 with difficulty 3
python run_node.py 5001         # starts on port 5001 with difficulty 3
python run_node.py 5001 4       # starts on port 5001 with difficulty 4
```

Each node stores its chain in a dedicated SQLite file (`chain_5000.db`, `chain_5001.db`, etc.), so you can run multiple nodes on the same machine without any conflicts.

On startup you'll see a summary of the node's configuration and available endpoints:

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

> If you installed via `pip install -e .`, you can use `kryptika-node` as a shorthand for `python run_node.py`.

---

## 7. Streamlit Dashboard

The dashboard is a browser-based GUI that connects to a running node over HTTP. It covers everything the CLI can do — wallets, sending, mining, peer management — plus live charts and a visual block explorer.

### Starting the dashboard

You need a node running first. Then open a second terminal and run:

```bash
# Terminal 1 — the node
python run_node.py 5000

# Terminal 2 — the dashboard
streamlit run dashboard.py
```

Streamlit will open `http://localhost:8501` in your browser automatically.

### Switching nodes

The sidebar has a **Connected Node** selector with presets for ports 5000, 5001, and 5002. Choose **custom...** to type any host and port — the dashboard verifies the connection before switching. Your current node's chain height, mempool count, and peer count are shown live beneath the selector.

### Pages at a glance

| Page | What you can do |
|---|---|
| **Overview** | See live stats (height, mempool, peers, uptime) and Plotly charts showing transactions per block and time between blocks. Scroll down for a live activity feed. |
| **Chain Explorer** | Browse every block on the chain. Search by block index or hash fragment. Expand any block to inspect its hashes, nonce, timestamp, and every transaction including notes. |
| **Mempool** | View all unconfirmed transactions waiting to be mined, with total pending volume and fee totals. |
| **Wallet** | Manage all your wallets in one place. Create a new keypair, import an existing wallet with its private key, check balances, set a default wallet, or view a full transaction history with a running balance for any address. |
| **Send** | Build and broadcast a transaction. Pick your sending wallet, enter a recipient address, amount, fee, and an optional note. A live summary panel updates your remaining balance as you type. |
| **Mine** | Choose which wallet receives the mining reward, then start mining. The result panel shows the block index, nonce that was found, how many transactions were confirmed, and the total reward earned. |
| **Peers** | See all connected nodes, add a new peer (the dashboard attempts a mutual handshake automatically), or trigger a sync to pull the longest chain from all peers. |
| **Chain Validator** | Fetch the full chain from the node and verify every block — hash linkage, proof-of-work compliance, and transaction signatures. Any tampered block is flagged with a specific error. |

### Auto-refresh

Toggle **Auto** in the sidebar to have the dashboard reload itself every 5 seconds. This is useful for monitoring a live network or watching blocks come in during a mining session.

> ⚠️ `wallets.json` stores private keys as plain hex on disk. The dashboard and the CLI share this same file, so wallets created in one are immediately available in the other. Never commit this file to version control or share it with anyone.

---

## 8. Wallet CLI

The wallet CLI is the terminal alternative to the dashboard. It connects directly to a running node and gives you a menu-driven interface for all the same operations.

### Connecting

```bash
python wallet_cli.py                    # auto-scans ports 5000–5010 and shows a list
python wallet_cli.py 5001               # connect directly to port 5001
python wallet_cli.py 192.168.1.5:5000   # connect to a node on another machine
```

If you don't pass a port, the CLI scans localhost automatically and presents whatever nodes it finds:

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

### Main menu

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

When you choose **Send** (option 3), the CLI will prompt for an optional note. If you skip it, the note defaults to `"<sender> -> <recipient>"`. Whatever you enter is included in the transaction signature.

---

## 9. Multi-Node Network

Running multiple nodes lets you see Kryptika's consensus and P2P broadcast in action. Blocks mined on one node propagate to all peers instantly; forks resolve automatically.

### Setting up three nodes

Open three terminals and start a node in each:

```bash
# Terminal 1
python run_node.py 5000

# Terminal 2
python run_node.py 5001

# Terminal 3
python run_node.py 5002
```

### Connecting them

Connect the nodes using the CLI or the dashboard's **Peers** page. Here's how to do it from the CLI:

```bash
# From a fourth terminal, connect to node 5000
python wallet_cli.py 5000
```

Choose **option 9 → Add a peer** and add the other two nodes:

```
Add peer: localhost:5001    ← both nodes register each other automatically
Add peer: localhost:5002    ← same mutual handshake
```

Then do the same from node 5001 to connect it to 5002:

```bash
python wallet_cli.py 5001
# option 9 → Add peer → localhost:5002
```

All three nodes now know each other — the network is fully meshed. Mine on any node and every other node receives the new block immediately.

### Suggested workflow for exploring the network

1. Mine a few blocks on port 5000 to put some coins into circulation.
2. Connect all three nodes to each other as described above.
3. Submit transactions from any node — they appear in every node's mempool automatically.
4. Mine from any node — the block propagates and is accepted by all peers.
5. Watch all nodes converge on the same chain height via `/status` or the dashboard Overview page.

### How forks resolve

If two nodes mine a block at the same height simultaneously, each broadcasts its version to the network. Both chains are temporarily valid and tied. As soon as either node mines the *next* block, it broadcasts a chain that's one block longer. Every other node sees it, validates it, and switches over — dropping the shorter fork. The whole process takes seconds and requires no human intervention.

> A transaction broadcast to one node's mempool reaches all connected peers immediately. If a peer was offline and missed the broadcast, it picks up the transaction anyway when the next block syncs.

---

## 10. REST API Reference

Every endpoint responds with JSON. If a request fails, the response will include an `"error"` key with a plain-English explanation of what went wrong.

### GET endpoints

| Endpoint | What it does | Example response |
|---|---|---|
| `GET /chain` | Returns the full chain as an array of blocks | `[{"index": 0, ...}, ...]` |
| `GET /status` | Node health — height, mempool size, peer count, difficulty, and uptime | `{"height": 4, "mempool": 1, "uptime_secs": 312.4, ...}` |
| `GET /peers` | Lists all connected peer addresses | `{"peers": ["localhost:5001"]}` |
| `GET /peers/sync` | Pulls chains from every peer; adopts the longest valid one | `{"replaced": true, "height": 5}` |
| `GET /mine?address=<addr>` | Mines a block and sends the reward to `<addr>` | `{"index": 4, "miner_reward": 10.5}` |
| `GET /balance/<address>` | Returns the confirmed balance for an address | `{"balance": 9.5}` |
| `GET /history/<address>` | All confirmed transactions involving an address | `{"count": 3, "history": [...]}` |
| `GET /transactions/pending` | All transactions currently in the mempool | `{"count": 1, "transactions": [...]}` |
| `GET /wallet/new` | Generates a fresh address on the node (private key is not stored) | `{"address": "abc123..."}` |

### POST endpoints

| Endpoint | Body | What it does |
|---|---|---|
| `POST /peers/add` | `{"address": "localhost:5001"}` | Registers a peer and attempts to sync |
| `POST /peers/receive` | `[{block}, ...]` | Accepts an incoming chain broadcast from a peer |
| `POST /transactions/new` | Transaction object (see below) | Validates and adds a signed transaction to the mempool |
| `POST /transactions/receive` | Transaction object | Accepts a transaction forwarded by a peer |

### Transaction format

The `note` field was added in v1.2.0. It's optional — omit it or pass `""` and it will be treated as empty.

```json
{
  "sender":     "<64-char hex address>",
  "recipient":  "<64-char hex address>",
  "amount":     5.0,
  "fee":        0.5,
  "note":       "optional label — signed alongside the rest of the fields",
  "signature":  "<hex>",
  "public_key": "<hex>",
  "tx_id":      "<hex>"
}
```

### curl examples

```bash
# Check node status
curl http://localhost:5000/status

# Check a wallet balance
curl http://localhost:5000/balance/<address>

# Mine a block (reward goes to your address)
curl "http://localhost:5000/mine?address=<your_address>"

# Submit a signed transaction
curl -X POST http://localhost:5000/transactions/new \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "...",
    "recipient": "...",
    "amount": 5.0,
    "fee": 0.5,
    "note": "payment for services",
    "signature": "...",
    "public_key": "..."
  }'

# Connect to another node
curl -X POST http://localhost:5000/peers/add \
  -H "Content-Type: application/json" \
  -d '{"address": "localhost:5001"}'

# Sync with all peers
curl http://localhost:5000/peers/sync
```

---

## 11. Running the Tests

Make sure your virtual environment is active and you're in the project root, then run:

```bash
python tests/test_core.py        # 34 unit tests — blockchain primitives
python tests/test_storage.py     #  5 unit tests — SQLite persistence
python tests/test_network.py     # 13 integration tests — live HTTP servers
```

Or run all 52 at once with pytest:

```bash
pytest
```

All 52 tests should pass. The network tests spin up real HTTP servers on ports 5100–5114 and shut them down cleanly after each test, so they won't interfere with any nodes you have running.

### What each suite covers

**Core (34 tests)** — Transaction creation, signing, and signature verification. Tamper detection. Coinbase transactions and mining rewards. Block hashing and determinism. Proof of Work enforcement. Chain validation across tampered data, broken links, and invalid signatures. Balance calculation with fee accounting. Replay attack prevention via `tx_id`. Batch double-spend rejection inside `mine_block()`.

**Storage (5 tests)** — Full save/load round-trip with chain integrity verified after reload. Hash preservation through serialise/deserialise cycles. Atomic overwrite — a new save fully replaces old data without any risk of corruption.

**Network (13 tests)** — All HTTP endpoints: chain, mine, balance, peers, and transactions. P2P broadcast — mine on one node, confirm the block appears on a connected peer. Chain sync — a shorter-chain node correctly adopts a longer chain from a peer. Threading — `/status` stays responsive while `/mine` is grinding through Proof of Work.

---

## 12. Architecture Notes

This section explains a handful of design decisions that might seem subtle at first. Each one has a concrete reason behind it.

### Why Proof of Work runs outside the node lock

When you call `/mine`, the hash-grinding loop runs *before* the node acquires its `RLock`. Only the very last step — appending the new block and writing to disk — is done inside the lock. This means `/status`, `/balance`, `/history`, and every other read endpoint stay fully responsive while a mine is in progress. It also means that if a peer broadcasts a longer chain while you're mid-computation, the block you were working on gets quietly discarded rather than triggering a conflict.

### Why coin amounts use Decimal arithmetic

Python's native `float` type accumulates rounding errors. After enough transactions, a comparison like `balance == expected` can silently return `False` even when the math is correct. Kryptika avoids this by representing every coin value as `decimal.Decimal` rounded to exactly 8 places using `ROUND_HALF_UP` — the same precision model Bitcoin uses for satoshis.

### Why `wallets.json` is written atomically

The wallet file is never overwritten directly. Instead, the code writes to a temporary `.tmp` file and then calls `os.replace()` to swap it into place. On every operating system, `os.replace()` is atomic — either the complete new file lands or nothing changes. A crash mid-write cannot leave you with a half-written, unreadable wallet file. Because the dashboard and the CLI both use this same file, a wallet created in one appears in the other immediately.

### Why the confirmed `tx_id` cache grows incrementally

`Node._confirmed_ids` is a set that accumulates `tx_id` values as blocks are mined, rather than being rebuilt by scanning the entire chain on every incoming transaction. When a block is added, only its transaction IDs are appended. When a longer chain is adopted via sync, the set rebuilds once from scratch. This keeps replay-attack checks at O(1) lookup cost instead of O(N × M) on every submission.

### Why transaction notes are part of the signature

The `note` field is serialised into the transaction payload before signing. This means the ECDSA signature covers the note as well as the financial fields. If anyone modifies a note after the transaction is broadcast, the signature becomes invalid and every node rejects the transaction. Notes are read-only once signed.

---

## 13. Security Model

| What's protected | How |
|---|---|
| **Signature forgery** | ECDSA P-256 — a transaction cannot be signed without the sender's private key |
| **Tamper detection** | SHA-256 chain hashing — altering any byte in any block breaks every hash that follows |
| **Replay attacks** | Every `tx_id` is unique and checked against both the confirmed chain and the live mempool before a transaction is accepted |
| **Mempool double-spend** | Before queuing a transaction, the node calculates effective balance as confirmed balance minus all pending outgoing amounts |
| **Block double-spend** | `mine_block()` tracks cumulative spend per sender within a single mining call, rejecting any transaction that would exceed the sender's remaining balance |
| **Thread safety** | An `RLock` protects all state mutations; Proof of Work runs outside the lock so read endpoints never block |
| **Disk integrity** | All SQLite writes use explicit `BEGIN / COMMIT / ROLLBACK` — a crash mid-write leaves the previous state intact |
| **Request flooding** | Incoming HTTP request bodies are hard-capped at 10 MB |
| **Note integrity** | Transaction notes are covered by the ECDSA signature — they cannot be altered after signing |

---

## 14. Known Limitations

Kryptika is designed for learning, not production. It deliberately leaves out several things that a real blockchain would require. Here's what's missing and why it matters:

| What's missing | What a real system would do |
|---|---|
| **No wallet encryption** | Private keys are stored as plain hex in `wallets.json`. A production wallet encrypts keys at rest using a password (BIP-38, AES, or similar). |
| **No peer authentication** | Any host that knows your IP can push a chain to `/peers/receive`. Real nodes authenticate peers and only accept data from whitelisted addresses. |
| **No Merkle tree** | Blocks hold the full transaction list. Real blockchains use a Merkle tree so a single transaction's inclusion can be proven without downloading the whole block. |
| **No UTXO set** | Balance checks scan every block from genesis. Bitcoin maintains a set of unspent transaction outputs so balance lookups take constant time regardless of chain length. |
| **Fixed mining reward** | The reward is always 10 KRY. Bitcoin cuts it in half roughly every four years to cap the total supply — Kryptika has no halving schedule. |
| **No fee-priority ordering** | The mempool includes transactions in the order they arrive. Real mempools rank pending transactions by fee and drop the lowest-fee ones when congested. |
| **Local-only peer discovery** | The CLI scans `localhost` automatically. Remote nodes have to be added by hand via the CLI or dashboard. |
| **Dashboard requires a running node** | The Streamlit dashboard is a pure REST client with no blockchain logic of its own. At least one node must be running before you open the dashboard. |

---

## 15. License

Released under the **MIT License** — see the [`LICENSE`](LICENSE) file for the full text.

---

<div align="center">

Built with pure Python · No blockchain frameworks · No shortcuts

*Read the source. Break things. Learn how it works.*

</div>