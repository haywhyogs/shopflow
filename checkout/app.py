from flask import Flask, jsonify, g, request, Response, render_template, session, redirect, url_for, flash
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
from datetime import datetime
import uuid

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
    ['endpoint'],
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0]
)

ORDERS_PROCESSED = Counter(
    'orders_processed_total',
    'Total orders processed successfully'
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "shopflow-dev-secret-key-change-in-production")

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


@app.get("/product/<product_id>")
def product_detail(product_id):
    """Product detail page - fetches product from Catalogue service."""
    try:
        response = requests.get(f"{CATALOGUE_URL}/products/{product_id}", timeout=5)
        if response.status_code == 404:
            return render_template("404.html"), 404
        if response.status_code != 200:
            logger.error(f"Catalogue returned {response.status_code} for product {product_id}")
            return render_template("error.html", message="Unable to fetch product details"), 503
        product = response.json()
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching product {product_id} from catalogue")
        return render_template("error.html", message="Catalogue service timeout"), 503
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching product {product_id} from catalogue")
        return render_template("error.html", message="Catalogue service unavailable"), 503
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        return render_template("error.html", message="An unexpected error occurred"), 500

    return render_template("product.html", product=product, cart_item_count=_get_cart_count())


# ============================================================
# SHOPPING CART ROUTES
# ============================================================

def _get_cart():
    """Get cart from session, initialize if not exists."""
    if 'cart' not in session:
        session['cart'] = {}
    return session['cart']


def _get_cart_count():
    """Get total item count in cart."""
    cart = _get_cart()
    return sum(cart.values()) if cart else 0


def _save_cart(cart):
    """Save cart to session and mark modified."""
    session['cart'] = cart
    session.modified = True


def _fetch_product_from_catalogue(product_id):
    """Fetch single product from Catalogue service."""
    try:
        response = requests.get(f"{CATALOGUE_URL}/products/{product_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            logger.error(f"Catalogue returned {response.status_code} for product {product_id}")
            return None
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching product {product_id} from catalogue")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching product {product_id} from catalogue")
        return None
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        return None


@app.get("/cart")
def view_cart():
    """View cart contents - fetch products from catalogue service. Renders cart page."""
    cart = _get_cart()

    if not cart:
        return render_template("cart.html", cart_items=[], grand_total=0, empty=True, messages=[])

    cart_items = []
    grand_total = 0
    messages = []

    for product_id, quantity in cart.items():
        product = _fetch_product_from_catalogue(product_id)
        if not product:
            # Product no longer exists, skip and add informational message
            messages.append(f"Product {product_id} no longer available and has been removed from cart")
            # Remove from cart since it no longer exists
            del cart[product_id]
            continue

        # Validate stock
        available_stock = product.get('stock', 0)
        actual_quantity = min(quantity, available_stock)

        if actual_quantity != quantity:
            # Adjust quantity to available stock
            cart[product_id] = actual_quantity
            messages.append(f"Adjusted quantity for {product['name']} to available stock ({available_stock})")

        line_total = product['price'] * actual_quantity
        grand_total += line_total

        cart_items.append({
            'product': product,
            'quantity': actual_quantity,
            'line_total': line_total,
            'in_stock': available_stock > 0,
            'available_stock': available_stock
        })

    # Save cart in case quantities were adjusted or products removed
    _save_cart(cart)

    return render_template("cart.html", cart_items=cart_items, grand_total=grand_total, empty=len(cart_items) == 0, messages=messages)


@app.post("/cart/add/<product_id>")
def add_to_cart(product_id):
    """Add product to cart."""
    # Verify product exists in catalogue
    product = _fetch_product_from_catalogue(product_id)
    if not product:
        return jsonify({"success": False, "error": "Product not found", "product_id": product_id}), 404

    if product.get('stock', 0) <= 0:
        return jsonify({"success": False, "error": "Product is out of stock", "product_id": product_id}), 400

    cart = _get_cart()
    current_qty = cart.get(product_id, 0)

    # Check stock limit
    if current_qty >= product['stock']:
        flash(f"Cannot add more. Only {product['stock']} in stock.", "warning")
    else:
        cart[product_id] = current_qty + 1
        _save_cart(cart)
        flash(f"Added {product['name']} to cart!", "success")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "product": product["name"],
            "cart_count": sum(cart.values())
        })

    return redirect(request.referrer or url_for('index'))


@app.post("/cart/remove/<product_id>")
def remove_from_cart(product_id):
    """Remove product from cart."""
    cart = _get_cart()
    if product_id in cart:
        del cart[product_id]
        _save_cart(cart)
        flash("Item removed from cart", "info")
    return redirect(url_for('view_cart'))


