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

*Blockchain, stripped to its essence in Python.*

<br/>

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

- **Streamlit Dashboard** — a browser-based GUI covering everything the CLI can do, plus live Plotly charts and a visual chain explorer. Launch with `streamlit run dashboard.py`.
- **Transaction Notes** — every transaction now accepts an optional `note` field, stored alongside the transaction and visible in the dashboard, CLI, and history API.
- **Wallet Import** — restore any existing wallet from its PKCS8 DER private key hex using `Wallet.from_private_key()`, available in both the dashboard and the CLI.
- **Node Uptime** — the `/status` endpoint now includes `uptime_secs`, so you can see exactly how long a node has been running.
- **Persistent Mempool** — pending transactions survive a node restart; they are written to the `mempool` table in SQLite and reloaded on startup, filtering out any that were confirmed while the node was offline.

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
| **Mining** | Proof of Work with configurable difficulty; 10 KRY base reward plus collected transaction fees |
| **Wallets** | ECDSA P-256 key pairs, address derivation via SHA-256, wallet import from private key hex |
| **Transactions** | Cryptographic signatures, replay protection via `tx_id`, 8-decimal-place precision, optional notes |
| **Network** | P2P broadcast, longest-chain consensus, mempool sync across peers, full REST API with CORS |
| **Dashboard** | Streamlit GUI with live Plotly charts, multi-wallet manager, chain explorer, and chain validator |
| **Safety** | Effective-balance mempool checks, per-batch double-spend tracking in `mine_block()`, O(1) replay detection |
| **Storage** | SQLite with atomic `BEGIN / COMMIT / ROLLBACK`; separate database file per node; schema migration for older databases |
| **CI** | GitHub Actions pipeline across Python 3.10, 3.11, 3.12, and 3.13 with `ruff` linting |

---

## 2. How It Works

### Blocks and the Chain

Every block contains a list of transactions, a timestamp, a nonce, and the hash of the block before it. Change even a single byte anywhere and the block's SHA-256 hash changes — which breaks every chain link that follows it. Tampering is immediately detectable.

Block `0` is the **genesis block** — always empty, always mined identically. Every block after it locks onto the previous block's hash, forming a chain that can't be quietly rewritten.

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Block 0         │     │  Block 1         │     │  Block 2         │
│  (Genesis)       │────→│                  │────→│                  │
│  prev: 000000    │     │  prev: 000a1b2c  │     │  prev: 000f3d9a  │
│  hash: 000a1b2c  │     │  hash: 000f3d9a  │     │  hash: 000c77e1  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

The hash covers five fields — `index`, `transactions`, `prev_hash`, `timestamp`, and `nonce` — serialised with `json.dumps(..., sort_keys=True)` to guarantee determinism across Python versions and platforms.

### Proof of Work

To add a block, a miner must find a `nonce` value that makes the block's SHA-256 hash start with a specific number of leading zeros (the *difficulty*). There's no shortcut — it requires thousands of hash attempts. That's the point. Rewriting history would mean redoing all that computation for every block that follows, which is what makes the chain trustworthy.

```python
# Simplified — difficulty 3 means the hash must start with "000"
while not block_hash.startswith("000"):
    block.nonce += 1
    block_hash = sha256(block)
```

> Each extra leading zero requires roughly 16× more hash attempts on average — difficulty scales exponentially.

### Wallets and Addresses

A wallet is an ECDSA P-256 key pair. The address is the SHA-256 hash of the uncompressed public key point (65 bytes → 64 hex characters), and it's safe to share with anyone. The private key stays on your machine; it's what proves you authorised a transaction.

```
Private key  ──(ECDSA P-256)──→  Public key (65 bytes)  ──(SHA-256)──→  Address (64 hex chars)
  SECRET — never share                  shareable                              shareable
```

Signatures are stored as raw `r‖s` (64 bytes, 128 hex characters). The private key is serialised as PKCS8 DER hex — raw P-256 DER raises a `ValueError` in the `cryptography` library.

### Transactions

When you send coins, you sign a payload containing the sender, recipient, amount, and fee. That signature is broadcast alongside the transaction. Every node verifies it against your embedded public key — without ever needing your private key.

```
{ sender, recipient, amount, fee }  +  private key
                    │
               ECDSA P-256 / SHA-256
                    │
               signature (128 hex chars)
                    │
          broadcast with public_key embedded
                    │
          node verifies with embedded public key ✓
```

The `note` field is stored alongside the transaction and visible in history and the dashboard, but it is **not** part of the signed payload — it is informational metadata.

