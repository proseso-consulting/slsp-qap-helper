"""Generator for BIR Form 1601-EQ (Quarterly Remittance of Creditable Income Taxes Withheld - Expanded).

XML structure reverse-engineered from: extracted_hta/decoded/renamed/forms_BIR-Form1601EQ.hta

Field mapping:
    frm1601EQ:txtYear             -> Return period year (YYYY)
    frm1601EQ:optQuarter:1/2/3/4  -> Quarter (radio)
    frm1601EQ:optAmend:Y/N        -> Is amended return?
    frm1601EQ:optWithheld:Y/N     -> Any taxes withheld?
    frm1601EQ:txtNoSheets         -> Number of sheets attached
    frm1601EQ:txtTIN1/2/3         -> TIN parts
    frm1601EQ:txtBranchCode       -> Branch code
    frm1601EQ:txtRDOCode          -> RDO code (select element)
    frm1601EQ:txtTaxpayerName     -> Taxpayer name
    frm1601EQ:txtLineBus          -> Line of business
    frm1601EQ:txtAddress          -> Address
    frm1601EQ:txtAddress2         -> Address continuation (merged into txtAddress on save)
    frm1601EQ:txtZipCode          -> ZIP code
    frm1601EQ:txtTelNum           -> Telephone
    frm1601EQ:optCategory:P/G     -> Private (P) or Government (G)
    txtEmail                      -> Email (no prefix)

    ATC table rows (1-indexed, dynamic count):
    frm1601EQ:txtAtcCd{n}         -> ATC code (e.g., WE011)
    frm1601EQ:txtTaxBase{n}       -> Tax base amount
    frm1601EQ:txtTaxRate{n}       -> Tax rate (%)
    frm1601EQ:txtTaxbeWithHeld{n} -> Tax withheld = taxBase * taxRate / 100

    frm1601EQ:txtTotalOtherTax    -> Total of "other selected ATC" rows (rows 7+)
    frm1601EQ:txtTax19            -> Total taxes withheld for the quarter (sum of ATC rows)
    frm1601EQ:txtTax20            -> Less: remittances made - 1st month of quarter
    frm1601EQ:txtTax21            -> Less: remittances made - 2nd month of quarter
    frm1601EQ:txtTax22            -> Tax remitted previously filed (amended returns only)
    frm1601EQ:txtTax23            -> Over-remittance from previous quarter
    frm1601EQ:txtTax24            -> Total remittances made (sum of 20-23)
    frm1601EQ:txtTax25            -> Tax still due (19 - 24)
    frm1601EQ:txtTax26            -> Surcharge
    frm1601EQ:txtTax27            -> Interest
    frm1601EQ:txtTax28            -> Compromise
    frm1601EQ:txtTax29            -> Total penalties (sum of 26-28)
    frm1601EQ:txtTax30            -> Total amount still due (25 + 29)

    frm1601EQ:ifRefund            -> Over-remittance: to be refunded
    frm1601EQ:ifIssueCert         -> Over-remittance: tax credit certificate
    frm1601EQ:ifCarriedOver       -> Over-remittance: carried over to next quarter

    Payment details (items 33-36):
    frm1601EQ:txtAgency33/34/35   -> Drawee bank name
    frm1601EQ:txtNumber33/34/35   -> Check/reference number
    frm1601EQ:txtDate33/34/35     -> Date of payment
    frm1601EQ:txtAmount33/34/35   -> Amount paid
    frm1601EQ:txtParticular36     -> Other payment particulars
    frm1601EQ:txtAgency36 / txtNumber36 / txtDate36 / txtAmount36

    txtTaxAgentNo                 -> Tax agent accreditation number
    txtDateIssue / txtDateExpiry  -> Accreditation dates
    txtFinalFlag                  -> 0 = not final
    txtEnroll                     -> N = not enrolled
"""

from dataclasses import dataclass
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt_money(amount: Decimal) -> str:
    """Format decimal as eBIRForms money string: '20,000.00'."""
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class AtcEntry:
    """A single row in the ATC table (Part II Computation of Tax)."""

    atc_code: str  # e.g., "WE011"
    tax_base: Decimal
    tax_rate: Decimal  # percentage, e.g., Decimal("1.00") for 1%

    @property
    def tax_withheld(self) -> Decimal:
        """Tax withheld = tax_base * tax_rate / 100, rounded to 2 decimal places."""
        return (self.tax_base * self.tax_rate / Decimal("100")).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class Form1601EQData:
    """Data needed to generate BIR Form 1601-EQ."""

    year: int
    quarter: int  # 1-4
    is_amended: bool
    is_private: bool  # True=Private sector, False=Government
    atc_entries: tuple[AtcEntry, ...]  # at least one entry when taxes are withheld

    # Less: Remittances Made (monthly 0619-E filings)
    remittance_month1: Decimal  # Item 20 - 1st month of quarter
    remittance_month2: Decimal  # Item 21 - 2nd month of quarter

    # Other credits
    previously_remitted_amended: Decimal  # Item 22 - only for amended returns
    over_remittance_prior_quarter: Decimal  # Item 23

    # Penalties (late filing)
    surcharge: Decimal  # Item 26
    interest: Decimal  # Item 27
    compromise: Decimal  # Item 28

    # Over-remittance disposition (mutually exclusive checkboxes)
    if_refund: bool = False
    if_issue_cert: bool = False
    if_carried_over: bool = False

    # Number of attached sheets
    no_sheets: int = 0

    @property
    def total_withheld(self) -> Decimal:
        """Item 19: Total taxes withheld for the quarter (sum of all ATC rows)."""
        return sum((e.tax_withheld for e in self.atc_entries), Decimal("0.00"))

    @property
    def total_remittances(self) -> Decimal:
        """Item 24: Total remittances made (sum of items 20-23)."""
        return (
            self.remittance_month1
            + self.remittance_month2
            + self.previously_remitted_amended
            + self.over_remittance_prior_quarter
        )

    @property
    def tax_still_due(self) -> Decimal:
        """Item 25: Tax still due (item 19 less item 24)."""
        return self.total_withheld - self.total_remittances

    @property
    def total_penalties(self) -> Decimal:
        """Item 29: Total penalties (sum of items 26-28)."""
        return self.surcharge + self.interest + self.compromise

    @property
    def total_amount_due(self) -> Decimal:
        """Item 30: Total amount still due (items 25 + 29)."""
        return self.tax_still_due + self.total_penalties

    @property
    def has_withheld(self) -> bool:
        return bool(self.atc_entries) and self.total_withheld > Decimal("0.00")


