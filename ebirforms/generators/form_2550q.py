"""Generator for BIR Form 2550-Q v2024 (Quarterly Value-Added Tax Return).

Field prefix: frm2550qv2024 (all lowercase)

Key field mappings (from HTA source / field map JSON):
    frm2550qv2024:calendarNo1          -> Calendar year radio (true/false)
    frm2550qv2024:fiscalNo1            -> Fiscal year radio (true/false)
    frm2550qv2024:selectedMonthNo2     -> Year-end month (MM, e.g. "12")
    frm2550qv2024:txtYearNo2           -> Tax year (YYYY)
    frm2550qv2024:OptQuarter1..4       -> Quarter selection radio (true/false)
    frm2550qv2024:RtnPeriodFromNo4     -> Return period start (MM/DD/YYYY)
    frm2550qv2024:RtnPeriodToNo4       -> Return period end (MM/DD/YYYY)
    frm2550qv2024:amendedReturnYesNo5  -> Amended return Yes radio
    frm2550qv2024:amendedReturnNo5     -> Amended return No radio
    frm2550qv2024:OptShortPrd1/2       -> Short period radios

    Taxpayer info:
    frm2550qv2024:txtTIN1/2/3          -> TIN parts
    frm2550qv2024:branchCode           -> Branch code
    frm2550qv2024:txtRDOCode           -> RDO code
    frm2550qv2024:taxpayerName         -> Taxpayer name (URL-encoded)
    frm2550qv2024:taxpayerAddress      -> Address (URL-encoded)
    frm2550qv2024:taxpayerZip          -> ZIP code
    frm2550qv2024:taxpayerContactNumber -> Telephone
    frm2550qv2024:taxpayerEmailAddress -> Email
    frm2550qv2024:taxPayerClassification1..4 -> Taxpayer classification radios

    Output VAT (Page 2, Part I):
    frm2550qv2024:vatableSales         -> 31A: Vatable sales/receipts
    frm2550qv2024:outputVatSales       -> 31B: Output VAT on vatable sales (= 31A * 12%)
    frm2550qv2024:zeroRatedSales       -> 32: Zero-rated sales
    frm2550qv2024:exemptSales          -> 33: Exempt sales
    frm2550qv2024:totalSales           -> 34: Total sales (31A + 32 + 33)
    frm2550qv2024:outputTaxDue         -> 35: Output tax due (= 31A * 12%)
    frm2550qv2024:lessOutputVat        -> 36: Less: deductions from output VAT
    frm2550qv2024:addOutputVat         -> 36A: Add: other output VAT
    frm2550qv2024:totalAdjOutput       -> 37: Total adjusted output VAT (35 - 36 + 36A)

    Input VAT carried forward:
    frm2550qv2024:inputTaxCarried      -> 38: Input tax carried over from previous quarter
    frm2550qv2024:inputTaxDeferred     -> 39: Deferred input tax from previous period
    frm2550qv2024:transitionalInputTax -> 40: Transitional input tax
    frm2550qv2024:presumptiveInputTax  -> 41: Presumptive input tax
    frm2550qv2024:addSpecifyNo42       -> 42 description (other prior period input tax)
    frm2550qv2024:otherSpecify42       -> 42 amount
    frm2550qv2024:total43              -> 43: Total input tax carried forward (38+39+40+41+42)

    Current period purchases:
    frm2550qv2024:domesticPurchase     -> 44A: Domestic purchases (goods)
    frm2550qv2024:domesticInputTax     -> 44B: Input tax from domestic purchases
    frm2550qv2024:servicesPurchase     -> 45A: Services from residents
    frm2550qv2024:serviceInputTax      -> 45B: Input tax on services from residents
    frm2550qv2024:importPurchase       -> 46A: Importation of goods / services by non-residents
    frm2550qv2024:importInputTax       -> 46B: Input tax on imports
    frm2550qv2024:addSpecifyNo47       -> 47 description
    frm2550qv2024:otherSpecify47       -> 47 amount (purchase)
    frm2550qv2024:domesticPurchaseNoTax -> 48: Domestic purchases - no input tax
    frm2550qv2024:vatExemptImports     -> 49: VAT-exempt imports
    frm2550qv2024:totalCurPurchase     -> 50A: Total current purchases
    frm2550qv2024:totalCurInputTax     -> 50B: Total current input tax (44B+45B+46B+47B)
    frm2550qv2024:totalAvailInputTax   -> 51: Total available input tax (43 + 50B)

    Input VAT deductions:
    frm2550qv2024:importCapitalInputTax -> 52: Input tax on capital goods (deferred)
    frm2550qv2024:inputTaxAttr         -> 53: Input tax attributable to exempt sales
    frm2550qv2024:vatRefund            -> 54: VAT refund / TCC applied
    frm2550qv2024:inputVatUnpaid       -> 55: Input VAT on unpaid purchases
    frm2550qv2024:addSpecifyNo56       -> 56 description
    frm2550qv2024:otherSpecify56       -> 56 amount
    frm2550qv2024:totalDeductions      -> 57: Total deductions
    frm2550qv2024:addInputVat          -> 58: Add: other adjustments to input VAT
    frm2550qv2024:adjDeductions        -> 59: Adjusted deductions (57 + 58)
    frm2550qv2024:totalAllowInputTax   -> 60: Total allowable input tax (51 - 59)
    frm2550qv2024:netVatPayable        -> 61: Net VAT payable (37 - 60)

    Tax credits (Page 1, Part II):
    frm2550qv2024:excessInputTax       -> 14/15: Excess input tax (= net VAT payable)
    frm2550qv2024:creditableVat        -> 16: Creditable VAT withheld (from Sched 3)
    frm2550qv2024:advVatPayment        -> 17: Advance VAT payment (from Sched 4)
    frm2550qv2024:vatPaidReturn        -> 18: VAT paid on previous return (amended only)
    frm2550qv2024:addSpecifyNo19       -> 19 description
    frm2550qv2024:otherCreditsNo19     -> 19 amount
    frm2550qv2024:totalTaxCredits      -> 20: Total tax credits (16+17+18+19)
    frm2550qv2024:excessCredits        -> 21: Net VAT payable after credits (15 - 20)
    frm2550qv2024:surcharge            -> 22: Surcharge
    frm2550qv2024:interest             -> 23: Interest
    frm2550qv2024:compromise           -> 24: Compromise
    frm2550qv2024:penalties            -> 25: Total penalties (22+23+24)
    frm2550qv2024:totalPayable         -> 26: Total amount payable (21 + 25, floor 0)

    Page 2 header:
    frm2550qv2024:txtPg2TIN1/2/3       -> Page 2 TIN repeat
    frm2550qv2024:txtPg2BranchCode     -> Page 2 branch code repeat
    frm2550qv2024:Pg2TaxPayer          -> Page 2 taxpayer name repeat
"""

