"""Tests for BIR Form 1702-Q v2018 generator."""

from decimal import Decimal

import pytest

from ebirforms.base import TaxpayerInfo, build_ebirforms_content, parse_ebirforms_file
from ebirforms.generators.form_1702q import (
    ATC_DOMESTIC_20,
    ATC_DOMESTIC_25,
    DEDUCTION_ITEMIZED,
    DEDUCTION_OSD,
    Form1702QData,
    Form1702QGenerator,
    Sched2Data,
    Sched3Data,
    Sched4Data,
)

_ZERO = Decimal("0.00")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def taxpayer():
    return TaxpayerInfo(
        tin="012-345-678-000",
        rdo_code="040",
        name="TEST CORPORATION",
        trade_name="TEST CORPORATION",
        address="123 MAIN STREET QUEZON CITY",
        zip_code="1100",
        telephone="02-8888-0000",
        email="ceo@testcorp.ph",
        line_of_business="INFORMATION TECHNOLOGY",
    )


def _sched2(
    revenues: str = "1,000,000.00",
    cost_of_sales: str = "400,000.00",
    non_operating_income: str = "0.00",
    deductions: str = "200,000.00",
    taxable_income_prior: str = "0.00",
    tax_rate: str = "25.00",
) -> Sched2Data:
    return Sched2Data(
        revenues=Decimal(revenues.replace(",", "")),
        cost_of_sales=Decimal(cost_of_sales.replace(",", "")),
        non_operating_income=Decimal(non_operating_income.replace(",", "")),
        deductions=Decimal(deductions.replace(",", "")),
        taxable_income_prior_quarters=Decimal(taxable_income_prior.replace(",", "")),
        tax_rate=Decimal(tax_rate),
    )


def _sched3(
    gross_ops: str = "600,000.00",
    non_op: str = "0.00",
    other: str = "0.00",
    mcit_rate: str = "2.00",
) -> Sched3Data:
    return Sched3Data(
        gross_income_from_operations=Decimal(gross_ops.replace(",", "")),
        non_operating_income=Decimal(non_op.replace(",", "")),
        other_gross_income=Decimal(other.replace(",", "")),
        mcit_rate=Decimal(mcit_rate),
    )


def _sched4_empty() -> Sched4Data:
    return Sched4Data(
        prior_quarter_payments=_ZERO,
        creditable_wt_prior_quarters=_ZERO,
        creditable_wt_this_quarter=_ZERO,
        tax_paid_previously_filed=_ZERO,
        foreign_tax_credits=_ZERO,
        special_tax_credits=_ZERO,
    )


def _sched4(prior: str = "0.00", cwt_prior: str = "0.00", cwt_current: str = "0.00") -> Sched4Data:
    return Sched4Data(
        prior_quarter_payments=Decimal(prior.replace(",", "")),
        creditable_wt_prior_quarters=Decimal(cwt_prior.replace(",", "")),
        creditable_wt_this_quarter=Decimal(cwt_current.replace(",", "")),
        tax_paid_previously_filed=_ZERO,
        foreign_tax_credits=_ZERO,
        special_tax_credits=_ZERO,
    )


def _default_data(**kwargs) -> Form1702QData:
    defaults = dict(
        fiscal_year_end_month=12,
        fiscal_year_end_year=25,
        quarter=1,
        is_calendar_year=True,
        is_amended=False,
        atc_code=ATC_DOMESTIC_25,
        deduction_method=DEDUCTION_ITEMIZED,
        sched2=_sched2(),
        sched3=_sched3(),
        sched4=_sched4_empty(),
    )
    defaults.update(kwargs)
    return Form1702QData(**defaults)


# ---------------------------------------------------------------------------
# Sched2Data unit tests
# ---------------------------------------------------------------------------


