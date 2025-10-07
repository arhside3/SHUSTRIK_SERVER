import serial
import json
import logging
import asyncio
import threading
from datetime import datetime
from backend.settings import CARD_DB

class SerialHandler:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
        self.data_buffer = ""
        self.loop = None
        
    def connect(self):
        """Подключение к COM-порту"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            logging.info(f"Подключено к {self.port} с Baudrate {self.baudrate}")
            return True
        except Exception as e:
            logging.error(f"Ошибка подключения к {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Отключение от COM-порта"""
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logging.info("COM-порт закрыт")
    
    async def process_message(self, message):
        """Обработка входящих сообщений от ESP32"""
        try:
            await self.send_to_monitor(message, "incoming")
            
            data = json.loads(message)
            logging.info(f"Получено сообщение от ESP32: {data}")
            
            message_type = data.get("type")
            device_id = data.get("deviceId")
            card_uid = data.get("cardUID")
            reader_id = data.get("readerId")
            
            if message_type == "cardData":
                if card_uid:
                    card_exists = False
                    card_type = "UNKNOWN"
                    
                    for check_type in ["KEY", "WORKER", "SECURITY"]:
                        if CARD_DB.check_card(check_type, card_uid):
                            card_exists = True
                            card_type = check_type
                            break
                    
                    access_granted = card_exists
                    
                    await self.send_card_scanned_event(card_uid, card_type, access_granted)
                    
                    response = {
                        "type": "cardResponse",
                        "cardType": card_type,
                        "accessGranted": access_granted,
                        "timestamp": int(datetime.now().timestamp())
                    }
                    
                    await self.send_response(response)
                    logging.info(f"Ответ отправлен: {response}")
                    
            elif message_type == "ping":
                response = {
                    "type": "pong",
                    "deviceId": device_id,
                    "timestamp": int(datetime.now().timestamp())
                }
                await self.send_response(response)
                logging.info(f"Pong отправлен: {response}")
                
        except json.JSONDecodeError as e:
            logging.error(f"Ошибка разбора JSON: {e}, данные: {message}")
            await self.send_to_monitor(f"INVALID JSON: {message}", "error")
        except Exception as e:
            logging.error(f"Ошибка обработки сообщения: {e}")
            await self.send_to_monitor(f"ERROR: {str(e)}", "error")
    
    async def send_card_scanned_event(self, card_uid, card_type, access_granted):
        """Отправка события сканирования карты"""
        try:
            from backend.views import SERIAL_MONITOR_CLIENTS
            from backend.settings import HTTP_PORT
            
            card_data = None
            for check_type in ["KEY", "WORKER", "SECURITY"]:
                card_data = CARD_DB.get_card_with_image(check_type, card_uid)
                if card_data:
                    break
            
            image_url = None
            has_image = False
            if card_data and card_data.get("has_image") and card_data.get("image_filename"):
                has_image = True
                image_url = f"http://localhost:{HTTP_PORT}/media/{card_data['image_filename']}"
            
            event_data = {
                "type": "card_scanned",
                "cardUID": card_uid,
                "cardType": card_type,
                "accessGranted": access_granted,
                "hasImage": has_image,
                "imageUrl": image_url,
                "timestamp": datetime.now().isoformat()
            }
            
            disconnected_clients = set()
            for client in SERIAL_MONITOR_CLIENTS:
                try:
                    await client.send(json.dumps(event_data))
                except:
                    disconnected_clients.add(client)
            
            for client in disconnected_clients:
                SERIAL_MONITOR_CLIENTS.remove(client)
                
        except Exception as e:
            logging.error(f"Ошибка отправки события карты: {e}")
    
    async def send_response(self, data):
        """Отправка ответа в COM-порт"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                message = json.dumps(data) + '\n'
                self.serial_conn.write(message.encode('utf-8'))
                self.serial_conn.flush()
                logging.info(f"Отправлено в COM-порт: {data}")
                
                await self.send_to_monitor(json.dumps(data), "outgoing")
        except Exception as e:
            logging.error(f"Ошибка отправки в COM-порт: {e}")
    
    def read_serial_data(self):
        """Чтение данных из COM-порта"""
        try:
            if self.serial_conn and self.serial_conn.is_open:
                data = self.serial_conn.readline().decode('utf-8').strip()
                if data:
                    return data
        except Exception as e:
            logging.error(f"Ошибка чтения из COM-порта: {e}")
        return None
    
    async def start_reading(self):
        """Асинхронный запуск чтения COM-порта"""
        self.running = True
        
        if not self.connect():
            logging.error("Не удалось подключиться к COM-порту")
            return
        
        logging.info("Начало чтения COM-порта...")
        
        while self.running:
            try:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.read_serial_data
                )
                
                if data:
                    lines = data.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            try:
                                json.loads(line)
                                asyncio.create_task(self.process_message(line))
                            except json.JSONDecodeError:
                                self.data_buffer += line
                                try:
                                    json.loads(self.data_buffer)
                                    asyncio.create_task(self.process_message(self.data_buffer))
                                    self.data_buffer = ""
                                except json.JSONDecodeError:
                                    if len(self.data_buffer) > 1000:
                                        self.data_buffer = ""
                    
            except Exception as e:
                logging.error(f"Ошибка в цикле чтения: {e}")
                await asyncio.sleep(1)
            
            await asyncio.sleep(0.01)
    
    async def send_to_monitor(self, message, direction="incoming"):
        """Отправка данных в монитор порта"""
        try:
            from backend.views import send_serial_monitor_message
            await send_serial_monitor_message(message, direction)
        except Exception as e:
            logging.error(f"Ошибка отправки в монитор: {e}")
    
    def start_background(self):
        """Запуск в фоновом потоке"""
        def run():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.start_reading())
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread

serial_handler = SerialHandler()