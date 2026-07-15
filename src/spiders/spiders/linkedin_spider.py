"""
LinkedIn Spider - Scrape job listings from linkedin.com
Strategy:
  - One spider instance processes all keywords sequentially.
  - First page loaded via Playwright to read target count, then API pagination.
  - LinkedIn does NOT sort by date, so no date-based filtering is used.
  - Stops only when consecutive duplicate count >= MAX_CONSECUTIVE_DUPS (checked
    by the DeduplicationPipeline via Jaccard similarity against DB).
"""

import scrapy
import re
from urllib.parse import urljoin
from scrapy_playwright.page import PageMethod
from spiders.spiders.base_spider import BaseJobSpider
from spiders.items import JobItem
from datetime import datetime
from config.config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD


class LinkedinSpider(BaseJobSpider):
    """Spider for scraping jobs from linkedin.com"""

    name = "linkedin_spider"
    allowed_domains = ["www.linkedin.com", "linkedin.com"]

    use_playwright = True

    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'CONCURRENT_REQUESTS': 1,
        'RETRY_TIMES': 3,
    }

    # Smart crawl settings
    MAX_CONSECUTIVE_DUPS = 15

    def __init__(self, keywords=None, max_pages: int = None, *args, **kwargs):
        self.max_pages = int(max_pages) if max_pages else None  # giới hạn số trang API mỗi keyword (None = không giới hạn)

        # Accept either keywords (list) from ScraperService or keyword (str) from run_spiders.py
        if keywords and isinstance(keywords, list):
            self.keywords = keywords
            first_kw = keywords[0]
        elif keywords and isinstance(keywords, str):
            # run_spiders.py passes a single keyword string
            self.keywords = [keywords]
            first_kw = keywords
        else:
            # run_spiders.py passes keyword= (singular) → pop to avoid duplicate kwarg to super()
            single_kw = kwargs.pop('keyword', 'Software Engineer')
            self.keywords = [single_kw]
            first_kw = single_kw

        # Pass first keyword to base class so self.keyword, self.location, etc. are set
        super().__init__(keyword=first_kw, *args, **kwargs)

        self.base_url = "https://www.linkedin.com"
        self.login_url = "https://www.linkedin.com/login"
        self.is_logged_in = False

        self.has_credentials = bool(LINKEDIN_EMAIL and LINKEDIN_PASSWORD)
        if not self.has_credentials:
            self.logger.warning("LinkedIn credentials not configured. Some jobs may not be accessible.")

        # Smart crawl state
        self.should_stop = False
        self.consecutive_dup_count = 0
        self.per_keyword_stop = True   # stop per-keyword, not entire spider

    def _init_db(self):
        """Check DB for existing linkedin data (used for logging only;
        actual dedup is handled by DeduplicationPipeline)."""
        from models.base import get_engine, get_session_factory
        from repositories.job_repository import JobRepository
        engine = get_engine(self.settings.get("DATABASE_URL"))
        session_factory = get_session_factory(engine)
        repo = JobRepository(session_factory)
        source = self.name.replace("_spider", "")  # 'linkedin'
        max_date = repo.get_max_posted_date(source=source)
        if max_date:
            self.logger.info(
                f"Smart crawl [linkedin]: DB has data up to {max_date} "
                f"(stop on {self.MAX_CONSECUTIVE_DUPS} consecutive dups)"
            )
        else:
            self.logger.info(
                f"Smart crawl [linkedin]: No existing data → full crawl "
                f"(stop on {self.MAX_CONSECUTIVE_DUPS} consecutive dups)"
            )

    def start_requests(self):
        """Generate initial requests - login first if credentials available."""
        self._init_db()
        if self.has_credentials:
            self.logger.info("LinkedIn credentials found. Starting login process...")
            yield scrapy.Request(
                url=self.login_url,
                callback=self.login,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "networkidle",
                        "timeout": 60000,
                    },
                },
                errback=self.handle_login_error,
            )
        else:
            self.logger.info("No LinkedIn credentials. Proceeding without login...")
            yield from self.generate_search_requests()

    async def login(self, response):
        """Handle LinkedIn login using Playwright page."""
        page = response.meta["playwright_page"]
        try:
            self.logger.info("Attempting to login to LinkedIn...")
            await page.fill('input#username', LINKEDIN_EMAIL)
            await page.wait_for_timeout(500)
            await page.fill('input#password', LINKEDIN_PASSWORD)
            await page.wait_for_timeout(500)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=30000)

            current_url = page.url
            if "/feed" in current_url or "/in/" in current_url or "/jobs" in current_url:
                self.is_logged_in = True
                self.logger.info("LinkedIn login successful!")
            elif "/checkpoint" in current_url or "/challenge" in current_url:
                self.logger.warning("LinkedIn requires verification. Manual intervention may be needed.")
            else:
                error_elem = await page.query_selector('div#error-for-username, div#error-for-password, div.alert')
                if error_elem:
                    error_text = await error_elem.text_content()
                    self.logger.error(f"LinkedIn login failed: {error_text}")
                else:
                    self.logger.warning(f"LinkedIn login status unclear. Current URL: {current_url}")
                self.is_logged_in = False
        except Exception as e:
            self.logger.error(f"Error during LinkedIn login: {e}")
            self.is_logged_in = False
        finally:
            await page.close()

        for request in self.generate_search_requests():
            yield request

    def handle_login_error(self, failure):
        """Handle login request failure."""
        self.logger.error(f"LinkedIn login request failed: {failure.value}")
        self.is_logged_in = False
        yield from self.generate_search_requests()

    # JavaScript executed inside Playwright's own event loop (via PageMethod)
    # to scroll the infinite-scroll job list.  Because scrapy-playwright runs
    # Playwright on a separate thread we CANNOT call page.evaluate() from the
    # spider callback — that causes "different event loop" errors.
    #
    # LinkedIn uses infinite scroll + "See more jobs" button cycling.
    # The target card count is read dynamically from the page header.
    _SCROLL_JS = """
    (async () => {
        const sleep = ms => new Promise(r => setTimeout(r, ms));
        const startTime = Date.now();
        const MAX_RUNTIME = 5 * 60 * 1000;  /* 5 minutes hard cap */

        const dismissModals = () => {
            for (const sel of [
                'button[data-tracking-control-name="public_jobs_contextual-sign-in-modal_modal_dismiss"]',
                '.modal__dismiss',
                '.contextual-sign-in-modal__modal-dismiss',
                'button[aria-label="Dismiss"]'
            ]) {
                const el = document.querySelector(sel);
                if (el) { el.click(); break; }
            }
        };

        const getCardCount = () =>
            document.querySelectorAll('div.job-search-card').length;

        const getTargetCount = () => {
            const el = document.querySelector('.results-context-header__job-count')
                    || document.querySelector('h1');
            if (el) {
                const m = el.textContent.replace(/,/g, '').match(/(\\d+)/);
                if (m) return parseInt(m[1], 10);
            }
            return 1000;
        };

        const clickSeeMore = () => {
            const btn = document.querySelector(
                'button.infinite-scroller__show-more-button--visible'
            ) || document.querySelector(
                'button.infinite-scroller__show-more-button'
            ) || document.querySelector(
                'button[aria-label="See more jobs"]'
            );
            if (btn) {
                btn.scrollIntoView();
                btn.click();
                return true;
            }
            return false;
        };

        /* ── config ────────────────────────────────────────────── */
        const MAX_ATTEMPTS   = 100;
        const SCROLL_WAIT    = 3000;
        const BTN_WAIT       = 5000;
        const NO_CHANGE_MAX  = 8;

        const target = getTargetCount();
        let noChangeCount = 0;

        for (let i = 0; i < MAX_ATTEMPTS; i++) {
            /* Hard time limit */
            if (Date.now() - startTime > MAX_RUNTIME) break;

            dismissModals();

            const prevCards = getCardCount();
            if (prevCards >= target) break;

            /* 1. Try "See more jobs" button */
            if (clickSeeMore()) {
                await sleep(BTN_WAIT);
                /* Only reset noChangeCount if cards actually increased */
                if (getCardCount() > prevCards) {
                    noChangeCount = 0;
                } else {
                    noChangeCount++;
                }
                if (noChangeCount >= NO_CHANGE_MAX) break;
                continue;
            }

            /* 2. Scroll down */
            window.scrollTo(0, document.body.scrollHeight);
            await sleep(SCROLL_WAIT);

            /* 3. Check progress */
            const newCards = getCardCount();
            if (newCards > prevCards) {
                noChangeCount = 0;
            } else {
                noChangeCount++;
                if (noChangeCount >= NO_CHANGE_MAX) break;
            }
        }
    })()
    """

    # LinkedIn guest API for pagination – returns HTML fragments with ~25
    # job cards per page.  `start` increments by 25.
    _API_TPL = "{base}/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={kw}&location={loc}&start={start}"

    # How many jobs per API page (LinkedIn guest API returns 10 per page)
    _PAGE_SIZE = 10

    # Maximum start offset to try (LinkedIn caps guest results ~1000)
    _MAX_START = 1000

    def generate_search_requests(self):
        """Yield one Playwright request per keyword (page 0) to read total count,
        then API requests for pages 1..N are generated in parse_first_page.
        """
        self.logger.info(
            f"Starting LinkedIn search: {len(self.keywords)} keyword(s), "
            f"location='{self.location}', "
            f"login={'yes' if self.is_logged_in else 'no'}"
        )
        for keyword in self.keywords:
            kw_enc  = keyword.replace(" ", "%20")
            loc_enc = self.location.replace(" ", "%20")
            # First page uses the normal search URL with Playwright to get the
            # target count from the page header and the first batch of cards.
            url = f"{self.base_url}/jobs/search/?keywords={kw_enc}&location={loc_enc}&start=0"
            self.logger.info(f"Queuing keyword: '{keyword}' → {url}")
            yield scrapy.Request(
                url=url,
                callback=self.parse_first_page,
                errback=lambda f, u=url: self.handle_error(f, u),
                meta={
                    "playwright": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "domcontentloaded",
                        "timeout": 120000,  # 2 min for first page
                    },
                    "playwright_page_methods": [
                        PageMethod("evaluate", self._SCROLL_JS),
                    ],
                    "keyword": keyword,
                },
                dont_filter=True,
            )

    # ── parse helpers ─────────────────────────────────────────────────────

    def _extract_cards(self, response, keyword):
        """Extract job cards from a response.
        Returns (list_of_requests, queued_count).
        No date filtering — LinkedIn doesn't sort by date.
        Dedup is handled downstream by DeduplicationPipeline.
        """
        job_cards = response.css('div.job-search-card')
        if not job_cards:
            return [], 0

        seen_urls: set = set()
        requests = []
        queued = 0

        for job_card in job_cards:
            job_link = job_card.css('a.base-card__full-link::attr(href)').get()
            if not job_link:
                continue

            job_url = urljoin(self.base_url, job_link)
            job_url = re.sub(
                r'https?://[a-z]{2}\.linkedin\.com',
                'https://www.linkedin.com',
                job_url
            )

            # Normalize URL: strip tracking params (trackingId, refId, etc.)
            job_url = self.normalize_job_url(job_url)

            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            # ── Extract date (for metadata only, NOT for filtering) ──
            date_attr = (
                job_card.css('time.job-search-card__listdate::attr(datetime)').get()
                or job_card.css('time.job-search-card__listdate--new::attr(datetime)').get()
            )

            basic_info = {
                'title':       job_card.css('h3.base-search-card__title::text').get('').strip(),
                'company':     job_card.css('h4.base-search-card__subtitle a::text, a.hidden-nested-link::text').get('').strip(),
                'location':    job_card.css('span.job-search-card__location::text').get('').strip(),
                'date_posted': date_attr[:10] if date_attr else None,
            }

            requests.append(self.make_request(
                url=job_url,
                callback=self.parse_job_detail,
                meta={'basic_info': basic_info},
                use_playwright=True,
            ))
            queued += 1

        return requests, queued

    def parse_first_page(self, response):
        """Parse the first page (loaded via Playwright) to get the total
        job count, then yield a CHAINED API request for the next page.
        Each API page will chain to the next, checking should_stop.
        """
        keyword = response.meta.get("keyword", "")
        self.should_stop = False
        self.consecutive_dup_count = 0

        self.logger.info(f"[{keyword}] Parsing first page: {response.url}")

        # ── Extract target count from page header ──
        target_text = (
            response.css('.results-context-header__job-count::text').get('')
            or response.css('h1::text').get('')
        )
        target_count = 1000  # default
        m = re.search(r'([\d,]+)', target_text.replace(',', ''))
        if m:
            target_count = int(m.group(1))
        target_count = min(target_count, self._MAX_START)
        self.logger.info(f"[{keyword}] Target job count: {target_count}")

        # ── Extract cards from first page ──
        requests, queued = self._extract_cards(response, keyword)
        for req in requests:
            yield req

        self.logger.info(f"[{keyword}] First page: {queued} cards queued.")

        # ── max_pages: page 1 is this Playwright-loaded page; stop here if limited to 1 ──
        if self.max_pages and self.max_pages <= 1:
            self.logger.info(f"[{keyword}] Reached max_pages={self.max_pages}, stopping pagination.")
            return

        # ── Chain to first API page (start=PAGE_SIZE) ──
        first_start = self._PAGE_SIZE
        if first_start < target_count:
            yield from self._yield_next_api_page(keyword, first_start, target_count)

    def _yield_next_api_page(self, keyword, start, target_count):
        """Yield a single API request for the given start offset.
        The callback (parse_api_page) will chain to the next page.
        """
        kw_enc  = keyword.replace(" ", "%20")
        loc_enc = self.location.replace(" ", "%20")
        api_url = self._API_TPL.format(
            base=self.base_url, kw=kw_enc, loc=loc_enc, start=start
        )
        self.logger.info(f"[{keyword}] Queuing API page start={start}")
        yield scrapy.Request(
            url=api_url,
            callback=self.parse_api_page,
            errback=lambda f, u=api_url: self.handle_error(f, u),
            meta={
                "keyword": keyword,
                "start": start,
                "target_count": target_count,
            },
            dont_filter=True,
        )

    def parse_api_page(self, response):
        """Parse an API pagination page, then chain to the next page
        unless should_stop is True or we've reached the target count.
        """
        keyword = response.meta.get("keyword", "")
        start = response.meta.get("start", 0)
        target_count = response.meta.get("target_count", self._MAX_START)

        # ── Check early stop BEFORE processing ──
        if self.should_stop:
            self.logger.info(
                f"[{keyword}] Stopping API pagination at start={start} "
                f"(should_stop=True, {self.consecutive_dup_count} consecutive dups)"
            )
            return

        job_cards = response.css('div.job-search-card')
        if not job_cards:
            self.logger.info(f"[{keyword}] API page start={start}: no cards (end of results).")
            return

        self.logger.info(f"[{keyword}] API page start={start}: {len(job_cards)} cards.")

        requests, queued = self._extract_cards(response, keyword)
        for req in requests:
            yield req

        self.logger.info(f"[{keyword}] API page start={start}: {queued} cards queued for detail.")

        # ── max_pages: start=PAGE_SIZE is page 2 (page 1 = initial Playwright load) ──
        current_page = (start // self._PAGE_SIZE) + 1
        if self.max_pages and current_page >= self.max_pages:
            self.logger.info(f"[{keyword}] Reached max_pages={self.max_pages}, stopping pagination.")
            return

        # ── Chain to next page (if not stopped and within target) ──
        next_start = start + self._PAGE_SIZE
        if next_start < target_count and not self.should_stop:
            yield from self._yield_next_api_page(keyword, next_start, target_count)

    def parse_job_detail(self, response):
        """
        Parse job detail page - LinkedIn
        Chỉ lấy các field có trong JobItem schema
        """
        self.logger.info(f"Parsing job detail: {response.url}")
        
        basic_info = response.meta.get('basic_info', {})
        item = self.create_job_item()
        item = self.populate_metadata(item, response.url)
        
        extra_data = {}

        # ==================== 1. TITLE ====================
        title = response.css('h1.top-card-layout__title::text').get()
        if not title:
            title = response.css('h2.topcard__title::text').get()
        
        item['title'] = title.strip() if title else basic_info.get('title')

        # ==================== 2. COMPANY ====================
        company = response.css('a.topcard__org-name-link::text').get()
        if not company:
            company = response.css('span.topcard__flavor::text').get()
        
        item['company_name'] = company.strip() if company else basic_info.get('company')

        # ==================== 3. LOCATION ====================
        location = response.css('span.topcard__flavor--bullet::text').get()
        if not location:
            location = basic_info.get('location')
        
        if location:
            item['location_raw'] = location.strip()
            # Parse location and save to extra_data
            location_data = self.field_extractor.parse_location(location.strip())
            extra_data['location_city'] = location_data.get('city')

        # ==================== 4. DATE POSTED ====================
        date_posted_elem = response.css('span.posted-time-ago__text::text').get()
        if date_posted_elem:
            extra_data['date_posted_raw'] = date_posted_elem.strip()
        # Ưu tiên date đã parse từ card (ISO format), fallback về crawl_date
        card_date = basic_info.get('date_posted')
        item['date_posted'] = card_date if card_date else datetime.now().strftime('%Y-%m-%d')

        # ==================== 5. DESCRIPTION ====================
        # LinkedIn typically has job description in div.description__text
        desc_elem = response.css('div.description__text, div.show-more-less-html__markup')

        if desc_elem:
            # Get all text from description
            description_texts = desc_elem.css('::text').getall()
            description = '\n'.join([t.strip() for t in description_texts if t.strip()])

            item['description'] = description
            # Also save to requirements as LinkedIn doesn't separate sections
            item['requirements'] = description

        # ==================== 6. SKILLS ====================
        # Skills might be in a separate section
        skills = response.css('span.job-criteria__text::text').getall()
        if skills:
            item['skills_tags'] = [s.strip() for s in skills if s.strip()]

        # ==================== 7. SALARY ====================
        # LinkedIn may not always show salary
        salary = response.css('span.salary::text').get()
        if salary:
            item['salary_raw'] = salary.strip()

        # ==================== 8. EXTRA DATA ====================
        # Job level, employment type, etc.
        criteria_items = response.css('li.description__job-criteria-item')
        for criteria in criteria_items:
            label = criteria.css('h3::text').get()
            value = criteria.css('span::text').get()
            if label and value:
                extra_data[label.strip()] = value.strip()

        # Infer Fields and save to extra_data
        if item.get('title') and item.get('description_full'):
            extra_data['job_category'] = self.normalizer.infer_job_category(
                item['title'], 
                item['description_full']
            )
            extra_data['job_level'] = self.normalizer.infer_job_level(item['title'])
            extra_data['work_mode'] = self.normalizer.infer_work_mode(
                item['description_full'], 
                item['title']
            )
        
        # Save extra_data to item
        item['extra_data'] = extra_data

        self.jobs_scraped += 1
        yield item
