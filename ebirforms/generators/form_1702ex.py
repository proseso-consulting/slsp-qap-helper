"""Generator for BIR Form 1702-EX v2018C (Annual ITR for Corporation - Exempt).

Field prefix: frm1702EX (note: the file internally uses frm1702MX prefix per the HTA,
but eBIRForms saves it as the 1702EX form variant)

This is the simplest 1702 variant - for corporations with income exempt from tax.
Focus on the summary fields; the detailed schedules are too numerous to pre-fill
(2,686 fields) and are better left for manual completion in eBIRForms.
"""

from dataclasses import dataclass
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt(amount: Decimal) -> str:
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class Form1702EXData:
    """Data for BIR Form 1702-EX (Exempt corporation)."""

    year: int
    is_amended: bool
    is_calendar_year: bool

    # Basic income summary
    gross_income: Decimal
    total_deductions: Decimal
    net_income: Decimal

    # The corporation's basis for exemption
    exemption_type: str  # description of exemption basis


class Form1702EXGenerator(FormGenerator):
    """Generates BIR Form 1702-EX (Exempt)."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form1702EXData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "1702EX"

    @property
    def form_prefix(self) -> str:
        return "frm1702EX"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields = {}

        # Fiscal year type
        fields[f"{p}:optCalendar"] = "true" if d.is_calendar_year else "false"
        fields[f"{p}:optFiscal"] = "false" if d.is_calendar_year else "true"
        fields[f"{p}:txtYear"] = str(d.year)

        # Amendment
        fields[f"{p}:optAmend:Y"] = "true" if d.is_amended else "false"
        fields[f"{p}:optAmend:N"] = "false" if d.is_amended else "true"

        # Taxpayer info
        fields.update(self._taxpayer_fields())
        fields[f"{p}:txtLineBus"] = self._taxpayer.line_of_business

        # Income summary
        fields[f"{p}:txtGrossIncome"] = _fmt(d.gross_income)
        fields[f"{p}:txtTotalDeductions"] = _fmt(d.total_deductions)
        fields[f"{p}:txtNetIncome"] = _fmt(d.net_income)

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
