"""
Static, hand-curated description of the tables the AI Market Insights
feature is allowed to query, plus the prompt templates built from it.

Only structured/aggregate columns are described here. Raw scraped text
(job description/requirements/benefits) is never persisted to the DB
(see schema.sql `jobs` table) and is never referenced in these prompts —
so there is no path for attacker-influenceable crawled content to reach
the SQL-generation prompt.
"""

SCHEMA_CONTEXT = """
You can query a PostgreSQL/TimescaleDB database about the Vietnamese IT job
market. Only use the tables and columns listed below — nothing else exists.

TABLE skill_daily_stats (continuous aggregate, one row per skill per day)
  - date        DATE
  - skill_id    UUID        -- join to skills.id
  - job_count   INTEGER     -- number of postings mentioning this skill, that day

TABLE domain_daily_stats (continuous aggregate, one row per business domain per day)
  - date        DATE
  - domain_id   UUID        -- join to domains.id
  - job_count   INTEGER

TABLE skills
  - id          UUID
  - name        TEXT        -- normalized skill name, e.g. 'ReactJS', 'Python'
  - category    TEXT        -- e.g. 'Framework', 'Language'

TABLE domains
  - id          UUID
  - name        TEXT        -- e.g. 'Fintech', 'E-commerce'

TABLE locations
  - id          UUID
  - city_name   TEXT        -- normalized Vietnamese province/city name,
                             -- STORED WITHOUT DIACRITICS, lowercase
                             -- (e.g. 'ha noi', 'ho chi minh', 'da nang') —
                             -- always match with the unaccented lowercase
                             -- form, never 'hà nội' / 'Hà Nội'

TABLE jobs
  - id              UUID
  - posted_date     TIMESTAMP
  - source          TEXT     -- 'itviec' | 'topcv' | 'linkedin'
  - title           TEXT
  - company_name    TEXT
  - salary_min      DECIMAL
  - salary_max      DECIMAL
  - salary_currency TEXT
  - experience      TEXT     -- free-text experience requirement
  - location_id     UUID     -- join to locations.id

TABLE job_skills (job <-> skill, many-to-many)
  - job_id, skill_id, posted_date

TABLE job_domain (job <-> domain, many-to-many)
  - job_id, domain_id, posted_date

Rules:
- Only SELECT statements (CTEs with WITH are fine). Never modify data.
- Always include a LIMIT (50 or fewer) unless the question asks for a single aggregate number.
- Prefer skill_daily_stats / domain_daily_stats for trend questions — do not scan
  jobs/job_skills directly for trend/demand-over-time questions.
- For "increased/decreased the most" questions, compare TWO EQUAL-LENGTH trailing
  windows (e.g. last 30 days vs the 30 days before that). Do NOT compare a
  calendar month-to-date against a full previous month — that always makes the
  current period look artificially lower purely because it has fewer days so far.
- When filtering by city_name, always strip diacritics and lowercase the value
  first (e.g. "Hà Nội" -> "ha noi") — the column never contains accented text.
- If the question cannot be answered with these tables, respond with
  {"sql": null, "reason": "<why not answerable>"} instead of guessing.
"""

FEW_SHOT_EXAMPLES = """
Q: Skill nào tăng nhu cầu nhiều nhất trong 30 ngày qua (so với 30 ngày trước đó)?
SQL: WITH cur AS (
       SELECT skill_id, SUM(job_count) AS c FROM skill_daily_stats
       WHERE date > CURRENT_DATE - INTERVAL '30 days' GROUP BY skill_id
     ), prev AS (
       SELECT skill_id, SUM(job_count) AS c FROM skill_daily_stats
       WHERE date > CURRENT_DATE - INTERVAL '60 days'
         AND date <= CURRENT_DATE - INTERVAL '30 days' GROUP BY skill_id
     )
     SELECT s.name, COALESCE(prev.c, 0) AS prev_count, COALESCE(cur.c, 0) AS cur_count,
            COALESCE(cur.c, 0) - COALESCE(prev.c, 0) AS delta
     FROM cur LEFT JOIN prev ON prev.skill_id = cur.skill_id
     JOIN skills s ON s.id = cur.skill_id
     ORDER BY delta DESC LIMIT 10;

Q: Domain nào giảm nhu cầu nhiều nhất trong 30 ngày qua (so với 30 ngày trước đó)?
SQL: WITH cur AS (
       SELECT domain_id, SUM(job_count) AS c FROM domain_daily_stats
       WHERE date > CURRENT_DATE - INTERVAL '30 days' GROUP BY domain_id
     ), prev AS (
       SELECT domain_id, SUM(job_count) AS c FROM domain_daily_stats
       WHERE date > CURRENT_DATE - INTERVAL '60 days'
         AND date <= CURRENT_DATE - INTERVAL '30 days' GROUP BY domain_id
     )
     SELECT dm.name, COALESCE(prev.c, 0) AS prev_count, COALESCE(cur.c, 0) AS cur_count,
            COALESCE(cur.c, 0) - COALESCE(prev.c, 0) AS delta
     FROM cur LEFT JOIN prev ON prev.domain_id = cur.domain_id
     JOIN domains dm ON dm.id = cur.domain_id
     ORDER BY delta ASC LIMIT 10;

Q: TopCV có bao nhiêu job đang mở ở Hà Nội?
SQL: SELECT COUNT(*) FROM jobs j JOIN locations l ON l.id = j.location_id
     WHERE j.source = 'topcv' AND l.city_name ILIKE '%ha noi%';
"""


def build_sql_prompt(question: str) -> str:
    return (
        f"{SCHEMA_CONTEXT}\nExamples:\n{FEW_SHOT_EXAMPLES}\n"
        f"Question: {question}\n\n"
        'Respond with ONLY a JSON object: {"sql": "<SELECT statement>"} '
        'or {"sql": null, "reason": "<why not answerable>"}. No markdown, no prose.'
    )


def build_answer_prompt(question: str, sql: str, rows: list[dict]) -> str:
    return (
        "You answered a question about the Vietnamese IT job market by running the SQL "
        "query below and getting exactly these rows back. Base your answer ONLY on this "
        "data — never invent a number that isn't here. Answer in the same language as the "
        "question, in 2-3 concise sentences.\n\n"
        f"Question: {question}\nSQL: {sql}\nRows: {rows}\n\nAnswer:"
    )
