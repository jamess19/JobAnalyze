"""
Data Normalizer - Standardize and normalize extracted data
"""

import re
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
    
    # Location mappings
    LOCATION_MAPPINGS = {
        'Ho Chi Minh City': ['hồ chí minh', 'hcm', 'sài gòn', 'saigon', 'tp hcm', 'tp.hcm'],
        'Hanoi': ['hà nội', 'hanoi', 'ha noi', 'hn'],
        'Da Nang': ['đà nẵng', 'da nang', 'danang'],
        'Can Tho': ['cần thơ', 'can tho'],
        'Hai Phong': ['hải phòng', 'hai phong'],
        'Bien Hoa': ['biên hòa', 'bien hoa'],
        'Nha Trang': ['nha trang'],
        'Hue': ['huế', 'hue'],
        'Vung Tau': ['vũng tàu', 'vung tau'],
    }
    
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
    
    @classmethod
    def normalize_location(cls, location_text: str) -> str:
        """
        Normalize location to standard city names
        
        :param location_text: Raw location text
        :return: Normalized city name
        """
        if not location_text:
            return 'Unknown'
        
        text = str(location_text).lower()
        
        for city, variations in cls.LOCATION_MAPPINGS.items():
            for variation in variations:
                if variation in text:
                    return city
        
        # If not found in mappings, return title case
        return location_text.strip().title()
    
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

