from flask import Flask, jsonify, Response, g, request, render_template
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
import requests
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
import logging
import os
from opentelemetry.trace import get_current_span

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

provider = TracerProvider(
    resource=Resource.create({"service.name": "checkout"})
)

# Jaeger — always on locally
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")))
)

# Azure Monitor — only active when connection string is set
azure_connection_string = os.getenv("AZURE_MONITOR_CONNECTION_STRING")
if azure_connection_string:
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
    provider.add_span_processor(
        BatchSpanProcessor(
            AzureMonitorTraceExporter(connection_string=azure_connection_string)
        )
    )
trace.set_tracer_provider(provider)

RequestsInstrumentor().instrument()

EXCLUDED_PATHS = {'/metrics', '/health', '/ready'}

FlaskInstrumentor().instrument_app(
    app,
    excluded_urls="health,ready,metrics"
)

PRODUCTS = {
    "1": {
        "id": "1",
        "name": "Logitech MX Keys S",
        "brand": "Logitech",
        "category": "Keyboards",
        "price": 129,
        "stock": 15,
        "image": "Logitech MX Keys S.png",
        "description": "Wireless illuminated keyboard designed for productivity."
    },
    "2": {
        "id": "2",
        "name": "Logitech MX Master 3S",
        "brand": "Logitech",
        "category": "Mice",
        "price": 99,
        "stock": 18,
        "image": "Logitech MX Master 3S.png",
        "description": "Ergonomic wireless mouse with precision tracking."
    },
    "3": {
        "id": "3",
        "name": "Dell XPS 13",
        "brand": "Dell",
        "category": "Laptops",
        "price": 1499,
        "stock": 6,
        "image": "Dell XPS 13.png",
        "description": "Ultra-portable laptop for developers and professionals."
    },
    "4": {
        "id": "4",
        "name": "Apple Magic Keyboard",
        "brand": "Apple",
        "category": "Keyboards",
        "price": 149,
        "stock": 12,
        "image": "Apple Magic Keyboard.png",
        "description": "Slim wireless keyboard with rechargeable battery."
    },
    "5": {
        "id": "5",
        "name": "ASUS ROG Strix G16",
        "brand": "ASUS",
        "category": "Laptops",
        "price": 1899,
        "stock": 4,
        "image": "ASUS ROG Strix G16.png",
        "description": "High-performance gaming laptop with Intel Core i9."
    },
    "6": {
        "id": "6",
        "name": "Samsung T7 SSD 1TB",
        "brand": "Samsung",
        "category": "Storage",
        "price": 109,
        "stock": 25,
        "image": "Samsung T7 SSD 1TB.png",
        "description": "Portable USB-C SSD with fast transfer speeds."
    },
    "7": {
        "id": "7",
        "name": "Sony WH-1000XM5",
        "brand": "Sony",
        "category": "Audio",
        "price": 399,
        "stock": 9,
        "image": "Sony WH-1000XM5.png",
        "description": "Industry-leading wireless noise-cancelling headphones."
    },
    "8": {
        "id": "8",
        "name": "Keychron K2",
        "brand": "Keychron",
        "category": "Keyboards",
        "price": 99,
        "stock": 14,
        "image": "Keychron K2.png",
        "description": "Wireless mechanical keyboard for developers."
    },
    "9": {
        "id": "9",
        "name": "Logitech Brio 4K",
        "brand": "Logitech",
        "category": "Webcams",
        "price": 179,
        "stock": 11,
        "image": "Logitech Brio 4K.png",
        "description": "Professional 4K webcam for meetings and streaming."
    },
    "10": {
        "id": "10",
        "name": "Apple AirPods Pro (2nd Gen)",
        "brand": "Apple",
        "category": "Audio",
        "price": 329,
        "stock": 13,
        "image": "Apple AirPods Pro (2nd Gen).png",
        "description": "Wireless earbuds with adaptive noise cancellation."
    },
    "11": {
        "id": "11",
        "name": "LG UltraFine 27 Monitor",
        "brand": "LG",
        "category": "Monitors",
        "price": 499,
        "stock": 8,
        "image": "LG UltraFine 27 Monitor.png",
        "description": "27-inch IPS monitor with stunning colour accuracy."
    },
    "12": {
        "id": "12",
        "name": "Anker USB-C Hub",
        "brand": "Anker",
        "category": "Accessories",
        "price": 49,
        "stock": 30,
        "image": "Anker USB-C Hub.png",
        "description": "7-in-1 USB-C hub for laptops and tablets."
    }
}

# Index route - renders the main storefront page
@app.get("/")
def index():
    products_list = list(PRODUCTS.values())

    # Get unique categories
    categories = sorted(set(p["category"] for p in products_list))

    # Category icons mapping
    category_icons = {
        "Keyboards": '<i class="bi bi-keyboard fs-1"></i>',
        "Mice": '<i class="bi bi-mouse fs-1"></i>',
        "Laptops": '<i class="bi bi-laptop fs-1"></i>',
        "Storage": '<i class="bi bi-hdd-stack fs-1"></i>',
        "Audio": '<i class="bi bi-headphones fs-1"></i>',
        "Webcams": '<i class="bi bi-camera-video fs-1"></i>',
        "Monitors": '<i class="bi bi-display fs-1"></i>',
        "Accessories": '<i class="bi bi-usb-plug fs-1"></i>',
    }

    # Category counts
    category_counts = {}
    for cat in categories:
        category_counts[cat] = sum(1 for p in products_list if p["category"] == cat)

    # Featured products (first 4)
    featured_products = products_list[:4]

    return render_template("index.html",
        products=products_list,
        featured_products=featured_products,
        categories=categories,
        category_icons=category_icons,
        category_counts=category_counts
    )

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
    span = get_current_span()
    trace_id = format(span.get_span_context().trace_id, "032x")
    logger.info(f"Product lookup | trace_id={trace_id} | product_id={product_id}")
    
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