A `tx_id` is computed as `SHA-256({sender, recipient, amount, fee, signature})` and is unique per transaction because ECDSA signing is randomised, even for identical inputs.

### The Mempool

Before a transaction lands on the chain, it waits in the **mempool** — a queue of unconfirmed transactions persisted to SQLite. Miners bundle the full mempool into the next block. The miner earns the base reward plus every fee in that block, so transactions with higher fees naturally confirm faster.

```
Mempool:  [alice→bob 5.0 | fee: 0.5]  [bob→carol 2.0 | fee: 0.5]  [carol→dave 1.0 | fee: 0.5]
                                    ↓  miner mines
                     Block confirmed → miner earns 10 KRY base + 1.5 KRY in fees = 11.5 KRY
```

When a node accepts a new transaction it checks four things in order: reject COINBASE sender → verify ECDSA signature → reject duplicate `tx_id` (against both mempool and confirmed chain) → effective balance ≥ amount + fee after subtracting all already-pending spend.

### Consensus — Longest Chain Wins

Sometimes two nodes mine a block at exactly the same moment. That creates a fork — two valid but competing chains. Kryptika resolves it the same way Bitcoin does: the longest valid chain wins. As soon as any node mines the next block, it broadcasts a chain one block longer. Every other node validates it and switches over automatically. No votes, no manual intervention — forks self-heal in seconds.

```
Fork:
  Node A: [0]──[1]──[2]──[3a]          ← tied
  Node B: [0]──[1]──[2]──[3b]          ← tied

Node A mines next:
  Node A: [0]──[1]──[2]──[3a]──[4]     ← broadcasts; wins (longer valid chain)
  Node B: [0]──[1]──[2]──[3a]──[4]     ← drops [3b], adopts A's chain
```

`sync_with_peers()` does two things in sequence: first it finds and adopts the longest valid chain across all known peers; then it absorbs any pending transactions from peer mempools, so unconfirmed transactions propagate even when chain heights are equal.

---

## 3. Project Structure

```
kryptika/                       ← project root — run all commands from here
│
├── run_node.py                 ← start a blockchain node
├── wallet_cli.py               ← interactive terminal wallet
├── dashboard.py                ← Streamlit browser dashboard (new in v1.2.0)
├── pyproject.toml              ← package metadata, dependencies, entry points
├── LICENSE                     ← MIT
│
├── kryptika/                   ← main Python package
│   ├── core/
│   │   ├── transaction.py      ← Wallet (keygen, sign, import) + Transaction (create, verify)
│   │   ├── block.py            ← Block (SHA-256 hash, nonce, serialisation)
│   │   └── blockchain.py       ← Blockchain (mine, validate, balance, history)
│   │
│   ├── network/
│   │   ├── node.py             ← Node (mempool, broadcast, sync — thread-safe RLock)
│   │   └── server.py           ← ThreadingHTTPServer JSON REST API (all 13 endpoints)
│   │
│   ├── storage/
│   │   └── storage.py          ← SQLiteStorage (atomic save/load, schema migration)
│   │
│   └── main.py                 ← standalone demo script
│
└── tests/
    ├── test_core.py            ← 34 unit tests
    ├── test_storage.py         ←  5 storage tests
    └── test_network.py         ← 13 integration tests  (52 total)
```

---

## 4. Installation

You'll need **Python 3.10 or newer**.

Working inside a virtual environment is strongly recommended so Kryptika's dependencies don't interfere with anything else on your machine.

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

This installs `cryptography`, `requests`, `streamlit`, and `plotly` automatically, and registers the `kryptika-node` command on your PATH so you can start nodes without typing `python run_node.py` every time.

**If you'd rather not install as a package**, install the dependencies manually and run scripts directly:

```bash
pip install "cryptography>=41.0" "requests>=2.31" "streamlit>=1.35" "plotly>=5.20"

python run_node.py
python wallet_cli.py
streamlit run dashboard.py
```

---

## 5. Quick Start

Don't want to spin up a server yet? This single command runs the full blockchain lifecycle — key generation, mining, signed transactions, balance tracking, and tamper detection — entirely in memory:

```bash
python -m kryptika.main
```

It creates wallets for Alice, Bob, and Carol; mines several blocks; sends signed transactions between them; prints final balances; validates the full chain; and then deliberately tampers with a block to show detection in action:

