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
                if spider_name == "topcv":
                    # TopCV: single instance processes all URLs sequentially
                    process.crawl(spider_class, start_urls=config["urls"])
                else:
                    # Other spiders: one instance per URL (parallel)
                    for url in config["urls"]:
                        process.crawl(spider_class, start_url=url)
            elif config.get("keywords"):
                # Keyword-based crawl: ONE spider instance handles all keywords sequentially
                process.crawl(
                    spider_class,
                    keywords=config["keywords"],
                    location=config.get("location", ""),
                )

        process.start()

        # All spiders have finished — write everything to one consolidated file
        ExportPipeline.export_all()
