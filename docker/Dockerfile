# syntax=docker/dockerfile:1.7
#
# Multi-stage build for minimal attack surface.
# Stage 1: build dependencies in a full Python image.
# Stage 2: copy only what we need into distroless.
#
# Final image has no shell, no package manager, no extra utilities.
# Size: ~50MB. Runs as non-root (uid 65532).
# ----------------------------------------------------------------------

# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /build

# Install dependencies into /install so we can copy just what we need
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy application code
COPY app/ /build/app/

# ---- Runtime stage ----
FROM gcr.io/distroless/python3-debian12:nonroot

# Build-time metadata (populated by CI)
ARG BUILD_VERSION=dev
ARG BUILD_COMMIT=unknown
ENV BUILD_VERSION=${BUILD_VERSION} \
    BUILD_COMMIT=${BUILD_COMMIT} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/usr/local/lib/python3.12/site-packages

WORKDIR /app

# Copy installed Python packages from build stage
COPY --from=builder /install /usr/local
# Copy application
COPY --from=builder /build/app ./app

# OCI image labels
LABEL org.opencontainers.image.title="devsecops-k8s-platform" \
      org.opencontainers.image.description="Reference DevSecOps platform with GitOps delivery" \
      org.opencontainers.image.source="https://github.com/akhiladarsh/devsecops-k8s-platform" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.authors="Akhil Adarsh Suryapagula"

USER nonroot
EXPOSE 8080

# Use python directly - distroless has no shell for gunicorn --daemon
# In production, run gunicorn as the ENTRYPOINT with config file
ENTRYPOINT ["python", "-m", "app.main"]
