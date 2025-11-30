# Data Collection - Job Scraper

Dự án thu thập dữ liệu việc làm từ các trang web tuyển dụng (ITViec, LinkedIn) và tự động upload lên Google Drive.

## 📋 Mô tả

Dự án này cung cấp một pipeline tự động để:

- Crawl dữ liệu việc làm từ ITViec và LinkedIn
- Lưu dữ liệu dưới nhiều định dạng (CSV, JSON, Excel)
- Tự động upload file lên Google Drive

## ✨ Tính năng

- **Crawler đa nguồn**: Hỗ trợ crawl từ ITViec và LinkedIn
- **Xuất đa định dạng**: Lưu dữ liệu dưới dạng CSV, JSON, Excel
- **Tự động upload**: Tích hợp Google Drive API để upload file tự động
- **Cấu hình linh hoạt**: Dễ dàng cấu hình keywords, location, và các tham số khác
- **Xử lý lỗi**: Có cơ chế xử lý lỗi và retry logic

## 🚀 Cài đặt

### Yêu cầu hệ thống

- Python 3.8 trở lên
- Google Chrome/Chromium (cho Selenium)

### Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Cấu hình Google Drive API

1. Tạo một project trên [Google Cloud Console](https://console.cloud.google.com/)
2. Bật Google Drive API
3. Tạo OAuth 2.0 credentials (Desktop app)
4. Tải file `client_secret.json` và đặt vào `src/config/credentials/`
5. Copy file `example.env` thành `.env` và cấu hình:

```bash
cp example.env .env
```

Chỉnh sửa file `.env` với các thông tin của bạn:

```env
SCOPES=https://www.googleapis.com/auth/drive
TOKEN_FILE_PATH=token.json
CLIENT_SECRET_FILE=src/config/credentials/client_secret.json
FOLDER_ID=your_google_drive_folder_id
OUTPUT_FOLDER=src/data
REDIRECT_URI=http://localhost:8000/callback
PORT=8000
```

## 📁 Cấu trúc dự án

```
data-collection/
├── src/
│   ├── main.py                 # Entry point chính
│   ├── config/
│   │   ├── config.py           # Cấu hình chung
│   │   └── credentials/        # Thư mục chứa credentials (không commit)
│   ├── crawler/
│   │   ├── base_crawler.py     # Lớp cơ sở cho crawlers
│   │   ├── itviec_crawler.py   # Crawler cho ITViec
│   │   └── linkedin_crawler.py # Crawler cho LinkedIn
│   ├── storage/
│   │   ├── base_uploader.py    # Lớp cơ sở cho uploaders
│   │   └── drive_uploader.py   # Google Drive uploader
│   ├── data/                   # Thư mục lưu dữ liệu output
│   └── utils/                  # Các utility functions
├── tests/                      # Test files
├── requirements.txt            # Python dependencies
├── example.env                 # Template file cho .env
└── README.md                   # File này
```

## 🔧 Cấu hình

Chỉnh sửa file `src/config/config.py` hoặc tạo file `.env` để cấu hình:

### Cấu hình ITViec

```python
"itviec_keywords": ["software engineer", "data analyst"],
"itviec_location": "ho-chi-minh",
```

### Cấu hình LinkedIn

```python
"linkedin_keywords": ["data analyst"],
"linkedin_location": "Vietnam",
"linkedin_results_wanted": 50,
"linkedin_hours_old": 72,
```

## 💻 Sử dụng

### Chạy pipeline đầy đủ

```bash
python src/main.py
```

Pipeline sẽ:

1. Crawl dữ liệu từ ITViec và LinkedIn
2. Kết hợp và lưu dữ liệu vào file CSV, JSON, Excel
3. Upload file CSV lên Google Drive

### Sử dụng crawler riêng lẻ

#### ITViec Crawler

```python
from src.crawler.itviec_crawler import ITViecCrawler

crawler = ITViecCrawler(
    output_path="src/data",
    keyword="software engineer",
    location="ho-chi-minh"
)
df = crawler.crawl()
```

#### LinkedIn Crawler

```python
from src.crawler.linkedin_crawler import LinkedInCrawler

crawler = LinkedInCrawler(
    output_path="src/data",
    search_term="data analyst",
    location="Vietnam",
    results_wanted=50,
    hours_old=72
)
df = crawler.crawl()
```

### Upload file lên Google Drive

```python
from src.storage.drive_uploader import GoogleDriveUploader

uploader = GoogleDriveUploader()
uploader.upload("path/to/file.csv")
```

## 🧪 Testing

Chạy các test files:

```bash
python tests/test-itviec.py
python tests/test-linkedin.py
```

## 📝 Lưu ý

- **Credentials**: Không commit file `client_secret.json` và `token.json` lên git
- **Rate limiting**: Các website có thể có rate limiting, nên điều chỉnh delay giữa các requests
- **Google Drive**: Lần đầu chạy sẽ yêu cầu xác thực OAuth, token sẽ được lưu tự động
- **Selenium**: LinkedIn crawler sử dụng Selenium, cần Chrome/Chromium browser

## 🤝 Đóng góp

1. Fork dự án
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

## 📄 License

Dự án này được phát triển cho mục đích học tập và nghiên cứu.

## ⚠️ Disclaimer

Dự án này chỉ dùng cho mục đích học tập và nghiên cứu. Vui lòng tuân thủ Terms of Service của các website khi sử dụng crawler.
