"""Measure text-to-SQL quality on a golden question set ("execution accuracy").

For each question, the generated SQL is executed and compared with the result of a reference query.
A question passes when every value of the reference result appears in the generated result
(a deliberately lenient check: extra columns or rows are tolerated).

Run:
    python evals/evaluate.py             # AI mode if ANTHROPIC_API_KEY is set, else offline demo
    python evals/evaluate.py --offline   # force the offline demo engine
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import db, guardrails, llm, offline  # noqa: E402


def _values(df):
    return {round(v, 0) if isinstance(v, float) else v for v in df.to_numpy().ravel().tolist()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="force the offline demo engine")
    args = parser.parse_args()

    use_ai = llm.is_available() and not args.offline
    engine = "AI (Claude)" if use_ai else "Offline demo"
    con = db.build_connection()
    cases = json.loads((ROOT / "evals" / "golden_questions.json").read_text(encoding="utf-8"))

    passed = 0
    print(f"Engine: {engine}\n")
    for case in cases:
        question = case["question"]
        try:
            sql = llm.generate_sql(question, db.SCHEMA_DOC) if use_ai else offline.generate_sql(question)
            generated = db.run_query(con, guardrails.validate_sql(sql)) if sql else None
            reference = db.run_query(con, guardrails.validate_sql(case["reference_sql"]))
            ok = generated is not None and _values(reference) <= _values(generated)
            note = "" if ok else "  (result does not cover the reference)"
        except Exception as exc:
            ok, note = False, f"  (error: {exc})"
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {question}{note}")

    print(f"\nExecution accuracy: {passed}/{len(cases)} = {passed / len(cases):.0%}")


if __name__ == "__main__":
    main()
