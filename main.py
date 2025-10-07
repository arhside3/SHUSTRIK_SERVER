import asyncio
import websockets
import logging
import threading
from flask import Flask

from backend.settings import PORT, HTTP_PORT, CARD_DB
from backend.views import handle_connection
from backend.urls import app_urls
from backend.cmd_handler import console_handler
from backend.serial_handler import serial_handler

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO,
)

app = Flask(__name__, static_folder='frontend/static', static_url_path='/static')
app.register_blueprint(app_urls)

def run_flask():
    app.run(host='0.0.0.0', port=HTTP_PORT, threaded=True, debug=False, use_reloader=False)

async def main():
    server_ip = "0.0.0.0"
    
    console_thread = threading.Thread(target=console_handler, daemon=True)
    console_thread.start()
    
    serial_handler.start_background()
    logging.info(f"COM-порт монитор запущен на {serial_handler.port}")
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logging.info(f"Flask HTTP сервер запущен на http://{server_ip}:{HTTP_PORT}")
    logging.info(f"Откройте в браузере: http://localhost:{HTTP_PORT}")
    
    async with websockets.serve(handle_connection, server_ip, PORT):
        logging.info(f"WebSocket сервер запущен на ws://{server_ip}:{PORT}")
        
        cards = CARD_DB.list_cards()
        logging.info(f"База данных карт SQLite: {len(cards)} карт")
        
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Сервер остановлен.")
        serial_handler.disconnect()