"""Ask Your Data: a natural-language analytics assistant (Streamlit app).

Run:  streamlit run app.py
"""
import streamlit as st

from src import charts, db, guardrails, llm, offline

st.set_page_config(page_title="Ask Your Data", page_icon="📊", layout="wide")

EXAMPLES = [
    "What are the total sales, profit and margin?",
    "How do sales and profit change by month?",
    "Which category has the lowest margin?",
    "How do discounts affect the profit margin?",
    "Who are the top customers?",
    "Compare the regions",
]


@st.cache_resource
def get_connection():
    return db.build_connection()


def set_question(text: str) -> None:
    st.session_state["question"] = text


con = get_connection()
ai_ready = llm.is_available()

with st.sidebar:
    st.header("Settings")
    engine = st.radio(
        "Engine",
        ["AI (Claude)", "Offline demo"],
        index=0 if ai_ready else 1,
        help="AI mode answers free-form questions. Offline demo works without an API key.",
    )
    if engine == "AI (Claude)" and not ai_ready:
        st.warning("ANTHROPIC_API_KEY is not set, so the offline demo is used.")
        engine = "Offline demo"
    st.header("Try an example")
    for i, example in enumerate(EXAMPLES):
        st.button(example, key=f"ex{i}", on_click=set_question, args=(example,), use_container_width=True)
    with st.expander("Database schema"):
        st.code(db.SCHEMA_DOC, language="text")

st.title("📊 Ask Your Data")
st.caption(
    "Ask a business question in plain English. The app writes the SQL, checks it for safety, "
    "runs it, and shows the result. Data is synthetic."
)

question = st.text_input("Your question", key="question", placeholder="e.g. Which region has the best margin?")

if question:
    sql, error = None, None
    try:
        if engine == "AI (Claude)":
            sql = llm.generate_sql(question, db.SCHEMA_DOC)
        else:
            sql = offline.generate_sql(question)
            if sql is None:
                error = ("The offline demo does not understand this question. Try one of the examples, "
                         "or set ANTHROPIC_API_KEY to use the AI engine.")
    except Exception as exc:  # network / API problems
        error = f"Could not generate SQL: {exc}"

    if error:
        st.info(error)
    elif sql:
        try:
            safe_sql = guardrails.validate_sql(sql)
            result = db.run_query(con, safe_sql)
        except guardrails.UnsafeSQLError as exc:
            st.error(f"🛡️ Blocked by the safety guardrails: {exc}")
        except Exception as exc:
            st.error(f"The query failed to run: {exc}")
        else:
            with st.expander("Generated SQL", expanded=False):
                st.code(safe_sql, language="sql")

            if engine == "AI (Claude)":
                try:
                    st.markdown(f"**Insight:** {llm.explain(question, result)}")
                except Exception:
                    st.markdown(f"**Summary:** {offline.summarize(result)}")
            else:
                st.markdown(f"**Summary:** {offline.summarize(result)}")

            chart = charts.pick_chart(result)
            left, right = st.columns([1, 1]) if chart else (st.container(), None)
            with left:
                st.dataframe(result, use_container_width=True, hide_index=True)
            if chart and right is not None:
                kind, plot_df = chart
                with right:
                    (st.line_chart if kind == "line" else st.bar_chart)(plot_df)
