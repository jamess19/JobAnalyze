#!/usr/bin/env python3
"""
Script to crawl ITViec jobs and save to CSV
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "crawl-data"))

from itviec_crawler import ITViecCrawler


def main():
    # Create crawler
    crawler = ITViecCrawler(
        output_path="data/raw", keyword="python", location="ho chi minh"
    )

    # Crawl data
    print(f"Crawling jobs for '{crawler.keyword}' in '{crawler.location}'...")
    jobs_data = crawler.crawl()

    # Save to multiple formats
    if jobs_data:
        # Save as CSV
        csv_filepath = crawler.save_raw_data("itviec_jobs", file_type="csv")
        if csv_filepath:
            print(f"CSV file saved: {csv_filepath}")
        # Save as JSON
        json_filepath = crawler.save_raw_data("itviec_jobs", file_type="json")
        if json_filepath:
            print(f"JSON file saved: {json_filepath}")
        # Save as Excel
        excel_filepath = crawler.save_raw_data("itviec_jobs", file_type="excel")
        if excel_filepath:
            print(f"Excel file saved: {excel_filepath}")


if __name__ == "__main__":
    main()
