# tests/test_slsp_builder.py
import io
import pytest
from openpyxl import load_workbook
from slsp_builder import (
    build_slsp_rows,
    write_slsp_xlsx,
    write_slsp_dat,
)


@pytest.fixture
def sample_bill_rows():
    return [
        {
            "tin": "123456789",
            "registered_name": "ACME CORP",
            "last_name": "",
            "first_name": "",
            "middle_name": "",
            "street": "123 MAIN ST",
            "city": "MAKATI",
            "date": "2026-01-15",
            "exempt_amount": 0,
            "zero_rated_amount": 0,
            "services_amount": 10000.00,
            "capital_goods_amount": 0,
            "other_goods_amount": 0,
            "input_tax": 1200.00,
            "source": "bill",
        },
    ]


@pytest.fixture
def sample_je_rows():
    return [
        {
            "tin": "987654321",
            "registered_name": "VENDOR TWO",
            "last_name": "TWO",
            "first_name": "VENDOR",
            "middle_name": "",
            "street": "456 SIDE ST",
            "city": "QUEZON CITY",
            "date": "2026-02-10",
            "exempt_amount": 0,
            "zero_rated_amount": 0,
            "services_amount": 0,
            "capital_goods_amount": 5000.00,
            "other_goods_amount": 0,
            "input_tax": 600.00,
            "source": "journal_entry",
        },
    ]


class TestBuildSlspRows:
    def test_merges_bills_and_jes(self, sample_bill_rows, sample_je_rows):
        merged = build_slsp_rows(sample_bill_rows, sample_je_rows)
        assert len(merged) == 2

    def test_sorted_by_date(self, sample_bill_rows, sample_je_rows):
        merged = build_slsp_rows(sample_bill_rows, sample_je_rows)
        dates = [r["date"] for r in merged]
        assert dates == sorted(dates)

    def test_empty_jes(self, sample_bill_rows):
        merged = build_slsp_rows(sample_bill_rows, [])
        assert len(merged) == 1

    def test_empty_bills_and_jes(self):
        merged = build_slsp_rows([], [])
        assert merged == []


class TestWriteSlspXlsx:
    def test_produces_valid_xlsx(self, sample_bill_rows, sample_je_rows):
        merged = build_slsp_rows(sample_bill_rows, sample_je_rows)
        buf = io.BytesIO()
        write_slsp_xlsx(merged, buf, report_type="purchases")
        buf.seek(0)
        wb = load_workbook(buf)
        ws = wb.active
        assert ws.max_row == 3  # header + 2 data rows
        headers = [cell.value for cell in ws[1]]
        assert "TIN" in headers
        assert "Input Tax" in headers
        assert "Source" in headers


class TestWriteSlspDat:
    def test_produces_dat_lines(self, sample_bill_rows):
        dat = write_slsp_dat(sample_bill_rows, report_type="purchases", filing_tin="999888777")
        assert "D,P," in dat
        assert "123456789" in dat
        assert "10000.00" in dat

    def test_empty_rows_returns_empty_string(self):
        dat = write_slsp_dat([], report_type="purchases", filing_tin="999888777")
        assert dat == ""
