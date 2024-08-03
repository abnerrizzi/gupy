# Use the official Python image from the Docker Hub
FROM python:3.9-alpine

WORKDIR /app

COPY app/* app/
RUN pip install --no-cache-dir -r app/requirements.txt

# COPY app /app/app
COPY *.sh *.sql .
RUN tree

# ENTRYPOINT ["/app/run_scrap.sh"]
