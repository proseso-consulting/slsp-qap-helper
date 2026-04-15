"""Orchestrate extraction and generation for eBIRForms XML files.

This module connects extractors (which aggregate Odoo data by ATC code)
to generators (which produce the eBIRForms pseudo-XML format).
"""

from decimal import Decimal

from ebirforms.base import TaxpayerInfo, build_ebirforms_content
from ebirforms.extractors import (
    EwtAtcTotal,
    extract_ewt_summary,
    extract_income_statement,
    extract_vat_summary,
)
from ebirforms.generators.form_0619e import Form0619EData, Form0619EGenerator
from ebirforms.generators.form_0619f import Form0619FData, Form0619FGenerator
from ebirforms.generators.form_1601eq import AtcEntry as EqAtcEntry
from ebirforms.generators.form_1601eq import Form1601EQData, Form1601EQGenerator
from ebirforms.generators.form_1601fq import AtcEntry as FqAtcEntry
from ebirforms.generators.form_1601fq import Form1601FQData, Form1601FQGenerator
from ebirforms.generators.form_1603q import Form1603QData, Form1603QGenerator, FringeBenefitEntry
from ebirforms.generators.form_1604e import Form1604EData, Form1604EGenerator
from ebirforms.generators.form_1702ex import Form1702EXData, Form1702EXGenerator
from ebirforms.generators.form_1702mx import Form1702MXData, Form1702MXGenerator
from ebirforms.generators.form_1702q import (
    DEDUCTION_ITEMIZED,
    Form1702QData,
    Form1702QGenerator,
    Sched2Data,
    Sched3Data,
    Sched4Data,
)
from ebirforms.generators.form_1702rt import DEDUCTION_ITEMIZED as RT_DEDUCTION_ITEMIZED
from ebirforms.generators.form_1702rt import Form1702RTData, Form1702RTGenerator
from ebirforms.generators.form_1702rt import IncomeStatementData as RTIncomeStatement
from ebirforms.generators.form_1702rt import TaxCreditsData as RTTaxCredits
from ebirforms.generators.form_2000 import DstLineItem, Form2000Data, Form2000Generator
from ebirforms.generators.form_2550m import Form2550MData, Form2550MGenerator
from ebirforms.generators.form_2550q import Form2550QData, Form2550QGenerator
from ebirforms.generators.form_2551q import Form2551QData, Form2551QGenerator, PercentageTaxRow


def build_savefile_name(tin12: str, form_number: str, date_from: str, date_to: str) -> str:
    """Build the eBIRForms savefile name: {TIN12}-{Form}-{MMYYYY}.xml"""
    month = date_to[5:7]
    year = date_to[:4]
    return f"{tin12}-{form_number}-{month}{year}.xml"


