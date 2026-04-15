# tests/test_ebirforms_profile.py
from ebirforms.base import TaxpayerInfo
from ebirforms.profile import build_profile_content, profile_filename


class TestBuildProfileContent:
    def test_basic_profile(self):
        info = TaxpayerInfo(
            tin="330-593-174-000",
            rdo_code="050",
            name="PROSESO CONSULTING INC",
            trade_name="PROSESO CONSULTING INC",
            address="BURGUNDY CORPORATE TOWER MAKATI",
            zip_code="1203",
            telephone="09605005960",
            email="joseph@proseso-consulting.com",
            line_of_business="OTHER SERVICE ACTIVITIES",
        )
        content = build_profile_content(info)
        assert "fn=PROSESO%20CONSULTING%20INC" in content
        assert "tin1=330" in content
        assert "tin2=593" in content
        assert "tin3=174" in content
        assert "tin4=000" in content
        assert "rdo=050" in content
        assert "lob=OTHER%20SERVICE%20ACTIVITIES" in content

    def test_profile_filename(self):
        info = TaxpayerInfo(
            tin="330-593-174-000",
            rdo_code="050",
            name="Test",
            trade_name="Test",
            address="Addr",
            zip_code="1000",
            telephone="",
            email="",
        )
        assert profile_filename(info) == "330593174000.xml"
