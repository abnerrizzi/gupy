FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gosu \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /app/logs /app/out && chown -R appuser:appuser /app

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "app.scraper"]
