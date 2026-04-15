# tests/test_ebirforms_vat.py
from decimal import Decimal

from ebirforms.base import TaxpayerInfo
from ebirforms.builder import build_form_xml
from ebirforms.extractors import extract_vat_summary

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


class TestExtractVatSummary:
    def test_basic_extraction(self):
        raw = {
            "output_vat": 12_000.0,
            "vatable_sales": 100_000.0,
            "zero_rated_sales": 0.0,
            "exempt_sales": 0.0,
            "input_vat": 6_000.0,
            "total_purchases": 50_000.0,
            "sales_to_govt": 0.0,
        }
        result = extract_vat_summary(raw)
        assert result.output_vat == Decimal("12000.0")
        assert result.vatable_sales == Decimal("100000.0")
        assert result.input_vat == Decimal("6000.0")


class TestBuild2550M:
    def test_produces_xml_content(self):
        vat_data = {
            "output_vat": 12_000.0,
            "vatable_sales": 100_000.0,
            "zero_rated_sales": 0.0,
            "exempt_sales": 0.0,
            "input_vat": 6_000.0,
            "total_purchases": 50_000.0,
            "sales_to_govt": 0.0,
        }
        content = build_form_xml("2550M", _TAXPAYER, vat_data, "2026-03-01", "2026-03-31", data_type="vat")
        assert "<?xml version='1.0'?>" in content
        assert "RtnMonth=3" in content


class TestBuild2550Q:
    def test_produces_xml_content(self):
        vat_data = {
            "output_vat": 36_000.0,
            "vatable_sales": 300_000.0,
            "zero_rated_sales": 0.0,
            "exempt_sales": 0.0,
            "input_vat": 18_000.0,
            "total_purchases": 150_000.0,
            "sales_to_govt": 0.0,
        }
        content = build_form_xml("2550Q", _TAXPAYER, vat_data, "2026-01-01", "2026-03-31", data_type="vat")
        assert "<?xml version='1.0'?>" in content
        assert "frm2550q" in content
