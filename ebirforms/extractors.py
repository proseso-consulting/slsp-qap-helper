"""Extract tax data from Odoo AML records into form-ready summaries.

These functions transform raw Odoo data (from odoo_client.fetch_tax_lines_by_atc)
into aggregated summaries grouped by ATC code, ready to feed into form generators.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from ebirforms.atc_reference import load_atc_reference


@dataclass(frozen=True)
class EwtAtcTotal:
    """Aggregated withholding tax data for a single ATC code."""

    atc_code: str
    tax_base: Decimal
    tax_withheld: Decimal
    tax_rate: Decimal


@dataclass(frozen=True)
class VatSummary:
    """Aggregated VAT data for a period."""

    output_vat: Decimal
    vatable_sales: Decimal
    zero_rated_sales: Decimal
    exempt_sales: Decimal
    input_vat: Decimal
    total_purchases: Decimal
    sales_to_govt: Decimal
    output_tax_govt: Decimal = Decimal(0)


def extract_vat_summary(raw_vat: dict) -> VatSummary:
    """Convert raw Odoo VAT data into a VatSummary.

    Accepts the dict from odoo_client.fetch_vat_summary().
    """
    return VatSummary(
        output_vat=Decimal(str(raw_vat.get("output_vat", 0))),
        vatable_sales=Decimal(str(raw_vat.get("vatable_sales", 0))),
        zero_rated_sales=Decimal(str(raw_vat.get("zero_rated_sales", 0))),
        exempt_sales=Decimal(str(raw_vat.get("exempt_sales", 0))),
        input_vat=Decimal(str(raw_vat.get("input_vat", 0))),
        total_purchases=Decimal(str(raw_vat.get("total_purchases", 0))),
        sales_to_govt=Decimal(str(raw_vat.get("sales_to_govt", 0))),
    )


@dataclass(frozen=True)
class IncomeStatementSummary:
    """Aggregated P&L data for income tax forms."""

    revenue: Decimal
    cost_of_sales: Decimal
    non_operating_income: Decimal
    deductions: Decimal

    @property
    def gross_income(self) -> Decimal:
        return self.revenue - self.cost_of_sales

    @property
    def net_taxable_income(self) -> Decimal:
        return self.gross_income + self.non_operating_income - self.deductions


def extract_income_statement(raw: dict) -> IncomeStatementSummary:
    """Convert raw Odoo income statement data into IncomeStatementSummary."""
    return IncomeStatementSummary(
        revenue=Decimal(str(raw.get("revenue", 0))),
        cost_of_sales=Decimal(str(raw.get("cost_of_sales", 0))),
        non_operating_income=Decimal(str(raw.get("non_operating_income", 0))),
        deductions=Decimal(str(raw.get("deductions", 0))),
    )


def extract_ewt_summary(
    raw_lines: list[dict],
    *,
    category: str | None = None,
) -> list[EwtAtcTotal]:
    """Aggregate raw AML tax lines by ATC code.

    Args:
        raw_lines: Output from odoo_client.fetch_tax_lines_by_atc().
            Each dict has: atc_code, tax_rate, tax_name, tax_base, tax_amount.
        category: Filter to "expanded" or "final" ATC codes per the reference.
            None means no filter (return all).

    Returns:
        List of EwtAtcTotal, one per ATC code, sorted by atc_code.
    """
    ref = load_atc_reference()

    filtered = raw_lines
    if category is not None:
        allowed_atcs = {code for code, entry in ref.items() if entry["category"] == category}
        filtered = [line for line in raw_lines if line["atc_code"] in allowed_atcs]

    groups: dict[str, dict] = defaultdict(lambda: {"base": Decimal(0), "withheld": Decimal(0), "rate": Decimal(0)})
    for line in filtered:
        atc = line["atc_code"]
        groups[atc]["base"] += Decimal(str(line["tax_base"]))
        groups[atc]["withheld"] += Decimal(str(line["tax_amount"]))
        groups[atc]["rate"] = Decimal(str(line["tax_rate"]))

    return sorted(
        [
            EwtAtcTotal(
                atc_code=atc,
                tax_base=data["base"],
                tax_withheld=data["withheld"],
                tax_rate=data["rate"],
            )
            for atc, data in groups.items()
        ],
        key=lambda x: x.atc_code,
    )
