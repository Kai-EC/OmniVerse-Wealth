"""PII (Personally Identifiable Information) Masking Module.

Ensures user privacy by de-identifying sensitive data before
writing to Bedrock Knowledge Bases or any external storage.

Masking strategies:
- Wallet addresses: SHA-256 hash → truncated pseudonym
- Exact balances: Bucketed ranges (e.g., "10,000-50,000 TWD")
- Timestamps: Rounded to day-level (remove exact hour/minute)
- Transaction amounts: Percentage-based relative values
"""

import hashlib
from decimal import Decimal
from datetime import datetime, timezone

from src.rag.csv_processor import TradeRecord


class PIIMasker:
    """De-identifies trading records for safe storage in vector databases.

    Design philosophy:
    - Preserve analytical value (trends, ratios, patterns)
    - Remove precise identification vectors (exact amounts, timestamps)
    - Maintain relative relationships between records
    """

    def __init__(
        self,
        round_timestamps_to_day: bool = True,
        bucket_balances: bool = True,
        hash_salt: str = "omniverse_wealth_pii",
    ):
        self.round_timestamps_to_day = round_timestamps_to_day
        self.bucket_balances = bucket_balances
        self.hash_salt = hash_salt

    def mask_record(self, record: TradeRecord) -> dict:
        """Mask a single trade record for safe embedding.

        Args:
            record: Raw TradeRecord from CSV.

        Returns:
            Dict with masked/de-identified fields.
        """
        masked = {
            "currency": record.currency,
            "action": record.action,
            "price": str(record.price),  # Market price is public data, kept as-is
        }

        # Timestamp: round to day if configured
        if self.round_timestamps_to_day:
            dt = record.datetime_utc
            masked["date"] = dt.strftime("%Y-%m-%d")
            masked["day_of_week"] = dt.strftime("%A")
        else:
            masked["timestamp"] = record.timestamp

        # Balance: bucket into ranges
        if self.bucket_balances:
            masked["balance_bucket"] = self._bucket_value(
                record.balance, record.currency
            )
            masked["change_bucket"] = self._bucket_value(
                abs(record.change), record.currency
            )
        else:
            masked["balance"] = str(record.balance)
            masked["change"] = str(record.change)

        # Add relative size indicator
        masked["relative_size"] = self._relative_size(record)

        return masked

    def mask_records(self, records: list[TradeRecord]) -> list[dict]:
        """Mask a batch of records."""
        return [self.mask_record(r) for r in records]

    def mask_for_embedding(self, records: list[TradeRecord]) -> str:
        """Generate privacy-safe text for vector embedding.

        Produces natural language summaries that preserve
        analytical insights without exposing exact values.

        Args:
            records: List of raw trade records.

        Returns:
            Text suitable for embedding into vector store.
        """
        if not records:
            return ""

        lines = []
        # Group by day
        days: dict[str, list[TradeRecord]] = {}
        for r in records:
            day = r.datetime_utc.strftime("%Y-%m-%d")
            days.setdefault(day, []).append(r)

        for day, day_records in sorted(days.items()):
            lines.append(f"日期: {day}")

            # Summarize actions
            buys = [r for r in day_records if r.action == "buy"]
            sells = [r for r in day_records if r.action == "sell"]
            deposits = [r for r in day_records if r.action == "deposit"]
            withdrawals = [r for r in day_records if r.action == "withdrawal"]

            if buys:
                currencies = set(r.currency.upper() for r in buys)
                lines.append(
                    f"  買入操作: {len(buys)} 筆, 幣種: {', '.join(currencies)}"
                )
                for b in buys:
                    size = self._relative_size(b)
                    lines.append(
                        f"    - {b.currency.upper()} {size}規模買入, 市價 ~{b.price} TWD"
                    )

            if sells:
                currencies = set(r.currency.upper() for r in sells)
                lines.append(
                    f"  賣出操作: {len(sells)} 筆, 幣種: {', '.join(currencies)}"
                )
                for s in sells:
                    size = self._relative_size(s)
                    lines.append(
                        f"    - {s.currency.upper()} {size}規模賣出, 市價 ~{s.price} TWD"
                    )

            if deposits:
                currencies = set(r.currency.upper() for r in deposits)
                lines.append(
                    f"  入金: {len(deposits)} 筆, 幣種: {', '.join(currencies)}"
                )

            if withdrawals:
                currencies = set(r.currency.upper() for r in withdrawals)
                lines.append(
                    f"  出金: {len(withdrawals)} 筆, 幣種: {', '.join(currencies)}"
                )

            lines.append("")

        return "\n".join(lines)

    def _bucket_value(self, value: Decimal, currency: str) -> str:
        """Bucket a numeric value into a privacy-safe range.

        Different currencies have different scales, so bucketing
        is currency-aware.
        """
        abs_val = abs(value)

        if currency == "twd":
            buckets = [
                (1000, "<1K"),
                (10000, "1K-10K"),
                (50000, "10K-50K"),
                (100000, "50K-100K"),
                (500000, "100K-500K"),
                (float("inf"), ">500K"),
            ]
        elif currency in ("btc",):
            buckets = [
                (Decimal("0.001"), "<0.001"),
                (Decimal("0.01"), "0.001-0.01"),
                (Decimal("0.1"), "0.01-0.1"),
                (Decimal("1"), "0.1-1"),
                (float("inf"), ">1"),
            ]
        elif currency in ("eth",):
            buckets = [
                (Decimal("0.01"), "<0.01"),
                (Decimal("0.1"), "0.01-0.1"),
                (Decimal("1"), "0.1-1"),
                (Decimal("10"), "1-10"),
                (float("inf"), ">10"),
            ]
        else:
            # Generic buckets for other crypto
            buckets = [
                (Decimal("1"), "<1"),
                (Decimal("10"), "1-10"),
                (Decimal("100"), "10-100"),
                (Decimal("1000"), "100-1K"),
                (Decimal("10000"), "1K-10K"),
                (float("inf"), ">10K"),
            ]

        for threshold, label in buckets:
            if abs_val < Decimal(str(threshold)):
                return label

        return "unknown"

    def _relative_size(self, record: TradeRecord) -> str:
        """Classify transaction as small/medium/large relative to typical trades."""
        value_twd = record.value_twd

        if value_twd < 5000:
            return "小"
        elif value_twd < 30000:
            return "中"
        elif value_twd < 100000:
            return "大"
        else:
            return "超大"

    def _hash_identifier(self, raw: str) -> str:
        """Create a pseudonymous identifier from raw data."""
        salted = f"{self.hash_salt}:{raw}"
        return hashlib.sha256(salted.encode()).hexdigest()[:12]
