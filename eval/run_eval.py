#!/usr/bin/env python3
"""
Eval harness for the AI Market Insights feature (Phase 2 of the
plans/260915-0010-ai-market-insights plan).

Runs every question in golden_questions.yaml through
src.ai.insight_engine.answer_question and grades it on three checks:
  1. valid    — did it produce/reject SQL the way it should have
                (a real question should succeed; an adversarial/unanswerable
                 one should NOT produce a successful grounded answer)
  2. table    — for non-adversarial questions with expected_tables set, does
                the generated SQL only reference those tables (ignoring CTEs)
  3. numeric  — for questions with expected_value set (i.e. ground truth has
                been filled in by hand), does the NL answer contain a number
                within `tolerance` of it

Usage: python eval/run_eval.py [path/to/golden_questions.yaml]
"""

import os
import re
import sys
from datetime import datetime

import yaml

_eval_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_eval_dir)
_src_dir = os.path.join(_project_root, "src")
sys.path.insert(0, _src_dir)

from dotenv import load_dotenv

load_dotenv(os.path.join(_project_root, ".env"))

from ai.insight_engine import answer_question
from ai.sql_guard import extract_cte_names, extract_referenced_tables

_NUMBER_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
# Infra/API-level failures (rate limit, network, malformed response) are not
# evidence that an adversarial question was actually defended against — the
# LLM may never have been meaningfully exercised. Only a guard rejection or
# a genuine LLM decline counts as a real "correctly refused" signal.
_INFRA_ERROR_PREFIXES = ("LLM SQL generation failed:", "LLM answer generation failed:")


def check_valid(question: dict, result) -> tuple[bool, str] | None:
    produced_answer = result.error is None and result.answer_text is not None
    if question["is_adversarial"]:
        if result.error and result.error.startswith(_INFRA_ERROR_PREFIXES):
            return None  # inconclusive — the LLM/API call itself failed, not a defense signal
        if not produced_answer:
            return True, "correctly refused/declined"
        return False, "produced an answer to an adversarial/unanswerable question"
    if produced_answer:
        return True, "produced an answer"
    return False, f"expected a real answer but got error: {result.error}"


def check_table(question: dict, result) -> tuple[bool, str] | None:
    if question["is_adversarial"] or not question.get("expected_tables"):
        return None  # not applicable
    if result.error is not None or not result.sql:
        # Guard rejected the SQL or execution failed — 'valid' check already
        # reports this. Don't grade table usage on unsafe/unexecuted SQL,
        # it would read as a misleading PASS next to a FAILing 'valid' check.
        return None
    referenced = extract_referenced_tables(result.sql) - extract_cte_names(result.sql)
    expected = {t.lower() for t in question["expected_tables"]}
    if referenced <= expected:
        return True, f"used tables {referenced or '{}'} (subset of {expected})"
    return False, f"used unexpected tables {referenced - expected}"


def _normalize_thousands_separators(text: str) -> str:
    """
    Collapse Vietnamese-style thousands grouping ("3 666", "3.666") down to
    plain digits ("3666") before number extraction, so answers like
    "ITViec đã đăng 3.666 job" don't get split into [3, 666]. Heuristic: only
    collapses a "." or whitespace between digits when followed by exactly 3
    digits (a thousands group), so real decimals like "17.3" are untouched.
    """
    return re.sub(r"(?<=\d)[.\s](?=\d{3}(?:\D|$))", "", text)


def _parse_number(token: str) -> float:
    """
    A bare comma is ambiguous: US-style thousands grouping ("17,311,424")
    vs Vietnamese/European decimal separator ("424,78" == 424.78). Heuristic:
    a comma followed by exactly 1-2 trailing digits is a decimal separator;
    anything else (3+ digit groups) is thousands grouping and gets stripped.
    Without this, "424,78" naively becomes 42478 instead of 424.78 — a real
    bug found via a live eval run (avg_salary_python false negative).
    """
    if re.fullmatch(r"\d+,\d{1,2}", token):
        return float(token.replace(",", "."))
    return float(token.replace(",", ""))


def check_numeric(question: dict, result) -> tuple[bool, str] | None:
    if question.get("expected_value") is None:
        return None  # no ground truth filled in yet
    if not result.answer_text:
        return False, "no answer text to check"
    expected = float(question["expected_value"])
    tolerance = float(question.get("tolerance") or 0)
    cleaned = _normalize_thousands_separators(result.answer_text)
    numbers = [_parse_number(n) for n in _NUMBER_RE.findall(cleaned)]
    if any(abs(n - expected) <= tolerance for n in numbers):
        return True, f"found a number within {tolerance} of {expected}"
    return False, f"expected ~{expected} (+/-{tolerance}), answer had {numbers} — raw answer: {result.answer_text!r}"


def run() -> int:
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(_eval_dir, "golden_questions.yaml")
    with open(yaml_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    questions = doc["questions"]
    snapshot_date = doc.get("snapshot_date")
    if snapshot_date:
        print(f"Ground truth in {os.path.basename(yaml_path)} is anchored to snapshot_date={snapshot_date} "
              f"— trend questions will only match if run against that same data snapshot.")

    lines = [f"# Eval report — {datetime.now().isoformat(timespec='seconds')}", ""]
    counts = {"valid": [0, 0], "table": [0, 0], "numeric": [0, 0]}
    ungraded_numeric = 0
    inconclusive_valid = 0

    for q in questions:
        result = answer_question(q["question"])
        row = [
            f"## {q['id']}", f"Q: {q['question']}", f"SQL: `{result.sql}`",
            f"Error: {result.error}", f"Answer: {result.answer_text!r}",
        ]

        valid_check = check_valid(q, result)
        if valid_check is None:
            inconclusive_valid += 1
            status = "INCONCLUSIVE"
            row.append(f"- valid: INCONCLUSIVE — LLM/API call failed before it could be tested ({result.error})")
        else:
            ok, reason = valid_check
            counts["valid"][ok] += 1
            status = "PASS" if ok else "FAIL"
            row.append(f"- valid: {status} — {reason}")

        table_check = check_table(q, result)
        if table_check is not None:
            ok, reason = table_check
            counts["table"][ok] += 1
            row.append(f"- table: {'PASS' if ok else 'FAIL'} — {reason}")

        numeric_check = check_numeric(q, result)
        if numeric_check is not None:
            ok, reason = numeric_check
            counts["numeric"][ok] += 1
            row.append(f"- numeric: {'PASS' if ok else 'FAIL'} — {reason}")
        elif not q["is_adversarial"]:
            ungraded_numeric += 1
            row.append("- numeric: SKIPPED — no ground truth in golden_questions.yaml yet")

        lines.append("\n".join(row))
        lines.append("")
        print(f"{q['id']}: valid={status}")

    def pct(pair):
        total = sum(pair)
        return "n/a" if total == 0 else f"{pair[1]}/{total} ({100 * pair[1] / total:.0f}%)"

    summary = (
        f"\nSummary: valid={pct(counts['valid'])}  "
        f"table={pct(counts['table'])}  numeric={pct(counts['numeric'])}  "
        f"(numeric checks skipped for {ungraded_numeric} questions — ground truth not filled in; "
        f"{inconclusive_valid} adversarial question(s) inconclusive due to LLM/API failures — re-run to get a real signal for those)"
    )
    print(summary)
    lines.insert(1, summary)

    report_path = os.path.join(_eval_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nFull report written to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