import calendar
from dataclasses import dataclass
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo

# VAT rate per TRAIN law
_VAT_RATE = Decimal("0.12")

# Quarter -> (start_month, end_month) for calendar-year taxpayers
_CALENDAR_QUARTERS: dict[int, tuple[int, int]] = {
    1: (1, 3),
    2: (4, 6),
    3: (7, 9),
    4: (10, 12),
}


def _fmt_money(amount: Decimal) -> str:
    """Format Decimal as eBIRForms money string: '20,000.00'."""
    return f"{amount:,.2f}"


def _last_day(month: int, year: int) -> int:
    return calendar.monthrange(year, month)[1]


def _period_from(quarter: int, year: int) -> str:
    """Return period start date as M/DD/YYYY (no leading zero on month)."""
    start_month, _ = _CALENDAR_QUARTERS[quarter]
    return f"{start_month}/01/{year}"


def _period_to(quarter: int, year: int) -> str:
    """Return period end date as M/DD/YYYY."""
    _, end_month = _CALENDAR_QUARTERS[quarter]
    last = _last_day(end_month, year)
    return f"{end_month}/{last}/{year}"


@dataclass(frozen=True)
class Form2550QData:
    """Data for BIR Form 2550-Q v2024 (Quarterly VAT Return).

    All monetary fields are Decimal.  The caller provides the raw figures;
    computed totals are derived as properties to avoid mutation.

    Tax period is expressed as a calendar year + quarter (1-4).
    The form also supports fiscal-year filers, but this generator targets
    the standard calendar-year case (year-end month = December).
    """

    year: int
    quarter: int  # 1-4

    is_amended: bool

    # Output VAT inputs (Part I, page 2)
    vatable_sales: Decimal  # 31A
    zero_rated_sales: Decimal  # 32
    exempt_sales: Decimal  # 33
    less_output_vat: Decimal  # 36 - deductions from output VAT
    add_output_vat: Decimal  # 36A - other output VAT to add

    # Input VAT from prior periods (items 38-42)
    input_tax_carried: Decimal  # 38: carried from prior quarter
    input_tax_deferred: Decimal  # 39: deferred from prior period
    transitional_input_tax: Decimal  # 40
    presumptive_input_tax: Decimal  # 41
    other_prior_input_tax: Decimal  # 42 amount (miscellaneous)
    other_prior_input_tax_label: str  # 42 description

    # Current period purchases (items 44-49)
    domestic_purchase: Decimal  # 44A
    domestic_input_tax: Decimal  # 44B
    services_purchase: Decimal  # 45A
    service_input_tax: Decimal  # 45B
    import_purchase: Decimal  # 46A
    import_input_tax: Decimal  # 46B
    other_purchase: Decimal  # 47A
    other_purchase_label: str  # 47 description
    other_purchase_input_tax: Decimal  # 47B
    domestic_purchase_no_tax: Decimal  # 48
    vat_exempt_imports: Decimal  # 49

    # Input VAT deductions (items 52-56)
    import_capital_input_tax: Decimal  # 52
    input_tax_attr: Decimal  # 53 (attributed to exempt sales)
    vat_refund: Decimal  # 54
    input_vat_unpaid: Decimal  # 55
    other_deduction: Decimal  # 56 amount
    other_deduction_label: str  # 56 description
    add_input_vat: Decimal  # 58: other adjustments

    # Tax credits (Part II, page 1: items 16-19)
    creditable_vat: Decimal  # 16: creditable VAT withheld
    adv_vat_payment: Decimal  # 17: advance VAT payment
    vat_paid_return: Decimal  # 18: VAT paid on previous return (amended only)
    other_credits: Decimal  # 19 amount
    other_credits_label: str  # 19 description

    # Penalties (items 22-24)
    surcharge: Decimal
    interest: Decimal
    compromise: Decimal

    # Taxpayer classification (1=individual, 2=estate/trust, 3=corporation, 4=partnership)
    taxpayer_classification: int = 1

    # -------------------------------------------------------------------------
    # Derived properties
    # -------------------------------------------------------------------------

    @property
    def output_vat_sales(self) -> Decimal:
        """31B: Output VAT on vatable sales (31A * 12%)."""
        return (self.vatable_sales * _VAT_RATE).quantize(Decimal("0.01"))

    @property
    def total_sales(self) -> Decimal:
        """34: Total sales (31A + 32 + 33)."""
        return self.vatable_sales + self.zero_rated_sales + self.exempt_sales

    @property
    def output_tax_due(self) -> Decimal:
        """35: Output tax due (same as 31B for the basic case)."""
        return self.output_vat_sales

    @property
    def total_adj_output(self) -> Decimal:
        """37: Total adjusted output VAT (35 - 36 + 36A)."""
        return self.output_tax_due - self.less_output_vat + self.add_output_vat

    @property
    def total_prior_input(self) -> Decimal:
        """43: Total input tax from prior periods (38+39+40+41+42)."""
        return (
            self.input_tax_carried
            + self.input_tax_deferred
            + self.transitional_input_tax
            + self.presumptive_input_tax
            + self.other_prior_input_tax
        )

    @property
    def total_cur_purchase(self) -> Decimal:
        """50A: Total current purchases."""
        return (
            self.domestic_purchase
            + self.services_purchase
            + self.import_purchase
            + self.other_purchase
            + self.domestic_purchase_no_tax
            + self.vat_exempt_imports
        )

    @property
    def total_cur_input_tax(self) -> Decimal:
        """50B: Total current input tax (44B+45B+46B+47B)."""
        return self.domestic_input_tax + self.service_input_tax + self.import_input_tax + self.other_purchase_input_tax

    @property
    def total_avail_input_tax(self) -> Decimal:
        """51: Total available input tax (43 + 50B)."""
        return self.total_prior_input + self.total_cur_input_tax

    @property
    def total_deductions(self) -> Decimal:
        """57: Total deductions (52+53+54+55+56)."""
        return (
            self.import_capital_input_tax
            + self.input_tax_attr
            + self.vat_refund
            + self.input_vat_unpaid
            + self.other_deduction
        )

    @property
    def adj_deductions(self) -> Decimal:
        """59: Adjusted deductions (57 + 58)."""
        return self.total_deductions + self.add_input_vat

    @property
    def total_allow_input_tax(self) -> Decimal:
        """60: Total allowable input tax (51 - 59)."""
        return self.total_avail_input_tax - self.adj_deductions

    @property
    def net_vat_payable(self) -> Decimal:
        """61: Net VAT payable (37 - 60)."""
        return self.total_adj_output - self.total_allow_input_tax

    @property
    def total_tax_credits(self) -> Decimal:
        """20: Total tax credits (16+17+18+19)."""
        return self.creditable_vat + self.adv_vat_payment + self.vat_paid_return + self.other_credits

    @property
    def excess_credits(self) -> Decimal:
        """21: Net VAT payable after credits (net_vat_payable - total_tax_credits)."""
        return self.net_vat_payable - self.total_tax_credits

    @property
    def penalties(self) -> Decimal:
        """25: Total penalties (22+23+24)."""
        return self.surcharge + self.interest + self.compromise

    @property
    def total_payable(self) -> Decimal:
        """26: Total amount payable (21 + 25, floor 0 when 21 is negative)."""
        if self.excess_credits < Decimal("0") and self.penalties > Decimal("0"):
            return self.penalties
        return max(self.excess_credits + self.penalties, Decimal("0"))

    @property
    def period_from(self) -> str:
        """Return period start date string (M/DD/YYYY)."""
        return _period_from(self.quarter, self.year)

    @property
    def period_to(self) -> str:
        """Return period end date string (M/DD/YYYY)."""
        return _period_to(self.quarter, self.year)