def _build_0619e(taxpayer: TaxpayerInfo, ewt_totals: list[EwtAtcTotal], date_from: str, date_to: str) -> str:
    """Build 0619-E XML from EWT totals."""
    month = int(date_from[5:7])
    year = int(date_from[:4])
    total_withheld = sum(t.tax_withheld for t in ewt_totals)

    top_atc = max(ewt_totals, key=lambda t: t.tax_withheld).atc_code if ewt_totals else "WC160"

    data = Form0619EData(
        year=year,
        month=month,
        is_amended=False,
        atc_code=top_atc,
        tax_type_code="WE",
        is_private=True,
        total_withheld=total_withheld,
        adjustment=Decimal(0),
        previously_remitted=Decimal(0),
        credit_17b=Decimal(0),
        credit_17c=Decimal(0),
        credit_17d=Decimal(0),
    )
    gen = Form0619EGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_1601eq(
    taxpayer: TaxpayerInfo,
    ewt_totals: list[EwtAtcTotal],
    date_from: str,
    date_to: str,
    *,
    month1_total: Decimal = Decimal(0),
    month2_total: Decimal = Decimal(0),
) -> str:
    """Build 1601-EQ XML from EWT totals.

    month1_total/month2_total are the 0619-E remittances for the first
    two months of the quarter (auto-computed from monthly EWT data).
    """
    year = int(date_from[:4])
    quarter_month = int(date_to[5:7])
    quarter = {3: 1, 6: 2, 9: 3, 12: 4}.get(quarter_month, 1)

    entries = tuple(EqAtcEntry(atc_code=t.atc_code, tax_base=t.tax_base, tax_rate=t.tax_rate) for t in ewt_totals)

    data = Form1601EQData(
        year=year,
        quarter=quarter,
        is_amended=False,
        is_private=True,
        atc_entries=entries,
        remittance_month1=month1_total,
        remittance_month2=month2_total,
        previously_remitted_amended=Decimal(0),
        over_remittance_prior_quarter=Decimal(0),
        surcharge=Decimal(0),
        interest=Decimal(0),
        compromise=Decimal(0),
        if_refund=False,
        if_issue_cert=False,
        if_carried_over=False,
    )
    gen = Form1601EQGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_0619f(taxpayer: TaxpayerInfo, fwt_totals: list[EwtAtcTotal], date_from: str, date_to: str) -> str:
    """Build 0619-F XML from FWT totals."""
    month = int(date_from[5:7])
    year = int(date_from[:4])

    business_total = sum(t.tax_withheld for t in fwt_totals if t.atc_code.startswith("WC"))
    final_total = sum(t.tax_withheld for t in fwt_totals if t.atc_code.startswith("WV"))

    tax_type = "WB" if business_total >= final_total else "WF"

    data = Form0619FData(
        year=year,
        month=month,
        is_amended=False,
        tax_type_code=tax_type,
        is_private=True,
        business_tax=business_total,
        final_tax=final_total,
        adjustment=Decimal(0),
        surcharge=Decimal(0),
        interest=Decimal(0),
        compromise=Decimal(0),
    )
    gen = Form0619FGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_1601fq(
    taxpayer: TaxpayerInfo,
    fwt_totals: list[EwtAtcTotal],
    date_from: str,
    date_to: str,
    *,
    month1_total: Decimal = Decimal(0),
    month2_total: Decimal = Decimal(0),
) -> str:
    """Build 1601-FQ XML from FWT totals."""
    year = int(date_from[:4])
    quarter_month = int(date_to[5:7])
    quarter = {3: 1, 6: 2, 9: 3, 12: 4}.get(quarter_month, 1)

    entries = tuple(
        FqAtcEntry(
            atc_code=t.atc_code,
            tax_base=t.tax_base,
            tax_rate=t.tax_rate,
            tax_withheld=t.tax_withheld,
        )
        for t in fwt_totals
    )
    total = sum(t.tax_withheld for t in fwt_totals)

    data = Form1601FQData(
        year=year,
        quarter=quarter,
        is_amended=False,
        is_private=True,
        atc_entries=entries,
        total_tax_withheld=total,
        tax_remitted_previous=Decimal(0),
        total_credits=month1_total + month2_total,
        surcharge=Decimal(0),
        interest=Decimal(0),
        compromise=Decimal(0),
    )
    gen = Form1601FQGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_2550m(taxpayer: TaxpayerInfo, raw_vat: dict, date_from: str, date_to: str) -> str:
    """Build 2550-M XML from VAT summary."""
    vat = extract_vat_summary(raw_vat)
    month = int(date_from[5:7])
    year = int(date_from[:4])

    data = Form2550MData(
        year=year,
        month=month,
        is_amended=False,
        vatable_sales=vat.vatable_sales,
        output_tax_private=vat.output_vat,
        sales_to_govt=vat.sales_to_govt,
        output_tax_govt=vat.output_tax_govt,
        zero_rated_sales=vat.zero_rated_sales,
        exempt_sales=vat.exempt_sales,
        domestic_services_purchases=vat.total_purchases,
        domestic_services_input_tax=vat.input_vat,
    )
    gen = Form2550MGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_2550q(taxpayer: TaxpayerInfo, raw_vat: dict, date_from: str, date_to: str) -> str:
    """Build 2550-Q XML from VAT summary."""
    vat = extract_vat_summary(raw_vat)
    year = int(date_from[:4])
    quarter_month = int(date_to[5:7])
    quarter = {3: 1, 6: 2, 9: 3, 12: 4}.get(quarter_month, 1)

    zero = Decimal(0)
    data = Form2550QData(
        year=year,
        quarter=quarter,
        is_amended=False,
        vatable_sales=vat.vatable_sales,
        zero_rated_sales=vat.zero_rated_sales,
        exempt_sales=vat.exempt_sales,
        less_output_vat=zero,
        add_output_vat=zero,
        input_tax_carried=zero,
        input_tax_deferred=zero,
        transitional_input_tax=zero,
        presumptive_input_tax=zero,
        other_prior_input_tax=zero,
        other_prior_input_tax_label="",
        domestic_purchase=zero,
        domestic_input_tax=zero,
        services_purchase=vat.total_purchases,
        service_input_tax=vat.input_vat,
        import_purchase=zero,
        import_input_tax=zero,
        other_purchase=zero,
        other_purchase_label="",
        other_purchase_input_tax=zero,
        domestic_purchase_no_tax=zero,
        vat_exempt_imports=zero,
        import_capital_input_tax=zero,
        input_tax_attr=zero,
        vat_refund=zero,
        input_vat_unpaid=zero,
        other_deduction=zero,
        other_deduction_label="",
        add_input_vat=zero,
        creditable_vat=zero,
        adv_vat_payment=zero,
        vat_paid_return=zero,
        other_credits=zero,
        other_credits_label="",
        surcharge=zero,
        interest=zero,
        compromise=zero,
        taxpayer_classification=3,
    )
    gen = Form2550QGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_1702q(taxpayer: TaxpayerInfo, raw_income: dict, date_from: str, date_to: str) -> str:
    """Build 1702-Q XML from income statement data."""
    pnl = extract_income_statement(raw_income)
    year = int(date_from[:4])
    quarter_month = int(date_to[5:7])
    quarter = {3: 1, 6: 2, 9: 3, 12: 4}.get(quarter_month, 1)

    tax_rate = Decimal("25.00")
    mcit_rate = Decimal("2.00")

    sched2 = Sched2Data(
        revenues=pnl.revenue,
        cost_of_sales=pnl.cost_of_sales,
        non_operating_income=pnl.non_operating_income,
        deductions=pnl.deductions,
        taxable_income_prior_quarters=Decimal(0),
        tax_rate=tax_rate,
    )
    sched3 = Sched3Data(
        gross_income_from_operations=pnl.gross_income,
        non_operating_income=pnl.non_operating_income,
        other_gross_income=Decimal(0),
        mcit_rate=mcit_rate,
    )
    sched4 = Sched4Data(
        prior_quarter_payments=Decimal(0),
        creditable_wt_prior_quarters=Decimal(0),
        creditable_wt_this_quarter=Decimal(0),
        tax_paid_previously_filed=Decimal(0),
        foreign_tax_credits=Decimal(0),
        special_tax_credits=Decimal(0),
    )

    data = Form1702QData(
        fiscal_year_end_month=12,
        fiscal_year_end_year=year % 100,
        quarter=quarter,
        is_calendar_year=True,
        is_amended=False,
        atc_code=f"IC010_{int(tax_rate)}%",
        deduction_method=DEDUCTION_ITEMIZED,
        sched2=sched2,
        sched3=sched3,
        sched4=sched4,
    )
    gen = Form1702QGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_1702rt(taxpayer: TaxpayerInfo, raw_income: dict, date_from: str, date_to: str) -> str:
    """Build 1702-RT XML from income statement data."""
    pnl = extract_income_statement(raw_income)
    year = int(date_from[:4])
    tax_rate = Decimal("25.00")

    income_stmt = RTIncomeStatement(
        gross_sales=pnl.revenue,
        sales_returns=Decimal(0),
        cost_of_sales=pnl.cost_of_sales,
        non_operating_income=pnl.non_operating_income,
        ordinary_allowable_deductions=pnl.deductions,
        special_allowable_deductions=Decimal(0),
        nolco=Decimal(0),
        tax_rate=tax_rate,
    )
    tax_credits = RTTaxCredits(
        excess_mcit_prior_years=Decimal(0),
        income_tax_payment_mcit=Decimal(0),
        income_tax_payment_regular=Decimal(0),
        creditable_wt_prior_year=Decimal(0),
        creditable_wt_4th_quarter=Decimal(0),
        foreign_tax_credits=Decimal(0),
        tax_paid_previously_filed=Decimal(0),
        special_tax_credits=Decimal(0),
    )

    data = Form1702RTData(
        fiscal_year_end_month=12,
        fiscal_year_end_year=year,
        is_calendar_year=True,
        is_amended=False,
        is_short_period=False,
        deduction_method=RT_DEDUCTION_ITEMIZED,
        income_statement=income_stmt,
        tax_credits=tax_credits,
    )
    gen = Form1702RTGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_1702ex(taxpayer: TaxpayerInfo, raw_income: dict, date_from: str, date_to: str) -> str:
    """Build 1702-EX XML from income statement data."""
    pnl = extract_income_statement(raw_income)
    year = int(date_from[:4])

    data = Form1702EXData(
        year=year,
        is_amended=False,
        is_calendar_year=True,
        gross_income=pnl.revenue - pnl.cost_of_sales + pnl.non_operating_income,
        total_deductions=pnl.deductions,
        net_income=pnl.net_taxable_income,
        exemption_type="",
    )
    gen = Form1702EXGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_1702mx(taxpayer: TaxpayerInfo, raw_income: dict, date_from: str, date_to: str) -> str:
    """Build 1702-MX XML from income statement data."""
    pnl = extract_income_statement(raw_income)
    year = int(date_from[:4])
    tax_rate = Decimal("25.00")

    data = Form1702MXData(
        year=year,
        is_amended=False,
        is_calendar_year=True,
        regular_gross_income=pnl.revenue - pnl.cost_of_sales + pnl.non_operating_income,
        regular_deductions=pnl.deductions,
        regular_net_taxable=pnl.net_taxable_income,
        regular_tax_rate=tax_rate,
        regular_tax_due=pnl.net_taxable_income * tax_rate / 100,
        exempt_gross_income=Decimal(0),
        exempt_deductions=Decimal(0),
        exempt_net_income=Decimal(0),
        prior_year_excess=Decimal(0),
        quarterly_payments=Decimal(0),
        creditable_wt=Decimal(0),
        surcharge=Decimal(0),
        interest=Decimal(0),
        compromise=Decimal(0),
    )
    gen = Form1702MXGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_1603q(taxpayer: TaxpayerInfo, manual: dict, date_from: str, date_to: str) -> str:
    """Build 1603-Q from manual fringe benefit entries."""
    entries = tuple(
        FringeBenefitEntry(
            description=e["description"],
            tax_base=Decimal(str(e["tax_base"])),
            tax_withheld=Decimal(str(e["tax_withheld"])),
        )
        for e in manual.get("entries", [])
    )
    total = sum(e.tax_withheld for e in entries)

    data = Form1603QData(
        year=manual["year"],
        quarter=manual["quarter"],
        is_amended=False,
        is_private=True,
        schedule_entries=entries,
        total_tax_withheld=total,
        tax_remitted_previous=Decimal(0),
        surcharge=Decimal(0),
        interest=Decimal(0),
        compromise=Decimal(0),
    )
    gen = Form1603QGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_2551q(taxpayer: TaxpayerInfo, manual: dict, date_from: str, date_to: str) -> str:
    """Build 2551-Q from manual percentage tax rows."""
    rows = tuple(
        PercentageTaxRow(
            atc_code=r["atc_code"],
            atc_description=r["atc_description"],
            tax_base=Decimal(str(r["tax_base"])),
            tax_rate=Decimal(str(r["tax_rate"])),
            tax_due=Decimal(str(r["tax_due"])),
        )
        for r in manual.get("rows", [])
    )
    data = Form2551QData(
        year=manual["year"],
        quarter=manual["quarter"],
        is_calendar_year=True,
        year_ended_month=12,
        is_amended=False,
        has_tax_treaty=False,
        tax_rows=rows,
        prior_year_excess=Decimal(0),
        amended_credits=Decimal(0),
        surcharge=Decimal(0),
        interest=Decimal(0),
        compromise=Decimal(0),
    )
    gen = Form2551QGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_2000(taxpayer: TaxpayerInfo, manual: dict, date_from: str, date_to: str) -> str:
    """Build 2000 from manual DST line items."""
    items = tuple(
        DstLineItem(
            atc_code=item["atc_code"],
            tax_base=Decimal(str(item["tax_base"])),
            tax_rate=item["tax_rate"],
            tax_due=Decimal(str(item["tax_due"])),
        )
        for item in manual.get("line_items", [])
    )
    data = Form2000Data(
        year=manual["year"],
        month=manual["month"],
        is_amended=False,
        line_items=items,
    )
    gen = Form2000Generator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


