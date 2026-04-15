"""Tests for BIR Form 1604-E v2018 generator."""

from decimal import Decimal

import pytest

from ebirforms.base import TaxpayerInfo, build_ebirforms_content, parse_ebirforms_file
from ebirforms.generators.form_1604e import Form1604EData, Form1604EGenerator, RemittanceRow


@pytest.fixture()
def taxpayer():
    return TaxpayerInfo(
        tin="010-318-867-000",
        rdo_code="032",
        name="ABC CORPORATION",
        trade_name="ABC CORPORATION",
        address="BURGUNDY CORPORATE TOWER MAKATI",
        zip_code="1232",
        telephone="09605005960",
        email="joseph@proseso-consulting.com",
        line_of_business="OTHER SERVICE ACTIVITIES",
    )


@pytest.fixture()
def q1_row():
    return RemittanceRow(
        rem_date="03/31/2025",
        bank_code="BDO",
        tra_no="TRA-001",
        tax_withheld=Decimal("5000.00"),
        penalties=Decimal("0.00"),
    )


@pytest.fixture()
def jan_row():
    return RemittanceRow(
        rem_date="01/10/2025",
        bank_code="BDO",
        tra_no="TRA-001",
        tax_withheld=Decimal("2000.00"),
        penalties=Decimal("0.00"),
    )


def _make_sched1(q1=None, q2=None, q3=None, q4=None):
    """Build a 4-tuple of RemittanceRow, defaulting to empty rows."""
    empty = RemittanceRow.empty()
    return (q1 or empty, q2 or empty, q3 or empty, q4 or empty)


def _make_sched2(**kwargs):
    """Build a 12-tuple of RemittanceRow. Pass month=row (1-indexed)."""
    rows = [RemittanceRow.empty()] * 12
    for month, row in kwargs.items():
        rows[int(month) - 1] = row
    return tuple(rows)


@pytest.fixture()
def basic_data(q1_row):
    return Form1604EData(
        year=2025,
        is_amended=False,
        is_private=True,
        is_top_withholding_agent=False,
        sched1_rows=_make_sched1(q1=q1_row),
    )


# ---------------------------------------------------------------------------
# RemittanceRow tests
# ---------------------------------------------------------------------------


class TestRemittanceRow:
    def test_total_remitted_is_withheld_plus_penalties(self):
        row = RemittanceRow("01/31/2025", "BDO", "TRA-001", Decimal("5000.00"), Decimal("250.00"))
        assert row.total_remitted == Decimal("5250.00")

    def test_empty_row_zeros(self):
        row = RemittanceRow.empty()
        assert row.tax_withheld == Decimal("0.00")
        assert row.penalties == Decimal("0.00")
        assert row.total_remitted == Decimal("0.00")
        assert row.rem_date == ""
        assert row.bank_code == ""
        assert row.tra_no == ""

    def test_no_penalties(self):
        row = RemittanceRow("03/31/2025", "BPI", "TRA-X", Decimal("10000.00"), Decimal("0.00"))
        assert row.total_remitted == Decimal("10000.00")


# ---------------------------------------------------------------------------
# Form1604EData validation tests
# ---------------------------------------------------------------------------


class TestForm1604EDataValidation:
    def test_rejects_wrong_sched1_length(self):
        with pytest.raises(ValueError, match="sched1_rows must have exactly 4"):
            Form1604EData(
                year=2025,
                is_amended=False,
                is_private=True,
                is_top_withholding_agent=False,
                sched1_rows=(RemittanceRow.empty(),),  # only 1 row
            )

    def test_rejects_wrong_sched2_length(self):
        with pytest.raises(ValueError, match="sched2_rows must have exactly 12"):
            Form1604EData(
                year=2025,
                is_amended=False,
                is_private=True,
                is_top_withholding_agent=False,
                sched2_rows=tuple(RemittanceRow.empty() for _ in range(3)),  # only 3
            )

    def test_accepts_correct_lengths(self):
        data = Form1604EData(
            year=2025,
            is_amended=False,
            is_private=True,
            is_top_withholding_agent=False,
        )
        assert len(data.sched1_rows) == 4
        assert len(data.sched2_rows) == 12


# ---------------------------------------------------------------------------
# Form1604EData aggregate properties
# ---------------------------------------------------------------------------


