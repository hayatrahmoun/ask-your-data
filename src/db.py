"""Database layer: loads the star schema into SQLite and runs queries safely."""
import sqlite3
import time
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
TABLES = ["fact_sales", "dim_customer", "dim_product", "dim_date"]

QUERY_TIMEOUT_S = 5

# Business-friendly description of the schema: this is what the LLM sees.
SCHEMA_DOC = """
SQLite database, star schema of retail sales (synthetic data, 2024-01 to 2025-12).

fact_sales (one row per order line)
  line_id, order_id, order_date (TEXT 'YYYY-MM-DD'), ship_date (TEXT 'YYYY-MM-DD'),
  customer_id, product_id, quantity, unit_price, discount (0 to 0.4),
  sales (revenue after discount), cost, profit (sales - cost)

dim_customer
  customer_id, customer_name, segment ('Consumer' | 'Corporate' | 'Home Office'),
  city, region ('East' | 'West' | 'Central' | 'South')

dim_product
  product_id, product_name, category ('Furniture' | 'Technology' | 'Office Supplies'),
  sub_category, unit_price, unit_cost

dim_date
  date (TEXT 'YYYY-MM-DD'), year, quarter ('Q1'..'Q4'), month_num, month_name,
  year_month ('YYYY-MM'), weekday, is_weekend

Joins: fact_sales.customer_id = dim_customer.customer_id
       fact_sales.product_id  = dim_product.product_id
       fact_sales.order_date  = dim_date.date
Profit margin % = 100.0 * SUM(profit) / SUM(sales)
""".strip()


def build_connection() -> sqlite3.Connection:
    """Load the CSV files into an in-memory SQLite database."""
    con = sqlite3.connect(":memory:", check_same_thread=False)
    for table in TABLES:
        pd.read_csv(DATA_DIR / f"{table}.csv").to_sql(table, con, index=False)
    return con


# SQLite action codes that a read-only analytics query is allowed to trigger.
_ALLOWED_ACTIONS = {
    sqlite3.SQLITE_SELECT,
    sqlite3.SQLITE_READ,
    sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}


def _authorizer(action, *_args):
    return sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY


def run_query(con: sqlite3.Connection, sql: str) -> pd.DataFrame:
    """Run an already-validated query with a second, database-level safety net.

    Defence in depth: even if the text validator missed something, SQLite itself
    refuses any statement that is not a plain read, and a time limit stops runaway queries.
    """
    deadline = time.monotonic() + QUERY_TIMEOUT_S
    con.set_authorizer(_authorizer)
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        return pd.read_sql_query(sql, con)
    finally:
        con.set_authorizer(None)
        con.set_progress_handler(None, 0)
