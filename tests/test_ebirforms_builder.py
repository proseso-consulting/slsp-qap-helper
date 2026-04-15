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