class TestSched2Data:
    def test_gross_income_from_operations(self):
        s2 = _sched2(revenues="1000000.00", cost_of_sales="400000.00")
        assert s2.gross_income_from_operations == Decimal("600000.00")

    def test_total_gross_income_with_non_operating(self):
        s2 = _sched2(revenues="1000000.00", cost_of_sales="400000.00", non_operating_income="50000.00")
        assert s2.total_gross_income == Decimal("650000.00")

    def test_taxable_income_itemized(self):
        s2 = _sched2(revenues="1000000.00", cost_of_sales="400000.00", deductions="200000.00")
        # TGI = 600k, itemized deductions = 200k, taxable = 400k
        assert s2.taxable_income_this_quarter(use_osd=False) == Decimal("400000.00")

    def test_taxable_income_osd(self):
        s2 = _sched2(revenues="1000000.00", cost_of_sales="400000.00")
        # TGI = 600k, OSD = 40% of 600k = 240k, taxable = 360k
        assert s2.taxable_income_this_quarter(use_osd=True) == Decimal("360000.00")

    def test_total_taxable_income_with_prior(self):
        s2 = _sched2(
            revenues="1000000.00",
            cost_of_sales="400000.00",
            deductions="200000.00",
            taxable_income_prior="300000.00",
        )
        # This quarter: 400k, total = 400k + 300k = 700k
        assert s2.total_taxable_income(use_osd=False) == Decimal("700000.00")

    def test_income_tax_due_regular_25_percent(self):
        s2 = _sched2(revenues="1000000.00", cost_of_sales="400000.00", deductions="200000.00", tax_rate="25.00")
        # Taxable = 400k, 25% = 100k
        assert s2.income_tax_due_regular(use_osd=False) == Decimal("100000.00")

    def test_income_tax_due_zero_when_taxable_income_negative(self):
        s2 = _sched2(revenues="100000.00", cost_of_sales="500000.00", deductions="0.00", tax_rate="25.00")
        # Gross income from ops = -400k, no non-op income, taxable = -400k
        assert s2.income_tax_due_regular(use_osd=False) == _ZERO

    def test_effective_deductions_osd_returns_40_percent_of_tgi(self):
        s2 = _sched2(revenues="1000000.00", cost_of_sales="400000.00")
        osd = s2.effective_deductions(use_osd=True)
        assert osd == Decimal("240000.00")  # 40% of 600k

    def test_effective_deductions_itemized_returns_actual(self):
        s2 = _sched2(revenues="1000000.00", cost_of_sales="400000.00", deductions="150000.00")
        assert s2.effective_deductions(use_osd=False) == Decimal("150000.00")


# ---------------------------------------------------------------------------
# Sched3Data unit tests
# ---------------------------------------------------------------------------


class TestSched3Data:
    def test_total_gross_income(self):
        s3 = _sched3(gross_ops="500000.00", non_op="50000.00", other="10000.00")
        assert s3.total_gross_income == Decimal("560000.00")

    def test_mcit_2_percent(self):
        s3 = _sched3(gross_ops="600000.00", mcit_rate="2.00")
        assert s3.mcit == Decimal("12000.00")  # 2% of 600k


# ---------------------------------------------------------------------------
# Sched4Data unit tests
# ---------------------------------------------------------------------------


class TestSched4Data:
    def test_total_sums_all_credits(self):
        s4 = Sched4Data(
            prior_quarter_payments=Decimal("10000.00"),
            creditable_wt_prior_quarters=Decimal("5000.00"),
            creditable_wt_this_quarter=Decimal("3000.00"),
            tax_paid_previously_filed=_ZERO,
            foreign_tax_credits=_ZERO,
            special_tax_credits=_ZERO,
        )
        assert s4.total == Decimal("18000.00")

    def test_empty_credits_total_zero(self):
        assert _sched4_empty().total == _ZERO


# ---------------------------------------------------------------------------
# Form1702QData tax computation tests
# ---------------------------------------------------------------------------


