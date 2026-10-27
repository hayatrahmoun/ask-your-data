"""AI mode: natural language -> SQL and result explanation using the Claude API.

Set the ANTHROPIC_API_KEY environment variable to enable it.
Optionally set ANTHROPIC_MODEL to choose the model.
"""
import os
import re

import pandas as pd

DEFAULT_MODEL = "claude-sonnet-5-5"

SQL_SYSTEM_PROMPT = """You are a careful senior data analyst who writes SQLite queries.

Rules:
- Reply with ONE SQL query inside a ```sql code block and nothing else.
- Use ONLY the tables and columns in the schema. Never invent columns.
- Read-only: SELECT (or WITH ... SELECT). No other statement types.
- Dates are TEXT 'YYYY-MM-DD'; use dim_date (year, year_month, ...) for time grouping.
- Round money to 0 decimals and percentages to 1 decimal.
- Give columns clear aliases, and put the category/time column first, numbers after.
- If the question cannot be answered from the schema, reply with: SELECT 'not answerable' AS message
"""

EXPLAIN_SYSTEM_PROMPT = """You are a business analyst. In 2-3 short sentences, explain what the
query result means for the business. Use only the numbers shown. Do not invent facts."""


def is_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _client():
    from anthropic import Anthropic  # imported lazily so offline mode needs no key

    return Anthropic()


def _model() -> str:
    return os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)


def extract_sql(text: str) -> str:
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else text).strip()


def generate_sql(question: str, schema_doc: str) -> str:
    message = _client().messages.create(
        model=_model(),
        max_tokens=600,
        system=SQL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Schema:\n{schema_doc}\n\nQuestion: {question}"}],
    )
    return extract_sql(message.content[0].text)


def explain(question: str, df: pd.DataFrame) -> str:
    sample = df.head(20).to_csv(index=False)
    message = _client().messages.create(
        model=_model(),
        max_tokens=300,
        system=EXPLAIN_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Question: {question}\n\nResult (CSV):\n{sample}"}],
    )
    return message.content[0].text.strip()
