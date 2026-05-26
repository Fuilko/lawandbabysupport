# Multi-arch (works on both x86_64 and arm64 Graviton).
FROM python:3.11-slim

# System deps for geopandas/shapely/asyncpg.
# libpq-dev is needed for asyncpg; gdal-bin for geopandas convenience scripts.
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      gdal-bin \
      libgdal-dev \
      libpq-dev \
      curl \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_CONFIG=/usr/bin/gdal-config \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip "setuptools<70" wheel \
 && pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8080

# Built-in HEALTHCHECK as a defence-in-depth (compose also has its own).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
