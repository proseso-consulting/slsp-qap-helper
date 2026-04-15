"""Generator for BIR Form 0619-F (Monthly Remittance of Final Income Taxes Withheld).

XML structure reverse-engineered from: extracted_hta/decoded/renamed/forms_BIR-Form0619F.hta

Field mapping:
    frm0619F:txtMonth          -> Return period month (MM)
    frm0619F:txtYear           -> Return period year (YYYY)
    frm0619F:txtDueMonth       -> Due date month
    frm0619F:txtDueDay         -> Due date day
    frm0619F:txtDueYear        -> Due date year
    frm0619F:optAmend:Y/N      -> Is amended return?
    frm0619F:optWithheld:Y/N   -> Any taxes withheld?
    frm0619F:txtTaxTypeCode    -> Tax type code: WB (Business) or WF (Final)
    frm0619F:txtTIN1/2/3       -> TIN parts
    frm0619F:txtBranchCode     -> Branch code
    frm0619F:txtRDOCode        -> RDO code
    frm0619F:txtTaxpayerName   -> Taxpayer name
    frm0619F:txtLineBus        -> Line of business
    frm0619F:txtAddress        -> Address
    frm0619F:txtZipCode        -> ZIP code
    frm0619F:txtTelNum         -> Telephone
    frm0619F:optCategory:P/G   -> Private (P) or Government (G)
    txtEmail                   -> Email (no prefix)
    frm0619F:txtTax13          -> Business tax withheld (enabled when WB)
    frm0619F:txtTax14          -> Final tax withheld (enabled when WF)
    frm0619F:txtTax15          -> Total (13 + 14)
    frm0619F:txtTax16          -> Adjustment from prior month (only for amended)
    frm0619F:txtTax17          -> Net amount to remit (15 - 16)
    frm0619F:txtTax18A         -> Surcharge
    frm0619F:txtTax18B         -> Interest
    frm0619F:txtTax18C         -> Compromise
    frm0619F:txtTax18D         -> Total penalties (18A + 18B + 18C) - computed
    frm0619F:txtTax19          -> Total amount payable (17 + 18D) - computed
    txtTaxAgentNo              -> Tax agent accreditation number
    txtDateIssue/Expiry        -> Accreditation dates
    txtAgency20..23            -> Payment details (drawee bank, number, date, amount)
    txtFinalFlag               -> 0 = not final
    txtEnroll                  -> N = not enrolled
"""

from dataclasses import dataclass
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo

# Valid tax type codes for 0619-F
TAX_TYPE_WB = "WB"  # Withholding Tax on Business (fringe benefits, etc.)
TAX_TYPE_WF = "WF"  # Withholding Tax on Final Income


def _fmt_money(amount: Decimal) -> str:
    """Format decimal as eBIRForms money string: '20,000.00'."""
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class Form0619FData:
    """Data needed to generate BIR Form 0619-F."""

    year: int
    month: int  # 1-12
    is_amended: bool
    tax_type_code: str  # "WB" or "WF"
    is_private: bool  # True = Private sector, False = Government

    # Tax computation
    # For WB: business_tax is the withheld amount, final_tax must be 0
    # For WF: final_tax is the withheld amount, business_tax must be 0
    business_tax: Decimal  # Item 13
    final_tax: Decimal  # Item 14
    adjustment: Decimal  # Item 16 (prior month adjustment; only for amended)

    # Penalties (normally 0 for on-time filing)
    surcharge: Decimal  # Item 18A
    interest: Decimal  # Item 18B
    compromise: Decimal  # Item 18C

    @property
    def total_withheld(self) -> Decimal:
        """Item 15: Total (13 + 14)."""
        return self.business_tax + self.final_tax

    @property
    def net_amount_to_remit(self) -> Decimal:
        """Item 17: Net amount to remit (15 - 16)."""
        return self.total_withheld - self.adjustment

    @property
    def total_penalties(self) -> Decimal:
        """Item 18D: Total penalties (18A + 18B + 18C)."""
        return self.surcharge + self.interest + self.compromise

    @property
    def total_amount_payable(self) -> Decimal:
        """Item 19: Total amount payable (17 + 18D)."""
        return self.net_amount_to_remit + self.total_penalties

    @property
    def due_month(self) -> int:
        """Due date is the 10th of the following month."""
        return self.month % 12 + 1

    @property
    def due_year(self) -> int:
        return self.year if self.month < 12 else self.year + 1


