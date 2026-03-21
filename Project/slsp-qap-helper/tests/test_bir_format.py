# tests/test_bir_format.py
import pytest
from bir_format import (
    clean_tin,
    clean_str,
    fmt_date_slsp,
    fmt_date_qap,
    slp_dat_line,
    sls_dat_header,
    slp_dat_header,
    qap_dat_line,
)


class TestCleanTin:
    def test_strips_non_digits(self):
        assert clean_tin("123-456-789") == "123456789"

    def test_pads_short_tin(self):
        assert clean_tin("12345") == "123450000"

    def test_truncates_long_tin(self):
        assert clean_tin("1234567890123") == "123456789"

    def test_none_returns_zeros(self):
        assert clean_tin(None) == "000000000"

    def test_empty_returns_zeros(self):
        assert clean_tin("") == "000000000"

    def test_letters_only_returns_zeros(self):
        assert clean_tin("ABCDEF") == "000000000"


class TestCleanStr:
    def test_uppercases(self):
        assert clean_str("hello world") == "HELLO WORLD"

    def test_replaces_ampersand(self):
        assert clean_str("A & B") == "A AND B"

    def test_replaces_enye(self):
        assert clean_str("Niño") == "NINO"

    def test_collapses_whitespace(self):
        assert clean_str("a   b  c") == "A B C"

    def test_truncates_to_max_len(self):
        assert clean_str("abcdefghij", max_len=5) == "ABCDE"

    def test_none_returns_empty(self):
        assert clean_str(None) == ""


class TestFmtDateSlsp:
    def test_formats_correctly(self):
        assert fmt_date_slsp("2026-01-15") == "01/15/2026"

    def test_end_of_year(self):
        assert fmt_date_slsp("2026-12-31") == "12/31/2026"


class TestFmtDateQap:
    def test_formats_correctly(self):
        assert fmt_date_qap("2026-01-15") == "01/2026"

    def test_end_of_year(self):
        assert fmt_date_qap("2026-12-31") == "12/2026"


class TestSlpDatLine:
    def test_produces_correct_format(self):
        row = {
            "tin": "123456789",
            "registered_name": "ACME CORP",
            "last_name": "",
            "first_name": "",
            "middle_name": "",
            "street": "123 MAIN ST",
            "city": "MAKATI",
            "exempt_amount": 0,
            "zero_rated_amount": 0,
            "services_amount": 10000.00,
            "capital_goods_amount": 0,
            "other_goods_amount": 0,
            "input_tax": 1200.00,
            "date": "01/15/2026",
        }
        line = slp_dat_line(row, filing_tin="999888777")
        assert line.startswith('D,P,"123456789","ACME CORP"')
        assert "10000.00" in line
        assert "1200.00" in line
        assert line.endswith("999888777,01/15/2026")


_SAMPLE_COMPANY = {
    "tin": "005302695",
    "registered_name": "FRENCH CHAMBER OF COMMERCE",
    "first_name": "",
    "middle_name": "",
    "last_name": "",
    "street": "UNIT 404 MADRIGAL BLDG",
    "city": "MAKATI CITY",
    "rdo": "050",
}

_SAMPLE_SLS_ROW = {
    "exempt_amount": 0, "zero_rated_amount": 0,
    "taxable_amount": 50000.00, "tax_amount": 6000.00,
}

_SAMPLE_SLP_ROW = {
    "exempt_amount": 0, "zero_rated_amount": 0,
    "services_amount": 30000.00, "capital_goods_amount": 0,
    "other_goods_amount": 0, "input_tax": 3600.00,
}


class TestSlsDatHeader:
    def test_starts_with_hs(self):
        line = sls_dat_header(_SAMPLE_COMPANY, [_SAMPLE_SLS_ROW], "11/30/2025")
        assert line.startswith("H,S,005302695,")

    def test_has_16_fields(self):
        line = sls_dat_header(_SAMPLE_COMPANY, [_SAMPLE_SLS_ROW], "11/30/2025")
        assert len(line.split(",")) == 16

    def test_totals_summed_from_rows(self):
        rows = [_SAMPLE_SLS_ROW, {**_SAMPLE_SLS_ROW, "taxable_amount": 10000.00, "tax_amount": 1200.00}]
        line = sls_dat_header(_SAMPLE_COMPANY, rows, "11/30/2025")
        assert "60000.00" in line   # 50000 + 10000
        assert "7200.00" in line    # 6000 + 1200

    def test_rdo_and_period_at_end(self):
        line = sls_dat_header(_SAMPLE_COMPANY, [_SAMPLE_SLS_ROW], "11/30/2025")
        assert line.endswith(",050,11/30/2025")


class TestSlpDatHeader:
    def test_starts_with_hp(self):
        line = slp_dat_header(_SAMPLE_COMPANY, [_SAMPLE_SLP_ROW], "11/30/2025")
        assert line.startswith("H,P,005302695,")

    def test_has_20_fields(self):
        line = slp_dat_header(_SAMPLE_COMPANY, [_SAMPLE_SLP_ROW], "11/30/2025")
        assert len(line.split(",")) == 20

    def test_vat_duplicated_and_importation_zero(self):
        line = slp_dat_header(_SAMPLE_COMPANY, [_SAMPLE_SLP_ROW], "11/30/2025")
        # last 4 fields: vat,vat,0,rdo,period → split gives [...,3600.00,3600.00,0,050,11/30/2025]
        fields = line.split(",")
        assert fields[-5] == "3600.00"  # vat
        assert fields[-4] == "3600.00"  # vat duplicate
        assert fields[-3] == "0"        # importation placeholder
        assert fields[-2] == "050"      # rdo
        assert fields[-1] == "11/30/2025"


class TestQapDatLine:
    def test_produces_correct_format(self):
        row = {
            "tin": "123456789",
            "registered_name": "ACME CORP",
            "last_name": "",
            "first_name": "",
            "middle_name": "",
            "date": "01/2026",
            "atc": "WI010",
            "tax_rate": 10,
            "gross_income": 50000.00,
            "tax_withheld": 5000.00,
        }
        line = qap_dat_line(row, seq=1)
        assert line.startswith("D1,1601EQ,1,123456789,0000")
        assert "WI010" in line
        assert "50000.00" in line
        assert "5000.00" in line
