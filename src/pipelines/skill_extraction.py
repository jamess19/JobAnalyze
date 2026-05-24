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
from utils.utils import clean_company_intro

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
        
        # Loại bỏ phần giới thiệu công ty trước khi đưa vào bộ trích xuất skill (tránh over-extraction)
        cleaned_desc = clean_company_intro(description)
        cleaned_req = clean_company_intro(requirements)
        full_text = f"{cleaned_desc}\n{cleaned_req}".strip()

        if not full_text:
            logger.info(f"SkillExtractionPipeline: NO text extracted for '{adapter.get('title')}' - skipping NLP")
            return item

        logger.info(f"SkillExtractionPipeline: Processing text (length {len(full_text)}) for '{adapter.get('title')}'")

        # --- Chạy NLP ---
        # [PATCH 1] Kết quả NLP được lưu hoàn toàn trong biến LOCAL của hàm này.
        # Tuyệt đối không tích lũy vào self.extractor hay bất kỳ biến instance nào
        # để tránh rò rỉ dữ liệu giữa các item (cross-item contamination).
        try:
            nlp_result: dict = self.extractor.extract(full_text)
        except Exception as e:
            logger.warning(f"SkillExtractionPipeline: NLP failed for job "
                           f"'{adapter.get('job_url')}': {e}")
            return item

        # Biến local, không gán vào self hay self.extractor
        nlp_skills: list[str] = nlp_result.get("skills") or []
        nlp_domains: list[str] = nlp_result.get("domains") or []

        # --- Merge skills vào skills_tags ---
        existing_tags = adapter.get("skills_tags") or []
        if isinstance(existing_tags, str):
            existing_tags = [s.strip() for s in existing_tags.split(",") if s.strip()]

        # Combine all skills then normalize + deduplicate
        all_skills: list[str] = list(existing_tags) + list(nlp_skills)
        normalized: list[str] = self.skill_normalizer.normalize_list(all_skills)

        # [PATCH 3] Final dedup safeguard: dùng set để loại bỏ mọi duplicate còn sót
        # sau quá trình normalize (phòng edge case: hai synonym khác nhau cùng map
        # về một canonical name nhưng normalize_list bị race hoặc dữ liệu cũ).
        # Dùng dict.fromkeys để giữ nguyên thứ tự (insertion-order, Python 3.7+).
        normalized = list(dict.fromkeys(normalized))

        if normalized:
            adapter["skills_tags"] = normalized
            logger.info(f"SkillExtractionPipeline: {len(normalized)} skills for '{adapter.get('title')}': {normalized}")

        # --- Merge domains vào extra_data['domains'] ---
        if nlp_domains:
            extra_data = adapter.get("extra_data") or {}
            if not isinstance(extra_data, dict):
                extra_data = {}

            existing_domains: list[str] = extra_data.get("domains") or []
            existing_domains_lower: set[str] = {d.lower() for d in existing_domains}
            new_domains = [d for d in nlp_domains if d.lower() not in existing_domains_lower]

            if new_domains:
                extra_data["domains"] = existing_domains + new_domains
                adapter["extra_data"] = extra_data
                logger.debug(f"SkillExtractionPipeline: +{len(new_domains)} NLP domains "
                             f"for '{adapter.get('title')}': {new_domains}")

        return item
