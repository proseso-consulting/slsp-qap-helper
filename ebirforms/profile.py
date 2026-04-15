"""Build eBIRForms profile files from TaxpayerInfo."""

from ebirforms.base import TaxpayerInfo, build_ebirforms_content


def build_profile_content(info: TaxpayerInfo) -> str:
    """Build the XML content for an eBIRForms profile file."""
    tin1, tin2, tin3, tin4 = info.tin_parts
    fields = {
        "fn": info.name,
        "tin1": tin1,
        "tin2": tin2,
        "tin3": tin3,
        "tin4": tin4,
        "rdo": info.rdo_code,
        "lob": info.line_of_business,
        "regAddr": info.address,
        "zip": info.zip_code,
        "telNo": info.telephone,
        "email": info.email,
        "confirmemail": info.email,
        "confirmtin1": tin1,
        "confirmtin2": tin2,
        "confirmtin3": tin3,
        "confirmtin4": tin4,
        "formType": "",
    }
    return build_ebirforms_content(fields)


def profile_filename(info: TaxpayerInfo) -> str:
    """Return the eBIRForms profile filename for a taxpayer."""
    return f"{info.tin.replace('-', '')}.xml"
