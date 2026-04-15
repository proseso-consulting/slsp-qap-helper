"""Generator for BIR Form 2000 v2018 (Documentary Stamp Tax Declaration/Return).

XML structure reverse-engineered from: extracted_hta/decoded/renamed/forms_BIR-Form2000v2018.hta

Form 2000 is filed per transaction. Each filing covers one month/year period and
one or more DST line items (Schedule 1), each identified by an ATC code (DS101-DS132).

Field mapping (from saveXML analysis):

    frm2000:txtMonth            -> Return period month (MM, select-one, "01".."12")
    frm2000:txtYear             -> Return period year (YYYY)
    frm2000:AmendedRtn_1        -> Is amended? radio (true/false)
    frm2000:AmendedRtn_2        -> Not amended radio (true/false)
    frm2000:txtSheets           -> Number of sheets attached (default 0)

    frm2000:txtTIN1/2/3         -> TIN parts
    frm2000:txtBranchCode       -> Branch code
    frm2000:txtRDOCode          -> RDO code (select-one)
    frm2000:txtTaxpayerName     -> Taxpayer name
    frm2000:txtLineBus          -> Line of business
    frm2000:txtAddress          -> Address (combined with txtAddress2 in XML)
    frm2000:txtAddress2         -> Address overflow (empty string keeps same div)
    frm2000:txtZipCode          -> ZIP code
    frm2000:txtTelNum           -> Telephone
    txtEmail                    -> Email (no prefix)

    frm2000:optParty_1/2/3      -> Other party radios: Creditor / Debtor / None
    frm2000:optMode_1/2/3       -> Mode of affixture: eDST / Constructive / Loose Stamps

    frm2000:txtOtherName        -> Other party name part 1 (escape-encoded)
    frm2000:txtOtherName2       -> Other party name part 2 (escape-encoded overflow)
    frm2000:txtOtherTIN         -> Other party TIN

    -- Schedule 1 (DST line items, up to N rows) --
    drpATCCode{i}               -> ATC code dropdown (select-one, e.g. "DS101")
    frm2000:sched1:txtTaxBase{i}-> Tax base amount (formatted with commas)
    frm2000:sched1:txtTaxRate{i}-> Tax rate description (disabled, populated by JS)
    frm2000:sched1:txtTaxDue{i} -> Tax due for this line (formatted with commas)
    frm2000:sched1:txtTotalDue1 -> Sum of all txtTaxDue rows (Item 14)

    -- Special ATC modifiers --
    frm2000:numOfDays           -> Term in days (DS106 only)
    frm2000:numOfMonths         -> Term in months (DS130 only)
    frm2000:numOfMonths131      -> Term in months (DS131 only)
    frm2000:numOfMonths132      -> Term in months (DS132 only)

    -- Tax computation (Part III) --
    frm2000:txtTax14            -> Total tax due from Schedule 1
    frm2000:txtTax15A           -> Add: Surcharge
    frm2000:txtTax15B           -> Add: Interest
    frm2000:txtTax15C           -> Add: Compromise
    frm2000:txtTax15D           -> Total penalties (15A + 15B + 15C)
    frm2000:txtTax16            -> Total amount payable (14 + 15D)
    frm2000:txtTax17A           -> Less: Tax credit/refund
    frm2000:txtTax17B           -> Less: Others
    frm2000:txtTax17C           -> Less: (another credit)
    frm2000:txtTax17D           -> Total credits (17A + 17B + 17C)
    frm2000:txtTax18            -> Tax still due (16 - 17D)
    frm2000:txtTax19            -> Total amount payable (same as 18 if no credits)

    -- Page 2 TIN repeat --
    frm2000:txtPg2TIN1/2/3      -> Page 2 TIN
    frm2000:txtPg2BranchCode    -> Page 2 branch code
    frm2000:txtPg2TaxpayerName  -> Page 2 taxpayer name

    -- Payment details --
    frm2000:txtAgency20/21/22/23    -> Payment bank / drawee
    frm2000:txtNumber20/21/22/23    -> Payment reference number
    frm2000:txtDate20/21/22/23      -> Payment date
    frm2000:txtAmount20/21/22/23    -> Payment amount
    frm2000:txtParticular36         -> Particular for item 36
    frm2000:txtParticular23         -> Particular for item 23

    txtTaxAgentNo               -> Tax agent accreditation number
    txtDateIssue                -> Agent accreditation issue date
    txtDateExpiry               -> Agent accreditation expiry date
    txtFinalFlag                -> 0 = not final
    txtEnroll                   -> N = not enrolled

ATC codes:
    DS010  General (manual)
    DS101  Original issue of shares
    DS102  Sales/transfers of shares
    DS103  Bank checks
    DS104  Certificates of profit or interest
    DS105  Mortgages, pledges, deeds of trust
    DS106  Bonds, debentures, certificates of indebtedness (term-based)
    DS107  Deeds of sales, conveyances
    DS108  Charters, parties
    DS109  Powers of attorney
    DS110  Leases and other hiring agreements
    DS111  Warehouse receipts
    DS112  Jai-alai, horse race tickets; lotto, other authorized numbers games
    DS113  Bills of lading or receipts (between points in Philippines)
    DS114  Bills of exchange, drafts
    DS115  Acceptance of bills of exchange
    DS116  Foreign bills of exchange, letters of credit
    DS117  Policies of annuities or other instruments by which annuities are made payable
    DS118  Pre-need plans
    DS119  Certificates
    DS120  Warehousing receipts for property held as collateral security
    DS121  Proxies for voting at any election
    DS122  Powers of attorney to vote at any election
    DS123  Renewal of WT or indemnity bond
    DS124  Indemnity bonds
    DS125  Assignments and renewals of certain instruments
    DS126  Bills of lading or receipts (from a foreign country)
    DS127  Charter parties and similar instruments
    DS128  Manifests
    DS129  Passage tickets
    DS130  Life insurance policies (term-based)
    DS131  Non-life insurance policies (term-based)
    DS132  Pre-need plans - family benefit (term-based)
"""

