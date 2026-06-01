from flask import Flask, jsonify

app = Flask(__name__)

@app.post("/notify")
def notify():
    print("[NOTIFICATIONS] Notification sent", flush=True)
    return {"status": "notification sent"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    return {"status": "ready"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003)