"""
Flask API for devsecops-k8s-platform.

Endpoints:
  GET /         build info
  GET /health   liveness probe
  GET /ready    readiness probe
  GET /metrics  Prometheus scrape
"""

import logging
import os
import socket
import time
from flask import Flask, jsonify, Response

# Prometheus client is optional - degrade gracefully if absent
try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

# Configure structured logging (JSON-friendly for Splunk/CloudWatch ingestion)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}'
)
log = logging.getLogger(__name__)

app = Flask(__name__)
START_TIME = time.time()
BUILD_VERSION = os.getenv("BUILD_VERSION", "dev")
BUILD_COMMIT = os.getenv("BUILD_COMMIT", "unknown")

# Metrics
if METRICS_ENABLED:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"]
    )
    REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency",
        ["endpoint"]
    )


@app.before_request
def before_request():
    from flask import request
    request.start_time = time.time()


@app.after_request
def after_request(response):
    if METRICS_ENABLED:
        from flask import request
        duration = time.time() - getattr(request, "start_time", time.time())
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        REQUEST_DURATION.labels(endpoint=request.path).observe(duration)
    return response


@app.route("/")
def index():
    return jsonify({
        "service": "devsecops-k8s-platform",
        "version": BUILD_VERSION,
        "commit": BUILD_COMMIT,
        "hostname": socket.gethostname(),
        "uptime_seconds": int(time.time() - START_TIME)
    })


@app.route("/health")
def health():
    """Liveness probe - always returns 200 if the process is alive."""
    return jsonify({"status": "healthy"}), 200


@app.route("/ready")
def ready():
    """
    Readiness probe - could check downstream dependencies.
    Kept simple here; in production this would verify DB connections,
    cache availability, etc.
    """
    return jsonify({"status": "ready"}), 200


@app.route("/metrics")
def metrics():
    """Prometheus scrape endpoint."""
    if not METRICS_ENABLED:
        return "prometheus_client not installed\n", 501
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    log.info(f"Starting devsecops-k8s-platform on port {port}")
    app.run(host="0.0.0.0", port=port)
