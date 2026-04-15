"""Tests for BIR Form 2000 v2018 generator (Documentary Stamp Tax)."""

from decimal import Decimal

import pytest

from ebirforms.base import TaxpayerInfo, build_ebirforms_content, parse_ebirforms_file
from ebirforms.generators.form_2000 import (
    MODE_EDST,
    MODE_LOOSE,
    PARTY_CREDITOR,
    PARTY_DEBTOR,
    DstLineItem,
    Form2000Data,
    Form2000Generator,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def taxpayer():
    return TaxpayerInfo(
        tin="010-318-867-000",
        rdo_code="032",
        name="ABC CORPORATION",
        trade_name="ABC CORPORATION",
        address="BURGUNDY CORPORATE TOWER MAKATI",
        zip_code="1232",
        telephone="8887-1234",
        email="finance@abc.com",
        line_of_business="REAL ESTATE ACTIVITIES",
    )


@pytest.fixture()
def single_line_item():
    """A simple DS101 line item (original issue of shares)."""
    return DstLineItem(
        atc_code="DS101",
        tax_base=Decimal("100000.00"),
        tax_rate="P2.00 on each P200 or fractional part",
        tax_due=Decimal("1000.00"),
    )


@pytest.fixture()
def basic_data(single_line_item):
    """Minimal Form 2000 data with one line item, no penalties, no credits."""
    return Form2000Data(
        year=2026,
        month=3,
        is_amended=False,
        line_items=(single_line_item,),
    )


@pytest.fixture()
def generator(taxpayer, basic_data):
    return Form2000Generator(taxpayer, basic_data)


# ---------------------------------------------------------------------------
# DstLineItem
# ---------------------------------------------------------------------------


class TestDstLineItem:
    def test_stores_fields(self):
        item = DstLineItem(
            atc_code="DS107",
            tax_base=Decimal("500000.00"),
            tax_rate="1.5% of consideration",
            tax_due=Decimal("7500.00"),
        )
        assert item.atc_code == "DS107"
        assert item.tax_base == Decimal("500000.00")
        assert item.tax_due == Decimal("7500.00")

    def test_is_frozen(self, single_line_item):
        with pytest.raises(AttributeError):
            single_line_item.atc_code = "DS102"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Form2000Data computed properties
# ---------------------------------------------------------------------------


class TestForm2000DataComputation:
    def test_total_tax_due_single_line(self, basic_data):
        assert basic_data.total_tax_due == Decimal("1000.00")

    def test_total_tax_due_multiple_lines(self):
        items = (
            DstLineItem("DS101", Decimal("100000.00"), "", Decimal("1000.00")),
            DstLineItem("DS107", Decimal("500000.00"), "", Decimal("7500.00")),
        )
        data = Form2000Data(year=2026, month=1, is_amended=False, line_items=items)
        assert data.total_tax_due == Decimal("8500.00")

    def test_total_penalties_zero_by_default(self, basic_data):
        assert basic_data.total_penalties == Decimal("0.00")

    def test_total_penalties_sum(self):
        item = DstLineItem("DS101", Decimal("100000.00"), "", Decimal("1000.00"))
        data = Form2000Data(
            year=2026,
            month=3,
            is_amended=False,
            line_items=(item,),
            surcharge=Decimal("250.00"),
            interest=Decimal("50.00"),
            compromise=Decimal("200.00"),
        )
        assert data.total_penalties == Decimal("500.00")

    def test_total_amount_payable_no_penalties(self, basic_data):
        assert basic_data.total_amount_payable == Decimal("1000.00")

    def test_total_amount_payable_with_penalties(self):
        item = DstLineItem("DS101", Decimal("100000.00"), "", Decimal("1000.00"))
        data = Form2000Data(
            year=2026,
            month=3,
            is_amended=False,
            line_items=(item,),
            surcharge=Decimal("250.00"),
            interest=Decimal("50.00"),
            compromise=Decimal("200.00"),
        )
        assert data.total_amount_payable == Decimal("1500.00")

    def test_total_credits_zero_by_default(self, basic_data):
        assert basic_data.total_credits == Decimal("0.00")

    def test_total_credits_sum(self):
        item = DstLineItem("DS101", Decimal("100000.00"), "", Decimal("1000.00"))
        data = Form2000Data(
            year=2026,
            month=3,
            is_amended=False,
            line_items=(item,),
            credit_17a=Decimal("300.00"),
            credit_17b=Decimal("100.00"),
            credit_17c=Decimal("50.00"),
        )
        assert data.total_credits == Decimal("450.00")

    def test_tax_still_due_no_credits(self, basic_data):
        assert basic_data.tax_still_due == Decimal("1000.00")

    def test_tax_still_due_with_credits(self):
        item = DstLineItem("DS101", Decimal("100000.00"), "", Decimal("1000.00"))
        data = Form2000Data(
            year=2026,
            month=3,
            is_amended=False,
            line_items=(item,),
            credit_17a=Decimal("400.00"),
        )
        assert data.tax_still_due == Decimal("600.00")

    def test_total_amount_payable_19_equals_tax_still_due(self, basic_data):
        assert basic_data.total_amount_payable_19 == basic_data.tax_still_due

    def test_is_frozen(self, basic_data):
        with pytest.raises(AttributeError):
            basic_data.year = 2025  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Form2000Generator identity
# ---------------------------------------------------------------------------


class TestForm2000GeneratorIdentity:
    def test_form_number(self, generator):
        assert generator.form_number == "2000v2018"

    def test_form_prefix(self, generator):
        assert generator.form_prefix == "frm2000"


# ---------------------------------------------------------------------------
# Period and amendment fields
# ---------------------------------------------------------------------------


class TestPeriodAndAmendmentFields:
    def test_month_zero_padded(self, generator):
        fields = generator.build_fields()
        assert fields["frm2000:txtMonth"] == "03"

    def test_single_digit_month_padded(self, taxpayer, single_line_item):
        data = Form2000Data(year=2026, month=1, is_amended=False, line_items=(single_line_item,))
        gen = Form2000Generator(taxpayer, data)
        assert gen.build_fields()["frm2000:txtMonth"] == "01"

    def test_year_field(self, generator):
        assert generator.build_fields()["frm2000:txtYear"] == "2026"

    def test_not_amended_radios(self, generator):
        fields = generator.build_fields()
        assert fields["frm2000:AmendedRtn_1"] == "false"
        assert fields["frm2000:AmendedRtn_2"] == "true"

    def test_amended_radios(self, taxpayer, single_line_item):
        data = Form2000Data(year=2026, month=3, is_amended=True, line_items=(single_line_item,))
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2000:AmendedRtn_1"] == "true"
        assert fields["frm2000:AmendedRtn_2"] == "false"

    def test_sheets_default_zero(self, generator):
        assert generator.build_fields()["frm2000:txtSheets"] == "0"

    def test_sheets_custom_value(self, taxpayer, single_line_item):
        data = Form2000Data(year=2026, month=3, is_amended=False, line_items=(single_line_item,), sheets_attached=2)
        gen = Form2000Generator(taxpayer, data)
        assert gen.build_fields()["frm2000:txtSheets"] == "2"


# ---------------------------------------------------------------------------
# Taxpayer identity fields
# ---------------------------------------------------------------------------


class TestTaxpayerFields:
    def test_tin_parts(self, generator):
        fields = generator.build_fields()
        assert fields["frm2000:txtTIN1"] == "010"
        assert fields["frm2000:txtTIN2"] == "318"
        assert fields["frm2000:txtTIN3"] == "867"
        assert fields["frm2000:txtBranchCode"] == "000"

    def test_rdo_code(self, generator):
        assert generator.build_fields()["frm2000:txtRDOCode"] == "032"

    def test_taxpayer_name(self, generator):
        assert generator.build_fields()["frm2000:txtTaxpayerName"] == "ABC CORPORATION"

    def test_address(self, generator):
        assert generator.build_fields()["frm2000:txtAddress"] == "BURGUNDY CORPORATE TOWER MAKATI"

    def test_address2_empty(self, generator):
        assert generator.build_fields()["frm2000:txtAddress2"] == ""

    def test_zip_code(self, generator):
        assert generator.build_fields()["frm2000:txtZipCode"] == "1232"

    def test_telephone(self, generator):
        assert generator.build_fields()["frm2000:txtTelNum"] == "8887-1234"

    def test_email(self, generator):
        assert generator.build_fields()["txtEmail"] == "finance@abc.com"

    def test_line_of_business(self, generator):
        assert generator.build_fields()["frm2000:txtLineBus"] == "REAL ESTATE ACTIVITIES"

    def test_page2_tin_repeat(self, generator):
        fields = generator.build_fields()
        assert fields["frm2000:txtPg2TIN1"] == "010"
        assert fields["frm2000:txtPg2TIN2"] == "318"
        assert fields["frm2000:txtPg2TIN3"] == "867"
        assert fields["frm2000:txtPg2BranchCode"] == "000"

    def test_page2_taxpayer_name(self, generator):
        assert generator.build_fields()["frm2000:txtPg2TaxpayerName"] == "ABC CORPORATION"


# ---------------------------------------------------------------------------
# Mode of affixture radios
# ---------------------------------------------------------------------------


class TestModeOfAffixture:
    def test_constructive_mode_default(self, generator):
        fields = generator.build_fields()
        assert fields["frm2000:optMode_1"] == "false"
        assert fields["frm2000:optMode_2"] == "true"
        assert fields["frm2000:optMode_3"] == "false"

    def test_edst_mode(self, taxpayer, single_line_item):
        data = Form2000Data(year=2026, month=3, is_amended=False, line_items=(single_line_item,), mode=MODE_EDST)
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2000:optMode_1"] == "true"
        assert fields["frm2000:optMode_2"] == "false"
        assert fields["frm2000:optMode_3"] == "false"

    def test_loose_stamps_mode(self, taxpayer, single_line_item):
        data = Form2000Data(year=2026, month=3, is_amended=False, line_items=(single_line_item,), mode=MODE_LOOSE)
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2000:optMode_1"] == "false"
        assert fields["frm2000:optMode_2"] == "false"
        assert fields["frm2000:optMode_3"] == "true"


# ---------------------------------------------------------------------------
# Other party radios
# ---------------------------------------------------------------------------


class TestOtherPartyFields:
    def test_none_by_default(self, generator):
        fields = generator.build_fields()
        assert fields["frm2000:optParty_1"] == "false"
        assert fields["frm2000:optParty_2"] == "false"
        assert fields["frm2000:optParty_3"] == "true"

    def test_creditor_party(self, taxpayer, single_line_item):
        data = Form2000Data(
            year=2026,
            month=3,
            is_amended=False,
            line_items=(single_line_item,),
            other_party=PARTY_CREDITOR,
            other_party_name="LENDER BANK INC",
            other_party_tin="123-456-789-000",
        )
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2000:optParty_1"] == "true"
        assert fields["frm2000:optParty_2"] == "false"
        assert fields["frm2000:optParty_3"] == "false"
        assert fields["frm2000:txtOtherName"] == "LENDER BANK INC"
        assert fields["frm2000:txtOtherTIN"] == "123-456-789-000"

    def test_debtor_party(self, taxpayer, single_line_item):
        data = Form2000Data(
            year=2026,
            month=3,
            is_amended=False,
            line_items=(single_line_item,),
            other_party=PARTY_DEBTOR,
        )
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2000:optParty_2"] == "true"
        assert fields["frm2000:optParty_1"] == "false"

    def test_other_name2_always_empty(self, generator):
        assert generator.build_fields()["frm2000:txtOtherName2"] == ""

    def test_other_tin_empty_by_default(self, generator):
        assert generator.build_fields()["frm2000:txtOtherTIN"] == ""


# ---------------------------------------------------------------------------
# Schedule 1 fields
# ---------------------------------------------------------------------------


class TestSchedule1Fields:
    def test_single_line_item_fields(self, generator):
        fields = generator.build_fields()
        assert fields["drpATCCode0"] == "DS101"
        assert fields["frm2000:sched1:txtTaxBase0"] == "100,000.00"
        assert fields["frm2000:sched1:txtTaxRate0"] == "P2.00 on each P200 or fractional part"
        assert fields["frm2000:sched1:txtTaxDue0"] == "1,000.00"

    def test_total_due_single_line(self, generator):
        assert generator.build_fields()["frm2000:sched1:txtTotalDue1"] == "1,000.00"

    def test_multiple_line_items(self, taxpayer):
        items = (
            DstLineItem("DS101", Decimal("100000.00"), "P2 per 200", Decimal("1000.00")),
            DstLineItem("DS107", Decimal("500000.00"), "1.5% of consideration", Decimal("7500.00")),
            DstLineItem("DS103", Decimal("1000.00"), "P3.00 per stub", Decimal("3.00")),
        )
        data = Form2000Data(year=2026, month=3, is_amended=False, line_items=items)
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["drpATCCode0"] == "DS101"
        assert fields["drpATCCode1"] == "DS107"
        assert fields["drpATCCode2"] == "DS103"
        assert fields["frm2000:sched1:txtTaxBase1"] == "500,000.00"
        assert fields["frm2000:sched1:txtTaxDue1"] == "7,500.00"
        assert fields["frm2000:sched1:txtTotalDue1"] == "8,503.00"

    def test_tax_base_formatted_with_commas(self, taxpayer):
        item = DstLineItem("DS107", Decimal("1234567.89"), "", Decimal("18518.52"))
        data = Form2000Data(year=2026, month=3, is_amended=False, line_items=(item,))
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2000:sched1:txtTaxBase0"] == "1,234,567.89"


# ---------------------------------------------------------------------------
# Special ATC term fields
# ---------------------------------------------------------------------------


class TestSpecialAtcTermFields:
    def test_defaults_to_zero(self, generator):
        fields = generator.build_fields()
        assert fields["frm2000:numOfDays"] == "0"
        assert fields["frm2000:numOfMonths"] == "0"
        assert fields["frm2000:numOfMonths131"] == "0"
        assert fields["frm2000:numOfMonths132"] == "0"

    def test_ds106_num_of_days(self, taxpayer):
        item = DstLineItem("DS106", Decimal("1000000.00"), "1.5/200 x days/365", Decimal("20547.95"))
        data = Form2000Data(year=2026, month=3, is_amended=False, line_items=(item,), num_of_days=365)
        gen = Form2000Generator(taxpayer, data)
        assert gen.build_fields()["frm2000:numOfDays"] == "365"

    def test_ds130_num_of_months(self, taxpayer):
        item = DstLineItem("DS130", Decimal("500000.00"), "", Decimal("10000.00"))
        data = Form2000Data(year=2026, month=3, is_amended=False, line_items=(item,), num_of_months=12)
        gen = Form2000Generator(taxpayer, data)
        assert gen.build_fields()["frm2000:numOfMonths"] == "12"


# ---------------------------------------------------------------------------
# Tax computation fields (Part III)
# ---------------------------------------------------------------------------


class TestTaxComputationFields:
    def test_basic_computation_no_penalties_no_credits(self, generator):
        fields = generator.build_fields()
        assert fields["frm2000:txtTax14"] == "1,000.00"
        assert fields["frm2000:txtTax15A"] == "0.00"
        assert fields["frm2000:txtTax15B"] == "0.00"
        assert fields["frm2000:txtTax15C"] == "0.00"
        assert fields["frm2000:txtTax15D"] == "0.00"
        assert fields["frm2000:txtTax16"] == "1,000.00"
        assert fields["frm2000:txtTax17A"] == "0.00"
        assert fields["frm2000:txtTax17B"] == "0.00"
        assert fields["frm2000:txtTax17C"] == "0.00"
        assert fields["frm2000:txtTax17D"] == "0.00"
        assert fields["frm2000:txtTax18"] == "1,000.00"
        assert fields["frm2000:txtTax19"] == "1,000.00"

    def test_computation_with_penalties(self, taxpayer, single_line_item):
        data = Form2000Data(
            year=2026,
            month=3,
            is_amended=False,
            line_items=(single_line_item,),
            surcharge=Decimal("250.00"),
            interest=Decimal("50.00"),
            compromise=Decimal("200.00"),
        )
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm2000:txtTax14"] == "1,000.00"
        assert fields["frm2000:txtTax15A"] == "250.00"
        assert fields["frm2000:txtTax15B"] == "50.00"
        assert fields["frm2000:txtTax15C"] == "200.00"
        assert fields["frm2000:txtTax15D"] == "500.00"
        assert fields["frm2000:txtTax16"] == "1,500.00"
        assert fields["frm2000:txtTax18"] == "1,500.00"
        assert fields["frm2000:txtTax19"] == "1,500.00"

    def test_computation_with_credits(self, taxpayer, single_line_item):
        data = Form2000Data(
            year=2026,
            month=3,
            is_amended=False,
            line_items=(single_line_item,),
            credit_17a=Decimal("300.00"),
            credit_17b=Decimal("100.00"),
            credit_17c=Decimal("50.00"),
        )
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm2000:txtTax17A"] == "300.00"
        assert fields["frm2000:txtTax17B"] == "100.00"
        assert fields["frm2000:txtTax17C"] == "50.00"
        assert fields["frm2000:txtTax17D"] == "450.00"
        assert fields["frm2000:txtTax18"] == "550.00"  # 1000 - 450
        assert fields["frm2000:txtTax19"] == "550.00"

    def test_large_amount_formatted_with_commas(self, taxpayer):
        item = DstLineItem("DS107", Decimal("10000000.00"), "", Decimal("150000.00"))
        data = Form2000Data(year=2026, month=3, is_amended=False, line_items=(item,))
        gen = Form2000Generator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2000:txtTax14"] == "150,000.00"
        assert fields["frm2000:txtTax16"] == "150,000.00"
        assert fields["frm2000:txtTax19"] == "150,000.00"


# ---------------------------------------------------------------------------
# Payment and agent fields
# ---------------------------------------------------------------------------


class TestPaymentAndAgentFields:
    def test_payment_fields_empty(self, generator):
        fields = generator.build_fields()
        for item in ("20", "21", "22", "23"):
            assert fields[f"frm2000:txtAgency{item}"] == ""
            assert fields[f"frm2000:txtNumber{item}"] == ""
            assert fields[f"frm2000:txtDate{item}"] == ""
            assert fields[f"frm2000:txtAmount{item}"] == ""

    def test_particular_fields_empty(self, generator):
        fields = generator.build_fields()
        assert fields["frm2000:txtParticular36"] == ""
        assert fields["frm2000:txtParticular23"] == ""

    def test_tax_agent_fields_empty(self, generator):
        fields = generator.build_fields()
        assert fields["txtTaxAgentNo"] == ""
        assert fields["txtDateIssue"] == ""
        assert fields["txtDateExpiry"] == ""


# ---------------------------------------------------------------------------
# Flags and system fields
# ---------------------------------------------------------------------------


class TestFlagFields:
    def test_final_flag(self, generator):
        assert generator.build_fields()["txtFinalFlag"] == "0"

    def test_enroll_flag(self, generator):
        assert generator.build_fields()["txtEnroll"] == "N"

    def test_current_page_always_one(self, generator):
        assert generator.build_fields()["frm2000:txtCurrentPage"] == "1"

    def test_ebir_online_fields_empty(self, generator):
        fields = generator.build_fields()
        assert fields["ebirOnlineSecret"] == ""
        assert fields["ebirOnlineUsername"] == ""


# ---------------------------------------------------------------------------
# Round-trip: save -> parse -> verify
# ---------------------------------------------------------------------------


class TestForm2000RoundTrip:
    def test_save_creates_xml_file(self, generator, tmp_path):
        path = generator.save(tmp_path)
        assert path.exists()
        assert path.suffix == ".xml"

    def test_default_filename_uses_tin_and_form_number(self, generator, tmp_path):
        path = generator.save(tmp_path)
        assert path.name == "010318867000-2000v2018.xml"

    def test_custom_filename(self, generator, tmp_path):
        path = generator.save(tmp_path, filename="custom.xml")
        assert path.name == "custom.xml"

    def test_saved_file_round_trips_key_fields(self, generator, tmp_path):
        path = generator.save(tmp_path)
        content = path.read_text(encoding="utf-8")
        fields = parse_ebirforms_file(content)

        assert fields["frm2000:txtMonth"] == "03"
        assert fields["frm2000:txtYear"] == "2026"
        assert fields["frm2000:txtTIN1"] == "010"
        assert fields["frm2000:txtTax14"] == "1,000.00"
        assert fields["frm2000:txtTax19"] == "1,000.00"

    def test_build_fields_round_trips_via_content(self, generator):
        original = generator.build_fields()
        content = build_ebirforms_content(original)
        parsed = parse_ebirforms_file(content)

        for key in (
            "frm2000:txtMonth",
            "frm2000:txtYear",
            "frm2000:txtTaxpayerName",
            "frm2000:txtTax14",
            "frm2000:txtTax19",
            "drpATCCode0",
        ):
            assert parsed[key] == original[key], f"Mismatch on {key}"

    def test_round_trip_with_multiple_line_items(self, taxpayer, tmp_path):
        items = (
            DstLineItem("DS101", Decimal("100000.00"), "P2 per 200", Decimal("1000.00")),
            DstLineItem("DS107", Decimal("500000.00"), "1.5%", Decimal("7500.00")),
        )
        data = Form2000Data(year=2026, month=6, is_amended=False, line_items=items)
        gen = Form2000Generator(taxpayer, data)
        path = gen.save(tmp_path)

        content = path.read_text(encoding="utf-8")
        fields = parse_ebirforms_file(content)

        assert fields["drpATCCode0"] == "DS101"
        assert fields["drpATCCode1"] == "DS107"
        assert fields["frm2000:sched1:txtTotalDue1"] == "8,500.00"
        assert fields["frm2000:txtTax14"] == "8,500.00"
