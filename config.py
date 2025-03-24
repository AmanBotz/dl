import os

# Telegram API credentials for Pyrogram – set these as environment variables.
API_ID = int(os.environ.get("TG_API_ID", 123456))  # Replace with your actual API_ID
API_HASH = os.environ.get("TG_API_HASH", "YOUR_API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

# Parmar Academy API credentials – these are now in config.
USER_ID = os.environ.get("USER_ID", "582457")
AUTHORIZATION = os.environ.get("AUTHORIZATION", "YOUR_AUTHORIZATION_TOKEN")

# API host for Parmar Academy
HOST = "https://parmaracademyapi.classx.co.in"
