"""
LinkedIn Spider - Scrape job listings from linkedin.com
"""

import scrapy
import re
from urllib.parse import urljoin
from spiders.spiders.base_spider import BaseJobSpider
from spiders.items import JobItem
from datetime import datetime
from config.config import LINKEDIN_EMAIL, LINKEDIN_PASSWORD


class LinkedinSpider(BaseJobSpider):
    """Spider for scraping jobs from linkedin.com"""

    name = "linkedin_spider"
    allowed_domains = ["www.linkedin.com", "linkedin.com"]

    # Enable Playwright for this spider
    use_playwright = True

    custom_settings = {
        'DOWNLOAD_DELAY': 5,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'RETRY_TIMES': 3,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.linkedin.com"
        self.login_url = "https://www.linkedin.com/login"
        self.is_logged_in = False

        # Check if credentials are configured
        self.has_credentials = bool(LINKEDIN_EMAIL and LINKEDIN_PASSWORD)
        if not self.has_credentials:
            self.logger.warning("LinkedIn credentials not configured. Some jobs may not be accessible.")
    
    def start_requests(self):
        """Generate initial requests - login first if credentials available"""
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
        """Handle LinkedIn login using Playwright page"""
        page = response.meta["playwright_page"]

        try:
            self.logger.info("Attempting to login to LinkedIn...")

            # Fill email
            await page.fill('input#username', LINKEDIN_EMAIL)
            await page.wait_for_timeout(500)

            # Fill password
            await page.fill('input#password', LINKEDIN_PASSWORD)
            await page.wait_for_timeout(500)

            # Click login button
            await page.click('button[type="submit"]')

            # Wait for navigation after login
            await page.wait_for_load_state("networkidle", timeout=30000)

            # Check if login successful by looking for feed or profile elements
            current_url = page.url
            if "/feed" in current_url or "/in/" in current_url or "/jobs" in current_url:
                self.is_logged_in = True
                self.logger.info("LinkedIn login successful!")
            elif "/checkpoint" in current_url or "/challenge" in current_url:
                self.logger.warning("LinkedIn requires verification. Manual intervention may be needed.")
                self.is_logged_in = False
            else:
                # Check for error messages
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

        # Continue with search requests regardless of login status
        for request in self.generate_search_requests():
            yield request

    def handle_login_error(self, failure):
        """Handle login request failure"""
        self.logger.error(f"LinkedIn login request failed: {failure.value}")
        self.is_logged_in = False
        # Continue without login
        yield from self.generate_search_requests()

    def generate_search_requests(self):
        """Generate search page requests"""
        keyword = self.keyword.replace(" ", "%20")
        location = self.location.replace(" ", "%20")

        self.logger.info(f"Starting LinkedIn search with keyword='{self.keyword}', location='{self.location}'")
        self.logger.info(f"Login status: {'Logged in' if self.is_logged_in else 'Not logged in'}")

        for page in range(self.start_page, self.end_page + 1):
            # LinkedIn uses offset-based pagination
            offset = page * 25
            url = f"{self.base_url}/jobs/search/?keywords={keyword}&location={location}&start={offset}"

            self.logger.info(f"Requesting search page {page}: {url}")

            yield self.make_request(
                url=url,
                callback=self.parse,
                meta={'page': page},
            )
    
    def parse(self, response):
        """
        Parse search results page
        Extract job links and basic info
        """
        page = response.meta.get('page', 1)
        self.logger.info(f"Parsing search page {page}: {response.url}")
        
        # LinkedIn job card selector (may need adjustment based on current HTML structure)
        job_cards = response.css('div.job-search-card') or response.css('li.jobs-search-results__list-item')
        
        if not job_cards:
            self.logger.warning(f"No job items found on page {page}")
            return
        
        self.logger.info(f"Found {len(job_cards)} job items on page {page}")
        
        for job_card in job_cards:
            # Extract job URL
            job_link = job_card.css('a.base-card__full-link::attr(href)').get()

            if not job_link:
                continue

            job_url = urljoin(self.base_url, job_link)

            # Convert regional LinkedIn URLs (e.g., vn.linkedin.com) to www.linkedin.com
            job_url = re.sub(r'https?://[a-z]{2}\.linkedin\.com', 'https://www.linkedin.com', job_url)
            
            # Extract basic info from search page
            basic_info = {
                'title': self.safe_extract_text(job_card, 'h3.base-search-card__title::text, h4::text'),
                'company': self.safe_extract_text(job_card, 'h4.base-search-card__subtitle::text, a.hidden-nested-link::text'),
                'location': self.safe_extract_text(job_card, 'span.job-search-card__location::text'),
            }
            
            self.logger.debug(f"Following job URL: {job_url}")

            yield self.make_request(
                url=job_url,
                callback=self.parse_job_detail,
                meta={'basic_info': basic_info},
            )
    
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
        # LinkedIn usually shows "Posted X days ago" or similar
        date_posted_elem = response.css('span.posted-time-ago__text::text').get()
        if date_posted_elem:
            extra_data['date_posted_raw'] = date_posted_elem.strip()
        # Set date_posted to crawl date (can be improved with date parsing)
        item['date_posted'] = datetime.now().strftime('%Y-%m-%d')

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
