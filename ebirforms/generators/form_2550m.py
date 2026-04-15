"""Generator for BIR Form 2550-M (Monthly Value-Added Tax Declaration).

Field mapping (reverse-engineered from forms_BIR-Form2550M.hta):

Period / header:
    frm2550q:RtnMonth           -> Return month (1-12, select index)
    frm2550q:txtYear            -> Return year (YYYY)
    frm2550q:RtnPeriodFrom      -> Period start date (MM/DD/YYYY, computed)
    frm2550q:RtnPeriodTo        -> Period end date (MM/DD/YYYY, computed)
    frm2550q:AmendedRtnY        -> Amended return Yes (radio checked bool)
    frm2550q:AmendedRtnN        -> Amended return No (radio checked bool)
    frm2550q:TaxPayer           -> Taxpayer registered name (URL-escaped)
    frm2550q:txtTIN1/2/3        -> TIN parts
    frm2550q:txtBranchCode      -> Branch code
    frm2550q:txtRDOCode         -> RDO code
    frm2550q:txtLineBus         -> Line of business
    frm2550q:txtTelNum          -> Telephone
    frm2550q:txtAddress         -> Address (URL-escaped)
    frm2550q:txtZipCode         -> ZIP code
    frm2550q:txtSheets          -> Number of sheets attached
    txtEmail                    -> Email (no prefix)

Part II - Output Tax (Sales/Receipts exclusive of VAT):
    frm2550q:txtTax15A          -> 15A: Vatable Sales/Receipts - Private (amount)
    frm2550q:txtTax15B          -> 15B: Output Tax Due on vatable sales
    frm2550q:txtTax16A          -> 16A: Sales to Government (amount)
    frm2550q:txtTax16B          -> 16B: Output Tax on sales to govt (5% or 12%)
    frm2550q:txtTax17           -> 17:  Zero-Rated Sales/Receipts
    frm2550q:txtTax18           -> 18:  Exempt Sales/Receipts
    frm2550q:txtTax19A          -> 19A: Total Sales/Receipts (computed)
    frm2550q:txtTax19B          -> 19B: Total Output Tax Due (computed)

Part II - Input Tax (Less: Allowable Input Tax):
    frm2550q:txtTax20A          -> 20A: Input Tax carried over from previous period
    frm2550q:txtTax20B          -> 20B: Input Tax deferred on capital goods > P1M
    frm2550q:txtTax20C          -> 20C: Transitional Input Tax
    frm2550q:txtTax20D          -> 20D: Presumptive Input Tax
    frm2550q:txtTax20E          -> 20E: Others
    frm2550q:txtTax20F          -> 20F: Total (20A+20B+20C+20D+20E, computed)
    frm2550q:txtTax21A          -> 21A: Capital goods <=P1M - Purchases (Sch. 2)
    frm2550q:txtTax21B          -> 21B: Capital goods <=P1M - Input Tax (Sch. 2)
    frm2550q:txtTax21C          -> 21C: Capital goods >P1M - Purchases (Sch. 3)
    frm2550q:txtTax21D          -> 21D: Capital goods >P1M - Input Tax (Sch. 3)
    frm2550q:txtTax21E          -> 21E: Domestic Purchases of Goods (non-capital)
    frm2550q:txtTax21F          -> 21F: Input Tax on domestic goods
    frm2550q:txtTax21G          -> 21G: Importation of Goods (non-capital)
    frm2550q:txtTax21H          -> 21H: Input Tax on importation
    frm2550q:txtTax21I          -> 21I: Domestic Purchase of Services
    frm2550q:txtTax21J          -> 21J: Input Tax on domestic services
    frm2550q:txtTax21K          -> 21K: Services by Non-residents
    frm2550q:txtTax21L          -> 21L: Input Tax on non-resident services
    frm2550q:txtTax21M          -> 21M: Purchases Not Qualified for Input Tax
    frm2550q:txtTax21N          -> 21N: Others (purchases)
    frm2550q:txtTax21O          -> 21O: Others (input tax)
    frm2550q:txtTax21P          -> 21P: Total Current Purchases (computed)
    frm2550q:txtTax22           -> 22:  Total Available Input Tax (20F + current IT, computed)

Part II - Deductions and Net VAT:
    frm2550q:txtTax23A          -> 23A: Input Tax on capital goods >P1M deferred (Sch. 3)
    frm2550q:txtTax23B          -> 23B: Input Tax on sale to Govt closed to expense (Sch. 4)
    frm2550q:txtTax23C          -> 23C: Input Tax allocable to exempt sales (Sch. 5)
    frm2550q:txtTax23D          -> 23D: VAT Refund/TCC claimed
    frm2550q:txtTax23E          -> 23E: Others
    frm2550q:txtTax23F          -> 23F: Total Deductions (sum of 23A-23E, computed)
    frm2550q:txtTax24           -> 24:  Total Allowable Input Tax (22 - 23F, computed)
    frm2550q:txtTax25           -> 25:  Net VAT Payable (19B - 24, computed)

Part II - Tax Credits/Payments:
    frm2550q:txtTax26A          -> 26A: Monthly VAT Payments - previous two months
    frm2550q:txtTax26B          -> 26B: Creditable VAT Withheld (Sch. 6)
    frm2550q:txtTax26C          -> 26C: Advance Payment - Sugar and Flour (Sch. 7)
    frm2550q:txtTax26D          -> 26D: VAT withheld on Sales to Government (Sch. 8)
    frm2550q:txtTax26E          -> 26E: VAT paid in return previously filed (amended only)
    frm2550q:txtTax26F          -> 26F: Advance Payments made (0605)
    frm2550q:txtTax26G          -> 26G: Others
    frm2550q:txtTax26H          -> 26H: Total Tax Credits/Payments (26A-26G, computed)
    frm2550q:txtTax27           -> 27:  Tax Still Payable / (Overpayment) (25 - 26H)
    frm2550q:txtTax28A          -> 28A: Surcharge
    frm2550q:txtTax28B          -> 28B: Interest
    frm2550q:txtTax28C          -> 28C: Compromise
    frm2550q:txtTax28D          -> 28D: Total Penalties (28A+28B+28C, computed)
    frm2550q:txtTax29           -> 29:  Total Amount Payable (27 + 28D, computed)

Note: The form's internal prefix is frm2550q (same as the quarterly 2550Q form).
The HTA file is named BIR-Form2550M.hta but internally uses the 2550Q code.
"""

