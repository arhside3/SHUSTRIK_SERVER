import time
import sys
import os
from backend.settings import CARD_DB

def console_handler():
    time.sleep(0.5)
    
    print("\n=== Консольное управление базой данных карт ===")
    print("Доступные команды:")
    print("  list                           - показать все карты")
    print("  add <тип> <HEX_UID>            - добавить карту (например: add key 09250C05)")
    print("  del <тип> <HEX_UID>            - удалить карту")
    print("  help                           - показать эту справку")
    print("  exit                           - выйти из программы")
    print("Пример: add key 09250C05")
    print("========================================")
    
    while True:
        try:
            sys.stdout.write("\nВведите команду > ")
            sys.stdout.flush()
            
            command = input().strip()
            print(f"Выполняется команда: {command}")  
            if not command:
                continue
                
            parts = command.split()
            if not parts:
                continue
                
            cmd = parts[0].lower()
            
            if cmd == "exit":
                print("Выход из программы...")
                os._exit(0)
                
            elif cmd == "help":
                print("\nДоступные команды:")
                print("  list                           - показать все карты")
                print("  add <тип> <HEX_UID>            - добавить карту")
                print("  del <тип> <HEX_UID>            - удалить карту")
                print("  help                           - показать эту справку")
                print("  exit                           - выйти из программы")
                print("Пример: add key 09250C05")
                
            elif cmd == "list":
                cards = CARD_DB.list_cards()
                if not cards:
                    print("База данных пуста")
                else:
                    print(f"\nСписок карт в БД ({len(cards)} шт.):")
                    for i, card in enumerate(cards, 1):
                        card_type = card["card_type"]
                        uid = card["uid"]
                        date_added = card.get("date_added", "неизвестно")
                        has_image = "Да" if card.get("has_image") else "Нет"
                        print(f"{i}. Тип: {card_type}, UID: {uid}, Изображение: {has_image}, Добавлена: {date_added}")
                
            elif cmd == "add" and len(parts) >= 3:
                card_type = parts[1]
                uid_str = " ".join(parts[2:])
                
                print(f"Добавление карты: тип={card_type}, UID={uid_str}")  
                success = CARD_DB.add_card(card_type, uid_str)
                
                if success:
                    print(f"Карта {card_type} с UID {uid_str} успешно добавлена!")
                else:
                    print(f"Карта {card_type} с UID {uid_str} уже существует в БД")
                    
            elif cmd == "del" and len(parts) >= 3:
                card_type = parts[1]
                uid_str = " ".join(parts[2:])
                
                print(f"Удаление карты: тип={card_type}, UID={uid_str}")  
                success = CARD_DB.remove_card(card_type, uid_str)
                
                if success:
                    print(f"Карта {card_type} с UID {uid_str} успешно удалена!")
                else:
                    print(f"Карта {card_type} с UID {uid_str} не найдена в БД")
                    
            else:
                print(f"Неизвестная команда: {command}")
                print("Введите 'help' для получения справки")
                
        except Exception as e:
            print(f"Ошибка при выполнении команды: {e}")
            import traceback
            traceback.print_exc()