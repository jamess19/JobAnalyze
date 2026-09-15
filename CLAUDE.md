# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

An ETL pipeline that crawls job listings from three Vietnamese job platforms (ITViec, TopCV, LinkedIn) with Scrapy + Playwright, cleans/deduplicates them, extracts skills/domains via NLP, and stores them in TimescaleDB. The `JobItem` schema (`src/spiders/items.py`) is explicitly designed as feature source data for a downstream **time-series LSTM model** (thesis project) — `date_posted` is the primary time index, so spiders must never infer or guess this field, only parse it from the source page.

## Commands

Run from the repo root unless noted.

```bash
# Install (local dev)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
playwright install chromium

# Run the full pipeline (all 3 spiders -> pipelines -> export -> Drive upload)
python src/main.py
python src/main.py --spider itviec     # single spider only: itviec | topcv | linkedin | all

# Run a spider directly via Scrapy CLI (from src/, bypasses main.py orchestration/export)
cd src
scrapy crawl itviec_spider -a keyword="software engineer" -a location="ho-chi-minh"
scrapy crawl topcv_spider  -a keyword="Data Engineer"
scrapy crawl linkedin_spider -a keyword="data analyst" -a location="Vietnam"

# Database (TimescaleDB via Docker) — required before any spider run since
# DeduplicationPipeline and DatabasePipeline connect to it
docker-compose up -d timescaledb

# Docker image build/run (matches Dockerfile CMD: python -m main)
docker build -t jobanalyze_scraper:latest .

# Airflow (local orchestration, daily DAG at 10:00 Asia/Ho_Chi_Minh)
docker compose -f docker-compose.airflow.yml up -d
```

There is no working automated test suite. `tests/test-itviec.py`, `tests/test-topcv.py`, and `tests/test-linkedin.py` import modules (`crawl-data`, `crawler.topcv_crawler`, `linkedin_crawler`) that no longer exist in `src/` — they predate the current Scrapy-based spider architecture and will fail if run. Validate spider/pipeline changes by running the actual `scrapy crawl` commands above against a small page range and inspecting DB rows / exported files, not by running these scripts.

## Architecture

### Data flow
`main.py` builds spider configs from `config/config.py:DEFAULT_CONFIG`, then `ScraperService` runs the selected Scrapy spiders. Each item flows through the Scrapy item pipeline chain in this fixed order (see `ITEM_PIPELINES` in `settings.py`):

1. **`pipelines/validation.py`** — drops items missing `job_url`/`title`/`source` or with a malformed URL.
2. **`pipelines/cleaning.py`** — strips HTML/whitespace from `description`/`requirements`/`benefits` only. Deliberately does **not** normalize location/salary/skills — that used to be a separate ML service's job.
3. **`pipelines/deduplication.py`** — DB-backed MinHash LSH: computes a 128-int signature, looks up candidate buckets in the `lsh_buckets` table, then verifies with exact Jaccard similarity (threshold 0.85) gated by a company-name + location metadata guard, plus a repost check (>=30 days apart is treated as a new posting, not a dup). Also keeps an in-process batch cache keyed on `md5(title|company)` to catch same-batch races before DB writes land. Runs *before* NLP extraction to avoid wasting NLP time on dupes.
4. **`pipelines/skill_extraction.py`** — runs a singleton spaCy `EntityRuler`-based extractor once per crawl (expensive to init), always re-runs NLP on `description`+`requirements` (even if HTML tags already gave `skills_tags`), then unions and normalizes (`utils/skill_normalizer.py`) the two skill sets and writes extracted domains into `extra_data['domains']`.
5. **`pipelines/database.py`** — persists to TimescaleDB via `repositories/job_repository.py` / SQLAlchemy models in `models/`.
6. **`pipelines/export.py`** — writes CSV/JSON/Excel; `ExportPipeline.export_all()` is called again after all spiders finish to produce one consolidated file, which `services/export_service.py` uploads to Google Drive.

### Spiders (`src/spiders/spiders/`)
All spiders subclass `base_spider.py:BaseJobSpider`, which provides: Playwright integration (`use_playwright = True` by default), `JobItem` construction with metadata defaults, job URL normalization (strips tracking params like `utm_*`, `trackingId`, `fbclid` so the same posting always hashes the same way), and deterministic `job_id` generation via UUID v5 from the normalized URL. Anti-bot behavior (rotating UA, proxy rotation, backoff) lives in downloader middlewares in `src/spiders/middlewares.py`, not in the spiders themselves — spiders opt in per-request via flags rather than each implementing their own evasion.

