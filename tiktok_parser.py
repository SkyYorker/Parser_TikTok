"""
Парсер TikTok для сбора роликов о туши для ресниц
"""

import re
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Set
from playwright.sync_api import sync_playwright, Page, Browser
import config


class TikTokParser:
    """Класс для парсинга роликов TikTok"""
    
    def __init__(self):
        self.config = config.PARSER_CONFIG
        self.base_url = config.TIKTOK_BASE_URL
        self.unique_videos: Set[str] = set()
        self.videos_data: List[Dict] = []
        self.cutoff_date = datetime.now() - timedelta(days=self.config["days_back"])
        
    def _random_delay(self):
        """Случайная задержка между запросами"""
        delay = random.uniform(
            self.config["delay_min"],
            self.config["delay_max"]
        )
        time.sleep(delay)
    
    def _extract_video_id(self, url: str) -> str:
        """Извлечение ID видео из URL"""
        # Формат URL: https://www.tiktok.com/@username/video/1234567890
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        return url
    
    def _parse_date(self, date_str: str) -> datetime:
        """Парсинг даты из строки"""
        try:
            # Различные форматы дат TikTok
            formats = [
                "%Y-%m-%d",
                "%d.%m.%Y",
                "%Y-%m-%d %H:%M:%S",
                "%d %b %Y",
                "%d %B %Y",
            ]
            
            # Попытка распарсить относительные даты
            if "час" in date_str.lower() or "hour" in date_str.lower():
                hours = int(re.search(r'(\d+)', date_str).group(1))
                return datetime.now() - timedelta(hours=hours)
            elif "день" in date_str.lower() or "day" in date_str.lower():
                days = int(re.search(r'(\d+)', date_str).group(1))
                return datetime.now() - timedelta(days=days)
            elif "недел" in date_str.lower() or "week" in date_str.lower():
                weeks = int(re.search(r'(\d+)', date_str).group(1))
                return datetime.now() - timedelta(weeks=weeks)
            elif "месяц" in date_str.lower() or "month" in date_str.lower():
                months = int(re.search(r'(\d+)', date_str).group(1))
                return datetime.now() - timedelta(days=months * 30)
            
            # Парсинг абсолютных дат
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Если не удалось распарсить, возвращаем текущую дату
            return datetime.now()
        except Exception:
            return datetime.now()
    
    def _extract_hashtags(self, description: str) -> List[str]:
        """Извлечение хештегов из описания"""
        hashtags = re.findall(r'#\w+', description)
        return hashtags
    
    def _parse_video_data(self, page: Page, video_url: str) -> Dict:
        """Парсинг данных одного ролика"""
        try:
            page.goto(video_url, wait_until="domcontentloaded", timeout=self.config["timeout"])
            self._random_delay()
            
            # Дополнительное ожидание загрузки контента
            time.sleep(2)
            
            # Извлечение данных
            video_id = self._extract_video_id(video_url)
            
            # Описание - несколько способов поиска
            description = ""
            try:
                # Различные селекторы для описания
                selectors = [
                    '[data-e2e="browse-video-desc"]',
                    'span[data-e2e="video-desc"]',
                    '[data-e2e="video-desc"]',
                    'h1[data-e2e="browse-video-desc"]',
                    '.video-meta-caption',
                    '[class*="video-desc"]',
                    '[class*="caption"]'
                ]
                for selector in selectors:
                    desc_element = page.query_selector(selector)
                    if desc_element:
                        description = desc_element.inner_text()
                        if description:
                            break
            except Exception:
                pass
            
            # Просмотры - улучшенный поиск с несколькими стратегиями
            views = 0
            try:
                # Стратегия 1: Стандартные селекторы TikTok
                selectors = [
                    '[data-e2e="browse-video-views"]',
                    'strong[data-e2e="video-views"]',
                    '[data-e2e="video-views"]',
                    '[data-e2e="video-view-count"]',
                    'span[data-e2e="video-views"]',
                    'div[data-e2e="video-views"]',
                ]
                for selector in selectors:
                    try:
                        views_element = page.query_selector(selector)
                        if views_element:
                            views_text = views_element.inner_text()
                            if views_text and views_text.strip():
                                views = self._parse_number(views_text)
                                if views > 0:
                                    break
                    except Exception:
                        continue
                
                # Стратегия 2: Поиск через JavaScript (внутренние данные TikTok)
                if views == 0:
                    try:
                        # TikTok хранит данные в window объектах
                        views_script = """
                        () => {
                            try {
                                // Поиск в window.__UNIVERSAL_DATA_FOR_REHYDRATION__
                                if (window.__UNIVERSAL_DATA_FOR_REHYDRATION__) {
                                    const data = window.__UNIVERSAL_DATA_FOR_REHYDRATION__;
                                    const jsonStr = JSON.stringify(data);
                                    const match = jsonStr.match(/"playCount":(\\d+)/);
                                    if (match) return match[1];
                                    const match2 = jsonStr.match(/"viewCount":(\\d+)/);
                                    if (match2) return match2[1];
                                }
                                // Альтернативный путь через __INITIAL_STATE__
                                if (window.__INITIAL_STATE__) {
                                    const state = window.__INITIAL_STATE__;
                                    const jsonStr = JSON.stringify(state);
                                    const match = jsonStr.match(/"viewCount":(\\d+)/);
                                    if (match) return match[1];
                                    const match2 = jsonStr.match(/"playCount":(\\d+)/);
                                    if (match2) return match2[1];
                                }
                                // Поиск в __NEXT_DATA__
                                if (window.__NEXT_DATA__) {
                                    const nextData = window.__NEXT_DATA__;
                                    const jsonStr = JSON.stringify(nextData);
                                    const match = jsonStr.match(/"playCount":(\\d+)/);
                                    if (match) return match[1];
                                    const match2 = jsonStr.match(/"viewCount":(\\d+)/);
                                    if (match2) return match2[1];
                                }
                                // Поиск в любых глобальных объектах
                                for (let key in window) {
                                    if (key.includes('DATA') || key.includes('STATE')) {
                                        try {
                                            const obj = window[key];
                                            if (obj && typeof obj === 'object') {
                                                const jsonStr = JSON.stringify(obj);
                                                const match = jsonStr.match(/"playCount":(\\d+)/);
                                                if (match) return match[1];
                                                const match2 = jsonStr.match(/"viewCount":(\\d+)/);
                                                if (match2) return match2[1];
                                            }
                                        } catch(e) {}
                                    }
                                }
                                return null;
                            } catch(e) {
                                return null;
                            }
                        }
                        """
                        js_result = page.evaluate(views_script)
                        if js_result:
                            views = int(js_result)
                    except Exception:
                        pass
                
                # Стратегия 3: Поиск по тексту и структуре страницы
                if views == 0:
                    try:
                        # Поиск всех элементов с числами, которые могут быть просмотрами
                        all_elements = page.query_selector_all('strong, span, div, p')
                        for elem in all_elements:
                            try:
                                text = elem.inner_text().strip()
                                if not text or len(text) > 20:  # Пропускаем длинные тексты
                                    continue
                                
                                # Проверяем, содержит ли текст число и индикаторы просмотров
                                has_number = any(char.isdigit() for char in text)
                                has_view_indicator = any(word in text.lower() for word in [
                                    'view', 'views', 'просмотр', 'просмотров', 'просмотра',
                                    'k', 'м', 'm', 'b', 'тыс', 'млн'
                                ])
                                
                                # Исключаем лайки, комментарии, репосты
                                is_not_other_metric = not any(word in text.lower() for word in [
                                    'like', 'лайк', 'comment', 'коммент', 'share', 'поделиться',
                                    'follow', 'подписк', 'follower', 'подписчик'
                                ])
                                
                                if has_number and has_view_indicator and is_not_other_metric:
                                    parsed_views = self._parse_number(text)
                                    if parsed_views > 0:
                                        views = parsed_views
                                        break
                            except Exception:
                                continue
                    except Exception:
                        pass
                
                # Стратегия 4: Поиск через XPath
                if views == 0:
                    try:
                        xpath_selectors = [
                            "//strong[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view')]",
                            "//span[contains(translate(text(), 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'), 'просмотр')]",
                            "//div[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'view')]",
                        ]
                        for xpath in xpath_selectors:
                            try:
                                elem = page.query_selector(f"xpath={xpath}")
                                if elem:
                                    text = elem.inner_text()
                                    if text:
                                        parsed_views = self._parse_number(text)
                                        if parsed_views > 0:
                                            views = parsed_views
                                            break
                            except Exception:
                                continue
                    except Exception:
                        pass
                
                # Стратегия 5: Поиск в метаданных страницы
                if views == 0:
                    try:
                        # Поиск в meta тегах
                        meta_views = page.query_selector('meta[property="og:video:view_count"]')
                        if not meta_views:
                            meta_views = page.query_selector('meta[name="video:view_count"]')
                        if meta_views:
                            content = meta_views.get_attribute('content')
                            if content:
                                views = int(content)
                    except Exception:
                        pass
                        
            except Exception as e:
                # Тихо игнорируем ошибки, чтобы не прерывать парсинг
                pass
            
            # Лайки - несколько способов поиска
            likes = 0
            try:
                selectors = [
                    '[data-e2e="browse-like-count"]',
                    'strong[data-e2e="like-count"]',
                    '[data-e2e="like-count"]',
                    '[class*="like"]',
                    'strong:has-text("likes")',
                    'strong:has-text("лайк")'
                ]
                for selector in selectors:
                    likes_element = page.query_selector(selector)
                    if likes_element:
                        likes_text = likes_element.inner_text()
                        if likes_text:
                            likes = self._parse_number(likes_text)
                            if likes > 0:
                                break
            except Exception:
                pass
            
            # Дата публикации - несколько способов поиска
            publish_date = datetime.now()
            try:
                selectors = [
                    '[data-e2e="browse-video-publish-time"]',
                    'span[data-e2e="video-publish-time"]',
                    '[data-e2e="video-publish-time"]',
                    '[class*="publish"]',
                    '[class*="date"]',
                    'time'
                ]
                for selector in selectors:
                    date_element = page.query_selector(selector)
                    if date_element:
                        date_str = date_element.inner_text()
                        if date_str:
                            publish_date = self._parse_date(date_str)
                            break
            except Exception:
                pass
            
            # Хештеги
            hashtags = self._extract_hashtags(description)
            
            return {
                "url": video_url,
                "description": description,
                "views": views,
                "likes": likes,
                "date": publish_date,
                "hashtags": ", ".join(hashtags) if hashtags else "",
                "video_id": video_id
            }
        except Exception as e:
            print(f"Ошибка при парсинге {video_url}: {e}")
            return None
    
    def _parse_number(self, text: str) -> int:
        """Парсинг числа из строки (например, '1.2M' -> 1200000)"""
        try:
            text = text.replace(",", "").replace(" ", "").strip()
            if "K" in text.upper() or "к" in text.lower():
                number = float(re.search(r'[\d.]+', text).group(0))
                return int(number * 1000)
            elif "M" in text.upper() or "м" in text.lower():
                number = float(re.search(r'[\d.]+', text).group(0))
                return int(number * 1000000)
            elif "B" in text.upper() or "млрд" in text.lower():
                number = float(re.search(r'[\d.]+', text).group(0))
                return int(number * 1000000000)
            else:
                return int(re.search(r'\d+', text).group(0))
        except Exception:
            return 0
    
    def _search_videos(self, page: Page, query: str) -> List[str]:
        """Поиск роликов по запросу"""
        video_urls = []
        try:
            # Формирование URL поиска
            search_url = f"{self.base_url}/search?q={query.replace(' ', '%20').replace('#', '%23')}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=self.config["timeout"])
            self._random_delay()
            
            # Ожидание загрузки контента
            try:
                page.wait_for_selector('a[href*="/video/"]', timeout=10000)
            except Exception:
                pass
            
            # Прокрутка страницы для загрузки больше контента
            for scroll in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                self._random_delay()
                # Дополнительное ожидание после прокрутки
                time.sleep(1)
            
            # Поиск ссылок на видео - несколько стратегий
            video_links = page.query_selector_all('a[href*="/video/"]')
            
            for link in video_links:
                try:
                    href = link.get_attribute("href")
                    if href and "/video/" in href:
                        # Нормализация URL
                        if href.startswith("//"):
                            full_url = "https:" + href
                        elif href.startswith("/"):
                            full_url = f"{self.base_url}{href}"
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            continue
                        
                        video_id = self._extract_video_id(full_url)
                        if video_id and video_id not in self.unique_videos:
                            video_urls.append(full_url)
                            self.unique_videos.add(video_id)
                except Exception:
                    continue
            
            # Альтернативный способ - поиск через data-e2e атрибуты
            if len(video_urls) < 5:
                try:
                    # Поиск через контейнеры видео
                    video_containers = page.query_selector_all('[data-e2e="search-result-item"]')
                    for container in video_containers:
                        link = container.query_selector('a[href*="/video/"]')
                        if link:
                            href = link.get_attribute("href")
                            if href and "/video/" in href:
                                full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                                video_id = self._extract_video_id(full_url)
                                if video_id and video_id not in self.unique_videos:
                                    video_urls.append(full_url)
                                    self.unique_videos.add(video_id)
                except Exception:
                    pass
            
            # Еще один способ - поиск всех ссылок
            if len(video_urls) < 5:
                all_links = page.query_selector_all('a')
                for link in all_links:
                    try:
                        href = link.get_attribute("href")
                        if href and "/video/" in href and "tiktok.com" in href:
                            full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                            video_id = self._extract_video_id(full_url)
                            if video_id and video_id not in self.unique_videos:
                                video_urls.append(full_url)
                                self.unique_videos.add(video_id)
                    except Exception:
                        continue
            
        except Exception as e:
            print(f"Ошибка при поиске '{query}': {e}")
        
        return video_urls
    
    def parse(self) -> List[Dict]:
        """Основной метод парсинга"""
        print("Запуск парсера TikTok...")
        
        # Сбор всех запросов
        all_queries = config.KEYWORDS + config.HASHTAGS
        
        with sync_playwright() as p:
            # Запуск браузера с настройками для обхода антибота
            # --disable-blink-features=AutomationControlled - скрывает признаки автоматизации
            browser = p.chromium.launch(
                headless=self.config["headless"],
                args=['--disable-blink-features=AutomationControlled']
            )
            # Создание контекста с реалистичными параметрами
            # viewport - размер окна как у обычного пользователя
            # user_agent - имитация реального браузера Chrome
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # Поиск видео по всем запросам
            all_video_urls = []
            for query in all_queries:
                print(f"Поиск по запросу: {query}")
                urls = self._search_videos(page, query)
                all_video_urls.extend(urls)
                print(f"Найдено {len(urls)} новых роликов")
                self._random_delay()
            
            # Удаление дублей
            unique_urls = list(set(all_video_urls))
            print(f"\nВсего найдено уникальных роликов: {len(unique_urls)}")
            
            # Парсинг данных каждого ролика
            print("\nНачинаю парсинг данных роликов...")
            for i, url in enumerate(unique_urls, 1):
                print(f"Парсинг {i}/{len(unique_urls)}: {url}")
                
                for attempt in range(self.config["max_retries"]):
                    try:
                        video_data = self._parse_video_data(page, url)
                        if video_data:
                            # Фильтрация по дате
                            if video_data["date"] >= self.cutoff_date:
                                self.videos_data.append(video_data)
                                views_info = f" ({video_data['views']} просмотров)" if video_data['views'] > 0 else " (просмотры не найдены)"
                                print(f"  ✓ Добавлен: {video_data['description'][:50]}...{views_info}")
                            else:
                                print(f"  ✗ Пропущен (старый): {video_data['date']}")
                            break
                    except Exception as e:
                        if attempt < self.config["max_retries"] - 1:
                            print(f"  Попытка {attempt + 1} не удалась, повтор...")
                            self._random_delay()
                        else:
                            print(f"  ✗ Ошибка после {self.config['max_retries']} попыток")
                
                self._random_delay()
                
                    # Проверка минимального количества
                if len(self.videos_data) >= self.config["min_videos"]:
                    print(f"\nДостигнуто минимальное количество роликов ({self.config['min_videos']})")
                    break
            
            # Если не набрали минимум, продолжаем с оставшимися URL
            if len(self.videos_data) < self.config["min_videos"]:
                print(f"\nПредупреждение: собрано только {len(self.videos_data)} роликов из {self.config['min_videos']} требуемых")
            
            browser.close()
        
        print(f"\nПарсинг завершен. Собрано {len(self.videos_data)} роликов")
        return self.videos_data

