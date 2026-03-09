# Scrapy settings for spiders project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import os
from datetime import datetime
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '.env')
print(f"[DEBUG] Loading .env from: {env_path}")
print(f"[DEBUG] File exists: {os.path.exists(env_path)}")

load_dotenv(env_path, override=True, verbose=True)  # verbose=True để debug


BOT_NAME = "spiders_job"

SPIDER_MODULES = ["spiders.spiders"]
NEWSPIDER_MODULE = "spiders.spiders"

ADDONS = {}

# ============================================================
# DATABASE CONFIGURATION
# ============================================================
# PostgreSQL/TimescaleDB connection string
# Format: postgresql://user:password@host:port/database
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'localhost://postgres:password@localhost:5433/job_market'
)

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False  # Set to False for job boards that may block crawlers

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 1  # Single request at a time to avoid anti-bot detection

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 5
RANDOMIZE_DOWNLOAD_DELAY = True  # Random delay between 0.5x and 1.5x DOWNLOAD_DELAY
# The download delay setting will honor only one of:
CONCURRENT_REQUESTS_PER_DOMAIN = 1
#CONCURRENT_REQUESTS_PER_IP = 16

# ── FIFO scheduling (breadth-first) ──
# Scrapy mặc định dùng LIFO (stack → depth-first), khiến request yield SAU
# lại được xử lý TRƯỚC. Chuyển sang FIFO (queue → breadth-first) để detail
# pages được xử lý đúng thứ tự xuất hiện trên trang listing.
DEPTH_PRIORITY = 1  # request yield trước → priority cao hơn
SCHEDULER_DISK_QUEUE = "scrapy.squeues.PickleFifoDiskQueue"
SCHEDULER_MEMORY_QUEUE = "scrapy.squeues.FifoMemoryQueue"

# Disable cookies (enabled by default)
COOKIES_ENABLED = True
# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
   "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
   "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
   "Accept-Encoding": "gzip, deflate, br",
   "Connection": "keep-alive",
   "Upgrade-Insecure-Requests": "1",
}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "spiders.middlewares.SpidersSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
   "spiders.middlewares.ProxyRotationMiddleware": 350,
   "spiders.middlewares.RotatingUserAgentMiddleware": 400,
   "spiders.middlewares.RateLimitBackoffMiddleware": 450,
   "spiders.middlewares.SpidersDownloaderMiddleware": 543,
}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
# Pipeline order: validation -> normalization -> deduplication -> export
ITEM_PIPELINES = {
   "pipelines.validation.ValidationPipeline": 100,
   "pipelines.cleaning.CleaningPipeline": 200,
   "pipelines.skill_extraction.SkillExtractionPipeline": 250,  # NLP skill/domain extraction
   "pipelines.deduplication.DeduplicationPipeline": 300,
   "pipelines.database.DatabasePipeline": 400,
   "pipelines.export.ExportPipeline": 500,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
AUTOTHROTTLE_START_DELAY = 2
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 120
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = False  # Disabled - no cache files created

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403, 400]
RETRY_PRIORITY_ADJUST = -1

# Redirect settings
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 5

# Timeout settings
DOWNLOAD_TIMEOUT = 30

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"

# ============================================================
# Playwright Settings
# ============================================================
# Download handlers for Playwright
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# Playwright browser settings
PLAYWRIGHT_BROWSER_TYPE = "chromium"  # Options: chromium, firefox, webkit
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 60000,  # Browser launch timeout
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-gpu",
    ],
}
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 1  # One page at a time to avoid overload

# Default Playwright context options (browser-like settings)
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "locale": "vi-VN",
        "timezone_id": "Asia/Ho_Chi_Minh",
        "java_script_enabled": True,
        "ignore_https_errors": True,
    }
}

# Abort unnecessary resource types to speed up crawling
# PLAYWRIGHT_ABORT_REQUEST = lambda req: req.resource_type in ["image", "media", "font", "stylesheet"]

# Logging settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"
LOG_STDOUT = True  # Enable console output

# Log file with timestamp (will be set dynamically in spider/runner)
from datetime import datetime
LOG_FILE = f"logs/scrapy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
LOG_FILE_APPEND = False  # Create new log file each run
LOG_ENCODING = "utf-8"

# ── Suppress Scrapy's verbose "Dropped:" item dump ──
# When DropItem is raised, Scrapy logs the ENTIRE item dict as WARNING.
# Our pipeline already logs a concise DUPLICATE FOUND / Batch duplicate INFO line,
# so the full item dump is redundant and bloats the log file.
import logging

class _DropItemLogFilter(logging.Filter):
    """Filter out 'Dropped:' WARNING messages from scrapy.core.scraper."""
    def filter(self, record):
        if record.levelno == logging.WARNING and isinstance(record.msg, str):
            return not record.msg.startswith("Dropped:")
        return True

# Attach filter at import time so it's active before any spider runs
logging.getLogger("scrapy.core.scraper").addFilter(_DropItemLogFilter())

# Custom settings for output
OUTPUT_DIR = "data"  # Changed from "data/output" to "data"
SEEN_JOBS_FILE = "data/seen_jobs.txt"

# Feed exports (alternative to ExportPipeline)
# Uncomment to use Scrapy's built-in feed exports instead
# FEEDS = {
#     'data/output/%(name)s_%(time)s.csv': {
#         'format': 'csv',
#         'encoding': 'utf-8-sig',
#         'overwrite': False,
#     },
#     'data/output/%(name)s_%(time)s.json': {
#         'format': 'json',
#         'encoding': 'utf-8',
#         'indent': 2,
#         'overwrite': False,
#     },
# }

# Memory usage settings
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048
MEMUSAGE_WARNING_MB = 1024

# Stats collection
STATS_DUMP = True

# Request fingerprinter
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_INDENT = 2