Crawling is intentionally conservative to avoid getting blocked: `CONCURRENT_REQUESTS_PER_DOMAIN = 1`, `DOWNLOAD_DELAY = 5` with randomization, AutoThrottle enabled, and FIFO (not Scrapy's default LIFO) scheduling so detail pages process in the same order they appear on listing pages.

### Database (TimescaleDB)
`schema.sql` defines `jobs` as a hypertable partitioned on `posted_date`, with `job_skills`/`job_domain` as hypertable association tables, `locations`/`skills`/`domains` as plain dimension tables, `lsh_buckets` for the deduplication step, and `skill_daily_stats`/`domain_daily_stats` as continuous aggregates (auto-refreshed materialized views) — these are what the downstream time-series work reads from, not the raw `jobs` table.

### Orchestration & deployment
- **Airflow** (`airflow/dags/scraper_dag.py`): a daily DAG runs the three spiders sequentially (itviec -> topcv -> linkedin) as separate `DockerOperator` tasks against the `jobanalyze_scraper:latest` image, mounting data/logs/credentials from `/opt/JobAnalyze/*` on the host.
- **CI/CD** (`.github/workflows/deploy.yml`): pushes to `main` SSH into a DigitalOcean droplet, `git pull`, rebuild the scraper image, and restart the Airflow compose stack. There is no test/lint gate in this workflow.
- Note: `docker-compose.yml` only defines the `timescaledb` service (no `scraper` service is currently defined there), while `scripts/run_pipeline.sh` and the Airflow DAG both assume a scraper image built separately via `docker build`.

### Configuration
Env vars are loaded from a root `.env` (see `example.env`) by both `settings.py` (DB URL) and `config/config.py` (Google Drive OAuth + crawl targets). `config/config.py:DEFAULT_CONFIG` holds the actual crawl targets — ITViec/TopCV are crawled as category listing URLs (not per-keyword) while LinkedIn is crawled per-keyword via `python-jobspy`-style search.

### AI Market Insights (`src/ai/`)
A separate, read-only NL-to-SQL feature layered on top of the same TimescaleDB data — does not touch the spaCy skill-extraction path. See `plans/260915-0010-ai-market-insights/plan.md` for the full design.

Flow: user question -> `ai/schema_context.py` builds a prompt from a hand-curated, allowlisted schema description -> `ai/llm_client.py` calls Groq (free-tier, OpenAI-compatible chat completions API) for a JSON `{"sql": ...}` -> `ai/sql_guard.py` validates it (single statement, SELECT/WITH only, table allowlist, forced LIMIT) -> executed via a dedicated **read-only Postgres role** (`ai_readonly`, granted in `schema.sql` — the real security boundary, not the guard) -> results fed back into a second LLM call for a grounded natural-language answer. `ai/insight_engine.py:answer_question()` is the single pure-function entrypoint; `src/ai_cli.py` is just a REPL wrapper around it. `ai/llm_client.py` is the only file that knows about Groq's REST shape — swapping providers means editing that one file.

```bash
# One-time setup
cp example.env .env   # then fill in GROQ_API_KEY, GROQ_MODEL if needed
docker-compose up -d timescaledb   # runs schema.sql on init, incl. the ai_readonly role

# Run the CLI
python src/ai_cli.py

# Run the eval harness (golden_questions.yaml + automated grading)
python eval/run_eval.py
```

**Verified live end-to-end on 2026-09-15** against real Groq API + real restored data (see below): `python eval/run_eval.py` → **14/14 valid (100%), 10/10 table (100%), 9/9 numeric (100%)** (the 16th question, a comparative one, has no single-number ground truth by design; 2 adversarial questions were separately re-run to confirm since they hit Groq free-tier rate limits on that particular pass — `llm_client.py` retries 429s with backoff, but the free tier's tokens-per-minute budget can still be exhausted across a full 16-question run). Several real bugs were found and fixed during this process — see `plans/260915-0010-ai-market-insights/phase-01-core-insight-engine.md`'s verification notes and `eval/golden_questions.yaml`'s per-question notes for what broke and why (partial-period bias in trend windows, Vietnamese city names stored without diacritics, decimal-comma vs thousands-comma number formats, continuous-aggregate vs raw-table count drift).

A real crawl snapshot from the now-decommissioned deploy server is available at `src/data/dump_data/dump-job_market-202608282241.sql` (pg_restore custom-format archive, ~16.9k jobs, despite the `.sql` extension — restore with `pg_restore`, not `psql -f`). The project's own `docker-compose.yml` `timescaledb` service (container `job_market_db`) has this restored and is the standing local dev/demo DB — port is **5435** in this repo's `docker-compose.yml` (not the historical 5433 default; changed because another project's container already holds 5433 on this machine — adjust back if that's not true for you). To rebuild from scratch:
```bash
# schema.sql's own hypertable/continuous-aggregate init conflicts with the
# dump's (both create the same TimescaleDB catalog objects) — restore into
# an EMPTY, un-initialized DB, then apply just the ai_readonly role after.
# Temporarily comment out the "./schema.sql:..." line in docker-compose.yml, then:
docker-compose down -v && docker-compose up -d timescaledb
pg_restore --no-owner --no-privileges -h localhost -p 5435 -U postgres -d job_market src/data/dump_data/dump-job_market-202608282241.sql
psql "postgresql://postgres:<POSTGRES_PASSWORD>@localhost:5435/job_market" -f schema.sql   # re-adds the ai_readonly role; safe to re-run
# then uncomment the schema.sql line back in docker-compose.yml for future fresh-volume inits
```
(4 harmless `ONLY option not supported on hypertable operations` errors on the top-level FK constraints during restore are expected — the real per-chunk FKs restore fine. Do NOT restore with `pg_restore --clean` on top of an already schema.sql-initialized DB — that produces ~60 TimescaleDB catalog conflicts, not 4.)

Golden questions with `expected_value: null` in `eval/golden_questions.yaml` are comparative (multi-number) answers, left ungraded by the numeric check by design — all other non-adversarial questions have hand-verified ground truth anchored to `snapshot_date: 2026-08-09`; re-verify by hand if evaluating against different/fresher data.
