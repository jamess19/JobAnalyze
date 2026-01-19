#!/usr/bin/env python3
"""
Main Pipeline - Scrapy Spiders Runner with Google Drive Upload
Uses Scrapy spiders to scrape job data, combine results, and upload to Google Drive
"""
import os
import sys

# Add src to path BEFORE any local imports
sys.path.insert(0, os.path.dirname(__file__))

# Set the working directory to src for scrapy.cfg discovery
os.chdir(os.path.dirname(__file__))

# Set Scrapy settings module
os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'settings')

import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
import warnings
import traceback
warnings.filterwarnings("ignore")

# Scrapy imports
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

import config.config as conf  # type: ignore

# Spider imports
from spiders.spiders.itviec_spider import ItviecSpider  # type: ignore
from spiders.spiders.topcv_spider import TopcvSpider  # type: ignore
from spiders.spiders.linkedin_spider import LinkedinSpider  # type: ignore
from storage.drive_uploader import GoogleDriveUploader  # type: ignore


def run_spiders(spider_configs: List[Dict], output_folder: str) -> List[Dict]:
    """
    Run multiple Scrapy spiders and collect all items in memory
    
    :param spider_configs: List of spider configurations
    :param output_folder: Output directory for scraped data
    :return: List of all collected items from all spiders
    """
    print("🕷️  Starting Scrapy spiders...\n")
    
    # Shared list to collect all items from all spiders
    collected_items = []
    
    # Get Scrapy settings
    settings = get_project_settings()
    
    # Override settings - DISABLE ExportPipeline
    settings.set('LOG_LEVEL', 'INFO')
    settings.set('OUTPUT_DIR', output_folder)
    
    # Disable ExportPipeline - we'll export manually after combining
    settings.set('ITEM_PIPELINES', {
        "spiders.pipelines.ValidationPipeline": 100,
        "spiders.pipelines.CleaningPipeline": 200,
        "spiders.pipelines.DeduplicationPipeline": 300,
        # ExportPipeline is DISABLED - no automatic export
    })
    
    # Create output directory
    os.makedirs(output_folder, exist_ok=True)
    
    # Custom item collector
    def item_scraped_handler(item, response, spider):
        """Handler to collect items as they're scraped"""
        collected_items.append(dict(item))
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Spider mapping
    spider_classes = {
        'itviec': ItviecSpider,
        'topcv': TopcvSpider,
        'linkedin': LinkedinSpider,
    }
    
    spider_count = 0
    
    # Schedule all spiders
    for config in spider_configs:
        spider_name = config.get('spider')
        keywords = config.get('keywords', [])
        location = config.get('location', 'Ho Chi Minh')
        start_page = config.get('start_page', 1)
        end_page = config.get('end_page', 3)
        
        if spider_name not in spider_classes:
            print(f"⚠️  Unknown spider: {spider_name}")
            continue
        
        spider_class = spider_classes[spider_name]
        
        # Schedule spider for each keyword
        for keyword in keywords:
            print(f"🔍 Scheduling {spider_name.upper()} spider")
            print(f"   Keyword: '{keyword}'")
            print(f"   Location: {location}")
            print(f"   Pages: {start_page} to {end_page}")
            
            crawler = process.create_crawler(spider_class)
            # Connect signal to collect items
            from scrapy import signals
            crawler.signals.connect(item_scraped_handler, signal=signals.item_scraped)
            
            process.crawl(
                crawler,
                keyword=keyword,
                location=location,
                start_page=start_page,
                end_page=end_page
            )
            spider_count += 1
    
    if spider_count == 0:
        print("❌ No spiders scheduled")
        return []
    
    # Start crawling process
    print(f"\n⏳ Running {spider_count} spider(s)...\n")
    print("=" * 70)
    
    start_time = datetime.now()
    
    try:
        process.start()  # Blocks until all spiders finish
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print(f"✅ All spiders completed!")
        print(f"⏱️  Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"📊 Total items collected: {len(collected_items)}")
        print("=" * 70 + "\n")
        
        return collected_items
        
    except Exception as e:
        print(f"\n❌ Error during spider execution: {e}")
        traceback.print_exc()
        return []


def combine_and_export_data(collected_items: List[Dict], output_folder: str) -> Optional[str]:
    """
    Combine all collected items and export to CSV, Excel, JSON
    
    :param collected_items: List of all items collected from spiders
    :param output_folder: Directory to save output files
    :return: Path to combined CSV file, or None if failed
    """
    print("📊 Processing and combining data...")
    
    try:
        if not collected_items:
            print("⚠️  No items collected from spiders")
            return None
        
        # Convert items to DataFrame to deduplication
        print(f"   Processing {len(collected_items)} items...")
        combined_df = pd.DataFrame(collected_items)
        
        # Remove duplicates based on job_url
        original_count = len(combined_df)
        combined_df = combined_df.drop_duplicates(subset=['job_url'], keep='first')
        dedup_count = original_count - len(combined_df)
        
        print(f"\n📊 Total items collected: {original_count}")
        if dedup_count > 0:
            print(f"⚠️ Removed {dedup_count} duplicate(s)")
        print(f" ✅ Final unique jobs: {len(combined_df)}")
        
        # Create combined filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        basename = f"combined_jobs_{timestamp}"
        
        # Save combined files (CSV, Excel, JSON)
        saved_files = save_data_files(combined_df, output_folder, basename)
        
        if 'csv' not in saved_files:
            print("\n❌ Error: Cannot save combined CSV file")
            return None
        
        print("\n✅ Data export completed")
        return saved_files['csv']
        
    except Exception as e:
        print(f"\n❌ Error processing data: {e}")
        traceback.print_exc()
        return None

def save_data_files(dataframe: pd.DataFrame, output_folder: str, basename: str) -> Dict[str, str]:
    """
    Lưu DataFrame ra nhiều định dạng file (CSV, Excel, JSON)
    
    :param dataframe: DataFrame cần lưu
    :param output_folder: Thư mục output
    :param basename: Tên file cơ bản (không có extension)
    :return: Dictionary chứa đường dẫn các file đã lưu với key là format (csv, excel, json)
    """
    saved_files = {}
    
    print(f"\n💾 Saving combined data...")
    
    try:
        # Lưu CSV
        csv_path = os.path.join(output_folder, f"{basename}.csv")
        dataframe.to_csv(csv_path, index=False, encoding='utf-8')
        saved_files['csv'] = csv_path
        print(f"   ✅ CSV: {csv_path}")
        
        # Lưu Excel
        excel_path = os.path.join(output_folder, f"{basename}.xlsx")
        dataframe.to_excel(excel_path, index=False)
        saved_files['excel'] = excel_path
        print(f"   ✅ Excel: {excel_path}")
        
        # Lưu JSON
        json_path = os.path.join(output_folder, f"{basename}.json")
        dataframe.to_json(json_path, orient='records', indent=2, force_ascii=False)
        saved_files['json'] = json_path
        print(f"   ✅ JSON: {json_path}")
        
    except Exception as e:
        print(f"   ❌ Lỗi khi lưu file: {e}")
        traceback.print_exc()
    
    return saved_files


def build_spider_configs(config: Dict) -> List[Dict]:
    """
    Build spider configurations from DEFAULT_CONFIG
    
    :param config: Configuration dictionary
    :return: List of spider configurations
    """
    spider_configs = []
    
    # ITViec configuration
    if config.get('itviec_keywords'):
        spider_configs.append({
            'spider': 'itviec',
            'keywords': config.get('itviec_keywords', []),
            'location': config.get('itviec_location', 'ho-chi-minh'),
            'start_page': 1,
            'end_page': 1,
        })
    
    # TopCV configuration
    if config.get('topcv_keywords'):
        spider_configs.append({
            'spider': 'topcv',
            'keywords': config.get('topcv_keywords', []),
            'location': 'Ho Chi Minh',
            'start_page': config.get('topcv_start_page', 1),
            'end_page': config.get('topcv_end_page', 1),
        })

    # LinkedIn configuration
    if config.get('linkedin_keywords'):
        spider_configs.append({
            'spider': 'linkedin',
            'keywords': config.get('linkedin_keywords', []),
            'location': config.get('linkedin_location', 'Vietnam'),
            'start_page': 1,
            'end_page': 2,
        })
    
    return spider_configs


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
        print(f"\n📤 Uploading to Google Drive...")
        print(f"   File: {os.path.basename(file_path)}")
        
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
    Main function - chạy Scrapy spiders pipeline và upload lên Google Drive
    
    Pipeline workflow:
    1. Cào dữ liệu từ ITViec và TopCV bằng Scrapy spiders (trong memory)
    2. Gộp tất cả dữ liệu lại
    3. Xuất thành CSV, Excel, JSON (1 lần duy nhất)
    4. Upload file CSV lên Google Drive
    
    :return: Exit code (0 = thành công, 1 = thất bại)
    """
    try:
        # Load config
        config = conf.DEFAULT_CONFIG
        output_folder = config.get("output_folder", "src/data")
        
        print("\n" + "=" * 70)
        print("🚀 DATA COLLECTION PIPELINE - SCRAPY SPIDERS")
        print("=" * 70)
        print(f"📁 Output folder: {output_folder}\n")
        
        # Build spider configurations from config
        spider_configs = build_spider_configs(config)
        
        if not spider_configs:
            print("❌ No spider configurations found in config")
            return 1
        
        print(f"📋 Found {len(spider_configs)} spider configuration(s)")
        for cfg in spider_configs:
            print(f"   - {cfg['spider'].upper()}: {len(cfg['keywords'])} keyword(s)")
        print()
        
        # Step 1: Run spiders to scrape data (collect in memory)
        print("=" * 70)
        print("STEP 1: SCRAPING DATA")
        print("=" * 70 + "\n")
        
        collected_items = run_spiders(spider_configs, output_folder)
        
        if not collected_items:
            print("\n❌ No items collected from spiders")
            return 1
        
        # Step 2: Combine and export data
        print("=" * 70)
        print("STEP 2: COMBINING & EXPORTING DATA")
        print("=" * 70 + "\n")
        
        combined_csv = combine_and_export_data(collected_items, output_folder)
        
        if combined_csv is None:
            print("\n❌ Failed to export data")
            return 1
        
        # Step 3: Upload to Google Drive
        print("=" * 70)
        print("STEP 3: UPLOADING TO GOOGLE DRIVE")
        print("=" * 70)
        
        upload_success = upload_to_drive(combined_csv)
        
        if not upload_success:
            print("\n⚠️  Upload failed but data saved locally")
            print(f"   📁 File location: {combined_csv}")
            return 1
        
        # Success
        print("\n" + "=" * 70)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"\n📁 Output files saved in: {output_folder}")
        print(f"📄 Combined file: {os.path.basename(combined_csv)}")
        print(f"☁️  Uploaded to Google Drive\n")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user (Ctrl+C)")
        return 130
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
