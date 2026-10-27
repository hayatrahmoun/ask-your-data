import pandas as pd
import pytest

from src import charts, db, guardrails, llm, offline


@pytest.fixture(scope="module")
def con():
    return db.build_connection()


@pytest.mark.parametrize("template", [sql for _, sql in offline.TEMPLATES])
def test_every_offline_template_is_safe_and_runs(con, template):
    safe = guardrails.validate_sql(" ".join(template.split()))
    result = db.run_query(con, safe)
    assert len(result) > 0


@pytest.mark.parametrize("question, expected_fragment", [
    ("What are the total sales and profit?", "SUM(sales)"),
    ("show monthly trend", "year_month"),
    ("which category has the lowest margin", "p.category"),
    ("how do discounts affect margin", "discount_band"),
    ("compare the regions", "c.region"),
])
def test_offline_routing(question, expected_fragment):
    assert expected_fragment in offline.generate_sql(question)


def test_offline_returns_none_for_unknown_question():
    assert offline.generate_sql("what is the weather on mars") is None


def test_extract_sql_from_model_reply():
    reply = "Here you go:\n```sql\nSELECT 1\n```\nHope it helps"
    assert llm.extract_sql(reply) == "SELECT 1"


def test_chart_picker():
    monthly = pd.DataFrame({"year_month": ["2024-01", "2024-02"], "sales": [1.0, 2.0]})
    assert charts.pick_chart(monthly)[0] == "line"
    by_region = pd.DataFrame({"region": ["East", "West"], "sales": [1.0, 2.0]})
    assert charts.pick_chart(by_region)[0] == "bar"
    single_row = pd.DataFrame({"total_sales": [5.0], "profit": [1.0]})
    assert charts.pick_chart(single_row) is None


def test_known_business_number(con):
    """Sanity check against the figure documented in the BI project (about 3,000 orders)."""
    orders = db.run_query(con, "SELECT COUNT(DISTINCT order_id) AS n FROM fact_sales")["n"][0]
    assert orders == 3000
