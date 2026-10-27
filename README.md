# Ask Your Data: an AI analytics assistant (natural language to SQL)

Ask a business question in plain English. The app **writes the SQL, checks it for safety, runs it, and shows
a table, a chart and a short explanation**. It works on the retail sales star schema from my
[BI Sales Analytics project](https://github.com/hayatrahmoun/bi-sales-analytics) (synthetic data).

```
"How do discounts affect the profit margin?"
        |
        v
  LLM (Claude API)  ->  SQL  ->  safety guardrails  ->  read-only SQLite  ->  table + chart + insight
```

## Why this project
Letting an AI query a database is easy to demo and easy to get wrong. This project focuses on the parts that
make it usable in a real company:

| Concern | How it is handled |
|---|---|
| **Safety** | Two layers: a validator (SELECT only, one statement, no comments, table allow-list, forced row limit) and a SQLite *authorizer* that refuses any non-read action at database level |
| **Prompt injection / bad SQL** | Generated SQL is never trusted; it is validated and executed with a 5-second time limit |
| **Quality** | `evals/evaluate.py` measures *execution accuracy* on a golden question set |
| **Reliability** | 38 automated tests (guardrails, routing, charts, and the full Streamlit app) |
| **Accessibility** | An **offline demo mode** runs without any API key |

## Example (real output, offline demo engine)

**Q: How do discounts affect the profit margin?**

| discount_band | sales | profit | margin_pct |
|---|---|---|---|
| 0% | 2,823,197 | 712,446 | 25.2 |
| 1-10% | 1,200,804 | 206,610 | 17.2 |
| 11-20% | 559,941 | 37,182 | 6.6 |
| 21%+ | 934,514 | -144,324 | -15.4 |

**A blocked attack:** `SELECT 1; DROP TABLE fact_sales` is rejected with *"multiple statements are not allowed"*,
and even without that check, SQLite's authorizer would refuse the `DROP`.

## Run it
```bash
git clone https://github.com/hayatrahmoun/ask-your-data
cd ask-your-data
pip install -r requirements.txt

# Option A: offline demo (no API key)
streamlit run app.py

# Option B: AI mode with Claude (free-form questions)
export ANTHROPIC_API_KEY="your-key"      # Windows PowerShell: $env:ANTHROPIC_API_KEY="your-key"
streamlit run app.py
```
Optional: `export ANTHROPIC_MODEL=...` to choose the model.

## Test and evaluate
```bash
pytest                                  # 38 tests
python evals/evaluate.py --offline      # offline demo engine on 6 golden questions
python evals/evaluate.py                # AI engine, if ANTHROPIC_API_KEY is set
```

## Project structure
```
app.py                 Streamlit interface
src/db.py              SQLite loading, schema description, read-only execution
src/guardrails.py      SQL validation and row limit
src/llm.py             Claude API: question -> SQL, result -> insight
src/offline.py         Keyword demo mode (10 reviewed queries)
src/charts.py          Automatic chart selection
tests/                 pytest suite (including end-to-end app tests)
evals/                 Golden questions and execution-accuracy script
data/                  Star schema CSV files (synthetic)
```

## Honest limitations
- **The offline demo only understands about 10 kinds of questions.** It exists so the app can be tried for free;
  the AI mode is the real engine.
- **Text-to-SQL is not always right.** The model can misunderstand a question. That is why the SQL is always
  shown and why the evaluation script exists. Treat results as a draft to verify, not as ground truth.
- The automated tests do not call the Claude API (they run without a key); the offline demo scores 6/6 on the
  golden set by design, so run the evaluation with a key to measure the AI engine.
- Data is synthetic and small (about 7,500 order lines).

## Ideas for next steps
Multi-turn questions with conversation memory, a larger golden set with harder questions (window functions,
cohorts), query caching, and deployment on Streamlit Community Cloud.

## Author
**Hayat Rahmoun**: Data Analyst | Power BI - Zoho Analytics - Python - SQL
[LinkedIn](https://linkedin.com/in/hayat-rahmoun-b49829221)
