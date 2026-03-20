"""
transaction.py — Wallet and Transaction for Kryptika.

Design decisions
----------------
- ECDSA P-256 (SECP256R1) signatures via the `cryptography` library.
- Address = SHA-256 of the uncompressed public key point (64 hex chars).
- Signature stored as raw r||s (64 bytes, 128 hex chars) for compactness.
- Private key serialised as PKCS8 DER hex (raw P-256 raises ValueError).
- tx_id = SHA-256(sender + recipient + amount + fee + signature), unique
  per transaction because ECDSA signing is randomised.
- DEFAULT_FEE uses a sentinel default so changing the class constant is
  always reflected in Transaction.create() calls.
"""

import hashlib
import json
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

_SENTINEL = object()   # sentinel for DEFAULT_FEE default argument


class Transaction:
    """A single transfer of coins between two addresses."""

    COINBASE_SENDER = "COINBASE"
    MINING_REWARD   = 10.0
    DEFAULT_FEE     = 0.5

    def __init__(
        self,
        sender:     str,
        recipient:  str,
        amount:     float,
        fee:        float = 0.0,
        signature:  str   = "",
        note:       str   = "",
        public_key: str   = "",
        tx_id:      str   = "",
    ):
        if float(amount) <= 0:
            raise ValueError(f"Amount must be positive, got {amount}.")
        if float(fee) < 0:
            raise ValueError(f"Fee cannot be negative, got {fee}.")
        self.sender     = sender
        self.recipient  = recipient
        self.amount     = round(float(amount), 8)   # cap at 8 decimal places
        self.fee        = round(float(fee),    8)
        self.signature  = signature
        self.note       = note
        self.public_key = public_key
        self.tx_id      = tx_id

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def coinbase(cls, recipient: str, fee_total: float = 0.0) -> "Transaction":
        """Create the miner reward transaction (base reward + collected fees)."""
        tx = cls(
            sender     = cls.COINBASE_SENDER,
            recipient  = recipient,
            amount     = cls.MINING_REWARD + fee_total,
            fee        = 0.0,
            signature  = "COINBASE",
            note       = f"Mining reward + {fee_total:.8f} fees",
            public_key = "",
        )
        tx.tx_id = tx._compute_tx_id()
        return tx

    @classmethod
    def create(
        cls,
        wallet:    "Wallet",
        recipient: str,
        amount:    float,
        fee        = _SENTINEL,   # resolves to DEFAULT_FEE at call time
        note:      str = "",
    ) -> "Transaction":
        """Create, sign, and fingerprint a transaction.

        Using a sentinel for `fee` means that if Transaction.DEFAULT_FEE
        is changed after import, the new value is always used.
        """
        actual_fee = cls.DEFAULT_FEE if fee is _SENTINEL else fee
        tx = cls(
            sender     = wallet.address,
            recipient  = recipient,
            amount     = amount,
            fee        = actual_fee,
            note       = note,
            public_key = wallet.public_key_hex(),
        )
        tx.signature = wallet.sign(tx._signable_bytes())
        tx.tx_id     = tx._compute_tx_id()
        return tx

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def _signable_bytes(self) -> bytes:
        """Canonical bytes that are signed — covers all economic fields."""
        return json.dumps(
            {
                "sender":    self.sender,
                "recipient": self.recipient,
                "amount":    self.amount,
                "fee":       self.fee,
            },
            sort_keys=True,
        ).encode()

    def _compute_tx_id(self) -> str:
        """SHA-256 fingerprint unique to this specific signed transaction."""
        return hashlib.sha256(
            json.dumps(
                {
                    "sender":    self.sender,
                    "recipient": self.recipient,
                    "amount":    self.amount,
                    "fee":       self.fee,
                    "signature": self.signature,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_valid(self) -> tuple[bool, str]:
        """Return (True, '') on success, or (False, reason) on failure.

        Coinbase transactions are always valid.
        User transactions must have a valid ECDSA signature verified
        against the embedded public key.
        """
        if self.sender == self.COINBASE_SENDER:
            return True, ""

        if not self.signature:
            return False, "Missing signature."

        # Resolve the public key
        if self.public_key:
            try:
                pub_bytes  = bytes.fromhex(self.public_key)
                public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                    ec.SECP256R1(), pub_bytes
                )
                if _derive_address(public_key) != self.sender:
                    return False, "Public key does not match sender address."
            except Exception as exc:
                return False, f"Invalid public key: {exc}"
        else:
            # Fallback: in-process registry (unit tests / same-process usage)
            public_key = _address_to_public_key(self.sender)
            if public_key is None:
                return False, (
                    "Cannot verify: public key not embedded and "
                    "wallet not registered in this process."
                )

        # Verify signature
        try:
            sig_bytes = bytes.fromhex(self.signature)
            if len(sig_bytes) != 64:
                return False, f"Signature must be 64 bytes, got {len(sig_bytes)}."
            r       = int.from_bytes(sig_bytes[:32], "big")
            s       = int.from_bytes(sig_bytes[32:], "big")
            der_sig = encode_dss_signature(r, s)
            public_key.verify(der_sig, self._signable_bytes(), ec.ECDSA(hashes.SHA256()))
            return True, ""
        except InvalidSignature:
            return False, "Signature verification failed."
        except Exception as exc:
            return False, f"Verification error: {exc}"

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "sender":     self.sender,
            "recipient":  self.recipient,
            "amount":     self.amount,
            "fee":        self.fee,
            "signature":  self.signature,
            "note":       self.note,
            "public_key": self.public_key,
            "tx_id":      self.tx_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        tx = cls(
            sender     = data["sender"],
            recipient  = data["recipient"],
            amount     = data["amount"],
            fee        = data.get("fee",        0.0),
            signature  = data.get("signature",  ""),
            note       = data.get("note",       ""),
            public_key = data.get("public_key", ""),
            tx_id      = data.get("tx_id",      ""),
        )
        if not tx.tx_id:
            tx.tx_id = tx._compute_tx_id()
        return tx

    def __repr__(self) -> str:
        return (
            f"Transaction(sender={self.sender[:12]}..., "
            f"recipient={self.recipient[:12]}..., "
            f"amount={self.amount}, fee={self.fee})"
        )


# ---------------------------------------------------------------------------
# In-process public-key registry (unit tests / same-process usage only)
# ---------------------------------------------------------------------------

_PUBLIC_KEY_REGISTRY: dict[str, ec.EllipticCurvePublicKey] = {}


def _register_public_key(address: str, public_key: ec.EllipticCurvePublicKey) -> None:
    _PUBLIC_KEY_REGISTRY[address] = public_key


def _address_to_public_key(address: str) -> Optional[ec.EllipticCurvePublicKey]:
    return _PUBLIC_KEY_REGISTRY.get(address)


def _derive_address(public_key: ec.EllipticCurvePublicKey) -> str:
    """Address = hex(SHA-256(uncompressed public key point))."""
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------

class Wallet:
    """An ECDSA P-256 key pair with a SHA-256 derived address."""

    def __init__(self, name: str = ""):
        self.name         = name
        self._private_key = ec.generate_private_key(ec.SECP256R1())
        self._public_key  = self._private_key.public_key()
        self.address      = _derive_address(self._public_key)
        _register_public_key(self.address, self._public_key)

    def sign(self, data: bytes) -> str:
        """Return a hex-encoded raw r||s signature (always exactly 64 bytes)."""
        der_sig = self._private_key.sign(data, ec.ECDSA(hashes.SHA256()))
        r, s    = decode_dss_signature(der_sig)
        raw     = r.to_bytes(32, "big") + s.to_bytes(32, "big")
        return raw.hex()

    def public_key_hex(self) -> str:
        """Uncompressed EC public key point as hex (130 hex chars = 65 bytes)."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        ).hex()

    def private_key_hex(self) -> str:
        """PKCS8 DER-encoded private key as hex."""
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).hex()

    @classmethod
    def from_private_key(cls, private_key_hex: str, name: str = "") -> "Wallet":
        """Reconstruct a Wallet from a PKCS8 DER hex string."""
        private_key          = serialization.load_der_private_key(
            bytes.fromhex(private_key_hex), password=None
        )
        wallet               = cls.__new__(cls)
        wallet.name          = name
        wallet._private_key  = private_key
        wallet._public_key   = private_key.public_key()
        wallet.address       = _derive_address(wallet._public_key)
        _register_public_key(wallet.address, wallet._public_key)
        return wallet

    def __repr__(self) -> str:
        return f"Wallet(name={self.name!r}, address={self.address[:16]}...)"
