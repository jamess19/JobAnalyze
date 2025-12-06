#!/usr/bin/env python3
"""
Main Pipeline - Scrape job data từ ITViec và LinkedIn, và upload lên Google Drive
"""
import os
import sys
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
import warnings
import traceback

warnings.filterwarnings("ignore")

import config.config as conf  # type: ignore

# Thêm src vào path
sys.path.insert(0, os.path.dirname(__file__))

from crawler.itviec_crawler import ITViecCrawler  # type: ignore
from crawler.linkedin_crawler import LinkedInCrawler  # type: ignore
from crawler.topcv_crawler import TopCVCrawler  # type: ignore
from storage.drive_uploader import GoogleDriveUploader  # type: ignore


def scrape_itviec(config: Dict) -> List[pd.DataFrame]:
    """
    Scrape job data từ ITViec cho tất cả keywords
    
    :param config: Dictionary cấu hình chứa itviec_keywords và itviec_location
    :return: List các DataFrame chứa dữ liệu job từ ITViec
    """
    dataframes: List[pd.DataFrame] = []

    print("🔍 Scraping ITViec...")
    keywords = config.get("itviec_keywords", [])
    location = config.get("itviec_location", "ho-chi-minh")
    output_path = config.get("output_folder", "src/data")
    
    for keyword in keywords:
        print(f"   Keyword: '{keyword}'")
        try:
            crawler = ITViecCrawler(
                output_path=output_path,
                keyword=keyword,
                location=location
            )

            df = crawler.crawl()
            
            if df is not None and not df.empty:
                df['source'] = 'ITViec'
                dataframes.append(df)
                print(f"   ✅ Crawled {len(df)} jobs")
            else:
                print(f"   ⚠️  Không tìm thấy job cho keyword '{keyword}'")
                
        except Exception as e:
            print(f"   ❌ Lỗi khi scrape ITViec với keyword '{keyword}': {e}")
            continue
    
    return dataframes


def scrape_linkedin(config: Dict) -> List[pd.DataFrame]:
    """
    Scrape job data từ LinkedIn cho tất cả keywords
    
    :param config: Dictionary cấu hình chứa linkedin_keywords và các tham số khác
    :return: List các DataFrame chứa dữ liệu job từ LinkedIn
    """
    dataframes: List[pd.DataFrame] = []
    
    print("\n🔍 Scraping LinkedIn...")
    keywords = config.get("linkedin_keywords", [])
    location = config.get("linkedin_location", "Vietnam")
    results_wanted = config.get("linkedin_results_wanted", 50)
    hours_old = config.get("linkedin_hours_old", 72)
    output_path = config.get("output_folder", "src/data")
    
    for keyword in keywords:
        print(f"   Keyword: '{keyword}'")
        try:
            crawler = LinkedInCrawler(
                output_path=output_path,
                search_term=keyword,
                location=location,
                results_wanted=results_wanted,
                hours_old=hours_old,
                fetch_description=True
            )
            df = crawler.crawl()
            
            if df is not None and not df.empty:
                df['source'] = 'LinkedIn'
                dataframes.append(df)
                print(f"   ✅ Crawled {len(df)} jobs")
            else:
                print(f"   ⚠️  Không tìm thấy job cho keyword '{keyword}'")
                
        except Exception as e:
            print(f"   ❌ Lỗi khi scrape LinkedIn với keyword '{keyword}': {e}")
            continue
    
    return dataframes

def scrape_topcv(config: Dict) -> List[pd.DataFrame]:
    """
    Scrape job data từ TopCV cho tất cả keywords
    
    :param config: Dictionary cấu hình chứa topcv_keywords và các tham số khác
    :return: List các DataFrame chứa dữ liệu job từ TopCV
    """
    dataframes: List[pd.DataFrame] = []
    
    print("\n🔍 Scraping TopCV...")
    keywords = config.get("topcv_keywords", [])
    start_page = config.get("topcv_start_page", 1)
    end_page = config.get("topcv_end_page", 3)
    output_path = config.get("output_folder", "src/data")
    
    for keyword in keywords:
        print(f"   Keyword: '{keyword}'")
        try:
            crawler = TopCVCrawler(
                output_path=output_path,
                keyword=keyword,
                start_page=start_page,
                end_page=end_page
            )
            df = crawler.crawl()
            
            if df is not None and not df.empty:
                df['source'] = 'TopCV'
                dataframes.append(df)
                print(f"   ✅ Crawled {len(df)} jobs")
            else:
                print(f"   ⚠️  Không tìm thấy job cho keyword '{keyword}'")
                
        except Exception as e:
            print(f"   ❌ Lỗi khi scrape TopCV với keyword '{keyword}': {e}")
            continue
    
    return dataframes

