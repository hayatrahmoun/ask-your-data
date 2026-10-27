"""SQL safety guardrails.

An LLM can produce wrong or even harmful SQL (by mistake or through prompt injection).
Every generated query goes through these checks BEFORE it touches the database.
"""
import re

ALLOWED_TABLES = {"fact_sales", "dim_customer", "dim_product", "dim_date"}
MAX_ROWS = 500

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|replace|"
    r"vacuum|reindex|truncate|load_extension|sqlite_master|sqlite_schema)\b",
    re.IGNORECASE,
)


class UnsafeSQLError(ValueError):
    """Raised when a query is not allowed to run."""


def clean_sql(raw: str) -> str:
    """Remove markdown fences and the trailing semicolon from model output."""
    text = raw.strip()
    fence = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    return text.rstrip(";").strip()


def validate_sql(raw: str) -> str:
    """Return a safe, row-limited version of the query or raise UnsafeSQLError."""
    sql = clean_sql(raw)
    if not sql:
        raise UnsafeSQLError("empty query")
    if ";" in sql:
        raise UnsafeSQLError("multiple statements are not allowed")
    if "--" in sql or "/*" in sql:
        raise UnsafeSQLError("comments are not allowed")
    if not re.match(r"^(select|with)\b", sql, flags=re.IGNORECASE):
        raise UnsafeSQLError("only SELECT queries are allowed")
    bad = _FORBIDDEN.search(sql)
    if bad:
        raise UnsafeSQLError(f"forbidden keyword: {bad.group(1).upper()}")

    used = {t.lower() for t in re.findall(r"\b(?:from|join)\s+([A-Za-z_]\w*)", sql, flags=re.IGNORECASE)}
    ctes = {c.lower() for c in re.findall(r"\b([A-Za-z_]\w*)\s+as\s*\(", sql, flags=re.IGNORECASE)}
    unknown = used - ALLOWED_TABLES - ctes
    if unknown:
        raise UnsafeSQLError(f"unknown table(s): {', '.join(sorted(unknown))}")

    if not re.search(r"\blimit\s+\d+\s*$", sql, flags=re.IGNORECASE):
        sql = f"{sql} LIMIT {MAX_ROWS}"
    return sql
