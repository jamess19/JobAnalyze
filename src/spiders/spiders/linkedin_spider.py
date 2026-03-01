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

    # JavaScript that runs inside Playwright's event loop to scroll the
    # infinite-scroll job list before the response is returned to parse().
    _SCROLL_JS = """
    (async () => {
        const maxScrolls = 30;
        let noChangeCount = 0;
        for (let i = 0; i < maxScrolls; i++) {
            const btn = document.querySelector(
                'button.infinite-scroller__show-more-button--visible'
            );
            if (btn) {
                btn.click();
                await new Promise(r => setTimeout(r, 5000));
                noChangeCount = 0;
                continue;
            }
            const prevHeight = document.body.scrollHeight;
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(r => setTimeout(r, 4000));
            const newHeight = document.body.scrollHeight;
            if (newHeight <= prevHeight) {
                noChangeCount++;
                if (noChangeCount >= 2) break;
            } else {
                noChangeCount = 0;
            }
        }
    })()
    """

    def generate_search_requests(self):
        """Yield one Playwright search request per keyword.

        All scroll / click-'See more jobs' logic runs as a JavaScript
        PageMethod inside Playwright's own event loop, so no async parse
        coroutine is required and there is no event-loop mismatch.
        """
        self.logger.info(
            f"Starting LinkedIn search: {len(self.keywords)} keyword(s), "
            f"location='{self.location}', "
            f"login={'yes' if self.is_logged_in else 'no'}"
        )
        for keyword in self.keywords:
            kw_enc  = keyword.replace(" ", "%20")
            loc_enc = self.location.replace(" ", "%20")
            url = f"{self.base_url}/jobs/search/?keywords={kw_enc}&location={loc_enc}&start=0"
            self.logger.info(f"Queuing keyword: '{keyword}' → {url}")
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=lambda f, u=url: self.handle_error(f, u),
                meta={
                    "playwright": True,
                    "playwright_page_goto_kwargs": {
                        "wait_until": "domcontentloaded",
                        "timeout": 60000,
                    },
                    "playwright_page_coroutines": [
                        PageMethod("evaluate", self._SCROLL_JS),
                    ],
                    "keyword": keyword,
                },
                dont_filter=True,
            )

    def parse(self, response):
        """
        Parse LinkedIn search results.

        By the time this callback is invoked, scrapy-playwright has already
        executed _SCROLL_JS inside its own event loop (via page_coroutines),
        so response.text contains the fully-scrolled page HTML.  No async /
        await is needed here, which avoids the "different event loop" error.
        """
        keyword = response.meta.get("keyword", "")

        # Reset per-keyword dup state so each keyword starts fresh.
        self.should_stop = False
        self.consecutive_dup_count = 0

        self.logger.info(f"[{keyword}] Parsing scrolled results: {response.url}")

        cutoff_follow = (
            (self._max_date - timedelta(days=self.DATE_FOLLOW_DAYS))
            if self._max_date else None
        )

        job_cards = response.css('div.job-search-card')
        if not job_cards:
            self.logger.warning(f"[{keyword}] No job cards found in response.")
            return

        self.logger.info(f"[{keyword}] {len(job_cards)} job cards to process.")
        seen_urls: set = set()
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

            # ── Date filter: skip old cards ──────────────────────────────────
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

            self.logger.debug(f"[{keyword}] Queuing job detail: {job_url}")
            yield self.make_request(
                url=job_url,
                callback=self.parse_job_detail,
                meta={'basic_info': basic_info},
                use_playwright=True,
            )
            queued += 1

        self.logger.info(f"[{keyword}] Done: {queued}/{len(seen_urls)} cards queued for detail.")

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
