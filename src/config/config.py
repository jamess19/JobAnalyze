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
    # Cấu hình ITViec
    "itviec_keywords": ["data analyst",
        "data engineer",
        "data scientist",
        "backend developer",
        "frontend developer",
        "devops engineer",
        "qa engineer",
        "mobile developer",
        "software engineer"],
    "itviec_location": "",
    "itviec_start_page": 1,
    "itviec_end_page": 5,
    # Cấu hình LinkedIn
    "linkedin_keywords": ["data analyst"],
    "linkedin_location": "Vietnam",
    "linkedin_results_wanted": 50,
    "linkedin_hours_old": 72,
    # Cấu hình TopCV
    "topcv_keywords": ["Data Analyst",
        "Data Engineer",
        "Data Scientist",
        "Backend Developer",
        "Frontend Developer",
        "DevOps Engineer",
        "QA Engineer",
        "Mobile Developer",
        "Software Engineer"],
    "topcv_start_page": 1,
    "topcv_end_page": 5,
}