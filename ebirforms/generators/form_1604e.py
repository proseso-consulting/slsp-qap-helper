"""Generator for BIR Form 1604-E v2018 (Annual Information Return of Creditable Income
Taxes Withheld - Expanded).

XML structure reverse-engineered from:
  extracted_hta/decoded/renamed/forms_BIR-Form1604Ev2018.hta

Form prefix: frm1604e  (not frm1604Ev2018 - the prefix in the HTA field IDs is frm1604e)

Key differences from 1601-EQ:
  - Annual return; no quarter selector
  - Taxpayer name field is txtWthhldngAgntsNme (withholding agent's name)
  - Amendment radio: frm1604e:AmendedRtn_1 (Yes) / _2 (No)
  - Category radio:  frm1604e:WthldngAgntCtgry_1 (Private) / _2 (Government)
  - Top withholding agent indicator: frm1604e:TpWthldngAgnt_1 (Yes) / _2 (No)
  - Sheets field: txtSheets (not txtNoSheets)
  - No ATC table; instead has two remittance schedules:
      Schedule 1 - 4 rows (one per quarter) from 1601-EQ remittances
      Schedule 2 - 12 rows (one per month) from 0619-E remittances
  - Each schedule row has: RemDate, BankCode, TRANo, TaxWithheld, Penalties,
    TotRemAmt (auto-computed: TaxWithheld + Penalties)
  - Schedule totals: txtSched1TaxWithheldTtl / PenaltiesTtl / TotRemAmtTtl
                     txtSched2TaxWithheldTtl / PenaltiesTtl / TotRemAmtTtl

Field reference:
    frm1604e:txtYear                -> Return period year (YYYY)
    frm1604e:AmendedRtn_1/2        -> Amended return (radio: Yes / No)
    frm1604e:txtSheets              -> Number of sheets attached
    frm1604e:txtTIN1/2/3            -> TIN parts
    frm1604e:txtBranchCode          -> Branch code
    frm1604e:txtRDOCode             -> RDO code
    frm1604e:txtWthhldngAgntsNme    -> Withholding agent's name
    frm1604e:txtAddress             -> Address (merged with txtAddress2 on save)
    frm1604e:txtAddress2            -> Address continuation
    frm1604e:txtZipCode             -> ZIP code
    frm1604e:txtTelNum              -> Telephone
    frm1604e:WthldngAgntCtgry_1/2  -> Category: Private / Government
    frm1604e:TpWthldngAgnt_1/2     -> Top withholding agent: Yes / No
    frm1604e:txtLineBus             -> Line of business
    txtEmail                        -> Email (no prefix)

    Schedule 1 (1601-EQ remittances, rows 1-4 = Q1-Q4):
    frm1604e:txtSched1RemDate{n}    -> Date of remittance (MM/DD/YYYY)
    frm1604e:txtSched1BankCode{n}   -> Drawee bank / bank code / agency
    frm1604e:txtSched1TRANo{n}      -> TRA/eROR/eAR number
    frm1604e:txtSched1TaxWithheld{n}-> Taxes withheld
    frm1604e:txtSched1Penalties{n}  -> Penalties
    frm1604e:txtSched1TotRemAmt{n}  -> Total amount remitted (auto = withheld + penalties)
    frm1604e:txtSched1TaxWithheldTtl-> Total taxes withheld (Schedule 1)
    frm1604e:txtSched1PenaltiesTtl  -> Total penalties (Schedule 1)
    frm1604e:txtSched1TotRemAmtTtl  -> Grand total remitted (Schedule 1)

    Schedule 2 (0619-E remittances, rows 1-12 = Jan-Dec):
    frm1604e:txtSched2RemDate{n}    -> Date of remittance (MM/DD/YYYY)
    frm1604e:txtSched2BankCode{n}   -> Drawee bank / bank code / agency
    frm1604e:txtSched2TRANo{n}      -> TRA/eROR/eAR number
    frm1604e:txtSched2TaxWithheld{n}-> Taxes withheld
    frm1604e:txtSched2Penalties{n}  -> Penalties
    frm1604e:txtSched2TotRemAmt{n}  -> Total amount remitted (auto = withheld + penalties)
    frm1604e:txtSched2TaxWithheldTtl-> Total taxes withheld (Schedule 2)
    frm1604e:txtSched2PenaltiesTtl  -> Total penalties (Schedule 2)
    frm1604e:txtSched2TotRemAmtTtl  -> Grand total remitted (Schedule 2)

    Page 2 header (mirrors page 1 for printing):
    frm1604e:txtPg2TIN1/2/3         -> TIN parts
    frm1604e:txtPg2BranchCode       -> Branch code
    frm1604e:txtPg2TaxpayerName     -> Taxpayer name

    Misc:
    frm1604e:txtCurrentPage         -> Always set to 1 on save
    txtFinalFlag                    -> 0 = not final
    txtEnroll                       -> N = not enrolled
"""

