"""Tests for BIR Form 2550-M generator."""

from decimal import Decimal

import pytest

from ebirforms.base import TaxpayerInfo, build_ebirforms_content, parse_ebirforms_file
from ebirforms.generators.form_2550m import Form2550MData, Form2550MGenerator


@pytest.fixture()
def taxpayer():
    return TaxpayerInfo(
        tin="010-318-867-000",
        rdo_code="032",
        name="ABC CORPORATION",
        trade_name="ABC CORPORATION",
        address="BURGUNDY CORPORATE TOWER MAKATI",
        zip_code="1232",
        telephone="02-1234567",
        email="accounting@example.com",
        line_of_business="WHOLESALE TRADE",
    )


@pytest.fixture()
def simple_data():
    """Basic monthly VAT with only vatable sales and domestic goods purchases."""
    return Form2550MData(
        year=2026,
        month=3,
        vatable_sales=Decimal("100000.00"),
        output_tax_private=Decimal("12000.00"),
        domestic_goods_purchases=Decimal("50000.00"),
        domestic_goods_input_tax=Decimal("6000.00"),
    )


class TestForm2550MDataComputations:
    def test_total_sales_sums_all_sale_types(self):
        data = Form2550MData(
            year=2026,
            month=3,
            vatable_sales=Decimal("100000.00"),
            sales_to_govt=Decimal("20000.00"),
            zero_rated_sales=Decimal("5000.00"),
            exempt_sales=Decimal("3000.00"),
        )
        assert data.total_sales == Decimal("128000.00")

    def test_total_output_tax_sums_private_and_govt(self):
        data = Form2550MData(
            year=2026,
            month=1,
            output_tax_private=Decimal("12000.00"),
            output_tax_govt=Decimal("1000.00"),
        )
        assert data.total_output_tax == Decimal("13000.00")

    def test_prior_input_tax_total_sums_20a_through_20e(self):
        data = Form2550MData(
            year=2026,
            month=1,
            input_tax_carryover=Decimal("1000.00"),
            input_tax_deferred_capital=Decimal("500.00"),
            transitional_input_tax=Decimal("200.00"),
            presumptive_input_tax=Decimal("100.00"),
            other_prior_input_tax=Decimal("50.00"),
        )
        assert data.prior_input_tax_total == Decimal("1850.00")

    def test_total_current_purchases_sums_purchase_columns(self):
        data = Form2550MData(
            year=2026,
            month=1,
            capital_goods_small_purchases=Decimal("10000.00"),
            domestic_goods_purchases=Decimal("50000.00"),
            imported_goods_purchases=Decimal("5000.00"),
            domestic_services_purchases=Decimal("20000.00"),
        )
        assert data.total_current_purchases == Decimal("85000.00")

    def test_total_available_input_tax_combines_prior_and_current(self):
        data = Form2550MData(
            year=2026,
            month=1,
            input_tax_carryover=Decimal("2000.00"),
            domestic_goods_input_tax=Decimal("6000.00"),
            domestic_services_input_tax=Decimal("1200.00"),
        )
        assert data.total_available_input_tax == Decimal("9200.00")

    def test_total_deductions_sums_23a_through_23e(self):
        data = Form2550MData(
            year=2026,
            month=1,
            deferred_input_capital_large=Decimal("500.00"),
            input_tax_govt_expense=Decimal("200.00"),
            input_tax_exempt_sales=Decimal("100.00"),
            vat_refund_tcc=Decimal("50.00"),
            other_deductions=Decimal("25.00"),
        )
        assert data.total_deductions == Decimal("875.00")

    def test_total_allowable_input_tax_is_22_minus_23f(self):
        data = Form2550MData(
            year=2026,
            month=1,
            domestic_goods_input_tax=Decimal("6000.00"),
            deferred_input_capital_large=Decimal("500.00"),
        )
        assert data.total_allowable_input_tax == Decimal("5500.00")

    def test_net_vat_payable_is_output_minus_allowable_input(self):
        data = Form2550MData(
            year=2026,
            month=3,
            output_tax_private=Decimal("12000.00"),
            domestic_goods_input_tax=Decimal("6000.00"),
        )
        assert data.net_vat_payable == Decimal("6000.00")

    def test_total_tax_credits_sums_26a_through_26g(self):
        data = Form2550MData(
            year=2026,
            month=3,
            monthly_vat_payments_prior=Decimal("3000.00"),
            creditable_vat_withheld=Decimal("500.00"),
            vat_withheld_govt=Decimal("200.00"),
        )
        assert data.total_tax_credits == Decimal("3700.00")

    def test_tax_still_payable_is_net_vat_minus_credits(self):
        data = Form2550MData(
            year=2026,
            month=3,
            output_tax_private=Decimal("12000.00"),
            domestic_goods_input_tax=Decimal("6000.00"),
            monthly_vat_payments_prior=Decimal("4000.00"),
        )
        assert data.tax_still_payable == Decimal("2000.00")

    def test_total_penalties_sums_28a_through_28c(self):
        data = Form2550MData(
            year=2026,
            month=3,
            surcharge=Decimal("500.00"),
            interest=Decimal("100.00"),
            compromise=Decimal("200.00"),
        )
        assert data.total_penalties == Decimal("800.00")

    def test_total_amount_payable_adds_penalties_to_tax_still_payable(self):
        data = Form2550MData(
            year=2026,
            month=3,
            output_tax_private=Decimal("12000.00"),
            domestic_goods_input_tax=Decimal("6000.00"),
            surcharge=Decimal("300.00"),
        )
        assert data.total_amount_payable == Decimal("6300.00")

    def test_overpayment_when_credits_exceed_net_vat(self):
        data = Form2550MData(
            year=2026,
            month=3,
            output_tax_private=Decimal("5000.00"),
            monthly_vat_payments_prior=Decimal("8000.00"),
        )
        assert data.tax_still_payable == Decimal("-3000.00")

    def test_all_zeros_by_default(self):
        data = Form2550MData(year=2026, month=1)
        assert data.total_output_tax == Decimal("0.00")
        assert data.net_vat_payable == Decimal("0.00")
        assert data.total_amount_payable == Decimal("0.00")


