# Use the official Python image from the Docker Hub
FROM python:3.9-slim

WORKDIR /app

COPY app /app/app
COPY create_sqlite_from_csv.sh /app/
COPY run_scrap.sh /app/
COPY sqlite-init.sql /app/

COPY app/requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN chmod +x /app/run_scrap.sh /app/create_sqlite_from_csv.sh

ENTRYPOINT ["/app/run_scrap.sh"]
