"""Unit tests for Spanish/English team matching."""

from app.team_names_en import names_match, to_english


class TestToEnglish:
    def test_mexico(self):
        assert to_english("México") == "Mexico"

    def test_usa_maps_united_states(self):
        assert to_english("USA") == "United States"

    def test_unknown_passthrough(self):
        assert to_english("Unknownland") == "Unknownland"


class TestNamesMatch:
    def test_direct(self):
        assert names_match("Brasil", "Brazil") is True

    def test_korea_alias(self):
        assert names_match("Corea", "South Korea") is True
        assert names_match("Corea", "Korea Republic") is True

    def test_turkey_alias(self):
        assert names_match("Turquía", "Türkiye") is True

    def test_no_match(self):
        assert names_match("México", "Brazil") is False
