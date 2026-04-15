"""Tests for BIR Form 2550-Q v2024 generator."""

from decimal import Decimal

import pytest

from ebirforms.base import TaxpayerInfo, build_ebirforms_content, parse_ebirforms_file
from ebirforms.generators.form_2550q import _VAT_RATE, Form2550QData, Form2550QGenerator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def taxpayer() -> TaxpayerInfo:
    return TaxpayerInfo(
        tin="010-318-867-000",
        rdo_code="032",
        name="ABC CORPORATION",
        trade_name="ABC CORPORATION",
        address="123 AYALA AVENUE MAKATI CITY",
        zip_code="1226",
        telephone="02-8123-4567",
        email="tax@abccorp.com",
        line_of_business="WHOLESALE AND RETAIL TRADE",
    )


def _zero_data(year: int = 2025, quarter: int = 1) -> Form2550QData:
    """Return a Form2550QData with all monetary fields at zero."""
    z = Decimal("0")
    return Form2550QData(
        year=year,
        quarter=quarter,
        is_amended=False,
        vatable_sales=z,
        zero_rated_sales=z,
        exempt_sales=z,
        less_output_vat=z,
        add_output_vat=z,
        input_tax_carried=z,
        input_tax_deferred=z,
        transitional_input_tax=z,
        presumptive_input_tax=z,
        other_prior_input_tax=z,
        other_prior_input_tax_label="",
        domestic_purchase=z,
        domestic_input_tax=z,
        services_purchase=z,
        service_input_tax=z,
        import_purchase=z,
        import_input_tax=z,
        other_purchase=z,
        other_purchase_label="",
        other_purchase_input_tax=z,
        domestic_purchase_no_tax=z,
        vat_exempt_imports=z,
        import_capital_input_tax=z,
        input_tax_attr=z,
        vat_refund=z,
        input_vat_unpaid=z,
        other_deduction=z,
        other_deduction_label="",
        add_input_vat=z,
        creditable_vat=z,
        adv_vat_payment=z,
        vat_paid_return=z,
        other_credits=z,
        other_credits_label="",
        surcharge=z,
        interest=z,
        compromise=z,
    )


@pytest.fixture()
def basic_data() -> Form2550QData:
    """Q1 2025 with simple vatable sales only."""
    return Form2550QData(
        year=2025,
        quarter=1,
        is_amended=False,
        vatable_sales=Decimal("1000000.00"),
        zero_rated_sales=Decimal("0"),
        exempt_sales=Decimal("0"),
        less_output_vat=Decimal("0"),
        add_output_vat=Decimal("0"),
        input_tax_carried=Decimal("0"),
        input_tax_deferred=Decimal("0"),
        transitional_input_tax=Decimal("0"),
        presumptive_input_tax=Decimal("0"),
        other_prior_input_tax=Decimal("0"),
        other_prior_input_tax_label="",
        domestic_purchase=Decimal("500000.00"),
        domestic_input_tax=Decimal("60000.00"),
        services_purchase=Decimal("0"),
        service_input_tax=Decimal("0"),
        import_purchase=Decimal("0"),
        import_input_tax=Decimal("0"),
        other_purchase=Decimal("0"),
        other_purchase_label="",
        other_purchase_input_tax=Decimal("0"),
        domestic_purchase_no_tax=Decimal("0"),
        vat_exempt_imports=Decimal("0"),
        import_capital_input_tax=Decimal("0"),
        input_tax_attr=Decimal("0"),
        vat_refund=Decimal("0"),
        input_vat_unpaid=Decimal("0"),
        other_deduction=Decimal("0"),
        other_deduction_label="",
        add_input_vat=Decimal("0"),
        creditable_vat=Decimal("0"),
        adv_vat_payment=Decimal("0"),
        vat_paid_return=Decimal("0"),
        other_credits=Decimal("0"),
        other_credits_label="",
        surcharge=Decimal("0"),
        interest=Decimal("0"),
        compromise=Decimal("0"),
    )


# ---------------------------------------------------------------------------
# Form2550QData computation tests
# ---------------------------------------------------------------------------


