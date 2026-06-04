from flask import Flask, jsonify, Response, g, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
import requests

app = Flask(__name__)

EXCLUDED_PATHS = {'/metrics', '/health', '/ready'}

PRODUCTS = {
    "1": {"id": "1", "name": "Keyboard", "price": 50, "stock": 10},
    "2": {"id": "2", "name": "Mouse", "price": 25, "stock": 20},
    "3": {"id": "3", "name": "Laptop", "price": 1200, "stock": 5},
}
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['endpoint']
)

@app.route("/favicon.ico")
def favicon():
    return "", 204

@app.before_request
def start_timer():
    g.start_time = time.time()

@app.after_request
def record_metrics(response):
    if request.path in EXCLUDED_PATHS:
        return response
    start_time = getattr(g, 'start_time', None)
    if start_time is not None:
        REQUEST_LATENCY.labels(endpoint=request.path).observe(time.time() - start_time)
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
    return response

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

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