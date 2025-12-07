import unicodedata
import re
from typing import Optional

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
