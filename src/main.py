#!/usr/bin/env python3
"""Main entry point - thin orchestrator."""

import os
import sys
import argparse

os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "settings")

from config.config import DEFAULT_CONFIG
from services.scraper_service import ScraperService
from services.export_service import ExportService
from pipelines.export import ExportPipeline


def build_spider_configs(config: dict, spider_filter: str = None) -> list[dict]:
    configs = []
    
    # ITViec
    if config.get("itviec_urls"):
        configs.append({
            "spider": "itviec",
            "urls": config["itviec_urls"],
        })

    # TopCV
    if config.get("topcv_urls"):
        configs.append({
            "spider": "topcv",
            "urls": config["topcv_urls"],
        })
    
    # LinkedIn
    if config.get("linkedin_keywords"):
        configs.append({
            "spider": "linkedin",
            "keywords": config["linkedin_keywords"],
            "location": config.get("linkedin_location", "Vietnam"),
            "start_page": config.get("linkedin_start_page", 1),  # Fix hardcode
            "end_page": config.get("linkedin_end_page", 2),       # Fix hardcode
        })
    
    # Filter nếu có --spider argument
    if spider_filter and spider_filter != "all":
        configs = [c for c in configs if c["spider"] == spider_filter]
    
    return configs


def main() -> int:
    # Add argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spider",
        choices=["itviec", "topcv", "linkedin", "all"],
        default="all",
        help="Spider to run (default: all)"
    )
    args = parser.parse_args()
    
    config = DEFAULT_CONFIG
    output_folder = config.get("output_folder", "src/data")
    spider_configs = build_spider_configs(config, spider_filter=args.spider)

    if not spider_configs:
        print(f"No spider configurations found for: {args.spider}")
        return 1

    print(f"Running spiders: {[c['spider'] for c in spider_configs]}")

    # Step 1: Scrape - Pipeline handles validate/clean/dedup/save DB/export
    scraper = ScraperService(spider_configs)
    scraper.run()

    # All spiders have finished — write everything to one consolidated file
    csv_path = ExportPipeline.export_all(output_dir=output_folder)

    # Step 2: (Optional) Upload latest export to Drive
    if csv_path and os.path.exists(csv_path):
        export_svc = ExportService(output_folder, config.get("drive_folder_id"))
        export_svc.upload_to_drive(csv_path)
    else:
        print("No new data to upload.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
