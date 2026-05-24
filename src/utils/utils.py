import unicodedata
import re
from typing import Optional

def join_text(text_list):
            if not text_list: return None
            lines = [t.strip() for t in text_list if t.strip()]
            return '\n'.join(lines) if lines else None
        

def slugify(text: str) -> str:
    """Convert text thành slug: 'Data Engineer' -> 'data-engineer'"""
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s-]", " ", text)
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    
    return text.lower()
    
    
# remove extra spaces and new lines from element   
def extract_text(el) -> Optional[str]:
        """Extract và clean text từ element"""
        if not el:
            return None
        t = el.get_text(" ", strip=True)
        return re.sub(r"\s+", " ", t) if t else None


def clean_company_intro(text: str) -> str:
    """
    Loại bỏ các phần giới thiệu công ty (Who We Are, About Us, Giới thiệu công ty...)
    khỏi văn bản JD trước khi đưa vào bộ trích xuất để tránh trích xuất thừa skill.
    """
    if not text:
        return ""
        
    lines = text.split('\n')
    cleaned_lines = []
    
    start_patterns = [
        r'^\s*(?:who\s+we\s+are|about\s+us|about\s+[a-z0-9_#-]+|về\s+chúng\s+tôi|giới\s+thiệu\s+công\s+ty|giới\s+thiệu\s+về\s+công\s+ty|về\s+công\s+ty|our\s+story|company\s+profile|company\s+overview)\b'
    ]
    
    end_patterns = [
        r'\b(?:job\s+description|mô\s+tả\s+công\s+việc|nhiệm\s+vụ|your\s+role|responsibilities|key\s+responsibilities|your\s+responsibilities|job\s+responsibilities|what\s+you\s+will\s+do|what\s+you\'ll\s+do|what\s+we\s+expect|requirements|yêu\s+cầu|yêu\s+cầu\s+công\s+việc|your\s+skills|what\s+you\s+need|skills\s+and\s+experience|your\s+skills\s+and\s+experience|we\s+are\s+looking\s+for|technologies\s+we\s+use|tech\s+stack|vị\s+trí|chi\s+tiết\s+công\s+việc|who\s+you\s+are|about\s+you|your\s+profile|why\s+you\'ll\s+love\s+working\s+here|quyền\s+lợi|benefits)\b'
    ]
    
    in_intro = False
    
    for line in lines:
        line_stripped = line.strip().lower()
        if not line_stripped:
            cleaned_lines.append(line)
            continue
            
        # Kiểm tra xem có bắt đầu phần giới thiệu không
        is_start = any(re.search(p, line_stripped) for p in start_patterns)
        if is_start:
            in_intro = True
            continue
            
        # Kiểm tra xem có kết thúc phần giới thiệu và quay lại JD không
        is_end = any(re.search(p, line_stripped) for p in end_patterns)
        if is_end:
            in_intro = False
            
        if not in_intro:
            cleaned_lines.append(line)
            
    return '\n'.join(cleaned_lines)

