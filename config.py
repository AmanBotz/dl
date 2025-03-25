# config.py
import os

# Telegram Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_here")
API_ID = int(os.getenv("API_ID", 12345))
API_HASH = os.getenv("API_HASH", "your_api_hash_here")

# Parmar Videos Download API credentials
USER_ID = os.getenv("USER_ID", "582457")
AUTHORIZATION = os.getenv("AUTHORIZATION", "your_authorization_token_here")

# Deployment settings
PORT = int(os.getenv("PORT", 8000))

# Maximum number of concurrent threads for downloading segments
MAX_THREADS = int(os.getenv("MAX_THREADS", 20))