class TestForm1702QDataTaxComputation:
    def test_tax14_equals_sched2_item13(self):
        # Regular tax > MCIT, so item13 = regular tax
        data = _default_data(
            sched2=_sched2(revenues="2000000.00", cost_of_sales="800000.00", deductions="400000.00", tax_rate="25.00"),
            sched3=_sched3(gross_ops="1200000.00", mcit_rate="2.00"),
        )
        # Regular: 800k * 25% = 200k; MCIT: 1200k * 2% = 24k; tax14 = 200k
        assert data.tax14 == Decimal("200000.00")

    def test_mcit_applies_when_higher_than_regular(self):
        # Revenues high but very thin margins, MCIT kicks in
        data = _default_data(
            sched2=_sched2(
                revenues="5000000.00",
                cost_of_sales="4900000.00",
                deductions="90000.00",
                tax_rate="25.00",
            ),
            sched3=_sched3(gross_ops="100000.00", mcit_rate="2.00"),
        )
        # Regular: (100k - 90k) * 25% = 2500; MCIT: 100k * 2% = 2000
        # Regular (2500) > MCIT (2000), so tax14 = 2500
        assert data.tax14 == Decimal("2500.00")

    def test_mcit_wins_when_regular_is_lower(self):
        data = _default_data(
            sched2=_sched2(
                revenues="1000000.00",
                cost_of_sales="999000.00",
                deductions="500.00",
                tax_rate="25.00",
            ),
            sched3=_sched3(gross_ops="1000000.00", mcit_rate="2.00"),
        )
        # Regular: (1000 - 500) * 25% = 125; MCIT: 1000000 * 2% = 20000
        assert data.tax14 == Decimal("20000.00")

    def test_tax16_is_tax14_minus_tax15(self):
        data = _default_data(
            sched2=_sched2(revenues="1000000.00", cost_of_sales="400000.00", deductions="200000.00"),
            sched4=_sched4(cwt_current="20000.00"),
        )
        # tax14 = 400k * 25% = 100k; tax15 = 20k; tax16 = 80k
        assert data.tax16 == Decimal("80000.00")

    def test_tax18_aggregate_includes_special_rate(self):
        data = _default_data(
            sched2=_sched2(revenues="1000000.00", cost_of_sales="400000.00", deductions="200000.00"),
            sched4=_sched4_empty(),
            special_rate_tax_due=Decimal("5000.00"),
        )
        # tax16 = 100k - 0 = 100k; tax17 = 5k; tax18 = 105k
        assert data.tax18 == Decimal("105000.00")

    def test_tax20_net_payable(self):
        data = _default_data(
            sched2=_sched2(revenues="1000000.00", cost_of_sales="400000.00", deductions="200000.00"),
            sched4=_sched4(cwt_prior="30000.00", cwt_current="20000.00"),
        )
        # tax14 = 100k; tax15 = 50k; tax16 = 50k; tax18 = 50k; tax19 = 50k; tax20 = 0
        assert data.tax20 == _ZERO

    def test_tax20_overpayment_when_credits_exceed_due(self):
        data = _default_data(
            sched2=_sched2(revenues="500000.00", cost_of_sales="300000.00", deductions="100000.00"),
            sched4=_sched4(cwt_current="50000.00"),
        )
        # Regular: 100k * 25% = 25k; tax15 = 50k; tax16 = -25k; tax18 = -25k; tax19 = 50k; tax20 = -75k
        assert data.tax20 == Decimal("-75000.00")

    def test_tax24_total_penalties(self):
        data = _default_data(
            surcharge=Decimal("1000.00"),
            interest=Decimal("500.00"),
            compromise=Decimal("200.00"),
        )
        assert data.tax24 == Decimal("1700.00")

    def test_tax25_total_amount_due(self):
        data = _default_data(
            sched2=_sched2(revenues="1000000.00", cost_of_sales="400000.00", deductions="200000.00"),
            sched4=_sched4_empty(),
            surcharge=Decimal("1000.00"),
        )
        # tax20 = 100k; tax24 = 1k; tax25 = 101k
        assert data.tax25 == Decimal("101000.00")

    def test_tax25_overpayment_with_penalties_shows_only_penalties(self):
        data = _default_data(
            sched2=_sched2(revenues="500000.00", cost_of_sales="300000.00", deductions="100000.00"),
            sched4=_sched4(cwt_current="50000.00"),
            surcharge=Decimal("500.00"),
        )
        # tax20 = -75k (overpayment), tax24 = 500; tax25 = only penalties = 500
        assert data.tax25 == Decimal("500.00")

    def test_osd_deduction_method(self):
        data = _default_data(
            sched2=_sched2(revenues="1000000.00", cost_of_sales="400000.00"),
            deduction_method=DEDUCTION_OSD,
        )
        # OSD = 40% of 600k = 240k; taxable = 360k; tax = 360k * 25% = 90k
        assert data.tax14 == Decimal("90000.00")


