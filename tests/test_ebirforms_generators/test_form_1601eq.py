"""Tests for BIR Form 1601-EQ generator."""

from decimal import Decimal

import pytest

from ebirforms.base import TaxpayerInfo, build_ebirforms_content, parse_ebirforms_file
from ebirforms.generators.form_1601eq import AtcEntry, Form1601EQData, Form1601EQGenerator


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
def single_atc_entry():
    return AtcEntry(
        atc_code="WE011",
        tax_base=Decimal("100000.00"),
        tax_rate=Decimal("2.00"),
    )


@pytest.fixture()
def basic_data(single_atc_entry):
    return Form1601EQData(
        year=2026,
        quarter=1,
        is_amended=False,
        is_private=True,
        atc_entries=(single_atc_entry,),
        remittance_month1=Decimal("1000.00"),
        remittance_month2=Decimal("1000.00"),
        previously_remitted_amended=Decimal("0.00"),
        over_remittance_prior_quarter=Decimal("0.00"),
        surcharge=Decimal("0.00"),
        interest=Decimal("0.00"),
        compromise=Decimal("0.00"),
    )


class TestAtcEntry:
    def test_tax_withheld_calculation(self):
        entry = AtcEntry("WE011", Decimal("100000.00"), Decimal("2.00"))
        assert entry.tax_withheld == Decimal("2000.00")

    def test_tax_withheld_rounds_to_two_decimals(self):
        entry = AtcEntry("WE030", Decimal("33333.33"), Decimal("1.00"))
        assert entry.tax_withheld == Decimal("333.33")

    def test_zero_tax_base(self):
        entry = AtcEntry("WE011", Decimal("0.00"), Decimal("2.00"))
        assert entry.tax_withheld == Decimal("0.00")


