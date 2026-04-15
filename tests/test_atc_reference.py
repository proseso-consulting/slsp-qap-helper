# tests/test_atc_reference.py
from ebirforms.atc_reference import get_atcs_for_form, get_forms_for_atc, load_atc_reference


class TestAtcReference:
    def test_load_returns_all_30_codes(self):
        ref = load_atc_reference()
        assert len(ref) == 30

    def test_each_entry_has_required_fields(self):
        ref = load_atc_reference()
        for code, entry in ref.items():
            assert "description" in entry
            assert "standard_rate" in entry
            assert "category" in entry
            assert "forms" in entry
            assert isinstance(entry["standard_rate"], (int, float))
            assert entry["category"] in ("expanded", "final")

    def test_get_forms_for_known_atc(self):
        assert "0619E" in get_forms_for_atc("WC011")
        assert "1601EQ" in get_forms_for_atc("WC011")

    def test_get_forms_for_unknown_atc_returns_empty(self):
        assert get_forms_for_atc("ZZZZ") == []

    def test_get_atcs_for_0619e(self):
        atcs = get_atcs_for_form("0619E")
        assert "WC011" in atcs
        assert "WI011" in atcs
        # Final WT codes should NOT be in 0619E
        assert "WC230" not in atcs
        assert "WV080" not in atcs

    def test_get_atcs_for_0619f(self):
        atcs = get_atcs_for_form("0619F")
        assert "WC230" in atcs
        assert "WV080" in atcs
        # Expanded WT codes should NOT be in 0619F
        assert "WC011" not in atcs

    def test_expanded_category_maps_to_ewt_forms(self):
        ref = load_atc_reference()
        for code, entry in ref.items():
            if entry["category"] == "expanded":
                assert "0619E" in entry["forms"]
                assert "1601EQ" in entry["forms"]
                assert "1604E" in entry["forms"]

    def test_final_category_maps_to_fwt_forms(self):
        ref = load_atc_reference()
        for code, entry in ref.items():
            if entry["category"] == "final":
                assert "0619F" in entry["forms"]
                assert "1601FQ" in entry["forms"]
