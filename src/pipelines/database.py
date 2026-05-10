from itemadapter import ItemAdapter
from models.base import get_engine, get_session_factory
from repositories.job_repository import JobRepository


class DatabasePipeline:
    """Batch save items to TimescaleDB."""

    BATCH_SIZE = 50

    def __init__(self):
        self.batch: list[dict] = []
        self.repo: JobRepository | None = None
        self.total_saved = 0

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        pipeline.crawler = crawler
        pipeline.database_url = crawler.settings.get("DATABASE_URL")
        return pipeline

    def open_spider(self):
        spider = self.crawler.spider
        engine = get_engine(self.database_url)
        session_factory = get_session_factory(engine)
        self.repo = JobRepository(session_factory)
        spider.logger.info("DatabasePipeline: Connected to TimescaleDB")

    def process_item(self, item):
        self.batch.append(dict(ItemAdapter(item)))
        if len(self.batch) >= self.BATCH_SIZE:
            self._flush()
        return item

    def close_spider(self):
        spider = self.crawler.spider
        self._flush()
        spider.logger.info(f"DatabasePipeline: Total saved to DB = {self.total_saved}")

    def _flush(self):
        if not self.batch:
            return
        spider = self.crawler.spider
        saved = self.repo.save_batch(self.batch)
        self.total_saved += saved
        spider.logger.info(f"DatabasePipeline: Flushed {saved}/{len(self.batch)} items")
        self.batch.clear()
