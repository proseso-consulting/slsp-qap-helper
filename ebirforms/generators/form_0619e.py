"""Generator for BIR Form 0619-E (Monthly Remittance of Creditable Income Taxes Withheld - Expanded).

XML structure reverse-engineered from: samples/010318867000-0619E-032026.xml

Field mapping (from sample):
    frm0619E:txtMonth          -> Return period month (MM)
    frm0619E:txtYear           -> Return period year (YYYY)
    frm0619E:txtDueMonth       -> Due date month
    frm0619E:txtDueDay         -> Due date day
    frm0619E:txtDueYear        -> Due date year
    frm0619E:optAmend:Y/N      -> Is amended return?
    frm0619E:optWithheld:Y/N   -> Any taxes withheld?
    frm0619E:txtAtc            -> ATC code (e.g., WME10)
    frm0619E:txtTaxTypeCode    -> Tax type code (e.g., WE)
    frm0619E:txtTIN1/2/3       -> TIN parts
    frm0619E:txtBranchCode     -> Branch code
    frm0619E:txtRDOCode        -> RDO code
    frm0619E:txtTaxpayerName   -> Taxpayer name
    frm0619E:txtLineBus        -> Line of business
    frm0619E:txtAddress        -> Address
    frm0619E:txtZipCode        -> ZIP code
    frm0619E:txtTelNum         -> Telephone
    frm0619E:optCategory:P/G   -> Private (P) or Government (G)
    txtEmail                   -> Email (no prefix)
    frm0619E:txtTax14          -> Total amount of taxes withheld for the month
    frm0619E:txtTax15          -> Adjustment from previous month/s
    frm0619E:txtTax16          -> Total (14 + 15)
    frm0619E:txtTax17A         -> Less: tax remitted in return previously filed
    frm0619E:txtTax17B         -> (another credit)
    frm0619E:txtTax17C         -> (another credit)
    frm0619E:txtTax17D         -> (another credit)
    frm0619E:txtTax18          -> Tax still due (16 - sum of 17A-D)
    txtTaxAgentNo              -> Tax agent accreditation number
    txtDateIssue/Expiry        -> Accreditation dates
    txtAgency19..22            -> Payment details (drawee bank, number, date, amount)
    txtFinalFlag               -> 0 = not final
    txtEnroll                  -> N = not enrolled
"""

from dataclasses import dataclass
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt_money(amount: Decimal) -> str:
    """Format decimal as eBIRForms money string: '20,000.00'."""
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class Form0619EData:
    """Data needed to generate BIR Form 0619-E."""

    year: int
    month: int  # 1-12
    is_amended: bool
    atc_code: str  # e.g., "WME10"
    tax_type_code: str  # e.g., "WE" for Expanded WT
    is_private: bool  # True=Private sector, False=Government

    # Tax computation
    total_withheld: Decimal  # Item 14
    adjustment: Decimal  # Item 15 (can be negative)
    previously_remitted: Decimal  # Item 17A
    credit_17b: Decimal
    credit_17c: Decimal
    credit_17d: Decimal

    @property
    def total_amount(self) -> Decimal:
        """Item 16: Total (14 + 15)."""
        return self.total_withheld + self.adjustment

    @property
    def tax_still_due(self) -> Decimal:
        """Item 18: Tax still due."""
        total_credits = self.previously_remitted + self.credit_17b + self.credit_17c + self.credit_17d
        return self.total_amount - total_credits

    @property
    def due_month(self) -> int:
        """Due date is the 10th of the following month."""
        return self.month % 12 + 1

    @property
    def due_year(self) -> int:
        return self.year if self.month < 12 else self.year + 1


class Form0619EGenerator(FormGenerator):
    """Generates BIR Form 0619-E."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form0619EData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "0619E"

    @property
    def form_prefix(self) -> str:
        return "frm0619E"

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

        # ATC and tax type
        fields[f"{p}:txtAtc"] = d.atc_code
        fields[f"{p}:txtTaxTypeCode"] = d.tax_type_code

        # Taxpayer info
        fields.update(self._taxpayer_fields())
        fields[f"{p}:txtLineBus"] = self._taxpayer.line_of_business

        # Category
        fields[f"{p}:optCategory:P"] = "true" if d.is_private else "false"
        fields[f"{p}:optCategory:G"] = "false" if d.is_private else "true"

        # Tax computation
        fields[f"{p}:txtTax14"] = _fmt_money(d.total_withheld)
        fields[f"{p}:txtTax15"] = _fmt_money(d.adjustment)
        fields[f"{p}:txtTax16"] = _fmt_money(d.total_amount)
        fields[f"{p}:txtTax17A"] = _fmt_money(d.previously_remitted)
        fields[f"{p}:txtTax17B"] = _fmt_money(d.credit_17b)
        fields[f"{p}:txtTax17C"] = _fmt_money(d.credit_17c)
        fields[f"{p}:txtTax17D"] = _fmt_money(d.credit_17d)
        fields[f"{p}:txtTax18"] = _fmt_money(d.tax_still_due)

        # Tax agent (empty if no agent)
        fields["txtTaxAgentNo"] = ""
        fields["txtDateIssue"] = ""
        fields["txtDateExpiry"] = ""

        # Payment details (empty - filled in eBIRForms after payment)
        for item in ("19", "20", "21"):
            fields[f"txtAgency{item}"] = ""
            fields[f"txtNumber{item}"] = ""
            fields[f"txtDate{item}"] = ""
            fields[f"txtAmount{item}"] = ""

        fields["txtParticular22"] = ""
        fields["txtAgency22"] = ""
        fields["txtNumber22"] = ""
        fields["txtDate22"] = ""
        fields["txtAmount22"] = ""

        # Flags
        fields["txtFinalFlag"] = "0"
        fields["txtEnroll"] = "N"
        fields["ebirOnlineConfirmUsername"] = ""
        fields["ebirOnlineUsername"] = ""
        fields["ebirOnlineSecret"] = ""
        fields["driveSelectTPExport"] = ""

        return fields
