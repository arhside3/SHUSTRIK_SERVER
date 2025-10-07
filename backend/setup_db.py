import logging
import sqlite3
import re
import os
from datetime import datetime
import time
from backend.initial_media import IMAGE_DIR

class CardDatabase:
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_database()
        
    def init_database(self):
        """Инициализация базы данных SQLite"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_type TEXT NOT NULL,
            uid TEXT NOT NULL,
            date_added TEXT,
            UNIQUE(card_type, uid)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_type TEXT NOT NULL,
            uid TEXT NOT NULL,
            image_filename TEXT NOT NULL,
            date_uploaded TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (card_type, uid) REFERENCES cards (card_type, uid),
            UNIQUE(card_type, uid)
        )
        ''')
        
        conn.commit()
        conn.close()
        logging.info(f"База данных SQLite инициализирована: {self.db_file}")
        
        os.makedirs(IMAGE_DIR, exist_ok=True)
    
    def check_card(self, card_type, uid):
        """Проверяет наличие карты в базе данных"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        uid_str = self._normalize_uid_for_search(uid)
        
        cursor.execute("SELECT COUNT(*) FROM cards WHERE card_type = ? AND uid = ?", 
                     (card_type, uid_str))
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
    
    def add_card(self, card_type, uid):
        """Добавляет карту в базу данных"""
        try:
            uid_str = self._normalize_uid_for_storage(uid)
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM cards WHERE card_type = ? AND uid = ?", 
                        (card_type, uid_str))
            if cursor.fetchone()[0] > 0:
                logging.warning(f"Карта {card_type} с UID {uid_str} уже существует в БД")
                conn.close()
                return False
            
            date_added = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO cards (card_type, uid, date_added) VALUES (?, ?, ?)", 
                        (card_type, uid_str, date_added))
            conn.commit()
            conn.close()
            
            logging.info(f"Карта {card_type} с UID {uid_str} добавлена в БД")
            return True
        except Exception as e:
            logging.error(f"Ошибка при добавлении карты: {e}")
            return False
    
    def remove_card(self, card_type, uid):
        """Удаляет карту из базы данных"""
        try:
            uid_str = self._normalize_uid_for_search(uid)
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM media WHERE card_type = ? AND uid = ?", 
                        (card_type, uid_str))
            
            cursor.execute("DELETE FROM cards WHERE card_type = ? AND uid = ?", 
                        (card_type, uid_str))
            deleted = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            if deleted:
                logging.info(f"Карта {card_type} с UID {uid_str} удалена из БД")
            else:
                logging.warning(f"Карта {card_type} с UID {uid_str} не найдена в БД")
                
            return deleted
        except Exception as e:
            logging.error(f"Ошибка при удалении карты: {e}")
            return False
    
    def list_cards(self):
        """Возвращает список всех карт с информацией об изображениях"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT c.card_type, c.uid, c.date_added, ci.image_filename 
                FROM cards c 
                LEFT JOIN media ci ON c.card_type = ci.card_type AND c.uid = ci.uid 
                ORDER BY c.date_added DESC
            ''')
            rows = cursor.fetchall()
            
            cards = []
            for row in rows:
                card_type, uid_str, date_added, image_filename = row
                cards.append({
                    "card_type": card_type,
                    "uid": uid_str,
                    "date_added": date_added,
                    "image_filename": image_filename,
                    "has_image": image_filename is not None
                })
            
            conn.close()
            return cards
        except Exception as e:
            logging.error(f"Ошибка при получении списка карт: {e}")
            return []
    
    def save_card_image(self, card_type, uid, image_data, filename):
        """Сохраняет изображение для карты"""
        try:
            uid_str = self._normalize_uid_for_search(uid)
            
            if not self.check_card(card_type, uid):
                return False, "Карта не существует"
            
            file_ext = os.path.splitext(filename)[1]
            safe_filename = f"{card_type}_{uid_str}_{int(time.time())}{file_ext}"
            image_path = os.path.join(IMAGE_DIR, safe_filename)
            
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM media WHERE card_type = ? AND uid = ?", 
                          (card_type, uid_str))
            
            date_uploaded = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO media (card_type, uid, image_filename, date_uploaded) VALUES (?, ?, ?, ?)", 
                          (card_type, uid_str, safe_filename, date_uploaded))
            
            conn.commit()
            conn.close()
            
            logging.info(f"Изображение сохранено для карты {card_type} с UID {uid_str}")
            return True, "Изображение успешно сохранено"
            
        except Exception as e:
            logging.error(f"Ошибка при сохранении изображения карты: {e}")
            return False, f"Ошибка: {str(e)}"
    
    def get_card_image_info(self, card_type, uid):
        """Получает информацию об изображении карты"""
        try:
            uid_str = self._normalize_uid_for_search(uid)
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ci.image_filename, ci.date_uploaded, c.date_added 
                FROM media ci 
                JOIN cards c ON ci.card_type = c.card_type AND ci.uid = c.uid 
                WHERE ci.card_type = ? AND ci.uid = ?
            ''', (card_type, uid_str))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                image_filename, date_uploaded, date_added = result
                return {
                    "image_filename": image_filename,
                    "date_uploaded": date_uploaded,
                    "date_added": date_added,
                    "has_image": True
                }
            return None
            
        except Exception as e:
            logging.error(f"Ошибка при получении информации об изображении карты: {e}")
            return None
    
    def get_card_with_image(self, card_type, uid):
        """Получает полные данные карты с информацией об изображении"""
        try:
            uid_str = self._normalize_uid_for_search(uid)
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT c.card_type, c.uid, c.date_added, ci.image_filename, ci.date_uploaded
                FROM cards c 
                LEFT JOIN media ci ON c.card_type = ci.card_type AND c.uid = ci.uid
                WHERE c.card_type = ? AND c.uid = ?
            ''', (card_type, uid_str))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                card_type, uid_str, date_added, image_filename, date_uploaded = result
                return {
                    "card_type": card_type,
                    "uid": uid_str,
                    "date_added": date_added,
                    "image_filename": image_filename,
                    "date_uploaded": date_uploaded,
                    "has_image": image_filename is not None
                }
            return None
            
        except Exception as e:
            logging.error(f"Ошибка при получении карты с изображением: {e}")
            return None
    
    def _normalize_uid_for_storage(self, uid):
        """Нормализует UID для сохранения в базу данных"""
        if isinstance(uid, list):
            hex_parts = [f"{part:02X}" for part in uid]
            return ''.join(hex_parts)
        elif isinstance(uid, str):
            cleaned = re.sub(r'[^0-9A-Fa-f]', '', uid).upper()
            if re.match(r'^[0-9A-F]+$', cleaned):
                return cleaned
            numbers = re.findall(r'\d+', uid)
            if numbers:
                hex_parts = [f"{int(num):02X}" for num in numbers]
                return ''.join(hex_parts)
        return str(uid).upper()
    
    def _normalize_uid_for_search(self, uid):
        """Нормализует UID для поиска в базе данных"""
        if isinstance(uid, list):
            hex_parts = [f"{part:02X}" for part in uid]
            return ''.join(hex_parts)
        elif isinstance(uid, str):
            cleaned = re.sub(r'[^0-9A-Fa-f]', '', uid).upper()
            return cleaned
        return str(uid).upper()
    
    def _extract_uid_numbers(self, uid):
        """Извлекает числа из UID в различных форматах (для обратной совместимости)"""
        if isinstance(uid, list):
            return uid
        elif isinstance(uid, str):
            try:
                if re.match(r'^[0-9A-Fa-f]+$', uid):
                    numbers = []
                    for i in range(0, len(uid), 2):
                        hex_byte = uid[i:i+2]
                        numbers.append(int(hex_byte, 16))
                    return numbers
                numbers = re.findall(r'\d+', uid)
                if numbers:
                    return [int(num) for num in numbers]
            except ValueError as e:
                logging.error(f"Ошибка при извлечении чисел из UID: {e}")
        return None