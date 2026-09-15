"""
App-level safety checks on LLM-generated SQL.

This is defense-in-depth, NOT the security boundary — the real boundary is
the `ai_readonly` Postgres role (see schema.sql section 7), which physically
cannot mutate data even if a query slips past this guard. This module exists
to fail fast with a clear error and enforce the table allowlist / LIMIT
convention — it is a regex-based check, not a full SQL parser, and is not
meant to be one.
"""

import re

TABLE_ALLOWLIST = {
    "jobs", "locations", "skills", "domains",
    "job_skills", "job_domain",
    "skill_daily_stats", "domain_daily_stats",
}

DEFAULT_LIMIT = 50

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|COPY|CREATE|CALL|EXECUTE|VACUUM)\b",
    re.IGNORECASE,
)
_TABLE_REF = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)
# CTE definitions look like `name AS (` — their names aren't real tables and
# must not be checked against TABLE_ALLOWLIST (see phase-01 plan note on the
# domain_daily_stats WITH-clause example).
_CTE_NAME = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s+AS\s*\(", re.IGNORECASE)


class SqlGuardError(Exception):
    pass


def extract_referenced_tables(sql: str) -> set[str]:
    return {m.lower() for m in _TABLE_REF.findall(sql)}


def extract_cte_names(sql: str) -> set[str]:
    return {m.lower() for m in _CTE_NAME.findall(sql)}


def validate_and_prepare(sql: str | None) -> str:
    """Validate `sql`, inject a default LIMIT if missing, return safe-to-run SQL.

    Raises SqlGuardError if the query is empty, multi-statement, non-SELECT,
    contains a forbidden keyword, or references a non-allowlisted table.
    """
    if not sql or not sql.strip():
        raise SqlGuardError("Empty SQL")

    statements = [s for s in sql.strip().split(";") if s.strip()]
    if len(statements) != 1:
        raise SqlGuardError("Only a single SQL statement is allowed")

    stmt = statements[0].strip()

    if not re.match(r"^\s*(SELECT|WITH)\b", stmt, re.IGNORECASE):
        raise SqlGuardError("Only SELECT (or WITH ... SELECT) statements are allowed")

    if _FORBIDDEN_KEYWORDS.search(stmt):
        raise SqlGuardError("Query contains a forbidden keyword")

    referenced = extract_referenced_tables(stmt)
    cte_names = extract_cte_names(stmt)
    disallowed = referenced - TABLE_ALLOWLIST - cte_names
    if disallowed:
        raise SqlGuardError(f"Query references non-allowlisted table(s): {disallowed}")

    if not re.search(r"\bLIMIT\s+\d+", stmt, re.IGNORECASE):
        stmt = f"{stmt}\nLIMIT {DEFAULT_LIMIT}"

    return stmt
