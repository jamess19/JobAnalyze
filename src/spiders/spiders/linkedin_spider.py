"""
LinkedIn Spider - Scrape job listings from linkedin.com
Strategy:
  - One spider instance processes all keywords sequentially.
  - Uses Playwright to scroll the infinite-scroll page and click "See more jobs".
  - Date filter: if max(posted_date) exists in DB for 'linkedin' source, skip individual
    cards older than T - DATE_FOLLOW_DAYS, but NEVER stop pagination on date alone.
  - Stops only when consecutive duplicate count >= MAX_CONSECUTIVE_DUPS.
"""

import scrapy
import re
from urllib.parse import urljoin
from scrapy_playwright.page import PageMethod
from spiders.spiders.base_spider import BaseJobSpider
from spiders.items import JobItem
from datetime import datetime, timedelta
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
    DATE_FOLLOW_DAYS     = 2   # skip card if posted_date < T - N days (but never stop)

    def __init__(self, keywords=None, *args, **kwargs):
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
        self._max_date = None
        self.should_stop = False
        self.consecutive_dup_count = 0
        self.per_keyword_stop = True   # stop per-keyword, not entire spider

    def _init_db(self):
        """Load T = max(posted_date) từ DB, lọc theo source 'linkedin'."""
        from models.base import get_engine, get_session_factory
        from repositories.job_repository import JobRepository
        engine = get_engine(self.settings.get("DATABASE_URL"))
        session_factory = get_session_factory(engine)
        repo = JobRepository(session_factory)
        source = self.name.replace("_spider", "")  # 'linkedin'
        max_date = repo.get_max_posted_date(source=source)
        if max_date:
            self._max_date = max_date.date() if hasattr(max_date, 'date') else max_date
            self.logger.info(
                f"Smart crawl [linkedin]: T = {self._max_date} "
                f"(skip cards older than T-{self.DATE_FOLLOW_DAYS}d, "
                f"stop on {self.MAX_CONSECUTIVE_DUPS} consecutive dups)"
            )
        else:
            self._max_date = None
            self.logger.info("Smart crawl [linkedin]: No existing data → full crawl mode (no date filter)")

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

    # How many jobs per API page (LinkedIn uses 25)
    _PAGE_SIZE = 25

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
        """
        cutoff_follow = (
            (self._max_date - timedelta(days=self.DATE_FOLLOW_DAYS))
            if self._max_date else None
        )

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

            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            # ── Date filter ──
            date_attr = (
                job_card.css('time.job-search-card__listdate::attr(datetime)').get()
                or job_card.css('time.job-search-card__listdate--new::attr(datetime)').get()
            )
            posted_date = None
            if date_attr:
                try:
                    posted_date = datetime.strptime(date_attr[:10], '%Y-%m-%d').date()
                except ValueError:
                    pass

            if posted_date and cutoff_follow and posted_date < cutoff_follow:
                self.logger.debug(
                    f"[{keyword}] Skipping old card ({posted_date} < {cutoff_follow}): {job_url}"
                )
                continue

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
        job count, then yield API requests for subsequent pages.
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

        # ── Yield API requests for remaining pages ──
        kw_enc  = keyword.replace(" ", "%20")
        loc_enc = self.location.replace(" ", "%20")

        for start in range(self._PAGE_SIZE, target_count, self._PAGE_SIZE):
            api_url = self._API_TPL.format(
                base=self.base_url, kw=kw_enc, loc=loc_enc, start=start
            )
            self.logger.info(f"[{keyword}] Queuing API page start={start}")
            yield scrapy.Request(
                url=api_url,
                callback=self.parse_api_page,
                errback=lambda f, u=api_url: self.handle_error(f, u),
                meta={"keyword": keyword, "start": start},
                dont_filter=True,
            )

    def parse_api_page(self, response):
        """Parse an API pagination page (plain HTML fragment, no Playwright)."""
        keyword = response.meta.get("keyword", "")
        start = response.meta.get("start", "?")

        job_cards = response.css('div.job-search-card')
        if not job_cards:
            self.logger.info(f"[{keyword}] API page start={start}: no cards (end of results).")
            return

        self.logger.info(f"[{keyword}] API page start={start}: {len(job_cards)} cards.")

        requests, queued = self._extract_cards(response, keyword)
        for req in requests:
            yield req

        self.logger.info(f"[{keyword}] API page start={start}: {queued} cards queued for detail.")

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
            description = ' '.join([t.strip() for t in description_texts if t.strip()])

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
