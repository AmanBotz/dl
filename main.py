# main.py
import threading
from bot import run_bot
from flask_app import run_flask

if __name__ == "__main__":
    # Start Flask (health check) in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Run the Telegram bot (this call is blocking)
    run_bot()
