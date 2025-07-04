import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
