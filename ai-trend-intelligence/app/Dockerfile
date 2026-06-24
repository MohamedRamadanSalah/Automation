FROM python:3.12-slim

# System dependencies for WeasyPrint (pango, cairo, gdk-pixbuf)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer 1: install all dependencies (cache-busts only when pyproject.toml changes)
COPY pyproject.toml ./
RUN mkdir -p src/trend_intel && touch src/trend_intel/__init__.py \
    && pip install --no-cache-dir . \
    && rm -rf src/trend_intel

# Layer 2: real source — re-install package only (deps already in layer 1)
COPY src/ ./src/
RUN pip install --no-cache-dir --no-deps .

# Alembic config and migrations
COPY alembic.ini ./
COPY migrations/ ./migrations/

RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "trend_intel.main:app", "--host", "0.0.0.0", "--port", "8000"]
