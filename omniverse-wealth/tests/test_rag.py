"""Tests for CSV RAG Pipeline.

Tests data loading, portfolio computation, PII masking,
and chunk generation for vector embedding.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from src.rag.csv_processor import CSVProcessor, TradeRecord, PortfolioSnapshot
from src.rag.pii_masker import PIIMasker


CSV_PATH = Path(__file__).parent.parent.parent / "MaiCoin_最近一年份出入金及交易紀錄.csv"


class TestCSVProcessor:
    """Test CSV loading and portfolio analysis."""

    @pytest.fixture
    def processor(self):
        if not CSV_PATH.exists():
            pytest.skip("CSV file not available")
        return CSVProcessor(str(CSV_PATH)).load()

    def test_load_records(self, processor):
        assert len(processor.records) > 0
        assert len(processor.records) == 10000

    def test_records_sorted_by_timestamp(self, processor):
        for i in range(1, len(processor.records)):
            assert processor.records[i].timestamp >= processor.records[i - 1].timestamp

    def test_currencies_detected(self, processor):
        currencies = processor.currencies
        assert "btc" in currencies
        assert "eth" in currencies
        assert "sol" in currencies
        assert "twd" in currencies

    def test_date_range(self, processor):
        start, end = processor.date_range
        assert start.year == 2025
        assert end.year == 2025

    def test_filter_by_currency(self, processor):
        btc_records = processor.filter_by_currency("btc")
        assert all(r.currency == "btc" for r in btc_records)
        assert len(btc_records) > 0

    def test_filter_by_action(self, processor):
        buys = processor.filter_by_action("buy")
        assert all(r.action == "buy" for r in buys)

    def test_compute_portfolio(self, processor):
        portfolio = processor.compute_portfolio()
        assert "btc" in portfolio
        assert "eth" in portfolio
        btc = portfolio["btc"]
        assert btc.buy_count > 0
        assert btc.total_bought > 0
        assert btc.avg_buy_price_twd > 0

    def test_generate_rag_chunks(self, processor):
        chunks = list(processor.generate_rag_chunks(chunk_size=10))
        assert len(chunks) > 0
        # Each chunk should be a readable text
        assert "交易紀錄期間" in chunks[0]

    def test_summary_text(self, processor):
        summary = processor.summary_text()
        assert "投資組合摘要" in summary
        assert "BTC" in summary


class TestTradeRecord:
    """Test TradeRecord validation."""

    def test_valid_record(self):
        record = TradeRecord(
            timestamp=1735690380000,
            currency="btc",
            price=Decimal("3400000"),
            action="buy",
            change=Decimal("0.01"),
            balance=Decimal("0.01"),
        )
        assert record.is_trade is True
        assert record.currency == "btc"

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError):
            TradeRecord(
                timestamp=1735690380000,
                currency="btc",
                price=Decimal("3400000"),
                action="invalid",
                change=Decimal("0.01"),
                balance=Decimal("0.01"),
            )

    def test_value_twd_calculation(self):
        record = TradeRecord(
            timestamp=1735690380000,
            currency="btc",
            price=Decimal("3400000"),
            action="buy",
            change=Decimal("0.01"),
            balance=Decimal("0.01"),
        )
        assert record.value_twd == Decimal("34000")

    def test_deposit_is_not_trade(self):
        record = TradeRecord(
            timestamp=1735690380000,
            currency="twd",
            price=Decimal("1"),
            action="deposit",
            change=Decimal("50000"),
            balance=Decimal("50000"),
        )
        assert record.is_trade is False


class TestPIIMasker:
    """Test PII de-identification."""

    def test_mask_record_hides_balance(self):
        masker = PIIMasker(bucket_balances=True)
        record = TradeRecord(
            timestamp=1735690380000,
            currency="btc",
            price=Decimal("3400000"),
            action="buy",
            change=Decimal("0.05"),
            balance=Decimal("0.05"),
        )
        masked = masker.mask_record(record)
        # Should not contain exact balance
        assert "balance_bucket" in masked
        assert masked["balance_bucket"] in ("<0.001", "0.001-0.01", "0.01-0.1", "0.1-1", ">1")

    def test_mask_record_rounds_timestamp(self):
        masker = PIIMasker(round_timestamps_to_day=True)
        record = TradeRecord(
            timestamp=1735690380000,
            currency="eth",
            price=Decimal("120000"),
            action="sell",
            change=Decimal("-0.5"),
            balance=Decimal("1.5"),
        )
        masked = masker.mask_record(record)
        assert "date" in masked
        assert "timestamp" not in masked

    def test_mask_preserves_public_price(self):
        masker = PIIMasker()
        record = TradeRecord(
            timestamp=1735690380000,
            currency="btc",
            price=Decimal("3400000"),
            action="buy",
            change=Decimal("0.01"),
            balance=Decimal("0.01"),
        )
        masked = masker.mask_record(record)
        assert masked["price"] == "3400000"

    def test_relative_size_classification(self):
        masker = PIIMasker()
        # Small trade: 100 TWD
        small = TradeRecord(
            timestamp=1, currency="doge", price=Decimal("10"),
            action="buy", change=Decimal("10"), balance=Decimal("10"),
        )
        assert masker._relative_size(small) == "小"

        # Large trade: 50000 TWD
        large = TradeRecord(
            timestamp=1, currency="eth", price=Decimal("100000"),
            action="buy", change=Decimal("0.5"), balance=Decimal("0.5"),
        )
        assert masker._relative_size(large) == "大"

    def test_mask_for_embedding_generates_text(self):
        masker = PIIMasker()
        records = [
            TradeRecord(
                timestamp=1735690380000, currency="btc",
                price=Decimal("3400000"), action="buy",
                change=Decimal("0.01"), balance=Decimal("0.01"),
            ),
            TradeRecord(
                timestamp=1735690480000, currency="eth",
                price=Decimal("120000"), action="sell",
                change=Decimal("-0.5"), balance=Decimal("1.0"),
            ),
        ]
        text = masker.mask_for_embedding(records)
        assert "日期" in text
        assert "買入" in text
        assert "賣出" in text