```
========================================================
  Kryptika Demo
========================================================

[1] Creating wallets...
  Alice : 3f9a2b1c...
  Bob   : 7d4e8f0a...
  Carol : c2e91f33...

[2] Initialising blockchain (difficulty=2)...
  Genesis block mined.  Height=1

[3] Mining reward blocks...
  Block mined -> Alice earns 10.0 coins.  Height=2
  Block mined -> Alice earns 10.0 coins.  Height=3

[5] Alice sends 7 coins to Bob (fee=0.5)...
[7] Validating chain...
  Chain valid : True

[8] Tamper test -- modifying a transaction amount...
  Chain valid after tamper : False
  Reason                   : Block #1 has been tampered with — stored hash does not match computed hash.
```

This is the fastest way to verify everything is working before you run a real node.

---

## 6. Running a Node

A node maintains the chain, validates transactions, mines blocks, and communicates with peers over HTTP. Each node writes its chain to a dedicated SQLite file (`chain_5000.db`, `chain_5001.db`, etc.), so multiple nodes on the same machine stay completely independent.

```bash
python run_node.py              # port 5000, difficulty 3
python run_node.py 5001         # port 5001, difficulty 3
python run_node.py 5001 4       # port 5001, difficulty 4
```

If you installed via `pip install -e .`, the registered entry point works identically:

```bash
kryptika-node                   # port 5000, difficulty 3
kryptika-node 5001 4            # port 5001, difficulty 4
```

On startup the node prints its configuration and every available endpoint:

```
  ┌─────────────────────────────────────────────────┐
  │                                                 │
  │    Kryptika Node                                │
  │                                                 │
  ├─────────────────────────────────────────────────┤
  │    Port       : 5000                            │
  │    Difficulty : 3                               │
  │    Database   : chain_5000.db                   │
  ├─────────────────────────────────────────────────┤
  │    GET  /chain  /status  /peers  /peers/sync    │
  │    GET  /mine?address=<addr>                    │
  │    GET  /balance/<addr>  /history/<addr>        │
  │    GET  /transactions/pending  /wallet/new      │
  │    POST /peers/add  /peers/receive              │
  │    POST /transactions/new  /transactions/receive│
  └─────────────────────────────────────────────────┘
  Press Ctrl+C to stop.
```

If a `chain_<port>.db` file already exists, the node resumes from it and prints the current height. If not, it mines the genesis block and saves it before accepting any connections.

---

## 7. Streamlit Dashboard

The dashboard is a browser-based GUI that connects to any running node over HTTP. It covers everything the CLI can do — wallets, sending, mining, peer management — plus live Plotly charts and a full block explorer.

### Starting

You need at least one node running first. Then open a second terminal:

```bash
# Terminal 1 — the node
python run_node.py 5000

# Terminal 2 — the dashboard
streamlit run dashboard.py
```

Streamlit opens `http://localhost:8501` in your browser automatically.

### Switching nodes

The sidebar has a **Connected Node** selector with presets for ports 5000, 5001, and 5002. Choose **custom...** to type any host and port — the dashboard verifies the connection before switching. Chain height, mempool count, and peer count update live beneath the selector.

### Pages

| Page | What you can do |
|---|---|
| **Overview** | Live stats (height, mempool, peers, uptime) and Plotly charts showing transactions per block and time between blocks. Scroll down for a live activity feed. |
| **Chain Explorer** | Browse every block on the chain. Search by block index or hash fragment. Expand any block to inspect its hashes, nonce, timestamp, and every transaction including notes. |
| **Mempool** | View all unconfirmed transactions waiting to be mined, with total pending volume and fee totals. |
| **Wallet** | Create a new keypair, import an existing wallet by private key hex, check balances, set a default wallet, and view a full transaction history with running balance for any address. |
| **Send** | Build and broadcast a transaction. Pick a sending wallet, enter a recipient address, amount, fee, and an optional note. A live summary panel updates your remaining balance as you type. |
| **Mine** | Choose which wallet receives the mining reward, then start mining. The result panel shows the block index, the winning nonce, how many transactions were confirmed, and the total reward earned. |
| **Peers** | See all connected nodes, add a new peer (the dashboard attempts a mutual handshake automatically), or trigger a sync to pull the longest chain from all peers. |
| **Chain Validator** | Fetch the full chain from the node and verify every block — hash linkage, Proof of Work compliance, and transaction signatures. Any tampered block is flagged with a specific error. |

### Auto-refresh

Toggle **Auto** in the sidebar to reload the dashboard every 5 seconds — useful for monitoring a live network or watching blocks arrive during a mining session.

