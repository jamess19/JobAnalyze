"""
Base Job Spider - Abstract base class for job scraping spiders
"""

import scrapy
from abc import abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any
import hashlib
import random
import uuid
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from scrapy_playwright.page import PageMethod
from spiders.items import JobItem
from utils.field_extractor import FieldExtractor
from utils.normalizer import DataNormalizer


class BaseJobSpider(scrapy.Spider):
    """
    Abstract base spider for job scraping
    Provides common functionality for all job spiders
    """

    # Default settings (can be overridden by subclasses)
    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "LOG_LEVEL": "INFO",
    }

    # Playwright enabled by default (can be overridden by subclasses)
    use_playwright = True

    def __init__(self, keyword: str = "software engineer", location: str = "Ho Chi Minh", 
                start_page: int = 1, end_page: int = 1, *args, **kwargs,):
        """
        Initialize base spider

        :param keyword: Search keyword
        :param location: Search location
        :param start_page: Starting page number
        :param end_page: Ending page number
        """
        super().__init__(*args, **kwargs)
        self.keyword = keyword
        self.location = location
        self.start_page = int(start_page)
        self.end_page = int(end_page)
        self.crawl_date = datetime.now().strftime("%Y-%m-%d")

        # Initialize utilities
        self.field_extractor = FieldExtractor()
        self.normalizer = DataNormalizer()

        # Statistics
        self.jobs_scraped = 0
        self.jobs_failed = 0

        self.logger.info(f"Initialized {self.name} spider:")
        self.logger.info(f"  Keyword: {self.keyword}")
        self.logger.info(f"  Location: {self.location}")
        self.logger.info(f"  Pages: {self.start_page} to {self.end_page}")

    def create_job_item(self) -> JobItem:
        """ 
            Create a new JobItem with default metadata populated
            :return: JobItem instance
        """
        item = JobItem()
        # Set metadata
        item["crawl_date"] = self.crawl_date
        item["source"] = self.name.replace("_spider", "")  # e.g., 'itviec', 'topcv'
        # Set date_posted to crawl_date by default (can be overridden)
        item["date_posted"] = self.crawl_date
        return item

    # ── Tracking parameters to strip from job URLs ──
    # LinkedIn: trackingId, refId, trk, currentJobId, position, pageNum, origin, originalSubdomain
    # General: utm_*, fbclid
    _TRACKING_PARAMS = {
        'trackingid', 'refid', 'trk', 'currentjobid',
        'position', 'pagenum', 'origin', 'originalsubdomain',
        'fbclid',
    }
    _TRACKING_PREFIXES = ('utm_',)

    @staticmethod
    def normalize_job_url(url: str) -> str:
        """
        Normalize a job URL by stripping tracking / session query parameters.
        
        This ensures the same job posting — even with different tracking IDs
        appended by LinkedIn, Facebook, etc. — produces the same UUID v5.
        
        :param url: Raw job URL (may contain tracking params)
        :return: Cleaned URL with tracking params removed
        """
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)

        # Filter out tracking params (case-insensitive key check)
        clean_params = {}
        for key, values in params.items():
            key_lower = key.lower()
            if key_lower in BaseJobSpider._TRACKING_PARAMS:
                continue
            if any(key_lower.startswith(p) for p in BaseJobSpider._TRACKING_PREFIXES):
                continue
            clean_params[key] = values[0]  # keep first value only

        # Rebuild URL; drop query string entirely if no params remain
        new_query = urlencode(clean_params) if clean_params else ''
        return urlunparse(parsed._replace(query=new_query, fragment=''))

    def generate_job_id(self, job_url: str, source: str = None) -> str:
        """
        Generate unique UUID v5 from URL
        Uses URL as name for deterministic UUID generation
        Same URL always generates same UUID
        
        :param job_url: Job URL
        :param source: Source name (ignored, kept for backward compatibility)
        :return: UUID string
        """
        # Use URL_NAMESPACE to generate deterministic UUID v5
        # This ensures same job URL always produces same UUID
        job_uuid = uuid.uuid5(uuid.NAMESPACE_URL, job_url)
        return str(job_uuid)

    def populate_metadata(self, item: JobItem, job_url: str) -> JobItem:
        """
        Populate metadata fields in item.
        Normalizes the URL (strips tracking params) before generating job_id.
        
        :param item: JobItem to populate
        :param job_url: Job URL (raw, may contain tracking params)
        :return: Updated JobItem
        """
        # Normalize URL to strip tracking parameters before ID generation
        clean_url = self.normalize_job_url(job_url)
        
        item["job_url"] = clean_url
        item["job_id"] = self.generate_job_id(clean_url)
        item["crawl_date"] = self.crawl_date
        item["source"] = self.name.replace("_spider", "")

        # Set date_posted if not already set
        if not item.get("date_posted"):
            item["date_posted"] = self.crawl_date

        return item

    def safe_extract(self, response, selector: str, get_all: bool = False) -> Optional[Any]:
        """
        Safely extract data from response

        :param response: Scrapy response
        :param selector: CSS or XPath selector
        :param get_all: Return all matches or just first
        :return: Extracted data or None
        """
        try:
            if get_all:
                result = response.css(selector).getall()
                return result if result else None
            else:
                result = response.css(selector).get()
                return result if result else None
        except Exception as e:
            self.logger.warning(f"Error extracting with selector '{selector}': {e}")
            return None

    def safe_extract_text(self, response, selector: str) -> Optional[str]:
        """
        Safely extract and clean text from response
        :param response: Scrapy response
        :param selector: CSS or XPath selector
        :return: Cleaned text or None
        """
        result = self.safe_extract(response, selector)
        if result:
            return self.field_extractor.extract_text(result)
        return None

    def handle_error(self, failure, job_url: str = None):
        """
        Handle request failures
        :param failure: Twisted failure
        :param job_url: URL that failed
        """
        self.jobs_failed += 1
        self.logger.error(f"Request failed for {job_url}: {failure.value}")

    def make_playwright_request(
        self,
        url: str,
        callback,
        errback=None,
        meta: Dict = None,
        wait_until: str = "domcontentloaded",
        wait_for_selector: str = None,
        page_timeout: int = 30000,
    ) -> scrapy.Request:
        """
        Create a Scrapy request with Playwright rendering

        :param url: URL to request
        :param callback: Callback function
        :param errback: Error callback function
        :param meta: Additional meta data
        :param wait_until: Wait until event (load, domcontentloaded, networkidle)
        :param wait_for_selector: Optional CSS selector to wait for
        :param page_timeout: Page timeout in milliseconds
        :return: Scrapy Request with Playwright meta
        """
        playwright_meta = {
            "playwright": True,
            "playwright_include_page": False,
            "playwright_context": "default",
            "playwright_page_goto_kwargs": {
                "wait_until": wait_until,
                "timeout": page_timeout,
            },
        }

        # Add wait for selector if specified
        if wait_for_selector:
            playwright_meta["playwright_page_methods"] = [
                PageMethod(
                    "wait_for_selector", wait_for_selector, timeout=page_timeout
                ),
            ]

        # Merge with provided meta
        request_meta = {**playwright_meta, **(meta or {})}

        return scrapy.Request(
            url=url,
            callback=callback,
            errback=errback or (lambda f: self.handle_error(f, url)),
            meta=request_meta,
            dont_filter=False,
        )

    def make_request(self, url: str, callback, errback=None, meta: Dict = None, use_playwright: bool = None, **playwright_kwargs) -> scrapy.Request:
        """
        Create a request, optionally using Playwright

        :param url: URL to request
        :param callback: Callback function
        :param errback: Error callback function
        :param meta: Additional meta data
        :param use_playwright: Override spider's use_playwright setting
        :param playwright_kwargs: Additional Playwright options
        :return: Scrapy Request
        """
        should_use_playwright = (
            use_playwright if use_playwright is not None else self.use_playwright
        )

        if should_use_playwright:
            return self.make_playwright_request(url=url, callback=callback, errback=errback, meta=meta, **playwright_kwargs)
        else:
            return scrapy.Request(url=url, callback=callback, errback=errback or (lambda f: self.handle_error(f, url)), meta=meta or {})

    def closed(self, reason):
        """
        Called when spider is closed
        Log final statistics
        """
        self.logger.info(f"Spider closed: {reason}")
        self.logger.info(f"Statistics:")
        self.logger.info(f"  Jobs scraped: {self.jobs_scraped}")
        self.logger.info(f"  Jobs failed: {self.jobs_failed}")
        self.logger.info(
            f"  Success rate: {self.jobs_scraped / max(self.jobs_scraped + self.jobs_failed, 1) * 100:.2f}%"
        )

    # ── Scrapy 2.13+ compatibility ──────────────────────────────────
    # Scrapy 2.13 replaced the synchronous start_requests() with an
    # async start() method.  The default Spider.start() iterates
    # self.start_urls with plain Request objects, so our custom
    # start_requests() (which adds Playwright meta, pagination, etc.)
    # is never called unless we bridge it here.
    async def start(self):
        """Bridge: delegate to the synchronous start_requests() generator."""
        for req in self.start_requests():
            yield req

    # Abstract methods to be implemented by subclasses
    @abstractmethod
    def start_requests(self):
        """
        Generate initial requests
        Must be implemented by subclass
        """
        pass

    @abstractmethod
    def parse(self, response):
        """
        Parse search results page
        Must be implemented by subclass
        """
        pass

    @abstractmethod
    def parse_job_detail(self, response):
        """
        Parse job detail page
        Must be implemented by subclass
        """
        pass

    def parse_company(self, response, item: JobItem) -> JobItem:
        """
        Parse company page (optional, can be overridden)
        :param response: Scrapy response from company page
        :param item: JobItem to update with company info
        :return: Updated JobItem
        """
        # Default implementation - subclasses can override
        self.logger.debug(f"Parsing company page: {response.url}")
        return item