# ---------------------------------------------------------------------------
# Form1702QGenerator field output tests
# ---------------------------------------------------------------------------


class TestForm1702QGeneratorFields:
    @pytest.fixture()
    def basic_data(self):
        return _default_data(
            sched2=_sched2(revenues="1000000.00", cost_of_sales="400000.00", deductions="200000.00"),
            sched3=_sched3(gross_ops="600000.00"),
            sched4=_sched4_empty(),
        )

    @pytest.fixture()
    def gen(self, taxpayer, basic_data):
        return Form1702QGenerator(taxpayer, basic_data)

    def test_form_number(self, gen):
        assert gen.form_number == "1702Qv2018"

    def test_form_prefix(self, gen):
        assert gen.form_prefix == "frm1702q"

    def test_tin_fields(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:txtTIN1"] == "012"
        assert fields["frm1702q:txtTIN2"] == "345"
        assert fields["frm1702q:txtTIN3"] == "678"
        assert fields["frm1702q:txtBranchCode"] == "000"

    def test_rdo_code(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:txtRDOCode"] == "040"

    def test_taxpayer_name(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:txtTaxpayerName1"] == "TEST CORPORATION"

    def test_email_has_no_prefix(self, gen):
        fields = gen.build_fields()
        assert fields["txtEmail"] == "ceo@testcorp.ph"

    def test_calendar_year_flag(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:rbForClndrFscl_1"] == "true"
        assert fields["frm1702q:rbForClndrFscl_2"] == "false"

    def test_fiscal_year_flag(self, taxpayer):
        data = _default_data(is_calendar_year=False)
        fields = Form1702QGenerator(taxpayer, data).build_fields()
        assert fields["frm1702q:rbForClndrFscl_1"] == "false"
        assert fields["frm1702q:rbForClndrFscl_2"] == "true"

    def test_quarter_selection(self, taxpayer):
        for q in (1, 2, 3):
            data = _default_data(quarter=q)
            fields = Form1702QGenerator(taxpayer, data).build_fields()
            assert fields[f"frm1702q:rbQuarter_{q}"] == "true"
            for other in (1, 2, 3):
                if other != q:
                    assert fields[f"frm1702q:rbQuarter_{other}"] == "false"

    def test_amended_return(self, taxpayer):
        data = _default_data(is_amended=True)
        fields = Form1702QGenerator(taxpayer, data).build_fields()
        assert fields["frm1702q:rbAmendedRtn_1"] == "true"
        assert fields["frm1702q:rbAmendedRtn_2"] == "false"

    def test_not_amended_return(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:rbAmendedRtn_1"] == "false"
        assert fields["frm1702q:rbAmendedRtn_2"] == "true"

    def test_atc_code(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:cbATC_2"] == ATC_DOMESTIC_25
        assert fields["frm1702q:rbATC_2"] == "true"
        assert fields["frm1702q:rbATC_1"] == "false"

    def test_deduction_method_itemized(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:rbMthdOfDdctns_1"] == "true"
        assert fields["frm1702q:rbMthdOfDdctns_2"] == "false"

    def test_deduction_method_osd(self, taxpayer):
        data = _default_data(deduction_method=DEDUCTION_OSD)
        fields = Form1702QGenerator(taxpayer, data).build_fields()
        assert fields["frm1702q:rbMthdOfDdctns_1"] == "false"
        assert fields["frm1702q:rbMthdOfDdctns_2"] == "true"

    def test_sched2_revenue_and_cos(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:Sched2:txtTax1"] == "1,000,000.00"
        assert fields["frm1702q:Sched2:txtTax2"] == "400,000.00"

    def test_sched2_derived_fields(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:Sched2:txtTax3"] == "600,000.00"  # gross income from ops
        assert fields["frm1702q:Sched2:txtTax5"] == "600,000.00"  # total gross income (no non-op)
        assert fields["frm1702q:Sched2:txtTax6"] == "200,000.00"  # deductions
        assert fields["frm1702q:Sched2:txtTax7"] == "400,000.00"  # taxable this quarter
        assert fields["frm1702q:Sched2:txtTax9"] == "400,000.00"  # total taxable (no prior)

    def test_sched2_tax_rate_and_due(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:Sched2:txtTax10"] == "25.00"
        assert fields["frm1702q:Sched2:txtTax11"] == "100,000.00"  # 400k * 25%

    def test_sched2_mcit_from_sched3(self, gen):
        fields = gen.build_fields()
        # MCIT: 600k * 2% = 12k
        assert fields["frm1702q:Sched2:txtTax12"] == "12,000.00"
        # Income Tax Due = max(100k, 12k) = 100k
        assert fields["frm1702q:Sched2:txtTax13"] == "100,000.00"

    def test_sched3_fields(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:Sched3:txtTax1"] == "600,000.00"
        assert fields["frm1702q:Sched3:txtTax4"] == "600,000.00"
        assert fields["frm1702q:Sched3:txtTax5"] == "2.00"
        assert fields["frm1702q:Sched3:txtTax6"] == "12,000.00"

    def test_part2_tax14_through_tax20(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:txtTax14"] == "100,000.00"
        assert fields["frm1702q:txtTax15"] == "0.00"
        assert fields["frm1702q:txtTax16"] == "100,000.00"
        assert fields["frm1702q:txtTax17"] == "0.00"
        assert fields["frm1702q:txtTax18"] == "100,000.00"
        assert fields["frm1702q:txtTax19"] == "0.00"
        assert fields["frm1702q:txtTax20"] == "100,000.00"

    def test_part2_zero_penalties(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:txtTax21"] == "0.00"
        assert fields["frm1702q:txtTax22"] == "0.00"
        assert fields["frm1702q:txtTax23"] == "0.00"
        assert fields["frm1702q:txtTax24"] == "0.00"
        assert fields["frm1702q:txtTax25"] == "100,000.00"

    def test_flags(self, gen):
        fields = gen.build_fields()
        assert fields["txtFinalFlag"] == "0"
        assert fields["txtEnroll"] == "N"

    def test_page2_tin_repeater(self, gen):
        fields = gen.build_fields()
        assert fields["frm1702q:txtPg2TIN1"] == "012"
        assert fields["frm1702q:txtPg2TIN2"] == "345"
        assert fields["frm1702q:txtPg2TIN3"] == "678"
        assert fields["frm1702q:txtPg2BranchCode"] == "000"
        assert fields["frm1702q:txtPg2TaxpayerName"] == "TEST CORPORATION"

    def test_sched4_credits_flow_to_tax15_and_tax19(self, taxpayer):
        data = _default_data(
            sched2=_sched2(revenues="2000000.00", cost_of_sales="800000.00", deductions="400000.00"),
            sched4=_sched4(cwt_prior="30000.00", cwt_current="20000.00"),
        )
        fields = Form1702QGenerator(taxpayer, data).build_fields()
        assert fields["frm1702q:Sched4:txtTax2"] == "30,000.00"
        assert fields["frm1702q:Sched4:txtTax3"] == "20,000.00"
        assert fields["frm1702q:Sched4:txtTax7"] == "50,000.00"
        assert fields["frm1702q:txtTax19"] == "50,000.00"

    def test_save_creates_xml_file(self, taxpayer, basic_data, tmp_path):
        gen = Form1702QGenerator(taxpayer, basic_data)
        path = gen.save(tmp_path)
        assert path.exists()
        assert path.suffix == ".xml"

    def test_saved_file_is_parseable(self, taxpayer, basic_data, tmp_path):
        gen = Form1702QGenerator(taxpayer, basic_data)
        path = gen.save(tmp_path)
        content = path.read_text(encoding="utf-8")
        fields = parse_ebirforms_file(content)
        assert fields["frm1702q:txtTax14"] == "100,000.00"
        assert fields["frm1702q:txtTIN1"] == "012"

    def test_build_and_parse_round_trip(self, taxpayer, basic_data):
        gen = Form1702QGenerator(taxpayer, basic_data)
        fields = gen.build_fields()
        content = build_ebirforms_content(fields)
        parsed = parse_ebirforms_file(content)
        for key, value in fields.items():
            assert parsed[key] == value, f"Round-trip mismatch for {key}"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestForm1702QEdgeCases:
    def test_q3_second_year_with_prior_quarters(self, taxpayer):
        """Q3 return: taxable income from Q1 and Q2 flows through item 8."""
        data = _default_data(
            quarter=3,
            sched2=_sched2(
                revenues="500000.00",
                cost_of_sales="200000.00",
                deductions="100000.00",
                taxable_income_prior="400000.00",
                tax_rate="25.00",
            ),
        )
        # This quarter taxable = 200k; total = 600k; tax = 150k
        assert data.sched2_item9 == Decimal("600000.00")
        assert data.tax14 == Decimal("150000.00")

    def test_msme_rate_20_percent(self, taxpayer):
        """MSME corporations with NTI <= 5M and assets <= 100M use 20%."""
        data = _default_data(
            atc_code=ATC_DOMESTIC_20,
            sched2=_sched2(revenues="3000000.00", cost_of_sales="1200000.00", deductions="600000.00", tax_rate="20.00"),
            sched3=_sched3(gross_ops="1800000.00"),
        )
        # Taxable = 1200k; 20% = 240k; MCIT = 1800k * 2% = 36k; tax = 240k
        assert data.tax14 == Decimal("240000.00")

    def test_all_sched1_fields_present_and_zero(self, taxpayer):
        """Schedule 1 fields are all emitted (zeroed) even when unused."""
        data = _default_data()
        fields = Form1702QGenerator(taxpayer, data).build_fields()
        for suffix in ("1A", "1B", "2A", "2B", "13B"):
            key = f"frm1702q:Sched1:txtTax{suffix}"
            assert key in fields, f"Missing {key}"
            assert fields[key] == "0.00"

    def test_fiscal_year_end_month_encoding(self, taxpayer):
        """Fiscal year end month is zero-padded in the select element."""
        data = _default_data(
            is_calendar_year=False,
            fiscal_year_end_month=3,
            fiscal_year_end_year=25,
        )
        fields = Form1702QGenerator(taxpayer, data).build_fields()
        assert fields["frm1702q:rbYrEndMonth"] == "03"
        assert fields["frm1702q:txtYrEndYear"] == "25"

    def test_line_of_business_stored(self, taxpayer):
        data = _default_data()
        fields = Form1702QGenerator(taxpayer, data).build_fields()
        assert fields["frm1702q:txtLOB"] == "INFORMATION TECHNOLOGY"
