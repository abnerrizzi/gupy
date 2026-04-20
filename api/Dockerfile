FROM python:3.12-alpine

RUN apk add --no-cache sqlite su-exec

WORKDIR /app

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/app.py .
COPY docker-entrypoint.sh .
COPY run_scrap.sh .
COPY sqlite-init.sql .

RUN chmod +x *.sh

ENTRYPOINT ["./docker-entrypoint.sh"]

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
