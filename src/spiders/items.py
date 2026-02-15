# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class JobItem(scrapy.Item):
    """
    Unified Job Item Schema - Tổng hợp từ ITViec, TopCV, LinkedIn
    Tối ưu cho Time Series LSTM Model
    """
    # --- GROUP 1: IDENTIFICATION & TIME (REQUIRED) ---
    # Necessary for creating Time Series Index
    source = scrapy.Field()               # e.g., 'itviec'
    job_id = scrapy.Field()               # Original ID from the website (e.g., '12345')
    job_url = scrapy.Field()              # To trace back if data is strange
    crawl_date = scrapy.Field()           # Bot run time (datetime)
    # date_posted_raw = scrapy.Field()      # Original text: "2 hours ago" (for debugging)
    date_posted = scrapy.Field()          # Converted: YYYY-MM-DD (Most important feature)
    
    # --- GROUP 2: RAW DATA FOR NLP (FEATURE SOURCE) ---
    # This is the raw material for Service 2 to extract skills, level...
    title = scrapy.Field()                # Job title
    
    # Combine Description, Requirements, Benefits, Responsibilities here if possible
    # Or separate if the website structure is clear. BUT always save original TEXT/HTML.
    # description_full = scrapy.Field()     # Save lightly cleaned full text/html
    description = scrapy.Field()          # Job description
    requirements = scrapy.Field()     # Original requirements text
    benefits = scrapy.Field()         # Original benefits text

    # --- GROUP 3: METADATA (IF AVAILABLE) ---
    # Only store if available on the web, DO NOT infer
    skills_tags = scrapy.Field()          # List tag có sẵn trên web (VD: ['Java', 'Spring'])
    
    location_raw = scrapy.Field()         # Text gốc: "District 1, Ho Chi Minh"
    salary_raw = scrapy.Field()           # Text gốc: "$1000 - $2000", "Thương lượng"
    
    company_name = scrapy.Field()
    
    # --- GROUP 4: METRICS (IF AVAILABLE) ---
    # Very valuable for assessing "hotness" (Demand Weight)
    view_count = scrapy.Field()           
    application_count = scrapy.Field()    

    # --- GROUP 5: EXTRA  ---
    # Các field không đồng nhất giữa các web (job_level, employment_type...)
    # Hãy nhét hết vào đây dưới dạng Dict
    extra_data = scrapy.Field()
    
    # --- GROUP 6: DEDUPLICATION & NLP (INTERNAL PROCESSING) ---
    # Fields used by pipelines for deduplication and skill extraction
    lsh_buckets = scrapy.Field()          # List of (band_idx, bucket_hash) tuples for LSH
    minhash_signature = scrapy.Field()    # List of 128 integers for Jaccard similarity
    domains = scrapy.Field()              # List of business domains (from SkillExtractor)

SpidersItem = JobItem