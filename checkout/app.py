from flask import Flask, jsonify
import requests

app = Flask(__name__)

# IMPORTANT: this will work in Docker later
CATALOGUE_URL = "http://catalogue:5001"
NOTIFICATIONS_URL = "http://notifications:5003"
@app.get("/checkout/<product_id>")
def checkout(product_id):
    try:
        print(f"[CHECKOUT] Order placed for product {product_id}",flush=True)
        response = requests.get(f"{CATALOGUE_URL}/products/{product_id}")
        if response.status_code != 200:
            return {"error": "Product not found"}, 404

        product = response.json()

        # 🔥 NEW: call notifications service
        requests.post(f"{NOTIFICATIONS_URL}/notify", json={
            "product_id": product_id
        })

        return {
            "message": "Order placed",
            "product": product
        }

    except Exception as e:
        return {"error": str(e)}, 500

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    return {"status": "ready"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)