class Form1601EQGenerator(FormGenerator):
    """Generates BIR Form 1601-EQ."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form1601EQData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "1601EQ"

    @property
    def form_prefix(self) -> str:
        return "frm1601EQ"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields: dict[str, str] = {}

        # Period
        fields[f"{p}:txtYear"] = str(d.year)

        # Quarter radio buttons (1-4)
        for q in range(1, 5):
            fields[f"{p}:optQuarter:{q}"] = "true" if d.quarter == q else "false"

        # Amendment
        fields[f"{p}:optAmend:Y"] = "true" if d.is_amended else "false"
        fields[f"{p}:optAmend:N"] = "false" if d.is_amended else "true"

        # Withheld indicator
        fields[f"{p}:optWithheld:Y"] = "true" if d.has_withheld else "false"
        fields[f"{p}:optWithheld:N"] = "false" if d.has_withheld else "true"

        # Number of sheets
        fields[f"{p}:txtNoSheets"] = str(d.no_sheets)

        # Taxpayer info
        fields.update(self._taxpayer_fields())
        fields[f"{p}:txtLineBus"] = self._taxpayer.line_of_business
        # txtAddress2 is merged into txtAddress by saveXML; keep it empty
        fields[f"{p}:txtAddress2"] = ""

        # Category
        fields[f"{p}:optCategory:P"] = "true" if d.is_private else "false"
        fields[f"{p}:optCategory:G"] = "false" if d.is_private else "true"

        # ATC rows (1-indexed)
        for idx, entry in enumerate(d.atc_entries, start=1):
            fields[f"{p}:txtAtcCd{idx}"] = entry.atc_code
            fields[f"{p}:txtTaxBase{idx}"] = _fmt_money(entry.tax_base)
            fields[f"{p}:txtTaxRate{idx}"] = _fmt_money(entry.tax_rate)
            fields[f"{p}:txtTaxbeWithHeld{idx}"] = _fmt_money(entry.tax_withheld)

        # Other selected ATC total (rows 7+ are classified as "other"; default 0)
        fields[f"{p}:txtTotalOtherTax"] = "0.00"

        # Tax computation (items 19-30)
        fields[f"{p}:txtTax19"] = _fmt_money(d.total_withheld)
        fields[f"{p}:txtTax20"] = _fmt_money(d.remittance_month1)
        fields[f"{p}:txtTax21"] = _fmt_money(d.remittance_month2)
        fields[f"{p}:txtTax22"] = _fmt_money(d.previously_remitted_amended)
        fields[f"{p}:txtTax23"] = _fmt_money(d.over_remittance_prior_quarter)
        fields[f"{p}:txtTax24"] = _fmt_money(d.total_remittances)
        fields[f"{p}:txtTax25"] = _fmt_money(d.tax_still_due)
        fields[f"{p}:txtTax26"] = _fmt_money(d.surcharge)
        fields[f"{p}:txtTax27"] = _fmt_money(d.interest)
        fields[f"{p}:txtTax28"] = _fmt_money(d.compromise)
        fields[f"{p}:txtTax29"] = _fmt_money(d.total_penalties)
        fields[f"{p}:txtTax30"] = _fmt_money(d.total_amount_due)

        # Over-remittance disposition checkboxes
        fields[f"{p}:ifRefund"] = "true" if d.if_refund else "false"
        fields[f"{p}:ifIssueCert"] = "true" if d.if_issue_cert else "false"
        fields[f"{p}:ifCarriedOver"] = "true" if d.if_carried_over else "false"

        # Tax agent (empty if no agent)
        fields["txtTaxAgentNo"] = ""
        fields["txtDateIssue"] = ""
        fields["txtDateExpiry"] = ""

        # Payment details (items 33-35)
        for item in ("33", "34", "35"):
            fields[f"{p}:txtAgency{item}"] = ""
            fields[f"{p}:txtNumber{item}"] = ""
            fields[f"{p}:txtDate{item}"] = ""
            fields[f"{p}:txtAmount{item}"] = ""

        # Item 36 (other payments - has an extra "particular" field)
        fields[f"{p}:txtParticular36"] = ""
        fields[f"{p}:txtAgency36"] = ""
        fields[f"{p}:txtNumber36"] = ""
        fields[f"{p}:txtDate36"] = ""
        fields[f"{p}:txtAmount36"] = ""

        # Flags
        fields["txtFinalFlag"] = "0"
        fields["txtEnroll"] = "N"
        fields["ebirOnlineConfirmUsername"] = ""
        fields["ebirOnlineUsername"] = ""
        fields["ebirOnlineSecret"] = ""
        fields["driveSelectTPExport"] = ""

        return fields