class TestForm2550QDataComputations:
    def test_output_vat_is_12_percent_of_vatable_sales(self, basic_data):
        expected = Decimal("1000000.00") * _VAT_RATE
        assert basic_data.output_vat_sales == expected

    def test_output_vat_equals_output_tax_due(self, basic_data):
        assert basic_data.output_vat_sales == basic_data.output_tax_due

    def test_total_sales_sums_all_sale_types(self):
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "vatable_sales": Decimal("500000"),
                "zero_rated_sales": Decimal("200000"),
                "exempt_sales": Decimal("100000"),
            }
        )
        assert data.total_sales == Decimal("800000")

    def test_total_adj_output_basic(self, basic_data):
        # 35 - 36 + 36A = 120000 - 0 + 0
        assert basic_data.total_adj_output == Decimal("1000000.00") * _VAT_RATE

    def test_total_adj_output_with_adjustments(self):
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "vatable_sales": Decimal("1000000"),
                "less_output_vat": Decimal("5000"),
                "add_output_vat": Decimal("2000"),
            }
        )
        expected = Decimal("1000000") * _VAT_RATE - Decimal("5000") + Decimal("2000")
        assert data.total_adj_output == expected

    def test_total_prior_input_sums_items_38_to_42(self):
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "input_tax_carried": Decimal("10000"),
                "input_tax_deferred": Decimal("2000"),
                "transitional_input_tax": Decimal("1000"),
                "presumptive_input_tax": Decimal("500"),
                "other_prior_input_tax": Decimal("750"),
            }
        )
        assert data.total_prior_input == Decimal("14250")

    def test_total_cur_input_tax_sums_all_purchase_taxes(self, basic_data):
        assert basic_data.total_cur_input_tax == Decimal("60000.00")

    def test_total_avail_input_is_43_plus_50b(self):
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "input_tax_carried": Decimal("20000"),
                "domestic_input_tax": Decimal("60000"),
            }
        )
        assert data.total_avail_input_tax == Decimal("80000")

    def test_net_vat_payable(self, basic_data):
        # output = 120000, input = 60000, net = 60000
        expected = Decimal("1000000.00") * _VAT_RATE - Decimal("60000.00")
        assert basic_data.net_vat_payable == expected

    def test_excess_credits_reduces_net_vat(self):
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "vatable_sales": Decimal("1000000"),
                "domestic_input_tax": Decimal("60000"),
                "creditable_vat": Decimal("10000"),
            }
        )
        # net = 120000 - 60000 = 60000, credits = 10000, excess = 50000
        assert data.excess_credits == Decimal("50000")

    def test_penalties_sum(self):
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "surcharge": Decimal("1000"),
                "interest": Decimal("500"),
                "compromise": Decimal("2000"),
            }
        )
        assert data.penalties == Decimal("3500")

    def test_total_payable_basic(self, basic_data):
        # net_vat = 60000, no credits, no penalties
        assert basic_data.total_payable == Decimal("60000.00")

    def test_total_payable_when_credits_exceed_vat(self):
        # excess_credits is negative (credits > vat), no penalties -> payable = 0
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "vatable_sales": Decimal("100000"),
                "domestic_input_tax": Decimal("20000"),
                "creditable_vat": Decimal("5000"),
            }
        )
        # net = 12000 - 20000 = -8000, credits = 5000, excess = -8000 - 5000 = -13000
        assert data.excess_credits < 0
        assert data.total_payable == Decimal("0")

    def test_total_payable_penalties_only_when_excess_negative(self):
        # When excess_credits < 0 and there are penalties, only penalties are payable
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "vatable_sales": Decimal("100000"),
                "domestic_input_tax": Decimal("20000"),
                "surcharge": Decimal("500"),
            }
        )
        # net = 12000 - 20000 = -8000, no credits, excess = -8000
        # penalties = 500, and excess < 0 -> total = 500
        assert data.total_payable == Decimal("500")

    def test_adj_deductions_is_57_plus_58(self):
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "import_capital_input_tax": Decimal("5000"),
                "input_tax_attr": Decimal("3000"),
                "add_input_vat": Decimal("1000"),
            }
        )
        assert data.total_deductions == Decimal("8000")
        assert data.adj_deductions == Decimal("9000")

    def test_total_allow_input_tax(self):
        data = Form2550QData(
            **{
                **_zero_data().__dict__,
                "domestic_input_tax": Decimal("60000"),
                "input_tax_attr": Decimal("10000"),
            }
        )
        assert data.total_allow_input_tax == Decimal("50000")


