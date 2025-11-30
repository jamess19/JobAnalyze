#!/usr/bin/env python3
"""
Script to crawl LinkedIn jobs and save to CSV
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "crawl-data"))

from linkedin_crawler import LinkedInCrawler


def main():
    # Create crawler
    crawler = LinkedInCrawler(
        output_path="data/raw",
        search_term="software engineer",
        location="Vietnam",
        results_wanted=20,
        hours_old=72,
        fetch_description=True
    )

    # Crawl data
    print(f"Crawling jobs for '{crawler.search_term}' in '{crawler.location}'...")
    jobs_data = crawler.crawl()

    # Save to multiple formats
    if jobs_data.empty is False:
        # Save as CSV
        csv_filepath = crawler.save_raw_data("linkedin_jobs", file_type="csv")
        if csv_filepath:
            print(f"CSV file saved: {csv_filepath}")

        # Save as JSON
        json_filepath = crawler.save_raw_data("linkedin_jobs", file_type="json")
        if json_filepath:
            print(f"JSON file saved: {json_filepath}")

        # Save as Excel
        excel_filepath = crawler.save_raw_data("linkedin_jobs", file_type="excel")
        if excel_filepath:
            print(f"Excel file saved: {excel_filepath}")


if __name__ == "__main__":
    main()
