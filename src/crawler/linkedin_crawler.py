"""
LinkedIn Job Crawler - Crawl job listings from LinkedIn using JobSpy API
"""

import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Any
from jobspy import scrape_jobs
import pandas as pd

from .base_crawler import BaseCrawler


class LinkedInCrawler(BaseCrawler):
    """Crawler cho LinkedIn jobs"""

    def __init__(
        self,
        output_path: str = "data/raw",
        search_term: str = "software engineer",
        location: str = "Vietnam",
        results_wanted: int = 20,
        hours_old: int = 72,
        fetch_description: bool = True,
    ):
        """
        Khoi tao LinkedIn Crawler
        :param output_path: Duong dan luu du lieu
        :param search_term: Tu khoa tim kiem job
        :param location: Dia diem tim kiem
        :param results_wanted: So luong ket qua muon lay
        :param hours_old: Chi lay job co trong so gio nay
        :param fetch_description: Co lay chi tiet mo ta job hay khong (cham hon)
        """
        super().__init__(output_path)
        self.base_url = "https://www.linkedin.com"
        self.search_term = search_term
        self.location = location
        self.results_wanted = results_wanted
        self.hours_old = hours_old
        self.fetch_description = fetch_description

        # Create output directory if not exists
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            print(f"Created directory: {output_path}")

    def build_list_urls(self) -> List[str]:
        """
        Xay dung danh sach URL - khong can thiet cho jobspy nhung giu de consistent voi interface
        :return: Danh sach job URLs (se trong voi jobspy API)
        """
        # JobSpy API khong can xay dung URL list, tuy nhien giu method nay de consistent voi BaseCrawler
        return []

    def crawl(self) -> pd.DataFrame:
        """
        Crawl toan bo du lieu job tu LinkedIn
        :return: DataFrame chua du lieu job
        """
        print(
            f"Dang crawl LinkedIn jobs cho '{self.search_term}' tai '{self.location}'..."
        )

        try:
            jobs = scrape_jobs(
                site_name=["linkedin"],
                search_term=self.search_term,
                location=self.location,
                results_wanted=self.results_wanted,
                hours_old=self.hours_old,
                linkedin_fetch_description=self.fetch_description,
            )

            if jobs is None or len(jobs) == 0:
                print("Khong tim thay job nao")
                return None

            print(f"Tim thay {len(jobs)} jobs")

            self.data = jobs
            print(f"Hoan thanh! Da crawl {len(jobs)} job")
            return jobs

        except Exception as e:
            print(f"[ERROR] Loi khi crawl LinkedIn: {e}")
            return pd.DataFrame()

    def save_raw_data(self, filename: str = None, file_type: str = "csv") -> str:
        """
        Lưu dữ liệu LinkedIn thô vào file với định dạng được chỉ định
        Tối ưu hóa cho cấu trúc dữ liệu job từ LinkedIn JobSpy API

        :param filename: Tên file (mặc định: linkedin_jobs_<timestamp>.<ext>)
        :param file_type: Loại file: "csv", "json", hoặc "excel" (mặc định: "csv")
        :return: Đường dẫn file hoặc None nếu lỗi
        """
        # Validate file_type
        valid_types = ["csv", "json", "excel"]
        if file_type.lower() not in valid_types:
            return None

        if self.data.empty:
            return None

        # Determine file extension and generate filename
        file_ext = {"csv": "csv", "json": "json", "excel": "xlsx"}[file_type.lower()]

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"linkedin_jobs_{timestamp}.{file_ext}"
        elif not filename.endswith(f".{file_ext}"):
            filename = f"{filename}.{file_ext}"

        filepath = f"{self.output_path}/{filename}"

        try:
            if file_type.lower() == "csv":
                self.data.to_csv(
                    os.path.join(self.output_path, filename),
                    quoting=csv.QUOTE_NONNUMERIC,
                    escapechar="\\",
                    index=False,
                )
            elif file_type.lower() == "json":
                self.data.to_json(
                    os.path.join(self.output_path, filename), orient="records", indent=2
                )
            elif file_type.lower() == "excel":
                self.data.to_excel(
                    os.path.join(self.output_path, filename), index=False
                )
            print(f"✅ Lưu dữ liệu thành công: {filepath} ({len(self.data)} rows)")
            return filepath
        except Exception as e:
            print(f"❌ Lỗi khi lưu dữ liệu: {e}")
            return None


if __name__ == "__main__":
    crawler = LinkedInCrawler(
        output_path="data/raw",
        search_term="software engineer",
        location="Vietnam",
        results_wanted=20,
        hours_old=72,
        fetch_description=True,
    )

    # Crawl data
    jobs_data = crawler.crawl()

    if jobs_data:
        # Save to CSV
        csv_filepath = crawler.save_raw_data("linkedin_jobs.csv", file_type="csv")
        print(f"CSV data saved to: {csv_filepath}")
        # Save to JSON
        json_filepath = crawler.save_raw_data("linkedin_jobs.json", file_type="json")
        print(f"JSON data saved to: {json_filepath}")
        # Save to Excel
        excel_filepath = crawler.save_raw_data("linkedin_jobs.xlsx", file_type="excel")
        print(f"Excel data saved to: {excel_filepath}")