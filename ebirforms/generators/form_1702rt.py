"""Generator for BIR Form 1702-RT v2018C (Annual Income Tax Return for Corporations - Regular Tax).

XML structure reverse-engineered from: extracted_hta/decoded/renamed/forms_BIR-Form1702RTv2018C.hta

Field prefix: frm1702RT

Key sections:
    Part I    (Pg1) - Background Information (items 1-13)
    Part II   (Pg1) - Tax Computation Summary (items 14-21)
    Part III  (Pg1) - Payment Details
    Part IV   (Pg2) - Income Statement and Tax Computation (items 27-59)
    Schedule 1 (Pg3) - Ordinary Allowable Itemized Deductions (skipped/zeroed)
    Schedule 2 (Pg3) - Special Allowable Deductions (skipped/zeroed)
    Schedule 3 (Pg4) - Net Operating Loss Carry-Over (NOLCO) (skipped/zeroed)
    Schedule 4 (Pg4) - Excess MCIT (skipped/zeroed)
    Schedule 5 (Pg4) - Related Party Transactions (skipped/zeroed)

Part IV income statement field map (main income computation):
    frm1702RT:txtPg2Pt4I27Sales               -> Gross Sales/Receipts/Revenues/Fees
    frm1702RT:txtPg2Pt4I28LessSales           -> Less: Sales Returns, Allowances & Discounts
    frm1702RT:txtPg2Pt4I29NetSales            -> Net Sales/Receipts/Revenues/Fees (27 - 28)
    frm1702RT:txtPg2Pt4I30LessCost            -> Less: Cost of Sales/Services
    frm1702RT:txtPg2Pt4I31GrossIncome         -> Gross Income from Operations (29 - 30)
    frm1702RT:txtPg2Pt4I32AddOtherTaxable     -> Add: Non-Operating & Other Taxable Income
    frm1702RT:txtPg2Pt4I33TotalGross          -> Total Gross Income (31 + 32)
    frm1702RT:txtPg2Pt4I34OrdinaryAllowable   -> Less: Ordinary Allowable Itemized Deductions
    frm1702RT:txtPg2Pt4I35SpecialAllowable    -> Less: Special Allowable Itemized Deductions
    frm1702RT:txtPg2Pt4I36Nolco               -> Less: Net Operating Loss Carry-Over (NOLCO)
    frm1702RT:txtPg2Pt4I37TotalItemized       -> Total Itemized Deductions (34+35+36)
    frm1702RT:txtPg2Pt4I38OptionalStandard    -> Optional Standard Deduction (OSD) (40% of Item 33)
    frm1702RT:txtPg2Pt4I39NetTaxable          -> Net Taxable Income (33 - 37 or 33 - 38)
    frm1702RT:Pg2Pt4I40IncomeTaxRate          -> Applicable Income Tax Rate (%)
    frm1702RT:txtPg2Pt4I41IncomeTaxDue        -> Income Tax Due (39 x 40)
    frm1702RT:txtPg2Pt4I42MinimumCorporate    -> Minimum Corporate Income Tax (MCIT) (2% of Item 33)
    frm1702RT:txtPg2Pt4I43TotalIncomeTax      -> Total Income Tax Due (higher of 41 and 42)
    frm1702RT:txtPg2Pt4I44ExcessCredits       -> Less: Excess MCIT from Previous 3 Years
    frm1702RT:txtPg2Pt4I45IncomeTaxPaymentUnderMCIT -> Less: Income Tax Under MCIT (from Sched 4)
    frm1702RT:txtPg2Pt4I46IncomeTaxUnderRegular     -> Less: Income Tax Payments Under Regular Tax
    frm1702RT:txtPg2Pt4I47ExcessMCIT                -> Excess MCIT Over Regular Tax (42 - 41, if positive)
    frm1702RT:txtPg2Pt4I48CreditableTaxWithheldFromPrevious -> Less: CWT from Previous Year
    frm1702RT:txtPg2Pt4I49CreditableTaxWithheldFor4thQuarter -> Less: CWT for 4th Quarter
    frm1702RT:txtPg2Pt4I50ForeignTaxCredits          -> Less: Foreign Tax Credits
    frm1702RT:txtPg2Pt4I51TaxPaidInReturn            -> Less: Tax Paid in Previously Filed Return
    frm1702RT:txtPg2Pt452SpecialTaxCredits           -> Less: Special Tax Credits
    frm1702RT:txtPg2Pt4I55TotalTaxCredits            -> Total Tax Credits (sum of 44-52)
    frm1702RT:txtPg2Pt4I56NetTax                     -> Net Tax Payable / (Overpayment) (43 - 55)
    frm1702RT:txtPg2Pt5I57SpecialAllowable           -> Add: Special Tax under Special Law
    frm1702RT:txtPg2Pt5I58AddSpecialTax              -> Add: Income Tax on Special Income
    frm1702RT:txtPg2Pt5I59TotalTax                   -> Total Tax (56 + 57 + 58)

Part II summary field map:
    frm1702RT:txtPg1Pt2I14IncomeTax          -> Total Income Tax Due (from Pt4I59 = Pt4I56 + Pt5)
    frm1702RT:txtPg1Pt2I15TotalTaxCredits    -> Less: Tax Credits/Payments
    frm1702RT:txtPg1Pt2I16NetTax             -> Net Tax Payable / (Overpayment) (14 - 15)
    frm1702RT:txtPg1Pt2I17Surcharge          -> Add: Surcharge
    frm1702RT:txtPg1Pt2I18Interest           -> Add: Interest
    frm1702RT:txtPg1Pt2I19Compromise         -> Add: Compromise Penalty
    frm1702RT:txtPg1Pt2I20TotalPenalties     -> Total Penalties (17 + 18 + 19)
    frm1702RT:txtPg1Pt2I21TotalAmount        -> Total Amount Still Due / (Overpayment) (16 + 20)
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo

# ATC codes for regular-rate corporations (Item 5 dropdown).
# The HTA uses a numeric value for the radio button; the rate is inferred from the tax computation.
ATC_REGULAR_25 = "IC010"  # Standard regular corporate tax (25%)
ATC_REGULAR_20 = "IC010"  # MSME rate (20% - same ATC, different rate in computation)

# Deduction method constants
DEDUCTION_ITEMIZED = "itemized"
DEDUCTION_OSD = "osd"  # 40% Optional Standard Deduction

# Tax rates
TAX_RATE_REGULAR = Decimal("25.00")  # Post-CREATE Act regular corporate rate
TAX_RATE_MSME = Decimal("20.00")  # MSME rate (net taxable income <= 5M, assets <= 100M)
TAX_RATE_OLD = Decimal("30.00")  # Pre-CREATE Act rate (retained for backward compat)

# MCIT rate (2% of total gross income)
MCIT_RATE = Decimal("2.00")

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
class IncomeStatementData:
    """Part IV income statement data for the annual return.

    This covers items 27-39 of the form (revenues through net taxable income).
    """

    gross_sales: Decimal  # Item 27: Gross sales/receipts/revenues/fees
    sales_returns: Decimal  # Item 28: Less: returns, allowances, discounts
    cost_of_sales: Decimal  # Item 30: Less: cost of sales/services
    non_operating_income: Decimal  # Item 32: Non-operating & other taxable income
    # Itemized deductions (used when deduction_method == DEDUCTION_ITEMIZED)
    ordinary_allowable_deductions: Decimal  # Item 34
    special_allowable_deductions: Decimal  # Item 35
    nolco: Decimal  # Item 36: Net operating loss carry-over
    # Tax rate
    tax_rate: Decimal  # Item 40: e.g., Decimal("25.00") for 25%

    @property
    def net_sales(self) -> Decimal:
        """Item 29: Gross sales less returns/allowances."""
        return _round2(self.gross_sales - self.sales_returns)

    @property
    def gross_income_from_operations(self) -> Decimal:
        """Item 31: Net sales less cost of sales."""
        return _round2(self.net_sales - self.cost_of_sales)

    @property
    def total_gross_income(self) -> Decimal:
        """Item 33: Gross income from operations plus non-operating income."""
        return _round2(self.gross_income_from_operations + self.non_operating_income)

    def total_itemized_deductions(self) -> Decimal:
        """Item 37: Sum of ordinary + special + NOLCO."""
        return _round2(self.ordinary_allowable_deductions + self.special_allowable_deductions + self.nolco)

    def osd_amount(self) -> Decimal:
        """Item 38: 40% of total gross income."""
        return _round2(self.total_gross_income * _OSD_RATE)

    def net_taxable_income(self, use_osd: bool) -> Decimal:
        """Item 39: Total gross income less applicable deductions (floored at zero)."""
        deductions = self.osd_amount() if use_osd else self.total_itemized_deductions()
        result = _round2(self.total_gross_income - deductions)
        return max(result, _ZERO)

    def income_tax_due(self, use_osd: bool) -> Decimal:
        """Item 41: Net taxable income x tax rate."""
        nti = self.net_taxable_income(use_osd)
        if nti <= _ZERO:
            return _ZERO
        return _round2(nti * self.tax_rate / Decimal("100"))

    def mcit(self) -> Decimal:
        """Item 42: 2% of total gross income (floored at zero)."""
        tgi = self.total_gross_income
        if tgi <= _ZERO:
            return _ZERO
        return _round2(tgi * MCIT_RATE / Decimal("100"))

    def total_income_tax_due(self, use_osd: bool) -> Decimal:
        """Item 43: Higher of regular income tax due and MCIT."""
        return max(self.income_tax_due(use_osd), self.mcit())


@dataclass(frozen=True)
class TaxCreditsData:
    """Tax credits and quarterly payments (items 44-52 in Part IV)."""

    excess_mcit_prior_years: Decimal  # Item 44: Excess MCIT from previous 3 years
    income_tax_payment_mcit: Decimal  # Item 45: IT payments under MCIT
    income_tax_payment_regular: Decimal  # Item 46: IT payments under regular rate
    creditable_wt_prior_year: Decimal  # Item 48: CWT from prior year
    creditable_wt_4th_quarter: Decimal  # Item 49: CWT for 4th quarter
    foreign_tax_credits: Decimal  # Item 50
    tax_paid_previously_filed: Decimal  # Item 51: Amended returns only
    special_tax_credits: Decimal  # Item 52

    @property
    def total(self) -> Decimal:
        """Item 55: Total of all tax credits."""
        return _round2(
            self.excess_mcit_prior_years
            + self.income_tax_payment_mcit
            + self.income_tax_payment_regular
            + self.creditable_wt_prior_year
            + self.creditable_wt_4th_quarter
            + self.foreign_tax_credits
            + self.tax_paid_previously_filed
            + self.special_tax_credits
        )


@dataclass(frozen=True)
class Form1702RTData:
    """All data needed to generate BIR Form 1702-RT v2018C."""

    # Period
    fiscal_year_end_month: int  # 1-12
    fiscal_year_end_year: int  # 4-digit year, e.g. 2024
    is_calendar_year: bool

    # Return type
    is_amended: bool
    is_short_period: bool  # Item 4: Short period return
    deduction_method: str  # DEDUCTION_ITEMIZED or DEDUCTION_OSD

    # Income statement
    income_statement: IncomeStatementData

    # Tax credits
    tax_credits: TaxCreditsData

    # Penalties (normally zero unless filing late)
    surcharge: Decimal = _ZERO  # Item 17
    interest: Decimal = _ZERO  # Item 18
    compromise: Decimal = _ZERO  # Item 19

    # Special tax additions (Part V, most corps leave these at zero)
    special_tax_special_law: Decimal = _ZERO  # Item 57
    special_income_tax: Decimal = _ZERO  # Item 58

    # Overpayment disposition (used when there is an overpayment)
    # "refunded", "issued", "carried" - leave blank for none
    overpayment_disposition: str = ""

    # Page count / sheets
    pages_filled: str = ""

    @property
    def _use_osd(self) -> bool:
        return self.deduction_method == DEDUCTION_OSD

    # ------------------------------------------------------------------
    # Part IV derived values
    # ------------------------------------------------------------------

    @property
    def pt4_i43_total_income_tax(self) -> Decimal:
        """Item 43: Higher of regular tax and MCIT."""
        return self.income_statement.total_income_tax_due(self._use_osd)

    @property
    def pt4_i47_excess_mcit(self) -> Decimal:
        """Item 47: Excess MCIT over regular tax (positive when MCIT > regular)."""
        mcit = self.income_statement.mcit()
        regular = self.income_statement.income_tax_due(self._use_osd)
        excess = _round2(mcit - regular)
        return max(excess, _ZERO)

    @property
    def pt4_i56_net_tax(self) -> Decimal:
        """Item 56: Net tax payable / (overpayment) = total income tax - total credits."""
        return _round2(self.pt4_i43_total_income_tax - self.tax_credits.total)

    @property
    def pt5_i59_total_tax(self) -> Decimal:
        """Item 59: Total tax = item56 + special tax additions."""
        return _round2(self.pt4_i56_net_tax + self.special_tax_special_law + self.special_income_tax)

    # ------------------------------------------------------------------
    # Part II summary (page 1)
    # ------------------------------------------------------------------

    @property
    def pt2_i14_income_tax(self) -> Decimal:
        """Item 14: Total income tax due (flows from Pt4 item 43)."""
        return self.pt4_i43_total_income_tax

    @property
    def pt2_i15_total_tax_credits(self) -> Decimal:
        """Item 15: Total tax credits/payments (flows from Pt4 item 55)."""
        return self.tax_credits.total

    @property
    def pt2_i16_net_tax(self) -> Decimal:
        """Item 16: Net tax payable / (overpayment) (14 - 15)."""
        return _round2(self.pt2_i14_income_tax - self.pt2_i15_total_tax_credits)

    @property
    def pt2_i20_total_penalties(self) -> Decimal:
        """Item 20: Total penalties (17 + 18 + 19)."""
        return _round2(self.surcharge + self.interest + self.compromise)

    @property
    def pt2_i21_total_amount(self) -> Decimal:
        """Item 21: Total amount still due / (overpayment) (16 + 20).

        When there is an overpayment but also penalties, only show penalties.
        """
        if self.pt2_i16_net_tax < _ZERO and self.pt2_i20_total_penalties > _ZERO:
            return self.pt2_i20_total_penalties
        return _round2(self.pt2_i16_net_tax + self.pt2_i20_total_penalties)


class Form1702RTGenerator(FormGenerator):
    """Generates BIR Form 1702-RT v2018C."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form1702RTData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "1702RTv2018C"

    @property
    def form_prefix(self) -> str:
        # The HTA uses 'frm1702RT' as the field prefix (without the 'v2018C' suffix).
        return "frm1702RT"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data
        ist = d.income_statement
        tc = d.tax_credits

        fields: dict[str, str] = {}

        # ------------------------------------------------------------------
        # Part I - Period and return type
        # ------------------------------------------------------------------
        fields[f"{p}:rdoPg1I1Calendar"] = "true" if d.is_calendar_year else "false"
        fields[f"{p}:rdoPg1I1Fiscal"] = "false" if d.is_calendar_year else "true"

        # Fiscal year-end month and year (4-digit)
        fields[f"{p}:txtPg1I2Month"] = f"{d.fiscal_year_end_month:02d}"
        fields[f"{p}:txtPg1I2Year"] = str(d.fiscal_year_end_year)

        # Amended return
        fields[f"{p}:rdoPg1I3AmmendYes"] = "true" if d.is_amended else "false"
        fields[f"{p}:rdoPg1I3AmmendNo"] = "false" if d.is_amended else "true"

        # Short period
        fields[f"{p}:rdoPg1I4ShortPeriodYes"] = "true" if d.is_short_period else "false"
        fields[f"{p}:rdoPg1I4ShortPeriodNo"] = "false" if d.is_short_period else "true"

        # ATC selection: rdoPg1I5Atc = standard "IC010" radio
        fields[f"{p}:rdoPg1I5Atc"] = "true"
        fields[f"{p}:rdoPg1I5AtcOther"] = "false"
        fields[f"{p}:drpPg1I5AtcOther"] = ""

        # ------------------------------------------------------------------
        # Part I background information (taxpayer)
        # ------------------------------------------------------------------
        tin1, tin2, tin3, branch = self._taxpayer.tin_parts
        fields[f"{p}:txtPg1Pt1I6TIN1"] = tin1
        fields[f"{p}:txtPg1Pt1I6TIN2"] = tin2
        fields[f"{p}:txtPg1Pt1I6TIN3"] = tin3
        fields[f"{p}:txtPg1Pt1I6TIN4"] = branch
        fields[f"{p}:txtRDO"] = self._taxpayer.rdo_code

        # Registered name split across three fields (each holding a portion of the name)
        name = self._taxpayer.name
        fields[f"{p}:txtPg1Pt1I8Name1"] = name
        fields[f"{p}:txtPg1Pt1I8Name2"] = ""
        fields[f"{p}:txtPg1Pt1I8Name3"] = ""

        # Address split across three fields
        address = self._taxpayer.address
        fields[f"{p}:txtPg1Pt1I9Address1"] = address
        fields[f"{p}:txtPg1Pt1I9Address2"] = ""
        fields[f"{p}:txtPg1Pt1I9Address3"] = ""

        fields[f"{p}:txtZIP"] = self._taxpayer.zip_code
        fields[f"{p}:txtPg1Pt1I10"] = self._taxpayer.trade_name
        fields[f"{p}:txtPg1Pt1I11Contact"] = self._taxpayer.telephone
        fields[f"{p}:txtPg1Pt1I12Email"] = self._taxpayer.email

        # Deduction method: itemized or OSD
        fields[f"{p}:rdoPg1Pt1I13ItemizedDeduction"] = "true" if d.deduction_method == DEDUCTION_ITEMIZED else "false"
        fields[f"{p}:rdoPg1Pt1I13OptionalStandard"] = "true" if d.deduction_method == DEDUCTION_OSD else "false"

        # ------------------------------------------------------------------
        # Part II - Tax computation summary (page 1)
        # ------------------------------------------------------------------
        fields[f"{p}:txtPg1Pt2I14IncomeTax"] = _fmt_money(d.pt2_i14_income_tax)
        fields[f"{p}:txtPg1Pt2I15TotalTaxCredits"] = _fmt_money(d.pt2_i15_total_tax_credits)
        fields[f"{p}:txtPg1Pt2I16NetTax"] = _fmt_money(d.pt2_i16_net_tax)
        fields[f"{p}:txtPg1Pt2I17Surcharge"] = _fmt_money(d.surcharge)
        fields[f"{p}:txtPg1Pt2I18Interest"] = _fmt_money(d.interest)
        fields[f"{p}:txtPg1Pt2I19Compromise"] = _fmt_money(d.compromise)
        fields[f"{p}:txtPg1Pt2I20TotalPenalties"] = _fmt_money(d.pt2_i20_total_penalties)
        fields[f"{p}:txtPg1Pt2I21TotalAmount"] = _fmt_money(d.pt2_i21_total_amount)

        # Overpayment disposition (radio buttons - all false unless specified)
        fields[f"{p}:rdoPg1Pt2I21OverpaymentRefunded"] = "true" if d.overpayment_disposition == "refunded" else "false"
        fields[f"{p}:rdoPg1Pt2I21OverpaymentIssued"] = "true" if d.overpayment_disposition == "issued" else "false"
        fields[f"{p}:rdoPg1Pt2I21OverpaymentCarried"] = "true" if d.overpayment_disposition == "carried" else "false"

        # Signatory fields (left blank for generator; user fills on print)
        fields[f"{p}:txtSignaturePresident"] = ""
        fields[f"{p}:txtSignatureTreasurer"] = ""
        fields[f"{p}:txtPg1Pt2PagesFilled"] = d.pages_filled
        fields[f"{p}:txtPg1Pt2Signatory1"] = ""
        fields[f"{p}:txtPg1Pt2SignatoryTin1"] = ""
        fields[f"{p}:txtPg1Pt2Signatory2"] = ""
        fields[f"{p}:txtPg1Pt2SignatoryTin2"] = ""

        # ------------------------------------------------------------------
        # Page 2 header (TIN / name repeater)
        # ------------------------------------------------------------------
        fields[f"{p}:txtPg2TIN1"] = tin1
        fields[f"{p}:txtPg2TIN2"] = tin2
        fields[f"{p}:txtPg2TIN3"] = tin3
        fields[f"{p}:txtPg2TIN4"] = branch
        fields[f"{p}:txtPg2RegisteredName"] = name

        # ------------------------------------------------------------------
        # Part IV - Income Statement and Tax Computation (page 2)
        # ------------------------------------------------------------------
        fields[f"{p}:txtPg2Pt4I27Sales"] = _fmt_money(ist.gross_sales)
        fields[f"{p}:txtPg2Pt4I28LessSales"] = _fmt_money(ist.sales_returns)
        fields[f"{p}:txtPg2Pt4I29NetSales"] = _fmt_money(ist.net_sales)
        fields[f"{p}:txtPg2Pt4I30LessCost"] = _fmt_money(ist.cost_of_sales)
        fields[f"{p}:txtPg2Pt4I31GrossIncome"] = _fmt_money(ist.gross_income_from_operations)
        fields[f"{p}:txtPg2Pt4I32AddOtherTaxable"] = _fmt_money(ist.non_operating_income)
        fields[f"{p}:txtPg2Pt4I33TotalGross"] = _fmt_money(ist.total_gross_income)

        # Itemized deductions (items 34-37)
        fields[f"{p}:txtPg2Pt4I34OrdinaryAllowable"] = _fmt_money(ist.ordinary_allowable_deductions)
        fields[f"{p}:txtPg2Pt4I35SpecialAllowable"] = _fmt_money(ist.special_allowable_deductions)
        fields[f"{p}:txtPg2Pt4I36Nolco"] = _fmt_money(ist.nolco)
        fields[f"{p}:txtPg2Pt4I37TotalItemized"] = _fmt_money(ist.total_itemized_deductions())

        # OSD (item 38) - populated whether or not OSD is used (for display)
        fields[f"{p}:txtPg2Pt4I38OptionalStandard"] = _fmt_money(ist.osd_amount())

        # Net taxable income (item 39)
        fields[f"{p}:txtPg2Pt4I39NetTaxable"] = _fmt_money(ist.net_taxable_income(d._use_osd))

        # Tax rate and tax due (items 40-43)
        fields[f"{p}:Pg2Pt4I40IncomeTaxRate"] = _fmt_rate(ist.tax_rate)
        fields[f"{p}:txtPg2Pt4I41IncomeTaxDue"] = _fmt_money(ist.income_tax_due(d._use_osd))
        fields[f"{p}:txtPg2Pt4I42MinimumCorporate"] = _fmt_money(ist.mcit())
        fields[f"{p}:txtPg2Pt4I43TotalIncomeTax"] = _fmt_money(d.pt4_i43_total_income_tax)

        # Excess MCIT (item 47)
        fields[f"{p}:txtPg2Pt4I47ExcessMCIT"] = _fmt_money(d.pt4_i47_excess_mcit)

        # Tax credits (items 44-52, 55)
        fields[f"{p}:txtPg2Pt4I44ExcessCredits"] = _fmt_money(tc.excess_mcit_prior_years)
        fields[f"{p}:txtPg2Pt4I45IncomeTaxPaymentUnderMCIT"] = _fmt_money(tc.income_tax_payment_mcit)
        fields[f"{p}:txtPg2Pt4I46IncomeTaxUnderRegular"] = _fmt_money(tc.income_tax_payment_regular)
        fields[f"{p}:txtPg2Pt4I48CreditableTaxWithheldFromPrevious"] = _fmt_money(tc.creditable_wt_prior_year)
        fields[f"{p}:txtPg2Pt4I49CreditableTaxWithheldFor4thQuarter"] = _fmt_money(tc.creditable_wt_4th_quarter)
        fields[f"{p}:txtPg2Pt4I50ForeignTaxCredits"] = _fmt_money(tc.foreign_tax_credits)
        fields[f"{p}:txtPg2Pt4I51TaxPaidInReturn"] = _fmt_money(tc.tax_paid_previously_filed)
        fields[f"{p}:txtPg2Pt452SpecialTaxCredits"] = _fmt_money(tc.special_tax_credits)
        # Items 53-54 are "other credits" rows (free-form) - zeroed
        fields[f"{p}:txtPg2Pt4I53C1"] = ""
        fields[f"{p}:txtPg2Pt4I53C2"] = "0.00"
        fields[f"{p}:txtPg2Pt4I54C1"] = ""
        fields[f"{p}:txtPg2Pt4I54C2"] = "0.00"
        fields[f"{p}:txtPg2Pt4I55TotalTaxCredits"] = _fmt_money(tc.total)
        fields[f"{p}:txtPg2Pt4I56NetTax"] = _fmt_money(d.pt4_i56_net_tax)

        # Part V additions (items 57-59) - most corps leave these at zero
        fields[f"{p}:txtPg2Pt5I57SpecialAllowable"] = _fmt_money(d.special_tax_special_law)
        fields[f"{p}:txtPg2Pt5I58AddSpecialTax"] = _fmt_money(d.special_income_tax)
        fields[f"{p}:txtPg2Pt5I59TotalTax"] = _fmt_money(d.pt5_i59_total_tax)

        # ------------------------------------------------------------------
        # Page 3 header (TIN / name repeater)
        # ------------------------------------------------------------------
        fields[f"{p}:txtPg3TIN1"] = tin1
        fields[f"{p}:txtPg3TIN2"] = tin2
        fields[f"{p}:txtPg3TIN3"] = tin3
        fields[f"{p}:txtPg3TIN4"] = branch
        fields[f"{p}:txtPg3RegisteredName"] = name

        # ------------------------------------------------------------------
        # Schedule 1 - Ordinary Allowable Itemized Deductions (page 3)
        # These are sub-line-item breakdowns; zero them all out since we only
        # use the aggregate (I34) from the income statement.
        # ------------------------------------------------------------------
        sched1_items = [
            "I1Amortization",
            "I2BadDebts",
            "I3CharitableContributions",
            "I4Depletion",
            "I5Depreciation",
            "I6Entertainment",
            "I7FringeBenefits",
            "I8Interest",
            "I9Losses",
            "I10PensionTrust",
            "I11Rental",
            "I12Research",
            "I13Salaries",
            "I14Contributions",
            "I15TaxesandLicenses",
            "I16TransportationandTravel",
            "I17aJanitorial",
            "I17bProfessionalFees",
            "I17cSecurityServices",
            "I17dC1",
            "I17dC2",
            "I17eC1",
            "I17eC2",
            "I17fC1",
            "I17fC2",
            "I17gC1",
            "I17gC2",
            "I17hC1",
            "I17hC2",
            "I17iC1",
            "I17iC2",
            "I18TotalOrdinaryAllowable",
        ]
        for item in sched1_items:
            fields[f"{p}:txtPg3Sc1{item}"] = "0.00"

        # ------------------------------------------------------------------
        # Schedule 2 - Special Allowable Deductions (page 3) - zeroed
        # ------------------------------------------------------------------
        for col in ("C1", "C2", "C3"):
            for row in ("I1", "I2", "I3", "I4"):
                fields[f"{p}:txtPg3Sc2{row}{col}"] = "0.00"
        fields[f"{p}:txtPg3Sc2I5TotalSpecialAllowable"] = "0.00"

        # ------------------------------------------------------------------
        # Page 4 header (TIN / name repeater)
        # ------------------------------------------------------------------
        fields[f"{p}:txtPg4TIN1"] = tin1
        fields[f"{p}:txtPg4TIN2"] = tin2
        fields[f"{p}:txtPg4TIN3"] = tin3
        fields[f"{p}:txtPg4TIN4"] = branch
        fields[f"{p}:txtPg4RegisteredName"] = name

        # ------------------------------------------------------------------
        # Schedule 3 - NOLCO (page 4) - zeroed
        # ------------------------------------------------------------------
        fields[f"{p}:txtPg4Sc3I1GrossIncome"] = "0.00"
        fields[f"{p}:txtPg4Sc3I2TotalDeductions"] = "0.00"
        fields[f"{p}:txtPg4Sc3I3NetOperatingLoss"] = "0.00"
        for row in ("I4", "I5", "I6", "I7"):
            for col in ("C1", "C2", "C3", "C4", "C5", "C6"):
                fields[f"{p}:txtPg4Sc3A{row}{col}"] = "0.00"
        fields[f"{p}:txtPg4Sc4I8TotalNOLCO"] = "0.00"

        # ------------------------------------------------------------------
        # Schedule 4 - Excess MCIT (page 4) - zeroed
        # ------------------------------------------------------------------
        for row in ("I1", "I2", "I3"):
            for col in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"):
                fields[f"{p}:txtPg4Sc4{row}{col}"] = "0.00"
        fields[f"{p}:txtPg4Sc4I4TotalExcessMCIT"] = "0.00"

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
        fields["ebirOnlinePassword"] = ""

        return fields
