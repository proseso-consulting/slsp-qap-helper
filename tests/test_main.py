# tests/test_main.py
"""Tests for extraction helpers in main.py."""

from main import _line_gross


class TestLineGross:
    """_line_gross should return price_subtotal for bills, debit-credit for JEs."""

    def test_uses_price_subtotal_when_present(self):
        line = {"price_subtotal": 900.0, "debit": 900.0, "credit": 0.0}
        assert _line_gross(line) == 900.0

    def test_falls_back_to_debit_minus_credit_when_subtotal_zero(self):
        # Journal entry lines have price_subtotal = 0
        line = {"price_subtotal": 0, "debit": 1000.0, "credit": 0.0}
        assert _line_gross(line) == 1000.0

    def test_falls_back_when_subtotal_missing(self):
        line = {"debit": 500.0, "credit": 0.0}
        assert _line_gross(line) == 500.0

    def test_credit_line_returns_positive(self):
        # A credit-side JE line (e.g. refund)
        line = {"price_subtotal": 0, "debit": 0.0, "credit": 750.0}
        assert _line_gross(line) == 750.0

    def test_negative_subtotal_returns_absolute(self):
        line = {"price_subtotal": -1200.0, "debit": 0.0, "credit": 1200.0}
        assert _line_gross(line) == 1200.0

    def test_all_zeros(self):
        line = {"price_subtotal": 0, "debit": 0.0, "credit": 0.0}
        assert _line_gross(line) == 0.0
