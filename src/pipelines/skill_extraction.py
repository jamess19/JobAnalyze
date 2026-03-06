"""
SkillExtractionPipeline

Chạy sau CleaningPipeline (200) và trước DeduplicationPipeline (300).
Trích xuất skill + domain từ description/requirements bằng NLP (Spacy EntityRuler),
sau đó merge vào skills_tags và extra_data['domains'] của item.

Lý do dùng pipeline riêng (không làm trong spider):
- Spider chỉ nên thu thập data thô.
- NLP nặng → khởi động 1 lần duy nhất qua singleton, tái dùng cho mọi spider.
"""

import logging
from itemadapter import ItemAdapter
from utils.skill_extractor import get_skill_extractor
from utils.skill_normalizer import SkillNormalizer

logger = logging.getLogger(__name__)


class SkillExtractionPipeline:
    """
    Bổ sung skill và domain từ NLP vào item.

    Chiến lược:
    - Luôn chạy NLP trên description + requirements (không chỉ khi skills_tags trống)
      để bắt những skill không có tag HTML hoặc bị whitelist filter bỏ sót.
    - Kết quả NLP được MERGE (union) với skills_tags có sẵn.
    - Domain trích xuất được ghi vào extra_data['domains'].
    """

    def open_spider(self, spider):
        self.extractor = get_skill_extractor()
        self.skill_normalizer = SkillNormalizer()
        spider.logger.info("SkillExtractionPipeline: NLP SkillExtractor ready")

    def close_spider(self, spider):
        # Flush unmapped skills frequency report at end of crawl
        log_path = self.skill_normalizer.flush_unmapped_log(threshold=1)
        if log_path:
            spider.logger.info(f"SkillExtractionPipeline: unmapped skills report → {log_path}")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # --- Lấy text để phân tích ---
        description = adapter.get("description") or ""
        requirements = adapter.get("requirements") or ""
        full_text = f"{description} {requirements}".strip()

        if not full_text:
            return item

        # --- Chạy NLP ---
        try:
            result = self.extractor.extract(full_text)
        except Exception as e:
            logger.warning(f"SkillExtractionPipeline: NLP failed for job "
                           f"'{adapter.get('job_url')}': {e}")
            return item

        nlp_skills: list[str] = result.get("skills") or []
        nlp_domains: list[str] = result.get("domains") or []

        # --- Merge skills vào skills_tags ---
        existing_tags = adapter.get("skills_tags") or []
        if isinstance(existing_tags, str):
            existing_tags = [s.strip() for s in existing_tags.split(",") if s.strip()]

        # Combine all skills then normalize + deduplicate
        all_skills = existing_tags + nlp_skills
        normalized = self.skill_normalizer.normalize_list(all_skills)

        if normalized:
            adapter["skills_tags"] = normalized
            logger.debug(f"SkillExtractionPipeline: {len(normalized)} normalized skills "
                         f"for '{adapter.get('title')}'")

        # --- Merge domains vào extra_data['domains'] ---
        if nlp_domains:
            extra_data = adapter.get("extra_data") or {}
            if not isinstance(extra_data, dict):
                extra_data = {}

            existing_domains = extra_data.get("domains") or []
            existing_domains_lower = {d.lower() for d in existing_domains}
            new_domains = [d for d in nlp_domains if d.lower() not in existing_domains_lower]

            if new_domains:
                extra_data["domains"] = existing_domains + new_domains
                adapter["extra_data"] = extra_data
                logger.debug(f"SkillExtractionPipeline: +{len(new_domains)} NLP domains "
                             f"for '{adapter.get('title')}': {new_domains}")

        return item
