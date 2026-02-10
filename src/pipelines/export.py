import os
from datetime import datetime
from itemadapter import ItemAdapter
import pandas as pd


class ExportPipeline:
    """Export items to CSV, JSON, and Excel"""

    def __init__(self):
        self.items = []
        self.output_dir = 'data'
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def open_spider(self, spider):
        os.makedirs(self.output_dir, exist_ok=True)
        spider.logger.info(f"Export pipeline initialized. Output dir: {self.output_dir}")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        item_dict = dict(adapter)

        self.items.append(item_dict)
        spider.logger.debug(f"Item collected for export: {adapter.get('job_url')}")

        return item

    def close_spider(self, spider):
        if not self.items:
            spider.logger.warning("No items to export")
            return

        spider.logger.info(f"Exporting {len(self.items)} items...")

        df = pd.DataFrame(self.items)

        # Define column order (prioritize important fields)
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
            spider.logger.info(f"Exported to CSV: {csv_path}")
        except Exception as e:
            spider.logger.error(f"Error exporting to CSV: {e}")

        # Export to JSON
        json_path = os.path.join(self.output_dir, f"{base_filename}.json")
        try:
            df.to_json(json_path, orient='records', indent=2, force_ascii=False)
            spider.logger.info(f"Exported to JSON: {json_path}")
        except Exception as e:
            spider.logger.error(f"Error exporting to JSON: {e}")

        # Export to Excel
        excel_path = os.path.join(self.output_dir, f"{base_filename}.xlsx")
        try:
            df.to_excel(excel_path, index=False, engine='openpyxl')
            spider.logger.info(f"Exported to Excel: {excel_path}")
        except Exception as e:
            spider.logger.error(f"Error exporting to Excel: {e}")

        spider.logger.info(f"Export complete! {len(self.items)} items exported.")
