#!/usr/bin/env python3
"""
AI Market Insights CLI — ask natural-language questions about the crawled
job market data. Run: python src/ai_cli.py

Requires: TimescaleDB running with schema.sql applied (incl. the ai_readonly
role), GROQ_API_KEY and AI_READONLY_DATABASE_URL set in .env.
"""

import os
import sys

_src_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _src_dir)

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(_src_dir), ".env"))

from ai.insight_engine import answer_question


def main() -> int:
    print("AI Market Insights — hỏi về thị trường job IT Việt Nam (Ctrl+C để thoát)")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if not question:
            continue

        result = answer_question(question)
        if result.error:
            print(f"[Error] {result.error}")
            if result.sql:
                print(f"(SQL attempted: {result.sql})")
            continue

        print(result.answer_text)
        print(f"\n  SQL used: {result.sql}")


if __name__ == "__main__":
    sys.exit(main())
