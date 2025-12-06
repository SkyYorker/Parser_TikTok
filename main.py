"""
Главный скрипт парсера TikTok
"""

from tiktok_parser import TikTokParser
from exporter import DataExporter
import config


def main():
    """Основная функция"""
    print("=" * 60)
    print("Парсер TikTok - Тушь для ресниц")
    print("=" * 60)
    print(f"Период: последние {config.PARSER_CONFIG['days_back']} дней")
    print(f"Минимум роликов: {config.PARSER_CONFIG['min_videos']}")
    print(f"Ключевые слова: {', '.join(config.KEYWORDS)}")
    print(f"Хештеги: {', '.join(config.HASHTAGS)}")
    print("=" * 60)
    print()
    
    # Инициализация парсера
    parser = TikTokParser()
    
    # Парсинг данных
    videos_data = parser.parse()
    
    if not videos_data:
        print("\n  Не удалось собрать данные.")
        print("Возможные причины:")
        print("  - Проблемы с интернет-соединением")
        print("  - Блокировка со стороны TikTok")
        print("  - Изменение структуры страниц TikTok")
        print("\nПопробуйте:")
        print("  - Запустить парсер снова")
        print("  - Изменить headless=False в config.py")
        print("  - Использовать VPN при блокировке IP")
        return
    
    if len(videos_data) < config.PARSER_CONFIG["min_videos"]:
        print(f"\n  Собрано только {len(videos_data)} роликов из {config.PARSER_CONFIG['min_videos']} требуемых")
        print("Продолжаю экспорт с имеющимися данными...")
    
    print(f"\nСобрано {len(videos_data)} уникальных роликов за последние {config.PARSER_CONFIG['days_back']} дней")
    
    # Экспорт данных
    print("\n" + "=" * 60)
    print("Экспорт данных...")
    print("=" * 60)
    
    exporter = DataExporter()
    csv_file = exporter.export(videos_data)
    
    print("\n" + "=" * 60)
    print("Готово!")
    print("=" * 60)
    if csv_file:
        print(f"CSV файл: {csv_file}")
    if exporter.google_sheets_available:
        print("Google Sheets: данные обновлены")
    print()


if __name__ == "__main__":
    main()

