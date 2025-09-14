from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello everyone! Flask app running in Docker ✅"

@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)