# main.py
import threading
import time
from bot import run_bot
from flask_app import run_flask

def main():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    while True:
        try:
            run_bot()
        except Exception as e:
            print(f"[Main] Bot crashed: {e}")
        print("[Main] Restarting bot in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    main()