class TestForm1601EQDataProperties:
    def test_total_withheld_single_entry(self, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        assert data.total_withheld == Decimal("2000.00")

    def test_total_withheld_multiple_entries(self):
        entries = (
            AtcEntry("WE011", Decimal("100000.00"), Decimal("2.00")),  # 2000.00
            AtcEntry("WE150", Decimal("50000.00"), Decimal("5.00")),  # 2500.00
        )
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=entries,
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        assert data.total_withheld == Decimal("4500.00")

    def test_total_remittances(self, basic_data):
        # remittance_month1=1000 + remittance_month2=1000 + 0 + 0 = 2000
        assert basic_data.total_remittances == Decimal("2000.00")

    def test_tax_still_due(self, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("1000.00"),
            remittance_month2=Decimal("500.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        # total_withheld=2000, total_remittances=1500
        assert data.tax_still_due == Decimal("500.00")

    def test_tax_still_due_over_remittance(self, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("1500.00"),
            remittance_month2=Decimal("1000.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        # total_withheld=2000, total_remittances=2500 -> negative (over-remittance)
        assert data.tax_still_due == Decimal("-500.00")

    def test_total_penalties(self, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("100.00"),
            interest=Decimal("50.00"),
            compromise=Decimal("25.00"),
        )
        assert data.total_penalties == Decimal("175.00")

    def test_total_amount_due(self, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("100.00"),
            interest=Decimal("50.00"),
            compromise=Decimal("25.00"),
        )
        # tax_still_due=2000 + penalties=175
        assert data.total_amount_due == Decimal("2175.00")

    def test_has_withheld_true(self, basic_data):
        assert basic_data.has_withheld is True

    def test_has_withheld_false_empty_entries(self):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=(),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        assert data.has_withheld is False


class TestForm1601EQGeneratorFields:
    def test_period_fields(self, taxpayer, basic_data):
        gen = Form1601EQGenerator(taxpayer, basic_data)
        fields = gen.build_fields()

        assert fields["frm1601EQ:txtYear"] == "2026"

    def test_quarter_radio_buttons(self, taxpayer, basic_data):
        gen = Form1601EQGenerator(taxpayer, basic_data)
        fields = gen.build_fields()

        assert fields["frm1601EQ:optQuarter:1"] == "true"
        assert fields["frm1601EQ:optQuarter:2"] == "false"
        assert fields["frm1601EQ:optQuarter:3"] == "false"
        assert fields["frm1601EQ:optQuarter:4"] == "false"

    def test_quarter_4_radio_buttons(self, taxpayer, basic_data):
        data = Form1601EQData(
            year=basic_data.year,
            quarter=4,
            is_amended=basic_data.is_amended,
            is_private=basic_data.is_private,
            atc_entries=basic_data.atc_entries,
            remittance_month1=basic_data.remittance_month1,
            remittance_month2=basic_data.remittance_month2,
            previously_remitted_amended=basic_data.previously_remitted_amended,
            over_remittance_prior_quarter=basic_data.over_remittance_prior_quarter,
            surcharge=basic_data.surcharge,
            interest=basic_data.interest,
            compromise=basic_data.compromise,
        )
        fields = Form1601EQGenerator(taxpayer, data).build_fields()

        assert fields["frm1601EQ:optQuarter:1"] == "false"
        assert fields["frm1601EQ:optQuarter:4"] == "true"

    def test_amend_no(self, taxpayer, basic_data):
        gen = Form1601EQGenerator(taxpayer, basic_data)
        fields = gen.build_fields()

        assert fields["frm1601EQ:optAmend:N"] == "true"
        assert fields["frm1601EQ:optAmend:Y"] == "false"

    def test_amend_yes(self, taxpayer, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=True,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("1500.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        fields = Form1601EQGenerator(taxpayer, data).build_fields()

        assert fields["frm1601EQ:optAmend:Y"] == "true"
        assert fields["frm1601EQ:optAmend:N"] == "false"

    def test_withheld_yes(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1601EQ:optWithheld:Y"] == "true"
        assert fields["frm1601EQ:optWithheld:N"] == "false"

    def test_withheld_no(self, taxpayer):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=(),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        fields = Form1601EQGenerator(taxpayer, data).build_fields()
        assert fields["frm1601EQ:optWithheld:Y"] == "false"
        assert fields["frm1601EQ:optWithheld:N"] == "true"

    def test_taxpayer_tin_fields(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1601EQ:txtTIN1"] == "010"
        assert fields["frm1601EQ:txtTIN2"] == "318"
        assert fields["frm1601EQ:txtTIN3"] == "867"
        assert fields["frm1601EQ:txtBranchCode"] == "000"

    def test_taxpayer_name_and_address(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1601EQ:txtTaxpayerName"] == "ABC CORPORATION"
        assert fields["frm1601EQ:txtRDOCode"] == "032"
        assert fields["frm1601EQ:txtAddress"] == "BURGUNDY CORPORATE TOWER MAKATI"
        assert fields["frm1601EQ:txtZipCode"] == "1232"

    def test_category_private(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1601EQ:optCategory:P"] == "true"
        assert fields["frm1601EQ:optCategory:G"] == "false"

    def test_category_government(self, taxpayer, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=False,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        fields = Form1601EQGenerator(taxpayer, data).build_fields()
        assert fields["frm1601EQ:optCategory:P"] == "false"
        assert fields["frm1601EQ:optCategory:G"] == "true"

    def test_atc_row_fields(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1601EQ:txtAtcCd1"] == "WE011"
        assert fields["frm1601EQ:txtTaxBase1"] == "100,000.00"
        assert fields["frm1601EQ:txtTaxRate1"] == "2.00"
        assert fields["frm1601EQ:txtTaxbeWithHeld1"] == "2,000.00"

    def test_multiple_atc_rows(self, taxpayer):
        entries = (
            AtcEntry("WE011", Decimal("100000.00"), Decimal("2.00")),
            AtcEntry("WE150", Decimal("50000.00"), Decimal("5.00")),
        )
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=entries,
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        fields = Form1601EQGenerator(taxpayer, data).build_fields()

        assert fields["frm1601EQ:txtAtcCd1"] == "WE011"
        assert fields["frm1601EQ:txtTaxbeWithHeld1"] == "2,000.00"
        assert fields["frm1601EQ:txtAtcCd2"] == "WE150"
        assert fields["frm1601EQ:txtTaxbeWithHeld2"] == "2,500.00"
        assert fields["frm1601EQ:txtTax19"] == "4,500.00"

    def test_tax_computation_fields(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()

        # basic_data: total_withheld=2000, month1=1000, month2=1000
        assert fields["frm1601EQ:txtTax19"] == "2,000.00"
        assert fields["frm1601EQ:txtTax20"] == "1,000.00"
        assert fields["frm1601EQ:txtTax21"] == "1,000.00"
        assert fields["frm1601EQ:txtTax22"] == "0.00"
        assert fields["frm1601EQ:txtTax23"] == "0.00"
        assert fields["frm1601EQ:txtTax24"] == "2,000.00"
        assert fields["frm1601EQ:txtTax25"] == "0.00"
        assert fields["frm1601EQ:txtTax26"] == "0.00"
        assert fields["frm1601EQ:txtTax27"] == "0.00"
        assert fields["frm1601EQ:txtTax28"] == "0.00"
        assert fields["frm1601EQ:txtTax29"] == "0.00"
        assert fields["frm1601EQ:txtTax30"] == "0.00"

    def test_penalties_flow(self, taxpayer, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("100.00"),
            interest=Decimal("50.00"),
            compromise=Decimal("25.00"),
        )
        fields = Form1601EQGenerator(taxpayer, data).build_fields()

        assert fields["frm1601EQ:txtTax26"] == "100.00"
        assert fields["frm1601EQ:txtTax27"] == "50.00"
        assert fields["frm1601EQ:txtTax28"] == "25.00"
        assert fields["frm1601EQ:txtTax29"] == "175.00"
        assert fields["frm1601EQ:txtTax30"] == "2,175.00"

    def test_over_remittance_checkboxes_default_false(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1601EQ:ifRefund"] == "false"
        assert fields["frm1601EQ:ifIssueCert"] == "false"
        assert fields["frm1601EQ:ifCarriedOver"] == "false"

    def test_over_remittance_carried_over(self, taxpayer, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=1,
            is_amended=False,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("3000.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
            if_carried_over=True,
        )
        fields = Form1601EQGenerator(taxpayer, data).build_fields()
        assert fields["frm1601EQ:ifCarriedOver"] == "true"
        assert fields["frm1601EQ:ifRefund"] == "false"
        assert fields["frm1601EQ:ifIssueCert"] == "false"

    def test_payment_fields_empty(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()
        for item in ("33", "34", "35", "36"):
            assert fields[f"frm1601EQ:txtAgency{item}"] == ""
            assert fields[f"frm1601EQ:txtNumber{item}"] == ""
            assert fields[f"frm1601EQ:txtDate{item}"] == ""
            assert fields[f"frm1601EQ:txtAmount{item}"] == ""

    def test_flags(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()
        assert fields["txtFinalFlag"] == "0"
        assert fields["txtEnroll"] == "N"
        assert fields["txtTaxAgentNo"] == ""

    def test_form_number(self, taxpayer, basic_data):
        gen = Form1601EQGenerator(taxpayer, basic_data)
        assert gen.form_number == "1601EQ"

    def test_form_prefix(self, taxpayer, basic_data):
        gen = Form1601EQGenerator(taxpayer, basic_data)
        assert gen.form_prefix == "frm1601EQ"


class TestForm1601EQRoundTrip:
    def test_save_creates_parseable_file(self, taxpayer, basic_data, tmp_path):
        gen = Form1601EQGenerator(taxpayer, basic_data)
        path = gen.save(tmp_path)

        assert path.exists()
        assert path.suffix == ".xml"

        content = path.read_text(encoding="utf-8")
        fields = parse_ebirforms_file(content)
        assert fields["frm1601EQ:txtYear"] == "2026"
        assert fields["frm1601EQ:txtTax19"] == "2,000.00"

    def test_round_trip_preserves_all_fields(self, taxpayer, basic_data):
        gen = Form1601EQGenerator(taxpayer, basic_data)
        original_fields = gen.build_fields()
        content = build_ebirforms_content(original_fields)
        parsed_fields = parse_ebirforms_file(content)

        for key, value in original_fields.items():
            assert parsed_fields.get(key) == value, f"Field mismatch for {key!r}"

    def test_no_sheets_default(self, taxpayer, basic_data):
        fields = Form1601EQGenerator(taxpayer, basic_data).build_fields()
        assert fields["frm1601EQ:txtNoSheets"] == "0"

    def test_no_sheets_custom(self, taxpayer, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=2,
            is_amended=False,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("0.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
            no_sheets=3,
        )
        fields = Form1601EQGenerator(taxpayer, data).build_fields()
        assert fields["frm1601EQ:txtNoSheets"] == "3"

    def test_over_remittance_from_prior_quarter(self, taxpayer, single_atc_entry):
        data = Form1601EQData(
            year=2026,
            quarter=2,
            is_amended=False,
            is_private=True,
            atc_entries=(single_atc_entry,),
            remittance_month1=Decimal("0.00"),
            remittance_month2=Decimal("0.00"),
            previously_remitted_amended=Decimal("0.00"),
            over_remittance_prior_quarter=Decimal("500.00"),
            surcharge=Decimal("0.00"),
            interest=Decimal("0.00"),
            compromise=Decimal("0.00"),
        )
        fields = Form1601EQGenerator(taxpayer, data).build_fields()

        # total_withheld=2000, total_remittances=500 -> still due=1500
        assert fields["frm1601EQ:txtTax23"] == "500.00"
        assert fields["frm1601EQ:txtTax24"] == "500.00"
        assert fields["frm1601EQ:txtTax25"] == "1,500.00"
