"""Generator for BIR Form 1601-FQ (Quarterly Remittance of Final Income Taxes Withheld).

Field prefix: frm1601FQ
Frequency: Quarterly
Data source: final_wt extractor
"""

from dataclasses import dataclass
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt(amount: Decimal) -> str:
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class AtcEntry:
    """A single ATC row in the 1601FQ schedule."""

    atc_code: str
    tax_base: Decimal
    tax_rate: Decimal
    tax_withheld: Decimal


@dataclass(frozen=True)
class Form1601FQData:
    """Data for BIR Form 1601-FQ."""

    year: int
    quarter: int  # 1-4
    is_amended: bool
    is_private: bool  # True=Private, False=Government

    # ATC entries for the schedule
    atc_entries: tuple[AtcEntry, ...]

    # Tax computation
    total_tax_withheld: Decimal  # Item 20 (sum of schedule)
    tax_remitted_previous: Decimal  # Item 21 (if amended)
    total_credits: Decimal  # Item 22

    # Penalties
    surcharge: Decimal
    interest: Decimal
    compromise: Decimal

    @property
    def tax_still_due(self) -> Decimal:
        return self.total_tax_withheld - self.total_credits

    @property
    def total_penalties(self) -> Decimal:
        return self.surcharge + self.interest + self.compromise

    @property
    def total_amount_due(self) -> Decimal:
        return self.tax_still_due + self.total_penalties

    @property
    def period_from(self) -> str:
        month = (self.quarter - 1) * 3 + 1
        return f"{self.year}-{month:02d}-01"

    @property
    def period_to(self) -> str:
        month = self.quarter * 3
        days = {3: 31, 6: 30, 9: 30, 12: 31}
        return f"{self.year}-{month:02d}-{days[month]}"


class Form1601FQGenerator(FormGenerator):
    """Generates BIR Form 1601-FQ."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form1601FQData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "1601FQ"

    @property
    def form_prefix(self) -> str:
        return "frm1601FQ"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields = {}

        # Period
        fields[f"{p}:txtYear"] = str(d.year)
        fields[f"{p}:txtQtr"] = str(d.quarter)

        # Amendment
        fields[f"{p}:optAmend:Y"] = "true" if d.is_amended else "false"
        fields[f"{p}:optAmend:N"] = "false" if d.is_amended else "true"

        # Taxpayer info
        fields.update(self._taxpayer_fields())
        fields[f"{p}:txtLineBus"] = self._taxpayer.line_of_business

        # Category
        fields[f"{p}:optCategory:P"] = "true" if d.is_private else "false"
        fields[f"{p}:optCategory:G"] = "false" if d.is_private else "true"

        # Withheld flag
        has_withheld = d.total_tax_withheld > 0
        fields[f"{p}:TaxWithheld_1"] = "true" if has_withheld else "false"
        fields[f"{p}:TaxWithheld_2"] = "false" if has_withheld else "true"

        # ATC schedule rows
        for i, entry in enumerate(d.atc_entries, 1):
            fields[f"{p}:txtAtcCd{i}"] = entry.atc_code
            fields[f"{p}:txtTaxBase{i}"] = _fmt(entry.tax_base)
            fields[f"{p}:txtTaxRate{i}"] = _fmt(entry.tax_rate)
            fields[f"{p}:txtTaxbeWithHeld{i}"] = _fmt(entry.tax_withheld)

        # Tax computation
        fields[f"{p}:txtTax20"] = _fmt(d.total_tax_withheld)
        fields[f"{p}:txtTax21"] = _fmt(d.tax_remitted_previous)
        fields[f"{p}:txtTax22"] = _fmt(d.total_credits)
        fields[f"{p}:txtTax23"] = _fmt(d.tax_still_due)

        # Penalties
        fields[f"{p}:txtTax25"] = _fmt(d.surcharge)
        fields[f"{p}:txtTax28"] = _fmt(d.interest)
        fields[f"{p}:txtTax29"] = _fmt(d.compromise)
        fields[f"{p}:txtTax30"] = _fmt(d.total_penalties)
        fields[f"{p}:txtTax31"] = _fmt(d.total_amount_due)

        # Email and standard fields
        fields["txtEmail"] = self._taxpayer.email
        fields["txtTaxAgentNo"] = ""
        fields["txtDateIssue"] = ""
        fields["txtDateExpiry"] = ""
        fields["txtFinalFlag"] = "0"
        fields["txtEnroll"] = "N"
        fields["ebirOnlineConfirmUsername"] = ""
        fields["ebirOnlineUsername"] = ""
        fields["ebirOnlineSecret"] = ""

        return fields
