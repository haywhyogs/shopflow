from flask import Flask, jsonify, g, request, Response
import requests
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
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
import random

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

EXCLUDED_PATHS = {'/metrics', '/health', '/ready'}


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

ORDERS_PROCESSED = Counter(
    'orders_processed_total',
    'Total orders processed successfully'
)

app = Flask(__name__)

provider = TracerProvider(
    resource=Resource.create({"service.name": "checkout"})
)
# Jaeger — always on locally
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")))
)

# Azure Monitor — only active when connection string is set
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

FlaskInstrumentor().instrument_app(
    app,
    excluded_urls="health,ready,metrics"
)
RequestsInstrumentor().instrument()

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

CATALOGUE_URL = "http://catalogue:5001"
NOTIFICATIONS_URL = "http://notifications:5003"

@app.get("/checkout/<product_id>")
def checkout(product_id):
    try:
        span = get_current_span()
        trace_id = format(span.get_span_context().trace_id, "032x")

        logger.info(f"Processing checkout | trace_id={trace_id} | product_id={product_id}")
  
        print(f"[CHECKOUT] Order placed for product {product_id}", flush=True)
        response = requests.get(f"{CATALOGUE_URL}/products/{product_id}")
        if response.status_code != 200:
            return {"error": "Product not found"}, 404
        product = response.json()
        requests.post(f"{NOTIFICATIONS_URL}/notify", json={"product_id": product_id})
        ORDERS_PROCESSED.inc()
        
        return {"message": "Order placed", "product": product, "version": "v2.0.0"}
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