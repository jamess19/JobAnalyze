from itemadapter import ItemAdapter
from utils.normalizer import DataNormalizer


class CleaningPipeline:
    """Clean text data only - NO normalization

    All data normalization (location, salary, skills, etc.)
    will be handled by the ML service.
    This pipeline only performs basic text cleaning.
    """

    def __init__(self):
        self.normalizer = DataNormalizer()

    def process_item(self, item, spider):
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
