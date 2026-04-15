"""Base class for eBIRForms XML generators.

eBIRForms uses a pseudo-XML format with <div> tags containing key-value pairs.
Each field is encoded as: <div>fieldName=valuefieldName=</div>

Example:
    <div>frm0619E:txtMonth=03frm0619E:txtMonth=</div>
    <div>frm0619E:txtTIN1=010frm0619E:txtTIN1=</div>

The field name is repeated as both a prefix and suffix delimiter around the value.
Values are URL-encoded (spaces become %20, etc.).
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote


@dataclass(frozen=True)
class TaxpayerInfo:
    """Taxpayer profile information used across all BIR forms."""

    tin: str  # e.g., "010-318-867-000" (with dashes)
    rdo_code: str  # e.g., "032"
    name: str
    trade_name: str
    address: str
    zip_code: str
    telephone: str
    email: str
    line_of_business: str = ""
    tax_agent_tin: str = ""
    tax_agent_name: str = ""

    @property
    def tin_parts(self) -> tuple[str, str, str, str]:
        """Split TIN into its 4 parts: (XXX, XXX, XXX, branch_code)."""
        parts = self.tin.replace("-", "")
        return parts[0:3], parts[3:6], parts[6:9], parts[9:12]


# eBIRForms field pattern: <div>key=valuekey=</div>
# The value part must be non-greedy (.*?) so it doesn't span across multiple fields on the same line.
_FIELD_PATTERN = re.compile(r"<div>(.+?)=(.*?)\1=</div>")


def parse_ebirforms_file(content: str) -> dict[str, str]:
    """Parse an eBIRForms saved file into a dict of field_name -> value.

    Values are URL-decoded automatically.
    """
    fields = {}
    for match in _FIELD_PATTERN.finditer(content):
        key = match.group(1)
        raw_value = match.group(2)
        fields[key] = unquote(unquote(raw_value))  # double-decode (%2520 -> %20 -> space)
    return fields


def build_ebirforms_content(fields: dict[str, str]) -> str:
    """Build eBIRForms file content from a dict of field_name -> value.

    Values are URL-encoded. The output matches the format that eBIRForms
    can load from its savefile/ directory.
    """
    parts = ["<?xml version='1.0'?>"]
    for key, value in fields.items():
        encoded_value = quote(str(value), safe=".,:-@")
        parts.append(f"            <div>{key}={encoded_value}{key}=</div>")
    parts.append("                        All Rights Reserved BIR 2012.")
    return "".join(parts)


class FormGenerator(ABC):
    """Base class for generating eBIRForms-compatible files.

    Subclasses must implement form_number and build_fields.
    """

    def __init__(self, taxpayer: TaxpayerInfo) -> None:
        self._taxpayer = taxpayer

    @property
    @abstractmethod
    def form_number(self) -> str:
        """BIR form number, e.g., '2550Q', '0619E'."""

    @property
    @abstractmethod
    def form_prefix(self) -> str:
        """Field name prefix used in the eBIRForms file, e.g., 'frm0619E'."""

    @abstractmethod
    def build_fields(self) -> dict[str, str]:
        """Build the field dict for this form.

        Keys should include the form prefix where needed.
        Returns dict of field_name -> value (unencoded).
        """

    def _taxpayer_fields(self) -> dict[str, str]:
        """Common taxpayer fields shared across all forms."""
        p = self.form_prefix
        tin1, tin2, tin3, branch = self._taxpayer.tin_parts
        return {
            f"{p}:txtTIN1": tin1,
            f"{p}:txtTIN2": tin2,
            f"{p}:txtTIN3": tin3,
            f"{p}:txtBranchCode": branch,
            f"{p}:txtRDOCode": self._taxpayer.rdo_code,
            f"{p}:txtTaxpayerName": self._taxpayer.name,
            f"{p}:txtAddress": self._taxpayer.address,
            f"{p}:txtZipCode": self._taxpayer.zip_code,
            f"{p}:txtTelNum": self._taxpayer.telephone,
            "txtEmail": self._taxpayer.email,
        }

    def save(self, output_dir: Path, filename: str | None = None) -> Path:
        """Save the generated file to a directory.

        Args:
            output_dir: Directory to write the file.
            filename: Optional filename. Defaults to eBIRForms naming convention.

        Returns:
            Path to the written file.
        """
        fields = self.build_fields()
        content = build_ebirforms_content(fields)

        if filename is None:
            tin_flat = self._taxpayer.tin.replace("-", "")
            filename = f"{tin_flat}-{self.form_number}.xml"

        output_path = output_dir / filename
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        return output_path
