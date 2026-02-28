"""
ITViec Spider - Scrape job listings from itviec.com
"""

import re
import scrapy
from urllib.parse import urljoin
from datetime import timedelta, datetime, date

# Use absolute imports
from spiders.spiders.base_spider import BaseJobSpider
from spiders.items import JobItem
from utils import utils

class ItviecSpider(BaseJobSpider):
    """Spider for scraping jobs from itviec.com"""

    name = "itviec_spider"
    allowed_domains = ["itviec.com"]

    # Enable Playwright for this spider
    use_playwright = True

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'RETRY_TIMES': 3,
    }

    # Smart crawl settings
    MAX_CONSECUTIVE_DUPS = 15   # stop if this many consecutive duplicate jobs
    DATE_FOLLOW_DAYS    = 2    # follow detail page only if posted_date >= T - N days
    DATE_STOP_DAYS      = 3    # stop pagination if posted_date < T - N days

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://itviec.com"

        # Smart crawl state
        self._max_date: date | None = None   # T = max(posted_date) from DB
        self.consecutive_dup_count = 0       # updated by DeduplicationPipeline
        self.should_stop = False             # set True to stop pagination

    def _init_db(self):
        """Load T = max(posted_date) from DB."""
        if self._max_date is not None:
            return
        from models.base import get_engine, get_session_factory
        from repositories.job_repository import JobRepository
        engine = get_engine(self.settings.get("DATABASE_URL"))
        session_factory = get_session_factory(engine)
        repo = JobRepository(session_factory)
        max_date = repo.get_max_posted_date()
        if max_date:
            self._max_date = max_date.date() if hasattr(max_date, 'date') else max_date
        else:
            self._max_date = datetime.now().date()
        self.logger.info(f"Smart crawl: T = {self._max_date} (DATE_FOLLOW >= T-{self.DATE_FOLLOW_DAYS}d, DATE_STOP < T-{self.DATE_STOP_DAYS}d, MAX_DUP={self.MAX_CONSECUTIVE_DUPS})")
    
    def normalize_search_params(self) -> tuple:
        """Normalize keyword and location for URL"""
        keyword = self.keyword.replace(" ", "-").lower().strip()
        location = self.location.replace(" ", "-").lower().strip()
        
        if location in ["ho-chi-minh", "hồ-chí-minh", "hcm"]:
            location = "ho-chi-minh-hcm"
        elif location in ["ha-noi", "hà-nội", "hanoi"]:
            location = "ha-noi"
        
        return keyword, location

    def parse_relative_date(self, raw_text):
        if not raw_text:
            return datetime.now().strftime('%Y-%m-%d')
        
        text = raw_text.lower().strip()
        # Xóa từ "posted" và khoảng trắng thừa, ví dụ: "posted \n 1 day ago" -> "1 day ago"
        text = re.sub(r'\s+', ' ', text).replace('posted', '').strip()
        
        today = datetime.now()
        delta = timedelta(days=0)

        try:
            if 'today' in text or 'just now' in text or 'hour' in text or 'minute' in text:
                delta = timedelta(days=0)
            elif 'yesterday' in text:
                delta = timedelta(days=1)
            elif 'day' in text:
                # Tìm số trong chuỗi "2 days ago", "1 day ago"
                # Xử lý trường hợp "30+ days ago" -> lấy 30
                number = re.search(r'(\d+)', text)
                if number:
                    days = int(number.group(1))
                    delta = timedelta(days=days)
            elif 'month' in text:
                # Ước lượng 1 tháng = 30 ngày
                number = re.search(r'(\d+)', text)
                if number:
                    months = int(number.group(1))
                    delta = timedelta(days=months * 30)
                    
            post_date = today - delta
            return post_date.strftime('%Y-%m-%d')
        except Exception as e:
            self.logger.error(f"Error parsing date '{raw_text}': {e}")
            return today.strftime('%Y-%m-%d')
    
    def start_requests(self):
        """Start from page 1 and auto-paginate until stop condition is met."""
        self._init_db()
        keyword, location = self.normalize_search_params()

        self.logger.info(f"Starting ITViec spider with keyword='{keyword}', location='{location}'")

        if location:
            url = f"{self.base_url}/it-jobs/{keyword}/{location}?page=1"
        else:
            url = f"{self.base_url}/it-jobs/{keyword}?page=1"

        self.logger.info(f"Requesting search page 1: {url}")
        yield self.make_request(url=url, callback=self.parse, meta={'page': 1, 'keyword': keyword, 'location': location})
    
    def parse(self, response):
        """
        Parse search results page:
        - Lọc date: chỉ follow job có posted_date >= T - DATE_FOLLOW_DAYS
        - Dừng pagination: posted_date < T - DATE_STOP_DAYS (quá cũ)
        - Dừng pagination: should_stop = True (do DeduplicationPipeline set khi đủ consecutive dups)
        - Auto-paginate không giới hạn trang
        Việc check duplicate thực hiện bởi DeduplicationPipeline (LSH + Jaccard)
        """
        if self.should_stop:
            return

        page     = response.meta.get('page', 1)
        keyword  = response.meta.get('keyword')
        location = response.meta.get('location')
        self.logger.info(f"Parsing search page {page}: {response.url}")

        cutoff_follow = self._max_date - timedelta(days=self.DATE_FOLLOW_DAYS)
        cutoff_stop   = self._max_date - timedelta(days=self.DATE_STOP_DAYS)

        job_items = response.css('div[data-controller="search--job-selection"]')
        if not job_items:
            self.logger.warning(f"No job items found on page {page}, stopping pagination.")
            return

        self.logger.info(f"Found {len(job_items)} job items on page {page}")

        stop_pagination = False

        for job_item in job_items:
            # --- Title & URL ---
            title_elem = job_item.css('h3[data-search--job-selection-target="jobTitle"]')
            job_url    = title_elem.attrib.get('data-url') if title_elem else None
            if not job_url:
                continue

            absolute_url = urljoin(self.base_url, job_url)

            # --- Date filter (best-effort từ list card) ---
            # ITViec hiển thị "Posted X days ago", "Posted today", v.v. trong text node
            date_raw = job_item.xpath(
                './/text()[contains(., "days ago") or contains(., "day ago") '
                'or contains(., "hours ago") or contains(., "hour ago") '
                'or contains(., "yesterday") or contains(., "today") '
                'or contains(., "just now") or contains(., "minutes ago")]'
            ).get()
            posted_date = None
            if date_raw:
                posted_date_str = self.parse_relative_date(date_raw.strip())
                posted_date = datetime.strptime(posted_date_str, '%Y-%m-%d').date()

                # Quá cũ → dừng toàn bộ pagination
                if posted_date < cutoff_stop:
                    self.logger.info(
                        f"Job too old ({posted_date} < T-{self.DATE_STOP_DAYS}d={cutoff_stop}), stopping pagination."
                    )
                    stop_pagination = True
                    break

                # Không đủ recent → skip card này, tiếp tục
                if posted_date < cutoff_follow:
                    self.logger.debug(f"Skipping (date {posted_date} < cutoff {cutoff_follow}): {absolute_url}")
                    continue

            # --- Vượt qua date filter → request detail page ---
            # DeduplicationPipeline sẽ check LSH + Jaccard và cập nhật
            # spider.consecutive_dup_count / spider.should_stop
            basic_info = {
                'title':    title_elem.css('::text').get('').strip(),
                'company':  job_item.css('a.text-rich-grey::text').get(),
                'location': job_item.css('div.text-rich-grey[title]::attr(title)').get(),
            }
            if posted_date:
                basic_info['posted_date'] = posted_date.strftime('%Y-%m-%d')

            skill_tags = job_item.css('div[data-controller="responsive-tag-list"] a::text').getall()
            if skill_tags:
                basic_info['skills'] = [s.strip() for s in skill_tags if s.strip()]

            self.logger.debug(f"Following job URL: {absolute_url}")
            yield self.make_request(
                url=absolute_url,
                callback=self.parse_job_detail,
                meta={'basic_info': basic_info},
            )

        # --- Auto-paginate ---
        if not stop_pagination and not self.should_stop:
            next_page = page + 1
            if location:
                next_url = f"{self.base_url}/it-jobs/{keyword}/{location}?page={next_page}"
            else:
                next_url = f"{self.base_url}/it-jobs/{keyword}?page={next_page}"
            self.logger.info(f"Requesting search page {next_page}: {next_url}")
            yield self.make_request(
                url=next_url,
                callback=self.parse,
                meta={'page': next_page, 'keyword': keyword, 'location': location},
            )
    
    def parse_job_detail(self, response):
        """
        Parse job detail page
        Chỉ lấy các field có trong JobItem schema
        """
        self.logger.info(f"Parsing job detail: {response.url}")

        # Get basic_info from search page (fallback if needed)
        basic_info = response.meta.get('basic_info', {})
        
        # Create default job item and populate metadata
        item = self.create_job_item()
        item = self.populate_metadata(item, response.url)
        
        # Dictionary to store extra data
        extra_data = {}

        # === 1. JOB INFORMATION ===

        # Get title from HTML structure
        title_elem = response.css('div.preview-job-header h2::text').get()
        item['title'] = title_elem.strip() if title_elem else basic_info.get('title')
        
        # Date posted in the format: posted x days ago, use the parse function to calculate the timestamp
        date_posted_raw = response.xpath('//div[contains(@class, "preview-header-item")]//svg[use[contains(@href, "clock")]]/following-sibling::span/text()').get()
        if date_posted_raw:
            item['date_posted'] = self.parse_relative_date(date_posted_raw)
        elif basic_info.get('posted_date'):
            # Fallback to date extracted from list page
            item['date_posted'] = basic_info['posted_date']
        
        # Salary: in the div.salary in the header
        salary_elem = response.css('div.preview-job-header .salary::text').get()
        if not salary_elem:
             # Case not logged in, it shows the link "Sign in to view"
             salary_elem = response.css('div.preview-job-header .salary a::text').get()
        
        item['salary_raw'] = salary_elem.strip() if salary_elem else "Negotiable"

        # Location: basic_info['location'] from list page is most reliable (e.g. "Ho Chi Minh")
        # Detail page has full address in <span class="normal-text text-rich-grey">
        location_city = basic_info.get('location')

        location_address = (
            response.css('span.normal-text.text-rich-grey::text').get() or
            response.css('a[href*="google.com/maps"]::text').get() or
            location_city
        )

        location_text = location_address or location_city
        if location_text:
            location_text = location_text.strip()
            item['location_raw'] = location_text
            extra_data['location_city'] = location_city.strip() if location_city else location_text
            extra_data['location_address'] = location_text

        # Skills: find the text "Skills:" then get the a tags in the next div
        skill_elems = response.xpath('//div[contains(text(), "Skills:")]/following-sibling::div//a/text()').getall()
        if skill_elems:
            skills = [s.strip() for s in skill_elems if s and s.strip()]
            if skills:
                item['skills_tags'] = skills

        # === 2. JOB DESCRIPTION SECTIONS ===
       # A. DESCRIPTION
        # Logic: Tìm div.paragraph có chứa thẻ h2 là "Job description" hoặc "Mô tả"
        # descendant::text()[not(parent::h2)]: Lấy toàn bộ text bên trong trừ cái tiêu đề
        desc_texts = response.xpath('''
            //div[contains(@class, "paragraph")]
            [h2[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "job description") or contains(text(), "Mô tả")]]
            /descendant::text()[not(parent::h2)]
        ''').getall()
        
        # Fallback: Nếu không tìm thấy (do layout cũ), thử dùng selector cũ
        if not desc_texts:
            desc_texts = response.css('section.job-description div.paragraph *::text').getall()
            
        item['description'] = utils.join_text(desc_texts)

        # B. REQUIREMENTS
        # Logic: Tìm div.paragraph có chứa h2 là "Skills" hoặc "Yêu cầu"
        req_texts = response.xpath('''
            //div[contains(@class, "paragraph")]
            [h2[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "skills") or contains(text(), "Yêu cầu")]]
            /descendant::text()[not(parent::h2)]
        ''').getall()

        if not req_texts:
             req_texts = response.css('section.job-experiences div.paragraph *::text').getall()

        requirements = utils.join_text(req_texts)
        item['requirements'] = requirements

        # C. BENEFITS
        # Logic: Tìm div.paragraph có chứa h2 là "Love Working" hoặc "Quyền lợi"
        ben_texts = response.xpath('''
            //div[contains(@class, "paragraph")]
            [h2[contains(translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "love working") or contains(text(), "Quyền lợi")]]
            /descendant::text()[not(parent::h2)]
        ''').getall()

        if not ben_texts:
            ben_texts = response.css('section.job-why-love-working div.paragraph *::text').getall()

        item['benefits'] = utils.join_text(ben_texts)

        # Infer additional fields
        if item.get('title'):
            extra_data['job_category'] = self.normalizer.infer_job_category(item['title'], item['description'])
            extra_data['job_level'] = self.normalizer.infer_job_level(item['title'])

        desc_combined = f"{item['description']} {item['requirements']}"
        extra_data['work_mode'] = self.normalizer.infer_work_mode(desc_combined, item.get('title'))

        # === 3. COMPANY INFORMATION ===
        # HTML has section "company-infos" at the end, get it directly without requesting the company page
        
        company_section = response.css('section.company-infos')
        
        if company_section:
            # Company name
            company_name = company_section.css('h2 a::text').get()
            if company_name:
                item['company_name'] = company_name.strip()
            elif basic_info.get('company'):
                item['company_name'] = basic_info.get('company')

            # Company URL - lưu vào extra_data
            company_link = company_section.css('h2 a::attr(href)').get()
            if company_link:
                extra_data['company_url'] = urljoin(self.base_url, company_link)

            # Industry (Column 2, Row 2 in the grid company info)
            # Based on the structure: .row:nth-of-type(2) .col:nth-child(2)
            industry_text = company_section.css('.row:nth-of-type(2) .col:nth-child(2) ::text').getall()
            if industry_text:
                clean_industry = ' '.join([t.strip() for t in industry_text if t.strip()])
                extra_data['company_industry'] = clean_industry

            # Size - lưu vào extra_data
            size_text = company_section.css('.row:nth-of-type(2) .col:nth-child(3)::text').get()
            if size_text:
                size_data = self.field_extractor.parse_company_size(size_text.strip())
                extra_data['company_size'] = size_data.get('category')
        else:
             # Fallback if the company section is not found
             item['company_name'] = basic_info.get('company')
        
        # Lưu extra_data vào item
        item['extra_data'] = extra_data

        self.jobs_scraped += 1
        yield item

    def parse_company(self, response, item: JobItem = None):
        """
        Legacy/Fallback method.
        Since we now extract company info in parse_job_detail, 
        this might only be used if deep crawling is strictly required.
        """
        # If you still need this for some reason, these would be the selectors 
        # for the external Company Page (not the job detail page).
        # Without the HTML for the Company Page, generic selectors are kept.
        pass
