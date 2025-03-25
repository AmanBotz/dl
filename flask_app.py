# flask_app.py
from flask import Flask, jsonify
from config import PORT

app = Flask(__name__)

@app.route("/")
def index():
    return "Bot server is running", 200

@app.route("/health")
def health_check():
    return jsonify({"status": "OK"}), 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    run_flask()
