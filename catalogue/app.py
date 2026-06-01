from flask import Flask, jsonify

app = Flask(__name__)

PRODUCTS = {
    "1": {"id": "1", "name": "Keyboard", "price": 50, "stock": 10},
    "2": {"id": "2", "name": "Mouse", "price": 25, "stock": 20},
    "3": {"id": "3", "name": "Laptop", "price": 1200, "stock": 5},
}
@app.get("/products")
def get_products():
    return jsonify(list(PRODUCTS.values()))

@app.get("/products/<product_id>")
def get_product(product_id):
    print(f"[CATALOGUE] Fetch product {product_id}",flush=True)
    product = PRODUCTS.get(product_id)
    if not product:
        return {"error": "Product not found"}, 404
    return jsonify(product)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    return {"status": "ready"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)