import calendar
from dataclasses import dataclass, field
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt_money(amount: Decimal) -> str:
    """Format decimal as eBIRForms money string: '20,000.00'."""
    return f"{amount:,.2f}"


def _period_end_date(year: int, month: int) -> str:
    """Return MM/DD/YYYY string for the last day of the given month."""
    last_day = calendar.monthrange(year, month)[1]
    return f"{month:02d}/{last_day:02d}/{year}"


def _period_start_date(year: int, month: int) -> str:
    """Return MM/DD/YYYY string for the first day of the given month."""
    return f"{month:02d}/01/{year}"


@dataclass(frozen=True)
class Form2550MData:
    """Data needed to generate BIR Form 2550-M (Monthly VAT Declaration).

    The form is structured in two parts:
    - Output VAT: sales and output tax (items 15-19)
    - Input VAT: available and allowable input tax (items 20-25)
    - Credits/payments and tax still payable (items 26-29)

    All Decimal fields default to zero so callers only need to supply
    fields relevant to their situation.
    """

    year: int
    month: int  # 1-12
    is_amended: bool = False

    # Output Tax - Part II items 15-18 (user-supplied)
    vatable_sales: Decimal = field(default_factory=lambda: Decimal("0.00"))
    output_tax_private: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 15B
    sales_to_govt: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 16A
    output_tax_govt: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 16B
    zero_rated_sales: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 17
    exempt_sales: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 18

    # Input Tax carried over / special (items 20A-20E)
    input_tax_carryover: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 20A
    input_tax_deferred_capital: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 20B
    transitional_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 20C
    presumptive_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 20D
    other_prior_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 20E

    # Current transactions - purchases (21A/C/E/G/I/K/M/N) and input tax (21B/D/F/H/J/L/O)
    capital_goods_small_purchases: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21A
    capital_goods_small_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21B
    capital_goods_large_purchases: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21C
    capital_goods_large_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21D
    domestic_goods_purchases: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21E
    domestic_goods_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21F
    imported_goods_purchases: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21G
    imported_goods_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21H
    domestic_services_purchases: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21I
    domestic_services_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21J
    nonresident_services_purchases: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21K
    nonresident_services_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21L
    non_qualified_purchases: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21M
    other_purchases: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21N
    other_input_tax: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 21O

    # Deductions from input tax (items 23A-23E)
    deferred_input_capital_large: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 23A
    input_tax_govt_expense: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 23B
    input_tax_exempt_sales: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 23C
    vat_refund_tcc: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 23D
    other_deductions: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 23E

    # Tax credits/payments (items 26A-26G)
    monthly_vat_payments_prior: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 26A
    creditable_vat_withheld: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 26B
    advance_payment_sugar_flour: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 26C
    vat_withheld_govt: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 26D
    vat_paid_previous_amended: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 26E
    advance_payments_0605: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 26F
    other_credits: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 26G

    # Penalties (items 28A-28C)
    surcharge: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 28A
    interest: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 28B
    compromise: Decimal = field(default_factory=lambda: Decimal("0.00"))  # 28C

    # Computed properties - Output Tax

    @property
    def total_sales(self) -> Decimal:
        """19A: Total Sales/Receipts (15A + 16A + 17 + 18)."""
        return self.vatable_sales + self.sales_to_govt + self.zero_rated_sales + self.exempt_sales

    @property
    def total_output_tax(self) -> Decimal:
        """19B: Total Output Tax Due (15B + 16B)."""
        return self.output_tax_private + self.output_tax_govt

    # Computed properties - Input Tax

    @property
    def prior_input_tax_total(self) -> Decimal:
        """20F: Total prior input tax (20A+20B+20C+20D+20E)."""
        return (
            self.input_tax_carryover
            + self.input_tax_deferred_capital
            + self.transitional_input_tax
            + self.presumptive_input_tax
            + self.other_prior_input_tax
        )

    @property
    def total_current_purchases(self) -> Decimal:
        """21P: Total Current Purchases (21A+21C+21E+21G+21I+21K+21M+21N)."""
        return (
            self.capital_goods_small_purchases
            + self.capital_goods_large_purchases
            + self.domestic_goods_purchases
            + self.imported_goods_purchases
            + self.domestic_services_purchases
            + self.nonresident_services_purchases
            + self.non_qualified_purchases
            + self.other_purchases
        )

    @property
    def total_available_input_tax(self) -> Decimal:
        """22: Total Available Input Tax (20F + 21B+21D+21F+21H+21J+21L+21O)."""
        current_input = (
            self.capital_goods_small_input_tax
            + self.capital_goods_large_input_tax
            + self.domestic_goods_input_tax
            + self.imported_goods_input_tax
            + self.domestic_services_input_tax
            + self.nonresident_services_input_tax
            + self.other_input_tax
        )
        return self.prior_input_tax_total + current_input

    @property
    def total_deductions(self) -> Decimal:
        """23F: Total Deductions from Input Tax (23A+23B+23C+23D+23E)."""
        return (
            self.deferred_input_capital_large
            + self.input_tax_govt_expense
            + self.input_tax_exempt_sales
            + self.vat_refund_tcc
            + self.other_deductions
        )

    @property
    def total_allowable_input_tax(self) -> Decimal:
        """24: Total Allowable Input Tax (22 - 23F)."""
        return self.total_available_input_tax - self.total_deductions

    @property
    def net_vat_payable(self) -> Decimal:
        """25: Net VAT Payable (19B - 24)."""
        return self.total_output_tax - self.total_allowable_input_tax

    @property
    def total_tax_credits(self) -> Decimal:
        """26H: Total Tax Credits/Payments (26A+26B+26C+26D+26E+26F+26G)."""
        return (
            self.monthly_vat_payments_prior
            + self.creditable_vat_withheld
            + self.advance_payment_sugar_flour
            + self.vat_withheld_govt
            + self.vat_paid_previous_amended
            + self.advance_payments_0605
            + self.other_credits
        )

    @property
    def tax_still_payable(self) -> Decimal:
        """27: Tax Still Payable / (Overpayment) (25 - 26H)."""
        return self.net_vat_payable - self.total_tax_credits

    @property
    def total_penalties(self) -> Decimal:
        """28D: Total Penalties (28A+28B+28C)."""
        return self.surcharge + self.interest + self.compromise

    @property
    def total_amount_payable(self) -> Decimal:
        """29: Total Amount Payable (27 + 28D)."""
        return self.tax_still_payable + self.total_penalties


