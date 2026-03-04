"""
ITViec Spider - Scrape job listings from itviec.com
"""

import re
import scrapy
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
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

    def __init__(self, *args, start_url: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url     = 'https://itviec.com'
        self.start_url    = start_url or 'https://itviec.com/it-jobs'
        self._max_date    = None          # T = max(posted_date) from DB, set in start_requests()

        # Dedup/stop counters – manipulated by DeduplicationPipeline
        self.consecutive_dup_count = 0       # updated by DeduplicationPipeline
        self.should_stop           = False             # set True to stop pagination

        # Sequential page processing: finish all detail pages before next search page
        self._pending_details     = 0
        self._next_page_request   = None
    
    def _init_db(self):
        """Load T = max(posted_date) từ DB, lọc theo source của spider này."""
        if self._max_date is not None:
            return
        from models.base import get_engine, get_session_factory
        from repositories.job_repository import JobRepository
        engine = get_engine(self.settings.get("DATABASE_URL"))
        session_factory = get_session_factory(engine)
        repo = JobRepository(session_factory)
        source = self.name.replace("_spider", "")  # 'itviec'
        max_date = repo.get_max_posted_date(source=source)
        if max_date:
            self._max_date = max_date.date() if hasattr(max_date, 'date') else max_date
            self.logger.info(f"Smart crawl [{source}]: T = {self._max_date} (DATE_FOLLOW >= T-{self.DATE_FOLLOW_DAYS}d, DATE_STOP < T-{self.DATE_STOP_DAYS}d, MAX_DUP={self.MAX_CONSECUTIVE_DUPS})")
        else:
            self._max_date = None  # Chưa có job từ source này → crawl toàn bộ
            self.logger.info(f"Smart crawl [{source}]: No existing data → full crawl mode (no date filter)")
    
    def normalize_search_params(self) -> tuple:
        """Normalize keyword and location for URL"""
        keyword = self.keyword.replace(" ", "-").lower().strip()
        location = self.location.replace(" ", "-").lower().strip()
        
        if location in ["ho-chi-minh", "hồ-chí-minh", "hcm"]:
            location = "ho-chi-minh-hcm"
        elif location in ["ha-noi", "hà-nội", "hanoi"]:
            location = "ha-noi"
        
        return keyword, location

    @staticmethod
    def _paginate_url(base_url: str, page: int) -> str:
        """Return base_url with page= set to the given page number."""
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params['page'] = [str(page)]
        new_query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=new_query))

    def parse_relative_date(self, raw_text):
        if not raw_text:
            return datetime.now().strftime('%Y-%m-%d')
        
        text = raw_text.lower().strip()
        # Chuẩn hóa: xóa prefix "posted" (EN) và "đăng" (VI)
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\b(posted|đăng|super hot|hot)\b', '', text).strip()
        
        today = datetime.now()
        delta = timedelta(days=0)

        try:
            # English: today / just now / hours / minutes
            # Vietnamese: hôm nay / vừa đăng / giờ trước / phút trước
            if any(k in text for k in ['today', 'just now', 'hôm nay', 'vừa đăng']):
                delta = timedelta(days=0)
            elif any(k in text for k in ['hour', 'giờ', 'minute', 'phút', 'second', 'giây']):
                delta = timedelta(days=0)
            elif any(k in text for k in ['yesterday', 'hôm qua']):
                delta = timedelta(days=1)
            elif any(k in text for k in ['day', 'ngày']):
                number = re.search(r'(\d+)', text)
                if number:
                    delta = timedelta(days=int(number.group(1)))
            elif any(k in text for k in ['week', 'tuần']):
                number = re.search(r'(\d+)', text)
                if number:
                    delta = timedelta(weeks=int(number.group(1)))
            elif any(k in text for k in ['month', 'tháng']):
                number = re.search(r'(\d+)', text)
                if number:
                    delta = timedelta(days=int(number.group(1)) * 30)
                    
            post_date = today - delta
            return post_date.strftime('%Y-%m-%d')
        except Exception as e:
            self.logger.error(f"Error parsing date '{raw_text}': {e}")
            return today.strftime('%Y-%m-%d')
    
    def start_requests(self):
        """Start from page 1 and auto-paginate until stop condition is met."""
        self._init_db()

        if self.start_url:
            base_search_url = self.start_url.split('?')[0] + ('?' + self.start_url.split('?')[1] if '?' in self.start_url else '')
            # Strip any existing page= so _paginate_url is the sole authority
            parsed = urlparse(self.start_url)
            params = {k: v[0] for k, v in parse_qs(parsed.query, keep_blank_values=True).items() if k != 'page'}
            base_search_url = urlunparse(parsed._replace(query=urlencode(params)))
            self.logger.info(f"Starting ITViec spider with URL: {base_search_url}")
        else:
            keyword, location = self.normalize_search_params()
            self.logger.info(f"Starting ITViec spider with keyword='{keyword}', location='{location}'")
            base_search_url = f"{self.base_url}/it-jobs/{keyword}/{location}" if location else f"{self.base_url}/it-jobs/{keyword}"

        first_url = self._paginate_url(base_search_url, 1)
        self.logger.info(f"Requesting search page 1: {first_url}")
        yield self.make_request(url=first_url, callback=self.parse, meta={'page': 1, 'base_search_url': base_search_url})
    
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

        page            = response.meta.get('page', 1)
        base_search_url = response.meta.get('base_search_url', '')
        self.logger.info(f"Parsing search page {page}: {response.url}")

        # Nếu _max_date là None (chưa có data source này) → crawl toàn bộ, không lọc date
        cutoff_follow = (self._max_date - timedelta(days=self.DATE_FOLLOW_DAYS)) if self._max_date else None
        cutoff_stop   = (self._max_date - timedelta(days=self.DATE_STOP_DAYS))   if self._max_date else None

        job_items = response.css('div[data-controller="search--job-selection"]')
        if not job_items:
            self.logger.warning(f"No job items found on page {page}, stopping pagination.")
            return

        self.logger.info(f"Found {len(job_items)} job items on page {page}")

        stop_pagination = False
        followed_count = 0
        skipped_date_count = 0
        skipped_no_url_count = 0
        detail_requests = []

        for job_item in job_items:
            # --- Title & URL ---
            title_elem = job_item.css('h3[data-search--job-selection-target="jobTitle"]')
            title_text = title_elem.css('::text').get('').strip() if title_elem else ''
            job_url    = title_elem.attrib.get('data-url') if title_elem else None
            if not job_url:
                skipped_no_url_count += 1
                self.logger.info(f"SKIP (no URL): '{title_text}' — CSS selector không tìm thấy data-url")
                continue

            absolute_url = urljoin(self.base_url, job_url)

            # --- Date filter (best-effort từ list card) ---
            # ITViec EN: "Posted X days ago" / "HOT Posted 2 days ago"
            # ITViec VI: "Đăng X ngày trước" / "HOT Đăng 2 giờ trước"
            date_raw = job_item.xpath(
                './/text()['
                'contains(., "days ago") or contains(., "day ago") or '
                'contains(., "hours ago") or contains(., "hour ago") or '
                'contains(., "yesterday") or contains(., "today") or '
                'contains(., "just now") or contains(., "minutes ago") or '
                'contains(., "ngày trước") or contains(., "giờ trước") or '
                'contains(., "phút trước") or contains(., "tuần trước") or '
                'contains(., "hôm nay") or contains(., "vừa đăng")'
                ']'
            ).get()
            posted_date = None
            if date_raw:
                posted_date_str = self.parse_relative_date(date_raw.strip())
                posted_date = datetime.strptime(posted_date_str, '%Y-%m-%d').date()

                # Quá cũ → dừng toàn bộ pagination (chỉ áp dụng khi có T)
                if cutoff_stop and posted_date < cutoff_stop:
                    self.logger.info(
                        f"Job too old ({posted_date} < T-{self.DATE_STOP_DAYS}d={cutoff_stop}), stopping pagination."
                    )
                    stop_pagination = True
                    break

                # Không đủ recent → skip card này, tiếp tục (chỉ áp dụng khi có T)
                if cutoff_follow and posted_date < cutoff_follow:
                    skipped_date_count += 1
                    self.logger.info(f"SKIP (date filter): '{title_text}' — posted {posted_date} < cutoff {cutoff_follow}")
                    continue

            # --- Vượt qua date filter → request detail page ---
            # DeduplicationPipeline sẽ check LSH + Jaccard và cập nhật
            # spider.consecutive_dup_count / spider.should_stop
            followed_count += 1
            basic_info = {
                'title':    title_text,
                'company':  job_item.css('a.text-rich-grey::text').get(),
                'location': job_item.css('div.text-rich-grey[title]::attr(title)').get(),
            }
            if posted_date:
                basic_info['posted_date'] = posted_date.strftime('%Y-%m-%d')

            skill_tags = job_item.css('div[data-controller="responsive-tag-list"] a::text').getall()
            if skill_tags:
                basic_info['skills'] = [s.strip() for s in skill_tags if s.strip()]

            self.logger.debug(f"Following job URL: {absolute_url}")
            detail_requests.append(self.make_request(
                url=absolute_url,
                callback=self.parse_job_detail,
                meta={'basic_info': basic_info},
            ))

        self.logger.info(
            f"Page {page} summary: {followed_count} followed, "
            f"{skipped_date_count} skipped (date), {skipped_no_url_count} skipped (no URL), "
            f"total={followed_count + skipped_date_count + skipped_no_url_count}/{len(job_items)}"
        )

        # --- Prepare next page request (will be triggered after all details finish) ---
        self._next_page_request = None
        if not stop_pagination and not self.should_stop:
            next_page = page + 1
            next_url = self._paginate_url(base_search_url, next_page)
            self.logger.info(f"Requesting search page {next_page}: {next_url} (after {len(detail_requests)} detail pages)")
            self._next_page_request = self.make_request(
                url=next_url,
                callback=self.parse,
                meta={'page': next_page, 'base_search_url': base_search_url},
            )

        # --- Yield detail requests sequentially ---
        if detail_requests:
            self._pending_details = len(detail_requests)
            for req in detail_requests:
                yield req
        elif self._next_page_request:
            # No detail requests on this page (all skipped) → go to next page immediately
            yield self._next_page_request
            self._next_page_request = None
    
    def parse_job_detail(self, response):
        """
        Parse job detail page
        Chỉ lấy các field có trong JobItem schema
        """
        self.logger.info(f"Parsing job detail ({self._pending_details} remaining): {response.url}")

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
        
        # Date posted — try multiple selectors from most to least specific
        # 1. Header item span (may have clock SVG sibling)
        # 2. Any span/p containing "Posted … ago" in the header area
        # 3. Broad text node fallback (scoped to first match = main job, before "More jobs" section)
        date_posted_raw = (
            response.xpath('//div[contains(@class,"preview-header-item")]//span[contains(.,"ago") or contains(.,"today") or contains(.,"yesterday") or contains(.,"trước") or contains(.,"hôm nay")]/text()').get()
            or response.xpath('//text()[contains(.,"Posted") and (contains(.,"ago") or contains(.,"today") or contains(.,"yesterday"))]').get()
            or response.xpath('//text()[contains(.,"Đăng") and (contains(.,"trước") or contains(.,"hôm nay") or contains(.,"vừa đăng"))]').get()
        )
        if date_posted_raw:
            item['date_posted'] = self.parse_relative_date(date_posted_raw.strip())
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

        # --- Sequential page processing: countdown and trigger next page ---
        self._pending_details -= 1
        if self._pending_details <= 0 and self._next_page_request:
            self.logger.info(
                f"All detail pages done → requesting next search page"
            )
            yield self._next_page_request
            self._next_page_request = None

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