def _build_1604e(taxpayer: TaxpayerInfo, manual: dict, date_from: str, date_to: str) -> str:
    """Build 1604-E from manual/aggregated remittance data."""
    data = Form1604EData(
        year=manual["year"],
        is_amended=False,
        is_private=True,
        is_top_withholding_agent=manual.get("is_top_withholding_agent", False),
    )
    gen = Form1604EGenerator(taxpayer, data)
    return build_ebirforms_content(gen.build_fields())


# Map form numbers to builder functions
_FORM_BUILDERS = {
    # EWT
    "0619E": lambda tp, data, df, dt: _build_0619e(tp, extract_ewt_summary(data, category="expanded"), df, dt),
    "1601EQ": lambda tp, data, df, dt: _build_1601eq(tp, extract_ewt_summary(data, category="expanded"), df, dt),
    # FWT
    "0619F": lambda tp, data, df, dt: _build_0619f(tp, extract_ewt_summary(data, category="final"), df, dt),
    "1601FQ": lambda tp, data, df, dt: _build_1601fq(tp, extract_ewt_summary(data, category="final"), df, dt),
    # VAT
    "2550M": lambda tp, data, df, dt: _build_2550m(tp, data, df, dt),
    "2550Q": lambda tp, data, df, dt: _build_2550q(tp, data, df, dt),
    # Income Tax
    "1702Q": lambda tp, data, df, dt: _build_1702q(tp, data, df, dt),
    "1702RT": lambda tp, data, df, dt: _build_1702rt(tp, data, df, dt),
    "1702EX": lambda tp, data, df, dt: _build_1702ex(tp, data, df, dt),
    "1702MX": lambda tp, data, df, dt: _build_1702mx(tp, data, df, dt),
    # Manual-input forms
    "1603Q": lambda tp, data, df, dt: _build_1603q(tp, data, df, dt),
    "2551Q": lambda tp, data, df, dt: _build_2551q(tp, data, df, dt),
    "2000": lambda tp, data, df, dt: _build_2000(tp, data, df, dt),
    "1604E": lambda tp, data, df, dt: _build_1604e(tp, data, df, dt),
}