from dataclasses import dataclass, field
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt_money(amount: Decimal) -> str:
    """Format decimal as eBIRForms money string: '20,000.00'."""
    return f"{amount:,.2f}"


@dataclass(frozen=True)
class RemittanceRow:
    """One row in Schedule 1 or Schedule 2.

    For Schedule 1, rows 1-4 represent Q1-Q4 of 1601-EQ remittances.
    For Schedule 2, rows 1-12 represent Jan-Dec of 0619-E remittances.
    """

    rem_date: str  # MM/DD/YYYY, empty if no remittance
    bank_code: str  # drawee bank name / agency, empty if none
    tra_no: str  # TRA/eROR/eAR number, empty if none
    tax_withheld: Decimal
    penalties: Decimal

    @property
    def total_remitted(self) -> Decimal:
        """Total amount remitted = tax withheld + penalties."""
        return self.tax_withheld + self.penalties

    @classmethod
    def empty(cls) -> "RemittanceRow":
        """Blank row with zero amounts."""
        return cls(
            rem_date="",
            bank_code="",
            tra_no="",
            tax_withheld=Decimal("0.00"),
            penalties=Decimal("0.00"),
        )


def _zero_rows(count: int) -> tuple["RemittanceRow", ...]:
    return tuple(RemittanceRow.empty() for _ in range(count))


@dataclass(frozen=True)
class Form1604EData:
    """Data needed to generate BIR Form 1604-E v2018."""

    year: int
    is_amended: bool
    is_private: bool  # True = Private sector, False = Government
    is_top_withholding_agent: bool  # Top withholding agent designation

    # Schedule 1: 4 rows, one per quarter (1601-EQ quarterly remittances)
    # Indices 0-3 correspond to Q1-Q4.
    sched1_rows: tuple[RemittanceRow, ...] = field(default_factory=lambda: _zero_rows(4))

    # Schedule 2: 12 rows, one per month (0619-E monthly remittances)
    # Indices 0-11 correspond to Jan-Dec.
    sched2_rows: tuple[RemittanceRow, ...] = field(default_factory=lambda: _zero_rows(12))

    no_sheets: int = 0

    def __post_init__(self) -> None:
        if len(self.sched1_rows) != 4:
            raise ValueError(f"sched1_rows must have exactly 4 entries, got {len(self.sched1_rows)}")
        if len(self.sched2_rows) != 12:
            raise ValueError(f"sched2_rows must have exactly 12 entries, got {len(self.sched2_rows)}")

    @property
    def sched1_tax_withheld_total(self) -> Decimal:
        return sum((r.tax_withheld for r in self.sched1_rows), Decimal("0.00"))

    @property
    def sched1_penalties_total(self) -> Decimal:
        return sum((r.penalties for r in self.sched1_rows), Decimal("0.00"))

    @property
    def sched1_total_remitted(self) -> Decimal:
        return self.sched1_tax_withheld_total + self.sched1_penalties_total

    @property
    def sched2_tax_withheld_total(self) -> Decimal:
        return sum((r.tax_withheld for r in self.sched2_rows), Decimal("0.00"))

    @property
    def sched2_penalties_total(self) -> Decimal:
        return sum((r.penalties for r in self.sched2_rows), Decimal("0.00"))

    @property
    def sched2_total_remitted(self) -> Decimal:
        return self.sched2_tax_withheld_total + self.sched2_penalties_total