def save_data_files(dataframe: pd.DataFrame, output_folder: str, basename: str) -> Dict[str, str]:
    """
    Lưu DataFrame ra nhiều định dạng file (CSV, Excel, JSON)
    
    :param dataframe: DataFrame cần lưu
    :param output_folder: Thư mục output
    :param basename: Tên file cơ bản (không có extension)
    :return: Dictionary chứa đường dẫn các file đã lưu với key là format (csv, excel, json)
    """
    saved_files = {}
    
    try:
        # Lưu CSV
        csv_path = os.path.join(output_folder, f"{basename}.csv")
        dataframe.to_csv(csv_path, index=False, encoding='utf-8')
        saved_files['csv'] = csv_path
        print(f"   ✅ Saved CSV: {csv_path}")
        
        # Lưu Excel
        excel_path = os.path.join(output_folder, f"{basename}.xlsx")
        dataframe.to_excel(excel_path, index=False)
        saved_files['excel'] = excel_path
        print(f"   ✅ Saved Excel: {excel_path}")
        
        # Lưu JSON
        json_path = os.path.join(output_folder, f"{basename}.json")
        dataframe.to_json(json_path, orient='records', indent=2, force_ascii=False)
        saved_files['json'] = json_path
        print(f"   ✅ Saved JSON: {json_path}")
        
    except Exception as e:
        print(f"   ❌ Lỗi khi lưu file: {e}")
        traceback.print_exc()
    
    return saved_files


def scrape(config: Dict) -> Optional[str]:
    """
    Scrape job data từ ITViec và LinkedIn, sau đó lưu vào file
    
    :param config: Dictionary cấu hình
    :return: Đường dẫn file CSV được lưu, hoặc None nếu thất bại
    """
    all_dataframes: List[pd.DataFrame] = []
    
    try:
        # Scrape từ ITViec
        itviec_data = scrape_itviec(config)
        all_dataframes.extend(itviec_data)
        
        # Scrape từ LinkedIn
        linkedin_data = scrape_linkedin(config)
        all_dataframes.extend(linkedin_data)

        # Scrape từ TopCV
        topcv_data = scrape_topcv(config)
        all_dataframes.extend(topcv_data)
        
        # Kiểm tra xem có dữ liệu không
        if not all_dataframes:
            print("\n⚠️  Không có dữ liệu từ bất kỳ nguồn nào")
            return None
        
        # Kết hợp tất cả dữ liệu
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        print(f"\n📊 Tổng jobs scraped: {len(combined_df)}")
        
        # Tạo tên file với timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        basename = f"jobs_{timestamp}"
        output_folder = config.get("output_folder", "src/data")
        
        # Đảm bảo thư mục output tồn tại
        os.makedirs(output_folder, exist_ok=True)
        
        # Lưu file
        saved_files = save_data_files(combined_df, output_folder, basename)
        
        if 'csv' not in saved_files:
            print("\n❌ Lỗi: Không thể lưu file CSV")
            return None
        
        print("\n✅ Scraping hoàn tất")
        return saved_files['csv']
        
    except Exception as e:
        print(f"\n❌ Lỗi scraping: {e}")
        traceback.print_exc()
        return None


def upload_to_drive(file_path: str) -> bool:
    """
    Upload file lên Google Drive
    
    :param file_path: Đường dẫn file cần upload
    :return: True nếu thành công, False nếu thất bại
    """
    if not file_path or not os.path.exists(file_path):
        print(f"❌ File không tồn tại: {file_path}")
        return False
    
    try:
        print(f"\n📤 Uploading file: {file_path} to Google Drive...")
        uploader = GoogleDriveUploader()
        uploader.upload(file_path)
        print("✅ Upload thành công")
        return True
        
    except Exception as e:
        print(f"❌ Lỗi upload: {e}")
        traceback.print_exc()
        return False


def main() -> int:
    """
    Main function - chạy pipeline scrape và upload
    
    :return: Exit code (0 = thành công, 1 = thất bại)
    """
    try:
        config = conf.DEFAULT_CONFIG
        
        # Scrape dữ liệu
        csv_file = scrape(config)
        
        if csv_file is None:
            print("\n❌ Scraping thất bại - Dừng pipeline")
            return 1
        
        # Upload lên Drive
        upload_success = upload_to_drive(csv_file)
        
        if not upload_success:
            print("\n⚠️  Upload thất bại nhưng dữ liệu đã được lưu cục bộ")
            print(f"   File location: {csv_file}")
            return 1
        
        # Thành công
        print("\n" + "=" * 70)
        print("✅ PIPELINE HOÀN TẤT THÀNH CÔNG")
        print("=" * 70)
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline bị dừng bởi người dùng")
        return 130  # Exit code cho SIGINT
        
    except Exception as e:
        print(f"\n❌ Lỗi không mong đợi trong main: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
