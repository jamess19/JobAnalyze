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
    # --- NHÓM 1: ĐỊNH DANH & THỜI GIAN (BẮT BUỘC) ---
    # Cần thiết để tạo Time Series Index
    source = scrapy.Field()               # VD: 'itviec'
    job_id = scrapy.Field()               # ID gốc từ web (VD: '12345')
    job_url = scrapy.Field()              # Để truy vết lại nếu dữ liệu lạ
    crawl_date = scrapy.Field()           # Thời điểm chạy bot (datetime)
    # date_posted_raw = scrapy.Field()      # Text gốc: "2 hours ago" (để debug)
    date_posted = scrapy.Field()          # Đã convert: YYYY-MM-DD (Feature quan trọng nhất)
    
    # --- NHÓM 2: DỮ LIỆU THÔ ĐỂ NLP (FEATURE SOURCE) ---
    # Đây là nguyên liệu để Service 2 trích xuất skills, level...
    title = scrapy.Field()                # Tiêu đề
    
    # Gộp Description, Requirements, Benefits, Responsibilities vào đây nếu có thể
    # Hoặc tách ra nếu web cấu trúc rõ ràng. NHƯNG hãy lưu TEXT/HTML gốc.
    # description_full = scrapy.Field()     # Lưu full text/html đã clean nhẹ
    description = scrapy.Field()          # Mô tả công việc
    requirements = scrapy.Field()     # Text yêu cầu gốc
    benefits = scrapy.Field()         # Text quyền lợi gốc

    # --- NHÓM 3: THUỘC TÍNH CÓ SẴN (METADATA) ---
    # Chỉ lưu nếu web có sẵn, KHÔNG tự suy diễn
    skills_tags = scrapy.Field()          # List tag có sẵn trên web (VD: ['Java', 'Spring'])
    
    location_raw = scrapy.Field()         # Text gốc: "District 1, Ho Chi Minh"
    salary_raw = scrapy.Field()           # Text gốc: "$1000 - $2000", "Thương lượng"
    
    company_name = scrapy.Field()
    
    # --- NHÓM 4: METRICS (NẾU CÓ) ---
    # Rất quý giá để đánh giá "Độ hot" (Demand Weight)
    view_count = scrapy.Field()           
    application_count = scrapy.Field()    

    # --- NHÓM 5: EXTRA (CHỨA TẤT CẢ NHỮNG THỨ CÒN LẠI) ---
    # Các field không đồng nhất giữa các web (job_level, employment_type...)
    # Hãy nhét hết vào đây dưới dạng Dict
    extra_data = scrapy.Field()

SpidersItem = JobItem