> ⚠️ `wallets.json` stores private keys as plain hex on disk. The dashboard and the CLI share this same file, so wallets created in one are immediately available in the other. Never commit this file to version control or share it with anyone.

---

## 8. Wallet CLI

The wallet CLI is the terminal alternative to the dashboard. It connects directly to a running node and provides a menu-driven interface for every operation.

### Connecting

```bash
python wallet_cli.py                    # auto-scans ports 5000–5010, shows found nodes
python wallet_cli.py 5001               # connect directly to localhost:5001
python wallet_cli.py 192.168.1.5:5000   # connect to a node on another machine
```

If you don't pass a port, the CLI scans localhost automatically and presents whatever nodes it finds:

```
  ══════════════════════════════════════════════════════════
    Kryptika Wallet CLI  --  Node Selection
  ══════════════════════════════════════════════════════════
  Scanning for running nodes...

  [1] localhost:5000   height=4  peers=1  mempool=0
  [2] localhost:5001   height=4  peers=1  mempool=2

  [c] Enter a custom address

  Select node (Enter for [1]):
```

### Main menu

```
  ════════════════════════════════════════
    Kryptika Wallet
  ════════════════════════════════════════
    1. Create / load wallet
    2. Show balance
    3. Send coins
    4. Transaction history
    5. Mine a block
    6. View pending transactions
    7. View the full chain
    8. Node status
    9. Manage peers / multi-node
    0. Exit
  ════════════════════════════════════════
```

Wallets are saved to `wallets.json` and persist between sessions. When you choose **Send** (option 3), you'll be prompted for an optional note — if you skip it, the field is stored as an empty string.

---

## 9. Multi-Node Network

Running multiple nodes lets you watch Kryptika's P2P broadcast and consensus resolve in real time. Blocks mined on one node propagate to all peers immediately; forks self-heal automatically.

### Setting up three nodes

```bash
# Terminal 1
python run_node.py 5000

# Terminal 2
python run_node.py 5001

# Terminal 3
python run_node.py 5002
```

### Peering them together

Use the CLI or the dashboard **Peers** page. From the CLI, connect to node 5000 and add the other two:

```bash
python wallet_cli.py 5000
# option 9 → Add a peer → localhost:5001   (mutual handshake registered automatically)
# option 9 → Add a peer → localhost:5002
```

Then link 5001 to 5002:

```bash
python wallet_cli.py 5001
# option 9 → Add peer → localhost:5002
```

All three nodes now know each other. Mine on any one of them and every other node receives the new block instantly.

### Suggested exploration workflow

1. Mine a few blocks on port 5000 to put some coins into circulation.
2. Peer all three nodes as described above.
3. Submit transactions from any node — they appear in every node's mempool automatically via P2P broadcast.
4. Mine from any node — the block propagates and is accepted by all peers.
5. Watch all nodes converge on the same chain height via `GET /status` or the dashboard **Overview** page.

### How forks resolve

If two nodes mine a block at the same height simultaneously, each broadcasts its version and both chains are temporarily tied. As soon as either node mines the *next* block, it broadcasts a chain one block longer. Every other node validates it, drops the shorter fork, and switches over. The process takes seconds and requires no human intervention.

> A transaction broadcast to one node's mempool immediately reaches all connected peers. If a peer was offline during the broadcast, it picks up the transaction during the next `sync_with_peers()` call via the mempool-sync step.

---

## 10. REST API Reference

Every endpoint responds with JSON. Errors always include an `"error"` key with a plain-English explanation. All responses include `Access-Control-Allow-Origin: *`. Request bodies are hard-capped at 10 MB.

### GET endpoints

| Endpoint | What it returns |
|---|---|
| `GET /status` | `{status, height, difficulty, peers, mempool, uptime_secs, last_block}` |
| `GET /chain` | Full blockchain as a JSON array of block objects |
| `GET /peers` | `{peers: ["localhost:5001", ...]}` |
| `GET /peers/sync` | Pulls chains + mempools from all peers; adopts longest valid chain → `{replaced, height, message}` |
| `GET /mine?address=<addr>` | Mines the mempool into a new block → `{message, index, transactions, nonce, hash, miner_reward}` |
| `GET /balance/<address>` | `{address, balance}` — confirmed balance, 8 decimal places |
| `GET /history/<address>` | `{address, count, history}` — all confirmed transactions, oldest first |
| `GET /transactions/pending` | `{count, transactions}` — current mempool |
| `GET /wallet/new` | Generates a fresh key pair on the node → `{address, warning}` *(private key is not stored server-side)* |