from dataclasses import dataclass, field
from decimal import Decimal

from ebirforms.base import FormGenerator, TaxpayerInfo


def _fmt_money(amount: Decimal) -> str:
    """Format decimal as eBIRForms money string: '20,000.00'."""
    return f"{amount:,.2f}"


# Mode of affixture values
MODE_EDST = "Mode1"  # eDST System
MODE_CONSTRUCTIVE = "Mode2"  # Constructive Affixture
MODE_LOOSE = "Mode3"  # Loose Stamps

# Other party values
PARTY_CREDITOR = "Creditor"
PARTY_DEBTOR = "Debtor"
PARTY_NONE = "None"


@dataclass(frozen=True)
class DstLineItem:
    """One DST entry in Schedule 1.

    atc_code: ATC code string, e.g. "DS101", "DS107".
    tax_base: Taxable amount (PHP).
    tax_rate: Rate description as shown in the form (populated by the caller;
              eBIRForms normally fills this automatically from the ATC lookup).
    tax_due:  Computed tax due for this line.
    """

    atc_code: str
    tax_base: Decimal
    tax_rate: str
    tax_due: Decimal


@dataclass(frozen=True)
class Form2000Data:
    """Data needed to generate BIR Form 2000 v2018 (Documentary Stamp Tax)."""

    year: int
    month: int  # 1-12
    is_amended: bool

    # Schedule 1 line items (at least one required)
    line_items: tuple[DstLineItem, ...]

    # Mode of affixture: use MODE_* constants
    mode: str = MODE_CONSTRUCTIVE

    # Other party to the transaction
    other_party: str = PARTY_NONE  # use PARTY_* constants
    other_party_name: str = ""
    other_party_tin: str = ""

    # Penalties
    surcharge: Decimal = field(default_factory=lambda: Decimal("0.00"))
    interest: Decimal = field(default_factory=lambda: Decimal("0.00"))
    compromise: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Credits
    credit_17a: Decimal = field(default_factory=lambda: Decimal("0.00"))
    credit_17b: Decimal = field(default_factory=lambda: Decimal("0.00"))
    credit_17c: Decimal = field(default_factory=lambda: Decimal("0.00"))

    # Special ATC modifiers (used by eDST system validation; pass 0 if not applicable)
    num_of_days: int = 0  # DS106: term in days
    num_of_months: int = 0  # DS130: term in months
    num_of_months_131: int = 0  # DS131: term in months
    num_of_months_132: int = 0  # DS132: term in months

    sheets_attached: int = 0

    @property
    def total_tax_due(self) -> Decimal:
        """Item 14: Total tax due (sum of all Schedule 1 lines)."""
        return sum((item.tax_due for item in self.line_items), Decimal("0.00"))

    @property
    def total_penalties(self) -> Decimal:
        """Item 15D: Total penalties (surcharge + interest + compromise)."""
        return self.surcharge + self.interest + self.compromise

    @property
    def total_amount_payable(self) -> Decimal:
        """Item 16: Total amount payable (Item 14 + Item 15D)."""
        return self.total_tax_due + self.total_penalties

    @property
    def total_credits(self) -> Decimal:
        """Item 17D: Total tax credits."""
        return self.credit_17a + self.credit_17b + self.credit_17c

    @property
    def tax_still_due(self) -> Decimal:
        """Item 18: Tax still due (Item 16 - Item 17D)."""
        return self.total_amount_payable - self.total_credits

    @property
    def total_amount_payable_19(self) -> Decimal:
        """Item 19: Total amount payable (same as tax_still_due)."""
        return self.tax_still_due


