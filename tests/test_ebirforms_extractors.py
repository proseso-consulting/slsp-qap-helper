# tests/test_ebirforms_extractors.py
from decimal import Decimal

from ebirforms.extractors import extract_ewt_summary


class TestExtractEwtSummary:
    def test_groups_by_atc_code(self):
        raw_lines = [
            {
                "atc_code": "WC011",
                "tax_rate": 15.0,
                "tax_name": "15% WC011",
                "tax_base": 100_000.0,
                "tax_amount": 15_000.0,
            },
            {
                "atc_code": "WC011",
                "tax_rate": 15.0,
                "tax_name": "15% WC011",
                "tax_base": 50_000.0,
                "tax_amount": 7_500.0,
            },
            {
                "atc_code": "WC120",
                "tax_rate": 2.0,
                "tax_name": "2% WC120",
                "tax_base": 200_000.0,
                "tax_amount": 4_000.0,
            },
        ]
        result = extract_ewt_summary(raw_lines, category="expanded")
        assert len(result) == 2

        wc011 = next(r for r in result if r.atc_code == "WC011")
        assert wc011.tax_base == Decimal("150000.00")
        assert wc011.tax_withheld == Decimal("22500.00")
        assert wc011.tax_rate == Decimal("15.0")

        wc120 = next(r for r in result if r.atc_code == "WC120")
        assert wc120.tax_base == Decimal("200000.00")
        assert wc120.tax_withheld == Decimal("4000.00")

    def test_filters_by_expanded_category(self):
        raw_lines = [
            {"atc_code": "WC011", "tax_rate": 15.0, "tax_name": "", "tax_base": 100_000.0, "tax_amount": 15_000.0},
            {"atc_code": "WC230", "tax_rate": 25.0, "tax_name": "", "tax_base": 50_000.0, "tax_amount": 12_500.0},
        ]
        result = extract_ewt_summary(raw_lines, category="expanded")
        assert len(result) == 1
        assert result[0].atc_code == "WC011"

    def test_filters_by_final_category(self):
        raw_lines = [
            {"atc_code": "WC011", "tax_rate": 15.0, "tax_name": "", "tax_base": 100_000.0, "tax_amount": 15_000.0},
            {"atc_code": "WC230", "tax_rate": 25.0, "tax_name": "", "tax_base": 50_000.0, "tax_amount": 12_500.0},
            {"atc_code": "WV080", "tax_rate": 12.0, "tax_name": "", "tax_base": 30_000.0, "tax_amount": 3_600.0},
        ]
        result = extract_ewt_summary(raw_lines, category="final")
        assert len(result) == 2
        atc_codes = {r.atc_code for r in result}
        assert atc_codes == {"WC230", "WV080"}

    def test_empty_lines_returns_empty(self):
        result = extract_ewt_summary([], category="expanded")
        assert result == []

    def test_unknown_atc_included_with_no_category_filter(self):
        raw_lines = [
            {"atc_code": "WC999", "tax_rate": 3.0, "tax_name": "", "tax_base": 10_000.0, "tax_amount": 300.0},
        ]
        result = extract_ewt_summary(raw_lines, category=None)
        assert len(result) == 1
        assert result[0].atc_code == "WC999"

    def test_total_properties(self):
        raw_lines = [
            {"atc_code": "WC011", "tax_rate": 15.0, "tax_name": "", "tax_base": 100_000.0, "tax_amount": 15_000.0},
            {"atc_code": "WC120", "tax_rate": 2.0, "tax_name": "", "tax_base": 200_000.0, "tax_amount": 4_000.0},
        ]
        result = extract_ewt_summary(raw_lines, category="expanded")
        total_base = sum(r.tax_base for r in result)
        total_withheld = sum(r.tax_withheld for r in result)
        assert total_base == Decimal("300000.00")
        assert total_withheld == Decimal("19000.00")