class TestForm1604EDataProperties:
    def test_sched1_totals_all_zero_by_default(self):
        data = Form1604EData(year=2025, is_amended=False, is_private=True, is_top_withholding_agent=False)
        assert data.sched1_tax_withheld_total == Decimal("0.00")
        assert data.sched1_penalties_total == Decimal("0.00")
        assert data.sched1_total_remitted == Decimal("0.00")

    def test_sched1_totals_sum_all_rows(self):
        rows = (
            RemittanceRow("03/31/2025", "BDO", "T1", Decimal("5000.00"), Decimal("0.00")),
            RemittanceRow("06/30/2025", "BDO", "T2", Decimal("6000.00"), Decimal("100.00")),
            RemittanceRow("09/30/2025", "BDO", "T3", Decimal("7000.00"), Decimal("0.00")),
            RemittanceRow("12/31/2025", "BDO", "T4", Decimal("8000.00"), Decimal("200.00")),
        )
        data = Form1604EData(
            year=2025, is_amended=False, is_private=True, is_top_withholding_agent=False, sched1_rows=rows
        )
        assert data.sched1_tax_withheld_total == Decimal("26000.00")
        assert data.sched1_penalties_total == Decimal("300.00")
        assert data.sched1_total_remitted == Decimal("26300.00")

    def test_sched2_totals_sum_all_months(self):
        rows = list(RemittanceRow.empty() for _ in range(12))
        rows[0] = RemittanceRow("01/10/2025", "BDO", "T01", Decimal("1000.00"), Decimal("0.00"))
        rows[6] = RemittanceRow("07/10/2025", "BDO", "T07", Decimal("2000.00"), Decimal("50.00"))
        data = Form1604EData(
            year=2025, is_amended=False, is_private=True, is_top_withholding_agent=False, sched2_rows=tuple(rows)
        )
        assert data.sched2_tax_withheld_total == Decimal("3000.00")
        assert data.sched2_penalties_total == Decimal("50.00")
        assert data.sched2_total_remitted == Decimal("3050.00")


# ---------------------------------------------------------------------------
# Generator field output tests
# ---------------------------------------------------------------------------


