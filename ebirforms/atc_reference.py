"""BIR ATC code reference data.

Loads the master list of 30 ATC codes and provides lookup functions
for mapping ATC codes to forms and vice versa.
"""

import json
from functools import lru_cache
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "bir_atc_reference.json"


@lru_cache(maxsize=1)
def load_atc_reference() -> dict[str, dict]:
    """Load the ATC reference from config/bir_atc_reference.json."""
    with _CONFIG_PATH.open() as f:
        return json.load(f)


def get_forms_for_atc(atc_code: str) -> list[str]:
    """Return the list of BIR form numbers that include this ATC code."""
    ref = load_atc_reference()
    entry = ref.get(atc_code)
    if entry is None:
        return []
    return entry["forms"]


def get_atcs_for_form(form_number: str) -> list[str]:
    """Return all ATC codes that belong to a given form."""
    ref = load_atc_reference()
    return [code for code, entry in ref.items() if form_number in entry["forms"]]


def get_standard_rate(atc_code: str) -> float | None:
    """Return the BIR-standard rate for an ATC code, or None if unknown."""
    ref = load_atc_reference()
    entry = ref.get(atc_code)
    return entry["standard_rate"] if entry else None
