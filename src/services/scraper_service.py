from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from pipelines.export import ExportPipeline
from spiders.spiders.itviec_spider import ItviecSpider
from spiders.spiders.topcv_spider import TopcvSpider
from spiders.spiders.linkedin_spider import LinkedinSpider

SPIDER_CLASSES = {
    "itviec": ItviecSpider,
    "topcv": TopcvSpider,
    "linkedin": LinkedinSpider,
}


class ScraperService:
    def __init__(self, spider_configs: list[dict]):
        self.spider_configs = spider_configs

    def run(self):
        """Run all configured spiders. Pipeline handles everything."""
        settings = get_project_settings()
        process = CrawlerProcess(settings)

        for config in self.spider_configs:
            spider_name = config["spider"]
            spider_class = SPIDER_CLASSES.get(spider_name)
            if not spider_class:
                continue

            if config.get("urls"):
                # URL-based crawl: one instance per URL
                for url in config["urls"]:
                    process.crawl(spider_class, start_url=url)
            else:
                # Legacy keyword-based crawl (LinkedIn still uses this)
                for keyword in config.get("keywords", []):
                    process.crawl(
                        spider_class,
                        keyword=keyword,
                        location=config.get("location", ""),
                        start_page=config.get("start_page", 1),
                        end_page=config.get("end_page", 1),
                    )

        process.start()

        # All spiders have finished — write everything to one consolidated file
        ExportPipeline.export_all()
