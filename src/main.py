#!/usr/bin/env python3
"""Main entry point - thin orchestrator."""

import os
import sys
import argparse
import warnings

os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "settings")

from config.config import DEFAULT_CONFIG
from services.scraper_service import ScraperService
from services.export_service import ExportService
from pipelines.export import ExportPipeline

# scrapy-playwright's background loop thread has a known shutdown race on Windows
# (_ThreadedLoopAdapter.stop() calls loop.stop() without waiting for queue.join() to
# finish, see scrapy_playwright/_loop.py). It only surfaces as harmless noise after
# the program has already finished (exit code is unaffected) — no fixed release exists
# yet, so hide only this exact signature and let any other unraisable exception through.
warnings.filterwarnings("ignore", message="coroutine 'Queue.join' was never awaited")
_default_unraisablehook = sys.unraisablehook


def _hide_playwright_loop_closed_noise(unraisable):
    if unraisable.exc_type is RuntimeError and "Event loop is closed" in str(unraisable.exc_value):
        return
    _default_unraisablehook(unraisable)


sys.unraisablehook = _hide_playwright_loop_closed_noise


def build_spider_configs(config: dict, spider_filter: str = None, max_pages: int = None, url: str = None, keyword: str = None) -> list[dict]:
    configs = []

    # ITViec
    itviec_urls = [url] if url else config.get("itviec_urls")
    if itviec_urls:
        configs.append({
            "spider": "itviec",
            "urls": itviec_urls,
            "max_pages": max_pages,
        })

    # TopCV
    topcv_urls = [url] if url else config.get("topcv_urls")
    if topcv_urls:
        configs.append({
            "spider": "topcv",
            "urls": topcv_urls,
            "max_pages": max_pages,
        })
    
    # LinkedIn
    linkedin_keywords = [keyword] if keyword else config.get("linkedin_keywords")
    if linkedin_keywords:
        configs.append({
            "spider": "linkedin",
            "keywords": linkedin_keywords,
            "location": config.get("linkedin_location", "Vietnam"),
            "max_pages": max_pages,
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
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Giới hạn số trang search crawl cho itviec/topcv, vd: --max-pages 1 chỉ crawl trang đầu (default: không giới hạn)"
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Chỉ crawl 1 URL cụ thể (ghi đè toàn bộ danh sách URL trong config.py). Dùng kèm --spider để chọn đúng spider, vd: --spider topcv --url \"https://...\" --max-pages 1"
    )
    parser.add_argument(
        "--keyword",
        type=str,
        default=None,
        help="Chỉ crawl 1 từ khoá LinkedIn cụ thể (ghi đè toàn bộ linkedin_keywords trong config.py), vd: --spider linkedin --keyword \"Data Analyst\" --max-pages 1"
    )
    args = parser.parse_args()

    config = DEFAULT_CONFIG
    output_folder = config.get("output_folder", "src/data")
    spider_configs = build_spider_configs(
        config, spider_filter=args.spider, max_pages=args.max_pages, url=args.url, keyword=args.keyword
    )

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
        try:
            export_svc = ExportService(output_folder, config.get("drive_folder_id"))
            export_svc.upload_to_drive(csv_path)
        except Exception as e:
            print(f"[WARNING] Google Drive upload failed, skipping: {e}")
    else:
        print("No new data to upload.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