class Form0619FGenerator(FormGenerator):
    """Generates BIR Form 0619-F."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form0619FData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "0619F"

    @property
    def form_prefix(self) -> str:
        return "frm0619F"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields = {}

        # Period
        fields[f"{p}:txtMonth"] = f"{d.month:02d}"
        fields[f"{p}:txtYear"] = str(d.year)
        fields[f"{p}:txtDueMonth"] = f"{d.due_month:02d}"
        fields[f"{p}:txtDueDay"] = "10"
        fields[f"{p}:txtDueYear"] = str(d.due_year)

        # Amendment
        fields[f"{p}:optAmend:Y"] = "true" if d.is_amended else "false"
        fields[f"{p}:optAmend:N"] = "false" if d.is_amended else "true"

        # Withheld
        has_withheld = d.total_withheld > 0
        fields[f"{p}:optWithheld:Y"] = "true" if has_withheld else "false"
        fields[f"{p}:optWithheld:N"] = "false" if has_withheld else "true"

        # Tax type (WB or WF - no ATC code on this form)
        fields[f"{p}:txtTaxTypeCode"] = d.tax_type_code

        # Taxpayer info
        fields.update(self._taxpayer_fields())
        fields[f"{p}:txtLineBus"] = self._taxpayer.line_of_business

        # Category
        fields[f"{p}:optCategory:P"] = "true" if d.is_private else "false"
        fields[f"{p}:optCategory:G"] = "false" if d.is_private else "true"

        # Tax computation
        fields[f"{p}:txtTax13"] = _fmt_money(d.business_tax)
        fields[f"{p}:txtTax14"] = _fmt_money(d.final_tax)
        fields[f"{p}:txtTax15"] = _fmt_money(d.total_withheld)
        fields[f"{p}:txtTax16"] = _fmt_money(d.adjustment)
        fields[f"{p}:txtTax17"] = _fmt_money(d.net_amount_to_remit)
        fields[f"{p}:txtTax18A"] = _fmt_money(d.surcharge)
        fields[f"{p}:txtTax18B"] = _fmt_money(d.interest)
        fields[f"{p}:txtTax18C"] = _fmt_money(d.compromise)
        fields[f"{p}:txtTax18D"] = _fmt_money(d.total_penalties)
        fields[f"{p}:txtTax19"] = _fmt_money(d.total_amount_payable)

        # Tax agent (empty if no agent)
        fields["txtTaxAgentNo"] = ""
        fields["txtDateIssue"] = ""
        fields["txtDateExpiry"] = ""

        # Payment details (empty - filled in eBIRForms after payment)
        # 0619F uses items 20, 21, 22 (and 23 for particulars)
        for item in ("20", "21", "22"):
            fields[f"txtAgency{item}"] = ""
            fields[f"txtNumber{item}"] = ""
            fields[f"txtDate{item}"] = ""
            fields[f"txtAmount{item}"] = ""

        fields["txtParticular23"] = ""
        fields["txtAgency23"] = ""
        fields["txtNumber23"] = ""
        fields["txtDate23"] = ""
        fields["txtAmount23"] = ""

        # Flags
        fields["txtFinalFlag"] = "0"
        fields["txtEnroll"] = "N"
        fields["ebirOnlineConfirmUsername"] = ""
        fields["ebirOnlineUsername"] = ""
        fields["ebirOnlineSecret"] = ""
        fields["driveSelectTPExport"] = ""

        return fields
