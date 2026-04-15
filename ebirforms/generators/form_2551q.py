"""Generator for BIR Form 2551-Q v2018 (Quarterly Percentage Tax Return).

Field prefix: frm2551Qv2018
Frequency: Quarterly
Data source: percentage_tax extractor
"""

from dataclasses import dataclass
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt(amount: Decimal) -> str:
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class PercentageTaxRow:
    """A single tax row (items 14-18, up to 5 rows)."""

    atc_code: str
    atc_description: str
    tax_base: Decimal
    tax_rate: Decimal
    tax_due: Decimal


@dataclass(frozen=True)
class Form2551QData:
    """Data for BIR Form 2551-Q."""

    year: int
    quarter: int  # 1-4
    is_calendar_year: bool
    year_ended_month: int  # 1-12 (usually 12 for calendar year)
    is_amended: bool
    has_tax_treaty: bool

    # Tax rows (up to 5)
    tax_rows: tuple[PercentageTaxRow, ...]

    # Credits
    prior_year_excess: Decimal  # Item 20A
    amended_credits: Decimal  # Item 20B (only for amended returns)

    # Penalties
    surcharge: Decimal
    interest: Decimal
    compromise: Decimal

    @property
    def total_tax_due(self) -> Decimal:
        """Item 19: Sum of all row tax_due amounts."""
        return sum((r.tax_due for r in self.tax_rows), Decimal("0"))

    @property
    def total_credits(self) -> Decimal:
        """Item 20C: 20A + 20B."""
        return self.prior_year_excess + self.amended_credits

    @property
    def tax_still_payable(self) -> Decimal:
        """Item 21: 19 - 20C."""
        return self.total_tax_due - self.total_credits

    @property
    def total_penalties(self) -> Decimal:
        """Item 22D: 22A + 22B + 22C."""
        return self.surcharge + self.interest + self.compromise

    @property
    def total_amount_payable(self) -> Decimal:
        """Item 23: 21 + 22D."""
        return self.tax_still_payable + self.total_penalties


class Form2551QGenerator(FormGenerator):
    """Generates BIR Form 2551-Q."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form2551QData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "2551Q"

    @property
    def form_prefix(self) -> str:
        return "frm2551Qv2018"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields = {}

        # Item 1: Calendar/Fiscal year
        fields[f"{p}:forThe_1"] = "true" if d.is_calendar_year else "false"
        fields[f"{p}:forThe_2"] = "false" if d.is_calendar_year else "true"

        # Item 2: Year ended
        fields[f"{p}:rtnMonth"] = f"{d.year_ended_month:02d}"
        fields[f"{p}:txtYear"] = str(d.year)

        # Item 3: Quarter
        for q in range(1, 5):
            fields[f"{p}:qtr_{q}"] = "true" if q == d.quarter else "false"

        # Item 4: Amended return
        fields[f"{p}:amendedRtn_1"] = "true" if d.is_amended else "false"
        fields[f"{p}:amendedRtn_2"] = "false" if d.is_amended else "true"

        # Item 5: Sheets attached (default 0)
        fields[f"{p}:txtSheets"] = "0"

        # Taxpayer info (items 6-12)
        fields.update(self._taxpayer_fields())
        fields[f"{p}:registeredName"] = self._taxpayer.name
        fields[f"{p}:registeredAddress"] = self._taxpayer.address
        fields[f"{p}:telNo"] = self._taxpayer.telephone
        fields[f"{p}:zipCode"] = self._taxpayer.zip_code
        fields[f"{p}:txtLineofBus"] = self._taxpayer.line_of_business

        # Category (Private/Government)
        fields[f"{p}:optCategory:P"] = "true"
        fields[f"{p}:optCategory:G"] = "false"

        # Tax treaty
        fields[f"{p}:taxTreaty_1"] = "true" if d.has_tax_treaty else "false"
        fields[f"{p}:taxTreaty_2"] = "false" if d.has_tax_treaty else "true"

        # Tax rows (items 14-18)
        row_numbers = [14, 15, 16, 17, 18]
        for i, row in enumerate(d.tax_rows):
            if i >= 5:
                break
            n = row_numbers[i]
            fields[f"{p}:txt{n}"] = row.atc_code
            fields[f"{p}:txtTax{n}B"] = row.atc_description
            fields[f"{p}:txtTax{n}C"] = _fmt(row.tax_base)
            fields[f"{p}:txtTax{n}D"] = _fmt(row.tax_rate)
            fields[f"{p}:txtTax{n}E"] = _fmt(row.tax_due)

        # Totals
        fields[f"{p}:txtTax19"] = _fmt(d.total_tax_due)
        fields[f"{p}:txtTax20A"] = _fmt(d.prior_year_excess)
        fields[f"{p}:txtTax20B"] = _fmt(d.amended_credits)
        fields[f"{p}:txtTax20C"] = _fmt(d.total_credits)
        fields[f"{p}:txtTax21"] = _fmt(d.tax_still_payable)

        # Penalties
        fields[f"{p}:txtTax22A"] = _fmt(d.surcharge)
        fields[f"{p}:txtTax22B"] = _fmt(d.interest)
        fields[f"{p}:txtTax22C"] = _fmt(d.compromise)
        fields[f"{p}:txtTax22D"] = _fmt(d.total_penalties)

        # Total amount payable
        fields[f"{p}:txtTax23"] = _fmt(d.total_amount_payable)

        # Overpayment options (item 24)
        is_overpayment = d.total_amount_payable < 0
        fields[f"{p}:opt23_1"] = "false"  # To be refunded
        fields[f"{p}:opt23_2"] = "true" if is_overpayment else "false"  # Carried over

        # Standard footer
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
