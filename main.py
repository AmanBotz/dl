# main.py
import threading
import time
from bot import run_bot
from flask_app import run_flask

def main():
    # Start the Flask health-check server in a daemon thread.
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Continuously run the Telegram bot; if it crashes, log and restart.
    while True:
        try:
            run_bot()
        except Exception as e:
            print(f"[Main] Bot crashed: {e}")
        print("[Main] Restarting bot in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    main()
