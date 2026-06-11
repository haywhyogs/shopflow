from flask import Flask, jsonify, Response, g, request
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