# ---------------------------------------------------------------------------
# Quarter period date tests
# ---------------------------------------------------------------------------


class TestQuarterPeriodDates:
    @pytest.mark.parametrize(
        "quarter,expected_from,expected_to",
        [
            (1, "1/01/2025", "3/31/2025"),
            (2, "4/01/2025", "6/30/2025"),
            (3, "7/01/2025", "9/30/2025"),
            (4, "10/01/2025", "12/31/2025"),
        ],
    )
    def test_calendar_year_periods(self, quarter, expected_from, expected_to):
        data = _zero_data(year=2025, quarter=quarter)
        assert data.period_from == expected_from
        assert data.period_to == expected_to

    def test_leap_year_q1(self):
        data = _zero_data(year=2024, quarter=1)
        assert data.period_to == "3/31/2024"

    def test_q2_ends_june_30(self):
        data = _zero_data(year=2025, quarter=2)
        assert data.period_to == "6/30/2025"


# ---------------------------------------------------------------------------
# Generator field output tests
# ---------------------------------------------------------------------------


class TestForm2550QGenerator:
    def test_form_number(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        assert gen.form_number == "2550Qv2024"

    def test_form_prefix(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        assert gen.form_prefix == "frm2550qv2024"

    def test_tin_fields(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:txtTIN1"] == "010"
        assert fields["frm2550qv2024:txtTIN2"] == "318"
        assert fields["frm2550qv2024:txtTIN3"] == "867"
        assert fields["frm2550qv2024:branchCode"] == "000"
        assert fields["frm2550qv2024:txtRDOCode"] == "032"

    def test_taxpayer_info_fields(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:taxpayerName"] == "ABC CORPORATION"
        assert fields["frm2550qv2024:taxpayerAddress"] == "123 AYALA AVENUE MAKATI CITY"
        assert fields["frm2550qv2024:taxpayerZip"] == "1226"
        assert fields["frm2550qv2024:taxpayerContactNumber"] == "02-8123-4567"
        assert fields["frm2550qv2024:taxpayerEmailAddress"] == "tax@abccorp.com"

    def test_calendar_year_flag(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:calendarNo1"] == "true"
        assert fields["frm2550qv2024:fiscalNo1"] == "false"

    def test_year_and_month_fields(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:txtYearNo2"] == "2025"
        assert fields["frm2550qv2024:selectedMonthNo2"] == "12"

    def test_quarter_radio_fields(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:OptQuarter1"] == "true"
        assert fields["frm2550qv2024:OptQuarter2"] == "false"
        assert fields["frm2550qv2024:OptQuarter3"] == "false"
        assert fields["frm2550qv2024:OptQuarter4"] == "false"

    def test_return_period_dates(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:RtnPeriodFromNo4"] == "1/01/2025"
        assert fields["frm2550qv2024:RtnPeriodToNo4"] == "3/31/2025"

    def test_amended_return_no(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:amendedReturnNo5"] == "true"
        assert fields["frm2550qv2024:amendedReturnYesNo5"] == "false"

    def test_amended_return_yes(self, taxpayer):
        data = Form2550QData(**{**basic_data_kwargs(), "is_amended": True})
        gen = Form2550QGenerator(taxpayer, data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:amendedReturnYesNo5"] == "true"
        assert fields["frm2550qv2024:amendedReturnNo5"] == "false"

    def test_output_vat_fields(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:vatableSales"] == "1,000,000.00"
        assert fields["frm2550qv2024:outputVatSales"] == "120,000.00"
        assert fields["frm2550qv2024:outputTaxDue"] == "120,000.00"
        assert fields["frm2550qv2024:totalSales"] == "1,000,000.00"
        assert fields["frm2550qv2024:totalAdjOutput"] == "120,000.00"

    def test_input_vat_fields(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:domesticInputTax"] == "60,000.00"
        assert fields["frm2550qv2024:totalCurInputTax"] == "60,000.00"
        assert fields["frm2550qv2024:totalAvailInputTax"] == "60,000.00"
        assert fields["frm2550qv2024:totalAllowInputTax"] == "60,000.00"

    def test_net_vat_payable_field(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:netVatPayable"] == "60,000.00"
        assert fields["frm2550qv2024:excessInputTax"] == "60,000.00"

    def test_total_payable_field(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:totalPayable"] == "60,000.00"

    def test_flags(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["txtFinalFlag"] == "0"
        assert fields["txtEnroll"] == "N"

    def test_page2_tin_repeat(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:txtPg2TIN1"] == "010"
        assert fields["frm2550qv2024:txtPg2TIN2"] == "318"
        assert fields["frm2550qv2024:txtPg2TIN3"] == "867"
        assert fields["frm2550qv2024:Pg2TaxPayer"] == "ABC CORPORATION"

    def test_all_quarters_generate_correct_period(self, taxpayer):
        for q, (from_date, to_date) in {
            1: ("1/01/2025", "3/31/2025"),
            2: ("4/01/2025", "6/30/2025"),
            3: ("7/01/2025", "9/30/2025"),
            4: ("10/01/2025", "12/31/2025"),
        }.items():
            data = _zero_data(year=2025, quarter=q)
            gen = Form2550QGenerator(taxpayer, data)
            fields = gen.build_fields()
            assert fields["frm2550qv2024:RtnPeriodFromNo4"] == from_date
            assert fields["frm2550qv2024:RtnPeriodToNo4"] == to_date
            assert fields[f"frm2550qv2024:OptQuarter{q}"] == "true"

    def test_save_creates_parseable_file(self, taxpayer, basic_data, tmp_path):
        gen = Form2550QGenerator(taxpayer, basic_data)
        path = gen.save(tmp_path)

        assert path.exists()
        assert path.suffix == ".xml"

        content = path.read_text(encoding="utf-8")
        fields = parse_ebirforms_file(content)

        assert fields["frm2550qv2024:vatableSales"] == "1,000,000.00"
        assert fields["frm2550qv2024:netVatPayable"] == "60,000.00"

    def test_round_trip_via_ebirforms_content(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        built_fields = gen.build_fields()
        content = build_ebirforms_content(built_fields)
        parsed = parse_ebirforms_file(content)

        assert parsed["frm2550qv2024:totalPayable"] == "60,000.00"
        assert parsed["frm2550qv2024:txtYearNo2"] == "2025"

    def test_taxpayer_classification_default_is_1(self, taxpayer, basic_data):
        gen = Form2550QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        assert fields["frm2550qv2024:taxPayerClassification1"] == "true"
        assert fields["frm2550qv2024:taxPayerClassification2"] == "false"
        assert fields["frm2550qv2024:taxPayerClassification3"] == "false"
        assert fields["frm2550qv2024:taxPayerClassification4"] == "false"

    def test_credits_reduce_total_payable(self, taxpayer):
        data = Form2550QData(
            **{
                **basic_data_kwargs(),
                "creditable_vat": Decimal("20000"),
            }
        )
        gen = Form2550QGenerator(taxpayer, data)
        fields = gen.build_fields()
        # net = 60000, credits = 20000, excess = 40000
        assert fields["frm2550qv2024:totalTaxCredits"] == "20,000.00"
        assert fields["frm2550qv2024:excessCredits"] == "40,000.00"
        assert fields["frm2550qv2024:totalPayable"] == "40,000.00"

    def test_with_multiple_purchase_types(self, taxpayer):
        data = Form2550QData(
            year=2025,
            quarter=2,
            is_amended=False,
            vatable_sales=Decimal("2000000"),
            zero_rated_sales=Decimal("100000"),
            exempt_sales=Decimal("50000"),
            less_output_vat=Decimal("0"),
            add_output_vat=Decimal("0"),
            input_tax_carried=Decimal("30000"),
            input_tax_deferred=Decimal("0"),
            transitional_input_tax=Decimal("0"),
            presumptive_input_tax=Decimal("0"),
            other_prior_input_tax=Decimal("0"),
            other_prior_input_tax_label="",
            domestic_purchase=Decimal("800000"),
            domestic_input_tax=Decimal("96000"),
            services_purchase=Decimal("200000"),
            service_input_tax=Decimal("24000"),
            import_purchase=Decimal("100000"),
            import_input_tax=Decimal("12000"),
            other_purchase=Decimal("0"),
            other_purchase_label="",
            other_purchase_input_tax=Decimal("0"),
            domestic_purchase_no_tax=Decimal("0"),
            vat_exempt_imports=Decimal("0"),
            import_capital_input_tax=Decimal("0"),
            input_tax_attr=Decimal("0"),
            vat_refund=Decimal("0"),
            input_vat_unpaid=Decimal("0"),
            other_deduction=Decimal("0"),
            other_deduction_label="",
            add_input_vat=Decimal("0"),
            creditable_vat=Decimal("0"),
            adv_vat_payment=Decimal("0"),
            vat_paid_return=Decimal("0"),
            other_credits=Decimal("0"),
            other_credits_label="",
            surcharge=Decimal("0"),
            interest=Decimal("0"),
            compromise=Decimal("0"),
        )
        gen = Form2550QGenerator(taxpayer, data)
        fields = gen.build_fields()

        # output: 2000000 * 0.12 = 240000
        assert fields["frm2550qv2024:outputTaxDue"] == "240,000.00"
        # total avail input: 30000 (carried) + 96000 + 24000 + 12000 = 162000
        assert fields["frm2550qv2024:totalAvailInputTax"] == "162,000.00"
        # net = 240000 - 162000 = 78000
        assert fields["frm2550qv2024:netVatPayable"] == "78,000.00"

        # period dates for Q2
        assert fields["frm2550qv2024:RtnPeriodFromNo4"] == "4/01/2025"
        assert fields["frm2550qv2024:RtnPeriodToNo4"] == "6/30/2025"
        assert fields["frm2550qv2024:OptQuarter2"] == "true"
        assert fields["frm2550qv2024:OptQuarter1"] == "false"


# ---------------------------------------------------------------------------
# Helper to avoid repeating fixture data in parameterised tests
# ---------------------------------------------------------------------------


def basic_data_kwargs() -> dict:
    """Return keyword arguments matching the basic_data fixture."""
    z = Decimal("0")
    return dict(
        year=2025,
        quarter=1,
        is_amended=False,
        vatable_sales=Decimal("1000000.00"),
        zero_rated_sales=z,
        exempt_sales=z,
        less_output_vat=z,
        add_output_vat=z,
        input_tax_carried=z,
        input_tax_deferred=z,
        transitional_input_tax=z,
        presumptive_input_tax=z,
        other_prior_input_tax=z,
        other_prior_input_tax_label="",
        domestic_purchase=Decimal("500000.00"),
        domestic_input_tax=Decimal("60000.00"),
        services_purchase=z,
        service_input_tax=z,
        import_purchase=z,
        import_input_tax=z,
        other_purchase=z,
        other_purchase_label="",
        other_purchase_input_tax=z,
        domestic_purchase_no_tax=z,
        vat_exempt_imports=z,
        import_capital_input_tax=z,
        input_tax_attr=z,
        vat_refund=z,
        input_vat_unpaid=z,
        other_deduction=z,
        other_deduction_label="",
        add_input_vat=z,
        creditable_vat=z,
        adv_vat_payment=z,
        vat_paid_return=z,
        other_credits=z,
        other_credits_label="",
        surcharge=z,
        interest=z,
        compromise=z,
    )
