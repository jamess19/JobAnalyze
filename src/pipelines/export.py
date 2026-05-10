import os
import threading
from datetime import datetime
from itemadapter import ItemAdapter
import pandas as pd


# Define column order (prioritize important fields)
_PRIORITY_COLUMNS = [
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


class ExportPipeline:
    """Export items to CSV, JSON, and Excel.

    Uses class-level shared storage so all spider instances (one per keyword)
    accumulate items together.  Actual file writing is deferred to
    :meth:`export_all`, which should be called once after *all* spiders finish.
    """

    _shared_items: list = []
    _lock = threading.Lock()

    def __init__(self):
        self.output_dir = 'data'

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def open_spider(self):
        spider = self.crawler.spider
        os.makedirs(self.output_dir, exist_ok=True)
        spider.logger.info(f"Export pipeline initialized. Output dir: {self.output_dir}")

    def process_item(self, item):
        spider = self.crawler.spider
        adapter = ItemAdapter(item)
        item_dict = dict(adapter)
        with ExportPipeline._lock:
            ExportPipeline._shared_items.append(item_dict)
        spider.logger.debug(f"Item collected for export: {adapter.get('job_url')}")
        return item

    def close_spider(self):
        spider = self.crawler.spider
        spider.logger.info(
            f"Spider '{spider.name}' finished. "
            f"Total items collected so far: {len(ExportPipeline._shared_items)}"
        )

    @classmethod
    def export_all(cls, output_dir: str = 'data', timestamp: str = None) -> str | None:
        """Write all accumulated items to a single set of files.

        Call this once after all spiders have completed.
        Returns the CSV file path, or None if there were no items.
        """
        if not cls._shared_items:
            print("[ExportPipeline] No items to export.")
            return None

        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        df = pd.DataFrame(cls._shared_items)

        # Reorder columns
        existing_cols = [col for col in _PRIORITY_COLUMNS if col in df.columns]
        other_cols = [col for col in df.columns if col not in _PRIORITY_COLUMNS]
        df = df[existing_cols + other_cols]

        os.makedirs(output_dir, exist_ok=True)
        base_filename = f"all_jobs_{timestamp}"

        # Export to CSV
        csv_path = os.path.join(output_dir, f"{base_filename}.csv")
        try:
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"[ExportPipeline] Exported to CSV: {csv_path}")
        except Exception as e:
            print(f"[ExportPipeline] Error exporting to CSV: {e}")

        # Export to JSON
        json_path = os.path.join(output_dir, f"{base_filename}.json")
        try:
            df.to_json(json_path, orient='records', indent=2, force_ascii=False)
            print(f"[ExportPipeline] Exported to JSON: {json_path}")
        except Exception as e:
            print(f"[ExportPipeline] Error exporting to JSON: {e}")

        # Export to Excel
        excel_path = os.path.join(output_dir, f"{base_filename}.xlsx")
        try:
            df.to_excel(excel_path, index=False, engine='openpyxl')
            print(f"[ExportPipeline] Exported to Excel: {excel_path}")
        except Exception as e:
            print(f"[ExportPipeline] Error exporting to Excel: {e}")

        print(
            f"[ExportPipeline] Export complete! "
            f"{len(cls._shared_items)} total items → {base_filename}.*"
        )
        cls._shared_items.clear()
        return csv_path
