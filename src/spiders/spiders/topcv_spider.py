"""
TopCV Spider - Scrape job listings from topcv.vn
"""

import scrapy
import re
import uuid
from datetime import datetime, timedelta, date
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from spiders.spiders.base_spider import BaseJobSpider
from spiders.items import JobItem


class TopcvSpider(BaseJobSpider):
    """Spider for scraping jobs from topcv.vn"""

    name = "topcv_spider"
    allowed_domains = ["www.topcv.vn", "topcv.vn"]

    # Enable Playwright for this spider
    use_playwright = True

    # Anti-429 features
    rotate_user_agent = True      # RotatingUserAgentMiddleware
    rate_limit_backoff = True     # RateLimitBackoffMiddleware
    referer_base = "https://www.topcv.vn/"

    # Smart crawl settings
    MAX_CONSECUTIVE_DUPS = 15   # stop if this many consecutive duplicate jobs
    DATE_FOLLOW_DAYS    = 2    # follow detail page only if posted_date >= T - N days
    DATE_STOP_DAYS      = 3    # stop pagination if posted_date < T - N days

    custom_settings = {
        'DOWNLOAD_DELAY': 6,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'CONCURRENT_REQUESTS': 1,              
        'AUTOTHROTTLE_ENABLED': True,          
        'AUTOTHROTTLE_START_DELAY': 10,
        'AUTOTHROTTLE_MAX_DELAY': 60,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 0.5,  # more conservative
        'RETRY_TIMES': 2,          # let RateLimitBackoffMiddleware handle 429
        'RETRY_HTTP_CODES': [500, 502, 503, 504],  # exclude 429 from default retry
    }

    def __init__(self, start_url: str = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.topcv.vn"
        self.seen_jobs = set()
        self.start_url = start_url  # Direct URL to crawl (overrides keyword slug)

        # Unique Playwright browser context per run → fresh cookies/session each time
        self._playwright_ctx = f"topcv_{uuid.uuid4().hex[:10]}"
        self.logger.info(f"Playwright context: {self._playwright_ctx}")

        # Smart crawl state
        self._max_date: date | None = None   # T = max(posted_date) from DB
        self.consecutive_dup_count = 0       # updated by DeduplicationPipeline
        self.should_stop = False             # set True to stop pagination
        self.vip_skipped_count = 0           # VIP/promoted jobs skipped due to old date

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
    
    @staticmethod
    def _paginate_url(base_url: str, page: int) -> str:
        """Return base_url with page= set to the given page number."""
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params['page'] = [str(page)]
        new_query = urlencode({k: v[0] for k, v in params.items()})
        return urlunparse(parsed._replace(query=new_query))

    def slugify(self, text: str) -> str:
        """Convert text to slug for URL"""
        import unicodedata
        text = unicodedata.normalize("NFD", text)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-zA-Z0-9\s-]", " ", text)
        text = re.sub(r"\s+", "-", text.strip())
        text = re.sub(r"-+", "-", text)
        return text.lower()
    
    def start_requests(self):
        """Start from page 1 and auto-paginate until stop condition is met."""
        self._init_db()

        if self.start_url:
            # Strip any existing page= so _paginate_url is the sole authority
            parsed = urlparse(self.start_url)
            params = {k: v[0] for k, v in parse_qs(parsed.query, keep_blank_values=True).items() if k != 'page'}
            base_search_url = urlunparse(parsed._replace(query=urlencode(params)))
            self.logger.info(f"Starting TopCV spider with URL: {base_search_url}")
        else:
            keyword_slug = self.slugify(self.keyword)
            self.logger.info(f"Starting TopCV spider with keyword='{self.keyword}' (slug: {keyword_slug})")
            base_search_url = f"{self.base_url}/tim-viec-lam-{keyword_slug}?sort=new&type_keyword=1&sba=1"

        first_url = self._paginate_url(base_search_url, 1)
        self.logger.info(f"Requesting search page 1: {first_url}")
        yield self.make_request(
            url=first_url,
            callback=self.parse,
            meta={'page': 1, 'base_search_url': base_search_url, 'playwright_context': self._playwright_ctx},
            page_timeout=60000,
        )
    
    def parse(self, response):
        """
        Parse search results page.
        - VIP job (class có bg-yellow, bg-highlight, hoặc bất kỳ bg-*): dùng cutoff_follow (T-based).
          Nếu quá cũ (< T-2d) thì skip, không dừng pagination, không đếm consecutive dup.
        - Job thường: date filter T-based (cutoff_follow / cutoff_stop) + đếm consecutive dup.
        - Dừng pagination: posted_date < cutoff_stop (job thường) hoặc should_stop = True.
        - Auto-paginate không giới hạn trang.
        """
        if self.should_stop:
            return

        page            = response.meta.get('page', 1)
        base_search_url = response.meta.get('base_search_url', '')
        self.logger.info(f"Parsing search page {page}: {response.url}")

        cutoff_follow = self._max_date - timedelta(days=self.DATE_FOLLOW_DAYS)
        cutoff_stop   = self._max_date - timedelta(days=self.DATE_STOP_DAYS)

        # Extract job items from search page
        job_items = response.css('div.job-item-search-result')

        if not job_items:
            self.logger.warning(f"No job items found on page {page}, stopping pagination.")
            return

        self.logger.info(f"Found {len(job_items)} job items on page {page}")

        stop_pagination = False

        for job_item in job_items:
            # Extract job URL
            title_link = job_item.css('h3.title a::attr(href)').get()
            if not title_link:
                continue

            job_url = urljoin(self.base_url, title_link)

            # URL-level dedup (within same crawl run)
            if job_url in self.seen_jobs:
                self.logger.debug(f"Skipping duplicate job: {job_url}")
                continue
            self.seen_jobs.add(job_url)

            # --- Detect VIP/promoted: class có thêm bg-* ngoài các class chuẩn ---
            # Normal: "job-item-search-result job-ta"
            # VIP:    "job-item-search-result bg-yellow job-ta"
            #         "job-item-search-result bg-highlight job-ta", etc.
            item_class = job_item.attrib.get('class', '')
            is_vip = bool(re.search(r'\bbg-\w+', item_class))

            # --- Parse date từ list card ---
            date_posted_raw = job_item.xpath(
                'normalize-space(.//label[contains(@class,"label-update")]/text()[normalize-space()])'
            ).get() or ''

            posted_date = None
            if date_posted_raw:
                parsed_str = self.parse_relative_date(date_posted_raw)
                if parsed_str:
                    posted_date = datetime.strptime(parsed_str, '%Y-%m-%d').date()

            if is_vip:
                # ---------- VIP JOB: T-based cutoff_follow, không dừng pagination ----------
                if posted_date and posted_date < cutoff_follow:
                    self.vip_skipped_count += 1
                    self.logger.debug(
                        f"VIP job too old ({posted_date} < T-{self.DATE_FOLLOW_DAYS}d={cutoff_follow}), "
                        f"skipping (total skipped: {self.vip_skipped_count}): {job_url}"
                    )
                    continue   # skip card, never stops pagination
                # VIP + đủ mới (hoặc không parse được date) → fall through

            else:
                # ---------- NORMAL JOB: T-based date filter ----------
                if posted_date:
                    if posted_date < cutoff_stop:
                        self.logger.info(
                            f"Job too old ({posted_date} < T-{self.DATE_STOP_DAYS}d={cutoff_stop}), stopping pagination."
                        )
                        stop_pagination = True
                        break

                    if posted_date < cutoff_follow:
                        self.logger.debug(f"Skipping (date {posted_date} < cutoff {cutoff_follow}): {job_url}")
                        continue

            # Extract basic info from search page
            basic_info = {
                'title': self.safe_extract_text(job_item, 'h3.title a::text'),
                'company': self.safe_extract_text(job_item, 'a.company .company-name::text'),
                'company_url': urljoin(self.base_url, job_item.css('a.company::attr(href)').get() or ''),
                'salary_list': self.safe_extract_text(job_item, 'label.title-salary::text'),
                'address_list': self.safe_extract_text(job_item, 'label.address .city-text::text'),
                'exp_list': self.safe_extract_text(job_item, 'label.exp span::text'),
                'date_posted_raw': date_posted_raw,
                'is_vip': is_vip,
            }

            self.logger.debug(f"Following job URL: {job_url}")

            # Brand pages need extra wait for JS-rendered content
            is_brand = '/brand/' in job_url
            yield self.make_request(
                url=job_url,
                callback=self.parse_job_detail,
                meta={'basic_info': basic_info, 'playwright_context': self._playwright_ctx},
                wait_for_selector='.premium-job-description__box--content, .box-info .content-tab' if is_brand else None,
                page_timeout=60000,
            )

        # --- Auto-paginate ---
        if not stop_pagination and not self.should_stop:
            next_page = page + 1
            next_url = self._paginate_url(base_search_url, next_page)
            self.logger.info(f"Requesting search page {next_page}: {next_url}")
            yield self.make_request(
                url=next_url,
                callback=self.parse,
                meta={'page': next_page, 'base_search_url': base_search_url, 'playwright_context': self._playwright_ctx},
                page_timeout=60000,
            )
    
    def parse_relative_date(self, text: str) -> str:
        """Convert '1 ngày trước', '3 giờ trước' → ISO date string"""
        now = datetime.now()
        text = text.strip().lower()

        # Handle "Hôm nay", "Vừa đăng"
        if any(k in text for k in ['hôm nay', 'vừa đăng', 'just now', 'today']):
            return now.strftime('%Y-%m-%d')

        match = re.search(r'(\d+)\s*(giây|phút|giờ|ngày|tuần|tháng)', text)
        if not match:
            return ''   # caller sẽ fallback về crawl_date

        value, unit = int(match.group(1)), match.group(2)
        delta_map = {
            'giây': timedelta(seconds=value),
            'phút': timedelta(minutes=value),
            'giờ':  timedelta(hours=value),
            'ngày': timedelta(days=value),
            'tuần': timedelta(weeks=value),
            'tháng': timedelta(days=value * 30),
        }
        result = now - delta_map.get(unit, timedelta(0))
        return result.strftime('%Y-%m-%d')

    def parse_job_detail(self, response):
        self.logger.info(f"Parsing job detail: {response.url}")
        
        basic_info = response.meta.get('basic_info', {})
        item = self.create_job_item()
        item = self.populate_metadata(item, response.url)
        item['is_vip'] = basic_info.get('is_vip', False)
        
        extra_data = {}

        # ==================== 1. TITLE ====================
        title = None
        title_selectors = ['h1.job-detail__info--title', 'h1.title-job', '.box-info-job h1', '#header-job-info h1']
        for sel in title_selectors:
            t = response.css(sel).xpath('string()').get()
            if t and t.strip():
                title = t.strip()
                break
        
        if not title:
            page_title = response.css('title::text').get()
            if page_title:
                title = page_title.split('-')[0].strip()

        item['title'] = title if title else basic_info.get('title')

        # ==================== 2. COMPANY ====================
        # SỬA: Gán company_name từ basic_info trước, sau đó override nếu trang detail có
        item['company_name'] = basic_info.get('company', '')

        company_box = response.css('.job-detail__company')
        if company_box:
            detail_company = company_box.css('.company-name-label .name::text').get(default='').strip()
            if detail_company:
                item['company_name'] = detail_company
        
        if not item.get('company_name'):
            item['company_name'] = response.xpath('//meta[@property="og:site_name"]/@content').get()

        # ==================== 3. DATE POSTED ====================
        # THÊM: Parse date từ basic_info (trang list) 
        date_posted_raw = basic_info.get('date_posted_raw', '')
        parsed_date = ''

        if date_posted_raw:
            parsed_date = self.parse_relative_date(date_posted_raw)
            self.logger.debug(f"date_posted: raw='{date_posted_raw}' → '{parsed_date}'")

        # Fallback về crawl_date nếu không parse được
        item['date_posted'] = parsed_date if parsed_date else self.crawl_date
        
        if not parsed_date:
            self.logger.debug(
                f"date_posted fallback to crawl_date='{self.crawl_date}' "
                f"(raw='{date_posted_raw or 'empty'}')"
            )

        # ==================== 4. SALARY & LOCATION ====================
        
        # --- Salary ---
        salary_text = self._pick_info_value(response, 'Mức lương') or \
                      self._find_text_by_label(response, ['Mức lương', 'Salary']) or \
                      self._extract_brand_salary(response) or \
                      basic_info.get('salary_list')  # THÊM: fallback từ list page
        if salary_text:
            item['salary_raw'] = salary_text

        # --- Location ---
        # Ưu tiên: standard layout → brand layout → list page (đã sạch) → _find_text_by_label (cuối cùng)
        is_brand = '/brand/' in response.url
        if is_brand:
            location_text = self._extract_brand_location(response) or \
                            basic_info.get('address_list')
        else:
            location_text = self._pick_info_value(response, 'Địa điểm') or \
                            basic_info.get('address_list') or \
                            self._find_text_by_label(response, ['Địa điểm', 'Location', 'Nơi làm việc'])

        if location_text:
            # Truncate sớm trước khi clean để tránh JD bị lẫn vào
            location_text = location_text[:300]

            stop_phrases = [
                "Thời gian làm việc", "Hạn nộp", "Bạn có hài lòng",
                "Xem số người", "Cách thức ứng tuyển", "Tuyển dụng bởi",
                "Kinh nghiệm:", "Mức lương:", "Mô tả công việc", "Yêu cầu", "\n"
            ]

            clean_loc = location_text
            for phrase in stop_phrases:
                idx = clean_loc.lower().find(phrase.lower())
                if idx != -1:
                    clean_loc = clean_loc[:idx]

            clean_loc = clean_loc.strip(" -:,.")
            # Giới hạn cuối cùng: location không bao giờ > 200 ký tự
            if len(clean_loc) > 200:
                self.logger.warning(f"location_raw quá dài ({len(clean_loc)} chars), truncate: {response.url}")
                clean_loc = clean_loc[:200]

            item['location_raw'] = clean_loc

            location_data = self.field_extractor.parse_location(item['location_raw'])
            extra_data['location_city'] = location_data.get('city')

            if len(item['location_raw']) > 10:
                extra_data['location_address'] = item['location_raw']

        # Deadline
        deadline_text = response.css('.job-detail__info--deadline-date::text').get() or \
                        self._find_text_by_label(response, ['Hạn nộp', 'Deadline'])
        
        if deadline_text:
            match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', deadline_text)
            if match:
                extra_data['deadline'] = match.group(1)
            else:
                extra_data['deadline'] = deadline_text.strip()

        # ==================== 5. CONTENT ====================
        desc_blocks = self._smart_extract_content(response)
        
        if not desc_blocks.get('description'):
             desc_blocks.update(self._extract_desc_blocks(response))

        # Brand layout fallback (/brand/ URLs: FPT, VPBank, Sapo, ...)
        if not desc_blocks.get('description'):
            desc_blocks.update(self._extract_brand_content(response))

        item['description'] = desc_blocks.get('description')
        item['requirements'] = desc_blocks.get('requirements')
        item['benefits'] = desc_blocks.get('benefits')

        # Skills
        tags = response.css('.job-tags .item.search-from-tag::text').getall()
        if tags:
             item['skills_tags'] = [t.strip() for t in tags if t.strip()]
        
        general_info = self._extract_general_info(response)
        extra_data.update(general_info)
        
        # SỬA: Tránh "None None" khi concat
        full_text = f"{item.get('description') or ''} {item.get('requirements') or ''}"
        if item.get('title'):
            extra_data['job_category'] = self.normalizer.infer_job_category(item['title'], full_text)
            extra_data['job_level'] = self.normalizer.infer_job_level(item['title'])
        extra_data['work_mode'] = self.normalizer.infer_work_mode(full_text, item.get('title'))
        
        item['extra_data'] = extra_data

        self.jobs_scraped += 1
        yield item

    def closed(self, reason):
        """Override to include premium-job stats in the final summary."""
        super().closed(reason)
        self.logger.info(f"  VIP/promoted jobs skipped (too old): {self.vip_skipped_count}")

    # ================= CÁC HÀM PHỤ (HELPER METHODS) - BẮT BUỘC PHẢI CÓ =================

    def _pick_info_value(self, response, title_keyword):
        """Lấy giá trị từ các box thông tin ở header (Layout Standard)"""
        sections = response.css('.job-detail__info--section')
        for section in sections:
            section_title = section.css('.job-detail__info--section-content-title::text').get()
            if section_title and title_keyword.lower() in section_title.strip().lower():
                value = section.css('.job-detail__info--section-content-value').xpath('string()').get()
                return value.strip() if value else None
        return None

    def _find_text_by_label(self, response, labels):
        """Tìm text dựa trên nhãn (Layout Brand/Custom)"""
        for label in labels:
            # Tìm thẻ chứa label, sau đó lấy text của thẻ bên cạnh hoặc cha
            xpath = f'//*[contains(text(), "{label}")]/following-sibling::*//text() | //*[contains(text(), "{label}")]/../following-sibling::*//text()'
            texts = response.xpath(xpath).getall()
            if texts:
                return ' '.join([t.strip() for t in texts if t.strip()])
            
            # Hoặc tìm text nằm ngay trong thẻ đó (VD: <div>Lương: 10tr</div>)
            xpath_inline = f'//*[contains(text(), "{label}")]/text()'
            inline_text = response.xpath(xpath_inline).get()
            if inline_text and ':' in inline_text:
                return inline_text.split(':', 1)[1].strip()
        return None

    def _smart_extract_content(self, response):
        """Tách các khối nội dung dựa trên tiêu đề h3/h4"""
        blocks = {}
        headers = response.css('.job-description__item h3, .content-tab h3, .job-data h3, .job-data h4, .job-data strong')
        
        for header in headers:
            header_text = header.xpath('string()').get().strip().lower()
            key = None
            if any(k in header_text for k in ['mô tả', 'description']): key = 'description'
            elif any(k in header_text for k in ['yêu cầu', 'requirement']): key = 'requirements'
            elif any(k in header_text for k in ['quyền lợi', 'benefit', 'đãi ngộ']): key = 'benefits'
            
            if key:
                # Lấy nội dung: Thử lấy sibling div hoặc parent div text
                parent = header.xpath('..') # Lên 1 cấp
                # Cách 1: Standard layout (nằm trong .job-description__item--content)
                content = parent.css('.job-description__item--content').xpath('string()').get()
                # Cách 2: Brand layout (thường nằm ngay trong thẻ p hoặc div sau header)
                if not content:
                    content = ''.join(parent.xpath('text() | *//text()').getall())
                
                # Loại bỏ chính cái header ra khỏi content
                if content:
                    clean_content = content.replace(header.xpath('string()').get(), '').strip()
                    blocks[key] = clean_content
        return blocks

    def _extract_desc_blocks(self, response):
        """Fallback cho layout cũ"""
        data = {}
        items = response.css('.job-description .job-description__item')
        for item in items:
            h3 = item.css('h3').xpath('string()').get()
            content = item.css('.job-description__item--content').xpath('string()').get()
            if h3 and content:
                key = 'description' if 'mô tả' in h3.lower() else 'requirements' if 'yêu cầu' in h3.lower() else 'benefits' if 'quyền lợi' in h3.lower() else None
                if key: data[key] = content.strip()
        return data

    def _extract_general_info(self, response):
        """Lấy thông tin từ sidebar phải"""
        info = {}
        groups = response.css('.box-general-group')
        for group in groups:
            title = group.css('.box-general-group-info-title::text').get()
            value = group.css('.box-general-group-info-value::text').get()
            if title and value:
                info[title.strip()] = value.strip()
        return info

    def _extract_brand_content(self, response):
        """
        Extract content blocks from brand layout pages (/brand/ URLs: FPT, VPBank, Sapo, ...).
        Scrapy CSS does not support :has()/:contains(), so XPath is used throughout.

        Premium brand layout (.premium-job-description__box):
            Container : div.premium-job-description__box
            Title     : h2.premium-job-description__box--title
            Content   : div.premium-job-description__box--content

        Fallback – generic h3 → next sibling div (older brand pages).
        """
        blocks = {}

        # ── Premium brand layout ──────────────────────────────────────────────
        _premium_base = (
            '//div[contains(@class,"premium-job-description__box")]'
            '[.//h2[contains(@class,"premium-job-description__box--title")'
            '       and contains(normalize-space(),"{kw}")]]'
            '//*[contains(@class,"premium-job-description__box--content")]'
        )

        for key, keyword in [
            ('description', 'Mô tả công việc'),
            ('requirements', 'Yêu cầu ứng viên'),
            ('benefits',     'Quyền lợi'),
        ]:
            text = response.xpath(_premium_base.format(kw=keyword)).xpath('string()').get()
            if text and text.strip():
                blocks[key] = text.strip()

        # ── Fallback: h3 → next sibling div (older/other brand pages) ─────────
        _h3_next_div = (
            '//h3[contains(normalize-space(),"{kw}")]/following-sibling::div[1]'
        )

        for key, keyword in [
            ('description', 'Mô tả công việc'),
            ('requirements', 'Yêu cầu ứng viên'),
            ('benefits',     'Quyền lợi'),
        ]:
            if not blocks.get(key):
                text = response.xpath(_h3_next_div.format(kw=keyword)).xpath('string()').get()
                if text and text.strip():
                    blocks[key] = text.strip()

        # ── box-info layout (VPBank, ...): div.box-info > h2.title + div.content-tab
        _box_info = (
            '//div[contains(@class,"box-info")]'
            '[./h2[contains(@class,"title") and contains(normalize-space(),"{kw}")]]'
            '/div[contains(@class,"content-tab")]'
        )

        for key, keyword in [
            ('description', 'Mô tả công việc'),
            ('requirements', 'Yêu cầu ứng viên'),
            ('benefits',     'Quyền lợi'),
        ]:
            if not blocks.get(key):
                text = response.xpath(_box_info.format(kw=keyword)).xpath('string()').get()
                if text and text.strip():
                    blocks[key] = text.strip()

        return blocks

    def _extract_brand_location(self, response):
        """
        Extract location from brand layout pages (/brand/ URLs: FPT, VPBank, Sapo, ...).

        Variant A (.basic-information-item): Sapo, FPT, ...
        Variant B (.box-item + fa-map-marker icon): VPBank, ...
        Variant C (premium layout): tên thành phố trong header thông tin.
        """
        # Variant A – basic-information-item
        location = response.xpath(
            '//div[contains(@class,"basic-information-item")]'
            '[.//*[contains(@class,"basic-information-item__data--label")'
            '      and (contains(normalize-space(),"Địa điểm")'
            '           or contains(normalize-space(),"Location"))]]'
            '//*[contains(@class,"basic-information-item__data--value")]'
        ).xpath('string()').get()
        if location and location.strip():
            return location.strip()[:200]

        # Variant B – box-item với icon bản đồ (VPBank, ...)
        location = response.xpath(
            '//div[contains(@class,"box-item")]'
            '[.//i[contains(@class,"fa-map-marker") or contains(@class,"fa-location")'
            '      or contains(@class,"fa-map-pin")]]'
            '/div[not(.//i)]'
        ).xpath('string()').get()
        if location and location.strip():
            return location.strip()[:200]

        # Variant C – premium brand header info
        location = response.xpath(
            '//div[contains(@class,"premium-job-info") or contains(@class,"job-info-header")]'
            '[.//*[contains(normalize-space(),"Địa điểm")'
            '      or contains(normalize-space(),"Location")]]'
            '//*[contains(@class,"value") or contains(@class,"content")]'
        ).xpath('string()').get()
        if location and location.strip():
            return location.strip()[:200]

        return None

    def _extract_brand_salary(self, response):
        """
        Extract salary from brand layout.
        Variant A (.basic-information-item): Sapo, FPT, ...
        Variant B (.box-item + fa-money-bill-wave icon): VPBank, ...
        """
        # Variant A
        salary = response.xpath(
            '//div[contains(@class,"basic-information-item")]'
            '[.//*[contains(@class,"basic-information-item__data--label")'
            '      and contains(normalize-space(),"Mức lương")]]'
            '//*[contains(@class,"basic-information-item__data--value")]'
        ).xpath('string()').get()
        if salary and salary.strip():
            return salary.strip()

        # Variant B – box-item with money icon
        salary = response.xpath(
            '//div[contains(@class,"box-item")]'
            '[.//i[contains(@class,"fa-money-bill-wave") or contains(@class,"fa-money")]]'
            '/div[not(.//i)]'
        ).xpath('string()').get()
        if salary and salary.strip():
            return salary.strip()

        return None