def build_form_xml(
    form_number: str,
    taxpayer: TaxpayerInfo,
    raw_data: list[dict] | dict,
    date_from: str,
    date_to: str,
    *,
    data_type: str = "ewt",
    monthly_raw: list[list[dict]] | None = None,
) -> str:
    """Build eBIRForms XML content for a given form.

    Args:
        form_number: BIR form number (e.g., "0619E", "1601EQ")
        taxpayer: Taxpayer profile info
        raw_data: Output from fetch_tax_lines_by_atc (list) or fetch_vat_summary (dict)
        date_from: Period start (YYYY-MM-DD)
        date_to: Period end (YYYY-MM-DD)
        data_type: "ewt" for withholding tax forms, "vat" for VAT forms
        monthly_raw: For quarterly EWT forms, list of 3 monthly raw line lists
            [month1_lines, month2_lines, month3_lines] used to compute
            0619-E/F remittance amounts for items 20-21.

    Returns:
        eBIRForms pseudo-XML string ready to write to file.
    """
    # Quarterly EWT/FWT forms with monthly data: compute remittances
    if form_number == "1601EQ" and monthly_raw and len(monthly_raw) == 3:
        ewt_totals = extract_ewt_summary(raw_data, category="expanded")
        m1 = sum(t.tax_withheld for t in extract_ewt_summary(monthly_raw[0], category="expanded"))
        m2 = sum(t.tax_withheld for t in extract_ewt_summary(monthly_raw[1], category="expanded"))
        return _build_1601eq(taxpayer, ewt_totals, date_from, date_to, month1_total=m1, month2_total=m2)

    if form_number == "1601FQ" and monthly_raw and len(monthly_raw) == 3:
        fwt_totals = extract_ewt_summary(raw_data, category="final")
        m1 = sum(t.tax_withheld for t in extract_ewt_summary(monthly_raw[0], category="final"))
        m2 = sum(t.tax_withheld for t in extract_ewt_summary(monthly_raw[1], category="final"))
        return _build_1601fq(taxpayer, fwt_totals, date_from, date_to, month1_total=m1, month2_total=m2)

    builder = _FORM_BUILDERS.get(form_number)
    if builder is None:
        raise ValueError(f"No builder for form {form_number}. Available: {sorted(_FORM_BUILDERS.keys())}")
    return builder(taxpayer, raw_data, date_from, date_to)
