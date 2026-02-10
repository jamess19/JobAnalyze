import os
import pandas as pd
from datetime import datetime
from storage.drive_uploader import GoogleDriveUploader


class ExportService:
    def __init__(self, output_folder: str, drive_folder_id: str | None = None):
        self.output_folder = output_folder
        self.drive_folder_id = drive_folder_id

    def export_from_db(self, engine, query: str = "SELECT * FROM jobs") -> str | None:
        """Export latest data from DB to files."""
        df = pd.read_sql(query, engine)
        if df.empty:
            return None
        return self._save(df)

    def upload_to_drive(self, file_path: str) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False
        uploader = GoogleDriveUploader()
        uploader.upload(file_path)
        return True

    def _save(self, df: pd.DataFrame) -> str:
        os.makedirs(self.output_folder, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        basename = f"combined_jobs_{ts}"

        csv_path = os.path.join(self.output_folder, f"{basename}.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8")

        excel_path = os.path.join(self.output_folder, f"{basename}.xlsx")
        df.to_excel(excel_path, index=False)

        return csv_path