class Form2550MGenerator(FormGenerator):
    """Generates BIR Form 2550-M (Monthly Value-Added Tax Declaration).

    The form's internal field prefix is frm2550q - the eBIRForms application
    reuses the quarterly 2550Q HTA code for the monthly 2550M filing.
    """

    def __init__(self, taxpayer: TaxpayerInfo, data: Form2550MData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "2550M"

    @property
    def form_prefix(self) -> str:
        # The HTA code uses frm2550q for both 2550M and 2550Q
        return "frm2550q"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields: dict[str, str] = {}

        # Period
        fields[f"{p}:RtnMonth"] = str(d.month)
        fields[f"{p}:txtYear"] = str(d.year)
        fields[f"{p}:RtnPeriodFrom"] = _period_start_date(d.year, d.month)
        fields[f"{p}:RtnPeriodTo"] = _period_end_date(d.year, d.month)

        # Amendment
        fields[f"{p}:AmendedRtnY"] = "true" if d.is_amended else "false"
        fields[f"{p}:AmendedRtnN"] = "false" if d.is_amended else "true"

        # Taxpayer info - note this form uses TaxPayer (not txtTaxpayerName)
        tin1, tin2, tin3, branch = self._taxpayer.tin_parts
        fields[f"{p}:txtTIN1"] = tin1
        fields[f"{p}:txtTIN2"] = tin2
        fields[f"{p}:txtTIN3"] = tin3
        fields[f"{p}:txtBranchCode"] = branch
        fields[f"{p}:txtRDOCode"] = self._taxpayer.rdo_code
        fields[f"{p}:TaxPayer"] = self._taxpayer.name
        fields[f"{p}:txtLineBus"] = self._taxpayer.line_of_business
        fields[f"{p}:txtTelNum"] = self._taxpayer.telephone
        fields[f"{p}:txtAddress"] = self._taxpayer.address
        fields[f"{p}:txtZipCode"] = self._taxpayer.zip_code
        fields[f"{p}:txtSheets"] = "0"
        fields["txtEmail"] = self._taxpayer.email

        # Output tax (Part II items 15-19)
        fields[f"{p}:txtTax15A"] = _fmt_money(d.vatable_sales)
        fields[f"{p}:txtTax15B"] = _fmt_money(d.output_tax_private)
        fields[f"{p}:txtTax16A"] = _fmt_money(d.sales_to_govt)
        fields[f"{p}:txtTax16B"] = _fmt_money(d.output_tax_govt)
        fields[f"{p}:txtTax17"] = _fmt_money(d.zero_rated_sales)
        fields[f"{p}:txtTax18"] = _fmt_money(d.exempt_sales)
        fields[f"{p}:txtTax19A"] = _fmt_money(d.total_sales)
        fields[f"{p}:txtTax19B"] = _fmt_money(d.total_output_tax)

        # Prior input tax (items 20A-20F)
        fields[f"{p}:txtTax20A"] = _fmt_money(d.input_tax_carryover)
        fields[f"{p}:txtTax20B"] = _fmt_money(d.input_tax_deferred_capital)
        fields[f"{p}:txtTax20C"] = _fmt_money(d.transitional_input_tax)
        fields[f"{p}:txtTax20D"] = _fmt_money(d.presumptive_input_tax)
        fields[f"{p}:txtTax20E"] = _fmt_money(d.other_prior_input_tax)
        fields[f"{p}:txtTax20F"] = _fmt_money(d.prior_input_tax_total)

        # Current transactions (items 21A-21P)
        fields[f"{p}:txtTax21A"] = _fmt_money(d.capital_goods_small_purchases)
        fields[f"{p}:txtTax21B"] = _fmt_money(d.capital_goods_small_input_tax)
        fields[f"{p}:txtTax21C"] = _fmt_money(d.capital_goods_large_purchases)
        fields[f"{p}:txtTax21D"] = _fmt_money(d.capital_goods_large_input_tax)
        fields[f"{p}:txtTax21E"] = _fmt_money(d.domestic_goods_purchases)
        fields[f"{p}:txtTax21F"] = _fmt_money(d.domestic_goods_input_tax)
        fields[f"{p}:txtTax21G"] = _fmt_money(d.imported_goods_purchases)
        fields[f"{p}:txtTax21H"] = _fmt_money(d.imported_goods_input_tax)
        fields[f"{p}:txtTax21I"] = _fmt_money(d.domestic_services_purchases)
        fields[f"{p}:txtTax21J"] = _fmt_money(d.domestic_services_input_tax)
        fields[f"{p}:txtTax21K"] = _fmt_money(d.nonresident_services_purchases)
        fields[f"{p}:txtTax21L"] = _fmt_money(d.nonresident_services_input_tax)
        fields[f"{p}:txtTax21M"] = _fmt_money(d.non_qualified_purchases)
        fields[f"{p}:txtTax21N"] = _fmt_money(d.other_purchases)
        fields[f"{p}:txtTax21O"] = _fmt_money(d.other_input_tax)
        fields[f"{p}:txtTax21P"] = _fmt_money(d.total_current_purchases)

        # Total available input tax (item 22)
        fields[f"{p}:txtTax22"] = _fmt_money(d.total_available_input_tax)

        # Deductions from input tax (items 23A-23F)
        fields[f"{p}:txtTax23A"] = _fmt_money(d.deferred_input_capital_large)
        fields[f"{p}:txtTax23B"] = _fmt_money(d.input_tax_govt_expense)
        fields[f"{p}:txtTax23C"] = _fmt_money(d.input_tax_exempt_sales)
        fields[f"{p}:txtTax23D"] = _fmt_money(d.vat_refund_tcc)
        fields[f"{p}:txtTax23E"] = _fmt_money(d.other_deductions)
        fields[f"{p}:txtTax23F"] = _fmt_money(d.total_deductions)

        # Net VAT payable (items 24-25)
        fields[f"{p}:txtTax24"] = _fmt_money(d.total_allowable_input_tax)
        fields[f"{p}:txtTax25"] = _fmt_money(d.net_vat_payable)

        # Tax credits/payments (items 26A-26H)
        fields[f"{p}:txtTax26A"] = _fmt_money(d.monthly_vat_payments_prior)
        fields[f"{p}:txtTax26B"] = _fmt_money(d.creditable_vat_withheld)
        fields[f"{p}:txtTax26C"] = _fmt_money(d.advance_payment_sugar_flour)
        fields[f"{p}:txtTax26D"] = _fmt_money(d.vat_withheld_govt)
        fields[f"{p}:txtTax26E"] = _fmt_money(d.vat_paid_previous_amended)
        fields[f"{p}:txtTax26F"] = _fmt_money(d.advance_payments_0605)
        fields[f"{p}:txtTax26G"] = _fmt_money(d.other_credits)
        fields[f"{p}:txtTax26H"] = _fmt_money(d.total_tax_credits)

        # Tax still payable (item 27)
        fields[f"{p}:txtTax27"] = _fmt_money(d.tax_still_payable)

        # Penalties (items 28A-28D)
        fields[f"{p}:txtTax28A"] = _fmt_money(d.surcharge)
        fields[f"{p}:txtTax28B"] = _fmt_money(d.interest)
        fields[f"{p}:txtTax28C"] = _fmt_money(d.compromise)
        fields[f"{p}:txtTax28D"] = _fmt_money(d.total_penalties)

        # Total amount payable (item 29)
        fields[f"{p}:txtTax29"] = _fmt_money(d.total_amount_payable)

        # Flags
        fields["txtFinalFlag"] = "0"
        fields["txtEnroll"] = "N"
        fields["ebirOnlineSecret"] = ""
        fields["ebirOnlineConfirmUsername"] = ""
        fields["ebirOnlineUsername"] = ""
        fields["driveSelectTPExport"] = ""

        return fields
