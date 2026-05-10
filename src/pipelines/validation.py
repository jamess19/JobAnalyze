import logging
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Validate scraped items"""

    def __init__(self):
        self.required_fields = ['job_url', 'title', 'source']

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        return pipeline

    def process_item(self, item):
        adapter = ItemAdapter(item)
        spider = self.crawler.spider

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
