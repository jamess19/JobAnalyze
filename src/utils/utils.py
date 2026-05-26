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

    Safeguard: nếu sau khi clean mà text < 20% text gốc → giữ nguyên text gốc
    để tránh over-stripping (ví dụ: LinkedIn text không có \\n).
    """
    if not text:
        return ""

    original_len = len(text.strip())
    if original_len == 0:
        return ""

    lines = text.split('\n')
    cleaned_lines = []

    # Patterns đánh dấu BẮT ĐẦU phần giới thiệu công ty.
    # "about" phải đi kèm tên công ty/cụm giới thiệu, KHÔNG match "about the role",
    # "about you", "about this position" (đây là JD content).
    start_patterns = [
        r'^\s*(?:who\s+we\s+are|where\s+we\s+are|about\s+us|về\s+chúng\s+tôi|giới\s+thiệu\s+công\s+ty|giới\s+thiệu\s+về\s+công\s+ty|về\s+công\s+ty|our\s+story|company\s+profile|company\s+overview)\s*:?\s*$',
        r'^\s*about\s+(?!the\s+role|the\s+job|the\s+position|the\s+team|you|this\s+role|this\s+position|this\s+job)[a-z0-9][a-z0-9\s_#-]*\s*:?\s*$',
    ]

    # Patterns đánh dấu KẾT THÚC phần giới thiệu (= bắt đầu lại phần JD).
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

    result = '\n'.join(cleaned_lines)

    # Safeguard: nếu clean quá nhiều (< 20% text gốc) → giữ nguyên text gốc.
    # Điều này bảo vệ khỏi trường hợp text không có \\n hoặc patterns match sai.
    result_len = len(result.strip())
    if result_len < original_len * 0.2:
        return text

    return result

