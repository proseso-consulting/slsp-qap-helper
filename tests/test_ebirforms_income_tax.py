# tests/test_ebirforms_income_tax.py
from decimal import Decimal

from ebirforms.base import TaxpayerInfo
from ebirforms.builder import build_form_xml
from ebirforms.extractors import extract_income_statement

_TAXPAYER = TaxpayerInfo(
    tin="330-593-174-000",
    rdo_code="050",
    name="TEST CORP",
    trade_name="TEST CORP",
    address="MAKATI",
    zip_code="1203",
    telephone="",
    email="test@test.com",
)


class TestExtractIncomeStatement:
    def test_basic_extraction(self):
        raw = {
            "revenue": 1_000_000.0,
            "cost_of_sales": 600_000.0,
            "non_operating_income": 50_000.0,
            "deductions": 200_000.0,
        }
        result = extract_income_statement(raw)
        assert result.revenue == Decimal("1000000.0")
        assert result.gross_income == Decimal("400000.0")
        assert result.net_taxable_income == Decimal("250000.0")


class TestBuild1702Q:
    def test_produces_xml_content(self):
        income_data = {
            "revenue": 500_000.0,
            "cost_of_sales": 300_000.0,
            "non_operating_income": 10_000.0,
            "deductions": 100_000.0,
        }
        content = build_form_xml("1702Q", _TAXPAYER, income_data, "2026-01-01", "2026-03-31", data_type="income")
        assert "frm1702q" in content


class TestBuild1702RT:
    def test_produces_xml_content(self):
        income_data = {
            "revenue": 2_000_000.0,
            "cost_of_sales": 1_200_000.0,
            "non_operating_income": 100_000.0,
            "deductions": 400_000.0,
        }
        content = build_form_xml("1702RT", _TAXPAYER, income_data, "2026-01-01", "2026-12-31", data_type="income")
        assert "frm1702RT" in content


class TestBuild1702EX:
    def test_produces_xml_content(self):
        income_data = {
            "revenue": 500_000.0,
            "cost_of_sales": 300_000.0,
            "non_operating_income": 0.0,
            "deductions": 100_000.0,
        }
        content = build_form_xml("1702EX", _TAXPAYER, income_data, "2026-01-01", "2026-12-31", data_type="income")
        assert "<?xml version='1.0'?>" in content
        assert "txtTIN1=330" in content


class TestBuild1702MX:
    def test_produces_xml_content(self):
        income_data = {
            "revenue": 1_000_000.0,
            "cost_of_sales": 600_000.0,
            "non_operating_income": 50_000.0,
            "deductions": 200_000.0,
        }
        content = build_form_xml("1702MX", _TAXPAYER, income_data, "2026-01-01", "2026-12-31", data_type="income")
        assert "<?xml version='1.0'?>" in content
        assert "txtTIN1=330" in content
