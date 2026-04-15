"""Generator for BIR Form 1702-MX v2018C (Annual ITR for Corporation - Mixed Income).

Field prefix: frm1702MX
This form is for corporations with both taxable AND exempt income.
It's the most complex 1702 variant (963 fields in the HTA).

Focus on the main tax computation; detailed schedules are left for eBIRForms.
"""

from dataclasses import dataclass
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt(amount: Decimal) -> str:
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class Form1702MXData:
    """Data for BIR Form 1702-MX (Mixed income corporation)."""

    year: int
    is_amended: bool
    is_calendar_year: bool

    # Regular (taxable) income
    regular_gross_income: Decimal
    regular_deductions: Decimal
    regular_net_taxable: Decimal
    regular_tax_rate: Decimal  # 25% or 20% for MSME
    regular_tax_due: Decimal

    # Special/exempt income
    exempt_gross_income: Decimal
    exempt_deductions: Decimal
    exempt_net_income: Decimal

    # Credits
    prior_year_excess: Decimal
    quarterly_payments: Decimal
    creditable_wt: Decimal

    # Penalties
    surcharge: Decimal
    interest: Decimal
    compromise: Decimal

    @property
    def total_credits(self) -> Decimal:
        return self.prior_year_excess + self.quarterly_payments + self.creditable_wt

    @property
    def tax_still_due(self) -> Decimal:
        return self.regular_tax_due - self.total_credits

    @property
    def total_penalties(self) -> Decimal:
        return self.surcharge + self.interest + self.compromise

    @property
    def total_amount_due(self) -> Decimal:
        return self.tax_still_due + self.total_penalties


class Form1702MXGenerator(FormGenerator):
    """Generates BIR Form 1702-MX (Mixed income)."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form1702MXData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "1702MX"

    @property
    def form_prefix(self) -> str:
        return "frm1702MX"

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

        # Regular taxable income
        fields[f"{p}:txtRegGrossIncome"] = _fmt(d.regular_gross_income)
        fields[f"{p}:txtRegDeductions"] = _fmt(d.regular_deductions)
        fields[f"{p}:txtRegNetTaxable"] = _fmt(d.regular_net_taxable)
        fields[f"{p}:txtRegTaxRate"] = _fmt(d.regular_tax_rate)
        fields[f"{p}:txtRegTaxDue"] = _fmt(d.regular_tax_due)

        # Exempt income
        fields[f"{p}:txtExemptGrossIncome"] = _fmt(d.exempt_gross_income)
        fields[f"{p}:txtExemptDeductions"] = _fmt(d.exempt_deductions)
        fields[f"{p}:txtExemptNetIncome"] = _fmt(d.exempt_net_income)

        # Credits
        fields[f"{p}:txtPriorYearExcess"] = _fmt(d.prior_year_excess)
        fields[f"{p}:txtQuarterlyPayments"] = _fmt(d.quarterly_payments)
        fields[f"{p}:txtCreditableWT"] = _fmt(d.creditable_wt)
        fields[f"{p}:txtTotalCredits"] = _fmt(d.total_credits)
        fields[f"{p}:txtTaxStillDue"] = _fmt(d.tax_still_due)

        # Penalties
        fields[f"{p}:txtSurcharge"] = _fmt(d.surcharge)
        fields[f"{p}:txtInterest"] = _fmt(d.interest)
        fields[f"{p}:txtCompromise"] = _fmt(d.compromise)
        fields[f"{p}:txtTotalPenalties"] = _fmt(d.total_penalties)
        fields[f"{p}:txtTotalAmountDue"] = _fmt(d.total_amount_due)

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
