#!/usr/bin/env python3
"""
Script to crawl TopCV jobs and save to CSV/JSON/Excel
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from crawler.topcv_crawler import TopCVCrawler


def main():
    # Create crawler
    crawler = TopCVCrawler(
        output_path="data/raw",
        keyword="Data Engineer",
        start_page=1,
        end_page=2
    )

    # Crawl data
    print(f"Crawling jobs for '{crawler.keyword}'...")
    jobs_data = crawler.crawl()

    # Save to multiple formats
    if not jobs_data.empty:
        # Save as CSV
        csv_filepath = crawler.save_raw_data(filename="topcv_jobs", file_type="csv")
        if csv_filepath:
            print(f"CSV file saved: {csv_filepath}")

        # Save as JSON
        json_filepath = crawler.save_raw_data(filename="topcv_jobs", file_type="json")
        if json_filepath:
            print(f"JSON file saved: {json_filepath}")

        # Save as Excel
        excel_filepath = crawler.save_raw_data(filename="topcv_jobs", file_type="excel")
        if excel_filepath:
            print(f"Excel file saved: {excel_filepath}")
    else:
        print("No jobs found!")


if __name__ == "__main__":
    main()