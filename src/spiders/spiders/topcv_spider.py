"""
TopCV Spider - Scrape job listings from topcv.vn
"""

import scrapy
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from spiders.spiders.base_spider import BaseJobSpider
from spiders.items import JobItem


class TopcvSpider(BaseJobSpider):
    """Spider for scraping jobs from topcv.vn"""

    name = "topcv_spider"
    allowed_domains = ["www.topcv.vn", "topcv.vn"]

    # Enable Playwright for this spider
    use_playwright = True

    custom_settings = {
        'DOWNLOAD_DELAY': 4,  # Increase delay to avoid 429
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'CONCURRENT_REQUESTS': 1,              
        'AUTOTHROTTLE_ENABLED': True,          
        'AUTOTHROTTLE_START_DELAY': 8,
        'AUTOTHROTTLE_MAX_DELAY': 30,
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [429, 500, 502, 503, 504],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.topcv.vn"
        self.seen_jobs = set()
    
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
        """Generate initial requests for search pages"""
        keyword_slug = self.slugify(self.keyword)

        self.logger.info(f"Starting TopCV spider with keyword='{self.keyword}' (slug: {keyword_slug})")

        for page in range(self.start_page, self.end_page + 1):
            url = f"{self.base_url}/tim-viec-lam-{keyword_slug}?sort=new&type_keyword=1&page={page}&sba=1"

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
        
        # Extract job items from search page
        job_items = response.css('div.job-item-search-result')
        
        if not job_items:
            self.logger.warning(f"No job items found on page {page}")
            return
        
        self.logger.info(f"Found {len(job_items)} job items on page {page}")
        
        for job_item in job_items:
            # Extract job URL
            title_link = job_item.css('h3.title a::attr(href)').get()
            
            if not title_link:
                continue
            
            job_url = urljoin(self.base_url, title_link)
            
            # Check for duplicates
            if job_url in self.seen_jobs:
                self.logger.debug(f"Skipping duplicate job: {job_url}")
                continue
            
            self.seen_jobs.add(job_url)
            
            # Extract basic info from search page
            basic_info = {
                'title': self.safe_extract_text(job_item, 'h3.title a::text'),
                'company': self.safe_extract_text(job_item, 'a.company .company-name::text'),
                'company_url': urljoin(self.base_url, job_item.css('a.company::attr(href)').get() or ''),
                'salary_list': self.safe_extract_text(job_item, 'label.title-salary::text'),
                'address_list': self.safe_extract_text(job_item, 'label.address .city-text::text'),
                'exp_list': self.safe_extract_text(job_item, 'label.exp span::text'),
                'date_posted_raw': job_item.xpath(
                    'normalize-space(.//label[contains(@class,"label-update")]/text()[normalize-space()])'
                ).get() or '',
            }
            
            self.logger.debug(f"Following job URL: {job_url}")

            yield self.make_request(
                url=job_url,
                callback=self.parse_job_detail,
                meta={'basic_info': basic_info},
            )
    
    def parse_relative_date(self, text: str) -> str:
        """Convert '1 ngày trước', '3 giờ trước' → ISO date string"""
        now = datetime.now()
        text = text.strip().lower()

        match = re.search(r'(\d+)\s*(giây|phút|giờ|ngày|tuần|tháng)', text)
        if not match:
            return ''

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
        if date_posted_raw:
            item['date_posted'] = self.parse_relative_date(date_posted_raw)
            self.logger.debug(f"date_posted from list page: '{date_posted_raw}' → '{item['date_posted']}'")

        # ==================== 4. SALARY & LOCATION ====================
        
        # --- Salary ---
        salary_text = self._pick_info_value(response, 'Mức lương') or \
                      self._find_text_by_label(response, ['Mức lương', 'Salary']) or \
                      basic_info.get('salary_list')  # THÊM: fallback từ list page
        if salary_text:
            item['salary_raw'] = salary_text

        # --- Location ---
        location_text = self._pick_info_value(response, 'Địa điểm') or \
                        self._find_text_by_label(response, ['Địa điểm', 'Location', 'Nơi làm việc']) or \
                        basic_info.get('address_list')  # THÊM: fallback từ list page
        
        if location_text:
            stop_phrases = [
                "Thời gian làm việc", "Hạn nộp", "Bạn có hài lòng", 
                "Xem số người", "Cách thức ứng tuyển", "Tuyển dụng bởi",
                "Kinh nghiệm:", "Mức lương:", "\n"
            ]
            
            clean_loc = location_text
            for phrase in stop_phrases:
                idx = clean_loc.lower().find(phrase.lower())
                if idx != -1:
                    clean_loc = clean_loc[:idx]

            item['location_raw'] = clean_loc.strip(" -:,.")
            
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