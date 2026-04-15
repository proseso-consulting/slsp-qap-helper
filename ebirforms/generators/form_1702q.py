"""Generator for BIR Form 1702-Q v2018 (Quarterly Income Tax Return for Corporations).

XML structure reverse-engineered from: extracted_hta/decoded/renamed/forms_BIR-Form1702Qv2018.hta

Field prefix: frm1702q  (note: lowercase q, differs from the filename suffix)

Key sections:
    Part I   - Background Information
    Part II  - Tax Computation Summary (Items 14-25)
    Sched 1  - Special/Exempt Rate Income (columns A/B)
    Sched 2  - Regular/Normal Rate Income Statement
    Sched 3  - Minimum Corporate Income Tax (MCIT)
    Sched 4  - Tax Credits / Payments

Schedule 2 field map (regular rate, the main income statement):
    frm1702q:Sched2:txtTax1   -> Sales/Receipts/Revenues/Fees
    frm1702q:Sched2:txtTax2   -> Less: Cost of Sale/Services
    frm1702q:Sched2:txtTax3   -> Gross Income from Operations (1 - 2)
    frm1702q:Sched2:txtTax4   -> Add: Non-Operating and Other Taxable Income
    frm1702q:Sched2:txtTax5   -> Total Gross Income (3 + 4)
    frm1702q:Sched2:txtTax6   -> Less: Deductions (actual or 40% OSD)
    frm1702q:Sched2:txtTax7   -> Taxable Income this Quarter (5 - 6)
    frm1702q:Sched2:txtTax8   -> Add: Taxable Income from Previous Quarter/s
    frm1702q:Sched2:txtTax9   -> Total Taxable Income to Date (7 + 8)
    frm1702q:Sched2:txtTax10  -> Applicable Tax Rate (%)
    frm1702q:Sched2:txtTax11  -> Income Tax Due Other than MCIT (9 x 10%)
    frm1702q:Sched2:txtTax12  -> MCIT (from Schedule 3)
    frm1702q:Sched2:txtTax13  -> Income Tax Due (higher of 11 and 12)

Schedule 3 field map (MCIT):
    frm1702q:Sched3:txtTax1   -> Gross Income from Operations
    frm1702q:Sched3:txtTax2   -> Add: Non-Operating Income
    frm1702q:Sched3:txtTax3   -> Other Gross Income
    frm1702q:Sched3:txtTax4   -> Total Gross Income (1 + 2 + 3)
    frm1702q:Sched3:txtTax5   -> MCIT Rate (%)
    frm1702q:Sched3:txtTax6   -> MCIT Amount (4 x 5%)

Schedule 4 field map (tax credits):
    frm1702q:Sched4:txtTax1   -> Prior Quarter Tax Payments
    frm1702q:Sched4:txtTax2   -> Creditable Tax Withheld Previous Quarter/s
    frm1702q:Sched4:txtTax3   -> Creditable Tax Withheld this Quarter
    frm1702q:Sched4:txtTax4   -> Tax Paid in Return Previously Filed (amended)
    frm1702q:Sched4:txtTax5   -> Foreign Tax Credits
    frm1702q:Sched4:txtTax6   -> Special Tax Credits
    frm1702q:Sched4:txtTax7   -> Total Tax Credits (sum of 1-6 + other credits)

Part II field map:
    frm1702q:txtTax14   -> Income Tax Due - Regular Rate (from Sched2 item 13)
    frm1702q:txtTax15   -> Less: Tax Credits/Payments this Return (user-editable)
    frm1702q:txtTax16   -> Income Tax Still Due (14 - 15)
    frm1702q:txtTax17   -> Add: Income Tax Due - Special Rate (from Sched1)
    frm1702q:txtTax18   -> Aggregate Income Tax Due (16 + 17)
    frm1702q:txtTax19   -> Less: Total Tax Credits/Payments (from Sched4 item 7)
    frm1702q:txtTax20   -> Net Tax Payable / (Overpayment) (18 - 19)
    frm1702q:txtTax21   -> Add: Surcharge
    frm1702q:txtTax22   -> Add: Interest
    frm1702q:txtTax23   -> Add: Compromise Penalty
    frm1702q:txtTax24   -> Total Penalties (21 + 22 + 23)
    frm1702q:txtTax25   -> Total Amount Still Due / (Overpayment) (20 + 24)
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo

# ATC codes for the cbATC_2 dropdown (regular-rate corporations).
# The value encodes the ATC + applicable rate, e.g. "IC010_25%".
ATC_DOMESTIC_25 = "IC010_25%"
ATC_DOMESTIC_20 = "IC010_20%"
ATC_DOMESTIC_30 = "IC010_30%"

# Deduction method constants (rbMthdOfDdctns)
DEDUCTION_ITEMIZED = "itemized"
DEDUCTION_OSD = "osd"  # 40% Optional Standard Deduction

_ZERO = Decimal("0.00")
_OSD_RATE = Decimal("0.40")


def _fmt_money(amount: Decimal) -> str:
    """Format decimal as eBIRForms money string: '1,234,567.00'."""
    return f"{amount:,.2f}"


def _fmt_rate(rate: Decimal) -> str:
    """Format tax rate as a plain decimal string: '25.00'."""
    return f"{rate:.2f}"


def _round2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Sched2Data:
    """Schedule 2: Regular/Normal Rate income statement for this quarter."""

    revenues: Decimal  # Item 1
    cost_of_sales: Decimal  # Item 2
    non_operating_income: Decimal  # Item 4
    deductions: Decimal  # Item 6 (actual deductions; ignored when OSD is used)
    taxable_income_prior_quarters: Decimal  # Item 8
    tax_rate: Decimal  # Item 10 (e.g., Decimal("25.00") for 25%)

    @property
    def gross_income_from_operations(self) -> Decimal:
        """Item 3: Revenue - COS."""
        return _round2(self.revenues - self.cost_of_sales)

    @property
    def total_gross_income(self) -> Decimal:
        """Item 5: Gross income from operations + non-operating income."""
        return _round2(self.gross_income_from_operations + self.non_operating_income)

    def taxable_income_this_quarter(self, use_osd: bool) -> Decimal:
        """Item 7: Total gross income less deductions (OSD = 40% of TGI)."""
        effective_deductions = _round2(self.total_gross_income * _OSD_RATE) if use_osd else self.deductions
        return _round2(self.total_gross_income - effective_deductions)

    def total_taxable_income(self, use_osd: bool) -> Decimal:
        """Item 9: This quarter + prior quarters."""
        return _round2(self.taxable_income_this_quarter(use_osd) + self.taxable_income_prior_quarters)

    def income_tax_due_regular(self, use_osd: bool) -> Decimal:
        """Item 11: Taxable income x tax rate (floored at zero)."""
        tti = self.total_taxable_income(use_osd)
        if tti <= _ZERO:
            return _ZERO
        return _round2(tti * self.tax_rate / Decimal("100"))

    def effective_deductions(self, use_osd: bool) -> Decimal:
        """Item 6 as stored in the form."""
        if use_osd:
            return _round2(self.total_gross_income * _OSD_RATE)
        return self.deductions


@dataclass(frozen=True)
class Sched3Data:
    """Schedule 3: Minimum Corporate Income Tax (MCIT)."""

    gross_income_from_operations: Decimal  # Item 1
    non_operating_income: Decimal  # Item 2
    other_gross_income: Decimal  # Item 3
    mcit_rate: Decimal  # Item 5 (e.g., Decimal("2.00") for 2%)

    @property
    def total_gross_income(self) -> Decimal:
        """Item 4: Sum of 1 + 2 + 3."""
        return _round2(self.gross_income_from_operations + self.non_operating_income + self.other_gross_income)

    @property
    def mcit(self) -> Decimal:
        """Item 6: Total gross income x MCIT rate."""
        return _round2(self.total_gross_income * self.mcit_rate / Decimal("100"))


@dataclass(frozen=True)
class Sched4Data:
    """Schedule 4: Tax credits and payments."""

    prior_quarter_payments: Decimal  # Item 1
    creditable_wt_prior_quarters: Decimal  # Item 2
    creditable_wt_this_quarter: Decimal  # Item 3
    tax_paid_previously_filed: Decimal  # Item 4 (amended returns)
    foreign_tax_credits: Decimal  # Item 5
    special_tax_credits: Decimal  # Item 6

    @property
    def total(self) -> Decimal:
        """Item 7: Sum of all credits (excluding 'other credits' rows)."""
        return _round2(
            self.prior_quarter_payments
            + self.creditable_wt_prior_quarters
            + self.creditable_wt_this_quarter
            + self.tax_paid_previously_filed
            + self.foreign_tax_credits
            + self.special_tax_credits
        )


@dataclass(frozen=True)
class Form1702QData:
    """All data needed to generate BIR Form 1702-Q v2018."""

    # Period
    fiscal_year_end_month: int  # 1-12
    fiscal_year_end_year: int  # last 2 digits, e.g. 25 for 2025
    quarter: int  # 1, 2, or 3
    is_calendar_year: bool  # True = calendar year, False = fiscal year

    # Return type
    is_amended: bool
    atc_code: str  # e.g., "IC010_25%"
    deduction_method: str  # DEDUCTION_ITEMIZED or DEDUCTION_OSD

    # Schedules
    sched2: Sched2Data
    sched3: Sched3Data
    sched4: Sched4Data

    # Penalties (normally zero unless filing late)
    surcharge: Decimal = _ZERO  # Item 21
    interest: Decimal = _ZERO  # Item 22
    compromise: Decimal = _ZERO  # Item 23

    # Special-rate income (Schedule 1) - most regular corps leave this at zero
    # Item 17 in Part II flows from Sched1:txtTax13B
    special_rate_tax_due: Decimal = _ZERO

    # Page 2 TIN repeater and sheets count
    sheets_attached: str = ""

    @property
    def _use_osd(self) -> bool:
        return self.deduction_method == DEDUCTION_OSD

    # ------------------------------------------------------------------
    # Sched2 derived values
    # ------------------------------------------------------------------

    @property
    def sched2_item3(self) -> Decimal:
        return self.sched2.gross_income_from_operations

    @property
    def sched2_item5(self) -> Decimal:
        return self.sched2.total_gross_income

    @property
    def sched2_item6(self) -> Decimal:
        return self.sched2.effective_deductions(self._use_osd)

    @property
    def sched2_item7(self) -> Decimal:
        return self.sched2.taxable_income_this_quarter(self._use_osd)

    @property
    def sched2_item9(self) -> Decimal:
        return self.sched2.total_taxable_income(self._use_osd)

    @property
    def sched2_item11(self) -> Decimal:
        return self.sched2.income_tax_due_regular(self._use_osd)

    @property
    def sched2_item12(self) -> Decimal:
        """MCIT from Schedule 3."""
        return self.sched3.mcit

    @property
    def sched2_item13(self) -> Decimal:
        """Income Tax Due: higher of regular tax and MCIT."""
        return max(self.sched2_item11, self.sched2_item12)

    # ------------------------------------------------------------------
    # Part II summary
    # ------------------------------------------------------------------

    @property
    def tax14(self) -> Decimal:
        """Income Tax Due - Regular Rate (from Sched2 item 13)."""
        return self.sched2_item13

    @property
    def tax15(self) -> Decimal:
        """Less: Tax Credits applied this return.

        The HTA only allows this field when regular tax > MCIT.  We always
        apply the full Sched4 total (caller can set it to zero if not applicable).
        """
        return self.sched4.total

    @property
    def tax16(self) -> Decimal:
        """Income Tax Still Due (14 - 15)."""
        return _round2(self.tax14 - self.tax15)

    @property
    def tax17(self) -> Decimal:
        """Add: Income Tax Due - Special Rate (from Sched1 item 13B)."""
        return self.special_rate_tax_due

    @property
    def tax18(self) -> Decimal:
        """Aggregate Income Tax Due (16 + 17)."""
        return _round2(self.tax16 + self.tax17)

    @property
    def tax19(self) -> Decimal:
        """Less: Total Tax Credits/Payments (Sched4 item 7)."""
        return self.sched4.total

    @property
    def tax20(self) -> Decimal:
        """Net Tax Payable / (Overpayment) (18 - 19)."""
        return _round2(self.tax18 - self.tax19)

    @property
    def tax24(self) -> Decimal:
        """Total Penalties (21 + 22 + 23)."""
        return _round2(self.surcharge + self.interest + self.compromise)

    @property
    def tax25(self) -> Decimal:
        """Total Amount Still Due / (Overpayment) (20 + 24)."""
        # When overpayment (tax20 < 0) and there are penalties, only show penalties.
        if self.tax20 < _ZERO and self.tax24 > _ZERO:
            return self.tax24
        return _round2(self.tax20 + self.tax24)


class Form1702QGenerator(FormGenerator):
    """Generates BIR Form 1702-Q v2018."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form1702QData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "1702Qv2018"

    @property
    def form_prefix(self) -> str:
        # The HTA uses 'frm1702q' (lowercase q) as the field prefix.
        return "frm1702q"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields: dict[str, str] = {}

        # ------------------------------------------------------------------
        # Part I - Period and return type
        # ------------------------------------------------------------------
        # Calendar (1) vs Fiscal (2) year
        fields[f"{p}:rbForClndrFscl_1"] = "true" if d.is_calendar_year else "false"
        fields[f"{p}:rbForClndrFscl_2"] = "false" if d.is_calendar_year else "true"

        # Year-end (last 2 digits) and month
        fields[f"{p}:txtYrEndYear"] = str(d.fiscal_year_end_year)
        fields[f"{p}:rbYrEndMonth"] = f"{d.fiscal_year_end_month:02d}"

        # Quarter (only Q1, Q2, Q3 are valid for 1702-Q)
        fields[f"{p}:rbQuarter_1"] = "true" if d.quarter == 1 else "false"
        fields[f"{p}:rbQuarter_2"] = "true" if d.quarter == 2 else "false"
        fields[f"{p}:rbQuarter_3"] = "true" if d.quarter == 3 else "false"

        # Amended return
        fields[f"{p}:rbAmendedRtn_1"] = "true" if d.is_amended else "false"
        fields[f"{p}:rbAmendedRtn_2"] = "false" if d.is_amended else "true"

        # ATC - regular corporations use cbATC_2; rbATC_1 is for non-standard
        fields[f"{p}:rbATC_1"] = "false"
        fields[f"{p}:cbATC_2"] = d.atc_code
        fields[f"{p}:rbATC_2"] = "true"
        fields[f"{p}:txtATC_1"] = ""

        # ------------------------------------------------------------------
        # Background information (taxpayer)
        # ------------------------------------------------------------------
        fields.update(self._taxpayer_fields())
        fields[f"{p}:txtTaxpayerName1"] = self._taxpayer.name
        fields[f"{p}:txtLOB"] = self._taxpayer.line_of_business

        # Method of deductions: 1 = itemized, 2 = OSD
        fields[f"{p}:rbMthdOfDdctns_1"] = "true" if d.deduction_method == DEDUCTION_ITEMIZED else "false"
        fields[f"{p}:rbMthdOfDdctns_2"] = "true" if d.deduction_method == DEDUCTION_OSD else "false"

        # Tax relief (N/A for regular corporations)
        fields[f"{p}:rbTxRlf_1"] = "false"
        fields[f"{p}:rbTxRlf_2"] = "true"
        fields[f"{p}:txtTxRlfSpcfy"] = ""

        # ------------------------------------------------------------------
        # Page 2 header (TIN / name repeater)
        # ------------------------------------------------------------------
        tin1, tin2, tin3, branch = self._taxpayer.tin_parts
        fields[f"{p}:txtPg2TIN1"] = tin1
        fields[f"{p}:txtPg2TIN2"] = tin2
        fields[f"{p}:txtPg2TIN3"] = tin3
        fields[f"{p}:txtPg2BranchCode"] = branch
        fields[f"{p}:txtPg2TaxpayerName"] = self._taxpayer.name
        fields[f"{p}:txtSheets"] = d.sheets_attached

        # ------------------------------------------------------------------
        # Schedule 1 - Special/Exempt Rate (not implemented, zeroed out)
        # ------------------------------------------------------------------
        sched1_fields = [
            "txtTax1A",
            "txtTax1B",
            "txtTax2A",
            "txtTax2B",
            "txtTax3A",
            "txtTax3B",
            "txtTax4A",
            "txtTax4B",
            "txtTax5A",
            "txtTax5B",
            "txtTax6A",
            "txtTax6B",
            "txtTax7A",
            "txtTax7B",
            "txtTax8A",
            "txtTax8B",
            "txtTax9A",
            "txtTax9B",
            "txtTax10A",
            "txtTax10B",
            "txtTax11A",
            "txtTax11B",
            "txtTax12B",
            "txtTax13B",
        ]
        for fname in sched1_fields:
            fields[f"{p}:Sched1:{fname}"] = "0.00"

        # ------------------------------------------------------------------
        # Schedule 2 - Regular Rate income statement
        # ------------------------------------------------------------------
        s2 = d.sched2
        s2p = f"{p}:Sched2"
        fields[f"{s2p}:txtTax1"] = _fmt_money(s2.revenues)
        fields[f"{s2p}:txtTax2"] = _fmt_money(s2.cost_of_sales)
        fields[f"{s2p}:txtTax3"] = _fmt_money(d.sched2_item3)
        fields[f"{s2p}:txtTax4"] = _fmt_money(s2.non_operating_income)
        fields[f"{s2p}:txtTax5"] = _fmt_money(d.sched2_item5)
        fields[f"{s2p}:txtTax6"] = _fmt_money(d.sched2_item6)
        fields[f"{s2p}:txtTax7"] = _fmt_money(d.sched2_item7)
        fields[f"{s2p}:txtTax8"] = _fmt_money(s2.taxable_income_prior_quarters)
        fields[f"{s2p}:txtTax9"] = _fmt_money(d.sched2_item9)
        fields[f"{s2p}:txtTax10"] = _fmt_rate(s2.tax_rate)
        fields[f"{s2p}:txtTax11"] = _fmt_money(d.sched2_item11)
        fields[f"{s2p}:txtTax12"] = _fmt_money(d.sched2_item12)
        fields[f"{s2p}:txtTax13"] = _fmt_money(d.sched2_item13)

        # ------------------------------------------------------------------
        # Schedule 3 - MCIT
        # ------------------------------------------------------------------
        s3 = d.sched3
        s3p = f"{p}:Sched3"
        fields[f"{s3p}:txtTax1"] = _fmt_money(s3.gross_income_from_operations)
        fields[f"{s3p}:txtTax2"] = _fmt_money(s3.non_operating_income)
        fields[f"{s3p}:txtTax3"] = _fmt_money(s3.other_gross_income)
        fields[f"{s3p}:txtTax4"] = _fmt_money(s3.total_gross_income)
        fields[f"{s3p}:txtTax5"] = _fmt_rate(s3.mcit_rate)
        fields[f"{s3p}:txtTax6"] = _fmt_money(s3.mcit)

        # ------------------------------------------------------------------
        # Schedule 4 - Tax Credits
        # ------------------------------------------------------------------
        s4 = d.sched4
        s4p = f"{p}:Sched4"
        fields[f"{s4p}:txtTax1"] = _fmt_money(s4.prior_quarter_payments)
        fields[f"{s4p}:txtTax2"] = _fmt_money(s4.creditable_wt_prior_quarters)
        fields[f"{s4p}:txtTax3"] = _fmt_money(s4.creditable_wt_this_quarter)
        fields[f"{s4p}:txtTax4"] = _fmt_money(s4.tax_paid_previously_filed)
        fields[f"{s4p}:txtTax5"] = _fmt_money(s4.foreign_tax_credits)
        fields[f"{s4p}:txtTax6"] = _fmt_money(s4.special_tax_credits)
        fields[f"{s4p}:txtTax7"] = _fmt_money(s4.total)

        # ------------------------------------------------------------------
        # Part II - Tax computation summary
        # ------------------------------------------------------------------
        fields[f"{p}:txtTax14"] = _fmt_money(d.tax14)
        fields[f"{p}:txtTax15"] = _fmt_money(d.tax15)
        fields[f"{p}:txtTax16"] = _fmt_money(d.tax16)
        fields[f"{p}:txtTax17"] = _fmt_money(d.tax17)
        fields[f"{p}:txtTax18"] = _fmt_money(d.tax18)
        fields[f"{p}:txtTax19"] = _fmt_money(d.tax19)
        fields[f"{p}:txtTax20"] = _fmt_money(d.tax20)
        fields[f"{p}:txtTax21"] = _fmt_money(d.surcharge)
        fields[f"{p}:txtTax22"] = _fmt_money(d.interest)
        fields[f"{p}:txtTax23"] = _fmt_money(d.compromise)
        fields[f"{p}:txtTax24"] = _fmt_money(d.tax24)
        fields[f"{p}:txtTax25"] = _fmt_money(d.tax25)

        # ------------------------------------------------------------------
        # Navigation / meta
        # ------------------------------------------------------------------
        fields[f"{p}:txtCurrentPage"] = "1"

        # ------------------------------------------------------------------
        # Global flags
        # ------------------------------------------------------------------
        fields["txtFinalFlag"] = "0"
        fields["txtEnroll"] = "N"
        fields["ebirOnlineSecret"] = ""
        fields["ebirOnlineConfirmUsername"] = ""
        fields["ebirOnlineUsername"] = ""
        fields["driveSelectTPExport"] = ""

        return fields
