"""
run_node.py -- Start a Kryptika node.

Usage:
    python run_node.py                  (port=5000, difficulty=3)
    python run_node.py 5001             (port=5001, difficulty=3)
    python run_node.py 5002 4           (port=5002, difficulty=4)

Each node saves its chain to chain_<port>.db so multiple nodes
running on the same machine have separate databases.
"""

from kryptika.network.server import main

main()