class TestForm2550MGenerator:
    def test_form_number(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        assert gen.form_number == "2550M"

    def test_form_prefix_is_frm2550q(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        assert gen.form_prefix == "frm2550q"

    def test_period_fields(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        fields = gen.build_fields()

        assert fields["frm2550q:RtnMonth"] == "3"
        assert fields["frm2550q:txtYear"] == "2026"
        assert fields["frm2550q:RtnPeriodFrom"] == "03/01/2026"
        assert fields["frm2550q:RtnPeriodTo"] == "03/31/2026"

    def test_period_end_respects_month_length(self, taxpayer):
        data = Form2550MData(year=2026, month=2)
        gen = Form2550MGenerator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2550q:RtnPeriodTo"] == "02/28/2026"

    def test_period_end_respects_leap_year(self, taxpayer):
        data = Form2550MData(year=2028, month=2)
        gen = Form2550MGenerator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2550q:RtnPeriodTo"] == "02/29/2028"

    def test_amended_return_flags(self, taxpayer):
        data = Form2550MData(year=2026, month=3, is_amended=True)
        gen = Form2550MGenerator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2550q:AmendedRtnY"] == "true"
        assert fields["frm2550q:AmendedRtnN"] == "false"

    def test_non_amended_return_flags(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        fields = gen.build_fields()
        assert fields["frm2550q:AmendedRtnY"] == "false"
        assert fields["frm2550q:AmendedRtnN"] == "true"

    def test_taxpayer_info_fields(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTIN1"] == "010"
        assert fields["frm2550q:txtTIN2"] == "318"
        assert fields["frm2550q:txtTIN3"] == "867"
        assert fields["frm2550q:txtBranchCode"] == "000"
        assert fields["frm2550q:txtRDOCode"] == "032"
        assert fields["frm2550q:TaxPayer"] == "ABC CORPORATION"
        assert fields["frm2550q:txtLineBus"] == "WHOLESALE TRADE"
        assert fields["frm2550q:txtTelNum"] == "02-1234567"
        assert fields["frm2550q:txtZipCode"] == "1232"
        assert fields["txtEmail"] == "accounting@example.com"

    def test_output_tax_fields(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTax15A"] == "100,000.00"
        assert fields["frm2550q:txtTax15B"] == "12,000.00"
        assert fields["frm2550q:txtTax19A"] == "100,000.00"  # total sales
        assert fields["frm2550q:txtTax19B"] == "12,000.00"  # total output tax

    def test_input_tax_fields(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTax21E"] == "50,000.00"
        assert fields["frm2550q:txtTax21F"] == "6,000.00"
        assert fields["frm2550q:txtTax22"] == "6,000.00"  # total available input tax

    def test_net_vat_payable_field(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        fields = gen.build_fields()

        # 24 = total allowable (6000), 25 = net VAT payable (12000 - 6000 = 6000)
        assert fields["frm2550q:txtTax24"] == "6,000.00"
        assert fields["frm2550q:txtTax25"] == "6,000.00"

    def test_tax_still_payable_field_no_credits(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTax27"] == "6,000.00"
        assert fields["frm2550q:txtTax29"] == "6,000.00"

    def test_credits_reduce_tax_payable(self, taxpayer):
        data = Form2550MData(
            year=2026,
            month=3,
            output_tax_private=Decimal("12000.00"),
            domestic_goods_input_tax=Decimal("6000.00"),
            monthly_vat_payments_prior=Decimal("4000.00"),
        )
        gen = Form2550MGenerator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTax26A"] == "4,000.00"
        assert fields["frm2550q:txtTax26H"] == "4,000.00"
        assert fields["frm2550q:txtTax27"] == "2,000.00"
        assert fields["frm2550q:txtTax29"] == "2,000.00"

    def test_penalties_added_to_total_payable(self, taxpayer):
        data = Form2550MData(
            year=2026,
            month=3,
            output_tax_private=Decimal("10000.00"),
            surcharge=Decimal("500.00"),
            interest=Decimal("100.00"),
            compromise=Decimal("200.00"),
        )
        gen = Form2550MGenerator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTax28A"] == "500.00"
        assert fields["frm2550q:txtTax28B"] == "100.00"
        assert fields["frm2550q:txtTax28C"] == "200.00"
        assert fields["frm2550q:txtTax28D"] == "800.00"
        assert fields["frm2550q:txtTax29"] == "10,800.00"

    def test_prior_input_tax_carryover(self, taxpayer):
        data = Form2550MData(
            year=2026,
            month=3,
            output_tax_private=Decimal("12000.00"),
            input_tax_carryover=Decimal("3000.00"),
            domestic_goods_input_tax=Decimal("6000.00"),
        )
        gen = Form2550MGenerator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTax20A"] == "3,000.00"
        assert fields["frm2550q:txtTax20F"] == "3,000.00"
        assert fields["frm2550q:txtTax22"] == "9,000.00"  # 3000 prior + 6000 current
        assert fields["frm2550q:txtTax25"] == "3,000.00"  # 12000 - 9000

    def test_deductions_reduce_allowable_input_tax(self, taxpayer):
        data = Form2550MData(
            year=2026,
            month=3,
            output_tax_private=Decimal("12000.00"),
            domestic_goods_input_tax=Decimal("8000.00"),
            input_tax_exempt_sales=Decimal("2000.00"),
        )
        gen = Form2550MGenerator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTax23C"] == "2,000.00"
        assert fields["frm2550q:txtTax23F"] == "2,000.00"
        assert fields["frm2550q:txtTax24"] == "6,000.00"  # 8000 - 2000
        assert fields["frm2550q:txtTax25"] == "6,000.00"  # 12000 - 6000

    def test_flags_are_set(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        fields = gen.build_fields()

        assert fields["txtFinalFlag"] == "0"
        assert fields["txtEnroll"] == "N"

    def test_save_creates_file(self, taxpayer, simple_data, tmp_path):
        gen = Form2550MGenerator(taxpayer, simple_data)
        path = gen.save(tmp_path)

        assert path.exists()
        assert path.suffix == ".xml"

    def test_saved_file_is_parseable(self, taxpayer, simple_data, tmp_path):
        gen = Form2550MGenerator(taxpayer, simple_data)
        path = gen.save(tmp_path)

        content = path.read_text(encoding="utf-8")
        parsed = parse_ebirforms_file(content)

        assert parsed["frm2550q:txtTax25"] == "6,000.00"
        assert parsed["frm2550q:txtYear"] == "2026"

    def test_round_trip_preserves_all_fields(self, taxpayer, simple_data):
        gen = Form2550MGenerator(taxpayer, simple_data)
        original_fields = gen.build_fields()
        content = build_ebirforms_content(original_fields)
        parsed_fields = parse_ebirforms_file(content)

        for key in original_fields:
            assert key in parsed_fields, f"Field missing after round-trip: {key}"

    def test_large_amounts_formatted_with_commas(self, taxpayer):
        data = Form2550MData(
            year=2026,
            month=1,
            vatable_sales=Decimal("1500000.00"),
            output_tax_private=Decimal("180000.00"),
        )
        gen = Form2550MGenerator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTax15A"] == "1,500,000.00"
        assert fields["frm2550q:txtTax15B"] == "180,000.00"

    def test_sales_to_govt_with_output_tax(self, taxpayer):
        data = Form2550MData(
            year=2026,
            month=4,
            vatable_sales=Decimal("200000.00"),
            output_tax_private=Decimal("24000.00"),
            sales_to_govt=Decimal("100000.00"),
            output_tax_govt=Decimal("5000.00"),
        )
        gen = Form2550MGenerator(taxpayer, data)
        fields = gen.build_fields()

        assert fields["frm2550q:txtTax16A"] == "100,000.00"
        assert fields["frm2550q:txtTax16B"] == "5,000.00"
        assert fields["frm2550q:txtTax19A"] == "300,000.00"
        assert fields["frm2550q:txtTax19B"] == "29,000.00"
