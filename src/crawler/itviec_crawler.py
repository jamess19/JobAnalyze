"""
ITViec Job Crawler - Crawl job listings from itviec.com
"""
import requests
from bs4 import BeautifulSoup
import time
import random
import os
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
from .base_crawler import BaseCrawler


class ITViecCrawler(BaseCrawler):
    """Crawler cho itviec.com"""

    def __init__(self, output_path: str = "data/raw", keyword: str = "software engineer", location: str = "ho-chi-minh"):
        """
        Khoi tao ITViec Crawler
        :param output_path: Duong dan luu du lieu
        :param keyword: Tu khoa tim kiem job
        :param location: Dia diem
        """
        super().__init__(output_path)
        self.base_url = "https://itviec.com"
        self.keyword = keyword
        self.location = location
        self.job_links = []

        # Create output directory if not exists
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            print(f"Created directory: {output_path}")

    def get_headers(self) -> Dict[str, str]:
        """Lay headers gia lap browser"""
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/124.0.0.0 Safari/537.36"
        }

    def normalize_search_params(self) -> tuple:
        """Chuan hoa tu khoa tim kiem va dia diem"""
        keyword = self.keyword.replace(" ", "-").lower().strip()
        location = self.location.replace(" ", "-").lower().strip()
        if location == "ho-chi-minh":
            location += "-hcm"
        return keyword, location

    def get_max_page(self, keyword: str, location: str) -> int:
        """
        Lay so trang toi da cho keyword va location
        :param keyword: Tu khoa (da chuan hoa)
        :param location: Dia diem (da chuan hoa)
        :return: So trang toi da
        """
        url = f"{self.base_url}/it-jobs/{keyword}/{location}"
        try:
            resp = requests.get(url, headers=self.get_headers(), timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            pages = soup.select("ul.pagination li a")
            if not pages:
                return 1
            return max(int(p.text.strip()) for p in pages if p.text.strip().isdigit())
        except Exception as e:
            print(f"[WARN] Loi lay so trang: {e}")
            return 1

    def build_list_urls(self) -> List[str]:
        """
        Xay dung danh sach URL job tu keyword va location
        :return: Danh sach job URLs
        """
        keyword, location = self.normalize_search_params()
        max_page = self.get_max_page(keyword, location)
        print(f"Tim thay {max_page} trang cho '{self.keyword}' tai '{self.location}'")

        job_links = []
        for page in range(1, max_page + 1):
            list_url = f"{self.base_url}/it-jobs/{keyword}/{location}?page={page}"
            try:
                response = requests.get(list_url, headers=self.get_headers(), timeout=10)
                if response.status_code != 200:
                    print(f"[WARN] Khong the fetch trang {page}")
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                job_items = soup.find_all("div", {"data-controller": "search--job-selection"})

                for job_item in job_items:
                    try:
                        title_elem = job_item.find("h3", {"data-search--job-selection-target": "jobTitle"})
                        if not title_elem or not title_elem.has_attr("data-url"):
                            continue
                        job_links.append(title_elem["data-url"])
                    except Exception as e:
                        print(f"[WARN] Loi khi scrape job link trang {page}: {e}")
                        continue

                print(f"[{page}/{max_page}] Tim thay {len(job_items)} job tren trang")
                time.sleep(random.uniform(3, 7))

            except Exception as e:
                print(f"[ERROR] Loi khi fetch trang {page}: {e}")
                continue

        self.job_links = job_links
        print(f"Tong cong tim thay {len(job_links)} job")
        return job_links

    def scrape_job_detail(self, job_url: str) -> Dict[str, Any]:
        """
        Scrape chi tiet job tu URL
        :param job_url: URL cua job
        :return: Dict chua thong tin job
        """
        job_post = {
            "title": None,
            "detail_title": None,
            "job_url": job_url,
            "company": None,
            "company_name_full": None,
            "company_url": None,
            "company_url_from_job": None,
            "salary_list": None,
            "detail_salary": None,
            "address_list": None,
            "detail_location": None,
            "exp_list": None,
            "detail_experience": None,
            "deadline": None,
            "working_addresses": None,
            "working_times": None,
            "desc_mota": None,
            "desc_yeucau": None,
            "desc_quyenloi": None,
            "skills": None,
            "company_website": None,
            "company_size": None,
            "company_industry": None,
            "company_address": None,
            "company_description": None,
        }

        try:
            job_detail = requests.get(job_url, headers=self.get_headers(), timeout=10)
            if job_detail.status_code != 200:
                print(f"[WARN] Khong the fetch job details: {job_url}")
                return job_post

            job_soup = BeautifulSoup(job_detail.text, "html.parser")

            # Thong tin job co ban
            title_elem = job_soup.select_one("div.job-header-info h1")
            if title_elem:
                job_post["title"] = title_elem.get_text(strip=True)
                job_post["detail_title"] = job_post["title"]

            job_post["detail_salary"] = "Login to view"

            # Dia diem lam viec
            location_elem = job_soup.select_one("div.imb-3 span.normal-text")
            if location_elem:
                location_text = location_elem.get_text(strip=True)
                job_post["detail_location"] = location_text
                job_post["address_list"] = [location_text]
                job_post["working_addresses"] = location_text

            job_post["working_times"] = ""

            # Ky nang yeu cau
            tags = [a.get_text(strip=True) for a in job_soup.select("div:has(> .fw-600:-soup-contains('Skills')) a")]
            job_post["skills"] = ", ".join(tags) if tags else None

            # Mo ta job
            desc_sections = job_soup.find_all("div", class_="job-description__item--content")
            if len(desc_sections) > 0:
                job_post["desc_mota"] = desc_sections[0].text.strip()
            if len(desc_sections) > 1:
                job_post["desc_yeucau"] = desc_sections[1].text.strip()
            if len(desc_sections) > 2:
                job_post["desc_quyenloi"] = desc_sections[2].text.strip()

            # Thong tin cong ty tu job page
            company_name_elem = job_soup.find("h2", class_="employer-long-overview__name")
            if company_name_elem:
                job_post["company_name_full"] = company_name_elem.text.strip()

            company_link_elem = job_soup.find("a", class_="employer-long-overview__info")
            if company_link_elem and company_link_elem.has_attr("href"):
                job_post["company_url"] = f"{self.base_url}{company_link_elem['href']}"
                self._scrape_company_details(job_post)

            time.sleep(random.uniform(2, 5))

        except Exception as e:
            print(f"[ERROR] Loi scrape job detail ({job_url}): {e}")

        return job_post

    def _scrape_company_details(self, job_post: Dict[str, Any]) -> None:
        """
        Scrape thong tin cong ty tu company page
        :param job_post: Dict chua thong tin job de update
        """
        if not job_post.get("company_url"):
            return

        try:
            comp_resp = requests.get(job_post["company_url"], headers=self.get_headers(), timeout=10)
            if comp_resp.status_code != 200:
                return

            comp_soup = BeautifulSoup(comp_resp.text, "html.parser")

            # Website cong ty
            website_elem = comp_soup.find("a", {"rel": "nofollow noopener noreferrer"})
            if website_elem and website_elem.has_attr("href"):
                job_post["company_website"] = website_elem["href"]

            # Quy mo cong ty
            size_elem = comp_soup.find("svg", class_="fi-rr-users-alt")
            if size_elem:
                parent = size_elem.parent.parent
                if parent:
                    job_post["company_size"] = parent.text.strip()

            # Nganh cong nghiep
            industry_elem = comp_soup.find("svg", class_="fi-rr-briefcase")
            if industry_elem:
                parent = industry_elem.parent.parent
                if parent:
                    job_post["company_industry"] = parent.text.strip()

            # Dia chi cong ty
            address_elem = comp_soup.find("svg", class_="fi-rr-marker")
            if address_elem:
                parent = address_elem.parent.parent
                if parent:
                    job_post["company_address"] = parent.text.strip()

            # Mo ta cong ty
            desc_elem = comp_soup.find("div", class_="employer-overview__description")
            if desc_elem:
                job_post["company_description"] = desc_elem.text.strip()

        except Exception as e:
            print(f"[WARN] Loi scrape company details: {e}")

    def crawl(self) -> pd.DataFrame:
        """
        Crawl toan bo du lieu job va tra ve DataFrame
        :return: DataFrame chua du lieu job
        """
        print(f"Dang crawl job cho '{self.keyword}' tai '{self.location}'...")

        # Build list URLs
        job_links = self.build_list_urls()
        if not job_links:
            print("Khong tim thay job nao")
            self.data = pd.DataFrame()
            return self.data

        # Scrape chi tiet tung job
        print(f"Dang scrape chi tiet {len(job_links)} job...")
        jobs_data = []
        for i, job_url in enumerate(job_links, 1):
            print(f"[{i}/{len(job_links)}] Scraping: {job_url}")
            detail = self.scrape_job_detail(job_url)
            jobs_data.append(detail)

        self.data = pd.DataFrame(jobs_data)
        print(f"Hoan thanh! Da crawl {len(self.data)} job")
        return self.data

    def save_raw_data(self, df: pd.DataFrame = None, filename: str = None, file_type: str = "csv") -> str:
        """
        Lưu dữ liệu ITViec DataFrame vào file với định dạng được chỉ định
        Tối ưu hóa cho cấu trúc dữ liệu job từ ITViec

        :param df: DataFrame để lưu (mặc định: sử dụng self.data)
        :param filename: Tên file (mặc định: itviec_jobs_<timestamp>.<ext>)
        :param file_type: Loại file: "csv", "json", hoặc "excel" (mặc định: "csv")
        :return: Đường dẫn file hoặc None nếu lỗi
        """
        # Validate file_type
        valid_types = ["csv", "json", "excel"]
        if file_type.lower() not in valid_types:
            print(f"❌ Loại file không hợp lệ: {file_type}. Hỗ trợ: {', '.join(valid_types)}")
            return None

        # Use provided df or use self.data
        if df is None:
            if isinstance(self.data, pd.DataFrame) and not self.data.empty:
                df = self.data
            else:
                print(f"⚠️  Không có dữ liệu để lưu")
                return None
        elif not isinstance(df, pd.DataFrame):
            print(f"❌ Tham số df phải là pandas DataFrame")
            return None

        if df.empty:
            print(f"⚠️  DataFrame trống, không có dữ liệu để lưu")
            return None

        # Determine file extension and generate filename
        file_ext = {"csv": "csv", "json": "json", "excel": "xlsx"}[file_type.lower()]

        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"itviec_jobs_{timestamp}.{file_ext}"
        elif not filename.endswith(f".{file_ext}"):
            filename = f"{filename}.{file_ext}"

        filepath = f"{self.output_path}/{filename}"

        try:
            if file_type.lower() == "csv":
                df.to_csv(filepath, index=False, encoding='utf-8')
            elif file_type.lower() == "json":
                df.to_json(filepath, orient='records', indent=2, force_ascii=False)
            elif file_type.lower() == "excel":
                df.to_excel(filepath, index=False, engine='openpyxl')

            print(f"✅ Lưu dữ liệu thành công: {filepath} ({len(df)} rows)")
            return filepath
        except Exception as e:
            print(f"❌ Lỗi khi lưu dữ liệu: {e}")
            return None



if __name__ == "__main__":
    crawler = ITViecCrawler(
        output_path="data/raw",
        keyword="software engineer",
        location="ho chi minh"
    )

    # Crawl data - returns DataFrame
    df = crawler.crawl()

    # Save to CSV
    if not df.empty:
        filepath = crawler.save_raw_data(df, "itviec_jobs", file_type="csv")
        print(f"Du lieu da luu tai: {filepath}")
        filepath = crawler.save_raw_data(df, "itviec_jobs", file_type="json")
        print(f"Du lieu da luu tai: {filepath}")
        filepath = crawler.save_raw_data(df, "itviec_jobs", file_type="excel")
        print(f"Du lieu da luu tai: {filepath}")