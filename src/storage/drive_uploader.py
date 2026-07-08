import config.config as conf
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from .base_uploader import BaseUploader

class GoogleDriveUploader(BaseUploader):
    """Lớp để upload file lên Google Drive sử dụng oauth2 client"""

    def __init__(self):
        self.client_secret_file = conf.CLIENT_SECRET_FILE
        self.scopes = conf.SCOPES
        self.token_file = conf.TOKEN_FILE_PATH
        self.folder_id = conf.FOLDER_ID
        self.redirect_uri = conf.REDIRECT_URI
        self.port = conf.PORT
        self.service = self.authenticate_drive()
    
    def authenticate_drive(self):
            """Xác thực với Google Drive sử dụng Web App Flow (OAuth 2.0)."""
            creds = None
            
            # 1. Tải token đã lưu (nếu có)
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
            
            # 2. Nếu token không hợp lệ hoặc không tồn tại, tiến hành xác thực mới
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secret_file, self.scopes)
                    creds = flow.run_local_server(port=self.port)    
                
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                
            return build("drive", "v3", credentials=creds)

    def upload(self, file_path):
        """
        Upload một file (Excel/CSV) lên Google Drive.
        :param file_path: Đường dẫn đến file cục bộ (e.g., 'data.xlsx' hoặc 'data.csv').
        """
        # Định nghĩa metadata cho file
        file_metadata = {
            'name': os.path.basename(file_path),
            'mimeType': 'text/csv', # MIME type cho file CSV
            'parents': [self.folder_id]
        }
        
        file_path = os.path.abspath(file_path)
        # Định nghĩa MediaUpload object
        media = MediaFileUpload(file_path, mimetype='text/csv', resumable=True)
        
        # Thực hiện lời gọi API để tạo (upload) file
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, parents' # Thêm 'parents' để kiểm tra kết quả
            ).execute()
            print(f"File '{file.get('name')}' đã được tải lên thành công. ID: {file.get('id')}, Parents: {file.get('parents')}")
        except Exception as e:
            print(f"Lỗi khi tải file: {e}")
