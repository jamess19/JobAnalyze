#!/usr/bin/env python3
"""
Spider Runner - CLI tool to run Scrapy spiders
"""

import sys
import os
import argparse
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from spiders.spiders.itviec_spider import ItviecSpider
from spiders.spiders.topcv_spider import TopcvSpider


def run_spider(spider_name, keyword, location, start_page, end_page):
    """
    Run a specific spider
    
    :param spider_name: Name of spider to run (itviec/topcv/all)
    :param keyword: Search keyword
    :param location: Search location
    :param start_page: Starting page number
    :param end_page: Ending page number
    """
    # Create necessary directories
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    # Get Scrapy settings
    settings = get_project_settings()
    
    # Override settings if needed
    settings.set('LOG_LEVEL', 'INFO')
    # logger.info("Starting spider runner")
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Spider mapping
    spiders = {
        'itviec': ItviecSpider,
        'topcv': TopcvSpider,
    }
    
    # Determine which spiders to run
    if spider_name == 'all':
        spiders_to_run = spiders.values()
        print(f"🚀 Running ALL spiders: {', '.join(spiders.keys())}")
    elif spider_name in spiders:
        spiders_to_run = [spiders[spider_name]]
        print(f"🚀 Running {spider_name} spider")
    else:
        print(f"❌ Error: Unknown spider '{spider_name}'")
        print(f"Available spiders: {', '.join(spiders.keys())}, all")
        return False
    
    # Run spiders
    for spider_class in spiders_to_run:
        print(f"\n{'='*60}")
        print(f"Starting {spider_class.name}")
        print(f"{'='*60}")
        print(f"Keyword: {keyword}")
        print(f"Location: {location}")
        print(f"Pages: {start_page} to {end_page}")
        print(f"{'='*60}\n")
        
        process.crawl(
            spider_class,
            keyword=keyword,
            location=location,
            start_page=start_page,
            end_page=end_page
        )
    
    # Start crawling
    print(f"\n⏳ Starting crawl process...")
    start_time = datetime.now()
    
    try:
        process.start()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print(f"✅ Crawl completed successfully!")
        print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print(f"{'='*60}\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during crawl: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Run Scrapy spiders to scrape job listings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            # Run ITViec spider for software engineer jobs in Ho Chi Minh
            python run_spiders.py itviec -k "software engineer" -l "Ho Chi Minh" -s 1 -e 3
            
            # Run TopCV spider for data engineer jobs
            python run_spiders.py topcv -k "data engineer" -l "Ha Noi" -s 1 -e 2
            
            # Run all spiders
            python run_spiders.py all -k "python developer" -l "Ho Chi Minh" -s 1 -e 1
            
            # Run with default settings
            python run_spiders.py itviec"""
        )
    
    parser.add_argument(
        'spider',
        choices=['itviec', 'topcv', 'all'],
        help='Spider to run (itviec, topcv, or all)'
    )
    
    parser.add_argument(
        '-k', '--keyword',
        default='software engineer',
        help='Search keyword (default: software engineer)'
    )
    
    parser.add_argument(
        '-l', '--location',
        default='Ho Chi Minh',
        help='Search location (default: Ho Chi Minh)'
    )
    
    parser.add_argument(
        '-s', '--start-page',
        type=int,
        default=1,
        help='Starting page number (default: 1)'
    )
    
    parser.add_argument(
        '-e', '--end-page',
        type=int,
        default=1,
        help='Ending page number (default: 1)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    
    args = parser.parse_args()
    
    # Run spider
    success = run_spider(
        spider_name=args.spider,
        keyword=args.keyword,
        location=args.location,
        start_page=args.start_page,
        end_page=args.end_page
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