class Form2550QGenerator(FormGenerator):
    """Generates BIR Form 2550-Q v2024 (Quarterly Value-Added Tax Return)."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form2550QData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "2550Qv2024"

    @property
    def form_prefix(self) -> str:
        return "frm2550qv2024"

    def _taxpayer_fields(self) -> dict[str, str]:
        """Override: 2550Q uses different field names from the base class."""
        p = self.form_prefix
        tin1, tin2, tin3, branch = self._taxpayer.tin_parts
        return {
            f"{p}:txtTIN1": tin1,
            f"{p}:txtTIN2": tin2,
            f"{p}:txtTIN3": tin3,
            f"{p}:branchCode": branch,
            f"{p}:txtRDOCode": self._taxpayer.rdo_code,
            f"{p}:taxpayerName": self._taxpayer.name,
            f"{p}:taxpayerAddress": self._taxpayer.address,
            f"{p}:taxpayerZip": self._taxpayer.zip_code,
            f"{p}:taxpayerContactNumber": self._taxpayer.telephone,
            f"{p}:taxpayerEmailAddress": self._taxpayer.email,
            "txtEmail": self._taxpayer.email,
        }

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields: dict[str, str] = {}

        # --- Year type (calendar vs fiscal) ---
        fields[f"{p}:calendarNo1"] = "true"
        fields[f"{p}:fiscalNo1"] = "false"

        # --- Period (item 2) ---
        fields[f"{p}:selectedMonthNo2"] = "12"  # December = calendar year-end
        fields[f"{p}:txtYearNo2"] = str(d.year)

        # --- Quarter (item 3) ---
        for q in range(1, 5):
            fields[f"{p}:OptQuarter{q}"] = "true" if q == d.quarter else "false"

        # --- Return period dates (item 4) ---
        fields[f"{p}:RtnPeriodFromNo4"] = d.period_from
        fields[f"{p}:RtnPeriodToNo4"] = d.period_to

        # --- Amended return (item 5) ---
        fields[f"{p}:amendedReturnYesNo5"] = "true" if d.is_amended else "false"
        fields[f"{p}:amendedReturnNo5"] = "false" if d.is_amended else "true"

        # --- Short period (not applicable for standard filers) ---
        fields[f"{p}:OptShortPrd1"] = "false"
        fields[f"{p}:OptShortPrd2"] = "true"

        # --- Taxpayer info ---
        fields.update(self._taxpayer_fields())

        # --- Taxpayer classification radios ---
        for cls in range(1, 5):
            fields[f"{p}:taxPayerClassification{cls}"] = "true" if cls == d.taxpayer_classification else "false"

        # --- International treaty / special rate (leave as false) ---
        fields[f"{p}:internationalTreatyYn"] = "false"
        fields[f"{p}:specialRateYn"] = "false"
        fields[f"{p}:specifyInternationalTreaty"] = ""

        # --- Page 2 TIN header ---
        tin1, tin2, tin3, branch = self._taxpayer.tin_parts
        fields[f"{p}:txtPg2TIN1"] = tin1
        fields[f"{p}:txtPg2TIN2"] = tin2
        fields[f"{p}:txtPg2TIN3"] = tin3
        fields[f"{p}:txtPg2BranchCode"] = branch
        fields[f"{p}:Pg2TaxPayer"] = self._taxpayer.name

        # --- Output VAT (items 31-37) ---
        fields[f"{p}:vatableSales"] = _fmt_money(d.vatable_sales)
        fields[f"{p}:outputVatSales"] = _fmt_money(d.output_vat_sales)
        fields[f"{p}:zeroRatedSales"] = _fmt_money(d.zero_rated_sales)
        fields[f"{p}:exemptSales"] = _fmt_money(d.exempt_sales)
        fields[f"{p}:totalSales"] = _fmt_money(d.total_sales)
        fields[f"{p}:outputTaxDue"] = _fmt_money(d.output_tax_due)
        fields[f"{p}:lessOutputVat"] = _fmt_money(d.less_output_vat)
        fields[f"{p}:addOutputVat"] = _fmt_money(d.add_output_vat)
        fields[f"{p}:totalAdjOutput"] = _fmt_money(d.total_adj_output)

        # --- Input VAT from prior periods (items 38-43) ---
        fields[f"{p}:inputTaxCarried"] = _fmt_money(d.input_tax_carried)
        fields[f"{p}:inputTaxDeferred"] = _fmt_money(d.input_tax_deferred)
        fields[f"{p}:transitionalInputTax"] = _fmt_money(d.transitional_input_tax)
        fields[f"{p}:presumptiveInputTax"] = _fmt_money(d.presumptive_input_tax)
        fields[f"{p}:addSpecifyNo42"] = d.other_prior_input_tax_label
        fields[f"{p}:otherSpecify42"] = _fmt_money(d.other_prior_input_tax)
        fields[f"{p}:total43"] = _fmt_money(d.total_prior_input)

        # --- Current period purchases (items 44-50) ---
        fields[f"{p}:domesticPurchase"] = _fmt_money(d.domestic_purchase)
        fields[f"{p}:domesticInputTax"] = _fmt_money(d.domestic_input_tax)
        fields[f"{p}:servicesPurchase"] = _fmt_money(d.services_purchase)
        fields[f"{p}:serviceInputTax"] = _fmt_money(d.service_input_tax)
        fields[f"{p}:importPurchase"] = _fmt_money(d.import_purchase)
        fields[f"{p}:importInputTax"] = _fmt_money(d.import_input_tax)
        fields[f"{p}:addSpecifyNo47"] = d.other_purchase_label
        fields[f"{p}:otherSpecify47"] = _fmt_money(d.other_purchase)
        fields[f"{p}:domesticPurchaseNoTax"] = _fmt_money(d.domestic_purchase_no_tax)
        fields[f"{p}:vatExemptImports"] = _fmt_money(d.vat_exempt_imports)
        fields[f"{p}:totalCurPurchase"] = _fmt_money(d.total_cur_purchase)
        fields[f"{p}:totalCurInputTax"] = _fmt_money(d.total_cur_input_tax)

        # --- Totals (items 51-61) ---
        fields[f"{p}:totalAvailInputTax"] = _fmt_money(d.total_avail_input_tax)
        fields[f"{p}:importCapitalInputTax"] = _fmt_money(d.import_capital_input_tax)
        fields[f"{p}:inputTaxAttr"] = _fmt_money(d.input_tax_attr)
        fields[f"{p}:vatRefund"] = _fmt_money(d.vat_refund)
        fields[f"{p}:inputVatUnpaid"] = _fmt_money(d.input_vat_unpaid)
        fields[f"{p}:addSpecifyNo56"] = d.other_deduction_label
        fields[f"{p}:otherSpecify56"] = _fmt_money(d.other_deduction)
        fields[f"{p}:totalDeductions"] = _fmt_money(d.total_deductions)
        fields[f"{p}:addInputVat"] = _fmt_money(d.add_input_vat)
        fields[f"{p}:adjDeductions"] = _fmt_money(d.adj_deductions)
        fields[f"{p}:totalAllowInputTax"] = _fmt_money(d.total_allow_input_tax)
        fields[f"{p}:netVatPayable"] = _fmt_money(d.net_vat_payable)

        # --- Tax credits / tax payable (Part II, page 1, items 14-26) ---
        fields[f"{p}:excessInputTax"] = _fmt_money(d.net_vat_payable)
        fields[f"{p}:creditableVat"] = _fmt_money(d.creditable_vat)
        fields[f"{p}:advVatPayment"] = _fmt_money(d.adv_vat_payment)
        fields[f"{p}:vatPaidReturn"] = _fmt_money(d.vat_paid_return)
        fields[f"{p}:addSpecifyNo19"] = d.other_credits_label
        fields[f"{p}:otherCreditsNo19"] = _fmt_money(d.other_credits)
        fields[f"{p}:totalTaxCredits"] = _fmt_money(d.total_tax_credits)
        fields[f"{p}:excessCredits"] = _fmt_money(d.excess_credits)
        fields[f"{p}:surcharge"] = _fmt_money(d.surcharge)
        fields[f"{p}:interest"] = _fmt_money(d.interest)
        fields[f"{p}:compromise"] = _fmt_money(d.compromise)
        fields[f"{p}:penalties"] = _fmt_money(d.penalties)
        fields[f"{p}:totalPayable"] = _fmt_money(d.total_payable)

        # --- Schedule 1 (capital goods amortization) totals ---
        fields[f"{p}:sched1TotalD"] = "0.00"
        fields[f"{p}:sched1TotalE"] = "0.00"
        fields[f"{p}:sched1TotalH"] = "0.00"
        fields[f"{p}:sched1TotalI"] = "0.00"

        # --- Schedule 2 (input tax allocation) - leave blank ---
        fields[f"{p}:sched2InputTaxDirect"] = "0.00"
        fields[f"{p}:sched2VatExemptSale"] = _fmt_money(d.exempt_sales)
        fields[f"{p}:sched2AmountInputTax"] = "0.00"
        fields[f"{p}:sched2TotalSales"] = _fmt_money(d.total_sales)
        fields[f"{p}:sched2TotalRatable"] = "0.00"
        fields[f"{p}:sched2TotalAttr"] = "0.00"

        # --- Misc flags ---
        fields["txtFinalFlag"] = "0"
        fields["txtEnroll"] = "N"
        fields["ebirOnlineSecret"] = ""
        fields["ebirOnlineUsername"] = ""
        fields["ebirOnlineConfirmUsername"] = ""
        fields["driveSelectTPExport"] = ""
        fields[f"{p}:txtCurrentPage"] = "1"
        fields[f"{p}:taxpayerName"] = self._taxpayer.name  # duplicate used in saveXML

        return fields