class Form2000Generator(FormGenerator):
    """Generates BIR Form 2000 v2018 (Documentary Stamp Tax Declaration/Return)."""

    def __init__(self, taxpayer: TaxpayerInfo, data: Form2000Data) -> None:
        super().__init__(taxpayer)
        self._data = data

    @property
    def form_number(self) -> str:
        return "2000v2018"

    @property
    def form_prefix(self) -> str:
        return "frm2000"

    def build_fields(self) -> dict[str, str]:
        p = self.form_prefix
        d = self._data

        fields: dict[str, str] = {}

        # Return period
        fields[f"{p}:txtMonth"] = f"{d.month:02d}"
        fields[f"{p}:txtYear"] = str(d.year)

        # Amendment radios
        fields[f"{p}:AmendedRtn_1"] = "true" if d.is_amended else "false"
        fields[f"{p}:AmendedRtn_2"] = "false" if d.is_amended else "true"

        # Sheets attached
        fields[f"{p}:txtSheets"] = str(d.sheets_attached)

        # Taxpayer identity fields (TIN, RDO, name, address, etc.)
        fields.update(self._taxpayer_fields())
        fields[f"{p}:txtLineBus"] = self._taxpayer.line_of_business
        fields[f"{p}:txtAddress2"] = ""

        # Page 2 TIN repeat
        tin1, tin2, tin3, branch = self._taxpayer.tin_parts
        fields[f"{p}:txtPg2TIN1"] = tin1
        fields[f"{p}:txtPg2TIN2"] = tin2
        fields[f"{p}:txtPg2TIN3"] = tin3
        fields[f"{p}:txtPg2BranchCode"] = branch
        fields[f"{p}:txtPg2TaxpayerName"] = self._taxpayer.name

        # Mode of affixture radios
        fields[f"{p}:optMode_1"] = "true" if d.mode == MODE_EDST else "false"
        fields[f"{p}:optMode_2"] = "true" if d.mode == MODE_CONSTRUCTIVE else "false"
        fields[f"{p}:optMode_3"] = "true" if d.mode == MODE_LOOSE else "false"

        # Other party radios
        fields[f"{p}:optParty_1"] = "true" if d.other_party == PARTY_CREDITOR else "false"
        fields[f"{p}:optParty_2"] = "true" if d.other_party == PARTY_DEBTOR else "false"
        fields[f"{p}:optParty_3"] = "true" if d.other_party == PARTY_NONE else "false"

        # Other party name and TIN
        fields[f"{p}:txtOtherName"] = d.other_party_name
        fields[f"{p}:txtOtherName2"] = ""
        fields[f"{p}:txtOtherTIN"] = d.other_party_tin

        # Schedule 1: DST line items
        for i, item in enumerate(d.line_items):
            fields[f"drpATCCode{i}"] = item.atc_code
            fields[f"{p}:sched1:txtTaxBase{i}"] = _fmt_money(item.tax_base)
            fields[f"{p}:sched1:txtTaxRate{i}"] = item.tax_rate
            fields[f"{p}:sched1:txtTaxDue{i}"] = _fmt_money(item.tax_due)

        fields[f"{p}:sched1:txtTotalDue1"] = _fmt_money(d.total_tax_due)

        # Special ATC term fields
        fields[f"{p}:numOfDays"] = str(d.num_of_days)
        fields[f"{p}:numOfMonths"] = str(d.num_of_months)
        fields[f"{p}:numOfMonths131"] = str(d.num_of_months_131)
        fields[f"{p}:numOfMonths132"] = str(d.num_of_months_132)

        # Tax computation (Part III)
        fields[f"{p}:txtTax14"] = _fmt_money(d.total_tax_due)
        fields[f"{p}:txtTax15A"] = _fmt_money(d.surcharge)
        fields[f"{p}:txtTax15B"] = _fmt_money(d.interest)
        fields[f"{p}:txtTax15C"] = _fmt_money(d.compromise)
        fields[f"{p}:txtTax15D"] = _fmt_money(d.total_penalties)
        fields[f"{p}:txtTax16"] = _fmt_money(d.total_amount_payable)
        fields[f"{p}:txtTax17A"] = _fmt_money(d.credit_17a)
        fields[f"{p}:txtTax17B"] = _fmt_money(d.credit_17b)
        fields[f"{p}:txtTax17C"] = _fmt_money(d.credit_17c)
        fields[f"{p}:txtTax17D"] = _fmt_money(d.total_credits)
        fields[f"{p}:txtTax18"] = _fmt_money(d.tax_still_due)
        fields[f"{p}:txtTax19"] = _fmt_money(d.total_amount_payable_19)

        # Payment details (empty - filled in eBIRForms after payment)
        for item in ("20", "21", "22"):
            fields[f"{p}:txtAgency{item}"] = ""
            fields[f"{p}:txtNumber{item}"] = ""
            fields[f"{p}:txtDate{item}"] = ""
            fields[f"{p}:txtAmount{item}"] = ""

        fields[f"{p}:txtParticular36"] = ""
        fields[f"{p}:txtAgency23"] = ""
        fields[f"{p}:txtNumber23"] = ""
        fields[f"{p}:txtDate23"] = ""
        fields[f"{p}:txtAmount23"] = ""
        fields[f"{p}:txtParticular23"] = ""

        # Tax agent (empty if no agent)
        fields["txtTaxAgentNo"] = ""
        fields["txtDateIssue"] = ""
        fields["txtDateExpiry"] = ""

        # Pagination - always start at page 1
        fields[f"{p}:txtCurrentPage"] = "1"

        # Flags
        fields["txtFinalFlag"] = "0"
        fields["txtEnroll"] = "N"
        fields["ebirOnlineSecret"] = ""
        fields["ebirOnlineUsername"] = ""

        return fields