class TestForm1604EGeneratorFields:
    def test_form_number(self, taxpayer, basic_data):
        gen = Form1604EGenerator(taxpayer, basic_data)
        assert gen.form_number == "1604Ev2018"

    def test_form_prefix(self, taxpayer, basic_data):
        gen = Form1604EGenerator(taxpayer, basic_data)
        assert gen.form_prefix == "frm1604e"

    def test_year_field(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1604e:txtYear"] == "2025"

    def test_amendment_no(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1604e:AmendedRtn_1"] == "false"
        assert fields["frm1604e:AmendedRtn_2"] == "true"

    def test_amendment_yes(self, taxpayer):
        data = Form1604EData(year=2025, is_amended=True, is_private=True, is_top_withholding_agent=False)
        fields = Form1604EGenerator(taxpayer, data).build_fields()
        assert fields["frm1604e:AmendedRtn_1"] == "true"
        assert fields["frm1604e:AmendedRtn_2"] == "false"

    def test_no_sheets_default(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1604e:txtSheets"] == "0"

    def test_no_sheets_custom(self, taxpayer):
        data = Form1604EData(year=2025, is_amended=False, is_private=True, is_top_withholding_agent=False, no_sheets=5)
        fields = Form1604EGenerator(taxpayer, data).build_fields()
        assert fields["frm1604e:txtSheets"] == "5"

    def test_tin_fields(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1604e:txtTIN1"] == "010"
        assert fields["frm1604e:txtTIN2"] == "318"
        assert fields["frm1604e:txtTIN3"] == "867"
        assert fields["frm1604e:txtBranchCode"] == "000"

    def test_taxpayer_identity_fields(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1604e:txtWthhldngAgntsNme"] == "ABC CORPORATION"
        assert fields["frm1604e:txtRDOCode"] == "032"
        assert fields["frm1604e:txtAddress"] == "BURGUNDY CORPORATE TOWER MAKATI"
        assert fields["frm1604e:txtAddress2"] == ""
        assert fields["frm1604e:txtZipCode"] == "1232"
        assert fields["frm1604e:txtTelNum"] == "09605005960"
        assert fields["txtEmail"] == "joseph@proseso-consulting.com"
        assert fields["frm1604e:txtLineBus"] == "OTHER SERVICE ACTIVITIES"

    def test_category_private(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1604e:WthldngAgntCtgry_1"] == "true"
        assert fields["frm1604e:WthldngAgntCtgry_2"] == "false"

    def test_category_government(self, taxpayer):
        data = Form1604EData(year=2025, is_amended=False, is_private=False, is_top_withholding_agent=False)
        fields = Form1604EGenerator(taxpayer, data).build_fields()
        assert fields["frm1604e:WthldngAgntCtgry_1"] == "false"
        assert fields["frm1604e:WthldngAgntCtgry_2"] == "true"

    def test_top_wh_agent_no(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1604e:TpWthldngAgnt_1"] == "false"
        assert fields["frm1604e:TpWthldngAgnt_2"] == "true"

    def test_top_wh_agent_yes(self, taxpayer):
        data = Form1604EData(year=2025, is_amended=False, is_private=True, is_top_withholding_agent=True)
        fields = Form1604EGenerator(taxpayer, data).build_fields()
        assert fields["frm1604e:TpWthldngAgnt_1"] == "true"
        assert fields["frm1604e:TpWthldngAgnt_2"] == "false"

    def test_sched1_row_fields(self, taxpayer, q1_row):
        data = Form1604EData(
            year=2025,
            is_amended=False,
            is_private=True,
            is_top_withholding_agent=False,
            sched1_rows=_make_sched1(q1=q1_row),
        )
        fields = Form1604EGenerator(taxpayer, data).build_fields()

        assert fields["frm1604e:txtSched1RemDate1"] == "03/31/2025"
        assert fields["frm1604e:txtSched1BankCode1"] == "BDO"
        assert fields["frm1604e:txtSched1TRANo1"] == "TRA-001"
        assert fields["frm1604e:txtSched1TaxWithheld1"] == "5,000.00"
        assert fields["frm1604e:txtSched1Penalties1"] == "0.00"
        assert fields["frm1604e:txtSched1TotRemAmt1"] == "5,000.00"

    def test_sched1_empty_rows_are_zero(self, taxpayer, q1_row):
        data = Form1604EData(
            year=2025,
            is_amended=False,
            is_private=True,
            is_top_withholding_agent=False,
            sched1_rows=_make_sched1(q1=q1_row),
        )
        fields = Form1604EGenerator(taxpayer, data).build_fields()

        # Q2-Q4 should be empty/zero
        for qrow in (2, 3, 4):
            assert fields[f"frm1604e:txtSched1RemDate{qrow}"] == ""
            assert fields[f"frm1604e:txtSched1TaxWithheld{qrow}"] == "0.00"

    def test_sched1_totals(self, taxpayer):
        rows = (
            RemittanceRow("03/31/2025", "BDO", "T1", Decimal("5000.00"), Decimal("0.00")),
            RemittanceRow("06/30/2025", "BDO", "T2", Decimal("6000.00"), Decimal("100.00")),
            RemittanceRow.empty(),
            RemittanceRow.empty(),
        )
        data = Form1604EData(
            year=2025, is_amended=False, is_private=True, is_top_withholding_agent=False, sched1_rows=rows
        )
        fields = Form1604EGenerator(taxpayer, data).build_fields()

        assert fields["frm1604e:txtSched1TaxWithheldTtl"] == "11,000.00"
        assert fields["frm1604e:txtSched1PenaltiesTtl"] == "100.00"
        assert fields["frm1604e:txtSched1TotRemAmtTtl"] == "11,100.00"

    def test_sched2_row_fields(self, taxpayer, jan_row):
        data = Form1604EData(
            year=2025,
            is_amended=False,
            is_private=True,
            is_top_withholding_agent=False,
            sched2_rows=_make_sched2(**{"1": jan_row}),
        )
        fields = Form1604EGenerator(taxpayer, data).build_fields()

        assert fields["frm1604e:txtSched2RemDate1"] == "01/10/2025"
        assert fields["frm1604e:txtSched2BankCode1"] == "BDO"
        assert fields["frm1604e:txtSched2TRANo1"] == "TRA-001"
        assert fields["frm1604e:txtSched2TaxWithheld1"] == "2,000.00"
        assert fields["frm1604e:txtSched2Penalties1"] == "0.00"
        assert fields["frm1604e:txtSched2TotRemAmt1"] == "2,000.00"

    def test_sched2_has_12_rows(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        for month in range(1, 13):
            assert f"frm1604e:txtSched2TaxWithheld{month}" in fields

    def test_sched2_totals(self, taxpayer):
        rows = list(RemittanceRow.empty() for _ in range(12))
        rows[0] = RemittanceRow("01/10/2025", "BDO", "T01", Decimal("1000.00"), Decimal("0.00"))
        rows[1] = RemittanceRow("02/10/2025", "BDO", "T02", Decimal("1500.00"), Decimal("75.00"))
        data = Form1604EData(
            year=2025, is_amended=False, is_private=True, is_top_withholding_agent=False, sched2_rows=tuple(rows)
        )
        fields = Form1604EGenerator(taxpayer, data).build_fields()

        assert fields["frm1604e:txtSched2TaxWithheldTtl"] == "2,500.00"
        assert fields["frm1604e:txtSched2PenaltiesTtl"] == "75.00"
        assert fields["frm1604e:txtSched2TotRemAmtTtl"] == "2,575.00"

    def test_page2_header_mirrors_page1(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1604e:txtPg2TIN1"] == "010"
        assert fields["frm1604e:txtPg2TIN2"] == "318"
        assert fields["frm1604e:txtPg2TIN3"] == "867"
        assert fields["frm1604e:txtPg2BranchCode"] == "000"
        assert fields["frm1604e:txtPg2TaxpayerName"] == "ABC CORPORATION"

    def test_current_page_always_1(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1604e:txtCurrentPage"] == "1"

    def test_global_flags(self, taxpayer, basic_data):
        fields = Form1604EGenerator(taxpayer, basic_data).build_fields()
        assert fields["txtFinalFlag"] == "0"
        assert fields["txtEnroll"] == "N"
        assert fields["ebirOnlineConfirmUsername"] == ""
        assert fields["ebirOnlineUsername"] == ""
        assert fields["ebirOnlineSecret"] == ""


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


class TestForm1604ERoundTrip:
    def test_save_creates_parseable_file(self, taxpayer, basic_data, tmp_path):
        gen = Form1604EGenerator(taxpayer, basic_data)
        path = gen.save(tmp_path)

        assert path.exists()
        assert path.suffix == ".xml"

        content = path.read_text(encoding="utf-8")
        parsed = parse_ebirforms_file(content)
        assert parsed["frm1604e:txtYear"] == "2025"
        assert parsed["frm1604e:txtWthhldngAgntsNme"] == "ABC CORPORATION"

    def test_round_trip_preserves_money_fields(self, taxpayer):
        rows = (
            RemittanceRow("03/31/2025", "BDO", "T1", Decimal("100000.00"), Decimal("500.00")),
            RemittanceRow.empty(),
            RemittanceRow.empty(),
            RemittanceRow.empty(),
        )
        data = Form1604EData(
            year=2025, is_amended=False, is_private=True, is_top_withholding_agent=False, sched1_rows=rows
        )
        gen = Form1604EGenerator(taxpayer, data)
        original_fields = gen.build_fields()
        content = build_ebirforms_content(original_fields)
        parsed = parse_ebirforms_file(content)

        assert parsed["frm1604e:txtSched1TaxWithheld1"] == "100,000.00"
        assert parsed["frm1604e:txtSched1Penalties1"] == "500.00"
        assert parsed["frm1604e:txtSched1TotRemAmt1"] == "100,500.00"
        assert parsed["frm1604e:txtSched1TaxWithheldTtl"] == "100,000.00"

    def test_round_trip_preserves_all_fields(self, taxpayer, basic_data):
        gen = Form1604EGenerator(taxpayer, basic_data)
        original_fields = gen.build_fields()
        content = build_ebirforms_content(original_fields)
        parsed_fields = parse_ebirforms_file(content)

        for key, value in original_fields.items():
            assert parsed_fields.get(key) == value, f"Field mismatch for {key!r}"

    def test_file_naming_convention(self, taxpayer, basic_data, tmp_path):
        gen = Form1604EGenerator(taxpayer, basic_data)
        path = gen.save(tmp_path)
        assert path.name == "010318867000-1604Ev2018.xml"
