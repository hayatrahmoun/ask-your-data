import pytest

from src import db, guardrails
from src.guardrails import UnsafeSQLError, validate_sql


def test_valid_select_gets_a_row_limit():
    sql = validate_sql("SELECT region, SUM(sales) FROM fact_sales f JOIN dim_customer c "
                       "ON c.customer_id = f.customer_id GROUP BY region")
    assert sql.endswith(f"LIMIT {guardrails.MAX_ROWS}")


def test_existing_limit_is_kept():
    assert validate_sql("SELECT * FROM dim_product LIMIT 5").endswith("LIMIT 5")


def test_markdown_fence_and_semicolon_are_cleaned():
    assert validate_sql("```sql\nSELECT 1 FROM dim_date;\n```").startswith("SELECT 1")


def test_cte_is_allowed():
    sql = "WITH t AS (SELECT region FROM dim_customer) SELECT region FROM t"
    assert validate_sql(sql)


@pytest.mark.parametrize("bad_sql", [
    "DROP TABLE fact_sales",
    "DELETE FROM fact_sales",
    "UPDATE fact_sales SET sales = 0",
    "INSERT INTO dim_product VALUES (1)",
    "SELECT 1; DROP TABLE fact_sales",                      # stacked statements
    "SELECT * FROM fact_sales -- hide something",           # comment
    "SELECT * FROM users",                                  # unknown table
    "SELECT * FROM sqlite_master",                          # schema leak
    "PRAGMA table_info(fact_sales)",
    "ATTACH DATABASE 'x.db' AS x",
    "",
])
def test_dangerous_queries_are_blocked(bad_sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(bad_sql)


def test_database_level_authorizer_blocks_writes_even_without_validation():
    """Second line of defence: SQLite itself refuses non-read statements."""
    con = db.build_connection()
    with pytest.raises(Exception):
        db.run_query(con, "DELETE FROM fact_sales")
    # data is untouched
    assert db.run_query(con, "SELECT COUNT(*) AS n FROM fact_sales")["n"][0] > 0
