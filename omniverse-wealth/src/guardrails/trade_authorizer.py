"""Trade Authorizer — Two-phase verification and user signature.

Ensures no trade executes without explicit user consent:
1. Phase 1: System proposes trade (from Agent recommendation)
2. Phase 2: User signs/authorizes the exact trade parameters

The signed payload must match exactly — any parameter change
requires re-authorization.
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass


@dataclass
class AuthorizationResult:
    """Result of trade authorization check."""
    authorized: bool
    reason: str = ""
    token: str = ""
    expires_at: float = 0.0


class TradeAuthorizer:
    """Two-phase trade authorization system.

    Flow:
    1. Agent recommends trade → create_authorization_token()
    2. Frontend shows Trade Confirmation Card
    3. User clicks "Authorize" → verify_authorization()
    4. Only if verified → Hermes executes

    Token is HMAC-signed to prevent tampering.
    """

    def __init__(self, secret_key: str = "omniverse-trade-auth-secret"):
        self._secret = secret_key
        self._token_ttl = 300  # 5 minutes to authorize
        self._pending: dict[str, dict] = {}

    def create_authorization_token(
        self,
        user_id: str,
        market: str,
        side: str,
        volume: str,
        price: str | None,
        ord_type: str = "limit",
    ) -> AuthorizationResult:
        """Create an authorization token for a proposed trade.

        The token encodes the exact trade parameters. Any change
        in parameters invalidates the token.

        Args:
            user_id: User requesting the trade.
            market: Trading pair.
            side: buy or sell.
            volume: Trade volume as string.
            price: Limit price as string (None for market orders).
            ord_type: Order type.

        Returns:
            AuthorizationResult with token for user to sign.
        """
        expires_at = time.time() + self._token_ttl

        payload = {
            "user_id": user_id,
            "market": market,
            "side": side,
            "volume": volume,
            "price": price or "market",
            "ord_type": ord_type,
            "expires_at": expires_at,
            "nonce": int(time.time() * 1000),
        }

        # Generate HMAC signature
        payload_str = json.dumps(payload, sort_keys=True)
        token = hmac.new(
            self._secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Store pending authorization
        self._pending[token] = payload

        return AuthorizationResult(
            authorized=False,  # Not yet authorized, pending user action
            reason="Awaiting user authorization",
            token=token,
            expires_at=expires_at,
        )

    def verify_authorization(
        self,
        token: str,
        user_id: str,
        market: str,
        side: str,
        volume: str,
        price: str | None,
        ord_type: str = "limit",
    ) -> AuthorizationResult:
        """Verify user authorization for a trade.

        Checks:
        1. Token exists and is pending
        2. Token has not expired
        3. Trade parameters match exactly
        4. User ID matches

        Args:
            token: Authorization token from create step.
            user_id: User confirming the trade.
            market, side, volume, price, ord_type: Must match original.

        Returns:
            AuthorizationResult with final authorization status.
        """
        # Check 1: Token exists
        if token not in self._pending:
            return AuthorizationResult(
                authorized=False,
                reason="Invalid or expired authorization token",
            )

        stored = self._pending[token]

        # Check 2: Not expired
        if time.time() > stored["expires_at"]:
            del self._pending[token]
            return AuthorizationResult(
                authorized=False,
                reason="Authorization token expired (5 min limit)",
            )

        # Check 3: User matches
        if stored["user_id"] != user_id:
            return AuthorizationResult(
                authorized=False,
                reason="User ID mismatch",
            )

        # Check 4: Parameters match exactly
        if (
            stored["market"] != market
            or stored["side"] != side
            or stored["volume"] != volume
            or stored["price"] != (price or "market")
            or stored["ord_type"] != ord_type
        ):
            return AuthorizationResult(
                authorized=False,
                reason="Trade parameters changed since authorization was issued",
            )

        # All checks pass — authorize and consume token
        del self._pending[token]

        return AuthorizationResult(
            authorized=True,
            reason="Trade authorized by user",
            token=token,
        )

    def revoke(self, token: str) -> bool:
        """Revoke a pending authorization (user cancelled).

        Returns:
            True if token was found and revoked.
        """
        if token in self._pending:
            del self._pending[token]
            return True
        return False

    def get_pending_count(self, user_id: str) -> int:
        """Get number of pending authorizations for a user."""
        return sum(
            1 for p in self._pending.values()
            if p["user_id"] == user_id and time.time() <= p["expires_at"]
        )
