# Backend container image (FastAPI). Works on Render, AWS App Runner,
# Azure Container Apps, Google Cloud Run, Fly.io or any Docker host.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer is cached between code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend ./backend
COPY cloud ./cloud

# Never run as root inside the container.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/storage_data \
    && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:' + __import__('os').getenv('PORT','8000') + '/api/health').status == 200 else 1)"

# Cloud platforms inject $PORT. --proxy-headers trusts X-Forwarded-* from the load balancer.
CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
