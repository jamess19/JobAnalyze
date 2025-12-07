"""
TopCV Job Crawler - Crawl job listings from topcv.vn
"""
import os
import re
import csv
import time
import random
import unicodedata
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from middleware.logging import LoggerSetup
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from .base_crawler import BaseCrawler
from utils.utils import slugify, extract_text

class TopCVCrawler(BaseCrawler):
    """Crawler cho topcv.vn"""

    BASE_URL = "https://www.topcv.vn"
    HEADERS = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/123.0.0.0 Safari/537.36"),
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.topcv.vn/",
        "Connection": "keep-alive",
    }

    def __init__(
        self,
        output_path: str = "data/raw",
        keyword: str = "software engineer",
        start_page: int = 1,
        end_page: int = 1,
        crawl_date: str = None
    ):
        """
        Khởi tạo TopCV Crawler
        
        :param output_path: Đường dẫn lưu dữ liệu
        :param keyword: Từ khóa tìm kiếm job
        :param start_page: Trang bắt đầu
        :param end_page: Trang kết thúc
        :param crawl_date: Ngày crawl (format YYYY-MM-DD). Mặc định: hôm nay
        """
        super().__init__(output_path, start_page, end_page)
        self.base_url = self.BASE_URL
        self.keyword = keyword
        self.crawl_date = crawl_date or datetime.now().strftime("%Y-%m-%d")
        self.session = self._build_session()
        self.seen_jobs = set()

        # Create output directory if not exists
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            self.logger.info(f"Created directory: {output_path}")
            
    def _build_session(self) -> requests.Session:
        """Tạo session với retry logic"""
        s = requests.Session()
        s.headers.update(self.HEADERS)

        retry = Retry(
            total=6,
            connect=3,
            read=3,
            status=6,
            backoff_factor=1.2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "HEAD"]),
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=50)
        s.mount("https://", adapter)
        s.mount("http://", adapter)

        try:
            s.get(self.BASE_URL, timeout=20)
            time.sleep(1.0)
        except requests.RequestException:
            pass
        return s


    @staticmethod
    def _smart_sleep(min_s: float = 1.2, max_s: float = 2.8):
        """Random sleep để tránh bị block"""
        time.sleep(random.uniform(min_s, max_s))


    def _get_soup(self, url: str) -> BeautifulSoup:
        """Fetch URL và trả về BeautifulSoup với retry logic cho 429"""
        for attempt in range(1, 6):
            r = self.session.get(url, timeout=30)
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait = int(retry_after)
                    except ValueError:
                        wait = 6 * attempt
                else:
                    wait = 6 * attempt
                wait = wait + random.uniform(0.5, 2.0)
                self.logger.info(f"Sleeping for {wait} seconds")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return BeautifulSoup(r.text, "lxml")
        r.raise_for_status()
        return BeautifulSoup("", "lxml")

    def build_list_urls(self) -> List[str]:
        """
        Xây dựng danh sách URL trang tìm kiếm
        
        :return: Danh sách URLs
        """
        slug = slugify(self.keyword)
        urls = []
        for page in range(self.start_page, self.end_page + 1):
            url = f"{self.BASE_URL}/tim-viec-lam-{slug}?type_keyword=1&page={page}&sba=1"
            urls.append(url)
        return urls

    def _parse_search_page(self, url: str) -> List[Dict]:
        """Parse trang search và trả về danh sách jobs cơ bản"""
        soup = self._get_soup(url)
        jobs = []
        
        for job in soup.select("div.job-item-search-result"):
            a_title = job.select_one("h3.title a[href]")
            if not a_title:
                continue
            
            title = extract_text(a_title)
            job_url = urljoin(self.BASE_URL, a_title.get("href"))

            comp_a = job.select_one("a.company[href]")
            company = extract_text(job.select_one("a.company .company-name"))
            company_url = urljoin(self.BASE_URL, comp_a.get("href")) if comp_a else None

            salary = extract_text(job.select_one("label.title-salary"))
            address = extract_text(job.select_one("label.address .city-text"))
            exp = extract_text(job.select_one("label.exp span"))

            jobs.append({
                "title": title,
                "job_url": job_url,
                "company": company,
                "company_url": company_url,
                "salary_list": salary,
                "address_list": address,
                "exp_list": exp,
            })
        return jobs

    def _pick_info_value(self, soup: BeautifulSoup, title: str) -> Optional[str]:
        """Lấy giá trị từ section info theo title"""
        for sec in soup.select(".job-detail__info--section"):
            t = extract_text(sec.select_one(".job-detail__info--section-content-title")) or ""
            if t.lower() == title.lower():
                v = sec.select_one(".job-detail__info--section-content-value")
                return extract_text(v) if v else extract_text(sec)
        return None

    def _extract_deadline(self, soup: BeautifulSoup) -> Optional[str]:
        """Trích xuất deadline từ job detail"""
        for el in soup.select(".job-detail__info--deadline, .job-detail__information-detail--actions-label"):
            t = extract_text(el)
            if t and "Hạn nộp" in t:
                m = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", t)
                return m.group(1) if m else t
        return None

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Trích xuất tags/skills từ job detail"""
        return [extract_text(a) for a in soup.select(".job-tags a.item") if extract_text(a)]

    def _extract_desc_blocks(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Trích xuất các block mô tả công việc"""
        data = {}
        for item in soup.select(".job-description .job-description__item"):
            h3 = extract_text(item.select_one("h3")) or ""
            content = item.select_one(".job-description__item--content")
            if content:
                data[h3] = extract_text(content)
        return data

    def _extract_working_addresses(self, soup: BeautifulSoup) -> List[str]:
        """Trích xuất địa điểm làm việc"""
        out = []
        for item in soup.select(".job-description__item h3"):
            if "Địa điểm làm việc" in (extract_text(item) or ""):
                wrap = item.find_parent(class_="job-description__item")
                if wrap:
                    for d in wrap.select(".job-description__item--content div, .job-description__item--content li"):
                        val = extract_text(d)
                        if val:
                            out.append(val)
        return out

    def _extract_working_times(self, soup: BeautifulSoup) -> List[str]:
        """Trích xuất thời gian làm việc"""
        out = []
        for item in soup.select(".job-description__item h3"):
            if "Thời gian làm việc" in (extract_text(item) or ""):
                wrap = item.find_parent(class_="job-description__item")
                if wrap:
                    for d in wrap.select(".job-description__item--content div, .job-description__item--content li"):
                        val = extract_text(d)
                        if val:
                            out.append(val)
        return out

    def _extract_company_link_from_job(self, soup: BeautifulSoup) -> Optional[str]:
        """Trích xuất link công ty từ trang job detail"""
        cand = soup.select_one("a.company[href]") or soup.select_one("a[href*='/cong-ty/']")
        return urljoin(self.BASE_URL, cand["href"]) if cand and cand.has_attr("href") else None

    def scrape_job_detail(self, job_url: str) -> Dict[str, Any]:
        """
        Scrape chi tiết job từ URL
        
        :param job_url: URL của job
        :return: Dict chứa thông tin chi tiết job
        """
        soup = self._get_soup(job_url)
        self._smart_sleep()

        title = extract_text(soup.select_one(".job-detail__info--title, h1"))
        salary = self._pick_info_value(soup, "Mức lương")
        location = self._pick_info_value(soup, "Địa điểm")
        experience = self._pick_info_value(soup, "Kinh nghiệm")
        deadline = self._extract_deadline(soup)
        tags = self._extract_tags(soup)
        desc_blocks = self._extract_desc_blocks(soup)
        addrs = self._extract_working_addresses(soup)
        times = self._extract_working_times(soup)
        company_url_detail = self._extract_company_link_from_job(soup)

        return {
            "detail_title": title,
            "detail_salary": salary,
            "detail_location": location,
            "detail_experience": experience,
            "deadline": deadline,
            "tags": "; ".join(tags) if tags else None,
            "desc_mota": desc_blocks.get("Mô tả công việc"),
            "desc_yeucau": desc_blocks.get("Yêu cầu ứng viên"),
            "desc_quyenloi": desc_blocks.get("Quyền lợi"),
            "working_addresses": "; ".join(addrs) if addrs else None,
            "working_times": "; ".join(times) if times else None,
            "company_url_from_job": company_url_detail,
        }

    def _scrape_company_details(self, company_url: Optional[str]) -> Dict[str, Any]:
        """
        Scrape thông tin công ty từ company page
        
        :param company_url: URL trang công ty
        :return: Dict chứa thông tin công ty
        """
        empty_result = {
            "company_name_full": None,
            "company_website": None,
            "company_size": None,
            "company_industry": None,
            "company_address": None,
            "company_description": None,
        }
        
        if not company_url:
            return empty_result

        try:
            soup = self._get_soup(company_url)
            self._smart_sleep()

            # Tên công ty
            company_name = None
            for css in ["h1.company-name", "h1.title", "div.company-header h1", "div.company-info h1",
                        "meta[property='og:title']", "meta[property='og:site_name']", "title"]:
                el = soup.select_one(css)
                if el:
                    company_name = el.get("content") if el.name == "meta" else extract_text(el)
                    if company_name:
                        company_name = re.sub(r"\s*\|\s*TopCV.*$", "", company_name, flags=re.I)
                        break

            website = size = industry = address = None
            
            # Tìm container chứa thông tin công ty
            containers = [
                "div.company-overview", "div.company-detail", "div.company-profile",
                "section#company", "section.company-info", "div.box-intro-company",
                "div.company-info-container"
            ]
            container = None
            for css in containers:
                c = soup.select_one(css)
                if c:
                    container = c
                    break
            if container is None:
                container = soup

            # Parse các thông tin từ rows
            rows = container.select("li, .row, .item, .info-item, .company-info-item, .dl, .d-flex")
            for row in rows:
                row_text = extract_text(row) or ""
                label = None
                value = None
                strong = row.find(["strong", "b"])
                if strong:
                    label = extract_text(strong)
                    value = row_text
                    if label:
                        value = re.sub(re.escape(label), "", value, flags=re.I).strip(" :-–—")
                else:
                    m = re.match(r"^([^:：]+)[:：]\s*(.+)$", row_text)
                    if m:
                        label, value = m.group(1).strip(), m.group(2).strip()

                if not label or not value:
                    continue

                ln = re.sub(r"\s+", " ", label.lower())
                if "website" in ln or "trang web" in ln:
                    website = value
                elif "quy mô" in ln or "size" in ln or "nhân sự" in ln:
                    size = value
                elif "lĩnh vực" in ln or "industry" in ln or "ngành" in ln:
                    industry = value
                elif "địa chỉ" in ln or "address" in ln:
                    address = value

            # Mô tả công ty
            description = None
            for css in [
                "div.company-description", "div#company-description", "div.box-intro-company",
                "div.company-introduction", "div.description", "section.company-description",
                "div#readmore-company", "div#readmore-content"
            ]:
                el = soup.select_one(css)
                if el:
                    description = extract_text(el)
                    if description:
                        break

            return {
                "company_name_full": company_name,
                "company_website": website,
                "company_size": size,
                "company_industry": industry,
                "company_address": address,
                "company_description": description,
            }
            
        except Exception as e:
            self.logger.error(f"Error scraping company details: {e}")
            return empty_result

    def crawl(self) -> pd.DataFrame:
        """
        Crawl toàn bộ dữ liệu job và trả về DataFrame
        
        :return: DataFrame chứa dữ liệu job
        """
        self.logger.info(f"Crawling jobs for '{self.keyword}' from page {self.start_page} to {self.end_page}")
        rows: List[Dict] = []
        search_urls = self.build_list_urls()

        for page, url in enumerate(search_urls, start=self.start_page):
            self.logger.info(f"Crawling search page {page}: {url}")
            jobs = self._parse_search_page(url)

            if not jobs:
                self.logger.info(f"Page {page} has no jobs — stopping early.")
                break

            for j in jobs:
                job_url = j["job_url"]
                job_id = urlparse(job_url).path
                if job_id in self.seen_jobs:
                    continue
                self.seen_jobs.add(job_id)

                # Scrape job detail
                try:
                    detail = self.scrape_job_detail(job_url)
                except Exception as e:
                    self.logger.error(f"Error scraping job detail {job_url}: {e}")
                    detail = {k: None for k in [
                        "detail_title", "detail_salary", "detail_location",
                        "detail_experience", "deadline", "tags", "desc_mota",
                        "desc_yeucau", "desc_quyenloi", "working_addresses",
                        "working_times", "company_url_from_job"
                    ]}

                # Scrape company detail
                company_url = detail.get("company_url_from_job") or j.get("company_url")
                try:
                    comp = self._scrape_company_details(company_url)
                except Exception as e:
                    self.logger.error(f"Error scraping company details {company_url}: {e}")
                    comp = {k: None for k in [
                        "company_name_full", "company_website", "company_size",
                        "company_industry", "company_address", "company_description"
                    ]}

                # Combine data
                row = {
                    "crawl_date": self.crawl_date,
                    "search_keyword": self.keyword,
                    "search_slug": slugify(self.keyword),
                    **j,
                    **detail,
                    **comp
                }
                rows.append(row)

            self._smart_sleep(0.5, 1.0)

        self.data = pd.DataFrame(rows)
        
        # Sắp xếp cột
        cols = [
            "crawl_date", "search_keyword", "search_slug",
            "title", "detail_title",
            "job_url",
            "company", "company_name_full",
            "company_url", "company_url_from_job",
            "salary_list", "detail_salary",
            "address_list", "detail_location",
            "exp_list", "detail_experience",
            "deadline", "tags",
            "working_addresses", "working_times",
            "desc_mota", "desc_yeucau", "desc_quyenloi",
            "company_website", "company_size", "company_industry",
            "company_address", "company_description",
        ]
        cols = [c for c in cols if c in self.data.columns]
        self.data = self.data.loc[:, cols] if cols else self.data
        
        self.logger.info(f"Finished! Crawled {len(self.data)} jobs")
        return self.data

    def save_raw_data(self, df: pd.DataFrame = None, filename: str = None, file_type: str = "csv") -> str:
        """
        Lưu dữ liệu TopCV DataFrame vào file
        
        :param df: DataFrame để lưu (mặc định: sử dụng self.data)
        :param filename: Tên file (mặc định: topcv_jobs_<timestamp>.<ext>)
        :param file_type: Loại file: "csv", "json", hoặc "excel" (mặc định: "csv")
        :return: Đường dẫn file hoặc None nếu lỗi
        """
        valid_types = ["csv", "json", "excel"]
        if file_type.lower() not in valid_types:
            self.logger.error(f"Invalid file type: {file_type}. Supported types: {', '.join(valid_types)}")
            return None

        # Use provided df or use self.data
        if df is None:
            if isinstance(self.data, pd.DataFrame) and not self.data.empty:
                df = self.data
            else:
                self.logger.error("No data to save")
                return None

        if df.empty:
            self.logger.error("DataFrame is empty, no data to save")
            return None

        # Determine file extension and generate filename
        file_ext = {"csv": "csv", "json": "json", "excel": "xlsx"}[file_type.lower()]

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"topcv_jobs_{timestamp}.{file_ext}"
        elif not filename.endswith(f".{file_ext}"):
            filename = f"{filename}.{file_ext}"

        filepath = os.path.join(self.output_path, filename)

        try:
            if file_type.lower() == "csv":
                df.to_csv(filepath, index=False, encoding='utf-8-sig')
            elif file_type.lower() == "json":
                df.to_json(filepath, orient='records', indent=2, force_ascii=False)
            elif file_type.lower() == "excel":
                df.to_excel(filepath, index=False, engine='openpyxl')

            self.logger.info(f"Successfully saved data to {filepath} ({len(df)} rows)")
            return filepath
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
            return None


# if __name__ == "__main__":
#     crawler = TopCVCrawler(
#         output_path="data/raw",
#         keyword="Data Engineer",
#         start_page=1,
#         end_page=2
#     )

#     # Crawl data
#     df = crawler.crawl()

#     # Save to files
#     if not df.empty:
#         crawler.save_raw_data(filename="topcv_jobs", file_type="csv")
#         crawler.save_raw_data(filename="topcv_jobs", file_type="json")
#         crawler.save_raw_data(filename="topcv_jobs", file_type="excel")