### POST endpoints

| Endpoint | Body | What it does |
|---|---|---|
| `POST /peers/add` | `{"address": "localhost:5001"}` | Registers a peer |
| `POST /peers/receive` | `[{block}, ...]` | Accepts a chain broadcast; replaces local chain if longer and valid |
| `POST /transactions/new` | Transaction object (see below) | Validates, adds to mempool, broadcasts to all peers → HTTP 201 |
| `POST /transactions/receive` | Transaction object | Silently accepts a transaction forwarded by a peer → HTTP 200 |

### Transaction object

```json
{
  "sender":     "<64-char hex address>",
  "recipient":  "<64-char hex address>",
  "amount":     5.0,
  "fee":        0.5,
  "note":       "optional label",
  "signature":  "<128 hex chars — raw r‖s, ECDSA P-256 / SHA-256>",
  "public_key": "<130 hex chars — uncompressed EC point>",
  "tx_id":      "<64 hex chars — SHA-256 fingerprint>"
}
```

### curl examples

```bash
# Node status
curl http://localhost:5000/status

# Check balance
curl http://localhost:5000/balance/<address>

# Mine a block
curl "http://localhost:5000/mine?address=<your_address>"

# View pending mempool
curl http://localhost:5000/transactions/pending

# Submit a signed transaction
curl -X POST http://localhost:5000/transactions/new \
  -H "Content-Type: application/json" \
  -d '{
    "sender":     "...",
    "recipient":  "...",
    "amount":     5.0,
    "fee":        0.5,
    "note":       "payment",
    "signature":  "...",
    "public_key": "...",
    "tx_id":      "..."
  }'

# Add a peer
curl -X POST http://localhost:5000/peers/add \
  -H "Content-Type: application/json" \
  -d '{"address": "localhost:5001"}'

# Sync with all peers
curl http://localhost:5000/peers/sync
```

---

## 11. Running the Tests

Make sure your virtual environment is active and you're in the project root:

```bash
# Install test dependencies
pip install pytest pytest-timeout ruff

# Run all 52 tests
pytest

# Run suites individually
pytest tests/test_core.py        # 34 unit tests  — core primitives
pytest tests/test_storage.py     #  5 unit tests  — SQLite persistence
pytest tests/test_network.py     # 13 integration tests — live HTTP servers
```

The network tests spin up real HTTP servers on ports 5100–5114 and tear them down cleanly after each test, so they won't interfere with any nodes you have running. A 60-second per-test timeout is applied automatically.

### What's covered

**Core — 34 tests**

Transaction creation, signing, and ECDSA verification. Tamper detection (`test_tampered_transaction_is_invalid`). Coinbase creation and validation. Block hash determinism (`test_block_hash_is_deterministic`, `test_nonce_changes_hash`). Proof of Work enforcement. Chain validation across tampered data, broken links, wrong `prev_hash`, and insufficient PoW. Balance calculation with fee accounting. `tx_id` uniqueness and round-trip serialisation. Batch double-spend rejection inside `mine_block()` (`test_batch_double_spend_rejected_by_mine_block`, `test_batch_double_spend_same_sender_different_recipients`). Fee collection by the miner. Fake coinbase rejection.

**Storage — 5 tests**

Save/load round-trip with chain integrity verified after reload. Hash preservation through serialise/deserialise cycles. Empty database raises `ValueError`. Atomic overwrite — a new save fully replaces old data.

**Network — 13 tests**

All HTTP GET endpoints: chain, status, wallet generation, mine, balance, pending transactions, peers. P2P broadcast — mine on one node, confirm the block appears on a connected peer. Chain sync — a shorter-chain node adopts a longer chain from a peer. Error cases — missing `address` query param returns 400, unknown endpoint returns 404, fake coinbase transaction rejected. Concurrent requests — `/status` stays responsive while `/mine` is running.

---

## 12. Architecture Notes

A handful of design decisions in the source that might seem subtle at first — each has a concrete reason.

### Why Proof of Work runs outside the node lock

When `/mine` is called, the entire hash-grinding loop runs *before* acquiring the `RLock`. Only the final step — appending the block to `self.blockchain.chain` and writing to disk — is done inside the lock. This keeps `/status`, `/balance`, `/history`, and all other read endpoints fully responsive during mining.

There's a second benefit: if a peer broadcasts a longer chain while PoW is in progress, `mine()` checks `self.blockchain.height != prev_height` after acquiring the lock and discards the stale candidate cleanly, without any conflict.

