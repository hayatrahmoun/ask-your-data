"""End-to-end test of the Streamlit app in offline mode (no API key needed)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_app_loads_without_errors():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception


def test_question_returns_table():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="question").set_value("How do discounts affect the profit margin?").run()
    assert not at.exception
    assert len(at.dataframe) == 1
    assert "discount_band" in at.dataframe[0].value.columns


def test_unknown_question_shows_friendly_message():
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.text_input(key="question").set_value("what is the weather on mars").run()
    assert not at.exception
    assert any("does not understand" in i.value for i in at.info)
