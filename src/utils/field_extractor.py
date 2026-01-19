"""
Field Extractor - Helper functions to extract and parse fields from scraped data
"""

import re
from typing import Optional, Dict, Tuple, List
from datetime import datetime
import unicodedata


class FieldExtractor:
    """Helper class for extracting and parsing fields from web scraping responses"""
    
    @staticmethod
    def extract_text(element) -> Optional[str]:
        """
        Extract clean text from a BeautifulSoup/Scrapy element
        
        :param element: BeautifulSoup tag or Scrapy selector
        :return: Cleaned text or None
        """
        if element is None:
            return None
        
        # Handle Scrapy selector
        if hasattr(element, 'get'):
            text = element.get()
        # Handle BeautifulSoup tag
        elif hasattr(element, 'get_text'):
            text = element.get_text(strip=True)
        # Handle string
        else:
            text = str(element)
        
        if not text:
            return None
        
        # Clean text
        text = unicodedata.normalize('NFKC', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text if text else None
    
    @staticmethod
    def parse_salary(salary_text: str) -> Dict[str, Optional[float]]:
        """
        Parse salary text to extract min, max, currency
        
        Examples:
        - "15 - 20 triệu VNĐ" -> min:15, max:20, currency:VND, unit:million
        - "$1000-2000" -> min:1000, max:2000, currency:USD
        - "Thỏa thuận" -> min:None, max:None, negotiable:True
        - "Up to $3000" -> min:None, max:3000, currency:USD
        
        :param salary_text: Raw salary text
        :return: Dict with min, max, currency, unit, negotiable
        """
        result = {
            'min': None,
            'max': None,
            'currency': None,
            'unit': None,
            'negotiable': False,
            'raw': salary_text
        }
        
        if not salary_text:
            return result
        
        text = str(salary_text).lower()
        
        # Check if negotiable
        if any(word in text for word in ['thỏa thuận', '协商', 'negotiable', 'competitive', 'login to view']):
            result['negotiable'] = True
            return result
        
        # Extract currency
        if 'usd' in text or '$' in text:
            result['currency'] = 'USD'
        elif 'vnd' in text or 'vnđ' in text or 'đ' in text or 'triệu' in text or 'tr' in text:
            result['currency'] = 'VND'
        elif 'eur' in text or '€' in text:
            result['currency'] = 'EUR'
        
        # Extract unit
        if 'triệu' in text or 'tr' in text.split():
            result['unit'] = 'million'
        elif 'nghìn' in text or 'ngàn' in text or 'k' in text:
            result['unit'] = 'thousand'
        elif 'tỷ' in text:
            result['unit'] = 'billion'
        
        # Extract numbers
        # Match patterns like: 15-20, 15 - 20, 15~20, 15 to 20
        numbers = re.findall(r'(\d+(?:[.,]\d+)?)', text)
        
        if numbers:
            nums = [float(n.replace(',', '.')) for n in numbers]
            
            # Check for range patterns
            if len(nums) >= 2:
                result['min'] = nums[0]
                result['max'] = nums[1]
            elif len(nums) == 1:
                # Check context for "up to", "đến", "tối đa"
                if any(word in text for word in ['up to', 'đến', 'tối đa', 'max']):
                    result['max'] = nums[0]
                # Check for "from", "từ", "tối thiểu"
                elif any(word in text for word in ['from', 'từ', 'tối thiểu', 'min']):
                    result['min'] = nums[0]
                else:
                    # Single value - treat as both min and max
                    result['min'] = nums[0]
                    result['max'] = nums[0]
        
        # Convert to standard unit (VND in millions, USD/EUR as is)
        if result['currency'] == 'VND':
            if result['unit'] == 'thousand':
                # Convert thousand to million
                if result['min']:
                    result['min'] = result['min'] / 1000
                if result['max']:
                    result['max'] = result['max'] / 1000
            elif result['unit'] == 'billion':
                # Convert billion to million
                if result['min']:
                    result['min'] = result['min'] * 1000
                if result['max']:
                    result['max'] = result['max'] * 1000
            # If already in million or no unit specified, keep as is
        
        return result
    
    @staticmethod
    def parse_experience(exp_text: str) -> Dict[str, Optional[any]]:
        """
        Parse experience text to extract years and level
        
        Examples:
        - "2-3 năm" -> min:2, max:3
        - "Trên 5 năm" -> min:5, max:None
        - "Không yêu cầu" -> min:0, max:0
        - "Fresher" -> min:0, max:1
        
        :param exp_text: Raw experience text
        :return: Dict with min_years, max_years, raw
        """
        result = {
            'min_years': None,
            'max_years': None,
            'raw': exp_text
        }
        
        if not exp_text:
            return result
        
        text = str(exp_text).lower()
        
        # No experience required
        if any(word in text for word in ['không yêu cầu', 'không cần', 'fresher', 'intern', 'no experience']):
            result['min_years'] = 0
            result['max_years'] = 0
            return result
        
        # Extract numbers
        numbers = re.findall(r'(\d+)', text)
        
        if numbers:
            nums = [int(n) for n in numbers]
            
            if len(nums) >= 2:
                result['min_years'] = nums[0]
                result['max_years'] = nums[1]
            elif len(nums) == 1:
                # Check context
                if any(word in text for word in ['trên', 'over', 'above', 'more than', '+']):
                    result['min_years'] = nums[0]
                    result['max_years'] = None
                elif any(word in text for word in ['dưới', 'under', 'below', 'less than']):
                    result['min_years'] = 0
                    result['max_years'] = nums[0]
                else:
                    # Single value
                    result['min_years'] = nums[0]
                    result['max_years'] = nums[0]
        
        return result
    
    @staticmethod
    def parse_location(location_text: str) -> Dict[str, Optional[str]]:
        """
        Parse location to extract city, district, and full address
        
        :param location_text: Raw location text
        :return: Dict with city, district, address
        """
        result = {
            'city': None,
            'district': None,
            'address': location_text,
            'country': 'Vietnam'
        }
        
        if not location_text:
            return result
        
        text = str(location_text)
        text_lower = text.lower()
        
        # Extract city
        city_mappings = {
            'hồ chí minh': 'Ho Chi Minh City',
            'hcm': 'Ho Chi Minh City',
            'sài gòn': 'Ho Chi Minh City',
            'saigon': 'Ho Chi Minh City',
            'hà nội': 'Hanoi',
            'hanoi': 'Hanoi',
            'đà nẵng': 'Da Nang',
            'da nang': 'Da Nang',
            'cần thơ': 'Can Tho',
            'can tho': 'Can Tho',
            'hải phòng': 'Hai Phong',
            'hai phong': 'Hai Phong',
            'biên hòa': 'Bien Hoa',
            'bien hoa': 'Bien Hoa',
            'nha trang': 'Nha Trang',
            'huế': 'Hue',
            'hue': 'Hue',
        }
        
        for key, city in city_mappings.items():
            if key in text_lower:
                result['city'] = city
                break
        
        # Extract district
        district_match = re.search(r'(quận|district|q\.|q)\s*(\d+|[a-z]+)', text_lower)
        if district_match:
            result['district'] = district_match.group(0).strip()
        
        return result
    
    @staticmethod
    def extract_skills(text: str, skill_keywords: List[str] = None) -> List[str]:
        """
        Extract skills from text
        
        :param text: Text to extract skills from
        :param skill_keywords: List of known skill keywords to look for
        :return: List of skills found
        """
        if not text:
            return []
        
        skills = []
        text_lower = text.lower()
        
        # Default skill keywords if not provided
        if skill_keywords is None:
            skill_keywords = [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust', 'ruby', 'php',
                'react', 'angular', 'vue', 'nodejs', 'django', 'flask', 'spring', 'express',
                'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git',
                'machine learning', 'deep learning', 'ai', 'data science', 'nlp',
                'html', 'css', 'sass', 'less', 'webpack', 'babel',
                'rest', 'graphql', 'api', 'microservices',
                'agile', 'scrum', 'jira', 'confluence'
            ]
        
        for skill in skill_keywords:
            if skill.lower() in text_lower:
                skills.append(skill.title())
        
        return list(set(skills))  # Remove duplicates
    
    @staticmethod
    def parse_company_size(size_text: str) -> Dict[str, Optional[any]]:
        """
        Parse company size to extract employee count range
        
        :param size_text: Raw company size text
        :return: Dict with min, max, category
        """
        result = {
            'min': None,
            'max': None,
            'category': None,
            'raw': size_text
        }
        
        if not size_text:
            return result
        
        text = str(size_text).lower()
        
        # Extract numbers
        numbers = re.findall(r'(\d+)', text)
        
        if numbers:
            nums = [int(n) for n in numbers]
            
            if len(nums) >= 2:
                result['min'] = nums[0]
                result['max'] = nums[1]
            elif len(nums) == 1:
                # Check context
                if any(word in text for word in ['trên', 'over', 'above', '+', 'more than']):
                    result['min'] = nums[0]
                elif any(word in text for word in ['dưới', 'under', 'below', 'less than']):
                    result['max'] = nums[0]
                else:
                    # Single value - use as approximate
                    result['min'] = nums[0]
                    result['max'] = nums[0]
        
        # Determine category based on size
        size = result['max'] if result['max'] else result['min']
        
        if size:
            if size < 50:
                result['category'] = '1-50'
            elif size < 200:
                result['category'] = '51-200'
            elif size < 500:
                result['category'] = '201-500'
            elif size < 1000:
                result['category'] = '501-1000'
            else:
                result['category'] = '1000+'
        
        return result
    
    @staticmethod
    def parse_date(date_text: str) -> Optional[str]:
        """
        Parse various date formats to standard format (YYYY-MM-DD)
        
        :param date_text: Raw date text
        :return: Standardized date string or None
        """
        if not date_text:
            return None
        
        text = str(date_text).strip()
        
        # Common date formats
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2024-01-15
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # 15/01/2024
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # 15-01-2024
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups[0]) == 4:  # Year first
                        year, month, day = groups
                    else:  # Day first
                        day, month, year = groups
                    
                    # Create date object to validate
                    date_obj = datetime(int(year), int(month), int(day))
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def clean_html(text: str) -> str:
        """
        Remove HTML tags and clean text
        
        :param text: Text with potential HTML
        :return: Clean text
        """
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        """Extract email address from text"""
        if not text:
            return None
        
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(pattern, text)
        
        return match.group(0) if match else None
    
    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        """Extract phone number from text"""
        if not text:
            return None
        
        # Vietnamese phone patterns
        patterns = [
            r'\b0\d{9,10}\b',  # 0123456789
            r'\+84\s?\d{9,10}\b',  # +84 123456789
            r'\(0\d{2,3}\)\s?\d{7,8}\b',  # (012) 3456789
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None