### Why coin amounts use Decimal arithmetic

Python's native `float` accumulates rounding errors. After enough transactions, a comparison like `balance == expected` can silently return `False` even when the math is correct. Kryptika avoids this by rounding every coin value to exactly 8 decimal places using `decimal.Decimal` with `ROUND_HALF_UP` — the same precision model Bitcoin uses for satoshis.

### Why the `tx_id` confirmed-set grows incrementally

`Node._confirmed_ids` is a `set` that gains new `tx_id` values as each block is mined (`_index_block()`), rather than scanning the full chain on every incoming transaction. When a longer chain is adopted via sync, the set is rebuilt once from scratch (`_rebuild_confirmed_ids()`). This keeps replay-attack checks at O(1) cost instead of O(chain length × mempool size) on every submission.

### Why the mempool is persisted to SQLite

Pending transactions are written to the `mempool` table after every `add_transaction()` call and on every mine. When a node restarts, it reloads the mempool and silently drops any transactions whose `tx_id` is already in `_confirmed_ids` — transactions that were confirmed while the node was offline are discarded automatically, with no risk of double-processing.

### Why notes are not part of the ECDSA signature

The `_signable_bytes()` method covers only the four economic fields — `sender`, `recipient`, `amount`, and `fee`. Notes are optional metadata attached to the transaction for human readability. They are stored in the database, returned by `/history`, and displayed in the dashboard and CLI, but they are not cryptographically bound to the signature. Changing a note on a stored transaction would not invalidate the signature.

---

## 13. Security Model

| What's protected | How |
|---|---|
| **Signature forgery** | ECDSA P-256 — a transaction cannot be signed without the sender's private key |
| **Tamper detection** | SHA-256 chain hashing — altering any byte in any block invalidates every hash that follows |
| **Replay attacks** | Every `tx_id` is checked against both the confirmed-chain cache and the live mempool before a transaction is accepted |
| **Mempool double-spend** | Effective balance = confirmed balance − all pending outgoing amounts for that sender |
| **Block double-spend** | `mine_block()` tracks cumulative spend per sender within a single call, rejecting any transaction that would exceed the remaining balance |
| **Thread safety** | An `RLock` protects all state mutations; PoW runs outside the lock so read endpoints never block |
| **Disk integrity** | All SQLite writes use explicit `BEGIN / COMMIT / ROLLBACK` — a crash mid-write leaves the previous valid state intact |
| **Request flooding** | Incoming HTTP request bodies are hard-capped at 10 MB |
| **Address binding** | During verification, the embedded `public_key` is hashed and compared against `sender` — a mismatched key is rejected |

---

## 14. Known Limitations

Kryptika is designed for learning, not production. Here's what's intentionally absent and why it matters:

| What's missing | What a real system would do |
|---|---|
| **No wallet encryption** | Private keys are stored as plain hex in `wallets.json`. A production wallet encrypts keys at rest using a password-derived key (BIP-38, AES-GCM, or similar). |
| **No peer authentication** | Any host that knows a node's IP can push a chain to `/peers/receive`. Real nodes authenticate peers and reject data from unknown sources. |
| **No Merkle tree** | Blocks store the full transaction list. Real blockchains use a Merkle tree so a single transaction's inclusion can be proved without downloading the whole block. |
| **No UTXO set** | Balance checks scan every block from genesis. Bitcoin maintains a set of unspent outputs so balance lookups take constant time regardless of chain length. |
| **Fixed mining reward** | The reward is always 10 KRY. Bitcoin halves it roughly every four years to cap total supply — Kryptika has no halving schedule. |
| **No fee-priority ordering** | The mempool includes transactions in arrival order. Real mempools rank by fee-per-byte and evict low-fee transactions under congestion. |
| **Local-only peer discovery** | The CLI scans `localhost` on ports 5000–5010 at startup. Remote nodes must be added manually via the CLI or dashboard. |
| **Dashboard requires a running node** | The Streamlit dashboard is a pure REST client with no blockchain logic of its own. At least one node must be running before the dashboard can do anything useful. |

---

## 15. License

Released under the **MIT License** — see the [`LICENSE`](LICENSE) file for the full text.

MIT © 2026 Kryptika Contributors

---

<div align="center">

Built with pure Python &nbsp;·&nbsp; No blockchain frameworks &nbsp;·&nbsp; No shortcuts

*Read the source. Break things. Learn how it works.*

</div>