"""Tests for BIR Form 0619-F generator."""

from decimal import Decimal

import pytest

from ebirforms.base import TaxpayerInfo, build_ebirforms_content, parse_ebirforms_file
from ebirforms.generators.form_0619f import (
    TAX_TYPE_WB,
    TAX_TYPE_WF,
    Form0619FData,
    Form0619FGenerator,
)


@pytest.fixture()
def taxpayer():
    return TaxpayerInfo(
        tin="010-318-867-000",
        rdo_code="032",
        name="abc corporation",
        trade_name="abc corporation",
        address="BURGUNDY CORPORATE TOWER MAKATI",
        zip_code="1232",
        telephone="",
        email="joseph@proseso-consulting.com",
        line_of_business="OTHER SERVICE ACTIVITIES",
    )


@pytest.fixture()
def wf_data():
    """Standard WF (Final) tax data."""
    return Form0619FData(
        year=2026,
        month=3,
        is_amended=False,
        tax_type_code=TAX_TYPE_WF,
        is_private=True,
        business_tax=Decimal("0.00"),
        final_tax=Decimal("15000.00"),
        adjustment=Decimal("0.00"),
        surcharge=Decimal("0.00"),
        interest=Decimal("0.00"),
        compromise=Decimal("0.00"),
    )


@pytest.fixture()
def wb_data():
    """Standard WB (Business) tax data."""
    return Form0619FData(
        year=2026,
        month=3,
        is_amended=False,
        tax_type_code=TAX_TYPE_WB,
        is_private=True,
        business_tax=Decimal("8000.00"),
        final_tax=Decimal("0.00"),
        adjustment=Decimal("0.00"),
        surcharge=Decimal("0.00"),
        interest=Decimal("0.00"),
        compromise=Decimal("0.00"),
    )


