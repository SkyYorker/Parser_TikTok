"""
Модуль экспорта данных в CSV и Google Sheets
"""

import os
import csv
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    print("Предупреждение: gspread не установлен. Экспорт в Google Sheets недоступен.")


class DataExporter:
    """Класс для экспорта данных в различные форматы"""
    
    def __init__(self):
        self.csv_filename = f"tiktok_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.google_sheets_available = False
        
        if GSPREAD_AVAILABLE:
            self._init_google_sheets()
    
    def _init_google_sheets(self):
        """Инициализация Google Sheets API"""
        credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        
        if credentials_path and spreadsheet_id:
            try:
                if os.path.exists(credentials_path):
                    scope = [
                        "https://spreadsheets.google.com/feeds",
                        "https://www.googleapis.com/auth/drive"
                    ]
                    creds = Credentials.from_service_account_file(
                        credentials_path,
                        scopes=scope
                    )
                    self.client = gspread.authorize(creds)
                    self.spreadsheet = self.client.open_by_key(spreadsheet_id)
                    self.google_sheets_available = True
                    print("Google Sheets API инициализирован успешно")
                else:
                    print(f"Файл credentials не найден: {credentials_path}")
            except Exception as e:
                print(f"Ошибка инициализации Google Sheets: {e}")
        else:
            print("Google Sheets credentials не настроены. Экспорт в CSV будет выполнен.")
    
    def export_to_csv(self, data: List[Dict]) -> str:
        """Экспорт данных в CSV файл"""
        if not data:
            print("Нет данных для экспорта")
            return None
        
        # Подготовка данных для экспорта
        export_data = []
        for video in data:
            export_data.append({
                "Ссылка на ролик": video.get("url", ""),
                "Описание": video.get("description", ""),
                "Просмотры": video.get("views", 0),
                "Лайки": video.get("likes", 0),
                "Дата публикации": video.get("date", "").strftime("%Y-%m-%d %H:%M:%S") if isinstance(video.get("date"), datetime) else str(video.get("date", "")),
                "Хештеги": video.get("hashtags", "")
            })
        
        # Экспорт в CSV через стандартную библиотеку csv
        with open(self.csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            if export_data:
                fieldnames = export_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(export_data)
        
        print(f"Данные экспортированы в CSV: {self.csv_filename}")
        return self.csv_filename
    
    def export_to_google_sheets(self, data: List[Dict], worksheet_name: str = None) -> bool:
        """Экспорт данных в Google Sheets"""
        if not self.google_sheets_available:
            print("Google Sheets недоступен. Проверьте настройки в .env файле.")
            return False
        
        if not data:
            print("Нет данных для экспорта")
            return False
        
        try:
            # Получение или создание листа
            if worksheet_name:
                try:
                    worksheet = self.spreadsheet.worksheet(worksheet_name)
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = self.spreadsheet.add_worksheet(
                        title=worksheet_name,
                        rows=len(data) + 1,
                        cols=6
                    )
            else:
                worksheet_name = os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Тушь TikTok")
                try:
                    worksheet = self.spreadsheet.worksheet(worksheet_name)
                except gspread.exceptions.WorksheetNotFound:
                    worksheet = self.spreadsheet.add_worksheet(
                        title=worksheet_name,
                        rows=len(data) + 1,
                        cols=6
                    )
            
            # Подготовка данных
            headers = ["Ссылка на ролик", "Описание", "Просмотры", "Лайки", "Дата публикации", "Хештеги"]
            rows = [headers]
            
            for video in data:
                date_str = video.get("date", "").strftime("%Y-%m-%d %H:%M:%S") if isinstance(video.get("date"), datetime) else str(video.get("date", ""))
                rows.append([
                    video.get("url", ""),
                    video.get("description", ""),
                    video.get("views", 0),
                    video.get("likes", 0),
                    date_str,
                    video.get("hashtags", "")
                ])
            
            # Очистка листа и запись данных
            worksheet.clear()
            worksheet.update("A1", rows)
            
            # Форматирование заголовков
            worksheet.format("A1:F1", {
                "textFormat": {"bold": True},
                "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
            })
            
            print(f"Данные экспортированы в Google Sheets: {worksheet_name}")
            return True
            
        except Exception as e:
            print(f"Ошибка экспорта в Google Sheets: {e}")
            return False
    
    def export(self, data: List[Dict], worksheet_name: str = None):
        """Экспорт данных во все доступные форматы"""
        # CSV всегда доступен
        csv_file = self.export_to_csv(data)
        
        # Google Sheets (если настроен)
        if self.google_sheets_available:
            self.export_to_google_sheets(data, worksheet_name)
        
        return csv_file

