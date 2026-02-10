# Job Data Collection Pipeline

An automated ETL pipeline that collects job listings from Vietnamese recruitment platforms (ITViec, TopCV, LinkedIn), processes and deduplicates them, and stores results in TimescaleDB.

## Overview

This pipeline automates the full data collection lifecycle:

- **Extract** — Crawl job listings from 3 sources using Scrapy + Playwright
- **Transform** — Validate, clean, and deduplicate data using MinHash LSH
- **Load** — Store normalized data in TimescaleDB (PostgreSQL)
- **Export** — Output to CSV/JSON/Excel and upload to Google Drive

## Tech Stack

| Component | Technology |
|---|---|
| Web Scraping | Scrapy, Scrapy-Playwright, BeautifulSoup4 |
| Browser Automation | Playwright (Chromium) |
| Database | TimescaleDB (PostgreSQL 14) |
| ORM | SQLAlchemy 2.0 |
| Deduplication | datasketch (MinHash LSH) |
| Data Processing | Pandas |
| Cloud Storage | Google Drive API |
| Containerization | Docker, Docker Compose |

## Project Structure

```
data-collection/
├── src/
│   ├── main.py                    # Entry point
│   ├── settings.py                # Scrapy settings
│   ├── config/
│   │   ├── config.py              # General config (keywords, locations)
│   │   ├── logging_config.py      # Logging setup
│   │   └── credentials/           # Google Drive credentials (git-ignored)
│   ├── spiders/
│   │   ├── items.py               # JobItem schema
│   │   ├── middlewares.py         # Scrapy middlewares
│   │   ├── run_spiders.py         # Spider runner
│   │   └── spiders/
│   │       ├── base_spider.py     # Abstract base spider
│   │       ├── itviec_spider.py   # ITViec spider
│   │       ├── topcv_spider.py    # TopCV spider
│   │       └── linkedin_spider.py # LinkedIn spider
│   ├── pipelines/
│   │   ├── validation.py          # Input data validation
│   │   ├── cleaning.py            # Data cleaning
│   │   ├── deduplication.py       # Duplicate detection (MinHash LSH)
│   │   ├── database.py            # Database persistence
│   │   └── export.py              # CSV/JSON/Excel export
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── base.py
│   │   ├── job.py                 # Jobs table
│   │   ├── location.py            # Locations dimension
│   │   ├── skill.py               # Skills dimension
│   │   ├── domain.py              # Domains dimension
│   │   └── associations.py        # Many-to-many associations
│   ├── repositories/
│   │   └── job_repository.py      # Data access layer
│   ├── services/
│   │   ├── scraper_service.py     # Spider orchestration
│   │   └── export_service.py      # Google Drive upload
│   ├── storage/
│   │   ├── base_uploader.py       # Abstract uploader
│   │   └── drive_uploader.py      # Google Drive uploader
│   ├── utils/
│   │   ├── normalizer.py          # Data normalization
│   │   ├── field_extractor.py     # Field extraction
│   │   ├── deduplicator.py        # Deduplication logic
│   │   └── utils.py               # General utilities
│   ├── logs/                      # Log files
│   └── data/                      # Output directory
├── tests/
│   ├── test-itviec.py
│   ├── test-topcv.py
│   └── test-linkedin.py
├── scripts/
│   └── run_pipeline.sh
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── schema.sql                     # TimescaleDB schema
└── example.env
```

## Prerequisites

- Python >= 3.10
- Docker & Docker Compose (for containerized deployment)
- Google Chrome / Chromium

## Installation

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd data-collection

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .

# Install Playwright browser
playwright install chromium
```

### 2. Configure environment variables

```bash
cp example.env .env
```

Edit `.env`:

```env
# Google Drive
SCOPES=https://www.googleapis.com/auth/drive
TOKEN_FILE_PATH=token.json
CLIENT_SECRET_FILE=src/config/credentials/client_secret.json
FOLDER_ID=<your_google_drive_folder_id>
OUTPUT_FOLDER=src/data
REDIRECT_URI=http://localhost:8000/callback
PORT=8000

# Database
POSTGRES_PASSWORD=password
POSTGRES_USER=postgres
POSTGRES_DB=job_market
DATABASE_URL=postgresql://postgres:password@localhost:5433/job_market
```

### 3. Set up Google Drive API

1. Create a project on [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Drive API
3. Create OAuth 2.0 credentials (Desktop app type)
4. Download `client_secret.json` and place it in `src/config/credentials/`
5. On first run, a browser window will open for OAuth authentication. The token is saved automatically.

## Usage

### Run with Docker (recommended)

```bash
docker-compose up
```

This starts:
- **TimescaleDB** (port 5433) — Database with auto-initialized schema
- **Scraper** — Runs the full pipeline after the DB is ready

### Run locally

```bash
# Run the full pipeline
python src/main.py

# Or use the CLI entry point
scrape
```

The pipeline executes in order:
1. Run spiders (ITViec, TopCV, LinkedIn) with Playwright
2. Process items: Validation → Cleaning → Deduplication → Database → Export
3. Export CSV/JSON/Excel to `src/data/`
4. Upload CSV to Google Drive

### Run individual spiders

```bash
scrapy crawl itviec -a keyword="software engineer" -a location="ho-chi-minh"

scrapy crawl topcv -a keyword="Data Engineer"

scrapy crawl linkedin -a keyword="data analyst" -a location="Vietnam"
```

## Spider Configuration

Edit `src/config/config.py`:

```python
DEFAULT_CONFIG = {
    # ITViec
    "itviec_keywords": ["software engineer", "data analyst"],
    "itviec_location": "ho-chi-minh",

    # TopCV
    "topcv_keywords": ["Data Engineer", "Data Analyst"],
    "topcv_start_page": 1,
    "topcv_end_page": 1,

    # LinkedIn
    "linkedin_keywords": ["data analyst"],
    "linkedin_location": "Vietnam",
    "linkedin_results_wanted": 50,
    "linkedin_hours_old": 72,
}
```

## Database Schema

The project uses TimescaleDB with a normalized data model:

- **jobs** — Main hypertable, partitioned by `posted_date`
- **locations**, **skills**, **domains** — Dimension tables
- **job_skills**, **job_domain** — Many-to-many associations (hypertables)
- **lsh_buckets** — MinHash LSH buckets for deduplication
- **skill_daily_stats**, **domain_daily_stats** — Continuous aggregates (auto-refreshed)

## Testing

```bash
python tests/test-itviec.py
python tests/test-topcv.py
python tests/test-linkedin.py
```

## Notes

- **Credentials** — Never commit `client_secret.json` or `token.json` to git
- **Rate limiting** — Scrapy is configured with auto-throttle and a 2s download delay
- **Concurrency** — Limited to 1 request per domain to avoid getting blocked
- **Deduplication** — Uses MinHash LSH to detect near-duplicate job listings across sources

## License

This project is developed for academic and research purposes.

---

> **Disclaimer**: This project is intended for educational and research use only. Please comply with the Terms of Service of each website when using the scrapers.
