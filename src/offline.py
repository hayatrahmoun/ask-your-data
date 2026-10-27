"""Offline demo mode: keyword matching to ready-made, reviewed SQL queries.

This lets anyone try the app without an API key. It is intentionally simple:
it only understands the questions below. The AI mode (llm.py) handles free-form questions.
"""
import re

import pandas as pd

# (keywords, sql)
TEMPLATES = [
    ({"total", "overall", "kpi", "kpis", "revenue", "orders", "average", "aov"},
     """SELECT ROUND(SUM(sales),0) AS total_sales, ROUND(SUM(profit),0) AS total_profit,
        ROUND(100.0*SUM(profit)/SUM(sales),1) AS margin_pct, COUNT(DISTINCT order_id) AS orders,
        ROUND(SUM(sales)/COUNT(DISTINCT order_id),0) AS avg_order_value
        FROM fact_sales"""),
    ({"year", "yearly", "annual", "growth", "2024", "2025"},
     """SELECT d.year, ROUND(SUM(f.sales),0) AS sales, ROUND(SUM(f.profit),0) AS profit,
        ROUND(100.0*SUM(f.profit)/SUM(f.sales),1) AS margin_pct
        FROM fact_sales f JOIN dim_date d ON d.date = f.order_date GROUP BY d.year ORDER BY d.year"""),
    ({"month", "monthly", "trend", "time", "seasonality", "season", "peak"},
     """SELECT d.year_month, ROUND(SUM(f.sales),0) AS sales, ROUND(SUM(f.profit),0) AS profit
        FROM fact_sales f JOIN dim_date d ON d.date = f.order_date GROUP BY d.year_month ORDER BY d.year_month"""),
    ({"category", "categories", "technology", "furniture", "supplies", "office"},
     """SELECT p.category, ROUND(SUM(f.sales),0) AS sales, ROUND(SUM(f.profit),0) AS profit,
        ROUND(100.0*SUM(f.profit)/SUM(f.sales),1) AS margin_pct
        FROM fact_sales f JOIN dim_product p ON p.product_id = f.product_id
        GROUP BY p.category ORDER BY profit DESC"""),
    ({"product", "products", "best", "selling", "profitable"},
     """SELECT p.product_name, ROUND(SUM(f.sales),0) AS sales, ROUND(SUM(f.profit),0) AS profit
        FROM fact_sales f JOIN dim_product p ON p.product_id = f.product_id
        GROUP BY p.product_name ORDER BY profit DESC LIMIT 10"""),
    ({"region", "regions", "east", "west", "south", "central", "geography"},
     """SELECT c.region, ROUND(SUM(f.sales),0) AS sales, ROUND(SUM(f.profit),0) AS profit,
        ROUND(100.0*SUM(f.profit)/SUM(f.sales),1) AS margin_pct
        FROM fact_sales f JOIN dim_customer c ON c.customer_id = f.customer_id
        GROUP BY c.region ORDER BY sales DESC"""),
    ({"discount", "discounts", "discounted"},
     """SELECT CASE WHEN discount = 0 THEN '0%' WHEN discount <= 0.1 THEN '1-10%'
        WHEN discount <= 0.2 THEN '11-20%' ELSE '21%+' END AS discount_band,
        ROUND(SUM(sales),0) AS sales, ROUND(SUM(profit),0) AS profit,
        ROUND(100.0*SUM(profit)/SUM(sales),1) AS margin_pct
        FROM fact_sales GROUP BY discount_band ORDER BY MIN(discount)"""),
    ({"customer", "customers", "clients", "buyers", "top"},
     """SELECT c.customer_name, c.segment, ROUND(SUM(f.sales),0) AS sales
        FROM fact_sales f JOIN dim_customer c ON c.customer_id = f.customer_id
        GROUP BY c.customer_id, c.customer_name, c.segment ORDER BY sales DESC LIMIT 10"""),
    ({"segment", "segments", "consumer", "corporate", "home"},
     """SELECT c.segment, COUNT(DISTINCT c.customer_id) AS customers, ROUND(SUM(f.sales),0) AS sales,
        ROUND(SUM(f.sales)/COUNT(DISTINCT c.customer_id),0) AS sales_per_customer
        FROM fact_sales f JOIN dim_customer c ON c.customer_id = f.customer_id
        GROUP BY c.segment ORDER BY sales DESC"""),
    ({"repeat", "loyal", "returning", "retention"},
     """SELECT CASE WHEN n_orders = 1 THEN 'One-time' ELSE 'Repeat' END AS customer_type,
        COUNT(*) AS customers
        FROM (SELECT customer_id, COUNT(DISTINCT order_id) AS n_orders FROM fact_sales GROUP BY customer_id)
        GROUP BY customer_type"""),
]


def generate_sql(question: str) -> str | None:
    """Return the best-matching template, or None if nothing matches."""
    words = set(re.findall(r"[a-z0-9]+", question.lower()))
    best_score, best_sql = 0, None
    for keywords, sql in TEMPLATES:
        score = len(words & keywords)
        if score > best_score:
            best_score, best_sql = score, sql
    return " ".join(best_sql.split()) if best_sql else None


def summarize(df: pd.DataFrame) -> str:
    """A deterministic one-line summary (no LLM needed)."""
    if df.empty:
        return "The query returned no rows."
    first = ", ".join(f"{c} = {v}" for c, v in df.iloc[0].items())
    return f"{len(df)} row(s). First row: {first}."
