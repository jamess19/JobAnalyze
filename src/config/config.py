import os
from dotenv import load_dotenv

base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
env_path = os.path.join(base_dir, '.env')
load_dotenv(env_path)

token_file = os.getenv("TOKEN_FILE_PATH", "token.json")
TOKEN_FILE_PATH = os.path.abspath(os.path.join(base_dir, token_file)) if not os.path.isabs(token_file) else token_file
client_secret = os.getenv("CLIENT_SECRET_FILE", "src/config/credentials/client_secret.json")
CLIENT_SECRET_FILE = os.path.abspath(os.path.join(base_dir, client_secret)) if not os.path.isabs(client_secret) else client_secret
scopes_str = os.getenv("SCOPES", "https://www.googleapis.com/auth/drive")
SCOPES = [s.strip() for s in scopes_str.split(",")] if "," in scopes_str else [scopes_str.strip()]
FOLDER_ID = os.getenv("FOLDER_ID")
output_folder = os.getenv("OUTPUT_FOLDER", "src/data")
OUTPUT_FOLDER = os.path.abspath(os.path.join(base_dir, output_folder)) if not os.path.isabs(output_folder) else output_folder
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")

PORT = int(os.getenv("PORT", 8000))

# LinkedIn credentials (for authenticated scraping)
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")


DEFAULT_CONFIG = {
    "output_folder": OUTPUT_FOLDER,
    "token_file": TOKEN_FILE_PATH,
    "drive_folder_id": FOLDER_ID,
    # Cấu hình ITViec — crawl category pages thay vì từng keyword slug
    "itviec_urls": [
        "https://itviec.com/it-jobs",
    ],
    # Cấu hình LinkedIn
    "linkedin_keywords": ["Data Analyst",
        "Data Engineer",
        "Data Scientist",
        "Backend Developer",
        "Frontend Developer",
        "DevOps Engineer",
        "QA Engineer",
        "Mobile Developer",
        "Software Engineer",
        "Big Data Engineer",
        "AI Engineer",
        "Business Analyst",
        "Product Manager",],
    "linkedin_location": "Vietnam",
    "linkedin_results_wanted": 50,
    "linkedin_hours_old": 72,
    # Cấu hình TopCV — crawl category pages thay vì từng keyword slug
    "topcv_urls": [
        "https://www.topcv.vn/tim-viec-lam-software-engineering-cr257cb258?sort=new&type_keyword=1&category_family=r257%7Eb258&saturday_status=0&sba=1",
        "https://www.topcv.vn/tim-viec-lam-it-infrastructure-and-operations-cr257cb262?sort=new&type_keyword=1&sba=1&category_family=r257~b262&saturday_status=0",
        "https://www.topcv.vn/tim-viec-lam-product-management-cr257cb268?sort=new&type_keyword=1&sba=1&category_family=r257~b268&saturday_status=0",
        "https://www.topcv.vn/tim-viec-lam-software-testing-cr257cb259?sort=new&type_keyword=1&sba=1&category_family=r257~b259&saturday_status=0",
        "https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-khac-cr257cb270?sort=new&type_keyword=1&sba=1&category_family=r257~b270&saturday_status=0",
        "https://www.topcv.vn/tim-viec-lam-it-project-management-cr257cb265?sort=new&type_keyword=1&sba=1&category_family=r257~b265&saturday_status=0",
        "https://www.topcv.vn/tim-viec-lam-data-science-cr257cb261?sort=new&type_keyword=1&sba=1&category_family=r257~b261&saturday_status=0",
    ],
}