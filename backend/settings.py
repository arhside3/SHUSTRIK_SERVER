from backend.setup_db import CardDatabase

PORT = 8765
HTTP_PORT = 8080
DB_FILE = "cards.db"
CARD_DB = CardDatabase(DB_FILE)
CONNECTED_CLIENTS = set()

