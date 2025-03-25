# config.py
import os

# Telegram Bot configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token_here")
API_ID = int(os.environ.get("API_ID", "12345"))
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")

# Parmar Videos Download API credentials
USER_ID = os.environ.get("USER_ID", "582457")
AUTHORIZATION = os.environ.get("AUTHORIZATION", "your_authorization_token_here")

# Deployment settings
PORT = int(os.environ.get("PORT", 8000))