@app.post("/cart/update/<product_id>")
def update_cart(product_id):
    """Update product quantity in cart."""
    cart = _get_cart()

    try:
        new_qty = int(request.form.get('quantity', 1))
    except ValueError:
        new_qty = 1

    # Verify product exists
    product = _fetch_product_from_catalogue(product_id)
    if not product:
        if product_id in cart:
            del cart[product_id]
            _save_cart(cart)
        flash("Product no longer available", "danger")
        return redirect(url_for('view_cart'))

    # Validate stock
    available_stock = product.get('stock', 0)
    if new_qty > available_stock:
        new_qty = available_stock
        flash(f"Adjusted to maximum available stock ({available_stock})", "warning")
    else:
        flash("Cart updated", "success")

    if new_qty <= 0:
        del cart[product_id]
        flash("Item removed from cart", "info")
    else:
        cart[product_id] = new_qty

    _save_cart(cart)
    return redirect(url_for('view_cart'))


# ============================================================
# CHECKOUT / PLACE ORDER ROUTE
# ============================================================

@app.post("/place-order")
def place_order():
    """Process order: validate stock, call notifications, generate order number, clear cart, redirect to success."""
    cart = _get_cart()

    if not cart:
        flash("Your cart is empty", "warning")
        return redirect(url_for('view_cart'))

    # Re-fetch all products from catalogue to validate stock
    order_items = []
    grand_total = 0
    catalogue_unavailable = False

    for product_id, quantity in cart.items():
        product = _fetch_product_from_catalogue(product_id)
        if not product:
            # Product not found - could be 404 or catalogue unavailable
            flash(f"Product {product_id} no longer available", "danger")
            return redirect(url_for('view_cart'))

        available_stock = product.get('stock', 0)
        if quantity > available_stock:
            flash(f"Not enough stock for {product['name']}. Only {available_stock} available.", "danger")
            return redirect(url_for('view_cart'))

        line_total = product['price'] * quantity
        grand_total += line_total

        order_items.append({
            'product': product,
            'quantity': quantity,
            'line_total': line_total
        })

    # Call Notifications service for each item
    notification_errors = []
    for item in order_items:
        product_id = item['product']['id']
        try:
            response = requests.post(
                f"{NOTIFICATIONS_URL}/notify",
                json={"product_id": product_id},
                timeout=5
            )
            if response.status_code != 200:
                logger.warning(f"Notification service returned {response.status_code} for product {product_id}")
                notification_errors.append(product_id)
        except Exception as e:
            logger.error(f"Failed to send notification for product {product_id}: {e}")
            notification_errors.append(product_id)

    # Generate order number: SHOPFLOW-YYYYMMDD-XXXX
    today = datetime.now().strftime("%Y%m%d")
    random_suffix = uuid.uuid4().hex[:8].upper()
    order_number = f"SHOPFLOW-{today}-{random_suffix}"

    # Store order details in session for success page
    session['last_order'] = {
        'order_number': order_number,
        'order_date': datetime.now().strftime("%B %d, %Y"),
        'order_items': [
            {
                'product_id': item['product']['id'],
                'product_name': item['product']['name'],
                'product_image': item['product'].get('image', ''),
                'price': item['product']['price'],
                'quantity': item['quantity'],
                'line_total': item['line_total']
            }
            for item in order_items
        ],
        'grand_total': grand_total,
        'notification_errors': notification_errors
    }
    session.modified = True

    # Clear cart
    session['cart'] = {}
    session.modified = True

    # Increment orders processed metric
    ORDERS_PROCESSED.inc()

    return redirect(url_for('order_success'))


@app.get("/order-success")
def order_success():
    """Display order success page."""
    order = session.get('last_order')
    if not order:
        flash("No recent order found", "warning")
        return redirect(url_for('index'))

    # Clear the order from session after displaying
    session.pop('last_order', None)
    session.modified = True

    # Build notification message
    notification_errors = order.get('notification_errors', [])
    notification_msg = "Order placed successfully!"
    if notification_errors:
        notification_msg += f" (Note: {len(notification_errors)} notification(s) could not be sent)"

    return render_template("order_success.html",
        order_number=order['order_number'],
        order_date=order['order_date'],
        order_items=order['order_items'],
        grand_total=order['grand_total'],
        notification_message=notification_msg,
        notification_errors=notification_errors
    )


# Index route - renders the storefront template using products from Catalogue service
@app.get("/")
def index():
    try:
        response = requests.get(f"{CATALOGUE_URL}/products", timeout=5)
        if response.status_code != 200:
            return {"error": "Failed to fetch products from catalogue"}, 500
        products_list = response.json()
    except Exception as e:
        logger.error(f"Failed to fetch products: {e}")
        return {"error": "Catalogue service unavailable"}, 503

    # Get unique categories
    categories = sorted(set(p["category"] for p in products_list))

    # Featured products (first 4)
    featured_products = products_list[:4]

    return render_template("index.html",
        products=products_list,
        featured_products=featured_products,
        categories=categories,
        cart_item_count=_get_cart_count()
    )

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