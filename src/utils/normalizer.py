"""
Data Normalizer - Standardize and normalize extracted data
"""

import re
import unicodedata
from typing import Optional, Dict, Any


class DataNormalizer:
    """Helper class for normalizing and standardizing scraped data"""
    
    # Experience level mappings
    EXPERIENCE_LEVELS = {
        'junior': ['junior', 'jr', 'fresher', 'entry', 'graduate', 'intern', '0-2', '0-3'],
        'mid': ['mid', 'middle', 'intermediate', '2-5', '3-5', '3-7'],
        'senior': ['senior', 'sr', 'experienced', '5-8', '5+', '7+'],
        'lead': ['lead', 'team lead', 'tech lead', 'principal', 'staff', '8+', '10+'],
    }
    
    # 63 Provinces of Vietnam: (city_name slug, raw_name Vietnamese, [match aliases after diacritics removed])
    PROVINCES_63 = [
        ("an giang",           "An Giang",            ["an giang"]),
        ("ba ria - vung tau",  "Bà Rịa - Vũng Tàu",   ["ba ria", "vung tau", "ba ria vung tau"]),
        ("bac giang",          "Bắc Giang",            ["bac giang"]),
        ("bac kan",            "Bắc Kạn",              ["bac kan"]),
        ("bac lieu",           "Bạc Liêu",             ["bac lieu"]),
        ("bac ninh",           "Bắc Ninh",             ["bac ninh"]),
        ("ben tre",            "Bến Tre",              ["ben tre"]),
        ("binh dinh",          "Bình Định",            ["binh dinh", "quy nhon", "quy nhơn"]),
        ("binh duong",         "Bình Dương",           ["binh duong", "thu dau mot"]),
        ("binh phuoc",         "Bình Phước",           ["binh phuoc"]),
        ("binh thuan",         "Bình Thuận",           ["binh thuan", "phan thiet"]),
        ("ca mau",             "Cà Mau",               ["ca mau"]),
        ("can tho",            "Cần Thơ",              ["can tho"]),
        ("cao bang",           "Cao Bằng",             ["cao bang"]),
        ("da nang",            "Đà Nẵng",              ["da nang", "danang"]),
        ("dak lak",            "Đắk Lắk",              ["dak lak", "dac lac", "buon ma thuot"]),
        ("dak nong",           "Đắk Nông",             ["dak nong", "dac nong"]),
        ("dien bien",          "Điện Biên",            ["dien bien"]),
        ("dong nai",           "Đồng Nai",             ["dong nai", "bien hoa"]),
        ("dong thap",          "Đồng Tháp",            ["dong thap", "cao lanh"]),
        ("gia lai",            "Gia Lai",              ["gia lai", "pleiku"]),
        ("ha giang",           "Hà Giang",             ["ha giang"]),
        ("ha nam",             "Hà Nam",               ["ha nam"]),
        ("ha noi",             "Hà Nội",               ["ha noi", "hanoi", " hn ", "ha nội"]),
        ("ha tinh",            "Hà Tĩnh",              ["ha tinh"]),
        ("hai duong",          "Hải Dương",            ["hai duong"]),
        ("hai phong",          "Hải Phòng",            ["hai phong"]),
        ("hau giang",          "Hậu Giang",            ["hau giang"]),
        ("hoa binh",           "Hòa Bình",             ["hoa binh"]),
        ("ho chi minh",        "Hồ Chí Minh",          ["ho chi minh", "hcm", "sai gon", "saigon",
                                                        "tp hcm", "tp.hcm", "tphcm", "thanh pho ho chi minh"]),
        ("hung yen",           "Hưng Yên",             ["hung yen"]),
        ("khanh hoa",          "Khánh Hòa",            ["khanh hoa", "nha trang"]),
        ("kien giang",         "Kiên Giang",           ["kien giang", "phu quoc", "rach gia"]),
        ("kon tum",            "Kon Tum",              ["kon tum"]),
        ("lai chau",           "Lai Châu",             ["lai chau"]),
        ("lam dong",           "Lâm Đồng",             ["lam dong", "da lat", "dalat"]),
        ("lang son",           "Lạng Sơn",             ["lang son"]),
        ("lao cai",            "Lào Cai",              ["lao cai", "sapa", "sa pa"]),
        ("long an",            "Long An",              ["long an", "tan an"]),
        ("nam dinh",           "Nam Định",             ["nam dinh"]),
        ("nghe an",            "Nghệ An",              ["nghe an", "vinh city", "thanh pho vinh"]),
        ("ninh binh",          "Ninh Bình",            ["ninh binh"]),
        ("ninh thuan",         "Ninh Thuận",           ["ninh thuan", "phan rang"]),
        ("phu tho",            "Phú Thọ",              ["phu tho", "viet tri"]),
        ("phu yen",            "Phú Yên",              ["phu yen", "tuy hoa"]),
        ("quang binh",         "Quảng Bình",           ["quang binh", "dong hoi"]),
        ("quang nam",          "Quảng Nam",            ["quang nam", "hoi an", "tam ky"]),
        ("quang ngai",         "Quảng Ngãi",           ["quang ngai"]),
        ("quang ninh",         "Quảng Ninh",           ["quang ninh", "ha long", "halong"]),
        ("quang tri",          "Quảng Trị",            ["quang tri", "dong ha"]),
        ("soc trang",          "Sóc Trăng",            ["soc trang"]),
        ("son la",             "Sơn La",               ["son la"]),
        ("tay ninh",           "Tây Ninh",             ["tay ninh"]),
        ("thai binh",          "Thái Bình",            ["thai binh"]),
        ("thai nguyen",        "Thái Nguyên",          ["thai nguyen"]),
        ("thanh hoa",          "Thanh Hóa",            ["thanh hoa"]),
        ("thua thien hue",     "Thừa Thiên Huế",       ["thua thien hue", " hue ", "tp hue", "thanh pho hue"]),
        ("tien giang",         "Tiền Giang",           ["tien giang", "my tho"]),
        ("tra vinh",           "Trà Vinh",             ["tra vinh"]),
        ("tuyen quang",        "Tuyên Quang",          ["tuyen quang"]),
        ("vinh long",          "Vĩnh Long",            ["vinh long"]),
        ("vinh phuc",          "Vĩnh Phúc",            ["vinh phuc", "phuc yen"]),
        ("yen bai",            "Yên Bái",              ["yen bai"]),
    ]
    
    # Job category keywords
    JOB_CATEGORIES = {
        'Software Engineer': [
            'software engineer', 'software developer', 'developer', 'programmer',
            'backend', 'frontend', 'full stack', 'fullstack'
        ],
        'Data Engineer': [
            'data engineer', 'data pipeline', 'etl', 'big data'
        ],
        'Data Scientist': [
            'data scientist', 'machine learning', 'ml engineer', 'ai engineer'
        ],
        'DevOps': [
            'devops', 'sre', 'site reliability', 'infrastructure engineer'
        ],
        'QA/Tester': [
            'qa', 'quality assurance', 'tester', 'test engineer', 'automation test'
        ],
        'Product Manager': [
            'product manager', 'pm', 'product owner', 'po'
        ],
        'Project Manager': [
            'project manager', 'scrum master', 'agile'
        ],
        'Business Analyst': [
            'business analyst', 'ba', 'system analyst'
        ],
        'UI/UX Designer': [
            'ui', 'ux', 'designer', 'graphic designer'
        ],
    }
    
    # Employment type mappings
    EMPLOYMENT_TYPES = {
        'Full-time': ['full-time', 'full time', 'fulltime', 'toàn thời gian'],
        'Part-time': ['part-time', 'part time', 'parttime', 'bán thời gian'],
        'Contract': ['contract', 'contractor', 'hợp đồng'],
        'Internship': ['intern', 'internship', 'thực tập'],
        'Freelance': ['freelance', 'tự do'],
    }
    
    # Company size categories
    COMPANY_SIZE_CATEGORIES = [
        (50, '1-50'),
        (200, '51-200'),
        (500, '201-500'),
        (1000, '501-1000'),
        (float('inf'), '1000+')
    ]
    
    @classmethod
    def normalize_experience_level(cls, experience_text: str, years: Optional[int] = None) -> str:
        """
        Normalize experience to standard levels
        
        :param experience_text: Raw experience text
        :param years: Number of years (if available)
        :return: Normalized level (Junior/Mid/Senior/Lead)
        """
        if not experience_text and years is None:
            return 'Unknown'
        
        # First try to normalize by years if provided
        if years is not None:
            if years <= 2:
                return 'Junior'
            elif years <= 5:
                return 'Mid'
            elif years <= 8:
                return 'Senior'
            else:
                return 'Lead'
        
        # Normalize by text
        text = str(experience_text).lower()
        
        for level, keywords in cls.EXPERIENCE_LEVELS.items():
            for keyword in keywords:
                if keyword in text:
                    return level.title()
        
        # Default fallback
        return 'Mid'
    
    @staticmethod
    def _remove_diacritics(text: str) -> str:
        """Remove Vietnamese diacritics and return lowercased ASCII."""
        nkfd = unicodedata.normalize('NFKD', str(text))
        return ''.join(c for c in nkfd if not unicodedata.combining(c)).lower()

    @classmethod
    def normalize_location_to_province(cls, text: str):
        """
        Map raw location text to one of 63 Vietnamese provinces.

        :return: (city_name_slug, raw_name_vietnamese) or (None, None)
        """
        if not text:
            return None, None
        normalized = cls._remove_diacritics(text)
        # Pad with spaces to avoid partial matches (e.g. 'vinh' in 'vinh long')
        padded = f' {normalized} '
        for city_name, raw_name, aliases in cls.PROVINCES_63:
            for alias in aliases:
                if alias in padded or alias in normalized:
                    return city_name, raw_name
        return None, None

    @classmethod
    def normalize_location(cls, location_text: str) -> str:
        """Legacy helper — returns city_name slug or 'Unknown'."""
        slug, _ = cls.normalize_location_to_province(location_text)
        return slug or 'Unknown'

    @staticmethod
    def parse_salary_topcv(text: str) -> dict:
        """
        Parse salary text from TopCV into structured dict.
        Patterns: 'Thỏa thuận', '26 - 35 triệu', 'Tới 30 triệu',
                  '1,000 - 3,000 USD', 'Tới 4,000 USD'

        :return: dict with keys salary_min, salary_max, salary_currency (all optional)
        """
        if not text:
            return {}
        text = text.strip()
        tl = text.lower()

        negotiable_kws = ['thỏa thuận', 'thoả thuận', 'thoa thuan', 'negotiable', 'competitive']
        if any(k in tl for k in negotiable_kws):
            return {}

        result = {}
        currency = 'USD' if ('usd' in tl or '$' in text) else 'VND'
        result['salary_currency'] = currency

        def clean_num(s):
            return float(s.replace(',', '').replace('.', '').strip())

        if currency == 'VND':
            mult = 1_000_000  # triệu → VND
            range_m = re.search(r'(\d+(?:[,.]\d+)?)\s*[-–]\s*(\d+(?:[,.]\d+)?)\s*tri[eệ]u', text, re.IGNORECASE)
            upto_m  = re.search(r'(?:tới|đến|lên đến|up to)\s*(\d+(?:[,.]\d+)?)\s*tri[eệ]u', text, re.IGNORECASE)
            single_m = re.search(r'(\d+(?:[,.]\d+)?)\s*tri[eệ]u', text, re.IGNORECASE)
            if range_m:
                result['salary_min'] = int(float(range_m.group(1).replace(',', '.')) * mult)
                result['salary_max'] = int(float(range_m.group(2).replace(',', '.')) * mult)
            elif upto_m:
                result['salary_max'] = int(float(upto_m.group(1).replace(',', '.')) * mult)
            elif single_m:
                val = int(float(single_m.group(1).replace(',', '.')) * mult)
                result['salary_min'] = val
                result['salary_max'] = val
        else:  # USD
            range_u  = re.search(r'(\d[\d,]*(?:\.\d+)?)\s*[-–]\s*(\d[\d,]*(?:\.\d+)?)', text)
            upto_u   = re.search(r'(?:tới|đến|lên đến|up to)\s*(\d[\d,]*(?:\.\d+)?)', text, re.IGNORECASE)
            if range_u:
                result['salary_min'] = int(float(range_u.group(1).replace(',', '')))
                result['salary_max'] = int(float(range_u.group(2).replace(',', '')))
            elif upto_u:
                result['salary_max'] = int(float(upto_u.group(1).replace(',', '')))

        # Drop currency key if no amounts found
        if 'salary_min' not in result and 'salary_max' not in result:
            return {}
        return result

    @staticmethod
    def extract_experience_from_tags(tags) -> str | None:
        """
        Extract experience string from TopCV skills_tags list.
        Tags like: '3 năm kinh nghiệm', 'Dưới 1 năm kinh nghiệm', 'Không yêu cầu kinh nghiệm'
        """
        if not tags:
            return None
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]
        for tag in tags:
            tl = tag.lower()
            if 'không yêu cầu kinh nghiệm' in tl:
                return 'Không yêu cầu'
            m = re.search(r'dưới\s*(\d+)\s*năm', tl)
            if m:
                return f'Dưới {m.group(1)} năm'
            m = re.search(r'trên\s*(\d+)\s*năm', tl)
            if m:
                return f'Trên {m.group(1)} năm'
            m = re.search(r'(\d+)\s*năm\s*kinh\s*nghiệm', tl)
            if m:
                return f'{m.group(1)} năm'
        return None

    @staticmethod
    def extract_experience_from_text(text: str) -> str | None:
        """
        Extract experience from free-form requirements text.
        """
        if not text:
            return None
        tl = text.lower()

        no_exp_kws = [
            'không yêu cầu kinh nghiệm', 'no experience required',
            'no experience needed', 'fresh graduate', 'fresher',
            '0 year', '0 năm kinh nghiệm',
        ]
        if any(k in tl for k in no_exp_kws):
            return 'Không yêu cầu'

        patterns = [
            # "X+ years" / "X years+"
            (r'(\d+)\s*\+\s*years?',                                         lambda m: f'{m.group(1)}+ năm'),
            (r'(\d+)\s*years?\s*\+',                                          lambda m: f'{m.group(1)}+ năm'),

            # "X - Y years"
            (r'(\d+)\s*[-–to]\s*(\d+)\s*years?\s*of\s*experience',           lambda m: f'{m.group(1)}-{m.group(2)} năm'),
            (r'(\d+)\s*[-–]\s*(\d+)\s*years?',                               lambda m: f'{m.group(1)}-{m.group(2)} năm'),

            # "at least / minimum / require minimum / a minimum of X years"
            (r'at\s*least\s*(\d+)\s*years?',                                  lambda m: f'{m.group(1)}+ năm'),
            (r'minim(?:um|ally)\s*(?:of\s*)?(\d+)\s*years?',                 lambda m: f'{m.group(1)}+ năm'),
            (r'require[sd]?\s+(?:a\s+)?minim(?:um|ally)\s*(?:of\s*)?(\d+)\s*years?',
                                                                               lambda m: f'{m.group(1)}+ năm'),
            (r'(?:a\s+)?minimum\s+of\s+(\d+)\s*years?',                      lambda m: f'{m.group(1)}+ năm'),

            # "more than / over / above X years"
            (r'(?:more\s+than|over|above|exceeding)\s*(\d+)\s*years?',        lambda m: f'{m.group(1)}+ năm'),

            # "X years of experience" (generic)
            (r'(\d+)\s*years?\s*of\s*(?:relevant\s*|working\s*|practical\s*)?experience',
                                                                               lambda m: f'{m.group(1)} năm'),
            # "experience of X years"
            (r'experience\s*of\s*(?:at\s*least\s*)?(\d+)\s*(?:\+\s*)?years?', lambda m: f'{m.group(1)} năm'),

            # Vietnamese patterns
            (r'(\d+)\s*năm\s*kinh\s*nghi[eệ]m',                              lambda m: f'{m.group(1)} năm'),
            (r'kinh\s*nghi[ệ]m\s*(\d+)\s*năm',                              lambda m: f'{m.group(1)} năm'),
            (r'tối\s*thiểu\s*(\d+)\s*năm',                                    lambda m: f'{m.group(1)}+ năm'),
            (r'ít\s*nhất\s*(\d+)\s*năm',                                      lambda m: f'{m.group(1)}+ năm'),
            (r'trên\s*(\d+)\s*năm',                                            lambda m: f'{m.group(1)}+ năm'),
        ]
        for pattern, formatter in patterns:
            m = re.search(pattern, tl)
            if m:
                return formatter(m)
        return None
    
    @classmethod
    def infer_job_category(cls, title: str, description: str = None) -> Optional[str]:
        """
        Infer job category from title and description
        
        :param title: Job title
        :param description: Job description (optional)
        :return: Job category or None
        """
        if not title:
            return None
        
        text = title.lower()
        if description:
            text += ' ' + description.lower()
        
        for category, keywords in cls.JOB_CATEGORIES.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        
        return None
    
    @classmethod
    def infer_job_level(cls, title: str, experience_level: str = None) -> Optional[str]:
        """
        Infer job level from title
        
        :param title: Job title
        :param experience_level: Experience level (if available)
        :return: Job level (Junior/Mid/Senior/Lead/Principal)
        """
        if not title:
            return experience_level
        
        text = title.lower()
        
        # Check for explicit level in title
        level_keywords = {
            'Junior': ['junior', 'jr', 'fresher', 'entry'],
            'Mid': ['mid', 'middle', 'intermediate'],
            'Senior': ['senior', 'sr', 'expert'],
            'Lead': ['lead', 'team lead', 'tech lead'],
            'Principal': ['principal', 'staff', 'chief', 'head of'],
        }
        
        for level, keywords in level_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return level
        
        # Fallback to experience_level if provided
        if experience_level:
            return experience_level
        
        return None
    
    @classmethod
    def normalize_employment_type(cls, text: str) -> str:
        """
        Normalize employment type
        
        :param text: Raw employment type text
        :return: Normalized employment type
        """
        if not text:
            return 'Full-time'  # Default
        
        text_lower = str(text).lower()
        
        for emp_type, keywords in cls.EMPLOYMENT_TYPES.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return emp_type
        
        return 'Full-time'  # Default
    
    @classmethod
    def normalize_company_size(cls, size_min: Optional[int], size_max: Optional[int]) -> str:
        """
        Normalize company size to standard categories
        
        :param size_min: Minimum employee count
        :param size_max: Maximum employee count
        :return: Size category (e.g., '1-50', '51-200')
        """
        # Use max if available, otherwise min
        size = size_max if size_max else size_min
        
        if not size:
            return 'Unknown'
        
        for threshold, category in cls.COMPANY_SIZE_CATEGORIES:
            if size <= threshold:
                return category
        
        return 'Unknown'
    
    @staticmethod
    def normalize_salary_to_vnd_million(
        amount: float,
        currency: str,
        unit: str = None
    ) -> Optional[float]:
        """
        Normalize salary to VND in millions
        
        :param amount: Salary amount
        :param currency: Currency (VND/USD/EUR)
        :param unit: Unit (million/thousand/billion)
        :return: Normalized amount in VND millions
        """
        if not amount:
            return None
        
        # Conversion rates (approximate)
        conversion_rates = {
            'VND': 1,
            'USD': 24000,  # 1 USD ≈ 24,000 VND
            'EUR': 26000,  # 1 EUR ≈ 26,000 VND
        }
        
        # Convert to VND first
        if currency in conversion_rates:
            vnd_amount = amount * conversion_rates[currency]
        else:
            vnd_amount = amount  # Assume VND
        
        # Convert to millions
        if unit == 'thousand':
            return vnd_amount / 1000
        elif unit == 'billion':
            return vnd_amount * 1000
        elif unit == 'million':
            return vnd_amount
        else:
            # If no unit, assume it's already in correct format
            # If it's USD/EUR without unit, assume the number is in that currency
            if currency in ['USD', 'EUR']:
                return vnd_amount / 1_000_000  # Convert to millions
            else:
                return vnd_amount
    
    @staticmethod
    def calculate_salary_avg(salary_min: Optional[float], salary_max: Optional[float]) -> Optional[float]:
        """
        Calculate average salary from min and max
        
        :param salary_min: Minimum salary
        :param salary_max: Maximum salary
        :return: Average salary
        """
        if salary_min and salary_max:
            return (salary_min + salary_max) / 2
        elif salary_min:
            return salary_min
        elif salary_max:
            return salary_max
        else:
            return None
    
    @staticmethod
    def clean_text(text: str, max_length: Optional[int] = None) -> str:
        """
        Clean and normalize text
        
        :param text: Raw text
        :param max_length: Maximum length (truncate if exceeded)
        :return: Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove special characters but keep Vietnamese
        # text = re.sub(r'[^\w\s\u00C0-\u1EF9,.-]', '', text)
        
        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + '...'
        
        return text
    
    @staticmethod
    def normalize_skills_list(skills_text: str) -> list:
        """
        Normalize skills from various formats to list
        
        :param skills_text: Skills as text (comma/semicolon separated)
        :return: List of normalized skills
        """
        if not skills_text:
            return []
        
        # Split by common separators
        skills = re.split(r'[,;|\n]', str(skills_text))
        
        # Clean and normalize each skill
        normalized = []
        for skill in skills:
            skill = skill.strip()
            if skill:
                # Title case for consistency
                skill = skill.title()
                normalized.append(skill)
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for skill in normalized:
            if skill.lower() not in seen:
                seen.add(skill.lower())
                result.append(skill)
        
        return result
    
    @staticmethod
    def infer_work_mode(description: str, title: str = None) -> str:
        """
        Infer work mode (Remote/Onsite/Hybrid) from description
        
        :param description: Job description
        :param title: Job title (optional)
        :return: Work mode
        """
        if not description:
            return 'Onsite'  # Default
        
        text = description.lower()
        if title:
            text += ' ' + title.lower()
        
        if any(word in text for word in ['remote', 'work from home', 'wfh', 'từ xa', 'làm việc tại nhà']):
            if any(word in text for word in ['hybrid', 'flexible', 'kết hợp']):
                return 'Hybrid'
            return 'Remote'
        elif any(word in text for word in ['hybrid', 'flexible', 'kết hợp']):
            return 'Hybrid'
        else:
            return 'Onsite'
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate if string is a valid URL
        
        :param url: URL to validate
        :return: True if valid
        """
        if not url:
            return False
        
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return bool(url_pattern.match(url))

