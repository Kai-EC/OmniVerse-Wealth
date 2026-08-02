"""Unit tests for MAX API Client.

Tests HMAC signing logic and request construction
without hitting the live API.
"""

import hashlib
import hmac
import json
import time
from base64 import b64encode
from unittest.mock import AsyncMock, patch

import pytest

from src.tools.max_client import MaxClient, MaxAPIError


class TestMaxClientSigning:
    """Test HMAC-SHA256 authentication signing."""

    def test_sign_generates_correct_headers(self):
        client = MaxClient(api_key="test_key", api_secret="test_secret")
        path = "/api/v3/info"
        params = {"nonce": 1700000000000}

        headers = client._sign(path, params)

        assert headers["X-MAX-ACCESSKEY"] == "test_key"
        assert "X-MAX-PAYLOAD" in headers
        assert "X-MAX-SIGNATURE" in headers

    def test_payload_contains_path(self):
        client = MaxClient(api_key="key", api_secret="secret")
        path = "/api/v3/wallet/spot/accounts"
        params = {"nonce": 1700000000000}

        headers = client._sign(path, params)
        payload = headers["X-MAX-PAYLOAD"]

        # Verify payload is base64 of JSON containing path
        import base64
        payload_decoded = json.loads(base64.b64decode(payload))
        assert payload_decoded["path"] == path
        assert payload_decoded["nonce"] == 1700000000000

    def test_signature_is_hmac_sha256(self):
        client = MaxClient(api_key="key", api_secret="my_secret")
        path = "/api/v3/info"
        params = {"nonce": 1234567890000}

        headers = client._sign(path, params)
        payload = headers["X-MAX-PAYLOAD"]

        # Manually compute expected signature
        expected_sig = hmac.new(
            "my_secret".encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        assert headers["X-MAX-SIGNATURE"] == expected_sig

    def test_nonce_generation(self):
        client = MaxClient(api_key="k", api_secret="s")
        nonce = client._generate_nonce()
        assert isinstance(nonce, int)
        assert nonce > 1700000000000  # After 2023
        assert nonce <= int(time.time() * 1000) + 1000


class TestMaxClientTrading:
    """Test trading safety guards."""

    @pytest.mark.asyncio
    async def test_create_order_blocked_when_trading_disabled(self):
        from unittest.mock import patch
        with patch("src.config.settings.max_enable_trading", False):
            client = MaxClient(api_key="k", api_secret="s")
            with pytest.raises(MaxAPIError) as exc:
                await client.create_order(
                    market="btctwd",
                    side="buy",
                    volume="0.01",
                    price="3400000",
                )
            assert exc.value.status_code == 403
            assert "disabled" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_cancel_order_blocked_when_trading_disabled(self):
        from unittest.mock import patch
        with patch("src.config.settings.max_enable_trading", False):
            client = MaxClient(api_key="k", api_secret="s")
            with pytest.raises(MaxAPIError) as exc:
                await client.cancel_order(12345)
            assert exc.value.status_code == 403


class TestMaxAPIError:
    """Test error handling."""

    def test_error_message_format(self):
        err = MaxAPIError(status_code=400, code=2002, message="Invalid volume")
        assert "400" in str(err)
        assert "2002" in str(err)
        assert "Invalid volume" in str(err)

    def test_error_without_code(self):
        err = MaxAPIError(status_code=500, message="Internal error")
        assert err.code is None
        assert err.status_code == 500
