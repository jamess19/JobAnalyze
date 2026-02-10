import os
from scrapy.exceptions import DropItem
from itemadapter import ItemAdapter
from utils.deduplicator import MinHashDeduplicator


class DeduplicationPipeline:
    """2-layer dedup: exact URL match + MinHash near-duplicate."""

    def __init__(self):
        self.seen_urls: set[str] = set()
        self.seen_file = "data/seen_jobs.txt"
        self.deduplicator = MinHashDeduplicator()
        self.stats = {"exact_dup": 0, "near_dup": 0, "unique": 0}

    def open_spider(self, spider):
        self._load_seen_urls()
        spider.logger.info(
            f"DeduplicationPipeline: Loaded {len(self.seen_urls)} seen URLs"
        )

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get("job_url", "")

        # Layer 1: Exact URL match (O(1) lookup)
        if url in self.seen_urls:
            self.stats["exact_dup"] += 1
            raise DropItem(f"Exact duplicate: {url}")

        # Layer 2: Near-duplicate via MinHash LSH
        text = " ".join(filter(None, [
            adapter.get("title", ""),
            adapter.get("description", ""),
            adapter.get("requirements", ""),
        ]))
        if text.strip() and self.deduplicator.is_duplicate(text):
            self.stats["near_dup"] += 1
            raise DropItem(f"Near-duplicate content: {url}")

        # Unique item
        self.seen_urls.add(url)
        self._save_seen_url(url)
        self.deduplicator.add(text)
        self.stats["unique"] += 1
        return item

    def close_spider(self, spider):
        spider.logger.info(
            f"Dedup stats: {self.stats['unique']} unique, "
            f"{self.stats['exact_dup']} exact dups, "
            f"{self.stats['near_dup']} near dups"
        )

    def _load_seen_urls(self):
        if os.path.exists(self.seen_file):
            try:
                with open(self.seen_file, "r", encoding="utf-8") as f:
                    self.seen_urls = {line.strip() for line in f if line.strip()}
            except Exception as e:
                print(f"Error loading seen URLs: {e}")

    def _save_seen_url(self, url: str):
        try:
            os.makedirs(os.path.dirname(self.seen_file), exist_ok=True)
            with open(self.seen_file, "a", encoding="utf-8") as f:
                f.write(f"{url}\n")
        except Exception as e:
            print(f"Error saving seen URL: {e}")