class Form1604EGenerator(FormGenerator):
    """Generates BIR Form 1604-E v2018."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form1604EData) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "1604Ev2018"

    @property
    def form_prefix(self) -> str:
        # The HTA uses "frm1604e" as the field prefix (lowercase e, no "v2018")
        return "frm1604e"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields: dict[str, str] = {}

        # Return period
        fields[f"{p}:txtYear"] = str(d.year)

        # Amendment radio (AmendedRtn_1 = Yes, _2 = No)
        fields[f"{p}:AmendedRtn_1"] = "true" if d.is_amended else "false"
        fields[f"{p}:AmendedRtn_2"] = "false" if d.is_amended else "true"

        # Number of sheets
        fields[f"{p}:txtSheets"] = str(d.no_sheets)

        # TIN and address (1604-E uses txtWthhldngAgntsNme instead of txtTaxpayerName)
        tin1, tin2, tin3, branch = self._taxpayer.tin_parts
        fields[f"{p}:txtTIN1"] = tin1
        fields[f"{p}:txtTIN2"] = tin2
        fields[f"{p}:txtTIN3"] = tin3
        fields[f"{p}:txtBranchCode"] = branch
        fields[f"{p}:txtRDOCode"] = self._taxpayer.rdo_code
        fields[f"{p}:txtWthhldngAgntsNme"] = self._taxpayer.name
        fields[f"{p}:txtAddress"] = self._taxpayer.address
        # txtAddress2 is merged into txtAddress by saveXML; keep empty
        fields[f"{p}:txtAddress2"] = ""
        fields[f"{p}:txtZipCode"] = self._taxpayer.zip_code
        fields[f"{p}:txtTelNum"] = self._taxpayer.telephone
        fields["txtEmail"] = self._taxpayer.email
        fields[f"{p}:txtLineBus"] = self._taxpayer.line_of_business

        # Category radio (WthldngAgntCtgry_1 = Private, _2 = Government)
        fields[f"{p}:WthldngAgntCtgry_1"] = "true" if d.is_private else "false"
        fields[f"{p}:WthldngAgntCtgry_2"] = "false" if d.is_private else "true"

        # Top withholding agent radio (TpWthldngAgnt_1 = Yes, _2 = No)
        fields[f"{p}:TpWthldngAgnt_1"] = "true" if d.is_top_withholding_agent else "false"
        fields[f"{p}:TpWthldngAgnt_2"] = "false" if d.is_top_withholding_agent else "true"

        # Schedule 1: 4 rows (Q1-Q4 from 1601-EQ)
        for idx, row in enumerate(d.sched1_rows, start=1):
            fields[f"{p}:txtSched1RemDate{idx}"] = row.rem_date
            fields[f"{p}:txtSched1BankCode{idx}"] = row.bank_code
            fields[f"{p}:txtSched1TRANo{idx}"] = row.tra_no
            fields[f"{p}:txtSched1TaxWithheld{idx}"] = _fmt_money(row.tax_withheld)
            fields[f"{p}:txtSched1Penalties{idx}"] = _fmt_money(row.penalties)
            fields[f"{p}:txtSched1TotRemAmt{idx}"] = _fmt_money(row.total_remitted)

        fields[f"{p}:txtSched1TaxWithheldTtl"] = _fmt_money(d.sched1_tax_withheld_total)
        fields[f"{p}:txtSched1PenaltiesTtl"] = _fmt_money(d.sched1_penalties_total)
        fields[f"{p}:txtSched1TotRemAmtTtl"] = _fmt_money(d.sched1_total_remitted)

        # Schedule 2: 12 rows (Jan-Dec from 0619-E)
        for idx, row in enumerate(d.sched2_rows, start=1):
            fields[f"{p}:txtSched2RemDate{idx}"] = row.rem_date
            fields[f"{p}:txtSched2BankCode{idx}"] = row.bank_code
            fields[f"{p}:txtSched2TRANo{idx}"] = row.tra_no
            fields[f"{p}:txtSched2TaxWithheld{idx}"] = _fmt_money(row.tax_withheld)
            fields[f"{p}:txtSched2Penalties{idx}"] = _fmt_money(row.penalties)
            fields[f"{p}:txtSched2TotRemAmt{idx}"] = _fmt_money(row.total_remitted)

        fields[f"{p}:txtSched2TaxWithheldTtl"] = _fmt_money(d.sched2_tax_withheld_total)
        fields[f"{p}:txtSched2PenaltiesTtl"] = _fmt_money(d.sched2_penalties_total)
        fields[f"{p}:txtSched2TotRemAmtTtl"] = _fmt_money(d.sched2_total_remitted)

        # Page 2 header (mirrors page 1; used for the second printed page)
        fields[f"{p}:txtPg2TIN1"] = tin1
        fields[f"{p}:txtPg2TIN2"] = tin2
        fields[f"{p}:txtPg2TIN3"] = tin3
        fields[f"{p}:txtPg2BranchCode"] = branch
        fields[f"{p}:txtPg2TaxpayerName"] = self._taxpayer.name

        # Page navigation field (always 1 on save, per HTA saveXML logic)
        fields[f"{p}:txtCurrentPage"] = "1"

        # Global flags
        fields["txtFinalFlag"] = "0"
        fields["txtEnroll"] = "N"
        fields["ebirOnlineConfirmUsername"] = ""
        fields["ebirOnlineUsername"] = ""
        fields["ebirOnlineSecret"] = ""
        fields["driveSelectTPExport"] = ""

        return fields