class TestForm0619FDataComputation:
    def test_total_withheld_wf(self, wf_data):
        assert wf_data.total_withheld == Decimal("15000.00")

    def test_total_withheld_wb(self, wb_data):
        assert wb_data.total_withheld == Decimal("8000.00")

    def test_total_withheld_is_sum_of_13_and_14(self):
        data = Form0619FData(
            year=2026,
            month=1,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("1000.00"),
            final_tax=Decimal("2000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        assert data.total_withheld == Decimal("3000.00")

    def test_net_amount_to_remit_no_adjustment(self, wf_data):
        assert wf_data.net_amount_to_remit == Decimal("15000.00")

    def test_net_amount_to_remit_with_adjustment(self):
        data = Form0619FData(
            year=2026,
            month=3,
            is_amended=True,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("20000.00"),
            adjustment=Decimal("5000.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        assert data.net_amount_to_remit == Decimal("15000.00")

    def test_total_penalties_sum(self):
        data = Form0619FData(
            year=2026,
            month=3,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("10000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("2500.00"),
            interest=Decimal("300.00"),
            compromise=Decimal("200.00"),
        )
        assert data.total_penalties == Decimal("3000.00")

    def test_total_amount_payable_with_penalties(self):
        data = Form0619FData(
            year=2026,
            month=3,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("10000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("2500.00"),
            interest=Decimal("300.00"),
            compromise=Decimal("200.00"),
        )
        # 10000 + 3000 = 13000
        assert data.total_amount_payable == Decimal("13000.00")

    def test_total_amount_payable_no_penalties(self, wf_data):
        assert wf_data.total_amount_payable == Decimal("15000.00")


class TestDueDateLogic:
    def test_march_due_date_is_april(self, wf_data):
        assert wf_data.due_month == 4
        assert wf_data.due_year == 2026

    def test_december_due_date_rolls_to_january_next_year(self):
        data = Form0619FData(
            year=2026,
            month=12,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("5000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        assert data.due_month == 1
        assert data.due_year == 2027

    def test_november_due_date_is_december_same_year(self):
        data = Form0619FData(
            year=2026,
            month=11,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("5000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        assert data.due_month == 12
        assert data.due_year == 2026

    def test_january_due_date_is_february(self):
        data = Form0619FData(
            year=2026,
            month=1,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("5000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        assert data.due_month == 2
        assert data.due_year == 2026


class TestForm0619FGeneratorFields:
    def test_form_number(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        assert gen.form_number == "0619F"

    def test_form_prefix(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        assert gen.form_prefix == "frm0619F"

    def test_period_fields(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["frm0619F:txtMonth"] == "03"
        assert fields["frm0619F:txtYear"] == "2026"

    def test_due_date_fields(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["frm0619F:txtDueMonth"] == "04"
        assert fields["frm0619F:txtDueDay"] == "10"
        assert fields["frm0619F:txtDueYear"] == "2026"

    def test_december_due_date_in_fields(self, taxpayer):
        data = Form0619FData(
            year=2026,
            month=12,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("5000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        gen = Form0619FGenerator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm0619F:txtDueMonth"] == "01"
        assert fields["frm0619F:txtDueYear"] == "2027"

    def test_amendment_flags_not_amended(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["frm0619F:optAmend:Y"] == "false"
        assert fields["frm0619F:optAmend:N"] == "true"

    def test_amendment_flags_amended(self, taxpayer):
        data = Form0619FData(
            year=2026,
            month=3,
            is_amended=True,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("15000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        gen = Form0619FGenerator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm0619F:optAmend:Y"] == "true"
        assert fields["frm0619F:optAmend:N"] == "false"

    def test_withheld_flags_when_tax_present(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["frm0619F:optWithheld:Y"] == "true"
        assert fields["frm0619F:optWithheld:N"] == "false"

    def test_withheld_flags_when_no_tax(self, taxpayer):
        data = Form0619FData(
            year=2026,
            month=3,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("0.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        gen = Form0619FGenerator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm0619F:optWithheld:Y"] == "false"
        assert fields["frm0619F:optWithheld:N"] == "true"

    def test_wf_tax_type_code(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["frm0619F:txtTaxTypeCode"] == "WF"

    def test_wb_tax_type_code(self, taxpayer, wb_data):
        gen = Form0619FGenerator(taxpayer, wb_data)
        fields = gen.build_fields()
        assert fields["frm0619F:txtTaxTypeCode"] == "WB"

    def test_taxpayer_tin_fields(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["frm0619F:txtTIN1"] == "010"
        assert fields["frm0619F:txtTIN2"] == "318"
        assert fields["frm0619F:txtTIN3"] == "867"
        assert fields["frm0619F:txtBranchCode"] == "000"

    def test_taxpayer_rdo_code(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["frm0619F:txtRDOCode"] == "032"

    def test_taxpayer_name(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["frm0619F:txtTaxpayerName"] == "abc corporation"

    def test_category_private(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["frm0619F:optCategory:P"] == "true"
        assert fields["frm0619F:optCategory:G"] == "false"

    def test_category_government(self, taxpayer):
        data = Form0619FData(
            year=2026,
            month=3,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=False,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("5000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        gen = Form0619FGenerator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm0619F:optCategory:P"] == "false"
        assert fields["frm0619F:optCategory:G"] == "true"

    def test_flags(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["txtFinalFlag"] == "0"
        assert fields["txtEnroll"] == "N"

    def test_payment_detail_fields_are_empty(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        for item in ("20", "21", "22", "23"):
            assert fields[f"txtAgency{item}"] == ""
            assert fields[f"txtNumber{item}"] == ""
            assert fields[f"txtDate{item}"] == ""
            assert fields[f"txtAmount{item}"] == ""

    def test_tax_agent_fields_are_empty(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()
        assert fields["txtTaxAgentNo"] == ""
        assert fields["txtDateIssue"] == ""
        assert fields["txtDateExpiry"] == ""


class TestForm0619FTaxComputation:
    def test_wf_basic_computation(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        fields = gen.build_fields()

        assert fields["frm0619F:txtTax13"] == "0.00"
        assert fields["frm0619F:txtTax14"] == "15,000.00"
        assert fields["frm0619F:txtTax15"] == "15,000.00"
        assert fields["frm0619F:txtTax16"] == "0.00"
        assert fields["frm0619F:txtTax17"] == "15,000.00"
        assert fields["frm0619F:txtTax18A"] == "0.00"
        assert fields["frm0619F:txtTax18B"] == "0.00"
        assert fields["frm0619F:txtTax18C"] == "0.00"
        assert fields["frm0619F:txtTax18D"] == "0.00"
        assert fields["frm0619F:txtTax19"] == "15,000.00"

    def test_wb_basic_computation(self, taxpayer, wb_data):
        gen = Form0619FGenerator(taxpayer, wb_data)
        fields = gen.build_fields()

        assert fields["frm0619F:txtTax13"] == "8,000.00"
        assert fields["frm0619F:txtTax14"] == "0.00"
        assert fields["frm0619F:txtTax15"] == "8,000.00"
        assert fields["frm0619F:txtTax17"] == "8,000.00"
        assert fields["frm0619F:txtTax19"] == "8,000.00"

    def test_computation_with_adjustment(self, taxpayer):
        data = Form0619FData(
            year=2026,
            month=3,
            is_amended=True,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("25000.00"),
            adjustment=Decimal("5000.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        gen = Form0619FGenerator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm0619F:txtTax14"] == "25,000.00"
        assert fields["frm0619F:txtTax15"] == "25,000.00"
        assert fields["frm0619F:txtTax16"] == "5,000.00"
        assert fields["frm0619F:txtTax17"] == "20,000.00"  # 25k - 5k
        assert fields["frm0619F:txtTax19"] == "20,000.00"

    def test_computation_with_penalties(self, taxpayer):
        data = Form0619FData(
            year=2026,
            month=3,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("10000.00"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("2500.00"),
            interest=Decimal("300.00"),
            compromise=Decimal("200.00"),
        )
        gen = Form0619FGenerator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm0619F:txtTax17"] == "10,000.00"
        assert fields["frm0619F:txtTax18A"] == "2,500.00"
        assert fields["frm0619F:txtTax18B"] == "300.00"
        assert fields["frm0619F:txtTax18C"] == "200.00"
        assert fields["frm0619F:txtTax18D"] == "3,000.00"  # 2500 + 300 + 200
        assert fields["frm0619F:txtTax19"] == "13,000.00"  # 10k + 3k

    def test_large_amounts_formatted_with_commas(self, taxpayer):
        data = Form0619FData(
            year=2026,
            month=3,
            is_amended=False,
            tax_type_code=TAX_TYPE_WF,
            is_private=True,
            business_tax=Decimal("0.00"),
            final_tax=Decimal("1234567.89"),
            adjustment=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        gen = Form0619FGenerator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm0619F:txtTax14"] == "1,234,567.89"


class TestForm0619FRoundTrip:
    def test_save_creates_xml_file(self, taxpayer, wf_data, tmp_path):
        gen = Form0619FGenerator(taxpayer, wf_data)
        path = gen.save(tmp_path)

        assert path.exists()
        assert path.suffix == ".xml"

    def test_default_filename_uses_tin_and_form_number(self, taxpayer, wf_data, tmp_path):
        gen = Form0619FGenerator(taxpayer, wf_data)
        path = gen.save(tmp_path)
        assert path.name == "010318867000-0619F.xml"

    def test_saved_file_round_trips(self, taxpayer, wf_data, tmp_path):
        gen = Form0619FGenerator(taxpayer, wf_data)
        path = gen.save(tmp_path)

        content = path.read_text(encoding="utf-8")
        fields = parse_ebirforms_file(content)

        assert fields["frm0619F:txtTax14"] == "15,000.00"
        assert fields["frm0619F:txtTax19"] == "15,000.00"

    def test_build_fields_round_trips_via_content(self, taxpayer, wf_data):
        gen = Form0619FGenerator(taxpayer, wf_data)
        original_fields = gen.build_fields()
        content = build_ebirforms_content(original_fields)
        parsed_fields = parse_ebirforms_file(content)

        for key in ("frm0619F:txtMonth", "frm0619F:txtTaxTypeCode", "frm0619F:txtTax19"):
            assert parsed_fields[key] == original_fields[key]
