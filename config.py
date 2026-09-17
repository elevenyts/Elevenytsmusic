from os import getenv

from dotenv import load_dotenv

load_dotenv()

API_ID = int(getenv("API_ID", "0"))
API_HASH = getenv("API_HASH", "")
BOT_TOKEN = getenv("BOT_TOKEN", "")
SESSION_STRING = getenv("SESSION_STRING", "")

MONGO_URL = getenv("MONGO_URL", "mongodb://localhost:27017")
OWNER_ID = int(getenv("OWNER_ID", "0"))

DURATION_LIMIT = int(getenv("DURATION_LIMIT_MIN", "60")) * 60
