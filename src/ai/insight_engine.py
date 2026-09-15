"""
Orchestrates one question through: NL -> SQL (LLM) -> safety guard ->
read-only execute -> grounded NL answer (LLM).

`answer_question()` is a pure function with no CLI/print/IO side effects —
a future web UI or bot imports and calls it unchanged (see plan's scope
decision on keeping this an expansion seam).
"""

import os
from dataclasses import dataclass, field

from sqlalchemy import create_engine, text

from ai.llm_client import LlmClientError, call_llm, parse_json_response
from ai.schema_context import build_answer_prompt, build_sql_prompt
from ai.sql_guard import SqlGuardError, validate_and_prepare

_engine = None


def _get_readonly_engine():
    global _engine
    if _engine is None:
        url = os.getenv("AI_READONLY_DATABASE_URL")
        if not url:
            raise RuntimeError("AI_READONLY_DATABASE_URL not set in environment")
        _engine = create_engine(url, pool_pre_ping=True, pool_size=2)
    return _engine


@dataclass
class InsightAnswer:
    question: str
    sql: str | None = None
    rows: list[dict] = field(default_factory=list)
    answer_text: str | None = None
    error: str | None = None


def answer_question(question: str) -> InsightAnswer:
    result = InsightAnswer(question=question)

    try:
        raw = call_llm(build_sql_prompt(question), want_json=True)
        parsed = parse_json_response(raw)
    except LlmClientError as e:
        result.error = f"LLM SQL generation failed: {e}"
        return result

    sql = parsed.get("sql")
    if not sql:
        result.error = parsed.get("reason") or "Question not answerable with available data"
        return result

    try:
        safe_sql = validate_and_prepare(sql)
    except SqlGuardError as e:
        result.sql = sql
        result.error = f"Rejected unsafe/invalid SQL: {e}"
        return result

    result.sql = safe_sql

    try:
        engine = _get_readonly_engine()
        with engine.connect() as conn:
            rows = [dict(row._mapping) for row in conn.execute(text(safe_sql))]
    except Exception as e:
        result.error = f"Query execution failed: {e}"
        return result

    result.rows = rows

    try:
        answer_text = call_llm(build_answer_prompt(question, safe_sql, rows))
    except LlmClientError as e:
        result.error = f"LLM answer generation failed: {e}"
        return result

    result.answer_text = answer_text.strip()
    return result
