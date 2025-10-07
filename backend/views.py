import json
import logging
import websockets
import base64
from datetime import datetime
from backend.settings import CONNECTED_CLIENTS, CARD_DB, HTTP_PORT

SERIAL_MONITOR_CLIENTS = set()

async def handle_connection(websocket):
    """Обработка подключения клиента"""
    CONNECTED_CLIENTS.add(websocket)
    client_ip = websocket.remote_address[0]
    logging.info(f"Новое подключение от {client_ip}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logging.info(f"Получено сообщение от {client_ip}: {data}")
                
                if "command" in data:
                    command = data.get("command")
                    logging.info(f"Обработка команды: {command}")
                    
                    if command == "start_serial_monitor":
                        SERIAL_MONITOR_CLIENTS.add(websocket)
                        response = {
                            "status": "success",
                            "command": "start_serial_monitor",
                            "message": "Монитор порта активирован"
                        }
                        await websocket.send(json.dumps(response))
                        continue
                    
                    elif command == "get_card_details_by_uid":
                        uid = data.get("uid")
                        if uid:
                            card_data = None
                            for card_type in ["KEY", "WORKER", "SECURITY"]:
                                card_data = CARD_DB.get_card_with_image(card_type, uid)
                                if card_data:
                                    break
                            
                            if card_data:
                                image_url = None
                                if card_data.get("has_image") and card_data.get("image_filename"):
                                    image_url = f"http://localhost:{HTTP_PORT}/media/{card_data['image_filename']}"
                                
                                response = {
                                    "type": "card_scanned",
                                    "cardUID": uid,
                                    "cardType": card_data["card_type"],
                                    "accessGranted": True,
                                    "hasImage": card_data.get("has_image", False),
                                    "imageUrl": image_url,
                                    "timestamp": datetime.now().isoformat()
                                }
                            else:
                                response = {
                                    "type": "card_scanned",
                                    "cardUID": uid,
                                    "cardType": "UNKNOWN",
                                    "accessGranted": False,
                                    "hasImage": False,
                                    "timestamp": datetime.now().isoformat()
                                }
                            
                            await websocket.send(json.dumps(response))
                        continue
                    
                    elif command == "list_cards":
                        cards = CARD_DB.list_cards()
                        response = {
                            "status": "success",
                            "command": "list_cards",
                            "cards": cards,
                            "count": len(cards)
                        }
                        await websocket.send(json.dumps(response))
                        continue
                        
                    elif command == "upload_image":
                        card_type = data.get("card_type")
                        uid = data.get("uid")
                        image_data = data.get("image_data")
                        filename = data.get("filename")
                        
                        logging.info(f"Загрузка изображения: тип={card_type}, UID={uid}, файл={filename}")
                        
                        if card_type and uid and image_data and filename:
                            try:
                                if ',' in image_data:
                                    image_data = image_data.split(',')[1]
                                
                                image_bytes = base64.b64decode(image_data)
                                logging.info(f"Изображение декодировано, размер: {len(image_bytes)} байт")
                                
                                success, message = CARD_DB.save_card_image(card_type, uid, image_bytes, filename)
                                
                                response = {
                                    "status": "success" if success else "error",
                                    "command": "upload_image",
                                    "message": message
                                }
                                logging.info(f"Результат загрузки: {message}")
                                
                            except Exception as e:
                                logging.error(f"Ошибка загрузки изображения: {str(e)}")
                                response = {
                                    "status": "error",
                                    "command": "upload_image",
                                    "message": f"Ошибка обработки изображения: {str(e)}"
                                }
                        else:
                            missing = []
                            if not card_type: missing.append("card_type")
                            if not uid: missing.append("uid")
                            if not image_data: missing.append("image_data")
                            if not filename: missing.append("filename")
                            response = {
                                "status": "error",
                                "command": "upload_image",
                                "message": f"Отсутствуют поля: {', '.join(missing)}"
                            }
                        await websocket.send(json.dumps(response))
                        continue
                    
                    elif command == "get_card_details":
                        card_type = data.get("card_type")
                        uid = data.get("uid")
                        
                        if card_type and uid:
                            card_data = CARD_DB.get_card_with_image(card_type, uid)
                            if card_data:
                                response = {
                                    "status": "success",
                                    "command": "get_card_details",
                                    "card": card_data
                                }
                            else:
                                response = {
                                    "status": "error",
                                    "command": "get_card_details",
                                    "message": "Карта не найдена"
                                }
                        else:
                            response = {
                                "status": "error",
                                "command": "get_card_details",
                                "message": "Отсутствуют card_type или uid"
                            }
                        await websocket.send(json.dumps(response))
                        continue
                        
                    else:
                        response = {
                            "status": "error",
                            "message": f"Неизвестная команда: {command}"
                        }
                        await websocket.send(json.dumps(response))
                        continue
                
                elif "card_type" in data and "uid" in data and "state" in data:
                    card_type = data.get("card_type")
                    uid = data.get("uid")
                    incoming_state = data.get("state")
                    
                    if incoming_state == "" or incoming_state is None:
                        exists = CARD_DB.check_card(card_type, uid)
                        state = 1 if exists else 0
                        
                        logging.info(f"Проверка карты: тип={card_type}, UID={uid}, результат={state}")
                        
                        response = {
                            "card_type": card_type,
                            "uid": uid,
                            "state": state
                        }
                        await websocket.send(json.dumps(response))
                        
                    elif isinstance(incoming_state, (int, bool, str)) and str(incoming_state) in ["1", "true", "True"]:
                        success = CARD_DB.add_card(card_type, uid)
                        
                        response = {
                            "status": "success" if success else "error",
                            "message": f"Карта {card_type} с UID {uid} {'добавлена' if success else 'уже существует'}"
                        }
                        await websocket.send(json.dumps(response))
                        
                    elif isinstance(incoming_state, (int, bool, str)) and str(incoming_state) in ["0", "false", "False"]:
                        success = CARD_DB.remove_card(card_type, uid)
                        
                        response = {
                            "status": "success" if success else "error",
                            "message": f"Карта {card_type} с UID {uid} {'удалена' if success else 'не найдена'}"
                        }
                        await websocket.send(json.dumps(response))
                    
                else:
                    logging.warning(f"Неизвестный формат сообщения: {data}")
                    response = {
                        "status": "error",
                        "message": "Неизвестный формат сообщения"
                    }
                    await websocket.send(json.dumps(response))
                    
            except json.JSONDecodeError:
                logging.error(f"Невозможно разобрать JSON: {message}")
                await websocket.send(json.dumps({
                    "status": "error", 
                    "message": "Неверный формат JSON"
                }))
    except websockets.exceptions.ConnectionClosed as e:
        logging.info(f"Соединение с {client_ip} закрыто: {e}")
    finally:
        CONNECTED_CLIENTS.remove(websocket)
        SERIAL_MONITOR_CLIENTS.discard(websocket)
        logging.info(f"Клиент {client_ip} отключен")

async def send_serial_monitor_message(message, direction="incoming"):
    """Отправка сообщения всем клиентам монитора порта"""
    if SERIAL_MONITOR_CLIENTS:
        monitor_message = {
            "type": "serial_data",
            "message": message,
            "direction": direction,
            "timestamp": datetime.now().isoformat()
        }
        
        disconnected_clients = set()
        for client in SERIAL_MONITOR_CLIENTS:
            try:
                await client.send(json.dumps(monitor_message))
            except:
                disconnected_clients.add(client)
        
        for client in disconnected_clients:
            SERIAL_MONITOR_CLIENTS.remove(client)