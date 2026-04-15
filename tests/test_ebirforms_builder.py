# tests/test_ebirforms_builder.py

from ebirforms.base import TaxpayerInfo
from ebirforms.builder import build_form_xml, build_savefile_name

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


class TestBuildSavefileName:
    def test_monthly_form(self):
        assert (
            build_savefile_name("330593174000", "0619E", "2026-03-01", "2026-03-31") == "330593174000-0619E-032026.xml"
        )

    def test_quarterly_form(self):
        assert (
            build_savefile_name("330593174000", "1601EQ", "2026-01-01", "2026-03-31")
            == "330593174000-1601EQ-032026.xml"
        )


class TestBuildFormXml:
    def test_0619e_produces_xml_content(self):
        ewt_lines = [
            {
                "atc_code": "WC011",
                "tax_rate": 15.0,
                "tax_name": "15% WC011",
                "tax_base": 100_000.0,
                "tax_amount": 15_000.0,
            },
        ]
        content = build_form_xml("0619E", _TAXPAYER, ewt_lines, "2026-03-01", "2026-03-31")
        assert "<?xml version='1.0'?>" in content
        assert "frm0619E" in content
        assert "txtTIN1=330" in content

    def test_1601eq_produces_xml_content(self):
        ewt_lines = [
            {
                "atc_code": "WC011",
                "tax_rate": 15.0,
                "tax_name": "15% WC011",
                "tax_base": 100_000.0,
                "tax_amount": 15_000.0,
            },
            {
                "atc_code": "WC120",
                "tax_rate": 2.0,
                "tax_name": "2% WC120",
                "tax_base": 200_000.0,
                "tax_amount": 4_000.0,
            },
        ]
        content = build_form_xml("1601EQ", _TAXPAYER, ewt_lines, "2026-01-01", "2026-03-31")
        assert "<?xml version='1.0'?>" in content
        assert "frm1601EQ" in content

    def test_unknown_form_raises(self):
        import pytest

        with pytest.raises(ValueError, match="No builder for form UNKNOWN"):
            build_form_xml("UNKNOWN", _TAXPAYER, [], "2026-01-01", "2026-03-31")


class TestBuild0619F:
    def test_produces_xml_content(self):
        fwt_lines = [
            {
                "atc_code": "WC230",
                "tax_rate": 25.0,
                "tax_name": "25% WC230",
                "tax_base": 100_000.0,
                "tax_amount": 25_000.0,
            },
        ]
        content = build_form_xml("0619F", _TAXPAYER, fwt_lines, "2026-03-01", "2026-03-31")
        assert "<?xml version='1.0'?>" in content
        assert "frm0619F" in content


class TestBuild1601FQ:
    def test_produces_xml_content(self):
        fwt_lines = [
            {
                "atc_code": "WC230",
                "tax_rate": 25.0,
                "tax_name": "25% WC230",
                "tax_base": 200_000.0,
                "tax_amount": 50_000.0,
            },
            {
                "atc_code": "WV080",
                "tax_rate": 12.0,
                "tax_name": "12% WV080",
                "tax_base": 30_000.0,
                "tax_amount": 3_600.0,
            },
        ]
        content = build_form_xml("1601FQ", _TAXPAYER, fwt_lines, "2026-01-01", "2026-03-31")
        assert "<?xml version='1.0'?>" in content
        assert "frm1601FQ" in content


class TestBuild1603Q:
    def test_produces_xml_content(self):
        manual_data = {
            "year": 2026,
            "quarter": 1,
            "entries": [
                {"description": "Housing benefit", "tax_base": 100_000.0, "tax_withheld": 53_846.15},
            ],
        }
        content = build_form_xml("1603Q", _TAXPAYER, manual_data, "2026-01-01", "2026-03-31", data_type="manual")
        assert "<?xml version='1.0'?>" in content
        assert "txtTIN1=330" in content


class TestBuild2551Q:
    def test_produces_xml_content(self):
        manual_data = {
            "year": 2026,
            "quarter": 1,
            "rows": [
                {
                    "atc_code": "PT010",
                    "atc_description": "Percentage tax",
                    "tax_base": 500_000.0,
                    "tax_rate": 3.0,
                    "tax_due": 15_000.0,
                },
            ],
        }
        content = build_form_xml("2551Q", _TAXPAYER, manual_data, "2026-01-01", "2026-03-31", data_type="manual")
        assert "<?xml version='1.0'?>" in content
        assert "txtTIN1=330" in content


class TestBuild2000:
    def test_produces_xml_content(self):
        manual_data = {
            "year": 2026,
            "month": 3,
            "line_items": [
                {"atc_code": "DS101", "tax_base": 1_000_000.0, "tax_rate": "P1.50 per P200", "tax_due": 7_500.0},
            ],
        }
        content = build_form_xml("2000", _TAXPAYER, manual_data, "2026-03-01", "2026-03-31", data_type="manual")
        assert "<?xml version='1.0'?>" in content
        assert "txtTIN1=330" in content


class TestBuild1604E:
    def test_produces_xml_content(self):
        manual_data = {
            "year": 2026,
            "is_top_withholding_agent": False,
        }
        content = build_form_xml("1604E", _TAXPAYER, manual_data, "2026-01-01", "2026-12-31", data_type="manual")
        assert "<?xml version='1.0'?>" in content
        assert "txtTIN1=330" in content
