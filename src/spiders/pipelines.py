"""
Item Pipelines - Process scraped items
"""

import os
import json
import csv
from datetime import datetime
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem
import pandas as pd
from utils.normalizer import DataNormalizer
from utils.field_extractor import FieldExtractor


class ValidationPipeline:
    """Validate scraped items"""
    
    def __init__(self):
        self.required_fields = ['job_url', 'title', 'source']
    
    def process_item(self, item, spider):
        """
        Validate item has required fields
        
        :param item: Scraped item
        :param spider: Spider instance
        :return: Item if valid
        :raises DropItem: If validation fails
        """
        adapter = ItemAdapter(item)
        
        # Check required fields
        for field in self.required_fields:
            if not adapter.get(field):
                raise DropItem(f"Missing required field: {field} in {item}")
        
        # Validate URL format
        job_url = adapter.get('job_url')
        if job_url and not job_url.startswith('http'):
            raise DropItem(f"Invalid job_url format: {job_url}")
        
        # Validate source
        valid_sources = ['itviec', 'topcv', 'linkedin']
        if adapter.get('source') not in valid_sources:
            spider.logger.warning(f"Unknown source: {adapter.get('source')}")
        
        spider.logger.debug(f"Item validated: {adapter.get('job_url')}")
        return item


class CleaningPipeline:
    """Clean text data only - NO normalization
    
    All data normalization (location, salary, skills, etc.) 
    will be handled by the ML service.
    This pipeline only performs basic text cleaning.
    """
    
    def __init__(self):
        self.normalizer = DataNormalizer()
    
    def process_item(self, item, spider):
        """
        Clean text fields only (remove HTML tags, normalize whitespace)
        
        :param item: Scraped item
        :param spider: Spider instance
        :return: Item with cleaned text
        """
        adapter = ItemAdapter(item)
        
        # Clean text fields: remove HTML tags, normalize whitespace
        text_fields = ['description', 'requirements', 'benefits']
        for field in text_fields:
            if adapter.get(field):
                try:
                    adapter[field] = self.normalizer.clean_text(adapter[field])
                except Exception as e:
                    spider.logger.warning(f"Error cleaning field '{field}': {e}")
        
        spider.logger.debug(f"Text cleaned for: {adapter.get('job_url')}")
        return item


class DeduplicationPipeline:
    """Remove duplicate items based on job_url"""
    
    def __init__(self):
        self.seen_urls = set()
        self.seen_file = 'data/seen_jobs.txt'
        self._load_seen_urls()
    
    def process_item(self, item, spider):
        """
        Check for duplicate items
        :param item: Scraped item
        :param spider: Spider instance
        :return: Item if not duplicate
        :raises DropItem: If duplicate found
        """
        adapter = ItemAdapter(item)
        job_url = adapter.get('job_url')
        
        if job_url in self.seen_urls:
            raise DropItem(f"Duplicate item found: {job_url}")
        
        self.seen_urls.add(job_url)
        self._save_seen_url(job_url)
        
        spider.logger.debug(f"Item is unique: {job_url}")
        return item
    
    def _load_seen_urls(self):
        """Load previously seen URLs from file"""
        if os.path.exists(self.seen_file):
            try:
                with open(self.seen_file, 'r', encoding='utf-8') as f:
                    self.seen_urls = set(line.strip() for line in f if line.strip())
            except Exception as e:
                print(f"Error loading seen URLs: {e}")
    
    def _save_seen_url(self, url: str):
        """Save URL to seen file"""
        try:
            os.makedirs(os.path.dirname(self.seen_file), exist_ok=True)
            with open(self.seen_file, 'a', encoding='utf-8') as f:
                f.write(f"{url}\n")
        except Exception as e:
            print(f"Error saving seen URL: {e}")
            
    def close_spider(self, spider):
        """Called when spider closes"""
        spider.logger.info(f"Deduplication: {len(self.seen_urls)} unique URLs tracked")


class ExportPipeline:
    """Export items to CSV, JSON, and Excel"""
    
    def __init__(self):
        self.items = []
        self.output_dir = 'data' 
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def open_spider(self, spider):
        """Called when spider opens"""
        os.makedirs(self.output_dir, exist_ok=True)
        spider.logger.info(f"Export pipeline initialized. Output dir: {self.output_dir}")
    
    def process_item(self, item, spider):
        """
        Collect items for batch export
        
        :param item: Scraped item
        :param spider: Spider instance
        :return: Item
        """
        # Convert item to dict
        adapter = ItemAdapter(item)
        item_dict = dict(adapter)
        
        self.items.append(item_dict)
        spider.logger.debug(f"Item collected for export: {adapter.get('job_url')}")
        
        return item
    
    def close_spider(self, spider):
        """
        Called when spider closes
        Export all collected items
        """
        if not self.items:
            spider.logger.warning("No items to export")
            return
        
        spider.logger.info(f"Exporting {len(self.items)} items...")
        
        # Create DataFrame
        df = pd.DataFrame(self.items)
        
        # Define column order (prioritize important fields for LSTM)
        priority_columns = [
            'crawl_date', 'date_posted', 'source', 'job_id', 'job_url',
            'title', 'job_category', 'job_level',
            'location_city', 'location_raw',
            'experience_level', 'experience_required',
            'salary_min', 'salary_max', 'salary_avg', 'salary_currency', 'salary_raw',
            'skills_required',
            'company_name', 'company_name_full', 'company_size', 'company_industry',
            'employment_type', 'work_mode',
            'description', 'requirements', 'benefits',
            'deadline',
            'company_url', 'company_website', 'company_address', 'company_description',
        ]
        
        # Reorder columns
        existing_cols = [col for col in priority_columns if col in df.columns]
        other_cols = [col for col in df.columns if col not in priority_columns]
        df = df[existing_cols + other_cols]
        
        # Generate filenames
        spider_name = spider.name.replace('_spider', '')
        base_filename = f"{spider_name}_jobs_{self.timestamp}"
        
        # Export to CSV
        csv_path = os.path.join(self.output_dir, f"{base_filename}.csv")
        try:
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            spider.logger.info(f"✓ Exported to CSV: {csv_path}")
        except Exception as e:
            spider.logger.error(f"Error exporting to CSV: {e}")
        
        # Export to JSON
        json_path = os.path.join(self.output_dir, f"{base_filename}.json")
        try:
            df.to_json(json_path, orient='records', indent=2, force_ascii=False)
            spider.logger.info(f"✓ Exported to JSON: {json_path}")
        except Exception as e:
            spider.logger.error(f"Error exporting to JSON: {e}")
        
        # Export to Excel
        excel_path = os.path.join(self.output_dir, f"{base_filename}.xlsx")
        try:
            df.to_excel(excel_path, index=False, engine='openpyxl')
            spider.logger.info(f"✓ Exported to Excel: {excel_path}")
        except Exception as e:
            spider.logger.error(f"Error exporting to Excel: {e}")
                
        spider.logger.info(f"Export complete! {len(self.items)} items exported.")

class DatabasePipeline:
    """Save items to database"""
    
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = os.getenv('MONGODB_URI', '')
        self.mongo_db = os.getenv('MONGODB_DB', 'job_crawler_db')
        self.repo = None
    
    def process_item(self, item, spider):
        """
        Save item to database"""
# Legacy pipeline (keep for backward compatibility)
class SpidersPipeline:
    def process_item(self, item, spider):
        return item
