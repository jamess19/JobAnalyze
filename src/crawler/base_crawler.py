"""
Base Crawler - Lớp cơ sở cho tất cả crawlers
"""
from abc import ABC, abstractmethod
import pandas as pd
from middleware.logging import LoggerSetup

class BaseCrawler(ABC):
    """Lớp cơ sở cho crawler, định nghĩa interface chung"""

    def __init__(self, output_path: str = "data/raw", start_page: int = 1, end_page: int = 1):
        """
        Khởi tạo Crawler
        """
        self.output_path = output_path
        self.start_page = start_page
        self.end_page = end_page
        self.data = pd.DataFrame()
        self.base_url = ""
        self.logger = LoggerSetup.setup_logger(__name__)

    @abstractmethod
    def crawl(self) -> pd.DataFrame:
        """
        Crawl dữ liệu từ nguồn
        Phải được implement bởi subclass
        :return: DataFrame chứa dữ liệu
        """
        pass

    def build_list_urls(self):
        """
        Xây dựng danh sách URL để crawl
        Phải được implement bởi subclass
        """
        pass
    
    def save_raw_data(self, filename: str = None, file_type: str = "csv") -> str:
        """
        Lưu dữ liệu thô vào file với định dạng được chỉ định
        :param filename: Tên file (mặc định: raw_data_<timestamp>.<ext>)
        :param file_type: Loại file: "csv", "json", hoặc "excel" (mặc định: "csv")
        :return: Đường dẫn file hoặc None nếu lỗi
        """
        pass
      