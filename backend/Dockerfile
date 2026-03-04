FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --without dev --no-root

ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright-browsers

RUN playwright install --with-deps chromium

COPY . .

RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /app/data/browser_state /app/data/debug && \
    chown -R appuser:appuser /app/data

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
