FROM python:3.12-alpine

RUN apk add --no-cache sqlite su-exec && \
    adduser -D -u 1000 appuser

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/app.py .
COPY api/fetchers ./fetchers
COPY api/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && chown -R appuser:appuser /app

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
