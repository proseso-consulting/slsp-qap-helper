"""Generator for BIR Form 1603-Q v2018 (Quarterly Remittance of Final WT on Fringe Benefits).

Field prefix: frm1603Q (note: uses 1603Q not 1603Qv2018 for field IDs)
Frequency: Quarterly
Data source: final_wt extractor
"""

from dataclasses import dataclass
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt(amount: Decimal) -> str:
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class FringeBenefitEntry:
    """A schedule row for fringe benefit tax."""

    description: str
    tax_base: Decimal
    tax_withheld: Decimal


@dataclass(frozen=True)
class Form1603QData:
    """Data for BIR Form 1603-Q."""

    year: int
    quarter: int  # 1-4
    is_amended: bool
    is_private: bool

    # Schedule 1: Fringe benefit entries
    schedule_entries: tuple[FringeBenefitEntry, ...]

    # Tax computation
    total_tax_withheld: Decimal  # Item 14 (sum of schedule)
    tax_remitted_previous: Decimal  # Item 15 (if amended)

    # Penalties
    surcharge: Decimal
    interest: Decimal
    compromise: Decimal

    @property
    def tax_still_due(self) -> Decimal:
        return self.total_tax_withheld - self.tax_remitted_previous

    @property
    def total_penalties(self) -> Decimal:
        return self.surcharge + self.interest + self.compromise

    @property
    def total_amount_due(self) -> Decimal:
        return self.tax_still_due + self.total_penalties


class Form1603QGenerator(FormGenerator):
    """Generates BIR Form 1603-Q."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form1603QData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "1603Q"

    @property
    def form_prefix(self) -> str:
        return "frm1603Q"

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

        # Schedule 1: Fringe benefit rows
        for i, entry in enumerate(d.schedule_entries, 1):
            fields[f"{p}:Sched1:txtTaxBase{i}"] = _fmt(entry.tax_base)
            fields[f"{p}:Sched1:txtTaxWithheld{i}"] = _fmt(entry.tax_withheld)

        fields[f"{p}:Sched1:txtTotalTax"] = _fmt(d.total_tax_withheld)

        # Tax computation
        fields[f"{p}:txtTax14"] = _fmt(d.total_tax_withheld)
        fields[f"{p}:txtTax15"] = _fmt(d.tax_remitted_previous)
        fields[f"{p}:txtTax16"] = _fmt(d.tax_still_due)

        # Penalties
        fields[f"{p}:txtTax17"] = _fmt(d.surcharge)
        fields[f"{p}:txtTax18"] = _fmt(d.interest)
        fields[f"{p}:txtTax19"] = _fmt(d.compromise)
        fields[f"{p}:txtTax20"] = _fmt(d.total_penalties)
        fields[f"{p}:txtTax21"] = _fmt(d.total_amount_due)

        # Standard footer fields
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
